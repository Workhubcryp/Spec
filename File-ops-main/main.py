"""Workspace entry point for running the Python File Browser MVP."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
FILE_BROWSER_ROOT = PROJECT_ROOT / "file-browser"
sys.path.insert(0, str(FILE_BROWSER_ROOT))

from file_browser.app import create_app
from file_browser.config import load_config


def main() -> None:
    os.environ.setdefault(
        "FILE_BROWSER_BASE_DIR",
        str(FILE_BROWSER_ROOT / "sample-data"),
    )
    config = load_config()
    app = create_app()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


if __name__ == "__main__":
    main()
