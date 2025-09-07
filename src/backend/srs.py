from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class ReviewItem:
    id: str
    front: str
    back: str
    repetitions: int = 0
    interval_days: int = 0
    ease: float = 2.5  # kept within [1.5, 3.0]
    due_at: datetime = field(default_factory=lambda: datetime.utcnow())


class SRSInMemoryStore:
    """Very small in-memory SRS store implementing a simplified SM-2.

    - grade: 2=correct, 1=partial, 0=wrong
    - ease is clamped into [1.5, 3.0]
    - next due is computed from interval and ease
    """

    def __init__(self) -> None:
        self._items: List[ReviewItem] = []
        self._seed()

    def _seed(self) -> None:
        if self._items:
            return
        now = datetime.utcnow()
        seeds = [
            ("w:converge", "converge", "to come together"),
            ("w:assumption", "assumption", "a thing that is accepted as true"),
            ("w:algorithm", "algorithm", "a step-by-step procedure"),
            ("w:robust", "robust", "strong and healthy; resilient"),
            ("w:tradeoff", "trade-off", "a balance achieved between two desirable but incompatible features"),
            ("w:approximate", "approximate", "close to the actual, but not completely accurate"),
            ("w:feasible", "feasible", "possible to do easily or conveniently"),
            ("w:insight", "insight", "the capacity to gain an accurate understanding"),
            ("w:via", "via", "traveling through (a place) en route"),
            ("w:yield", "yield", "produce or provide"),
        ]
        for idx, (rid, front, back) in enumerate(seeds):
            # spread due dates a bit in the past so some are always due
            due = now - timedelta(days=(idx % 3))
            self._items.append(
                ReviewItem(id=rid, front=front, back=back, repetitions=0, interval_days=0, ease=2.5, due_at=due)
            )

    def get_today(self, limit: int = 5) -> List[ReviewItem]:
        now = datetime.utcnow()
        due_items = [it for it in self._items if it.due_at <= now]
        # deterministic order: earliest due first
        due_items.sort(key=lambda x: (x.due_at, x.id))
        return due_items[:limit]

    def grade(self, item_id: str, grade: int) -> Optional[ReviewItem]:
        target = next((it for it in self._items if it.id == item_id), None)
        if target is None:
            return None

        # clamp grade into {0,1,2}
        g = 2 if grade >= 2 else (1 if grade == 1 else 0)

        # update ease
        if g == 2:  # correct
            target.ease += 0.10
        elif g == 1:  # partial
            target.ease += 0.00
        else:  # wrong
            target.ease -= 0.20
        target.ease = max(1.5, min(3.0, target.ease))

        # update interval and repetitions
        if g == 0:
            target.repetitions = 0
            target.interval_days = 1
        else:
            target.repetitions += 1
            if target.repetitions == 1:
                target.interval_days = 1
            elif target.repetitions == 2:
                target.interval_days = 6
            else:
                # general repetition
                target.interval_days = max(1, int(round(target.interval_days * (target.ease if g == 2 else 1.2))))

        target.due_at = datetime.utcnow() + timedelta(days=target.interval_days)
        return target


# module-level singleton store
store = SRSInMemoryStore()


