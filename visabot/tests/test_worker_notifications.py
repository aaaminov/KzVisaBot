from __future__ import annotations

from unittest.mock import patch

import pytest

from visabot.config import Settings
from visabot.domain import BusyError, Slot
from visabot.worker import run_check_once


def _settings(*, admin_chat_id: str | None = None, chat_ids: tuple[str, ...] = ("1", "2", "3")) -> Settings:
    # Минимально заполненный Settings, достаточный для run_check_once().
    # ВАЖНО: тесты не должны содержать реальные данные/токены/id и не должны отправлять сообщения в сеть.
    return Settings(
        visa_username="u",
        visa_password="p",
        country_code="ru-kz",
        schedule_id="71716653",
        facility_id=1,
        telegram_bot_token="TEST_TOKEN",
        telegram_chat_ids=chat_ids,
        telegram_admin_chat_id=admin_chat_id,
        check_interval_seconds=1,
        headless=True,
        check_retry_attempts=1,
        appointments_max_refresh_attempts=1,
        state_file=":memory:",
    )


def test_busy_error_without_admin_chat_does_not_send_telegram() -> None:
    settings = _settings(admin_chat_id=None)

    with (
        patch("visabot.worker._run_check_once_with_retry", side_effect=BusyError("busy")),
        patch("visabot.worker.send_telegram_message") as send_msg,
    ):
        run_check_once(settings)  # should not raise
        send_msg.assert_not_called()


def test_busy_error_with_admin_chat_sends_only_to_admin() -> None:
    settings = _settings(admin_chat_id="999")

    with (
        patch("visabot.worker._run_check_once_with_retry", side_effect=BusyError("busy")),
        patch("visabot.worker.send_telegram_message") as send_msg,
    ):
        run_check_once(settings)  # should not raise
        assert send_msg.call_count == 1
        assert send_msg.call_args.kwargs["chat_id"] == "999"


def test_real_error_sends_telegram_and_reraises() -> None:
    settings = _settings(admin_chat_id=None)

    with (
        patch("visabot.worker._run_check_once_with_retry", side_effect=RuntimeError("boom")),
        patch("visabot.worker.send_telegram_message") as send_msg,
    ):
        with pytest.raises(RuntimeError):
            run_check_once(settings)
        assert send_msg.call_count == len(settings.telegram_chat_ids)


def test_real_error_is_duplicated_to_admin_chat() -> None:
    settings = _settings(admin_chat_id="999")

    with (
        patch("visabot.worker._run_check_once_with_retry", side_effect=RuntimeError("boom")),
        patch("visabot.worker.send_telegram_message") as send_msg,
    ):
        with pytest.raises(RuntimeError):
            run_check_once(settings)
        assert send_msg.call_count == len(settings.telegram_chat_ids) + 1


def test_real_error_admin_chat_is_deduplicated_when_already_in_chat_ids() -> None:
    settings = _settings(admin_chat_id="2", chat_ids=("1", "2", "3"))

    with (
        patch("visabot.worker._run_check_once_with_retry", side_effect=RuntimeError("boom")),
        patch("visabot.worker.send_telegram_message") as send_msg,
    ):
        with pytest.raises(RuntimeError):
            run_check_once(settings)
        assert send_msg.call_count == len(settings.telegram_chat_ids)


def test_new_slots_send_telegram() -> None:
    settings = _settings(admin_chat_id=None)

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


def test_new_slots_are_duplicated_to_admin_chat() -> None:
    settings = _settings(admin_chat_id="999")

    current = {Slot(date_iso="2025-01-01", facility_id=1)}

    with (
        patch("visabot.worker._run_check_once_with_retry", return_value=current),
        patch("visabot.worker.load_slots", return_value=set()),
        patch("visabot.worker.save_slots") as save_slots,
        patch("visabot.worker.send_telegram_message") as send_msg,
    ):
        run_check_once(settings)
        assert send_msg.call_count == len(settings.telegram_chat_ids) + 1
        save_slots.assert_called_once()
