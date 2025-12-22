from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Slot:
    """A single available appointment date.

    For MVP we only track the calendar date and facility id.
    """

    date_iso: str  # YYYY-MM-DD
    facility_id: int


class BusyError(RuntimeError):
    """Штатное состояние сайта: он временно отвечает 'Система занята...'.

    Это не является 'реальной' ошибкой бизнес-логики, поэтому такие исключения
    не должны приводить к Telegram-алертам.
    """
