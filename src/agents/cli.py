"""CLI entrypoint for QuantumReach agents."""
from __future__ import annotations

import argparse
import json
from typing import Sequence

from src.agents.ceo_control import CEOControlAgent
from src.agents.cold_email import ColdEmailAgent
from src.agents.content import ContentAgent
from src.agents.followup import FollowupAgent
from src.agents.lead_research import LeadResearchAgent
from src.agents.orchestrator import DailyOrchestrator
from src.agents.profit import ProfitAgent
from src.agents.proposal import ProposalAgent
from src.agents.tool_research import ToolResearchAgent


def _print_result(result) -> None:
    print(json.dumps(
        {
            "agent": result.agent_name,
            "status": result.status,
            "message": result.message,
            "count": result.count,
            "outputs": result.outputs,
        },
        indent=2,
    ))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QuantumReach Agency OS agents")
    parser.add_argument("--dry-run", action="store_true", help="Run without business-data writes or Telegram sends")
    parser.add_argument("--date", help="ISO date override, e.g. 2026-05-12")
    sub = parser.add_subparsers(dest="command", required=True)

    lead = sub.add_parser("lead-research", aliases=["lead_research"])
    lead.add_argument("--input", help="CSV of approved researched leads to import/score")
    lead.add_argument("--india-limit", type=int, default=35)
    lead.add_argument("--foreign-limit", type=int, default=10)

    cold = sub.add_parser("cold-email")
    cold.add_argument("--limit", type=int, default=30)

    sub.add_parser("followups")
    sub.add_parser("content")
    tools = sub.add_parser("tool-research")
    tools.add_argument("--count", type=int, default=3)
    sub.add_parser("profit")
    sub.add_parser("daily")
    sub.add_parser("ceo-summary")

    proposal = sub.add_parser("proposal")
    proposal.add_argument("--payload-json", required=True, help="JSON object with client_name, package, scope fields")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dry_run = bool(args.dry_run)
    day = args.date

    if args.command in {"lead-research", "lead_research"}:
        result = LeadResearchAgent().run(dry_run=dry_run, input_path=args.input, india_limit=args.india_limit, foreign_limit=args.foreign_limit, day=day)
        _print_result(result)
        return 0
    if args.command == "cold-email":
        result = ColdEmailAgent().run(dry_run=dry_run, limit=args.limit, day=day)
        _print_result(result)
        return 0
    if args.command == "followups":
        _print_result(FollowupAgent().run(dry_run=dry_run, day=day))
        return 0
    if args.command == "content":
        _print_result(ContentAgent().run(dry_run=dry_run, day=day))
        return 0
    if args.command == "tool-research":
        _print_result(ToolResearchAgent().run(dry_run=dry_run, day=day, count=args.count))
        return 0
    if args.command == "profit":
        _print_result(ProfitAgent().run(dry_run=dry_run, day=day))
        return 0
    if args.command == "daily":
        for result in DailyOrchestrator().run_daily(dry_run=dry_run, day=day):
            _print_result(result)
        return 0
    if args.command == "ceo-summary":
        _print_result(CEOControlAgent().run(dry_run=dry_run, day=day))
        return 0
    if args.command == "proposal":
        payload = json.loads(args.payload_json)
        _print_result(ProposalAgent().run(payload, dry_run=dry_run, day=day))
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
