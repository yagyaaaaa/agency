"""Daily tool research workflow."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from src import db
from src.agents.base import AgentResult, BaseAgent
from src.config import data_path

TOOL_LIBRARY = [
    {
        "name": "Framer",
        "url": "https://www.framer.com/",
        "category": "premium website design",
        "cost": "Free tier; paid site plans vary",
        "use_case": "Fast premium landing pages and campaign microsites.",
        "implementation_difficulty": "low",
        "expected_agency_impact": "faster design iteration for premium local clients",
        "recommended_action": "use for visual prototypes and small launch sites",
    },
    {
        "name": "Three.js",
        "url": "https://threejs.org/",
        "category": "3D sites / WebGL",
        "cost": "free open source",
        "use_case": "Interactive 3D hero sections and product/space visualizers.",
        "implementation_difficulty": "medium",
        "expected_agency_impact": "higher perceived quality for architecture and luxury clients",
        "recommended_action": "build one reusable architecture-material demo",
    },
    {
        "name": "n8n",
        "url": "https://n8n.io/",
        "category": "automation",
        "cost": "self-host or cloud plans",
        "use_case": "Lead capture, CRM sync, WhatsApp/email handoffs, reporting.",
        "implementation_difficulty": "medium",
        "expected_agency_impact": "turns websites into repeatable lead systems",
        "recommended_action": "standardize two workflows: lead intake and follow-up reminder",
    },
    {
        "name": "PageSpeed Insights",
        "url": "https://pagespeed.web.dev/",
        "category": "SEO/performance",
        "cost": "free",
        "use_case": "Diagnose mobile performance and technical trust issues.",
        "implementation_difficulty": "low",
        "expected_agency_impact": "creates objective audit points for teardowns",
        "recommended_action": "include screenshots/metrics in lead teardown docs",
    },
    {
        "name": "Stripe Payment Links",
        "url": "https://stripe.com/payments/payment-links",
        "category": "payment systems",
        "cost": "transaction fees",
        "use_case": "Simple advance payment collection for foreign clients.",
        "implementation_difficulty": "low",
        "expected_agency_impact": "reduces payment friction for Dubai/foreign packages",
        "recommended_action": "validate account availability and GST/accounting flow before quoting",
    },
    {
        "name": "Tally",
        "url": "https://tally.so/",
        "category": "lead generation",
        "cost": "free tier; paid features available",
        "use_case": "Fast lead forms connected to Sheets/CRM automations.",
        "implementation_difficulty": "low",
        "expected_agency_impact": "quick MVP for clients before custom form work",
        "recommended_action": "use as fallback lead capture when client site stack is limited",
    },
]


def select_tools_for_day(day: str | None = None, count: int = 3) -> list[dict[str, str]]:
    current = date.fromisoformat(day) if day else date.today()
    start = current.toordinal() % len(TOOL_LIBRARY)
    return [TOOL_LIBRARY[(start + offset) % len(TOOL_LIBRARY)] for offset in range(count)]


class ToolResearchAgent(BaseAgent):
    agent_name = "tool_research_agent"

    def _output_path(self, day: str) -> Path:
        return data_path("tool-research", f"{day}.md")

    def _markdown(self, tools: list[dict[str, str]], day: str) -> str:
        lines = [f"# Tool Research - {day}", ""]
        for tool in tools:
            lines.extend(
                [
                    f"## {tool['name']}",
                    f"- URL: {tool['url']}",
                    f"- Category: {tool['category']}",
                    f"- Cost: {tool['cost']}",
                    f"- Use case: {tool['use_case']}",
                    f"- Implementation difficulty: {tool['implementation_difficulty']}",
                    f"- Expected agency impact: {tool['expected_agency_impact']}",
                    f"- Recommended action: {tool['recommended_action']}",
                    "",
                ]
            )
        return "\n".join(lines)

    def run(self, dry_run: bool = False, day: str | None = None, count: int = 3) -> AgentResult:
        day = day or date.today().isoformat()
        tools = select_tools_for_day(day, count=count)
        with self.run_context(dry_run=dry_run):
            outputs: dict[str, str] = {}
            if not dry_run:
                path = self._output_path(day)
                path.write_text(self._markdown(tools, day), encoding="utf-8")
                with db.cursor() as cur:
                    for tool in tools:
                        cur.execute(
                            """
                            INSERT INTO tool_research (
                                name, category, url, notes, rating, cost, use_case,
                                implementation_difficulty, expected_agency_impact,
                                recommended_action, source_date
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                tool["name"],
                                tool["category"],
                                tool["url"],
                                json.dumps(tool, ensure_ascii=True),
                                4,
                                tool["cost"],
                                tool["use_case"],
                                tool["implementation_difficulty"],
                                tool["expected_agency_impact"],
                                tool["recommended_action"],
                                day,
                            ),
                        )
                outputs["tool_research"] = str(path)
            return AgentResult(
                self.agent_name,
                "ok",
                "tool research generated" if not dry_run else "dry-run tool research generated",
                count=len(tools),
                outputs=outputs,
                data={"tools": tools},
            )
