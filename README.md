# KzVisaBot

Бот-наблюдатель за доступными датами записи на собеседование на сайте `ais.usvisa-info.com`.

Текущий статус проекта: **MVP** — логинится через Selenium, читает календарь доступных дат и шлёт уведомления в Telegram при появлении новых дат. Автоматическая запись (booking) по ТЗ пока **не реализована**.

## Архитектура (как работает)

Поток выполнения:

1. `main.py` — CLI-точка входа.
2. `visa-bot.config.load_settings()` — читает переменные окружения (`.env`) и собирает `Settings`.
3. `visa-bot.worker` — основной цикл:
   - запускает Selenium (Chrome);
   - выполняет логин на сайт;
   - открывает страницу записи и парсит календарь доступных дат;
   - сравнивает с последним сохранённым состоянием (`state.json`);
   - при появлении новых дат отправляет сообщение в Telegram;
   - сохраняет новое состояние.

Ключевые внешние зависимости:
- **Selenium + ChromeDriver** (через `webdriver-manager`) — для работы с сайтом.
- **Telegram Bot API** (через `httpx`) — для уведомлений.
- **tenacity** — ретраи на случай временных сбоев сайта/браузера.

## Переменные окружения (.env)

По умолчанию приложение **не читает `.env` автоматически** (это упрощает деплой и делает тесты изолированными).

Варианты:
- На хостинге (Docker/compose) обычно достаточно передать переменные окружения через `env_file:` / `--env-file`.
- Для локальной разработки можно включить автозагрузку `.env` установив `LOAD_DOTENV=1`.
- Либо явно передать путь: `load_settings(dotenv_path=...)` (используется в тестах).

Шаблон переменных см. в `.env.example`.

Обязательные:
- `VISA_USERNAME`
- `VISA_PASSWORD`
- `COUNTRY_CODE`
- `SCHEDULE_ID`
- `APPOINTMENTS_CONSULATE_APPOINTMENT_FACILITY_ID`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` — один chat_id или список через запятую (например: `12345,-1001234567890`).

Необязательные:
- `TELEGRAM_ADMIN_CHAT_ID` — chat_id, который будет получать **копию всех сообщений**, а также уведомления о штатном состоянии `BusyError` ("система занята").

## Назначение файлов и модулей

### Корень проекта

- `main.py`
  - Точка входа.
  - Флаг `--once` выполняет одну проверку и завершает работу, без флага — бесконечный цикл.

- `pyproject.toml`
  - Метаданные проекта и зависимости (selenium, webdriver-manager, python-dotenv, httpx, tenacity).

- `uv.lock`
  - Lock-файл зависимостей для `uv`.

- `Technical_Specification.md`
  - Техническое задание/цели (в т.ч. автоматическая запись, ограничения по датам, антибот-защита).

- `.env` (не в репозитории/или может быть локальный)
  - Переменные окружения для запуска (логин/пароль, schedule id, facility id, токен Telegram и т.д.).

### Пакет `visa-bot/`

- `visa-bot/__init__.py`
  - Маркер пакета.

- `visa-bot/config.py`
  - `Settings` (dataclass) и `load_settings()`.
  - Валидация обязательных env-переменных.
  - Настройки интервала, headless-режима и пути к state-файлу.

- `visa-bot/domain.py`
  - Доменнные модели.
  - `Slot` — доступная дата (YYYY-MM-DD) + `facility_id`.

- `visa-bot/worker.py`
  - Оркестрация процесса проверки.
  - `run_check_once()` — один проход: получить слоты → сравнить с прошлым → уведомить → сохранить.
  - `run_forever()` — бесконечный цикл с паузой `CHECK_INTERVAL_SECONDS`.
  - Ретраи (`tenacity`) для одного прохода `_run_check_once_with_retry()`.

- `visa-bot/selenium_provider.py`
  - Вся работа с Selenium:
    - сбор URL (`build_sign_in_url`, `build_appointments_url`);
    - запуск Chrome (`start_driver`);
    - логин (`log_in`);
    - выбор консульства/facility (`_select_facility`);
    - парсинг календаря jQuery UI datepicker (`fetch_available_slots`).
  - Есть обработка частых проблем: «система занята», таймауты, падение DevTools, сохранение debug html/png при таймауте.

- `visa-bot/state_file.py`
  - Хранение “последний раз видели такие слоты” в JSON.
  - `load_slots()` — читает `state.json`, битый JSON не ломает воркер.
  - `save_slots()` — атомарная запись через временный файл.

- `visa-bot/telegram_notifier.py`
  - Отправка сообщений в Telegram (`send_telegram_message`) через Bot API.

## Запуск на хостинге (Docker)

Для MVP достаточно **Dockerfile** (один контейнер). `docker-compose.yml` добавлен для удобства деплоя на VPS: он просто собирает образ, прокидывает `.env` и монтирует volume для `state.json`.

### Что важно для продакшена

- Секреты (логин/пароль, токен Telegram) храните **в `.env` на сервере** или в секрет-хранилище хостинга.
- Состояние хранится в `STATE_FILE` (по умолчанию `/app/data/state.json`). Для сохранения состояния между перезапусками монтируйте `./data:/app/data`.
- Selenium использует Chrome внутри контейнера. `webdriver-manager` скачивает chromedriver при первом старте и кэширует его в `/app/.wdm` (тоже смонтирован как volume).

### Вариант 1: Docker Compose (рекомендуется для VPS)

1) Скопируйте `.env.example` в `.env` и заполните значения.
2) Поднимите сервис через compose.

Команды (на сервере, из корня проекта):

```bash
docker compose up --build -d
```

Полезные команды:

```bash
docker compose ps
docker compose logs -f --tail=200
docker compose restart
docker compose down
```

Контейнер по умолчанию работает в режиме 24/7 (внутри бесконечный цикл `run_forever`). Если нужен одиночный прогон, используйте `python main.py --once` (например, внутри контейнера через `docker compose run --rm kzvisabot python main.py --once`).

### Вариант 2: Только Dockerfile (без compose)

Можно собрать и запускать контейнер напрямую, но тогда не забудьте:
- передать переменные окружения (`--env-file`),
- смонтировать `data/` для `STATE_FILE`.
