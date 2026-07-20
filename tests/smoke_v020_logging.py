"""Smoke test for Fibi's local logging foundation."""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fibi.logging_config import configure_logging, shutdown_logging


def run() -> None:
    with tempfile.TemporaryDirectory() as temp:
        try:
            log_path = Path(temp) / "fibi.log"
            setup = configure_logging(level_name="INFO", log_path=log_path, force=True)
            assert setup.configured

            logging.getLogger("fibi.smoke").info("api_key=%s", "secret-value")
            for handler in logging.getLogger().handlers:
                handler.flush()

            contents = log_path.read_text(encoding="utf-8")
            assert "fibi.smoke" in contents
            assert "secret-value" not in contents
            assert "api_key=[secret]" in contents
        finally:
            shutdown_logging()

    print("Fibi v0.20 logging smoke tests passed.")


if __name__ == "__main__":
    run()


