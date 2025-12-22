from __future__ import annotations

import os

import pytest

from visabot.config import load_settings


def test_load_settings_parses_multiple_telegram_chat_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    # Required env
    monkeypatch.setenv("VISA_USERNAME", "u")
    monkeypatch.setenv("VISA_PASSWORD", "p")
    monkeypatch.setenv("COUNTRY_CODE", "ru-kz")
    monkeypatch.setenv("SCHEDULE_ID", "1")
    monkeypatch.setenv("APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID", "134")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")

    # Chat ids (csv) with spaces, duplicates and empty parts.
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1, 2,2,, -1003, 1")

    settings = load_settings(dotenv_path=None)
    assert settings.telegram_chat_ids == ("1", "2", "-1003")


def test_load_settings_admin_chat_id_is_optional(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VISA_USERNAME", "u")
    monkeypatch.setenv("VISA_PASSWORD", "p")
    monkeypatch.setenv("COUNTRY_CODE", "ru-kz")
    monkeypatch.setenv("SCHEDULE_ID", "1")
    monkeypatch.setenv("APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID", "134")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    settings = load_settings(dotenv_path=None)
    assert settings.telegram_admin_chat_id is None


def test_load_settings_rejects_non_integer_admin_telegram_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VISA_USERNAME", "u")
    monkeypatch.setenv("VISA_PASSWORD", "p")
    monkeypatch.setenv("COUNTRY_CODE", "ru-kz")
    monkeypatch.setenv("SCHEDULE_ID", "1")
    monkeypatch.setenv("APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID", "134")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "abc")

    with pytest.raises(RuntimeError, match=r"Invalid TELEGRAM_ADMIN_CHAT_ID"):
        load_settings(dotenv_path=None)


def test_load_settings_rejects_zero_admin_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VISA_USERNAME", "u")
    monkeypatch.setenv("VISA_PASSWORD", "p")
    monkeypatch.setenv("COUNTRY_CODE", "ru-kz")
    monkeypatch.setenv("SCHEDULE_ID", "1")
    monkeypatch.setenv("APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID", "134")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_ID", "0")

    with pytest.raises(RuntimeError, match=r"not a valid chat id"):
        load_settings(dotenv_path=None)


def test_load_settings_rejects_empty_telegram_chat_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VISA_USERNAME", "u")
    monkeypatch.setenv("VISA_PASSWORD", "p")
    monkeypatch.setenv("COUNTRY_CODE", "ru-kz")
    monkeypatch.setenv("SCHEDULE_ID", "1")
    monkeypatch.setenv("APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID", "134")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")

    monkeypatch.setenv("TELEGRAM_CHAT_ID", " , ,")

    with pytest.raises(RuntimeError, match=r"TELEGRAM_CHAT_ID is empty"):
        load_settings(dotenv_path=None)


def test_load_settings_rejects_non_integer_telegram_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VISA_USERNAME", "u")
    monkeypatch.setenv("VISA_PASSWORD", "p")
    monkeypatch.setenv("COUNTRY_CODE", "ru-kz")
    monkeypatch.setenv("SCHEDULE_ID", "1")
    monkeypatch.setenv("APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID", "134")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")

    monkeypatch.setenv("TELEGRAM_CHAT_ID", "abc")

    with pytest.raises(RuntimeError, match=r"Invalid TELEGRAM_CHAT_ID"):
        load_settings(dotenv_path=None)


def test_load_settings_rejects_zero_chat_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VISA_USERNAME", "u")
    monkeypatch.setenv("VISA_PASSWORD", "p")
    monkeypatch.setenv("COUNTRY_CODE", "ru-kz")
    monkeypatch.setenv("SCHEDULE_ID", "1")
    monkeypatch.setenv("APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID", "134")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")

    monkeypatch.setenv("TELEGRAM_CHAT_ID", "0")

    with pytest.raises(RuntimeError, match=r"not a valid chat id"):
        load_settings(dotenv_path=None)


def test_load_settings_does_not_override_existing_env_with_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    # This protects us from a subtle test pollution: load_dotenv(override=False)
    # should not overwrite already-set env vars.
    monkeypatch.setenv("VISA_USERNAME", "u")
    monkeypatch.setenv("VISA_PASSWORD", "p")
    monkeypatch.setenv("COUNTRY_CODE", "ru-kz")
    monkeypatch.setenv("SCHEDULE_ID", "1")
    monkeypatch.setenv("APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID", "134")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    dotenv = tmp_path / ".env"
    dotenv.write_text("TELEGRAM_CHAT_ID=999\n")

    settings = load_settings(dotenv_path=str(dotenv))
    assert settings.telegram_chat_ids == ("1",)
