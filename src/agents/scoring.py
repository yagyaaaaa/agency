"""Lead scoring for QuantumReach outbound prioritization."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from src.agents.lead_utils import (
    has_active_social_or_portfolio,
    has_clear_email,
    has_weak_lead_capture,
    is_foreign_market,
    is_high_ticket_industry,
    is_premium_service,
    normalize_lead,
)


@dataclass(frozen=True)
class LeadScore:
    score: int
    reasons: list[str]


def _website_is_bad_or_missing(lead: Mapping[str, object]) -> bool:
    website = str(lead.get("website") or "").strip()
    quality = lead.get("website_quality_score")
    if not website:
        return True
    try:
        return int(quality) <= 4
    except (TypeError, ValueError):
        return False


def _strong_personalization_hook(lead: Mapping[str, object]) -> bool:
    hook = str(lead.get("personalization_hook") or "").strip()
    generic = {"good website", "needs better website", "website improvement", "generic hook"}
    return len(hook) >= 35 and hook.lower() not in generic


def score_lead(raw_lead: Mapping[str, object]) -> LeadScore:
    """Score a lead using the operating rules from the agency playbook."""

    lead = normalize_lead(raw_lead)
    score = 0
    reasons: list[str] = []

    if _website_is_bad_or_missing(lead):
        score += 2
        reasons.append("bad/outdated or missing website")

    if is_premium_service(str(lead.get("industry") or ""), str(lead.get("notes") or "")):
        score += 2
        reasons.append("premium service business")

    if has_clear_email(str(lead.get("email") or "")):
        score += 1
        reasons.append("clear contact email")

    if is_high_ticket_industry(str(lead.get("industry") or ""), str(lead.get("notes") or "")):
        score += 2
        reasons.append("high-ticket industry")

    if has_active_social_or_portfolio(lead):
        score += 1
        reasons.append("active Instagram/portfolio signal")

    if has_weak_lead_capture(lead):
        score += 2
        reasons.append("weak lead capture or follow-up")

    if is_foreign_market(str(lead.get("city_country") or "")):
        score += 1
        reasons.append("Dubai/foreign market")

    if _strong_personalization_hook(lead):
        score += 2
        reasons.append("strong personalization hook")

    return LeadScore(score=score, reasons=reasons)
