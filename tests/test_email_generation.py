from src.agents.cold_email import render_followups, render_initial_email


def test_initial_email_uses_india_template_and_opt_out():
    lead = {
        "business_name": "Vision Studio",
        "industry": "architect",
        "city_country": "Mumbai, India",
        "decision_maker": "Rohan Mehta",
        "personalization_hook": "The portfolio is strong, but enquiry CTA placement can be clearer on mobile.",
    }

    draft = render_initial_email(lead)

    assert draft["subject"] == "Quick idea for Vision Studio"
    assert "Hi Rohan," in draft["email_body"]
    assert "Reply \"no\" and I won't follow up." in draft["email_body"]
    assert "send" not in draft["subject"].lower()


def test_initial_email_uses_foreign_variant():
    lead = {
        "business_name": "Palm Interiors",
        "industry": "interior designers",
        "city_country": "Dubai, UAE",
        "decision_maker": "",
        "personalization_hook": "Project pages could lead into WhatsApp enquiry faster.",
    }

    draft = render_initial_email(lead)

    assert draft["subject"] == "Website + lead system idea for Palm Interiors"
    assert "Hi there," in draft["email_body"]
    assert "AI-powered lead systems" in draft["email_body"]


def test_followups_keep_manual_outreach_tone():
    lead = {
        "business_name": "Prime Dental",
        "decision_maker": "Aisha Khan",
        "personalization_hook": "Booking intent is present, but the patient path has too many steps.",
    }

    followup_1, followup_2 = render_followups(lead, "Quick idea for Prime Dental")

    assert "Reply \"no\"" in followup_1
    assert "Last note from my side" in followup_2
    assert "Aisha" in followup_1
