"""Weight log repository — stores daily weight entries per user."""
from __future__ import annotations
import json, os
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_USERS_DIR = os.path.join(_ROOT, "storage_agents", "users")


@dataclass
class WeightEntry:
    date: str          # YYYY-MM-DD
    weight_kg: float
    note: str = ""


class WeightRepository:
    def _path(self, user_id: str) -> str:
        d = os.path.join(_USERS_DIR, user_id)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "weight_log.json")

    def get_log(self, user_id: str) -> List[WeightEntry]:
        p = self._path(user_id)
        if not os.path.exists(p):
            return []
        try:
            data = json.load(open(p, encoding="utf-8"))
            return [WeightEntry(**e) for e in data]
        except Exception:
            return []

    def add_entry(self, user_id: str, weight_kg: float, note: str = "", entry_date: Optional[date] = None) -> WeightEntry:
        log = self.get_log(user_id)
        d = (entry_date or date.today()).isoformat()
        # Update if same date exists
        for e in log:
            if e.date == d:
                e.weight_kg = weight_kg
                e.note = note
                self._save(user_id, log)
                return e
        entry = WeightEntry(date=d, weight_kg=weight_kg, note=note)
        log.append(entry)
        log.sort(key=lambda e: e.date)
        self._save(user_id, log)
        return entry

    def _save(self, user_id: str, log: List[WeightEntry]):
        with open(self._path(user_id), "w", encoding="utf-8") as f:
            json.dump([e.__dict__ for e in log], f, ensure_ascii=False, indent=2)
