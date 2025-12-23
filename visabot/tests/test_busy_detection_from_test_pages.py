from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from visabot.selenium_provider import _busy_message_present


@dataclass
class _FakeElement:
    displayed: bool

    def is_displayed(self) -> bool:  # selenium-like
        return self.displayed


class _FakeDriver:
    """Мини-драйвер для unit-теста _busy_message_present без Selenium.

    Нам важно проверить логику "%busy только если контейнер видим%".
    """

    def __init__(self, *, html: str, busy_container_displayed: bool | None):
        self._html = html
        self._busy_container_displayed = busy_container_displayed

    def find_elements(self, by: object, value: str):  # signature similar to selenium
        # _busy_message_present ищет только By.ID == "consulate_date_time_not_available"
        if value != "consulate_date_time_not_available":
            return []
        if self._busy_container_displayed is None:
            return []
        return [_FakeElement(displayed=self._busy_container_displayed)]

    @property
    def page_source(self) -> str:
        return self._html


_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "rel_path, expected_busy, expected_container_displayed",
    [
        (
            "test-pages/busy/Запись на собеседование _ Official U.S. Department of State Visa Appointment Service _ Kazakhstan _ Russian.html",
            True,
            True,
        ),
        (
            "test-pages/show input and selector/Запись на собеседование _ Official U.S. Department of State Visa Appointment Service _ Kazakhstan _ Russian.html",
            False,
            False,
        ),
    ],
)
def test_busy_message_present_matches_test_pages(rel_path: str, expected_busy: bool, expected_container_displayed: bool) -> None:
    html = (_REPO_ROOT / rel_path).read_text(encoding="utf-8")

    # Sanity: текст busy есть в обоих HTML (в одном он скрыт).
    assert "Система занята" in html

    driver = _FakeDriver(html=html, busy_container_displayed=expected_container_displayed)
    assert _busy_message_present(driver) is expected_busy


def test_busy_message_present_fallback_to_text_when_no_container() -> None:
    html = "<html><body>Система занята. Пожалуйста, повторите попытку позже.</body></html>"
    driver = _FakeDriver(html=html, busy_container_displayed=None)
    assert _busy_message_present(driver) is True

