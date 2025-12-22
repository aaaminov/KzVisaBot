from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict
from typing import Iterable

from visabot.domain import Slot


def load_slots(path: str) -> set[Slot]:
    if not os.path.exists(path):
        return set()

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError:
        # Corrupted state shouldn't brick the worker; start fresh.
        return set()

    slots_raw = raw.get("slots", [])
    slots: set[Slot] = set()
    for item in slots_raw:
        try:
            slots.add(Slot(date_iso=str(item["date_iso"]), facility_id=int(item["facility_id"])))
        except Exception:
            continue
    return slots


def save_slots(path: str, slots: Iterable[Slot]) -> None:
    data = {
        "slots": [asdict(s) for s in sorted(set(slots))],
    }

    folder = os.path.dirname(os.path.abspath(path))
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

    # Atomic write
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", dir=folder, suffix=".tmp") as tf:
        json.dump(data, tf, ensure_ascii=False, indent=2)
        tmp_name = tf.name

    os.replace(tmp_name, path)

