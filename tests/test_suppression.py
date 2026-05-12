def test_suppression_blocks_insert_and_draft():
    from src.db import init_db
    from src.crm.suppression import add_suppression, is_suppressed
    from src.crm.leads import insert_lead
    init_db()
    add_suppression(email="block@example.com", reason="unsub")
    assert is_suppressed(email="BLOCK@example.com")
    new_id = insert_lead({"business_name": "Blocked Co", "email": "block@example.com"})
    assert new_id == 0


def test_suppression_by_domain_and_business():
    from src.db import init_db
    from src.crm.suppression import add_suppression, is_suppressed
    init_db()
    add_suppression(domain="competitor.com")
    add_suppression(business_name="Do Not Contact LLP")
    assert is_suppressed(website="https://competitor.com/about")
    assert is_suppressed(business_name="do not contact")
