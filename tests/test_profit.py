def test_profit_summary():
    from src.db import init_db
    from src.profit.tracker import record_revenue, record_expense, compute_summary
    init_db()
    record_revenue({
        "client": "Acme", "package": "pro",
        "amount_booked": 34999, "amount_collected": 17500,
        "payment_method": "upi", "payment_status": "partial",
        "commission_due": 0,
    })
    record_expense({"category": "vps", "vendor": "DigitalOcean", "amount": 800, "payment_method": "card"})
    s = compute_summary()
    assert s["revenue_booked"] == 34999
    assert s["cash_collected"] == 17500
    assert s["pending_invoices"] == 34999 - 17500
    assert s["expenses_total"] == 800
    # net estimate should be collected - commission - 5% fee, then minus expenses
    assert s["net_profit_estimate"] < s["cash_collected"]


def test_profit_zero_state():
    from src.db import init_db
    from src.profit.tracker import compute_summary
    init_db()
    s = compute_summary()
    assert s["revenue_booked"] == 0
    assert s["net_profit_estimate"] == 0
