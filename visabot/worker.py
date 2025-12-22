from __future__ import annotations

import logging
import time
from typing import Iterable

from tenacity import RetryCallState, retry, stop_after_attempt, wait_exponential

from visabot.config import Settings
from visabot.domain import Slot, BusyError
from visabot.selenium_provider import (
    build_appointments_url,
    build_sign_in_url,
    fetch_available_slots,
    log_in,
    start_driver,
)
from visabot.state_file import load_slots, save_slots
from visabot.telegram_notifier import send_telegram_message

logger = logging.getLogger(__name__)


def _format_slots(slots: Iterable[Slot]) -> str:
    by_date = sorted(slots, key=lambda s: (s.date_iso, s.facility_id))
    return "\n".join([f"• {s.date_iso} (facility_id={s.facility_id})" for s in by_date])


def _broadcast_telegram(settings: Settings, text: str) -> None:
    errors: list[tuple[str, Exception]] = []

    for chat_id in settings.telegram_chat_ids:
        try:
            send_telegram_message(
                bot_token=settings.telegram_bot_token,
                chat_id=chat_id,
                text=text,
            )
        except Exception as e:
            # Best-effort: don't stop sending to other chat_ids.
            logger.warning("Failed to send telegram message to chat_id=%s (%s: %s)", chat_id, type(e).__name__, e)
            errors.append((chat_id, e))

    if errors:
        # Keep behavior explicit: if at least one send failed, raise.
        # This is safer for monitoring; caller may catch.
        failed = ", ".join([cid for cid, _ in errors])
        raise RuntimeError(f"Failed to send telegram message to some recipients: {failed}")


def _send_status_message(settings: Settings, text: str) -> None:
    # Статусные сообщения полезны для контроля, но могут спамить.
    # Если захочешь — легко выключим через env-флаг.
    _broadcast_telegram(settings, text)


def _short_exc(retry_state: RetryCallState) -> str | None:
    if retry_state.outcome is None or not retry_state.outcome.failed:
        return None
    exc = retry_state.outcome.exception()
    if exc is None:
        return None
    # Без стектрейса: только тип и сообщение, чтобы не спамить между попытками.
    msg = str(exc).strip()
    return f"{type(exc).__name__}: {msg}" if msg else type(exc).__name__


def _log_before_attempt(retry_state: RetryCallState) -> None:
    logger.info("Попытка %s: старт", retry_state.attempt_number)


def _log_after_attempt(retry_state: RetryCallState) -> None:
    # after вызывается в конце каждой попытки (и успешной, и неуспешной)
    if retry_state.outcome is not None and retry_state.outcome.failed:
        reason = _short_exc(retry_state)
        if reason:
            logger.warning("Попытка %s: ошибка (%s)", retry_state.attempt_number, reason)
        else:
            logger.warning("Попытка %s: ошибка", retry_state.attempt_number)


def _log_before_sleep(retry_state: RetryCallState) -> None:
    sleep_seconds = getattr(retry_state.next_action, "sleep", None)
    next_attempt = retry_state.attempt_number + 1
    reason = _short_exc(retry_state)

    if sleep_seconds is None:
        if reason:
            logger.info("Перед следующей попыткой ждём паузу... (причина: %s)", reason)
        else:
            logger.info("Перед следующей попыткой ждём паузу...")
        return

    if reason:
        logger.info(
            "Перед попыткой %s пауза %.0f сек. (причина: %s)",
            next_attempt,
            sleep_seconds,
            reason,
        )
    else:
        logger.info("Перед попыткой %s пауза %.0f сек.", next_attempt, sleep_seconds)


def _run_check_once(settings: Settings) -> set[Slot]:
    sign_in_url = build_sign_in_url(settings.country_code)
    appointments_url = build_appointments_url(settings.country_code, settings.schedule_id)

    logger.info("Starting browser (headless=%s)", settings.headless)
    driver = start_driver(headless=settings.headless)

    try:
        logger.info("Logging in: %s", sign_in_url)
        log_in(
            driver,
            sign_in_url=sign_in_url,
            username=settings.visa_username,
            password=settings.visa_password,
        )

        logger.info("Fetching available slots: %s", appointments_url)
        return fetch_available_slots(
            driver,
            appointments_url=appointments_url,
            facility_id=settings.facility_id,
            max_refresh_attempts=settings.appointments_max_refresh_attempts,
        )
    finally:
        try:
            driver.quit()
        except Exception:
            logger.warning("Failed to quit driver cleanly", exc_info=True)


def _run_check_once_with_retry(settings: Settings) -> set[Slot]:
    decorated = retry(
        stop=stop_after_attempt(settings.check_retry_attempts),
        wait=wait_exponential(multiplier=2, min=2, max=4),
        before=_log_before_attempt,
        after=_log_after_attempt,
        before_sleep=_log_before_sleep,
        reraise=True,
    )(_run_check_once)

    return decorated(settings)


def run_check_once(settings: Settings) -> None:
    appointments_url = build_appointments_url(settings.country_code, settings.schedule_id)

    try:
        current = _run_check_once_with_retry(settings)

        previous = load_slots(settings.state_file)
        new_slots = set(current) - set(previous)

        logger.info("Slots: current=%d previous=%d new=%d", len(current), len(previous), len(new_slots))

        # По требованию: если календарь появился (а значит мы получили current), можно уведомлять.
        # Но чтобы не спамить, минимально продолжаем уведомлять только при появлении новых дат,
        # а при отсутствии новых дат отправляем статус (как было раньше).
        if new_slots:
            text = (
                "Появились новые свободные даты на собеседование:\n\n"
                f"{_format_slots(new_slots)}\n\n"
                f"Ссылка: {appointments_url}"
            )
            _broadcast_telegram(settings, text)
            logger.info("Telegram notification sent.")
        else:
            _send_status_message(
                settings,
                text=(
                    "Проверка выполнена: новых свободных дат не найдено.\n"
                    f"Текущее количество дат в календаре: {len(current)}\n"
                    f"Ссылка: {appointments_url}"
                ),
            )

        save_slots(settings.state_file, current)
        logger.info("State saved to %s", settings.state_file)

    except BusyError as e:
        # Штатное состояние сайта. В Telegram не шлём.
        logger.info("Site is busy, skipping notification (%s)", e)
        return

    except Exception as e:
        # Стектрейс не логируем, чтобы не засорять логи
        logger.error("Check failed (%s: %s)", type(e).__name__, e)
        try:
            _send_status_message(
                settings,
                text=(
                    "Проверка НЕ удалась (ошибка при получении календаря/слотов).\n"
                    f"Причина: {type(e).__name__}: {e}\n"
                    f"Ссылка: {appointments_url}"
                ),
            )
        except Exception:
            logger.warning("Failed to send telegram status message", exc_info=True)
        raise


def run_forever(settings: Settings) -> None:
    logger.info("Worker started. Interval=%ss", settings.check_interval_seconds)
    while True:
        try:
            run_check_once(settings)
        except Exception as e:
            # Не дублируем полный traceback: он уже залогирован в run_check_once().
            logger.error("Check failed in run_forever (%s: %s)", type(e).__name__, e)
        time.sleep(settings.check_interval_seconds)
