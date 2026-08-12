"""Filesystem and serialization safety helpers for private backup artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path, PurePosixPath
from typing import Any


class BackupSafetyError(ValueError):
    def __init__(self, category: str) -> None:
        super().__init__(category)
        self.category = category


def is_link_like(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        return bool(callable(is_junction) and is_junction())
    except OSError:
        return True


def ensure_no_link_ancestors(path: Path) -> None:
    current = Path(path)
    while True:
        if current.exists() and is_link_like(current):
            raise BackupSafetyError("unsafe_link_or_reparse_point")
        if current.parent == current:
            return
        current = current.parent


def safe_relative_path(value: str) -> PurePosixPath:
    if not value or "\\" in value or "\x00" in value:
        raise BackupSafetyError("unsafe_manifest_path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.drive or any(part in {"", ".", ".."} for part in path.parts):
        raise BackupSafetyError("unsafe_manifest_path")
    if ":" in path.parts[0]:
        raise BackupSafetyError("unsafe_manifest_path")
    return path


def resolve_bundle_artifact(bundle_root: Path, relative: str) -> Path:
    safe = safe_relative_path(relative)
    root = Path(bundle_root).resolve(strict=False)
    candidate = root.joinpath(*safe.parts).resolve(strict=False)
    if candidate == root or root not in candidate.parents:
        raise BackupSafetyError("manifest_path_escape")
    return candidate


def is_same_or_parent(candidate: Path, child: Path) -> bool:
    left = Path(candidate).resolve(strict=False)
    right = Path(child).resolve(strict=False)
    return left == right or left in right.parents


def is_within(candidate: Path, parent: Path) -> bool:
    child = Path(candidate).resolve(strict=False)
    root = Path(parent).resolve(strict=False)
    return child == root or root in child.parents


def validate_backup_output_root(output_root: Path, data_root: Path, repository_root: Path) -> Path:
    output = Path(output_root).expanduser()
    ensure_no_link_ancestors(output)
    resolved = output.resolve(strict=False)
    active = Path(data_root).resolve(strict=False)
    repository = Path(repository_root).resolve(strict=False)
    dedicated_private_root = active / "private_memory_backups"
    if is_same_or_parent(resolved, active):
        raise BackupSafetyError("unsafe_backup_destination")
    if is_within(resolved, active) and not is_within(resolved, dedicated_private_root):
        raise BackupSafetyError("unsafe_backup_destination")
    if is_within(resolved, repository) and not is_within(resolved, dedicated_private_root):
        raise BackupSafetyError("source_controlled_backup_destination")
    if resolved.exists() and not resolved.is_dir():
        raise BackupSafetyError("backup_destination_not_directory")
    return resolved


def validate_rehearsal_root(
    destination_root: Path,
    active_data_root: Path,
    backup_bundle: Path,
    repository_root: Path,
) -> Path:
    destination = Path(destination_root).expanduser()
    ensure_no_link_ancestors(destination)
    resolved = destination.resolve(strict=False)
    active = Path(active_data_root).resolve(strict=False)
    bundle = Path(backup_bundle).resolve(strict=False)
    repository = Path(repository_root).resolve(strict=False)
    if is_same_or_parent(resolved, active) or is_within(resolved, active):
        raise BackupSafetyError("active_data_destination_rejected")
    if is_same_or_parent(resolved, bundle) or is_within(resolved, bundle):
        raise BackupSafetyError("backup_bundle_destination_rejected")
    if is_within(resolved, repository) or is_same_or_parent(resolved, repository):
        raise BackupSafetyError("repository_destination_rejected")
    if resolved.exists() and not resolved.is_dir():
        raise BackupSafetyError("rehearsal_destination_not_directory")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    temporary = target.with_name(target.name + ".tmp")
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    replace_path(temporary, target)


def replace_path(source: Path, destination: Path, *, attempts: int = 5, delay_seconds: float = 0.05) -> None:
    """Replace a path, tolerating brief Windows scanner/indexer locks."""

    for attempt in range(attempts):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            if attempt + 1 >= attempts:
                raise
            time.sleep(delay_seconds)


def safe_remove_created_directory(path: Path, expected_parent: Path, prefix: str) -> bool:
    target = Path(path)
    parent = Path(expected_parent).resolve(strict=False)
    resolved = target.resolve(strict=False)
    if resolved.parent != parent or not resolved.name.startswith(prefix) or is_link_like(target):
        return False
    try:
        if target.exists():
            shutil.rmtree(target)
        return True
    except OSError:
        return False


__all__ = [
    "BackupSafetyError",
    "ensure_no_link_ancestors",
    "is_link_like",
    "is_same_or_parent",
    "is_within",
    "resolve_bundle_artifact",
    "replace_path",
    "safe_relative_path",
    "safe_remove_created_directory",
    "sha256_file",
    "validate_backup_output_root",
    "validate_rehearsal_root",
    "write_json_atomic",
]
