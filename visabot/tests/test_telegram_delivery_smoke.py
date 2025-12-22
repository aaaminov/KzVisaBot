"""Smoke/integration test for Telegram delivery.

ВАЖНО:
- Этот тест обращается в реальный Telegram API.
- По умолчанию тест пропускается.
- Для запуска установите переменные окружения:
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID

Запуск:
$env:TELEGRAM_BOT_TOKEN="123"
$env:TELEGRAM_CHAT_ID="123"
python -m pytest -q -m telegram

"""

from __future__ import annotations

import os

import pytest

from visabot.telegram_notifier import send_telegram_message


pytestmark = pytest.mark.telegram


@pytest.mark.skipif(
    not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"),
    reason="Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to run Telegram smoke test",
)
def test_telegram_message_delivery_smoke() -> None:
    send_telegram_message(
        bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        chat_id=os.environ["TELEGRAM_CHAT_ID"],
        text="KzVisaBot: Telegram smoke test (pytest)",
    )

