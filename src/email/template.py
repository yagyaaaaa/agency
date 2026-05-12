"""Cold email template rendering (no live sending — drafts only)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import CONFIG

DEFAULT_TEMPLATE_PATH = Path("configs/email_template.txt")


def _first_name(decision_maker: str | None) -> str:
    if not decision_maker:
        return "there"
    parts = decision_maker.strip().split()
    if not parts:
        return "there"
    # strip common honorifics
    if parts[0].lower().rstrip(".") in {"mr", "mrs", "ms", "dr", "miss"}:
        parts = parts[1:] or parts
    return parts[0] if parts else "there"


def render_cold_email(lead: dict, *, template_path: Path | None = None) -> dict:
    """Return dict with subject + body (and follow-up drafts).

    Lead expected keys: business_name, industry, city_country, decision_maker,
    personalization_hook (used as personalized_observation).
    """
    tpl_path = template_path or DEFAULT_TEMPLATE_PATH
    raw = tpl_path.read_text(encoding="utf-8")
    subject_line, _, body_template = raw.partition("\n")
    subject_text = subject_line.replace("Subject:", "").strip()

    fields = {
        "business_name": lead.get("business_name") or "your business",
        "first_name": _first_name(lead.get("decision_maker")),
        "industry": (lead.get("industry") or "service").replace("_", " "),
        "city_country": lead.get("city_country") or "your city",
        "personalized_observation": lead.get("personalization_hook")
            or "the homepage could lead with a clear enquiry CTA and trust signals",
    }

    def render(text: str) -> str:
        for k, v in fields.items():
            text = text.replace("{{" + k + "}}", str(v))
        return text

    subject = render(subject_text)
    body = render(body_template).lstrip("\n")

    f1 = render_followup_1(lead, fields)
    f2 = render_followup_2(lead, fields)
    f1_due = (datetime.now(timezone.utc) + timedelta(days=3)).date().isoformat()
    f2_due = (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()

    return {
        "subject": subject,
        "body": body,
        "personalization_reason": fields["personalized_observation"],
        "followup_1_body": f1,
        "followup_1_date": f1_due,
        "followup_2_body": f2,
        "followup_2_date": f2_due,
    }


def render_followup_1(lead: dict, fields: dict) -> str:
    return (
        f"Hi {fields['first_name']},\n\n"
        f"Following up on my note about {fields['business_name']}. "
        "Happy to send over the quick 2–3 point teardown if useful — "
        "no pressure either way.\n\n"
        "Best,\nYagya\nQuantumReach"
    )


def render_followup_2(lead: dict, fields: dict) -> str:
    return (
        f"Hi {fields['first_name']},\n\n"
        "Last one from me. If the timing isn't right, all good — "
        "I'll close this out on my side. If it is, just reply with a quick 'send it' "
        "and I'll share the teardown.\n\n"
        f"Either way, wishing {fields['business_name']} a strong quarter.\n\n"
        "Best,\nYagya"
    )
