from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from file_browser.app import create_app


@pytest.fixture()
def file_tree(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    (root / "documents").mkdir(parents=True)
    (root / "documents" / "README.md").write_text("# Hello\n", encoding="utf-8")
    (root / "documents" / "notes.txt").write_text("notes", encoding="utf-8")
    (root / "image.png").write_bytes(b"\x89PNG\r\n")
    return root


@pytest.fixture()
def app(file_tree: Path):
    return create_app({"BASE_DIR": file_tree, "TESTING": True})


@pytest.fixture()
def client(app):
    return app.test_client()