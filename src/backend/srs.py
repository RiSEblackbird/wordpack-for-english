from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .config import settings


@dataclass
class ReviewItem:
    id: str
    front: str
    back: str
    repetitions: int = 0
    interval_days: int = 0
    ease: float = 2.5
    due_at: datetime = field(default_factory=lambda: datetime.utcnow())


class SRSSQLiteStore:
    """SQLite-backed SRS store implementing a simplified SM-2 with history.

    - grade: 2=correct, 1=partial, 0=wrong
    - ease is clamped into [1.5, 3.0]
    - due/interval/ease/repetitions updated transactionally; review history recorded
    - default user/deck are seeded for MVP compatibility
    """

    def __init__(self, db_path: str, default_user_id: str = "default", default_deck_id: str = "default") -> None:
        self.db_path = db_path
        self.default_user_id = default_user_id
        self.default_deck_id = default_deck_id
        self._ensure_dirs()
        self._init_db()
        self._seed_if_empty()

    # --- low-level helpers ---
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0, isolation_level=None, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        with conn:  # autocommit on PRAGMA
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _ensure_dirs(self) -> None:
        p = Path(self.db_path)
        if p.parent and not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS decks (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cards (
                        id TEXT PRIMARY KEY,
                        deck_id TEXT NOT NULL,
                        front TEXT NOT NULL,
                        back TEXT NOT NULL,
                        repetitions INTEGER NOT NULL DEFAULT 0,
                        interval_days INTEGER NOT NULL DEFAULT 0,
                        ease REAL NOT NULL DEFAULT 2.5,
                        due_at TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
                    );
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        card_id TEXT NOT NULL,
                        reviewed_at TEXT NOT NULL,
                        grade INTEGER NOT NULL,
                        ease REAL NOT NULL,
                        interval_days INTEGER NOT NULL,
                        due_at TEXT NOT NULL,
                        FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE
                    );
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_due_at ON cards(due_at);")
        finally:
            conn.close()

    def _seed_if_empty(self) -> None:
        conn = self._connect()
        try:
            cur = conn.execute("SELECT COUNT(1) AS c FROM cards;")
            row = cur.fetchone()
            if row and int(row["c"]) > 0:
                return

            now = datetime.utcnow()
            seeds: List[tuple[str, str, str]] = [
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

            with conn:
                # seed user/deck
                conn.execute(
                    "INSERT OR IGNORE INTO users(id, created_at) VALUES (?, ?);",
                    (self.default_user_id, now.isoformat()),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO decks(id, user_id, name, created_at) VALUES (?, ?, ?, ?);",
                    (self.default_deck_id, self.default_user_id, "default", now.isoformat()),
                )
                for idx, (rid, front, back) in enumerate(seeds):
                    due = (now - timedelta(days=(idx % 3))).isoformat()
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO cards(
                            id, deck_id, front, back, repetitions, interval_days, ease, due_at, created_at
                        ) VALUES (?, ?, ?, ?, 0, 0, 2.5, ?, ?);
                        """,
                        (rid, self.default_deck_id, front, back, due, now.isoformat()),
                    )
        finally:
            conn.close()

    # --- public API ---
    def get_today(self, limit: int = 5) -> List[ReviewItem]:
        now = datetime.utcnow().isoformat()
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT id, front, back, repetitions, interval_days, ease, due_at FROM cards WHERE due_at <= ? ORDER BY due_at ASC, id ASC LIMIT ?;",
                (now, limit),
            )
            items: List[ReviewItem] = []
            for row in cur.fetchall():
                items.append(
                    ReviewItem(
                        id=row["id"],
                        front=row["front"],
                        back=row["back"],
                        repetitions=int(row["repetitions"]),
                        interval_days=int(row["interval_days"]),
                        ease=float(row["ease"]),
                        due_at=datetime.fromisoformat(row["due_at"]),
                    )
                )
            return items
        finally:
            conn.close()

    def grade(self, item_id: str, grade: int) -> Optional[ReviewItem]:
        # clamp grade into {0,1,2}
        g = 2 if grade >= 2 else (1 if grade == 1 else 0)
        conn = self._connect()
        try:
            # BEGIN IMMEDIATE to avoid concurrent writers on the same row
            conn.execute("BEGIN IMMEDIATE;")
            cur = conn.execute(
                "SELECT id, front, back, repetitions, interval_days, ease, due_at FROM cards WHERE id = ?;",
                (item_id,),
            )
            row = cur.fetchone()
            if row is None:
                conn.execute("ROLLBACK;")
                return None

            repetitions = int(row["repetitions"]) or 0
            interval_days = int(row["interval_days"]) or 0
            ease = float(row["ease"]) if row["ease"] is not None else 2.5

            # update ease
            if g == 2:
                ease += 0.10
            elif g == 1:
                ease += 0.00
            else:
                ease -= 0.20
            ease = max(1.5, min(3.0, ease))

            # update interval and repetitions
            if g == 0:
                repetitions = 0
                interval_days = 1
            else:
                repetitions += 1
                if repetitions == 1:
                    interval_days = 1
                elif repetitions == 2:
                    interval_days = 6
                else:
                    interval_days = max(1, int(round(interval_days * (ease if g == 2 else 1.2))))

            next_due_dt = datetime.utcnow() + timedelta(days=interval_days)
            next_due = next_due_dt.isoformat()

            # persist update
            conn.execute(
                """
                UPDATE cards
                SET repetitions = ?, interval_days = ?, ease = ?, due_at = ?
                WHERE id = ?;
                """,
                (repetitions, interval_days, ease, next_due, item_id),
            )
            conn.execute(
                """
                INSERT INTO reviews(card_id, reviewed_at, grade, ease, interval_days, due_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (item_id, datetime.utcnow().isoformat(), g, ease, interval_days, next_due),
            )
            conn.execute("COMMIT;")

            return ReviewItem(
                id=row["id"],
                front=row["front"],
                back=row["back"],
                repetitions=repetitions,
                interval_days=interval_days,
                ease=ease,
                due_at=next_due_dt,
            )
        except Exception:
            try:
                conn.execute("ROLLBACK;")
            except Exception:
                pass
            raise
        finally:
            conn.close()


    def ensure_card(self, item_id: str, front: str, back: str) -> None:
        """Ensure a card exists; create if missing with defaults.

        Newly created cards are due immediately (due_at=now) so they can be graded at once.
        """
        now = datetime.utcnow()
        conn = self._connect()
        try:
            cur = conn.execute("SELECT 1 FROM cards WHERE id = ?;", (item_id,))
            if cur.fetchone() is not None:
                return
            with conn:
                conn.execute(
                    "INSERT INTO cards(id, deck_id, front, back, repetitions, interval_days, ease, due_at, created_at) VALUES (?, ?, ?, ?, 0, 0, 2.5, ?, ?);",
                    (item_id, self.default_deck_id, front, back, now.isoformat(), now.isoformat()),
                )
        finally:
            conn.close()

    # --- stats & history ---
    def get_stats(self) -> Tuple[int, int]:
        """Return (due_now_count, reviewed_today_count).

        - due_now_count: 現在時刻までに due のカード件数
        - reviewed_today_count: 当日 00:00 UTC 以降にレビューされた件数
        """
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        conn = self._connect()
        try:
            cur1 = conn.execute("SELECT COUNT(1) AS c FROM cards WHERE due_at <= ?;", (now.isoformat(),))
            due_now = int(cur1.fetchone()["c"])
            cur2 = conn.execute("SELECT COUNT(1) AS c FROM reviews WHERE reviewed_at >= ?;", (today_start.isoformat(),))
            reviewed_today = int(cur2.fetchone()["c"])
            return due_now, reviewed_today
        finally:
            conn.close()

    def get_recent_reviewed(self, limit: int = 5) -> List[ReviewItem]:
        """直近レビューのカードを新しい順に最大 limit 件返す。"""
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT c.id, c.front, c.back, c.repetitions, c.interval_days, c.ease, c.due_at
                FROM reviews r
                JOIN cards c ON c.id = r.card_id
                ORDER BY r.reviewed_at DESC
                LIMIT ?;
                """,
                (limit,),
            )
            items: List[ReviewItem] = []
            for row in cur.fetchall():
                items.append(
                    ReviewItem(
                        id=row["id"],
                        front=row["front"],
                        back=row["back"],
                        repetitions=int(row["repetitions"]),
                        interval_days=int(row["interval_days"]),
                        ease=float(row["ease"]),
                        due_at=datetime.fromisoformat(row["due_at"]),
                    )
                )
            return items
        finally:
            conn.close()

    def get_popular(self, limit: int = 10) -> List[ReviewItem]:
        """よく見る順（レビュー件数の多い順）にカードを返す。

        - reviews の件数で降順ソート
        - 同数の場合は cards.created_at の昇順で安定化
        """
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT c.id, c.front, c.back, c.repetitions, c.interval_days, c.ease, c.due_at
                FROM cards c
                LEFT JOIN (
                    SELECT card_id, COUNT(1) AS rc
                    FROM reviews
                    GROUP BY card_id
                ) r ON r.card_id = c.id
                ORDER BY COALESCE(r.rc, 0) DESC, c.created_at ASC, c.id ASC
                LIMIT ?;
                """,
                (limit,),
            )
            items: List[ReviewItem] = []
            for row in cur.fetchall():
                items.append(
                    ReviewItem(
                        id=row["id"],
                        front=row["front"],
                        back=row["back"],
                        repetitions=int(row["repetitions"]),
                        interval_days=int(row["interval_days"]),
                        ease=float(row["ease"]),
                        due_at=datetime.fromisoformat(row["due_at"]),
                    )
                )
            return items
        finally:
            conn.close()


# module-level singleton store (wired to settings)
store = SRSSQLiteStore(db_path=settings.srs_db_path)

