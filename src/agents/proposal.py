"""Proposal agent wrapper around the core proposal generator."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Mapping

from src import db
from src.agents.base import AgentResult, BaseAgent
from src.agents.integrations import generate_proposal_with_core
from src.config import data_path

DEFAULT_PAYMENT_TERMS = "50% advance; 50% before launch; support starts after launch; add-ons billed separately; prices exclude GST if applicable."


class ProposalAgent(BaseAgent):
    agent_name = "proposal_agent"

    def _fallback_proposal(self, payload: Mapping[str, object], day: str) -> Path:
        client = str(payload.get("client_name") or payload.get("business_name") or "Client").strip()
        package = str(payload.get("package") or payload.get("recommended_package") or "Pro").strip()
        path = data_path("proposals", f"{client.lower().replace(' ', '_')}_{day}.md")
        body = f"""# QuantumReach Proposal - {client}

## Objective
Build a premium website and lightweight lead system that improves trust, enquiry flow, and follow-up speed.

## Recommended Package
{package}

## Scope
- Premium website structure and copy direction
- Mobile-first enquiry path
- WhatsApp or form lead capture
- Google Sheets/CRM sync where applicable
- Simple follow-up workflow

## Timeline
{payload.get('timeline', '2-4 weeks depending on scope and client inputs')}

## Investment
{payload.get('investment', payload.get('price', 'To be confirmed after scope approval'))}

## Payment Terms
{DEFAULT_PAYMENT_TERMS}

## Client Requirements
Brand assets, service details, proof/testimonials, project images, domain/hosting access where needed.

## Revision Terms
Two structured revision rounds before launch. Scope changes are estimated separately.

## Support
Support starts after launch. Retainers and add-ons are billed separately.

## Next Steps
Approve scope, pay advance, share assets, and confirm launch targets.
"""
        path.write_text(body, encoding="utf-8")
        return path

    def run(self, payload: Mapping[str, object], dry_run: bool = False, day: str | None = None) -> AgentResult:
        day = day or date.today().isoformat()
        with self.run_context(dry_run=dry_run):
            core_path = None if dry_run else generate_proposal_with_core(payload)
            path = core_path if core_path else (Path("") if dry_run else self._fallback_proposal(payload, day))
            if not dry_run:
                with db.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO proposals (
                            client_name, industry, package, add_ons, timeline, price,
                            support_plan, payment_terms, notes, md_path
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            payload.get("client_name") or payload.get("business_name"),
                            payload.get("industry"),
                            payload.get("package") or payload.get("recommended_package"),
                            payload.get("add_ons"),
                            payload.get("timeline"),
                            payload.get("price") or 0,
                            payload.get("support_plan"),
                            DEFAULT_PAYMENT_TERMS,
                            payload.get("notes"),
                            str(path),
                        ),
                    )
            return AgentResult(
                self.agent_name,
                "ok",
                "proposal generated" if not dry_run else "dry-run proposal prepared",
                count=1,
                outputs={"proposal": str(path) if str(path) else ""},
            )
