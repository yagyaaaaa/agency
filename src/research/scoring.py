"""Lead scoring + package recommendation logic.

Score is 0–100. Recommendation per spec:
 - Pro is the default.
 - Enterprise for high-ticket businesses with strong lead potential.
 - Starter only for small/easy clients (never lead with this).
"""
from __future__ import annotations

HIGH_TICKET_INDUSTRIES = {"architects", "interior_designers", "builders", "clinics",
                         "premium_local_businesses", "dubai_foreign_service_businesses"}
MID_TICKET_INDUSTRIES = {"gyms_fitness_coaches", "coaching_institutes"}


def _norm_industry(industry: str | None) -> str:
    if not industry:
        return ""
    return industry.strip().lower().replace(" ", "_").replace("/", "_").replace("-", "_")


def score_lead(lead: dict) -> int:
    """Heuristic 0–100 score.

    Inputs we use (any may be missing):
      - website_quality_score (0–10) — lower = more upside = higher our score
      - email present
      - decision_maker present
      - industry in primary niches
      - city_country present
      - personalization_hook present
    """
    score = 0

    wq = lead.get("website_quality_score")
    try:
        wq = int(wq) if wq is not None and wq != "" else None
    except (TypeError, ValueError):
        wq = None
    if wq is not None:
        # 0..10; weaker site = bigger opportunity
        score += max(0, min(40, (10 - wq) * 4))

    industry = _norm_industry(lead.get("industry"))
    if industry in HIGH_TICKET_INDUSTRIES:
        score += 25
    elif industry in MID_TICKET_INDUSTRIES:
        score += 15

    if lead.get("email"):
        score += 10
    if lead.get("decision_maker"):
        score += 10
    if lead.get("personalization_hook"):
        score += 10
    if lead.get("city_country"):
        score += 5

    return max(0, min(100, score))


def recommend_package(lead: dict, score: int | None = None) -> str:
    """Returns 'pro' | 'enterprise' | 'starter'."""
    s = score if score is not None else score_lead(lead)
    industry = _norm_industry(lead.get("industry"))
    city = (lead.get("city_country") or "").lower()
    foreign = any(k in city for k in ("dubai", "uae", "abu dhabi", "doha", "riyadh", "singapore", "london", "usa", "united states"))

    if foreign and s >= 60:
        return "enterprise"
    if industry in HIGH_TICKET_INDUSTRIES and s >= 65:
        return "enterprise"
    if s >= 35:
        return "pro"
    return "starter"
