"""Cold email draft generation with manual approval only."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Mapping

from src import db
from src.agents.base import AgentResult, BaseAgent
from src.agents.integrations import excel_output, export_rows_to_excel
from src.agents.lead_utils import first_name, has_clear_email, is_foreign_market, normalize_lead
from src.agents.outreach_policy import has_negative_reply, is_followup_eligible_status, is_suppressed
from src.agents.package_recommendation import recommend_package
from src.config import CONFIG


def _personalized_observation(lead: Mapping[str, object]) -> str:
    hook = str(lead.get("personalization_hook") or "").strip()
    if hook:
        return hook
    opportunity = str(lead.get("automation_opportunity") or "").strip()
    if opportunity:
        return opportunity
    return "The enquiry path can be made clearer with a stronger project/service page and a faster WhatsApp follow-up flow."


def render_initial_email(raw_lead: Mapping[str, object]) -> dict[str, str]:
    lead = normalize_lead(raw_lead)
    name = first_name(str(lead.get("decision_maker") or ""))
    business = str(lead.get("business_name") or "your business").strip()
    industry = str(lead.get("industry") or "service").strip()
    city_country = str(lead.get("city_country") or "your market").strip()
    observation = _personalized_observation(lead)
    foreign = is_foreign_market(city_country)

    if foreign:
        subject = f"Website + lead system idea for {business}"
        body = f"""Hi {name},

I came across {business} while looking at {industry} businesses in {city_country}.

You seem to have strong service credibility, but your website could likely be doing more to convert visitors into enquiries - especially through better positioning, stronger proof, cleaner mobile flow, and automated lead follow-up.

I run {CONFIG.agency_name}. We build premium websites and AI-powered lead systems for service businesses.

One specific improvement I noticed:
{observation}

Would it be useful if I sent a short teardown with 2-3 practical improvements?

Best,
Yagya
{CONFIG.agency_name}
{CONFIG.founder_email}
{CONFIG.agency_domain}

Reply "no" and I won't follow up."""
    else:
        subject = f"Quick idea for {business}"
        body = f"""Hi {name},

I came across {business} while looking at {industry} businesses in {city_country}.

Your work seems strong, but your website could probably do more of the heavy lifting: clearer project presentation, stronger trust signals, faster enquiry flow, and automated follow-up after someone shows interest.

I run {CONFIG.agency_name}. We build premium websites and lightweight AI automations for service businesses - websites, WhatsApp lead capture, Google Sheets/CRM sync, and simple follow-up systems.

One specific idea for your site:
{observation}

Worth sending you a quick 2-3 point teardown?

Best,
Yagya
{CONFIG.agency_name}
{CONFIG.founder_email}
{CONFIG.agency_domain}

Reply "no" and I won't follow up."""

    return {
        "subject": subject,
        "email_body": body,
        "personalization_reason": observation,
        "recommended_package": str(lead.get("recommended_package") or recommend_package(lead)),
    }


def render_followups(raw_lead: Mapping[str, object], initial_subject: str) -> tuple[str, str]:
    lead = normalize_lead(raw_lead)
    name = first_name(str(lead.get("decision_maker") or ""))
    business = str(lead.get("business_name") or "your business").strip()
    observation = _personalized_observation(lead)
    followup_1 = f"""Hi {name},

Just bumping this in case it got buried.

The quick win I noticed for {business}: {observation}

I can send a short teardown with 2-3 practical fixes. No pitch deck, just useful notes.

Best,
Yagya

Reply "no" and I won't follow up."""
    followup_2 = f"""Hi {name},

Last note from my side.

If improving the website and follow-up flow is not a priority right now, no problem. If it is, I can send a compact teardown for {business} and you can decide from there.

Best,
Yagya

Reply "no" and I won't follow up."""
    return followup_1, followup_2


class ColdEmailAgent(BaseAgent):
    agent_name = "cold_email_agent"

    def _candidate_rows(self, conn, limit: int) -> list[dict[str, object]]:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM leads
            WHERE email IS NOT NULL
              AND email != ''
              AND LOWER(COALESCE(status, 'new')) NOT IN ('suppressed', 'negative_reply', 'unsubscribed', 'rejected', 'converted', 'client')
            ORDER BY lead_score DESC, created_at DESC
            LIMIT ?
            """,
            (limit * 4,),
        )
        out: list[dict[str, object]] = []
        for row in cur.fetchall():
            lead = dict(row)
            if not has_clear_email(str(lead.get("email") or "")):
                continue
            if not is_followup_eligible_status(str(lead.get("status") or "")):
                continue
            if is_suppressed(conn, lead) or has_negative_reply(conn, int(lead["lead_id"])):
                continue
            cur.execute(
                "SELECT 1 FROM outreach_messages WHERE lead_id = ? OR LOWER(email) = ? LIMIT 1",
                (lead["lead_id"], str(lead["email"]).lower()),
            )
            if cur.fetchone():
                continue
            out.append(lead)
            if len(out) >= limit:
                break
        return out

    def _draft_row(self, lead: dict[str, object], today: date) -> dict[str, object]:
        rendered = render_initial_email(lead)
        followup_1, followup_2 = render_followups(lead, rendered["subject"])
        return {
            "lead_id": lead["lead_id"],
            "business_name": lead.get("business_name", ""),
            "email": lead.get("email", ""),
            "subject": rendered["subject"],
            "email_body": rendered["email_body"],
            "personalization_reason": rendered["personalization_reason"],
            "recommended_package": rendered["recommended_package"],
            "status": "needs_approval",
            "approved_by_yagya": 0,
            "followup_1_body": followup_1,
            "followup_1_date": (today + timedelta(days=3)).isoformat(),
            "followup_2_body": followup_2,
            "followup_2_date": (today + timedelta(days=7)).isoformat(),
        }

    def run(self, dry_run: bool = False, limit: int = 30, day: str | None = None) -> AgentResult:
        today = date.fromisoformat(day) if day else date.today()
        with self.run_context(dry_run=dry_run):
            with db.connect() as conn:
                candidates = self._candidate_rows(conn, limit)
                drafts = [self._draft_row(lead, today) for lead in candidates]
                if not dry_run:
                    for draft in drafts:
                        conn.execute(
                            """
                            INSERT INTO outreach_messages (
                                lead_id, business_name, email, subject, email_body,
                                personalization_reason, recommended_package, status,
                                approved_by_yagya, followup_1_body, followup_1_date,
                                followup_2_body, followup_2_date
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                draft["lead_id"],
                                draft["business_name"],
                                draft["email"],
                                draft["subject"],
                                draft["email_body"],
                                draft["personalization_reason"],
                                draft["recommended_package"],
                                draft["status"],
                                draft["approved_by_yagya"],
                                draft["followup_1_body"],
                                draft["followup_1_date"],
                                draft["followup_2_body"],
                                draft["followup_2_date"],
                            ),
                        )
                    conn.commit()
            outputs: dict[str, str] = {}
            if not dry_run:
                outputs["drafts_excel"] = str(export_rows_to_excel(drafts, excel_output("cold_email_drafts.xlsx"), "Drafts"))
            return AgentResult(
                self.agent_name,
                "ok",
                "cold email drafts generated for manual approval" if not dry_run else "dry-run cold email drafts generated",
                count=len(drafts),
                outputs=outputs,
                data={"drafts": drafts},
            )
