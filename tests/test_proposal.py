from pathlib import Path


def test_generate_proposal_md_and_html():
    from src.db import init_db
    from src.proposal.generator import generate_proposal
    init_db()
    out = generate_proposal({
        "client_name": "Aurelia Architects",
        "industry": "architects",
        "package": "Pro",
        "add_ons": "WhatsApp lead capture",
        "timeline": "4 weeks",
        "price": 34999,
        "support_plan": "Standard monthly support",
        "notes": "Strong portfolio.",
    }, make_pdf=False)
    md = Path(out["md"]).read_text(encoding="utf-8")
    html = Path(out["html"]).read_text(encoding="utf-8")
    assert "Aurelia Architects" in md
    assert "50% advance" in md
    assert "<h1>" in html
    assert "Aurelia Architects" in html


def test_proposal_requires_client_name():
    import pytest
    from src.proposal.generator import generate_proposal
    with pytest.raises(ValueError):
        generate_proposal({"package": "pro"})
