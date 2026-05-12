import pytest


def test_dedupe_by_email():
    from src.db import init_db
    from src.crm.leads import insert_lead, DuplicateLead
    init_db()
    insert_lead({"business_name": "One", "email": "same@example.com"})
    with pytest.raises(DuplicateLead) as exc:
        insert_lead({"business_name": "Different Name", "email": "SAME@example.com"})
    assert exc.value.reason == "email"


def test_dedupe_by_domain():
    from src.db import init_db
    from src.crm.leads import insert_lead, DuplicateLead
    init_db()
    insert_lead({"business_name": "One", "website": "https://acme.example.in/about"})
    with pytest.raises(DuplicateLead) as exc:
        insert_lead({"business_name": "Acme Studio", "website": "acme.example.in"})
    assert exc.value.reason == "domain"


def test_dedupe_by_business_name():
    from src.db import init_db
    from src.crm.leads import insert_lead, DuplicateLead
    init_db()
    insert_lead({"business_name": "Studio Anvaya Architects Pvt Ltd"})
    with pytest.raises(DuplicateLead) as exc:
        insert_lead({"business_name": "studio  anvaya architects"})
    assert exc.value.reason == "business_name"


def test_dedupe_normalizers():
    from src.utils.dedupe import domain_from_email, domain_from_url, norm_business
    assert domain_from_email("X@Foo.COM") == "foo.com"
    assert domain_from_url("https://www.foo.com/path") == "foo.com"
    assert norm_business("FooBar Studios LLP") == "foobar"
