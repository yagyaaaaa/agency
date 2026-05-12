"""Pytest fixtures. Each test gets an isolated SQLite DB in a temp dir."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """Point SQLITE_PATH + DATA_DIR at a per-test temp dir. Reset module caches."""
    db_dir = tmp_path / "db"
    data_dir = tmp_path
    db_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    (data_dir / "excel").mkdir(parents=True, exist_ok=True)
    (data_dir / "proposals").mkdir(parents=True, exist_ok=True)
    (data_dir / "content").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    (data_dir / "outreach").mkdir(parents=True, exist_ok=True)
    (data_dir / "exports").mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("SQLITE_PATH", str(db_dir / "agency.sqlite"))
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    # purge cached singletons
    for mod in list(sys.modules):
        if mod.startswith("src."):
            del sys.modules[mod]

    yield
