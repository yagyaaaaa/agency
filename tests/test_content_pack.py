from src.agents.content import build_content_pack


def test_content_pack_contains_required_daily_assets():
    pack = build_content_pack("2026-05-12")

    assert "## LinkedIn/X Post" in pack
    assert "## Instagram Carousel Outline" in pack
    assert "## Cold DM Variant" in pack
    assert "## Case-Study Style Post" in pack
    assert "## Website Teardown Idea" in pack
    assert "fake guru" not in pack.lower()
