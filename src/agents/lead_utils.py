"""Lead normalization and classification helpers."""
from __future__ import annotations

from typing import Mapping

from src.utils.dedupe import domain_from_email, domain_from_url, norm_business, norm_email

LEAD_FIELDS = [
    "lead_id",
    "business_name",
    "industry",
    "city_country",
    "website",
    "email",
    "phone",
    "instagram",
    "linkedin",
    "decision_maker",
    "source_url",
    "website_quality_score",
    "automation_opportunity",
    "personalization_hook",
    "recommended_package",
    "lead_score",
    "status",
    "notes",
]

FOREIGN_MARKET_HINTS = {
    "dubai",
    "uae",
    "united arab emirates",
    "abu dhabi",
    "sharjah",
    "singapore",
    "london",
    "uk",
    "usa",
    "canada",
    "australia",
    "foreign",
}

INDIA_MARKET_HINTS = {
    "india",
    "mumbai",
    "delhi",
    "bengaluru",
    "bangalore",
    "pune",
    "hyderabad",
    "ahmedabad",
    "chennai",
    "kolkata",
    "thane",
    "navi mumbai",
    "borivali",
}

HIGH_TICKET_HINTS = {
    "architect",
    "interior",
    "builder",
    "real estate",
    "developer",
    "clinic",
    "dental",
    "cosmetic",
    "dermatology",
    "luxury",
    "premium",
    "villa",
    "construction",
}

PREMIUM_SERVICE_HINTS = HIGH_TICKET_HINTS | {
    "gym",
    "fitness",
    "coach",
    "coaching",
    "institute",
    "studio",
    "consultant",
}

SMALL_EASY_HINTS = {
    "small",
    "solo",
    "basic",
    "easy",
    "single location",
    "starter",
    "low budget",
}

WEAK_CAPTURE_HINTS = {
    "weak",
    "missing",
    "none",
    "manual",
    "slow",
    "no form",
    "no enquiry",
    "no follow",
    "follow-up",
    "followup",
    "whatsapp",
    "lead capture",
    "booking",
}


def text_blob(lead: Mapping[str, object], *fields: str) -> str:
    return " ".join(str(lead.get(field) or "") for field in fields).lower()


def normalize_lead(raw: Mapping[str, object]) -> dict[str, object]:
    lead = {field: raw.get(field, "") for field in LEAD_FIELDS}
    lead["business_name"] = str(lead.get("business_name") or "").strip()
    lead["industry"] = str(lead.get("industry") or "").strip()
    lead["city_country"] = str(lead.get("city_country") or "").strip()
    lead["email"] = norm_email(str(lead.get("email") or ""))
    lead["website"] = str(lead.get("website") or "").strip()
    lead["status"] = str(lead.get("status") or "new").strip() or "new"
    try:
        if lead.get("website_quality_score") in ("", None):
            lead["website_quality_score"] = None
        else:
            lead["website_quality_score"] = int(float(str(lead.get("website_quality_score"))))
    except (TypeError, ValueError):
        lead["website_quality_score"] = None
    try:
        lead["lead_score"] = int(float(str(lead.get("lead_score") or 0)))
    except (TypeError, ValueError):
        lead["lead_score"] = 0
    return lead


def is_foreign_market(city_country: str | None) -> bool:
    text = (city_country or "").lower()
    if any(hint in text for hint in FOREIGN_MARKET_HINTS):
        return True
    if any(hint in text for hint in INDIA_MARKET_HINTS):
        return False
    parts = [part.strip() for part in text.split(",") if part.strip()]
    return len(parts) >= 2 and parts[-1] not in {"india", "in"}


def is_high_ticket_industry(industry: str | None, notes: str | None = None) -> bool:
    text = f"{industry or ''} {notes or ''}".lower()
    return any(hint in text for hint in HIGH_TICKET_HINTS)


def is_premium_service(industry: str | None, notes: str | None = None) -> bool:
    text = f"{industry or ''} {notes or ''}".lower()
    return any(hint in text for hint in PREMIUM_SERVICE_HINTS)


def is_small_easy_client(lead: Mapping[str, object]) -> bool:
    text = text_blob(lead, "industry", "automation_opportunity", "notes", "personalization_hook")
    return any(hint in text for hint in SMALL_EASY_HINTS)


def has_weak_lead_capture(lead: Mapping[str, object]) -> bool:
    text = text_blob(lead, "automation_opportunity", "notes", "personalization_hook")
    return any(hint in text for hint in WEAK_CAPTURE_HINTS)


def has_active_social_or_portfolio(lead: Mapping[str, object]) -> bool:
    if lead.get("instagram") or lead.get("linkedin"):
        return True
    text = text_blob(lead, "website", "source_url", "notes")
    return "portfolio" in text or "behance" in text or "dribbble" in text


def has_clear_email(email: str | None) -> bool:
    email = norm_email(email)
    return bool(email and "@" in email and "." in domain_from_email(email))


def first_name(decision_maker: str | None) -> str:
    raw = (decision_maker or "").strip()
    if not raw:
        return "there"
    first = raw.replace(",", " ").split()[0].strip()
    return first or "there"


def lead_domain(lead: Mapping[str, object]) -> str:
    return domain_from_email(str(lead.get("email") or "")) or domain_from_url(str(lead.get("website") or ""))


def normalized_business(lead: Mapping[str, object]) -> str:
    return norm_business(str(lead.get("business_name") or ""))
