"""Adapters around core modules, with deterministic local fallbacks."""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Iterable, Mapping

from openpyxl import Workbook

from src.config import data_path
from src.utils.logger import get_logger

logger = get_logger("agents.integrations")


def _call_first(candidates: list[tuple[str, str]], *args, **kwargs):
    for module_name, function_name in candidates:
        try:
            module = importlib.import_module(module_name)
            fn = getattr(module, function_name)
        except (ImportError, AttributeError):
            continue
        return fn(*args, **kwargs)
    raise ImportError("no integration callable found")


def export_rows_to_excel(rows: Iterable[Mapping[str, object]], output_path: str | Path, sheet_name: str = "Sheet1") -> Path:
    """Export rows through the core exporter if present, else openpyxl."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    core_export_map = {
        "Leads": ("src.excel.exporter", "export_leads"),
        "Drafts": ("src.excel.exporter", "export_drafts"),
        "Followups": ("src.excel.exporter", "export_followups_due"),
        "Profit": ("src.excel.exporter", "export_profit"),
    }
    if sheet_name in core_export_map:
        module_name, function_name = core_export_map[sheet_name]
        try:
            module = importlib.import_module(module_name)
            exported = getattr(module, function_name)()
            return Path(exported)
        except Exception as exc:
            logger.warning("core Excel export failed for %s; using fallback: %s", sheet_name, exc)

    candidates = [
        ("src.excel_exporter", "export_rows"),
        ("src.exporter", "export_rows"),
        ("src.reports.excel_exporter", "export_rows"),
    ]
    try:
        _call_first(candidates, rows, path, sheet_name=sheet_name)
        return path
    except ImportError:
        pass

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31] or "Sheet1"
    headers: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in headers:
                headers.append(str(key))
    if headers:
        ws.append(headers)
        for row in rows:
            ws.append([row.get(header, "") for header in headers])
    else:
        ws.append(["empty"])
    wb.save(path)
    return path


def excel_output(name: str) -> Path:
    return data_path("excel", name)


def send_telegram_message(text: str, files: list[str | Path] | None = None, dry_run: bool = False) -> bool:
    """Send via existing Telegram module when available.

    This adapter never reads secrets directly. The Telegram implementation, if
    installed by the core backend, owns token access through environment vars.
    """

    if dry_run:
        logger.info("dry-run Telegram message length=%s files=%s", len(text), files or [])
        return False

    try:
        notify = importlib.import_module("src.telegram.notify")
        ok = bool(notify.send_message(text))
        for file_path in files or []:
            notify.send_document(file_path, caption=Path(file_path).name)
        return ok
    except Exception as exc:
        logger.warning("core Telegram notify failed or unavailable: %s", exc)

    candidates = [
        ("src.telegram_bot", "send_message"),
        ("src.telegram.bot", "send_message"),
        ("src.telegram.reporter", "send_message"),
        ("src.reporting.telegram", "send_message"),
    ]
    try:
        _call_first(candidates, text, files=files or [])
        return True
    except (ImportError, TypeError):
        logger.warning("Telegram module not found; digest not sent")
        return False


def generate_proposal_with_core(payload: Mapping[str, object]) -> Path | None:
    candidates = [
        ("src.proposal_generator", "generate_proposal"),
        ("src.proposals.generator", "generate_proposal"),
        ("src.proposal.generator", "generate_proposal"),
    ]
    try:
        out = _call_first(candidates, payload)
        return Path(out) if out else None
    except ImportError:
        return None
