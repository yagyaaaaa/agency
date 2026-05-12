"""Seed sample leads for first-run / dry-run demos."""
from __future__ import annotations

from src.crm.leads import upsert_lead
from src.research.scoring import recommend_package, score_lead
from src.utils.logger import get_logger

log = get_logger("research.seed")

SAMPLES = [
    {
        "business_name": "Studio Anvaya Architects",
        "industry": "architects",
        "city_country": "Pune, India",
        "website": "studioanvaya.example.in",
        "email": "hello@studioanvaya.example.in",
        "decision_maker": "Principal Architect",
        "source_url": "https://example.com/listing/anvaya",
        "website_quality_score": 5,
        "automation_opportunity": "No enquiry capture, no follow-up",
        "personalization_hook": "Strong portfolio photography but the project pages have no CTA",
        "notes": "Pune-based, mid-size firm",
    },
    {
        "business_name": "FitForge Strength Studio",
        "industry": "gyms_fitness_coaches",
        "city_country": "Bengaluru, India",
        "website": "fitforge.example.in",
        "email": "owner@fitforge.example.in",
        "decision_maker": "Founder/Head Coach",
        "source_url": "https://example.com/listing/fitforge",
        "website_quality_score": 4,
        "automation_opportunity": "Trial signup is a static form with no auto-followup",
        "personalization_hook": "Trial signup form looks abandoned — add WhatsApp + 2-step nudge",
        "notes": "High intent traffic from Instagram",
    },
    {
        "business_name": "Marble & Light Interiors",
        "industry": "interior_designers",
        "city_country": "Mumbai, India",
        "website": "marbleandlight.example.in",
        "email": "studio@marbleandlight.example.in",
        "decision_maker": "Co-founder",
        "source_url": "https://example.com/listing/ml",
        "website_quality_score": 6,
        "automation_opportunity": "Visuals are great, enquiry path is buried",
        "personalization_hook": "Project gallery is gorgeous but enquiry is 4 clicks deep",
        "notes": "",
    },
    {
        "business_name": "Greenleaf Multispecialty Clinic",
        "industry": "clinics",
        "city_country": "Hyderabad, India",
        "website": "greenleafclinic.example.in",
        "email": "frontdesk@greenleafclinic.example.in",
        "decision_maker": "Clinic Admin",
        "source_url": "https://example.com/listing/greenleaf",
        "website_quality_score": 3,
        "automation_opportunity": "Booking by phone only, no WhatsApp",
        "personalization_hook": "Patients want booking in two taps — add WhatsApp + reminders",
        "notes": "Multi-doctor practice",
    },
    {
        "business_name": "Sahara Premium Property Group",
        "industry": "builders",
        "city_country": "Dubai, UAE",
        "website": "saharapremium.example.ae",
        "email": "sales@saharapremium.example.ae",
        "decision_maker": "Sales Director",
        "source_url": "https://example.com/listing/sahara",
        "website_quality_score": 5,
        "automation_opportunity": "No automated enquiry distribution to brokers",
        "personalization_hook": "Trust signals + project status timeline would lift enquiries",
        "notes": "Dubai market — foreign pricing applies",
    },
]


def seed() -> int:
    n = 0
    for s in SAMPLES:
        s["lead_score"] = score_lead(s)
        s["recommended_package"] = recommend_package(s, s["lead_score"])
        s["status"] = "new"
        _id, action = upsert_lead(s)
        log.info("seed %s -> %s (id=%s)", s["business_name"], action, _id)
        if action == "inserted":
            n += 1
    return n


if __name__ == "__main__":
    from src.db import init_db
    init_db()
    n = seed()
    print(f"seeded {n} new leads")
