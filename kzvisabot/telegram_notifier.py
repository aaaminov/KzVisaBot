from __future__ import annotations

import httpx


def send_telegram_message(*, bot_token: str, chat_id: str, text: str, timeout_seconds: float = 20.0) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    with httpx.Client(timeout=timeout_seconds) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok", False):
            raise RuntimeError(f"Telegram API error: {data}")

