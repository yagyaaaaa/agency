"""Daily orchestration for Jarvis-hosted agency automation."""
from __future__ import annotations

from datetime import date

from src.agents.base import AgentResult
from src.agents.ceo_control import CEOControlAgent
from src.agents.cold_email import ColdEmailAgent
from src.agents.content import ContentAgent
from src.agents.followup import FollowupAgent
from src.agents.lead_research import LeadResearchAgent
from src.agents.profit import ProfitAgent
from src.agents.tool_research import ToolResearchAgent


class DailyOrchestrator:
    def __init__(self) -> None:
        self.lead_research = LeadResearchAgent()
        self.cold_email = ColdEmailAgent()
        self.followups = FollowupAgent()
        self.content = ContentAgent()
        self.tool_research = ToolResearchAgent()
        self.profit = ProfitAgent()
        self.ceo = CEOControlAgent()

    def run_daily(self, dry_run: bool = False, input_path: str | None = None, day: str | None = None) -> list[AgentResult]:
        day = day or date.today().isoformat()
        results: list[AgentResult] = []
        results.append(self.lead_research.run(dry_run=dry_run, input_path=input_path, day=day))
        results.append(self.cold_email.run(dry_run=dry_run, day=day))
        results.append(self.followups.run(dry_run=dry_run, day=day))
        results.append(self.content.run(dry_run=dry_run, day=day))
        results.append(self.tool_research.run(dry_run=dry_run, day=day))
        results.append(self.profit.run(dry_run=dry_run, day=day))

        files: list[str] = []
        for result in results:
            files.extend(value for value in result.outputs.values() if value and value.endswith((".xlsx", ".md")))
        results.append(self.ceo.run(dry_run=dry_run, day=day, files=files))
        return results
