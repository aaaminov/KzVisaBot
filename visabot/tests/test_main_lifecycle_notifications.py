from __future__ import annotations

from unittest.mock import patch

import pytest

import main
from visabot.config import Settings


def _settings() -> Settings:
    return Settings(
        visa_username="u",
        visa_password="p",
        country_code="ru-kz",
        schedule_id="71716653",
        facility_id=1,
        telegram_bot_token="TEST_TOKEN",
        telegram_chat_ids=("1", "2"),
        telegram_admin_chat_id=None,
        check_interval_seconds=1,
        headless=True,
        check_retry_attempts=1,
        appointments_max_refresh_attempts=1,
        state_file=":memory:",
    )


def test_main_sends_start_and_shutdown_messages_in_once_mode() -> None:
    settings = _settings()

    with (
        patch("main.load_settings", return_value=settings),
        patch("main.run_check_once") as run_once,
        patch("main._send_status_message") as send_status,
        patch("main.argparse.ArgumentParser.parse_args", return_value=type("Args", (), {"once": True})()),
    ):
        assert main.main() == 0
        run_once.assert_called_once_with(settings)

        # startup + shutdown
        assert send_status.call_count == 2
        assert "KzVisaBot запущен" in send_status.call_args_list[0].kwargs["text"]
        assert "KzVisaBot остановлен" in send_status.call_args_list[1].kwargs["text"]


def test_main_sends_crash_and_shutdown_messages_on_error() -> None:
    settings = _settings()

    with (
        patch("main.load_settings", return_value=settings),
        patch("main.run_forever", side_effect=RuntimeError("boom")),
        patch("main._send_status_message") as send_status,
        patch("main.argparse.ArgumentParser.parse_args", return_value=type("Args", (), {"once": False})()),
    ):
        with pytest.raises(RuntimeError):
            main.main()

        # startup + crash + shutdown
        assert send_status.call_count == 3
        assert "KzVisaBot запущен" in send_status.call_args_list[0].kwargs["text"]
        assert "завершился с ошибкой" in send_status.call_args_list[1].kwargs["text"]
        assert "KzVisaBot остановлен" in send_status.call_args_list[2].kwargs["text"]

