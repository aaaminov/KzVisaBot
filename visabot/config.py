from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    visa_username: str
    visa_password: str
    country_code: str
    schedule_id: str
    facility_id: int

    telegram_bot_token: str
    telegram_chat_id: str

    check_interval_seconds: int = 300
    headless: bool = True

    # Where we store last seen slots
    state_file: str = "state.json"


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_settings(dotenv_path: str | None = None) -> Settings:
    # Prefer .env in repo root; dotenv_path allows overriding in tests.
    load_dotenv(dotenv_path=dotenv_path, override=False)

    check_interval_seconds = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
    headless_raw = os.getenv("HEADLESS", "1").strip().lower()
    headless = headless_raw not in {"0", "false", "no"}

    state_file = os.getenv("STATE_FILE", "state.json")

    return Settings(
        visa_username=_require("VISA_USERNAME"),
        visa_password=_require("VISA_PASSWORD"),
        country_code=_require("COUNTRY_CODE"),
        schedule_id=_require("SCHEDULE_ID"),
        facility_id=int(_require("APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID")),
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_require("TELEGRAM_CHAT_ID"),
        check_interval_seconds=check_interval_seconds,
        headless=headless,
        state_file=state_file,
    )

