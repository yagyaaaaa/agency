"""Package recommendation rules."""
from __future__ import annotations

from typing import Mapping

from src.agents.lead_utils import (
    has_weak_lead_capture,
    is_foreign_market,
    is_high_ticket_industry,
    is_small_easy_client,
    normalize_lead,
    text_blob,
)
from src.agents.scoring import score_lead

INDIA_STARTER = "Starter (INR 14,999 + INR 3,499/mo)"
INDIA_PRO = "Pro (INR 34,999 + INR 5,999/mo)"
INDIA_ENTERPRISE = "Enterprise (INR 79,999+ + INR 9,999/mo)"

FOREIGN_LAUNCH = "Launch Website ($499-$799)"
FOREIGN_GROWTH = "Growth Website + Automation ($1,200-$2,500)"
FOREIGN_INFRA = "AI Growth Infrastructure ($3,000-$7,500)"


def _score(lead: Mapping[str, object]) -> int:
    try:
        existing = int(lead.get("lead_score") or 0)
    except (TypeError, ValueError):
        existing = 0
    return existing or score_lead(lead).score


def _enterprise_signal(lead: Mapping[str, object], score: int) -> bool:
    text = text_blob(lead, "industry", "business_name", "notes", "automation_opportunity")
    if any(hint in text for hint in ("builder", "developer", "multi-service", "multi location", "luxury", "premium clinic")):
        return True
    if "architect" in text and score >= 8:
        return True
    if is_high_ticket_industry(str(lead.get("industry") or ""), str(lead.get("notes") or "")) and score >= 9:
        return True
    return score >= 10


def recommend_package(raw_lead: Mapping[str, object]) -> str:
    lead = normalize_lead(raw_lead)
    score = _score(lead)

    if is_foreign_market(str(lead.get("city_country") or "")):
        if _enterprise_signal(lead, score) or score >= 10:
            return FOREIGN_INFRA
        if score >= 6 or has_weak_lead_capture(lead):
            return FOREIGN_GROWTH
        return FOREIGN_LAUNCH

    if _enterprise_signal(lead, score):
        return INDIA_ENTERPRISE

    if score <= 4 and is_small_easy_client(lead):
        return INDIA_STARTER

    return INDIA_PRO
