"""Unit tests for Fibi's local logging configuration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.logging_config import configure_logging, mask_secrets, shutdown_logging


def test_mask_secrets_filters_common_credentials() -> None:
    text = "api_key=abc123 token:supersecret authorization: Bearer abc.def sk-1234567890abcdef"

    masked = mask_secrets(text)

    assert "abc123" not in masked
    assert "supersecret" not in masked
    assert "abc.def" not in masked
    assert "sk-1234567890abcdef" not in masked
    assert "[secret]" in masked


def test_configure_logging_writes_masked_local_file(tmp_path: Path) -> None:
    log_path = tmp_path / "fibi.log"
    try:
        setup = configure_logging(level_name="DEBUG", log_path=log_path, force=True)

        logger = logging.getLogger("fibi.test")
        logger.info("token=%s", "plain-secret")

        for handler in logging.getLogger().handlers:
            handler.flush()

        contents = log_path.read_text(encoding="utf-8")
        assert setup.configured
        assert setup.log_path == log_path
        assert "plain-secret" not in contents
        assert "token=[secret]" in contents
    finally:
        shutdown_logging()


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    try:
        first = configure_logging(log_path=tmp_path / "one.log", force=True)
        handler_count = len(logging.getLogger().handlers)
        second = configure_logging(log_path=tmp_path / "two.log", force=False)

        assert first.configured
        assert not second.configured
        assert len(logging.getLogger().handlers) == handler_count
    finally:
        shutdown_logging()


