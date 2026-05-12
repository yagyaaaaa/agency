"""Normalization helpers for de-duplication by email, domain, business name."""
from __future__ import annotations

import re
from urllib.parse import urlparse

_WS = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def norm_email(email: str | None) -> str:
    if not email:
        return ""
    return email.strip().lower()


def domain_from_email(email: str | None) -> str:
    e = norm_email(email)
    if "@" not in e:
        return ""
    return e.split("@", 1)[1]


def domain_from_url(url: str | None) -> str:
    if not url:
        return ""
    raw = url.strip().lower()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "http://" + raw
    try:
        host = urlparse(raw).hostname or ""
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def norm_business(name: str | None) -> str:
    if not name:
        return ""
    n = _WS.sub(" ", name.strip().lower())
    # collapse punctuation; keep word boundaries
    n = _NON_ALNUM.sub(" ", n).strip()
    # drop common suffixes
    for suffix in (" pvt ltd", " private limited", " ltd", " llp", " inc", " llc", " co", " studio", " studios"):
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return n
