from __future__ import annotations

import os
import sqlite3
import json
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
                
                # WordPack永続化テーブル
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS word_packs (
                        id TEXT PRIMARY KEY,
                        lemma TEXT NOT NULL,
                        data TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_word_packs_lemma ON word_packs(lemma);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_word_packs_created_at ON word_packs(created_at);")
                # 例文を正規化して保存するテーブル（WordPack 1:多 Examples）
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS word_pack_examples (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        word_pack_id TEXT NOT NULL,
                        category TEXT NOT NULL,
                        position INTEGER NOT NULL,
                        en TEXT NOT NULL,
                        ja TEXT NOT NULL,
                        grammar_ja TEXT,
                        llm_model TEXT,
                        llm_params TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY(word_pack_id) REFERENCES word_packs(id) ON DELETE CASCADE
                    );
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_wpex_pack ON word_pack_examples(word_pack_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_wpex_pack_cat_pos ON word_pack_examples(word_pack_id, category, position);")
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

    def get_card_meta(self, item_id: str) -> Optional[ReviewItem]:
        """Return SRS metadata for a card if it exists.

        Includes repetitions, interval_days, and due_at. Returns None if not found.
        """
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT id, front, back, repetitions, interval_days, ease, due_at FROM cards WHERE id = ?;",
                (item_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return ReviewItem(
                id=row["id"],
                front=row["front"],
                back=row["back"],
                repetitions=int(row["repetitions"]),
                interval_days=int(row["interval_days"]),
                ease=float(row["ease"]),
                due_at=datetime.fromisoformat(row["due_at"]),
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

    # --- WordPack永続化機能 ---
    def save_word_pack(self, word_pack_id: str, lemma: str, data: str) -> None:
        """WordPackをデータベースに保存する。

        入力の data(JSON) から examples を分離して正規化テーブルに保存し、
        core 部分（examples を除く）を word_packs.data に保存する。
        """
        now = datetime.utcnow().isoformat()
        # JSON を解析し、examples を分離
        try:
            parsed = json.loads(data) if isinstance(data, str) else dict(data or {})
        except Exception:
            # 不正な JSON はそのまま保存（従来互換）
            parsed = None
        examples = None
        core_json = data
        if isinstance(parsed, dict):
            try:
                examples = parsed.get("examples")
                if isinstance(examples, dict):
                    # core から examples を取り除いて保存用 JSON を作る
                    core = dict(parsed)
                    core.pop("examples", None)
                    core_json = json.dumps(core, ensure_ascii=False)
            except Exception:
                examples = None

        conn = self._connect()
        try:
            with conn:
                # 1) core を upsert
                conn.execute(
                    """
                    INSERT OR REPLACE INTO word_packs(id, lemma, data, created_at, updated_at)
                    VALUES (?, ?, ?, 
                        COALESCE((SELECT created_at FROM word_packs WHERE id = ?), ?),
                        ?);
                    """,
                    (word_pack_id, lemma, core_json, word_pack_id, now, now),
                )

                # 2) examples が dict なら正規化テーブルを置き換え
                if isinstance(examples, dict):
                    conn.execute("DELETE FROM word_pack_examples WHERE word_pack_id = ?;", (word_pack_id,))
                    categories = ["Dev", "CS", "LLM", "Business", "Common"]
                    for cat in categories:
                        arr = examples.get(cat) or []
                        if not isinstance(arr, list):
                            continue
                        for pos, item in enumerate(arr):
                            if not isinstance(item, dict):
                                continue
                            en = str(item.get("en") or "").strip()
                            ja = str(item.get("ja") or "").strip()
                            if not en or not ja:
                                continue
                            grammar_ja = (str(item.get("grammar_ja") or "").strip() or None)
                            llm_model = (str(item.get("llm_model") or "").strip() or None)
                            llm_params = (str(item.get("llm_params") or "").strip() or None)
                            conn.execute(
                                """
                                INSERT INTO word_pack_examples(
                                    word_pack_id, category, position, en, ja, grammar_ja, llm_model, llm_params, created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                                """,
                                (word_pack_id, cat, pos, en, ja, grammar_ja, llm_model, llm_params, now),
                            )
        finally:
            conn.close()

    def get_word_pack(self, word_pack_id: str) -> Optional[tuple[str, str, str, str]]:
        """WordPackをIDで取得する。戻り値: (lemma, data_json, created_at, updated_at)

        保存時に examples を分離しているため、ここで examples を結合して返す。
        旧データ互換として、正規化テーブルに行が無い場合は data 内の examples を使用する。
        """
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT lemma, data, created_at, updated_at FROM word_packs WHERE id = ?;",
                (word_pack_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None

            lemma = row["lemma"]
            core_json = row["data"]
            created_at = row["created_at"]
            updated_at = row["updated_at"]

            # core を辞書化
            try:
                core = json.loads(core_json) if core_json else {}
            except Exception:
                core = {}

            # 正規化テーブルから examples を再構築
            examples: dict = {"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []}
            ex_cur = conn.execute(
                """
                SELECT category, en, ja, grammar_ja, llm_model, llm_params
                FROM word_pack_examples
                WHERE word_pack_id = ?
                ORDER BY category ASC, position ASC, id ASC;
                """,
                (word_pack_id,),
            )
            any_row = False
            for ex_row in ex_cur.fetchall():
                any_row = True
                cat = ex_row["category"]
                item = {
                    "en": ex_row["en"],
                    "ja": ex_row["ja"],
                }
                if ex_row["grammar_ja"]:
                    item["grammar_ja"] = ex_row["grammar_ja"]
                if ex_row["llm_model"]:
                    item["llm_model"] = ex_row["llm_model"]
                if ex_row["llm_params"]:
                    item["llm_params"] = ex_row["llm_params"]
                if cat in examples:
                    examples[cat].append(item)
            # 旧データ互換: 行が無い場合は core に残っている examples をそのまま採用
            if any_row:
                core["examples"] = examples
            else:
                try:
                    ex_in_core = core.get("examples")
                    if not isinstance(ex_in_core, dict):
                        core["examples"] = {"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []}
                except Exception:
                    core["examples"] = {"Dev": [], "CS": [], "LLM": [], "Business": [], "Common": []}

            return (lemma, json.dumps(core, ensure_ascii=False), created_at, updated_at)
        finally:
            conn.close()

    def list_word_packs(self, limit: int = 50, offset: int = 0) -> List[tuple[str, str, str, str]]:
        """WordPack一覧を取得する。戻り値: [(id, lemma, created_at, updated_at), ...]"""
        conn = self._connect()
        try:
            cur = conn.execute(
                "SELECT id, lemma, created_at, updated_at FROM word_packs ORDER BY created_at DESC LIMIT ? OFFSET ?;",
                (limit, offset),
            )
            return [(row["id"], row["lemma"], row["created_at"], row["updated_at"]) for row in cur.fetchall()]
        finally:
            conn.close()

    def delete_word_pack(self, word_pack_id: str) -> bool:
        """WordPackを削除する。成功時True、存在しない場合False。"""
        conn = self._connect()
        try:
            with conn:
                cur = conn.execute("DELETE FROM word_packs WHERE id = ?;", (word_pack_id,))
                return cur.rowcount > 0
        finally:
            conn.close()

    # --- WordPack Examples operations (optimized) ---
    def delete_example(self, word_pack_id: str, category: str, index: int) -> Optional[int]:
        """指定カテゴリ内の index の例文を削除し、残件数を返す。存在しなければ None。

        位置の整列（position の詰め）も行う。
        """
        if index < 0:
            return None
        conn = self._connect()
        try:
            with conn:
                # 行の存在確認とターゲット id の特定（position 順）
                cur = conn.execute(
                    """
                    SELECT id FROM word_pack_examples
                    WHERE word_pack_id = ? AND category = ?
                    ORDER BY position ASC, id ASC
                    LIMIT 1 OFFSET ?;
                    """,
                    (word_pack_id, category, index),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                target_id = int(row["id"])

                # 削除
                conn.execute("DELETE FROM word_pack_examples WHERE id = ?;", (target_id,))

                # 位置の再採番（category 内で 0..N-1 に詰める）
                cur2 = conn.execute(
                    """
                    SELECT id FROM word_pack_examples
                    WHERE word_pack_id = ? AND category = ?
                    ORDER BY position ASC, id ASC;
                    """,
                    (word_pack_id, category),
                )
                ids = [int(r["id"]) for r in cur2.fetchall()]
                for new_pos, rid in enumerate(ids):
                    conn.execute(
                        "UPDATE word_pack_examples SET position = ? WHERE id = ?;",
                        (new_pos, rid),
                    )

                # 残件数
                remaining = len(ids)
                return remaining
        finally:
            conn.close()


# module-level singleton store (wired to settings)
store = SRSSQLiteStore(db_path=settings.srs_db_path)

