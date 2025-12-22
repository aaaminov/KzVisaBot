import argparse
import logging

from visabot.config import load_settings
from visabot.worker import run_check_once, run_forever


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

    if args.once:
        run_check_once(settings)
        return 0

    run_forever(settings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
