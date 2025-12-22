from __future__ import annotations

from unittest.mock import patch

import pytest

from visabot.config import Settings
from visabot.domain import BusyError, Slot
from visabot.worker import run_check_once


def _settings() -> Settings:
    # Минимально заполненный Settings, достаточный для run_check_once().
    # ВАЖНО: тесты не должны содержать реальные данные/токены/id и не должны отправлять сообщения в сеть.
    return Settings(
        visa_username="u",
        visa_password="p",
        country_code="ru-kz",
        schedule_id="71716653",
        facility_id=1,
        telegram_bot_token="TEST_TOKEN",
        telegram_chat_ids=("1", "2", "3"),
        check_interval_seconds=1,
        headless=True,
        check_retry_attempts=1,
        appointments_max_refresh_attempts=1,
        state_file=":memory:",
    )


def test_busy_error_does_not_send_telegram() -> None:
    settings = _settings()

    with (
        patch("visabot.worker._run_check_once_with_retry", side_effect=BusyError("busy")),
        patch("visabot.worker.send_telegram_message") as send_msg,
    ):
        run_check_once(settings)  # should not raise
        send_msg.assert_not_called()


def test_real_error_sends_telegram_and_reraises() -> None:
    settings = _settings()

    with (
        patch("visabot.worker._run_check_once_with_retry", side_effect=RuntimeError("boom")),
        patch("visabot.worker.send_telegram_message") as send_msg,
    ):
        with pytest.raises(RuntimeError):
            run_check_once(settings)
        assert send_msg.call_count == len(settings.telegram_chat_ids)


def test_new_slots_send_telegram() -> None:
    settings = _settings()

    current = {Slot(date_iso="2025-01-01", facility_id=1)}

    with (
        patch("visabot.worker._run_check_once_with_retry", return_value=current),
        patch("visabot.worker.load_slots", return_value=set()),
        patch("visabot.worker.save_slots") as save_slots,
        patch("visabot.worker.send_telegram_message") as send_msg,
    ):
        run_check_once(settings)
        assert send_msg.call_count == len(settings.telegram_chat_ids)
        save_slots.assert_called_once()
