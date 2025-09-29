from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence

from .config import settings
from .sense_title import choose_sense_title


EXAMPLE_CATEGORIES: tuple[str, ...] = ("Dev", "CS", "LLM", "Business", "Common")


class AppSQLiteStore:
    """SQLite-backed persistence layer for WordPack data."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_dirs()
        self._init_db()

    # --- low-level helpers ---
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path, timeout=10.0, isolation_level=None, check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        with conn:  # autocommit on pragma
            conn.execute("pragma journal_mode=WAL;")
            conn.execute("pragma foreign_keys=ON;")
        return conn

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_dirs(self) -> None:
        p = Path(self.db_path)
        if p.parent and not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_non_negative_int(value: Any) -> int:
        """入力を非負整数に正規化する（不正値/負値は0）。"""

        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            return 0
        return ivalue if ivalue >= 0 else 0

    def _init_db(self) -> None:
        with self._conn() as conn:
            with conn:
                self._ensure_lemmas_table(conn)
                self._ensure_word_packs_table(conn)
                self._ensure_word_pack_examples_table(conn)
                self._ensure_articles_table(conn)
                self._ensure_article_word_packs_table(conn)

    def _ensure_lemmas_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lemmas (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                sense_title TEXT NOT NULL DEFAULT '',
                llm_model TEXT,
                llm_params TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_lemmas_label_ci ON lemmas(lower(label));"
        )

    def _ensure_word_packs_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS word_packs (
                id TEXT PRIMARY KEY,
                lemma_id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                checked_only_count INTEGER NOT NULL DEFAULT 0,
                learned_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(lemma_id) REFERENCES lemmas(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_word_packs_lemma_id ON word_packs(lemma_id);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_word_packs_created_at ON word_packs(created_at);"
        )

    def _ensure_word_pack_examples_table(self, conn: sqlite3.Connection) -> None:
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
                checked_only_count INTEGER NOT NULL DEFAULT 0,
                learned_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(word_pack_id) REFERENCES word_packs(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wpex_pack ON word_pack_examples(word_pack_id);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wpex_pack_cat_pos ON word_pack_examples(word_pack_id, category, position);"
        )

    def _ensure_articles_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title_en TEXT NOT NULL,
                body_en TEXT NOT NULL,
                body_ja TEXT NOT NULL,
                notes_ja TEXT,
                llm_model TEXT,
                llm_params TEXT,
                generation_category TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                generation_started_at TEXT,
                generation_completed_at TEXT,
                generation_duration_ms INTEGER
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_title ON articles(title_en);"
        )

    def _ensure_article_word_packs_table(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS article_word_packs (
                article_id TEXT NOT NULL,
                word_pack_id TEXT NOT NULL,
                lemma TEXT NOT NULL,
                status TEXT NOT NULL, -- 'existing' | 'created'
                created_at TEXT NOT NULL,
                PRIMARY KEY(article_id, word_pack_id),
                FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE,
                FOREIGN KEY(word_pack_id) REFERENCES word_packs(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_article_wps_article ON article_word_packs(article_id);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_article_wps_lemma ON article_word_packs(lemma);"
        )

    def _split_examples_from_payload(
        self, data: str | Mapping[str, Any]
    ) -> tuple[
        str,
        Mapping[str, Any] | None,
        str,
        list[str],
        tuple[int, int],
        tuple[str | None, str | None],
    ]:
        """payload(JSON or dict) から examples を分離し、コアJSONと例文テーブル保存用データに分ける。"""

        checked_only_count = 0
        learned_count = 0
        lemma_llm_model: str | None = None
        lemma_llm_params: str | None = None

        if isinstance(data, Mapping):
            parsed: Mapping[str, Any] = dict(data)
        else:
            try:
                parsed = json.loads(data) if data else {}
            except Exception:
                empty_json = json.dumps({}, ensure_ascii=False)
                return (
                    data if isinstance(data, str) else empty_json,
                    None,
                    "",
                    [],
                    (checked_only_count, learned_count),
                    (lemma_llm_model, lemma_llm_params),
                )
            if not isinstance(parsed, Mapping):
                empty_json = json.dumps({}, ensure_ascii=False)
                return (
                    data if isinstance(data, str) else empty_json,
                    None,
                    "",
                    [],
                    (checked_only_count, learned_count),
                    (lemma_llm_model, lemma_llm_params),
                )

        sense_title = ""
        sense_candidates: list[str] = []
        try:
            sense_title = str(parsed.get("sense_title") or "").strip()
        except Exception:
            sense_title = ""

        try:
            val = str(parsed.get("llm_model") or "").strip()
            lemma_llm_model = val or None
        except Exception:
            lemma_llm_model = None
        try:
            val = str(parsed.get("llm_params") or "").strip()
            lemma_llm_params = val or None
        except Exception:
            lemma_llm_params = None

        try:
            checked_only_count = self._normalize_non_negative_int(
                (parsed or {}).get("checked_only_count")
            )
        except Exception:
            checked_only_count = 0
        try:
            learned_count = self._normalize_non_negative_int(
                (parsed or {}).get("learned_count")
            )
        except Exception:
            learned_count = 0

        senses_payload = parsed.get("senses") if isinstance(parsed, Mapping) else None
        if isinstance(senses_payload, Sequence):
            for sense in senses_payload:
                if not isinstance(sense, Mapping):
                    continue
                for key in (
                    "gloss_ja",
                    "term_overview_ja",
                    "term_core_ja",
                    "definition_ja",
                    "nuances_ja",
                ):
                    try:
                        val = str(sense.get(key) or "").strip()
                    except Exception:
                        val = ""
                    if val:
                        sense_candidates.append(val)

        examples = parsed.get("examples") if isinstance(parsed, Mapping) else None
        if isinstance(examples, Mapping):
            core = dict(parsed)
            core.pop("examples", None)
            return (
                json.dumps(core, ensure_ascii=False),
                examples,
                sense_title,
                sense_candidates,
                (checked_only_count, learned_count),
                (lemma_llm_model, lemma_llm_params),
            )
        serialized = (
            json.dumps(parsed, ensure_ascii=False)
            if not isinstance(data, str)
            else data
        )
        return (
            serialized,
            None,
            sense_title,
            sense_candidates,
            (checked_only_count, learned_count),
            (lemma_llm_model, lemma_llm_params),
        )

    def _iter_example_rows(
        self, examples: Mapping[str, Any]
    ) -> Iterable[
        tuple[str, int, str, str, str | None, str | None, str | None, int, int]
    ]:
        for category in EXAMPLE_CATEGORIES:
            arr = examples.get(category)
            if not isinstance(arr, Sequence):
                continue
            for pos, item in enumerate(arr):
                if not isinstance(item, Mapping):
                    continue
                en = str(item.get("en") or "").strip()
                ja = str(item.get("ja") or "").strip()
                if not en or not ja:
                    continue
                grammar_ja = str(item.get("grammar_ja") or "").strip() or None
                llm_model = str(item.get("llm_model") or "").strip() or None
                llm_params = str(item.get("llm_params") or "").strip() or None
                checked_only_count = self._normalize_non_negative_int(
                    (item or {}).get("checked_only_count")
                )
                learned_count = self._normalize_non_negative_int(
                    (item or {}).get("learned_count")
                )
                yield (
                    category,
                    pos,
                    en,
                    ja,
                    grammar_ja,
                    llm_model,
                    llm_params,
                    checked_only_count,
                    learned_count,
                )

    def _load_examples_rows(
        self, conn: sqlite3.Connection, word_pack_id: str
    ) -> Sequence[sqlite3.Row]:
        cur = conn.execute(
            """
            SELECT
                category,
                en,
                ja,
                grammar_ja,
                llm_model,
                llm_params,
                checked_only_count,
                learned_count
            FROM word_pack_examples
            WHERE word_pack_id = ?
            ORDER BY category ASC, position ASC, id ASC;
            """,
            (word_pack_id,),
        )
        return cur.fetchall()

    def _merge_core_with_examples(
        self, core_json: str, rows: Sequence[sqlite3.Row]
    ) -> str:
        try:
            core = json.loads(core_json) if core_json else {}
        except Exception:
            core = {}
        examples: dict[str, list[dict[str, Any]]] = {
            cat: [] for cat in EXAMPLE_CATEGORIES
        }
        for r in rows:
            cat = r["category"]
            item = {"en": r["en"], "ja": r["ja"]}
            if r["grammar_ja"]:
                item["grammar_ja"] = r["grammar_ja"]
            if r["llm_model"]:
                item["llm_model"] = r["llm_model"]
            if r["llm_params"]:
                item["llm_params"] = r["llm_params"]
            item["checked_only_count"] = self._normalize_non_negative_int(
                r["checked_only_count"]
            )
            item["learned_count"] = self._normalize_non_negative_int(r["learned_count"])
            examples.setdefault(cat, []).append(item)
        # ensure categories exist even if absent in DB
        for cat in EXAMPLE_CATEGORIES:
            examples.setdefault(cat, [])
        core["examples"] = examples
        return json.dumps(core, ensure_ascii=False)

    def _upsert_lemma(
        self,
        conn: sqlite3.Connection,
        *,
        label: str,
        sense_title: str,
        llm_model: str | None,
        llm_params: str | None,
        now: str,
    ) -> str:
        """lemma テーブルに label を upsert し、ID を返す。"""

        original_label = str(label or "").strip()
        if not original_label:
            raise ValueError("lemma label must not be empty")

        normalized = original_label.lower()

        cur = conn.execute(
            """
            SELECT id, label, sense_title, llm_model, llm_params
            FROM lemmas
            WHERE lower(label) = lower(?)
            LIMIT 1;
            """,
            (normalized,),
        )
        row = cur.fetchone()
        if row is None:
            lemma_id = f"lm:{normalized}:{uuid.uuid4().hex[:8]}"
            conn.execute(
                """
                INSERT INTO lemmas(id, label, sense_title, llm_model, llm_params, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    lemma_id,
                    original_label,
                    sense_title or "",
                    llm_model,
                    llm_params,
                    now,
                ),
            )
            return lemma_id

        lemma_id = row["id"]
        stored_label = str(row["label"] or "")
        if stored_label and stored_label.lower() == original_label.lower():
            new_label = stored_label
        else:
            new_label = original_label or stored_label
        stripped_sense = str(sense_title or "").strip()
        stored_sense_title = str(row["sense_title"] or "")
        if stored_sense_title:
            new_sense_title = stored_sense_title
        else:
            new_sense_title = stripped_sense
        new_llm_model = llm_model if llm_model is not None else row["llm_model"]
        new_llm_params = llm_params if llm_params is not None else row["llm_params"]
        conn.execute(
            """
            UPDATE lemmas
            SET label = ?,
                sense_title = ?,
                llm_model = ?,
                llm_params = ?
            WHERE id = ?;
            """,
            (new_label, new_sense_title, new_llm_model, new_llm_params, lemma_id),
        )
        return lemma_id

    # --- WordPack 永続化機能 ---
    def save_word_pack(self, word_pack_id: str, lemma: str, data: str) -> None:
        """WordPackをデータベースに保存する。

        入力の data(JSON) から examples を分離して正規化テーブルに保存し、
        core 部分（examples を除く）を word_packs.data に保存する。
        """
        now = datetime.now(UTC).isoformat()
        (
            core_json,
            examples,
            sense_title_raw,
            sense_candidates,
            (checked_only_count, learned_count),
            (lemma_llm_model, lemma_llm_params),
        ) = self._split_examples_from_payload(data)
        sense_title = choose_sense_title(
            sense_title_raw,
            sense_candidates,
            lemma=lemma,
            limit=40,
        )

        with self._conn() as conn:
            with conn:
                lemma_id = self._upsert_lemma(
                    conn,
                    label=lemma,
                    sense_title=sense_title,
                    llm_model=lemma_llm_model,
                    llm_params=lemma_llm_params,
                    now=now,
                )
                conn.execute(
                    """
                    INSERT INTO word_packs(
                        id, lemma_id, data, created_at, updated_at, checked_only_count, learned_count
                    )
                    VALUES (
                        ?, ?, ?,
                        COALESCE((SELECT created_at FROM word_packs WHERE id = ?), ?),
                        ?,
                        ?,
                        ?
                    )
                    ON CONFLICT(id) DO UPDATE SET
                        lemma_id = excluded.lemma_id,
                        data = excluded.data,
                        updated_at = excluded.updated_at,
                        checked_only_count = excluded.checked_only_count,
                        learned_count = excluded.learned_count;
                    """,
                    (
                        word_pack_id,
                        lemma_id,
                        core_json,
                        word_pack_id,
                        now,
                        now,
                        checked_only_count,
                        learned_count,
                    ),
                )

                if isinstance(examples, Mapping):
                    conn.execute(
                        "DELETE FROM word_pack_examples WHERE word_pack_id = ?;",
                        (word_pack_id,),
                    )
                    for (
                        cat,
                        pos,
                        en,
                        ja,
                        grammar_ja,
                        llm_model,
                        llm_params,
                        checked_only_count,
                        learned_count,
                    ) in self._iter_example_rows(examples):
                        conn.execute(
                            """
                            INSERT INTO word_pack_examples(
                                word_pack_id, category, position, en, ja, grammar_ja, llm_model, llm_params,
                                checked_only_count, learned_count, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """,
                            (
                                word_pack_id,
                                cat,
                                pos,
                                en,
                                ja,
                                grammar_ja,
                                llm_model,
                                llm_params,
                                checked_only_count,
                                learned_count,
                                now,
                            ),
                        )

    def get_word_pack(self, word_pack_id: str) -> Optional[tuple[str, str, str, str]]:
        """WordPackをIDで取得する。戻り値: (lemma, data_json, created_at, updated_at)

        保存時に examples を分離しているため、ここで examples を結合して返す。
        """
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT lm.label AS lemma, wp.data, wp.created_at, wp.updated_at,
                       wp.checked_only_count, wp.learned_count
                FROM word_packs AS wp
                JOIN lemmas AS lm ON lm.id = wp.lemma_id
                WHERE wp.id = ?;
                """,
                (word_pack_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None

            rows = self._load_examples_rows(conn, word_pack_id)
            data_json = self._merge_core_with_examples(row["data"], rows)
            try:
                data_dict = json.loads(data_json) if data_json else {}
            except Exception:
                data_dict = {}
            data_dict["checked_only_count"] = self._normalize_non_negative_int(
                row["checked_only_count"]
            )
            data_dict["learned_count"] = self._normalize_non_negative_int(
                row["learned_count"]
            )
            data_json_with_progress = json.dumps(data_dict, ensure_ascii=False)
            return (
                row["lemma"],
                data_json_with_progress,
                row["created_at"],
                row["updated_at"],
            )

    def list_word_packs(
        self, limit: int = 50, offset: int = 0
    ) -> list[tuple[str, str, str, str, str]]:
        """WordPack一覧を取得する。戻り値: [(id, lemma, sense_title, created_at, updated_at), ...]"""
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT wp.id, lm.label AS lemma, lm.sense_title, wp.created_at, wp.updated_at
                FROM word_packs AS wp
                JOIN lemmas AS lm ON lm.id = wp.lemma_id
                ORDER BY wp.created_at DESC
                LIMIT ? OFFSET ?;
                """,
                (limit, offset),
            )
            return [
                (
                    row["id"],
                    row["lemma"],
                    row["sense_title"],
                    row["created_at"],
                    row["updated_at"],
                )
                for row in cur.fetchall()
            ]

    def count_word_packs(self) -> int:
        """WordPack総件数を返す。"""
        with self._conn() as conn:
            cur = conn.execute("SELECT COUNT(1) AS c FROM word_packs;")
            row = cur.fetchone()
            return int(row["c"]) if row is not None else 0

    def list_word_packs_with_flags(
        self, limit: int = 50, offset: int = 0
    ) -> list[tuple[str, str, str, str, str, bool, Optional[dict], int, int]]:
        """一覧取得のための軽量フラグ/集計付きリストを返す。

        戻り値: [(id, lemma, sense_title, created_at, updated_at, is_empty, examples_count_dict|None, checked_only, learned), ...]

        - is_empty: examples と study_card/senses の有無に依存するが、一覧は軽量化のため
          examples の件数のみで空判定の近似値を算出する。
        - examples_count_dict: {category: count}
        """
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT wp.id, lm.label AS lemma, lm.sense_title, wp.created_at, wp.updated_at,
                       SUM(CASE WHEN wpe.category = 'Dev' THEN 1 ELSE 0 END) AS cnt_dev,
                       SUM(CASE WHEN wpe.category = 'CS' THEN 1 ELSE 0 END) AS cnt_cs,
                       SUM(CASE WHEN wpe.category = 'LLM' THEN 1 ELSE 0 END) AS cnt_llm,
                       SUM(CASE WHEN wpe.category = 'Business' THEN 1 ELSE 0 END) AS cnt_biz,
                       SUM(CASE WHEN wpe.category = 'Common' THEN 1 ELSE 0 END) AS cnt_common,
                       wp.checked_only_count AS checked_only_count,
                       wp.learned_count AS learned_count
                FROM word_packs wp
                JOIN lemmas lm ON lm.id = wp.lemma_id
                LEFT JOIN word_pack_examples wpe ON wpe.word_pack_id = wp.id
                GROUP BY wp.id, lm.label, lm.sense_title, wp.created_at, wp.updated_at, wp.checked_only_count, wp.learned_count
                ORDER BY wp.created_at DESC
                LIMIT ? OFFSET ?;
                """,
                (limit, offset),
            )
            items: list[tuple[str, str, str, str, str, bool, Optional[dict]]] = []
            for row in cur.fetchall():
                cnt_dev = int(row["cnt_dev"] or 0)
                cnt_cs = int(row["cnt_cs"] or 0)
                cnt_llm = int(row["cnt_llm"] or 0)
                cnt_biz = int(row["cnt_biz"] or 0)
                cnt_common = int(row["cnt_common"] or 0)
                total_examples = cnt_dev + cnt_cs + cnt_llm + cnt_biz + cnt_common
                is_empty = total_examples == 0
                examples_count = {
                    "Dev": cnt_dev,
                    "CS": cnt_cs,
                    "LLM": cnt_llm,
                    "Business": cnt_biz,
                    "Common": cnt_common,
                }
                checked_only = self._normalize_non_negative_int(
                    row["checked_only_count"]
                )
                learned = self._normalize_non_negative_int(row["learned_count"])
                items.append(
                    (
                        row["id"],
                        row["lemma"],
                        row["sense_title"],
                        row["created_at"],
                        row["updated_at"],
                        is_empty,
                        examples_count,
                        checked_only,
                        learned,
                    )
                )
            return items

    def delete_word_pack(self, word_pack_id: str) -> bool:
        """WordPackを削除する。成功時True、存在しない場合False。"""
        with self._conn() as conn:
            with conn:
                cur = conn.execute(
                    "DELETE FROM word_packs WHERE id = ?;", (word_pack_id,)
                )
                return cur.rowcount > 0

    def update_word_pack_study_progress(
        self, word_pack_id: str, checked_increment: int, learned_increment: int
    ) -> Optional[tuple[int, int]]:
        """WordPackの学習進捗カウントを加算し、更新後の値を返す。"""

        with self._conn() as conn:
            with conn:
                cur = conn.execute(
                    "SELECT checked_only_count, learned_count FROM word_packs WHERE id = ?;",
                    (word_pack_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                current_checked = self._normalize_non_negative_int(
                    row["checked_only_count"]
                )
                current_learned = self._normalize_non_negative_int(row["learned_count"])
                next_checked = max(0, current_checked + int(checked_increment))
                next_learned = max(0, current_learned + int(learned_increment))
                if next_checked != current_checked or next_learned != current_learned:
                    conn.execute(
                        "UPDATE word_packs SET checked_only_count = ?, learned_count = ? WHERE id = ?;",
                        (next_checked, next_learned, word_pack_id),
                    )
                return next_checked, next_learned

    def update_example_study_progress(
        self, example_id: int, checked_increment: int, learned_increment: int
    ) -> Optional[tuple[str, int, int]]:
        """例文単位の学習進捗カウントを加算し、更新後の値と所属WordPack IDを返す。"""

        with self._conn() as conn:
            with conn:
                cur = conn.execute(
                    """
                    SELECT word_pack_id, checked_only_count, learned_count
                    FROM word_pack_examples
                    WHERE id = ?;
                    """,
                    (example_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                current_checked = self._normalize_non_negative_int(
                    row["checked_only_count"]
                )
                current_learned = self._normalize_non_negative_int(row["learned_count"])
                next_checked = max(0, current_checked + int(checked_increment))
                next_learned = max(0, current_learned + int(learned_increment))
                if next_checked != current_checked or next_learned != current_learned:
                    conn.execute(
                        """
                        UPDATE word_pack_examples
                        SET checked_only_count = ?, learned_count = ?
                        WHERE id = ?;
                        """,
                        (next_checked, next_learned, example_id),
                    )
                return str(row["word_pack_id"]), next_checked, next_learned

    # --- WordPack Examples operations (optimized) ---
    def delete_example(
        self, word_pack_id: str, category: str, index: int
    ) -> Optional[int]:
        """指定カテゴリ内の index の例文を削除し、残件数を返す。存在しなければ None。

        位置の整列（position の詰め）も行う。
        """
        if index < 0:
            return None
        with self._conn() as conn:
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
                conn.execute(
                    "DELETE FROM word_pack_examples WHERE id = ?;", (target_id,)
                )

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

    def delete_examples_by_ids(
        self, example_ids: Iterable[int]
    ) -> tuple[int, list[int]]:
        """例文ID一覧を受け取り、一括削除する。

        戻り値は (削除件数, 未削除ID一覧)。同一カテゴリの再採番も行う。
        """
        normalized: list[int] = []
        for eid in example_ids:
            try:
                normalized.append(int(eid))
            except (TypeError, ValueError):
                continue
        if not normalized:
            return 0, []

        deleted = 0
        not_found: list[int] = []
        touched: set[tuple[str, str]] = set()

        with self._conn() as conn:
            with conn:
                for example_id in normalized:
                    cur = conn.execute(
                        "SELECT word_pack_id, category FROM word_pack_examples WHERE id = ?;",
                        (example_id,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        not_found.append(example_id)
                        continue
                    conn.execute(
                        "DELETE FROM word_pack_examples WHERE id = ?;", (example_id,)
                    )
                    deleted += 1
                    touched.add((row["word_pack_id"], row["category"]))

                for word_pack_id, category in touched:
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

        return deleted, not_found

    # --- WordPack helpers ---
    def find_word_pack_id_by_lemma(self, lemma: str) -> Optional[str]:
        """見出し語から既存のWordPack IDを1件返す（更新日時降順）。無ければNone。"""
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT wp.id
                FROM word_packs AS wp
                JOIN lemmas AS lm ON lm.id = wp.lemma_id
                WHERE lm.label = ?
                ORDER BY wp.updated_at DESC
                LIMIT 1;
                """,
                (lemma,),
            )
            row = cur.fetchone()
            return row["id"] if row is not None else None

    def find_word_pack_by_lemma_ci(self, lemma: str) -> Optional[tuple[str, str, str]]:
        """大文字小文字を無視して lemma を検索し、(id, lemma, sense_title) を返す。無ければ None。

        複合語（空白含む）でも完全一致を前提とする。
        """
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT wp.id, lm.label AS lemma, lm.sense_title
                FROM word_packs AS wp
                JOIN lemmas AS lm ON lm.id = wp.lemma_id
                WHERE lower(lm.label) = lower(?)
                ORDER BY wp.updated_at DESC
                LIMIT 1;
                """,
                (lemma,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return (row["id"], row["lemma"], row["sense_title"])  # type: ignore[return-value]

    # --- Articles operations ---
    def save_article(
        self,
        article_id: str,
        *,
        title_en: str,
        body_en: str,
        body_ja: str,
        notes_ja: str | None,
        llm_model: str | None = None,
        llm_params: str | None = None,
        generation_category: str | None = None,
        related_word_packs: list[tuple[str, str, str]] | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
        generation_started_at: str | None = None,
        generation_completed_at: str | None = None,
        generation_duration_ms: int | None = None,
    ) -> None:
        """記事を保存（upsert）し、関連WordPackリンクも置き換える。

        - related_word_packs: [(word_pack_id, lemma, status), ...]
        """
        now = datetime.now(UTC).isoformat()
        created_at_override = created_at
        updated_at_value = updated_at or now
        generation_started_at_override = generation_started_at or None
        generation_started_at_default = (
            generation_started_at_override or created_at_override or now
        )
        generation_completed_at_override = generation_completed_at or None
        generation_completed_at_default = (
            generation_completed_at_override or updated_at_value or now
        )
        generation_duration_value = (
            None if generation_duration_ms is None else int(generation_duration_ms)
        )
        generation_duration_default = generation_duration_value
        with self._conn() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO articles(
                        id, title_en, body_en, body_ja, notes_ja, llm_model, llm_params, generation_category,
                        created_at, updated_at, generation_started_at, generation_completed_at, generation_duration_ms
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?,
                        COALESCE(?, (SELECT created_at FROM articles WHERE id = ?), ?),
                        ?,
                        COALESCE(?, (SELECT generation_started_at FROM articles WHERE id = ?), ?),
                        COALESCE(?, (SELECT generation_completed_at FROM articles WHERE id = ?), ?),
                        COALESCE(?, (SELECT generation_duration_ms FROM articles WHERE id = ?), ?)
                    );
                    """,
                    (
                        article_id,
                        title_en,
                        body_en,
                        body_ja,
                        (notes_ja or ""),
                        (llm_model or None),
                        (llm_params or None),
                        (generation_category or None),
                        created_at_override,
                        article_id,
                        now,
                        updated_at_value,
                        generation_started_at_override,
                        article_id,
                        generation_started_at_default,
                        generation_completed_at_override,
                        article_id,
                        generation_completed_at_default,
                        generation_duration_value,
                        article_id,
                        generation_duration_default,
                    ),
                )
                if related_word_packs is not None:
                    conn.execute(
                        "DELETE FROM article_word_packs WHERE article_id = ?;",
                        (article_id,),
                    )
                    for wp_id, lemma, status in related_word_packs:
                        conn.execute(
                            """
                            INSERT INTO article_word_packs(article_id, word_pack_id, lemma, status, created_at)
                            VALUES (?, ?, ?, ?, ?);
                            """,
                            (article_id, wp_id, lemma, status, now),
                        )

    def get_article(
        self,
        article_id: str,
    ) -> Optional[
        tuple[
            str,
            str,
            str,
            str | None,
            str | None,
            str | None,
            str | None,
            str,
            str,
            str | None,
            str | None,
            int | None,
            list[tuple[str, str, str]],
        ]
    ]:
        """記事を取得し、関連WordPackリンク一覧を返す。

        戻り値: (title_en, body_en, body_ja, notes_ja, llm_model, llm_params, created_at, updated_at, [(word_pack_id, lemma, status)])
        """
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT
                    title_en,
                    body_en,
                    body_ja,
                    notes_ja,
                    llm_model,
                    llm_params,
                    generation_category,
                    created_at,
                    updated_at,
                    generation_started_at,
                    generation_completed_at,
                    generation_duration_ms
                FROM articles
                WHERE id = ?;
                """,
                (article_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            cur2 = conn.execute(
                """
                SELECT word_pack_id, lemma, status
                FROM article_word_packs
                WHERE article_id = ?
                ORDER BY lemma ASC, word_pack_id ASC;
                """,
                (article_id,),
            )
            links = [
                (r["word_pack_id"], r["lemma"], r["status"]) for r in cur2.fetchall()
            ]
            return (
                row["title_en"],
                row["body_en"],
                row["body_ja"],
                row["notes_ja"],
                row["llm_model"],
                row["llm_params"],
                row["generation_category"],
                row["created_at"],
                row["updated_at"],
                row["generation_started_at"],
                row["generation_completed_at"],
                row["generation_duration_ms"],
                links,
            )

    def list_articles(
        self, limit: int = 50, offset: int = 0
    ) -> list[tuple[str, str, str, str]]:
        """記事一覧: [(id, title_en, created_at, updated_at)] を返す。"""
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT id, title_en, created_at, updated_at
                FROM articles
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
                """,
                (limit, offset),
            )
            return [
                (row["id"], row["title_en"], row["created_at"], row["updated_at"])
                for row in cur.fetchall()
            ]

    def count_articles(self) -> int:
        """記事総件数を返す。"""
        with self._conn() as conn:
            cur = conn.execute("SELECT COUNT(1) AS c FROM articles;")
            row = cur.fetchone()
            return int(row["c"] or 0)

    def delete_article(self, article_id: str) -> bool:
        """記事を削除する（関連リンクも外部キーで削除）。"""
        with self._conn() as conn:
            with conn:
                cur = conn.execute("DELETE FROM articles WHERE id = ?;", (article_id,))
                return cur.rowcount > 0

    def append_examples(
        self, word_pack_id: str, category: str, items: list[dict]
    ) -> int:
        """指定カテゴリに例文を末尾追記し、追加件数を返す。

        - `items`: {en, ja, grammar_ja?, llm_model?, llm_params?, checked_only_count?, learned_count?} の辞書配列
        - `word_packs.updated_at` を現在時刻で更新する
        """
        if not items:
            return 0
        now = datetime.now(UTC).isoformat()
        with self._conn() as conn:
            with conn:
                # 既存の末尾位置を取得
                cur = conn.execute(
                    """
                    SELECT COALESCE(MAX(position), -1) AS max_pos
                    FROM word_pack_examples
                    WHERE word_pack_id = ? AND category = ?;
                    """,
                    (word_pack_id, category),
                )
                row = cur.fetchone()
                start_pos = int(row["max_pos"]) + 1 if row is not None else 0

                # 追記
                inserted = 0
                for offset, item in enumerate(items):
                    en = str((item or {}).get("en") or "").strip()
                    ja = str((item or {}).get("ja") or "").strip()
                    if not en or not ja:
                        continue
                    grammar_ja = (
                        str((item or {}).get("grammar_ja") or "").strip() or None
                    )
                    llm_model = str((item or {}).get("llm_model") or "").strip() or None
                    llm_params = (
                        str((item or {}).get("llm_params") or "").strip() or None
                    )
                    checked_only_count = self._normalize_non_negative_int(
                        (item or {}).get("checked_only_count")
                    )
                    learned_count = self._normalize_non_negative_int(
                        (item or {}).get("learned_count")
                    )
                    conn.execute(
                        """
                        INSERT INTO word_pack_examples(
                            word_pack_id, category, position, en, ja, grammar_ja, llm_model, llm_params,
                            checked_only_count, learned_count, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            word_pack_id,
                            category,
                            start_pos + offset,
                            en,
                            ja,
                            grammar_ja,
                            llm_model,
                            llm_params,
                            checked_only_count,
                            learned_count,
                            now,
                        ),
                    )
                    inserted += 1

                # 本体の updated_at を更新
                conn.execute(
                    "UPDATE word_packs SET updated_at = ? WHERE id = ?;",
                    (now, word_pack_id),
                )

                return inserted

    def count_examples(
        self,
        *,
        search: str | None = None,
        search_mode: str = "contains",
        category: str | None = None,
    ) -> int:
        """正規化テーブルの例文総数（フィルタ適用後）を返す。"""
        with self._conn() as conn:
            where_clauses: list[str] = []
            params: list[object] = []
            if isinstance(category, str) and category:
                where_clauses.append("wpe.category = ?")
                params.append(category)
            if isinstance(search, str) and search.strip():
                q = search.strip()
                if search_mode == "prefix":
                    where_clauses.append("LOWER(wpe.en) LIKE LOWER(?)")
                    params.append(f"{q}%")
                elif search_mode == "suffix":
                    where_clauses.append("LOWER(wpe.en) LIKE LOWER(?)")
                    params.append(f"%{q}")
                else:
                    where_clauses.append("LOWER(wpe.en) LIKE LOWER(?)")
                    params.append(f"%{q}%")
            where_sql = (
                ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            )
            cur = conn.execute(
                f"""
                SELECT COUNT(1) AS c
                FROM word_pack_examples wpe
                JOIN word_packs wp ON wp.id = wpe.word_pack_id
                {where_sql};
                """,
                tuple(params),
            )
            row = cur.fetchone()
            return int(row["c"] or 0)

    def list_examples(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        order_dir: str = "desc",
        search: str | None = None,
        search_mode: str = "contains",
        category: str | None = None,
    ) -> list[
        tuple[int, str, str, str, str, str, str | None, str, str | None, int, int]
    ]:
        """例文一覧（WordPack結合）を返す。

        戻り値: [(id, word_pack_id, lemma, category, en, ja, grammar_ja, created_at, word_pack_updated_at, checked_only, learned)]
        """
        # ORDER BY の安全なマッピング
        order_map = {
            "created_at": "wpe.created_at",
            "pack_updated_at": "wp.updated_at",
            "lemma": "lm.label",
            "category": "wpe.category",
        }
        order_col = order_map.get(order_by, "wpe.created_at")
        order_dir_sql = "DESC" if str(order_dir).lower() == "desc" else "ASC"

        with self._conn() as conn:
            where_clauses: list[str] = []
            params: list[object] = []
            if isinstance(category, str) and category:
                where_clauses.append("wpe.category = ?")
                params.append(category)
            if isinstance(search, str) and search.strip():
                q = search.strip()
                if search_mode == "prefix":
                    where_clauses.append("LOWER(wpe.en) LIKE LOWER(?)")
                    params.append(f"{q}%")
                elif search_mode == "suffix":
                    where_clauses.append("LOWER(wpe.en) LIKE LOWER(?)")
                    params.append(f"%{q}")
                else:
                    where_clauses.append("LOWER(wpe.en) LIKE LOWER(?)")
                    params.append(f"%{q}%")
            where_sql = (
                ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            )

            cur = conn.execute(
                f"""
                SELECT
                    wpe.id AS id,
                    wpe.word_pack_id AS word_pack_id,
                    lm.label AS lemma,
                    wpe.category AS category,
                    wpe.en AS en,
                    wpe.ja AS ja,
                    wpe.grammar_ja AS grammar_ja,
                    wpe.created_at AS created_at,
                    wp.updated_at AS pack_updated_at,
                    wpe.checked_only_count AS checked_only_count,
                    wpe.learned_count AS learned_count
                FROM word_pack_examples wpe
                JOIN word_packs wp ON wp.id = wpe.word_pack_id
                JOIN lemmas lm ON lm.id = wp.lemma_id
                {where_sql}
                ORDER BY {order_col} {order_dir_sql}, wpe.id ASC
                LIMIT ? OFFSET ?;
                """,
                tuple(params + [limit, offset]),
            )
            items: list[
                tuple[
                    int, str, str, str, str, str, str | None, str, str | None, int, int
                ]
            ] = []
            for r in cur.fetchall():
                items.append(
                    (
                        int(r["id"]),
                        r["word_pack_id"],
                        r["lemma"],
                        r["category"],
                        r["en"],
                        r["ja"],
                        r["grammar_ja"],
                        r["created_at"],
                        r["pack_updated_at"],
                        self._normalize_non_negative_int(r["checked_only_count"]),
                        self._normalize_non_negative_int(r["learned_count"]),
                    )
                )
            return items


# module-level singleton store (wired to settings)
store = AppSQLiteStore(db_path=settings.wordpack_db_path)
