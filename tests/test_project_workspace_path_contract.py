from __future__ import annotations

from pathlib import Path

import pytest

from fibi.engines.project_workspace_engine import ProjectWorkspaceEngine
from fibi.engines.types import FileDropResult


class ReadSpy:
    def __init__(self) -> None:
        self.paths: list[Path] = []

    def read_user_file(self, path: str | Path, source: str = "dropped_file") -> FileDropResult:
        self.paths.append(Path(path))
        return FileDropResult(False, message="unexpected read", error="unexpected_read")


def _workspace(tmp_path: Path) -> tuple[ProjectWorkspaceEngine, Path]:
    project = tmp_path / "project"
    (project / "app").mkdir(parents=True)
    (project / "app" / "page.txt").write_text("safe project text", encoding="utf-8")
    engine = ProjectWorkspaceEngine(tmp_path / "workspaces.json")
    assert engine.add_workspace(project).ok
    return engine, project


@pytest.mark.parametrize(
    "untrusted_path",
    [
        "../outside.txt",
        r"..\outside.txt",
        r"nested\..\..\outside.txt",
        r"nested/..\../outside.txt",
        "/tmp/outside.txt",
        r"C:\outside.txt",
        r"C:outside.txt",
        r"\rooted.txt",
        r"\\server\share\outside.txt",
        "bad\x00name.txt",
    ],
)
def test_untrusted_paths_are_rejected_before_file_reader(
    tmp_path: Path,
    untrusted_path: str,
) -> None:
    engine, _project = _workspace(tmp_path)
    reader = ReadSpy()
    engine.file_reader = reader  # type: ignore[assignment]

    result = engine.read_file(untrusted_path)

    assert not result.ok
    assert result.error == "outside project"
    assert "outside the project" in result.message
    assert reader.paths == []


def test_internal_windows_separators_read_the_scanned_project_file(tmp_path: Path) -> None:
    engine, project = _workspace(tmp_path)
    reader = engine.file_reader
    reader_paths: list[Path] = []
    original_read = reader.read_user_file

    def record_read(path: str | Path, source: str = "dropped_file") -> FileDropResult:
        reader_paths.append(Path(path))
        return original_read(path, source)

    reader.read_user_file = record_read  # type: ignore[method-assign]

    result = engine.read_file(r"app\page.txt")

    assert result.ok
    assert result.item is not None and result.item.content_text == "safe project text"
    assert reader_paths == [project / "app" / "page.txt"]


def test_symlink_escape_fails_closed_without_opening_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    engine, project = _workspace(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside project text", encoding="utf-8")
    link = project / "linked.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        # Keep the fail-closed branch covered on Windows configurations where
        # creating a symlink requires privileges unavailable to the test user.
        monkeypatch.setattr(engine, "_contains_reparse_point", lambda path: Path(path) == link)

    reader = ReadSpy()
    engine.file_reader = reader  # type: ignore[assignment]

    result = engine.read_file("linked.txt")

    assert not result.ok
    assert result.error == "unsafe_link_or_reparse_point"
    assert reader.paths == []
