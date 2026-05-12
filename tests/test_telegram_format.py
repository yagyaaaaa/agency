def test_daily_brief_renders():
    from src.telegram.formatting import fmt_daily_brief
    out = fmt_daily_brief(
        day="2026-05-12",
        lead_counts={"new": 3, "contacted": 1},
        top_leads=[{"lead_score": 80, "business_name": "Acme", "industry": "architects", "city_country": "Pune"}],
        drafts_pending=2, followups_due=1,
        profit={"revenue_booked": 100000, "cash_collected": 50000, "pending_invoices": 50000, "net_profit_estimate": 30000},
    )
    assert "Daily Brief" in out
    assert "Acme" in out
    assert "₹1,00,000" in out or "₹100,000" in out  # locale-tolerant


def test_help_lists_all_commands():
    from src.telegram.formatting import fmt_help
    out = fmt_help()
    for cmd in ("/status", "/today", "/leads", "/hot", "/drafts",
                "/approve_today", "/reject_lead", "/pipeline",
                "/profit", "/content", "/tools", "/proposal", "/help"):
        assert cmd in out


def test_fmt_hot_empty():
    from src.telegram.formatting import fmt_hot_leads
    assert "No hot leads" in fmt_hot_leads([])
