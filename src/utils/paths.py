"""Date-stamped path helpers."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from src.config import data_path


def today_str() -> str:
    return date.today().isoformat()


def excel_path(name: str, day: str | None = None) -> Path:
    day = day or today_str()
    return data_path("excel", f"{name}_{day}.xlsx")


def proposal_dir() -> Path:
    return data_path("proposals", ".keep").parent


def report_path(name: str, day: str | None = None, ext: str = "xlsx") -> Path:
    day = day or today_str()
    return data_path("reports", f"{name}_{day}.{ext}")
