"""Lead research ingestion, scoring, dedupe, and export."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Iterable

from src import db
from src.agents.base import AgentResult, BaseAgent
from src.agents.integrations import excel_output, export_rows_to_excel
from src.agents.lead_utils import LEAD_FIELDS, is_foreign_market, normalize_lead, normalized_business
from src.agents.package_recommendation import recommend_package
from src.agents.scoring import score_lead
from src.config import data_path
from src.utils.dedupe import domain_from_url, norm_email


DEFAULT_NICHES = [
    "architects",
    "interior designers",
    "builders",
    "clinics",
    "gyms fitness coaches",
    "coaching institutes",
    "premium local businesses",
    "Dubai service businesses",
]

INDIA_CITIES = ["Mumbai", "Thane", "Navi Mumbai", "Pune", "Bengaluru", "Delhi NCR", "Ahmedabad"]
FOREIGN_CITIES = ["Dubai", "Abu Dhabi", "Sharjah"]


class LeadResearchAgent(BaseAgent):
    agent_name = "lead_research_agent"

    def build_search_plan(self, india_limit: int = 35, foreign_limit: int = 10) -> list[str]:
        queries: list[str] = []
        for niche in DEFAULT_NICHES[:7]:
            for city in INDIA_CITIES[:3]:
                queries.append(f'{niche} "{city}" website email Instagram')
        for niche in ("architects", "interior designers", "clinics", "premium service businesses"):
            for city in FOREIGN_CITIES:
                queries.append(f'{niche} "{city}" website contact')
        return queries[: india_limit + foreign_limit]

    def _load_csv(self, input_path: str | Path) -> list[dict[str, object]]:
        with Path(input_path).open("r", newline="", encoding="utf-8-sig") as f:
            return [normalize_lead(row) for row in csv.DictReader(f)]

    def _existing_lead_id(self, conn, lead: dict[str, object]) -> int | None:
        email = norm_email(str(lead.get("email") or ""))
        cur = conn.cursor()
        if email:
            cur.execute("SELECT lead_id FROM leads WHERE LOWER(email) = ? LIMIT 1", (email,))
            row = cur.fetchone()
            if row:
                return int(row["lead_id"])
        business = normalized_business(lead)
        website_domain = domain_from_url(str(lead.get("website") or ""))
        if business:
            cur.execute("SELECT lead_id, business_name, website FROM leads")
            for row in cur.fetchall():
                same_business = normalized_business({"business_name": row["business_name"]}) == business
                same_domain = website_domain and domain_from_url(row["website"]) == website_domain
                if same_business or same_domain:
                    return int(row["lead_id"])
        return None

    def _upsert_lead(self, conn, lead: dict[str, object]) -> int:
        existing = self._existing_lead_id(conn, lead)
        values = {field: lead.get(field, "") for field in LEAD_FIELDS if field != "lead_id"}
        if existing:
            assignments = ", ".join(f"{field} = ?" for field in values.keys())
            conn.execute(
                f"UPDATE leads SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE lead_id = ?",
                [*values.values(), existing],
            )
            return existing
        fields = ", ".join(values.keys())
        placeholders = ", ".join("?" for _ in values)
        cur = conn.execute(f"INSERT INTO leads ({fields}) VALUES ({placeholders})", list(values.values()))
        return int(cur.lastrowid)

    def _prepare_rows(self, rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
        prepared: list[dict[str, object]] = []
        india_count = 0
        foreign_count = 0
        for raw in rows:
            lead = normalize_lead(raw)
            scoring = score_lead(lead)
            lead["lead_score"] = scoring.score
            base_notes = str(lead.get("notes") or "").split(" | score reasons:", 1)[0].strip()
            lead["notes"] = (base_notes + f" | score reasons: {', '.join(scoring.reasons)}").strip(" |")
            lead["recommended_package"] = lead.get("recommended_package") or recommend_package(lead)
            if is_foreign_market(str(lead.get("city_country") or "")):
                foreign_count += 1
            else:
                india_count += 1
            prepared.append(lead)
        self.logger.info("prepared leads india=%s foreign=%s total=%s", india_count, foreign_count, len(prepared))
        return prepared

    def _write_search_plan(self, queries: list[str], day: str) -> Path:
        path = data_path("reports", f"lead_research_plan_{day}.md")
        body = ["# Lead Research Plan", "", f"Date: {day}", "", "Use OpenClaw browser access only for this agent.", ""]
        body.extend(f"- {query}" for query in queries)
        path.write_text("\n".join(body) + "\n", encoding="utf-8")
        return path

    def run(
        self,
        dry_run: bool = False,
        input_path: str | Path | None = None,
        india_limit: int = 35,
        foreign_limit: int = 10,
        day: str | None = None,
    ) -> AgentResult:
        day = day or date.today().isoformat()
        with self.run_context(dry_run=dry_run):
            if not input_path:
                queries = self.build_search_plan(india_limit=india_limit, foreign_limit=foreign_limit)
                output = ""
                if not dry_run:
                    output = str(self._write_search_plan(queries, day))
                return AgentResult(
                    self.agent_name,
                    "ok",
                    "no input CSV supplied; wrote research query plan" if not dry_run else "dry-run research query plan generated",
                    count=len(queries),
                    outputs={"research_plan": output},
                    data={"queries": queries},
                )

            rows = self._prepare_rows(self._load_csv(input_path))
            if dry_run:
                return AgentResult(self.agent_name, "ok", "dry-run lead import prepared", count=len(rows), data={"rows": rows})

            with db.connect() as conn:
                for lead in rows:
                    lead["lead_id"] = self._upsert_lead(conn, lead)
                conn.commit()
            out = export_rows_to_excel(rows, excel_output("leads_today.xlsx"), "Leads")
            return AgentResult(
                self.agent_name,
                "ok",
                "leads imported, scored, deduped, and exported",
                count=len(rows),
                outputs={"leads_excel": str(out)},
            )
