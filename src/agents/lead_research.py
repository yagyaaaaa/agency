"""Lead research sourcing, scoring, budget guarding, and CRM upsert."""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import quote_plus

import httpx
import yaml

from src import db
from src.agents.base import AgentResult, BaseAgent
from src.agents.integrations import excel_output, export_rows_to_excel
from src.agents.lead_utils import is_foreign_market, normalize_lead
from src.agents.package_recommendation import recommend_package
from src.agents.scoring import score_lead
from src.config import data_path
from src.crm.leads import upsert_lead
from src.utils.dedupe import domain_from_url, norm_business, norm_email


DEFAULT_CONFIG_PATH = Path("configs/research_targets.yaml")
DEFAULT_FIXTURES_PATH = Path("data/seed/research_fixtures.json")
DEFAULT_MAX_RESEARCH_QUERIES_PER_DAY = 80
DEFAULT_SERPAPI_COST_ESTIMATE = 0.005
DEFAULT_APIFY_COST_ESTIMATE = 0.01

FOREIGN_CITY_HINTS = {
    "dubai",
    "abu dhabi",
    "sharjah",
    "doha",
    "riyadh",
    "singapore",
    "london",
    "new york",
    "toronto",
}

NICHE_SEARCH_LABELS = {
    "architects": "architects",
    "interior_designers": "interior designers",
    "builders": "builders",
    "clinics": "premium clinics",
    "gyms_fitness_coaches": "gyms fitness coaches",
    "coaching_institutes": "coaching institutes",
    "premium_local_businesses": "premium local businesses",
    "dubai_foreign_service_businesses": "premium service businesses",
}

NICHE_HOOKS = {
    "architects": "The portfolio can convert better with sharper project proof and a clearer enquiry path.",
    "interior_designers": "The visual work deserves a premium mobile flow with faster WhatsApp enquiry capture.",
    "builders": "Project trust signals, inventory status, and WhatsApp lead capture can be tightened.",
    "clinics": "Booking intent can be captured faster with clearer proof, CTA placement, and reminders.",
    "gyms_fitness_coaches": "Trial enquiries can be captured and followed up before leads go cold.",
    "coaching_institutes": "Demo class enquiries can sync into a simple CRM with reminder follow-up.",
    "premium_local_businesses": "The site can work harder as a lead system instead of just a brochure.",
    "dubai_foreign_service_businesses": "Credibility and enquiry flow can be localized for a higher-value foreign market.",
}


@dataclass(frozen=True)
class ResearchTarget:
    niche_id: str
    cities: list[str]
    daily_quota: int


@dataclass(frozen=True)
class ResearchConfig:
    targets: list[ResearchTarget]
    india_share_pct: int = 80
    foreign_share_pct: int = 20
    global_daily_cap: int = 30


@dataclass(frozen=True)
class SearchPair:
    niche_id: str
    city: str
    market: str
    query: str


@dataclass
class LeadResearchStats:
    queries: int = 0
    candidates_returned: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    suppressed: int = 0
    cost_estimate: float = 0.0
    providers_used: set[str] = field(default_factory=set)
    query_lines: list[str] = field(default_factory=list)

    @property
    def accepted(self) -> int:
        return self.inserted + self.updated

    def as_dict(self) -> dict[str, object]:
        return {
            "queries": self.queries,
            "candidates_returned": self.candidates_returned,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "suppressed": self.suppressed,
            "cost_estimate": round(self.cost_estimate, 4),
            "providers_used": sorted(self.providers_used),
        }

    def summary(self) -> str:
        return (
            f"queries={self.queries}, inserted={self.inserted}, updated={self.updated}, "
            f"skipped={self.skipped}, suppressed={self.suppressed}, "
            f"cost_est=${self.cost_estimate:.2f}"
        )


class ResearchProviderError(RuntimeError):
    pass


class SerpApiMapsProvider:
    name = "serpapi"
    cost_estimate = DEFAULT_SERPAPI_COST_ESTIMATE

    def __init__(self, api_key: str, client: httpx.Client) -> None:
        self.api_key = api_key
        self.client = client

    def search(self, pair: SearchPair, limit: int) -> list[dict[str, object]]:
        response = self.client.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_maps",
                "type": "search",
                "q": pair.query,
                "api_key": self.api_key,
            },
            timeout=25.0,
        )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise ResearchProviderError(str(payload["error"]))
        rows = payload.get("local_results") or payload.get("places_results") or []
        return [self._normalize(row, pair) for row in rows[:limit]]

    def _normalize(self, row: Mapping[str, Any], pair: SearchPair) -> dict[str, object]:
        title = row.get("title") or row.get("name") or ""
        source_url = row.get("place_id_search") or row.get("link") or _google_maps_search_url(str(title), pair.city)
        return {
            "business_name": title,
            "industry": pair.niche_id,
            "city_country": _city_country(pair.city),
            "website": row.get("website") or "",
            "email": row.get("email") or "",
            "phone": row.get("phone") or row.get("phone_number") or "",
            "source_url": source_url,
            "notes": _safe_notes("serpapi", row),
        }


class ApifyGoogleMapsProvider:
    name = "apify"
    cost_estimate = DEFAULT_APIFY_COST_ESTIMATE

    def __init__(self, token: str, client: httpx.Client) -> None:
        self.token = token
        self.client = client
        actor = os.getenv("APIFY_GOOGLE_MAPS_ACTOR", "compass/crawler-google-places").replace("/", "~")
        self.url = f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"

    def search(self, pair: SearchPair, limit: int) -> list[dict[str, object]]:
        response = self.client.post(
            self.url,
            params={"token": self.token},
            json={
                "searchStringsArray": [pair.query],
                "locationQuery": pair.city,
                "maxCrawledPlacesPerSearch": limit,
                "language": "en",
            },
            timeout=60.0,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ResearchProviderError("Apify response was not a dataset item list")
        return [self._normalize(row, pair) for row in payload[:limit]]

    def _normalize(self, row: Mapping[str, Any], pair: SearchPair) -> dict[str, object]:
        title = row.get("title") or row.get("name") or row.get("businessName") or ""
        return {
            "business_name": title,
            "industry": pair.niche_id,
            "city_country": _city_country(pair.city),
            "website": row.get("website") or row.get("url") or "",
            "email": row.get("email") or "",
            "phone": row.get("phone") or row.get("phoneNumber") or "",
            "source_url": row.get("url") or row.get("placeUrl") or _google_maps_search_url(str(title), pair.city),
            "notes": _safe_notes("apify", row),
        }


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    try:
        return int(str(raw))
    except (TypeError, ValueError):
        return default


def _city_country(city: str) -> str:
    return f"{city}, UAE" if _is_foreign_city(city) else f"{city}, India"


def _is_foreign_city(city: str) -> bool:
    text = city.lower()
    return any(hint in text for hint in FOREIGN_CITY_HINTS) or is_foreign_market(city)


def _query_for(niche_id: str, city: str) -> str:
    label = NICHE_SEARCH_LABELS.get(niche_id, niche_id.replace("_", " "))
    return f"{label} in {city} website phone"


def _google_maps_search_url(name: str, city: str) -> str:
    return f"https://www.google.com/maps/search/{quote_plus((name + ' ' + city).strip())}"


def _safe_notes(provider: str, row: Mapping[str, Any]) -> str:
    rating = row.get("rating")
    reviews = row.get("reviews") or row.get("reviews_count") or row.get("reviewsCount")
    parts = [f"source={provider}"]
    if rating:
        parts.append(f"rating={rating}")
    if reviews:
        parts.append(f"reviews={reviews}")
    return "; ".join(parts)


def _candidate_key(lead: Mapping[str, object]) -> str:
    email = norm_email(str(lead.get("email") or ""))
    if email:
        return f"email:{email}"
    domain = domain_from_url(str(lead.get("website") or ""))
    if domain:
        return f"domain:{domain}"
    return f"business:{norm_business(str(lead.get('business_name') or ''))}"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"research config must be a mapping: {path}")
    return loaded


def load_research_config(path: str | Path = DEFAULT_CONFIG_PATH) -> ResearchConfig:
    raw = _load_yaml(Path(path))
    targets = [
        ResearchTarget(
            niche_id=str(item["id"]),
            cities=[str(city) for city in item.get("cities", [])],
            daily_quota=int(item.get("daily_quota", 0)),
        )
        for item in raw.get("niches", [])
        if item.get("id") and item.get("cities") and int(item.get("daily_quota", 0)) > 0
    ]
    split = raw.get("market_split") or {}
    return ResearchConfig(
        targets=targets,
        india_share_pct=int(split.get("india_share_pct", 80)),
        foreign_share_pct=int(split.get("foreign_share_pct", 20)),
        global_daily_cap=int(raw.get("global_daily_cap", 30)),
    )


def _ensure_research_schema() -> None:
    db.init_db()
    with db.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS research_query_usage (
                usage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                niche_id TEXT,
                city TEXT,
                market TEXT,
                query TEXT,
                provider TEXT,
                candidates_returned INTEGER DEFAULT 0,
                cost_estimate REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_research_usage_date ON research_query_usage(run_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_research_usage_market ON research_query_usage(market, run_date)")


class LeadResearchAgent(BaseAgent):
    agent_name = "lead_research_agent"

    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
        fixtures_path: str | Path = DEFAULT_FIXTURES_PATH,
    ) -> None:
        super().__init__()
        self.http_client = http_client or httpx.Client(timeout=25.0)
        self.config_path = Path(config_path)
        self.fixtures_path = Path(fixtures_path)

    def build_search_plan(self, india_limit: int = 35, foreign_limit: int = 10) -> list[str]:
        """Backward-compatible query-plan helper used by older docs/tests."""

        config = load_research_config(self.config_path)
        pairs = self.build_search_pairs(config=config, max_pairs=india_limit + foreign_limit)
        india: list[str] = []
        foreign: list[str] = []
        for pair in pairs:
            if pair.market == "foreign":
                foreign.append(pair.query)
            else:
                india.append(pair.query)
        return india[:india_limit] + foreign[:foreign_limit]

    def build_search_pairs(
        self,
        *,
        config: ResearchConfig | None = None,
        day: str | None = None,
        max_pairs: int | None = None,
    ) -> list[SearchPair]:
        config = config or load_research_config(self.config_path)
        day = day or date.today().isoformat()
        slots = self._expand_target_slots(config)
        if not slots:
            return []
        max_pairs = max_pairs or config.global_daily_cap
        rolling = self._rolling_market_counts(day)
        start_offset = (rolling["india"] + rolling["foreign"]) % len(slots)
        rotated = slots[start_offset:] + slots[:start_offset]
        pools = {
            "india": [pair for pair in rotated if pair.market == "india"],
            "foreign": [pair for pair in rotated if pair.market == "foreign"],
        }
        idx = {"india": 0, "foreign": 0}
        selected: list[SearchPair] = []
        local_counts = dict(rolling)

        while len(selected) < max_pairs and (pools["india"] or pools["foreign"]):
            market = self._next_market(config, local_counts)
            if not pools[market]:
                market = "foreign" if market == "india" else "india"
            if not pools[market]:
                break
            pair = pools[market][idx[market] % len(pools[market])]
            idx[market] += 1
            selected.append(pair)
            local_counts[market] += 1
        return selected

    def _expand_target_slots(self, config: ResearchConfig) -> list[SearchPair]:
        slots: list[SearchPair] = []
        for target in config.targets:
            for offset in range(target.daily_quota):
                city = target.cities[offset % len(target.cities)]
                market = "foreign" if _is_foreign_city(city) else "india"
                slots.append(SearchPair(target.niche_id, city, market, _query_for(target.niche_id, city)))
        return slots

    def _next_market(self, config: ResearchConfig, counts: Mapping[str, int]) -> str:
        india_count = counts.get("india", 0)
        foreign_count = counts.get("foreign", 0)
        total_after_next = india_count + foreign_count + 1
        target_india = total_after_next * max(config.india_share_pct, 0) / 100
        if india_count < target_india:
            return "india"
        return "foreign"

    def _rolling_market_counts(self, day: str) -> dict[str, int]:
        _ensure_research_schema()
        current = date.fromisoformat(day)
        since = (current - timedelta(days=6)).isoformat()
        with db.cursor() as cur:
            rows = cur.execute(
                """
                SELECT market, COUNT(*) AS n
                FROM research_query_usage
                WHERE date(run_date) BETWEEN date(?) AND date(?)
                GROUP BY market
                """,
                (since, day),
            ).fetchall()
        counts = {"india": 0, "foreign": 0}
        for row in rows:
            if row["market"] in counts:
                counts[row["market"]] = int(row["n"])
        return counts

    def _queries_used_today(self, day: str) -> int:
        _ensure_research_schema()
        with db.cursor() as cur:
            row = cur.execute(
                "SELECT COUNT(*) AS n FROM research_query_usage WHERE date(run_date) = date(?)",
                (day,),
            ).fetchone()
        return int(row["n"] if row else 0)

    def _record_query_usage(self, day: str, pair: SearchPair, provider: str, candidates_returned: int, cost_estimate: float) -> None:
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO research_query_usage (
                    run_date, niche_id, city, market, query, provider,
                    candidates_returned, cost_estimate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (day, pair.niche_id, pair.city, pair.market, pair.query, provider, candidates_returned, cost_estimate),
            )

    def _providers(self) -> list[SerpApiMapsProvider | ApifyGoogleMapsProvider]:
        providers: list[SerpApiMapsProvider | ApifyGoogleMapsProvider] = []
        serpapi_key = os.getenv("SERPAPI_API_KEY", "").strip()
        apify_token = os.getenv("APIFY_API_TOKEN", "").strip()
        if serpapi_key:
            providers.append(SerpApiMapsProvider(serpapi_key, self.http_client))
        if apify_token:
            providers.append(ApifyGoogleMapsProvider(apify_token, self.http_client))
        return providers

    def _fetch_candidates(
        self,
        pair: SearchPair,
        *,
        limit: int,
        remaining_query_budget: int,
    ) -> tuple[list[dict[str, object]], list[tuple[str, int, float, str]]]:
        attempts: list[tuple[str, int, float, str]] = []
        for provider in self._providers():
            if len(attempts) >= remaining_query_budget:
                break
            try:
                candidates = provider.search(pair, limit=limit)
                attempts.append((provider.name, len(candidates), provider.cost_estimate, "ok"))
                if candidates:
                    return candidates, attempts
            except Exception as exc:
                attempts.append((provider.name, 0, provider.cost_estimate, exc.__class__.__name__))
                self.logger.warning("research provider failed provider=%s query=%s error=%s", provider.name, pair.query, exc.__class__.__name__)
        return [], attempts

    def _load_csv(self, input_path: str | Path) -> list[dict[str, object]]:
        with Path(input_path).open("r", newline="", encoding="utf-8-sig") as f:
            return [normalize_lead(row) for row in csv.DictReader(f)]

    def _load_fixtures(self) -> list[dict[str, object]]:
        if not self.fixtures_path.exists():
            return []
        payload = json.loads(self.fixtures_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rows = payload.get("businesses", [])
        else:
            rows = payload
        if not isinstance(rows, list):
            return []
        return [dict(row) for row in rows if isinstance(row, dict)]

    def _prepare_rows(self, rows: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
        prepared: list[dict[str, object]] = []
        for raw in rows:
            raw_lead = dict(raw)
            if not raw_lead.get("business_name"):
                raw_lead["business_name"] = raw_lead.get("title") or raw_lead.get("name") or raw_lead.get("businessName") or ""
            if not raw_lead.get("website"):
                raw_lead["website"] = raw_lead.get("url") or ""
            lead = normalize_lead(raw_lead)
            if not lead.get("business_name"):
                continue
            lead["email"] = norm_email(str(lead.get("email") or ""))
            lead["status"] = str(lead.get("status") or "new")
            lead["automation_opportunity"] = lead.get("automation_opportunity") or NICHE_HOOKS.get(str(lead.get("industry") or ""), NICHE_HOOKS["premium_local_businesses"])
            lead["personalization_hook"] = lead.get("personalization_hook") or lead["automation_opportunity"]
            scoring = score_lead(lead)
            lead["lead_score"] = scoring.score
            base_notes = str(lead.get("notes") or "").split(" | score reasons:", 1)[0].strip()
            lead["notes"] = (base_notes + f" | score reasons: {', '.join(scoring.reasons)}").strip(" |")
            lead["recommended_package"] = lead.get("recommended_package") or recommend_package(lead)
            prepared.append(lead)
        return prepared

    def _write_run_log(self, day: str, stats: LeadResearchStats, *, dry_run: bool) -> Path:
        path = data_path("logs", f"lead_research_{day}.log")
        lines = [
            f"date={day}",
            f"mode={'dry-run' if dry_run else 'live'}",
            stats.summary(),
            f"candidates_returned={stats.candidates_returned}",
            f"providers={','.join(sorted(stats.providers_used)) or 'fixtures'}",
        ]
        lines.extend(stats.query_lines)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def _run_from_rows(self, rows: Iterable[Mapping[str, object]], *, dry_run: bool, day: str, stats: LeadResearchStats) -> list[dict[str, object]]:
        prepared = self._prepare_rows(rows)
        if dry_run:
            stats.candidates_returned += len(prepared)
            return prepared

        accepted_rows: list[dict[str, object]] = []
        for lead in prepared:
            if stats.accepted >= self._config.global_daily_cap:
                break
            lead_id, action = upsert_lead(lead)
            if action == "inserted":
                stats.inserted += 1
                lead["lead_id"] = lead_id
                accepted_rows.append(lead)
            elif action == "updated":
                stats.updated += 1
                lead["lead_id"] = lead_id
                accepted_rows.append(lead)
            elif action == "suppressed":
                stats.suppressed += 1
            else:
                stats.skipped += 1
        return accepted_rows

    def run(
        self,
        dry_run: bool = False,
        input_path: str | Path | None = None,
        india_limit: int = 35,
        foreign_limit: int = 10,
        day: str | None = None,
    ) -> AgentResult:
        day = day or date.today().isoformat()
        effective_dry_run = dry_run or _env_bool("RESEARCH_DRY_RUN", False)
        self._config = load_research_config(self.config_path)
        stats = LeadResearchStats()
        seen_candidates: set[str] = set()
        max_queries = _env_int("MAX_RESEARCH_QUERIES_PER_DAY", DEFAULT_MAX_RESEARCH_QUERIES_PER_DAY)
        output_rows: list[dict[str, object]] = []

        with self.run_context(dry_run=effective_dry_run):
            if input_path:
                rows = self._load_csv(input_path)
                output_rows = self._run_from_rows(rows, dry_run=effective_dry_run, day=day, stats=stats)
            elif effective_dry_run:
                fixtures = self._load_fixtures()
                output_rows = self._run_from_rows(fixtures, dry_run=True, day=day, stats=stats)
            else:
                queries_used = self._queries_used_today(day)
                remaining_budget = max(0, max_queries - queries_used)
                if remaining_budget <= 0:
                    stats.query_lines.append(f"budget_guard=tripped used={queries_used} max={max_queries}")
                pairs = self.build_search_pairs(config=self._config, day=day, max_pairs=min(self._config.global_daily_cap, remaining_budget))
                for pair in pairs:
                    if stats.accepted >= self._config.global_daily_cap:
                        break
                    if queries_used + stats.queries >= max_queries:
                        stats.query_lines.append(f"budget_guard=tripped used={queries_used + stats.queries} max={max_queries}")
                        break
                    candidates, attempts = self._fetch_candidates(
                        pair,
                        limit=max(5, self._config.global_daily_cap - stats.accepted),
                        remaining_query_budget=max_queries - queries_used - stats.queries,
                    )
                    for provider, count, cost_estimate, status in attempts:
                        stats.queries += 1
                        stats.cost_estimate += cost_estimate
                        stats.providers_used.add(provider)
                        stats.query_lines.append(
                            f"query market={pair.market} niche={pair.niche_id} city={pair.city} provider={provider} status={status} candidates={count}"
                        )
                        self._record_query_usage(day, pair, provider, count, cost_estimate)
                    stats.candidates_returned += len(candidates)
                    for candidate in candidates:
                        if stats.accepted >= self._config.global_daily_cap:
                            break
                        lead = self._prepare_rows([candidate])
                        if not lead:
                            stats.skipped += 1
                            continue
                        key = _candidate_key(lead[0])
                        if key in seen_candidates:
                            stats.skipped += 1
                            continue
                        seen_candidates.add(key)
                        lead_id, action = upsert_lead(lead[0])
                        if action == "inserted":
                            stats.inserted += 1
                            lead[0]["lead_id"] = lead_id
                            output_rows.append(lead[0])
                        elif action == "updated":
                            stats.updated += 1
                            lead[0]["lead_id"] = lead_id
                            output_rows.append(lead[0])
                        elif action == "suppressed":
                            stats.suppressed += 1
                        else:
                            stats.skipped += 1

            log_path = self._write_run_log(day, stats, dry_run=effective_dry_run)
            outputs = {"run_log": str(log_path)}
            if output_rows and not effective_dry_run:
                out = export_rows_to_excel(output_rows, excel_output("leads_today.xlsx"), "Leads")
                outputs["leads_excel"] = str(out)

            message = stats.summary()
            self._job_log_message = message
            return AgentResult(
                self.agent_name,
                "ok",
                message,
                count=len(output_rows),
                outputs=outputs,
                data={"stats": stats.as_dict(), "rows": output_rows},
            )
