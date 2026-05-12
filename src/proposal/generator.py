"""Proposal generator — outputs Markdown, HTML, and PDF-ready HTML."""
from __future__ import annotations

import html as _html
import re
from datetime import date
from pathlib import Path
from typing import Any

from src.config import CONFIG, data_path
from src.db import cursor
from src.utils.logger import get_logger

log = get_logger("proposal")

DEFAULT_PAYMENT_TERMS = [
    "50% advance to begin work",
    "50% before launch / handover",
    "Support starts after launch",
    "Add-ons billed separately",
    "Prices exclude GST where applicable",
]


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    return s or "client"


def _md(inputs: dict[str, Any]) -> str:
    name = inputs["client_name"]
    industry = inputs.get("industry") or ""
    package = inputs.get("package") or "Pro"
    add_ons = inputs.get("add_ons") or "None"
    timeline = inputs.get("timeline") or "3–5 weeks"
    price = inputs.get("price")
    support_plan = inputs.get("support_plan") or "Standard monthly support"
    payment_terms = inputs.get("payment_terms") or DEFAULT_PAYMENT_TERMS
    notes = inputs.get("notes") or ""
    currency = inputs.get("currency") or "INR"
    today = date.today().isoformat()

    if isinstance(payment_terms, str):
        payment_terms = [t.strip() for t in payment_terms.split(";") if t.strip()] or DEFAULT_PAYMENT_TERMS

    parts: list[str] = []
    parts.append(f"# Proposal for {name}")
    parts.append("")
    parts.append(f"*Prepared by {CONFIG.agency_name} — {today}*")
    parts.append("")
    if industry:
        parts.append(f"**Industry:** {industry}")
    parts.append(f"**Recommended package:** {package}")
    parts.append(f"**Add-ons:** {add_ons}")
    parts.append(f"**Timeline:** {timeline}")
    if price is not None:
        parts.append(f"**Investment:** {currency} {price:,}".rstrip("0").rstrip(".") if isinstance(price, (int, float)) else f"**Investment:** {price}")
    parts.append(f"**Support plan:** {support_plan}")
    parts.append("")
    parts.append("## What you get")
    parts.append("- Premium website tailored to your brand")
    parts.append("- Clear enquiry capture and follow-up flow")
    parts.append("- Lightweight automations (WhatsApp / Google Sheets / CRM sync)")
    parts.append("- Analytics + lead source tracking")
    parts.append("")
    parts.append("## How we work")
    parts.append("1. Brand + structure brief (1 short call)")
    parts.append("2. Design + copy draft for review")
    parts.append("3. Build + automations wired up")
    parts.append("4. Launch + handover + support kickoff")
    parts.append("")
    parts.append("## Payment terms")
    for t in payment_terms:
        parts.append(f"- {t}")
    parts.append("")
    if notes:
        parts.append("## Notes")
        parts.append(notes)
        parts.append("")
    parts.append("---")
    parts.append(
        f"**Contact**  \n{CONFIG.founder_name}  \n{CONFIG.agency_name}  \n"
        f"{CONFIG.founder_email}  \n{CONFIG.agency_domain}"
    )
    return "\n".join(parts) + "\n"


HTML_WRAPPER = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Proposal — {title}</title>
<style>
  :root {{
    --bg: #ffffff;
    --ink: #0f172a;
    --muted: #475569;
    --brand: #1f4e78;
    --accent: #0ea5e9;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: var(--ink); background: var(--bg);
    margin: 0; padding: 48px;
    max-width: 820px; margin: 0 auto;
    line-height: 1.55;
  }}
  h1 {{ color: var(--brand); margin-bottom: 4px; }}
  h2 {{ color: var(--brand); margin-top: 32px; border-bottom: 2px solid var(--accent); padding-bottom: 6px; }}
  .meta {{ color: var(--muted); margin-bottom: 24px; }}
  ul, ol {{ padding-left: 22px; }}
  li {{ margin: 4px 0; }}
  hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 32px 0; }}
  .footer {{ color: var(--muted); font-size: 14px; }}
  @media print {{
    body {{ padding: 24px; max-width: 100%; }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def _md_to_html(md_text: str) -> str:
    # extremely small markdown-to-HTML — enough for our structured proposal
    lines = md_text.splitlines()
    out: list[str] = []
    in_list: str | None = None
    for line in lines:
        s = line.rstrip()
        if not s:
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            out.append("")
            continue
        if s.startswith("# "):
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            out.append(f"<h1>{_html.escape(s[2:])}</h1>")
            continue
        if s.startswith("## "):
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            out.append(f"<h2>{_html.escape(s[3:])}</h2>")
            continue
        if s == "---":
            if in_list:
                out.append(f"</{in_list}>")
                in_list = None
            out.append("<hr/>")
            continue
        if s.startswith("- "):
            if in_list != "ul":
                if in_list:
                    out.append(f"</{in_list}>")
                out.append("<ul>")
                in_list = "ul"
            out.append(f"<li>{_inline_md(s[2:])}</li>")
            continue
        if re.match(r"^\d+\.\s", s):
            if in_list != "ol":
                if in_list:
                    out.append(f"</{in_list}>")
                out.append("<ol>")
                in_list = "ol"
            out.append(f"<li>{_inline_md(s.split('. ', 1)[1])}</li>")
            continue
        # paragraph
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None
        out.append(f"<p>{_inline_md(s)}</p>")
    if in_list:
        out.append(f"</{in_list}>")
    return "\n".join(out)


def _inline_md(text: str) -> str:
    s = _html.escape(text)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
    s = s.replace("  \n", "<br/>")
    return s


def generate_proposal(inputs: dict[str, Any], *, make_pdf: bool = False) -> dict[str, Path]:
    """Build proposal artifacts and persist them. Returns paths dict."""
    if not inputs.get("client_name"):
        raise ValueError("client_name is required")

    md_text = _md(inputs)
    html_body = _md_to_html(md_text)
    html_text = HTML_WRAPPER.format(
        title=_html.escape(inputs["client_name"]),
        body=html_body,
    )

    slug = _slug(inputs["client_name"])
    day = date.today().isoformat()
    md_path = data_path("proposals", f"proposal_{slug}_{day}.md")
    html_path = data_path("proposals", f"proposal_{slug}_{day}.html")

    md_path.write_text(md_text, encoding="utf-8")
    html_path.write_text(html_text, encoding="utf-8")

    pdf_path: Path | None = None
    if make_pdf:
        try:
            from weasyprint import HTML
            pdf_path = data_path("proposals", f"proposal_{slug}_{day}.pdf")
            HTML(string=html_text).write_pdf(str(pdf_path))
        except Exception as exc:
            log.warning("PDF render skipped: %s", exc)
            pdf_path = None

    with cursor() as cur:
        cur.execute(
            "INSERT INTO proposals (client_name, industry, package, add_ons, timeline, price, "
            "support_plan, payment_terms, notes, md_path, html_path, pdf_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                inputs.get("client_name"), inputs.get("industry"), inputs.get("package"),
                str(inputs.get("add_ons") or ""), inputs.get("timeline"),
                inputs.get("price"), inputs.get("support_plan"),
                "; ".join(inputs.get("payment_terms") or DEFAULT_PAYMENT_TERMS),
                inputs.get("notes"),
                str(md_path), str(html_path), str(pdf_path) if pdf_path else None,
            ),
        )

    out: dict[str, Path] = {"md": md_path, "html": html_path}
    if pdf_path:
        out["pdf"] = pdf_path
    return out
