"""Centralized config loader. Reads .env (via python-dotenv) and exposes typed accessors."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Packages:
    starter_one_time: int = _int("PKG_STARTER_ONE_TIME", 14999)
    starter_monthly: int = _int("PKG_STARTER_MONTHLY", 3499)
    pro_one_time: int = _int("PKG_PRO_ONE_TIME", 34999)
    pro_monthly: int = _int("PKG_PRO_MONTHLY", 5999)
    enterprise_one_time: int = _int("PKG_ENTERPRISE_ONE_TIME", 79999)
    enterprise_monthly: int = _int("PKG_ENTERPRISE_MONTHLY", 9999)

    usd_launch_min: int = _int("USD_LAUNCH_MIN", 499)
    usd_launch_max: int = _int("USD_LAUNCH_MAX", 799)
    usd_growth_min: int = _int("USD_GROWTH_MIN", 1200)
    usd_growth_max: int = _int("USD_GROWTH_MAX", 2500)
    usd_infra_min: int = _int("USD_INFRA_MIN", 3000)
    usd_infra_max: int = _int("USD_INFRA_MAX", 7500)


@dataclass(frozen=True)
class Config:
    founder_name: str = os.getenv("FOUNDER_NAME", "Yagya Chauhan")
    founder_email: str = os.getenv("FOUNDER_EMAIL_PRIMARY", "connect@quantumreach.tech")
    founder_email_personal: str = os.getenv("FOUNDER_EMAIL_PERSONAL", "yagya@quantumreach.tech")
    agency_name: str = os.getenv("AGENCY_NAME", "QuantumReach")
    agency_domain: str = os.getenv("AGENCY_DOMAIN", "quantumreach.tech")
    timezone: str = os.getenv("TIMEZONE", "Asia/Kolkata")

    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    telegram_admin_ids: str = os.getenv("TELEGRAM_ADMIN_USER_IDS", "")

    sqlite_path: str = os.getenv("SQLITE_PATH", str(Path("data/db/agency.sqlite").resolve()))
    data_dir: str = os.getenv("DATA_DIR", str(Path("data").resolve()))

    enable_scheduler: bool = _bool("ENABLE_SCHEDULER", True)
    enable_telegram_bot: bool = _bool("ENABLE_TELEGRAM_BOT", True)
    email_send_enabled: bool = _bool("EMAIL_SEND_ENABLED", False)

    email_from_name: str = os.getenv("EMAIL_FROM_NAME", "Yagya — QuantumReach")
    email_reply_to: str = os.getenv("EMAIL_REPLY_TO", "connect@quantumreach.tech")

    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    packages: Packages = Packages()

    @property
    def admin_ids_list(self) -> list[int]:
        raw = self.telegram_admin_ids
        out: list[int] = []
        for chunk in raw.replace(";", ",").split(","):
            chunk = chunk.strip()
            if chunk.isdigit():
                out.append(int(chunk))
        return out


CONFIG = Config()


def data_path(*parts: str) -> Path:
    p = Path(CONFIG.data_dir).joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
