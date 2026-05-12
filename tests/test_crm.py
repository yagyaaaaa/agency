def test_insert_and_get_lead():
    from src.db import init_db
    from src.crm.leads import insert_lead, get_lead
    init_db()
    lid = insert_lead({"business_name": "Acme Studio", "email": "x@acme.example", "industry": "architects"})
    assert lid > 0
    got = get_lead(lid)
    assert got["business_name"] == "Acme Studio"
    assert got["email"] == "x@acme.example"


def test_upsert_updates_existing():
    from src.db import init_db
    from src.crm.leads import upsert_lead
    init_db()
    a, action_a = upsert_lead({"business_name": "Acme Studio", "email": "x@acme.example", "industry": "architects"})
    assert action_a == "inserted"
    b, action_b = upsert_lead({"business_name": "Acme Studio", "email": "x@acme.example", "industry": "architects", "city_country": "Pune, India"})
    assert action_b == "updated"
    assert b == a

    from src.crm.leads import get_lead
    assert get_lead(a)["city_country"] == "Pune, India"


def test_status_changes():
    from src.db import init_db
    from src.crm.leads import insert_lead, set_status, get_lead
    init_db()
    lid = insert_lead({"business_name": "S1"})
    set_status(lid, "rejected", note="not a fit")
    assert get_lead(lid)["status"] == "rejected"
    assert "not a fit" in (get_lead(lid)["notes"] or "")
