"""Structured logging setup for Fibi.

The app still has older ``print`` diagnostics in some hot paths. This module is
the production logging foundation used by newer code and future migrations.
It keeps logs local, rotates them by startup overwrite, and masks obvious
secrets before records reach console or file handlers.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from fibi.runtime_paths import logs_dir

DEFAULT_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)([^\s,;]+)"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
)


@dataclass(frozen=True)
class LoggingSetup:
    """Details about the active logging setup."""

    level: int
    log_path: Path | None
    configured: bool


class SecretMaskingFilter(logging.Filter):
    """Mask common secret shapes in log messages and arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_secrets(record.getMessage())
        record.args = ()
        return True


def configure_logging(
    *,
    level_name: str | None = None,
    log_path: Path | None = None,
    force: bool = False,
) -> LoggingSetup:
    """Configure root logging once for local console and file output."""

    root = logging.getLogger()
    if root.handlers and not force:
        return LoggingSetup(root.level, log_path, False)

    level = _level_from_name(level_name or os.getenv("FIBI_LOG_LEVEL", "INFO"))
    resolved_log_path = _log_path(log_path)
    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
    secret_filter = SecretMaskingFilter()

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    console.addFilter(secret_filter)

    file_handler = logging.FileHandler(resolved_log_path, encoding="utf-8", mode="a")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(secret_filter)

    if force:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()

    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)
    logging.getLogger(__name__).debug("Fibi logging configured at %s", logging.getLevelName(level))
    return LoggingSetup(level, resolved_log_path, True)


def shutdown_logging() -> None:
    """Flush, close, and detach root handlers.

    Normal app shutdown can let Python close handlers automatically. Tests and
    tools that write logs to temporary folders should call this before deleting
    those folders, especially on Windows.
    """

    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.flush()
        handler.close()
        root.removeHandler(handler)


def mask_secrets(text: str) -> str:
    """Return text with obvious credentials replaced by ``[secret]``."""

    masked = text
    for pattern in SECRET_PATTERNS:
        if pattern.pattern.startswith("\\bsk-"):
            masked = pattern.sub("sk-[secret]", masked)
        else:
            masked = pattern.sub(lambda match: f"{match.group(1)}=[secret]", masked)
    return masked


def _log_path(path: Path | None) -> Path:
    if path is not None:
        return Path(path)
    configured = os.getenv("FIBI_LOG_FILE", "").strip()
    return Path(configured).expanduser() if configured else logs_dir() / "fibi.log"


def _level_from_name(name: str) -> int:
    normalized = name.strip().upper()
    level = logging.getLevelName(normalized)
    return level if isinstance(level, int) else logging.INFO
