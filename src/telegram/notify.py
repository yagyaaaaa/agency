"""Lightweight sync Telegram sender used by scheduled jobs.

Uses the raw Bot API via httpx — no python-telegram-bot dependency here,
so jobs don't need the asyncio event loop.

Never raises on auth/network failure; logs and returns False instead.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from src.config import CONFIG
from src.utils.logger import get_logger

log = get_logger("telegram.notify")

API = "https://api.telegram.org/bot{token}/{method}"


def _enabled() -> bool:
    return bool(CONFIG.telegram_token and CONFIG.telegram_chat_id)


def send_message(text: str, *, chat_id: str | None = None, parse_mode: str | None = "Markdown") -> bool:
    if not _enabled():
        log.warning("telegram not configured — message dropped")
        return False
    target = chat_id or CONFIG.telegram_chat_id
    url = API.format(token=CONFIG.telegram_token, method="sendMessage")
    payload = {"chat_id": target, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = httpx.post(url, json=payload, timeout=15.0)
        r.raise_for_status()
        return True
    except Exception as exc:
        log.error("send_message failed: %s", exc)
        return False


def send_document(path: str | Path, *, caption: str | None = None, chat_id: str | None = None) -> bool:
    if not _enabled():
        log.warning("telegram not configured — document dropped (%s)", path)
        return False
    p = Path(path)
    if not p.exists():
        log.error("send_document: file missing: %s", p)
        return False
    target = chat_id or CONFIG.telegram_chat_id
    url = API.format(token=CONFIG.telegram_token, method="sendDocument")
    try:
        with p.open("rb") as f:
            files = {"document": (p.name, f)}
            data = {"chat_id": target}
            if caption:
                data["caption"] = caption[:1024]
            r = httpx.post(url, data=data, files=files, timeout=60.0)
            r.raise_for_status()
        return True
    except Exception as exc:
        log.error("send_document failed: %s", exc)
        return False
