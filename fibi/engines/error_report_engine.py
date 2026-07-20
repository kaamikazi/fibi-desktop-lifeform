"""Export safe local diagnostic bundles for Fibi."""

from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path

from fibi.logging_config import mask_secrets
from fibi.paths import data_dir, data_path
from fibi.runtime_paths import logs_dir, reports_dir, runtime_info
from fibi.version import APP_NAME, APP_VERSION, BUILD_CHANNEL
from fibi.build_info import build_summary


class ErrorReportEngine:
    """Create a small report zip without private databases or source files."""

    def __init__(self, reports_dir: Path | None = None) -> None:
        self.reports_dir = Path(reports_dir) if reports_dir is not None else reports_dir_fn()
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        health_snapshot: str = "",
        last_route_decision: str = "",
        recent_errors: list[str] | None = None,
        *,
        beta_mode: bool = False,
        issue_metadata: dict[str, object] | None = None,
        feedback_metadata: list[dict[str, object]] | None = None,
    ) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = self.reports_dir / f"fibi_error_report_{stamp}.zip"
        recent_errors = recent_errors or []
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
            version = {"app_name": APP_NAME, "app_version": APP_VERSION, "build_channel": BUILD_CHANNEL}
            version.update(build_summary())
            bundle.writestr("version.json", json.dumps(version, indent=2))
            bundle.writestr("runtime_paths.json", json.dumps(self._runtime_summary(), indent=2))
            bundle.writestr("beta_mode.txt", "on" if beta_mode else "off")
            bundle.writestr("health_snapshot.txt", mask_secrets(health_snapshot or "no health snapshot"))
            bundle.writestr("last_route_decision.txt", mask_secrets(last_route_decision or "unknown"))
            bundle.writestr("recent_errors.txt", mask_secrets("\n".join(recent_errors[-30:]) or "none"))
            if issue_metadata:
                bundle.writestr("issue_metadata.json", mask_secrets(json.dumps(issue_metadata, indent=2)))
            if feedback_metadata:
                bundle.writestr("feedback_metadata.json", mask_secrets(json.dumps(feedback_metadata, indent=2)))
            self._add_if_exists(bundle, data_path("startup_diagnostics.json"), "startup_diagnostics.json")
            self._add_if_exists(bundle, data_path("shutdown_marker.json"), "shutdown_marker.json")
            self._add_sanitized_settings(bundle)
            self._add_log_tail(bundle)
        return target

    @staticmethod
    def _runtime_summary() -> dict[str, object]:
        info = runtime_info()
        return {
            "packaged": info.packaged,
            "portable": info.portable,
            "app_root": str(info.app_root),
            "executable_dir": str(info.executable_dir),
            "user_data_dir": str(info.user_data_dir),
            "logs_dir": str(logs_dir()),
            "reports_dir": str(reports_dir()),
        }

    @staticmethod
    def _add_if_exists(bundle: zipfile.ZipFile, path: Path, arcname: str) -> None:
        if path.exists() and path.is_file():
            bundle.writestr(arcname, mask_secrets(path.read_text(encoding="utf-8", errors="replace")[:60_000]))

    @staticmethod
    def _add_sanitized_settings(bundle: zipfile.ZipFile) -> None:
        names = ["fibi_state.json", "app_settings.json", "voice_settings.json", "voice_skin_settings.json"]
        summary: dict[str, object] = {}
        for name in names:
            path = data_dir() / name
            if not path.exists():
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                summary[name] = "unreadable"
                continue
            summary[name] = ErrorReportEngine._mask_obj(raw)
        bundle.writestr("settings_summary.json", json.dumps(summary, indent=2))

    @staticmethod
    def _add_log_tail(bundle: zipfile.ZipFile) -> None:
        path = logs_dir() / "fibi.log"
        if not path.exists():
            legacy_path = data_path("fibi.log")
            path = legacy_path if legacy_path.exists() else path
        if not path.exists():
            bundle.writestr("recent_logs.txt", "no log file")
            return
        text = path.read_text(encoding="utf-8", errors="replace")
        bundle.writestr("recent_logs.txt", mask_secrets(text[-60_000:]))

    @staticmethod
    def _mask_obj(value):
        if isinstance(value, dict):
            masked = {}
            for key, item in value.items():
                lowered = str(key).lower()
                if any(token in lowered for token in ("key", "token", "secret", "password")):
                    masked[key] = "[secret]"
                else:
                    masked[key] = ErrorReportEngine._mask_obj(item)
            return masked
        if isinstance(value, list):
            return [ErrorReportEngine._mask_obj(item) for item in value[:20]]
        if isinstance(value, str):
            return mask_secrets(value[:500])
        return value


def reports_dir_fn() -> Path:
    """Tiny indirection to avoid shadowing the imported function in __init__."""

    return reports_dir()
