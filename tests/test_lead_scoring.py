from src.agents.package_recommendation import (
    FOREIGN_INFRA,
    INDIA_PRO,
    INDIA_STARTER,
    recommend_package,
)
from src.agents.scoring import score_lead


def test_score_lead_applies_all_requested_signals():
    lead = {
        "business_name": "Apex Villas",
        "industry": "premium architect",
        "city_country": "Dubai, UAE",
        "website": "",
        "email": "hello@apexvillas.ae",
        "instagram": "https://instagram.com/apexvillas",
        "automation_opportunity": "Weak lead capture and no follow-up after enquiry.",
        "personalization_hook": "Their villa portfolio is strong, but the enquiry path is buried below project visuals.",
    }

    scoring = score_lead(lead)

    assert scoring.score == 13
    assert "Dubai/foreign market" in scoring.reasons
    assert "strong personalization hook" in scoring.reasons


def test_recommend_package_uses_starter_only_for_small_easy_clients():
    lead = {
        "business_name": "Small Local Tutor",
        "industry": "small coaching institute",
        "city_country": "Mumbai, India",
        "website": "https://example.com",
        "website_quality_score": 8,
        "notes": "small easy starter scope low budget",
    }

    assert recommend_package(lead) == INDIA_STARTER


def test_recommend_package_defaults_viable_india_leads_to_pro():
    lead = {
        "business_name": "FitCore Studio",
        "industry": "gym fitness coach",
        "city_country": "Mumbai, India",
        "website": "https://fitcore.example",
        "email": "hello@fitcore.example",
        "instagram": "https://instagram.com/fitcore",
        "automation_opportunity": "Trial lead capture can sync to CRM.",
    }

    assert recommend_package(lead) == INDIA_PRO


def test_recommend_package_escalates_strong_foreign_leads():
    lead = {
        "business_name": "Dubai Prime Clinics",
        "industry": "premium clinic multi-service",
        "city_country": "Dubai, UAE",
        "website": "",
        "email": "growth@dubaiprime.example",
        "instagram": "https://instagram.com/dubaiprime",
        "automation_opportunity": "Weak booking capture and manual follow-up.",
        "personalization_hook": "The clinic has premium services, but the mobile booking path does not match the trust level.",
    }

    assert recommend_package(lead) == FOREIGN_INFRA
