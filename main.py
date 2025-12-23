import argparse
import logging

from visabot.config import load_settings
from visabot.worker import run_check_once, run_forever, _send_status_message


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="KzVisaBot: visa slot watcher")
    parser.add_argument("--once", action="store_true", help="Run single check and exit")
    args = parser.parse_args()

    _setup_logging()
    settings = load_settings()

    # Уведомление о старте (best-effort)
    try:
        _send_status_message(
            settings,
            text=(
                "KzVisaBot запущен.\n"
                f"Режим: {'once' if args.once else 'forever'}\n"
                f"headless={settings.headless} interval={settings.check_interval_seconds}s"
            ),
        )
    except Exception:
        logging.getLogger(__name__).warning("Failed to send Telegram startup message", exc_info=True)

    try:
        if args.once:
            run_check_once(settings)
            return 0

        run_forever(settings)
        return 0

    except Exception as e:
        # Уведомление о краше (best-effort)
        try:
            _send_status_message(
                settings,
                text=(
                    "KzVisaBot завершился с ошибкой.\n"
                    f"Причина: {type(e).__name__}: {e}"
                ),
            )
        except Exception:
            logging.getLogger(__name__).warning("Failed to send Telegram crash message", exc_info=True)
        raise

    finally:
        # Уведомление о выходе/остановке процесса (best-effort)
        try:
            _send_status_message(settings, text="KzVisaBot остановлен (выход из процесса).")
        except Exception:
            logging.getLogger(__name__).warning("Failed to send Telegram shutdown message", exc_info=True)


if __name__ == "__main__":
    raise SystemExit(main())
