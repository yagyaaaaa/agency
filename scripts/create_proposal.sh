#!/usr/bin/env bash
# Create a proposal. Usage:
#   scripts/create_proposal.sh "Client Name" pro 34999 "Add-on1,Add-on2" [industry]
set -euo pipefail
cd "$(dirname "$0")/.."
name="${1:?client name required}"
pkg="${2:-pro}"
price="${3:-34999}"
addons="${4:-}"
industry="${5:-}"

python - <<PY
from src.db import init_db
init_db()
from src.proposal.generator import generate_proposal
out = generate_proposal({
    "client_name": "$name",
    "industry": "$industry",
    "package": "$pkg",
    "add_ons": "$addons",
    "timeline": "3–5 weeks",
    "price": $price,
    "support_plan": "Standard monthly support",
    "notes": "",
}, make_pdf=True)
print(out)
from src.telegram.notify import send_document, send_message
send_message(f"Proposal created for $name ($pkg) — ₹$price")
for kind, path in out.items():
    send_document(path, caption=f"{kind.upper()} — $name")
PY
