"""Daily founder-led content pack generation."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from src import db
from src.agents.base import AgentResult, BaseAgent
from src.config import data_path

THEMES = [
    "premium website mistakes",
    "AI automation for service businesses",
    "Mumbai businesses losing leads due to slow follow-up",
    "before/after redesign concepts",
    "founder building agency while building product",
    "websites as lead systems, not brochures",
]


def _theme_for_day(day: date) -> str:
    return THEMES[day.toordinal() % len(THEMES)]


def build_content_pack(day: str | None = None) -> str:
    current = date.fromisoformat(day) if day else date.today()
    theme = _theme_for_day(current)
    return f"""# QuantumReach Content Pack - {current.isoformat()}

Theme: {theme}

## LinkedIn/X Post
Most service business websites are still built like brochures.

The better model:
- show proof fast
- make the offer obvious
- remove friction from enquiry
- follow up automatically when someone shows intent

A premium website is not decoration. It is the front end of a lead system.

## Instagram Carousel Outline
Title: 5 website fixes that make premium service businesses look more trustworthy
1. Lead with the strongest proof, not a vague welcome line.
2. Make the enquiry CTA visible before the first scroll.
3. Show project/service depth with clean structure.
4. Add WhatsApp or booking capture where intent is highest.
5. Follow up automatically within minutes, not days.
Close: Your website should help sales, not just exist online.

## Cold DM Variant
Saw your work and had one practical website idea: your service/project pages could push more visitors toward enquiry with sharper proof, cleaner mobile CTA placement, and faster follow-up. Worth sending a short teardown?

## Case-Study Style Post
A premium local business does not always need a bigger website first.

Usually the first wins are operational:
- clarify the offer
- improve the mobile enquiry path
- connect enquiries to a Sheet/CRM
- send an instant WhatsApp or email follow-up

That turns the site from a passive portfolio into a basic growth system. Simple, but most businesses still do not have it.

## Website Teardown Idea
Pick one architect, clinic, gym, or coaching institute with a strong offline reputation but a weak enquiry path. Teardown angle: where trust drops, where mobile friction appears, and what automation should happen after the first enquiry.
"""


class ContentAgent(BaseAgent):
    agent_name = "content_agent"

    def _output_path(self, day: str) -> Path:
        return data_path("content", day, "content_pack.md")

    def run(self, dry_run: bool = False, day: str | None = None) -> AgentResult:
        day = day or date.today().isoformat()
        pack = build_content_pack(day)
        with self.run_context(dry_run=dry_run):
            outputs: dict[str, str] = {}
            if not dry_run:
                path = self._output_path(day)
                path.write_text(pack, encoding="utf-8")
                with db.cursor() as cur:
                    cur.execute(
                        "INSERT INTO content_assets (kind, title, body, path, tags) VALUES (?, ?, ?, ?, ?)",
                        ("daily_content_pack", f"Content Pack {day}", pack, str(path), "daily,content,quantumreach"),
                    )
                outputs["content_pack"] = str(path)
            return AgentResult(
                self.agent_name,
                "ok",
                "content pack generated" if not dry_run else "dry-run content pack generated",
                count=1,
                outputs=outputs,
                data={"content_pack": pack},
            )
