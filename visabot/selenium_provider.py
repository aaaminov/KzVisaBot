from __future__ import annotations

import datetime as dt
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSessionIdException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait, Select
from webdriver_manager.chrome import ChromeDriverManager

from visabot.domain import Slot

BASE_URL = "https://ais.usvisa-info.com"


_MONTHS = {
    # English month names as used by jQuery UI datepicker
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _parse_date(day: str, month_name: str, year: str) -> dt.date:
    m = _MONTHS.get(month_name.strip().lower())
    if not m:
        raise ValueError(f"Unknown month name: {month_name}")
    return dt.date(int(year), m, int(day))


def build_sign_in_url(country_code: str) -> str:
    # e.g. ru-kz
    return f"{BASE_URL}/{country_code}/niv/users/sign_in"


def build_appointments_url(country_code: str, schedule_id: str) -> str:
    return f"{BASE_URL}/{country_code}/niv/schedule/{schedule_id}/appointment"


def start_driver(*, headless: bool) -> webdriver.Chrome:
    options = Options()
    # Keep it close to a real browser. Headless can be toggled via env.
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1200,900")
    # Часто помогает от 'not connected to DevTools' на Windows
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-features=Translate,BackForwardCache")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def log_in(driver: webdriver.Chrome, *, sign_in_url: str, username: str, password: str, wait_seconds: int = 60) -> None:
    driver.get(sign_in_url)

    # Cloudflare/captcha can appear; this MVP just waits for the form.
    wait = WebDriverWait(driver, wait_seconds)
    wait.until(EC.presence_of_element_located((By.NAME, "user[email]")))

    # Cookie consent sometimes appears
    try:
        ok_button = driver.find_element(By.XPATH, "/html/body/div[7]/div[3]/div/button")
        ok_button.click()
    except Exception:
        pass

    user_box = driver.find_element(By.NAME, "user[email]")
    user_box.clear()
    user_box.send_keys(username)

    password_box = driver.find_element(By.NAME, "user[password]")
    password_box.clear()
    password_box.send_keys(password)

    # Accept privacy policy checkbox
    driver.find_element(By.XPATH, '//*[@id="sign_in_form"]/div[3]/label/div').click()
    # Submit
    driver.find_element(By.XPATH, '//*[@id="sign_in_form"]/p[1]/input').click()

    wait.until(EC.url_changes(sign_in_url))


def _busy_message_present(driver: webdriver.Chrome) -> bool:
    # На странице иногда появляется баннер/текст: "Система занята. Пожалуйста, повторите попытку позже".
    # Ищем по подстроке, чтобы не быть привязанными к конкретной разметке.
    text = driver.page_source.lower()
    return "система занята" in text and "повторите попытку позже" in text


def _select_facility(driver: webdriver.Chrome, *, facility_id: int, wait_seconds: int = 30) -> None:
    """Выбирает 'Адрес консульского отдела' (facility).

    Важно: на странице appointment select может быть disabled до завершения загрузки.
    """

    wait = WebDriverWait(driver, wait_seconds)

    select_locator = (By.ID, "appointments_consulate_appointment_facility_id")
    wait.until(EC.presence_of_element_located(select_locator))
    wait.until(EC.element_to_be_clickable(select_locator))

    select_el = driver.find_element(*select_locator)
    select = Select(select_el)  # type: ignore[arg-type]

    def _has_option(_: object) -> bool:
        return any(o.get_attribute("value") == str(facility_id) for o in select.options)

    wait.until(_has_option)

    try:
        if select.first_selected_option.get_attribute("value") == str(facility_id):
            return
    except Exception:
        pass

    select.select_by_value(str(facility_id))
    driver.execute_script(
        "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
        select_el,
    )


def fetch_available_slots(
    driver: webdriver.Chrome,
    *,
    appointments_url: str,
    facility_id: int,
    months_ahead: int = 6,
    wait_seconds: int = 60,
) -> set[Slot]:
    driver.get(appointments_url)

    wait = WebDriverWait(driver, wait_seconds)

    date_input_id = "appointments_consulate_appointment_date"
    time_select_id = "appointments_consulate_appointment_time"

    def _date_widgets_exist() -> bool:
        # Элементы могут быть в DOM, но скрыты (display:none) — нам важно именно наличие.
        return bool(driver.find_elements(By.ID, date_input_id)) and bool(driver.find_elements(By.ID, time_select_id))

    def _open_datepicker_if_possible() -> None:
        # Календарь часто появляется только после клика по input даты.
        if not driver.find_elements(By.ID, date_input_id):
            return

        try:
            el = driver.find_element(By.ID, date_input_id)
            # Иногда обычный click не срабатывает из-за перекрытий/скрытия. Пробуем оба.
            try:
                el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", el)
            time.sleep(0.5)
        except Exception:
            return

    def _calendar_or_busy(_: object) -> bool:
        if _busy_message_present(driver):
            return True
        if driver.find_elements(By.CLASS_NAME, "ui-datepicker-group"):
            return True
        if _date_widgets_exist():
            _open_datepicker_if_possible()
            return bool(driver.find_elements(By.CLASS_NAME, "ui-datepicker-group"))
        return False

    # Основной цикл: выбираем консульство, затем ждём либо календарь, либо busy.
    # Если busy — обновляем страницу и повторяем.
    for attempt in range(1, 6):
        try:
            _select_facility(driver, facility_id=facility_id, wait_seconds=min(30, wait_seconds))

            # Ждём, пока появятся либо календарь, либо busy, либо хотя бы элементы даты/времени.
            try:
                wait.until(_calendar_or_busy)
            except TimeoutException:
                ts = int(time.time())
                try:
                    driver.save_screenshot(f"debug_appointments_{ts}.png")
                    with open(f"debug_appointments_{ts}.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                except Exception:
                    pass
                raise RuntimeError(
                    "Не дождались календаря/busy и не нашли элементы даты/времени. Сохранил debug_appointments_*.png/html в корень проекта."
                )

            if driver.find_elements(By.CLASS_NAME, "ui-datepicker-group"):
                break

            if _busy_message_present(driver):
                time.sleep(min(10, 2 * attempt))
                try:
                    driver.refresh()
                except (InvalidSessionIdException, WebDriverException) as e:
                    raise RuntimeError("Сессия браузера упала во время refresh (DevTools disconnect)") from e
                continue

            # Элементы даты/времени есть, но календарь не открылся — дадим шанс ещё раз.
            if _date_widgets_exist():
                _open_datepicker_if_possible()
                if driver.find_elements(By.CLASS_NAME, "ui-datepicker-group"):
                    break

                time.sleep(1)
                try:
                    driver.refresh()
                except (InvalidSessionIdException, WebDriverException) as e:
                    raise RuntimeError("Сессия браузера упала во время refresh (DevTools disconnect)") from e
                continue

            time.sleep(1)
            try:
                driver.refresh()
            except (InvalidSessionIdException, WebDriverException) as e:
                raise RuntimeError("Сессия браузера упала во время refresh (DevTools disconnect)") from e

        except (InvalidSessionIdException, WebDriverException) as e:
            raise RuntimeError("Сессия Selenium оборвалась (not connected to DevTools)") from e

    if _busy_message_present(driver):
        raise RuntimeError("Сайт вернул сообщение 'Система занята. Пожалуйста, повторите попытку позже'.")

    if not driver.find_elements(By.CLASS_NAME, "ui-datepicker-group"):
        raise RuntimeError(
            "Календарь не найден. Ожидали, что откроется после выбора консульства и клика по полю даты (appointments_consulate_appointment_date)."
        )

    slots: set[Slot] = set()

    current_month_index = 0
    while current_month_index < months_ahead:
        date_pickers = driver.find_elements(By.CLASS_NAME, "ui-datepicker-group")
        if not date_pickers:
            break

        for date_picker in date_pickers:
            try:
                month = date_picker.find_element(By.CLASS_NAME, "ui-datepicker-month").text
                year = date_picker.find_element(By.CLASS_NAME, "ui-datepicker-year").text
                days = date_picker.find_elements(By.CSS_SELECTOR, 'td[data-handler="selectDay"]')
                for day in days:
                    day_text = day.find_element(By.CLASS_NAME, "ui-state-default").text
                    d = _parse_date(day_text, month, year)
                    slots.add(Slot(date_iso=d.isoformat(), facility_id=facility_id))
            except Exception:
                continue

        # Next month
        try:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "ui-datepicker-next"))
            )
            next_button.click()
            time.sleep(0.7)
        except (TimeoutException, NoSuchElementException):
            break

        current_month_index += 1

    return slots

