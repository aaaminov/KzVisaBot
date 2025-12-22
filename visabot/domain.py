from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class Slot:
    """A single available appointment date.

    For MVP we only track the calendar date and facility id.
    """

    date_iso: str  # YYYY-MM-DD
    facility_id: int

