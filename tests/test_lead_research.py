import json

import httpx


FAKE_MAPS_RESULTS = [
    {
        "title": "Asterline Architects",
        "website": "https://asterline-architects.example",
        "email": "hello@asterline-architects.example",
        "phone": "+91 90000 10001",
        "place_id_search": "https://maps.example/asterline",
    },
    {
        "title": "CasaGrid Interiors",
        "website": "https://casagrid-interiors.example",
        "email": "studio@casagrid-interiors.example",
        "phone": "+91 90000 10002",
        "place_id_search": "https://maps.example/casagrid",
    },
    {
        "title": "NoEmail Dental Studio",
        "website": "https://noemail-dental.example",
        "email": "",
        "phone": "+91 90000 10003",
        "place_id_search": "https://maps.example/noemail",
    },
    {
        "title": "Suppressed Fitness Lab",
        "website": "https://suppressed-fitness.example",
        "email": "owner@suppressed-fitness.example",
        "phone": "+91 90000 10004",
        "place_id_search": "https://maps.example/suppressed",
    },
    {
        "title": "Palm District Builders",
        "website": "https://palm-district-builders.example",
        "email": "sales@palm-district-builders.example",
        "phone": "+971 50 000 1005",
        "place_id_search": "https://maps.example/palm",
    },
]


def write_research_config(tmp_path, *, cap=30):
    path = tmp_path / "research_targets.yaml"
    path.write_text(
        f"""
niches:
  - id: architects
    cities: [Pune, Mumbai, Bengaluru, Delhi]
    daily_quota: 8
  - id: builders
    cities: [Dubai, Abu Dhabi]
    daily_quota: 4
market_split:
  india_share_pct: 80
  foreign_share_pct: 20
global_daily_cap: {cap}
""",
        encoding="utf-8",
    )
    return path


def make_serpapi_client(calls):
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"local_results": FAKE_MAPS_RESULTS})

    return httpx.Client(transport=httpx.MockTransport(handler))


def count_leads():
    from src.db import cursor

    with cursor() as cur:
        return cur.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]


def test_round_robin_honors_india_foreign_split(tmp_path):
    from src.agents.lead_research import LeadResearchAgent

    config_path = write_research_config(tmp_path, cap=10)
    agent = LeadResearchAgent(config_path=config_path)

    pairs = agent.build_search_pairs(day="2026-05-12", max_pairs=10)

    assert len(pairs) == 10
    assert sum(pair.market == "india" for pair in pairs) == 8
    assert sum(pair.market == "foreign" for pair in pairs) == 2


def test_provider_run_upserts_dedupes_and_respects_suppression(tmp_path, monkeypatch):
    from src.agents.lead_research import LeadResearchAgent
    from src.crm.leads import upsert_lead
    from src.crm.suppression import add_suppression
    from src.db import init_db

    init_db()
    upsert_lead(
        {
            "business_name": "Asterline Architects",
            "email": "hello@asterline-architects.example",
            "website": "https://asterline-architects.example",
        }
    )
    add_suppression(email="owner@suppressed-fitness.example", reason="test")
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    monkeypatch.setenv("MAX_RESEARCH_QUERIES_PER_DAY", "80")
    calls = []

    result = LeadResearchAgent(
        http_client=make_serpapi_client(calls),
        config_path=write_research_config(tmp_path, cap=4),
    ).run(day="2026-05-12")

    stats = result.data["stats"]
    assert len(calls) == 1
    assert stats["inserted"] == 3
    assert stats["updated"] == 1
    assert stats["suppressed"] == 1
    assert count_leads() == 4


def test_global_daily_cap_stops_candidate_processing(tmp_path, monkeypatch):
    from src.agents.lead_research import LeadResearchAgent
    from src.db import init_db

    init_db()
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    calls = []

    result = LeadResearchAgent(
        http_client=make_serpapi_client(calls),
        config_path=write_research_config(tmp_path, cap=2),
    ).run(day="2026-05-12")

    stats = result.data["stats"]
    assert len(calls) == 1
    assert stats["inserted"] == 2
    assert count_leads() == 2


def test_budget_guard_blocks_extra_http_calls(tmp_path, monkeypatch):
    from src.agents import lead_research as lr

    lr._ensure_research_schema()
    with lr.db.cursor() as cur:
        for i in range(2):
            cur.execute(
                "INSERT INTO research_query_usage (run_date, niche_id, city, market, query, provider) VALUES (?, ?, ?, ?, ?, ?)",
                ("2026-05-12", "architects", "Pune", "india", f"q{i}", "serpapi"),
            )
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    monkeypatch.setenv("MAX_RESEARCH_QUERIES_PER_DAY", "2")
    calls = []

    result = lr.LeadResearchAgent(
        http_client=make_serpapi_client(calls),
        config_path=write_research_config(tmp_path),
    ).run(day="2026-05-12")

    assert len(calls) == 0
    assert result.data["stats"]["queries"] == 0
    assert "queries=0" in result.message


def test_dry_run_uses_fixtures_without_http(tmp_path, monkeypatch):
    from src.agents.lead_research import LeadResearchAgent

    fixtures_path = tmp_path / "research_fixtures.json"
    fixtures_path.write_text(json.dumps({"businesses": FAKE_MAPS_RESULTS}), encoding="utf-8")

    def handler(request):
        raise AssertionError("dry-run should not call HTTP")

    monkeypatch.setenv("RESEARCH_DRY_RUN", "1")
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")

    result = LeadResearchAgent(
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        config_path=write_research_config(tmp_path),
        fixtures_path=fixtures_path,
    ).run(day="2026-05-12")

    assert result.count == 5
    assert result.data["stats"]["queries"] == 0


def test_live_run_writes_job_log_summary(tmp_path, monkeypatch):
    from src.agents.lead_research import LeadResearchAgent
    from src.db import init_db

    init_db()
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    calls = []

    result = LeadResearchAgent(
        http_client=make_serpapi_client(calls),
        config_path=write_research_config(tmp_path, cap=1),
    ).run(day="2026-05-12")

    log_text = open(result.outputs["run_log"], encoding="utf-8").read()
    assert "queries=1" in result.message
    assert "cost_est=$" in result.message
    assert "mode=live" in log_text
