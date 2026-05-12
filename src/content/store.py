"""Content & tool-research asset storage. Filesystem + index in SQLite."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.config import data_path
from src.db import cursor


def save_content_asset(kind: str, title: str, body: str, tags: str | None = None) -> int:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in title)[:60] or "asset"
    fp = data_path("content", f"{kind}_{safe}.md")
    fp.write_text(body, encoding="utf-8")
    with cursor() as cur:
        cur.execute(
            "INSERT INTO content_assets (kind, title, body, path, tags) VALUES (?, ?, ?, ?, ?)",
            (kind, title, body, str(fp), tags),
        )
        return cur.lastrowid or 0


def list_content(limit: int = 50) -> list[dict]:
    with cursor() as cur:
        return [dict(r) for r in cur.execute(
            "SELECT asset_id, kind, title, path, tags, created_at FROM content_assets "
            "ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()]


def save_tool_research(name: str, category: str, url: str | None, notes: str | None, rating: int | None = None) -> int:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO tool_research (name, category, url, notes, rating) VALUES (?, ?, ?, ?, ?)",
            (name, category, url, notes, rating),
        )
        return cur.lastrowid or 0


def list_tools(limit: int = 50) -> list[dict]:
    with cursor() as cur:
        return [dict(r) for r in cur.execute(
            "SELECT * FROM tool_research ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()]
