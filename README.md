# KzVisaBot

Сервис-воркер для отслеживания свободных дат собеседования на сайте `ais.usvisa-info.com` и отправки уведомлений в Telegram.

## Быстрый старт (Windows)

1) Создайте файл `.env` в корне проекта (на основе `.env.example`) и заполните реальными значениями:

- `VISA_USERNAME`, `VISA_PASSWORD`
- `COUNTRY_CODE` (например `ru-kz`)
- `SCHEDULE_ID` (id записи в URL при попытке reschedule)
- `APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID` (134/135)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

Опционально:
- `CHECK_INTERVAL_SECONDS` (по умолчанию 300)
- `HEADLESS` (1/0)
- `STATE_FILE` (по умолчанию `state.json`)

2) Установите зависимости (проект использует `uv.lock`, но подойдёт и обычный pip).

3) Запуск одного прохода (смоук-тест):

- `python main.py --once`

4) Запуск 24/7 мониторинга:

- `python main.py`

## Важно про капчу / антибот

Сайт `ais.usvisa-info.com` может показывать Cloudflare/reCAPTCHA. В этом MVP мы не решаем капчу автоматически.
Если капча появляется часто, попробуйте:
- запускать не в headless (`HEADLESS=0`),
- увеличить интервалы проверки,
- использовать отдельный стабильный IP.
