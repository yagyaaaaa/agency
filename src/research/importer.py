"""Manual CSV/XLSX lead importer. Codex will later wire up real research agents."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import openpyxl

from src.crm.leads import DuplicateLead, insert_lead, upsert_lead
from src.research.scoring import recommend_package, score_lead
from src.utils.logger import get_logger

log = get_logger("research.importer")

EXPECTED_FIELDS = [
    "business_name", "industry", "city_country", "website", "email", "phone",
    "instagram", "linkedin", "decision_maker", "source_url",
    "website_quality_score", "automation_opportunity", "personalization_hook",
    "recommended_package", "notes",
]


def _enrich(row: dict[str, Any]) -> dict[str, Any]:
    row.setdefault("status", "new")
    s = score_lead(row)
    row["lead_score"] = s
    if not row.get("recommended_package"):
        row["recommended_package"] = recommend_package(row, s)
    return row


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def _load_xlsx(path: Path) -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(filename=str(path), data_only=True, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    out = []
    for r in rows[1:]:
        if r is None or all(c in (None, "") for c in r):
            continue
        out.append({headers[i]: r[i] for i in range(len(headers)) if headers[i]})
    return out


def import_leads_file(path: str | Path, *, mode: str = "upsert") -> dict[str, int]:
    """Import leads from .csv or .xlsx.

    mode: 'insert' raises on duplicates, 'upsert' updates them, 'skip' silently skips duplicates.
    Returns counters: {inserted, updated, skipped, suppressed, errors}.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    if p.suffix.lower() == ".csv":
        raw = _load_csv(p)
    elif p.suffix.lower() in (".xlsx", ".xlsm"):
        raw = _load_xlsx(p)
    else:
        raise ValueError(f"Unsupported file type: {p.suffix}")

    counters = {"inserted": 0, "updated": 0, "skipped": 0, "suppressed": 0, "errors": 0}
    for raw_row in raw:
        row = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items() if k in EXPECTED_FIELDS or k == "business_name"}
        if not row.get("business_name"):
            counters["errors"] += 1
            continue
        row = _enrich(row)
        try:
            if mode == "upsert":
                _id, action = upsert_lead(row)
                if action == "suppressed":
                    counters["suppressed"] += 1
                else:
                    counters[action] += 1
            elif mode == "insert":
                new_id = insert_lead(row)
                if new_id == 0:
                    counters["suppressed"] += 1
                else:
                    counters["inserted"] += 1
            else:  # skip
                try:
                    new_id = insert_lead(row)
                    if new_id == 0:
                        counters["suppressed"] += 1
                    else:
                        counters["inserted"] += 1
                except DuplicateLead:
                    counters["skipped"] += 1
        except DuplicateLead:
            counters["skipped"] += 1
        except Exception as exc:
            log.exception("import row failed: %s", exc)
            counters["errors"] += 1
    log.info("import done: %s", counters)
    return counters
