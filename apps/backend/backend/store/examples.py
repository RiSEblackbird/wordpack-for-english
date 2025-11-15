from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, datetime
import sqlite3
from typing import Any, ContextManager

from .common import normalize_non_negative_int

EXAMPLE_CATEGORIES: tuple[str, ...] = ("Dev", "CS", "LLM", "Business", "Common")


def ensure_tables(conn: sqlite3.Connection) -> None:
    """例文正規化テーブルを初期化する。"""

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
            transcription_typing_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(word_pack_id) REFERENCES word_packs(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_wpex_pack ON word_pack_examples(word_pack_id);"
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wpex_pack_cat_pos
        ON word_pack_examples(word_pack_id, category, position);
        """
    )
    cur = conn.execute("PRAGMA table_info(word_pack_examples);")
    column_names = {str(row["name"]) for row in cur.fetchall()}
    if "transcription_typing_count" not in column_names:
        conn.execute(
            """
            ALTER TABLE word_pack_examples
            ADD COLUMN transcription_typing_count INTEGER NOT NULL DEFAULT 0;
            """
        )


class ExampleStore:
    """WordPack 配下の例文を扱う永続化ロジック。"""

    def __init__(
        self, conn_provider: Callable[[], ContextManager[sqlite3.Connection]]
    ) -> None:
        self._conn_provider = conn_provider

    def update_example_study_progress(
        self, example_id: int, checked_increment: int, learned_increment: int
    ) -> tuple[str, int, int] | None:
        """例文単位の学習進捗カウンタを加算し、更新後の値を返す。

        カウンタは学習履歴の UI と同期されているため、欠番や負値を許すと
        一貫した進捗率が算出できなくなる。ここで非負に正規化したうえで更新する。"""

        with self._conn_provider() as conn:
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
                current_checked = normalize_non_negative_int(row["checked_only_count"])
                current_learned = normalize_non_negative_int(row["learned_count"])
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
                return (str(row["word_pack_id"]), next_checked, next_learned)

    def delete_example(
        self, word_pack_id: str, category: str, index: int
    ) -> int | None:
        """指定カテゴリ内の index の例文を削除し、残件数を返す。

        SQLite の position 列は UI 側での順序維持に利用するため、削除後に
        0..N-1 の連番へ詰め直す。欠番を放置するとクライアントが position を
        再利用した際に例文が重複してしまうためである。"""

        if index < 0:
            return None
        with self._conn_provider() as conn:
            with conn:
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
                conn.execute(
                    "DELETE FROM word_pack_examples WHERE id = ?;", (target_id,)
                )
                remaining = self._reindex_category(conn, word_pack_id, category)
                return remaining

    def delete_examples_by_ids(
        self, example_ids: Iterable[int]
    ) -> tuple[int, list[int]]:
        """例文IDの配列を受け取り、一括削除する。

        まとめて削除してもカテゴリ内の position は欠番にしないため、触れたカテゴリを
        再採番して UI 側での順序崩れを防ぐ。"""

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

        with self._conn_provider() as conn:
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
                    self._reindex_category(conn, str(word_pack_id), str(category))

        return deleted, not_found

    def append_examples(
        self, word_pack_id: str, category: str, items: Sequence[Mapping[str, Any]]
    ) -> int:
        """指定カテゴリへ例文を末尾追記し、追加件数を返す。

        WordPack の updated_at も同時に進めることで、例文追加がタイムラインから
        追跡できるようにしている。"""

        if not items:
            return 0
        now = datetime.now(UTC).isoformat()
        with self._conn_provider() as conn:
            with conn:
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
                inserted = 0
                for offset, item in enumerate(items):
                    en = str((item or {}).get("en") or "").strip()
                    ja = str((item or {}).get("ja") or "").strip()
                    if not en or not ja:
                        continue
                    grammar_ja = str((item or {}).get("grammar_ja") or "").strip() or None
                    llm_model = str((item or {}).get("llm_model") or "").strip() or None
                    llm_params = str((item or {}).get("llm_params") or "").strip() or None
                    checked_only_count = normalize_non_negative_int(
                        (item or {}).get("checked_only_count")
                    )
                    learned_count = normalize_non_negative_int(
                        (item or {}).get("learned_count")
                    )
                    conn.execute(
                        """
                        INSERT INTO word_pack_examples(
                            word_pack_id, category, position, en, ja, grammar_ja, llm_model, llm_params,
                            checked_only_count, learned_count, transcription_typing_count, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
                            normalize_non_negative_int(
                                (item or {}).get("transcription_typing_count")
                            ),
                            now,
                        ),
                    )
                    inserted += 1
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
        """検索条件付きで例文件数を返す。"""

        with self._conn_provider() as conn:
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
            where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
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
        tuple[int, str, str, str, str, str, str | None, str, str | None, int, int, int]
    ]:
        """検索条件付きで例文を取得する。"""

        order_map = {
            "created_at": "wpe.created_at",
            "pack_updated_at": "wp.updated_at",
            "lemma": "lm.label",
            "category": "wpe.category",
        }
        order_col = order_map.get(order_by, "wpe.created_at")
        order_dir_sql = "DESC" if str(order_dir).lower() == "desc" else "ASC"

        with self._conn_provider() as conn:
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
            where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
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
                    wpe.learned_count AS learned_count,
                    wpe.transcription_typing_count AS transcription_typing_count
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
                tuple[int, str, str, str, str, str, str | None, str, str | None, int, int, int]
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
                        normalize_non_negative_int(r["checked_only_count"]),
                        normalize_non_negative_int(r["learned_count"]),
                        normalize_non_negative_int(r["transcription_typing_count"]),
                    )
                )
            return items

    def update_example_transcription_typing(
        self, example_id: int, input_length: int
    ) -> int | None:
        """文字起こし練習の入力長をバリデートし、累積カウントへ加算する。"""

        try:
            normalized_length = int(input_length)
        except (TypeError, ValueError) as exc:  # 異常な入力は 422 相当へ委譲
            raise ValueError("input length must be convertible to int") from exc
        if normalized_length <= 0:
            raise ValueError("input length must be positive")

        with self._conn_provider() as conn:
            with conn:
                cur = conn.execute(
                    """
                    SELECT en, transcription_typing_count
                    FROM word_pack_examples
                    WHERE id = ?;
                    """,
                    (example_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None

                expected_length = len(str(row["en"] or ""))
                # なぜ: UI 側が送る入力長は英文長とほぼ一致するため、乖離が±10文字を
                # 超えた場合は異常入力として弾く。これは bot などによる加算誤用防止策。
                if abs(expected_length - normalized_length) > 10:
                    raise ValueError(
                        "input length deviates from sentence length beyond tolerance"
                    )

                current = normalize_non_negative_int(row["transcription_typing_count"])
                updated = current + normalized_length
                conn.execute(
                    """
                    UPDATE word_pack_examples
                    SET transcription_typing_count = ?
                    WHERE id = ?;
                    """,
                    (updated, example_id),
                )
                return updated

    def _reindex_category(
        self, conn: sqlite3.Connection, word_pack_id: str, category: str
    ) -> int:
        cur = conn.execute(
            """
            SELECT id FROM word_pack_examples
            WHERE word_pack_id = ? AND category = ?
            ORDER BY position ASC, id ASC;
            """,
            (word_pack_id, category),
        )
        ids = [int(r["id"]) for r in cur.fetchall()]
        for new_pos, rid in enumerate(ids):
            conn.execute(
                "UPDATE word_pack_examples SET position = ? WHERE id = ?;",
                (new_pos, rid),
            )
        return len(ids)


def iter_example_rows(examples: Mapping[str, Any]) -> Iterable[tuple]:
    """保存用に examples ペイロードを正規化し、挿入レコードを返す。"""

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
            checked_only_count = normalize_non_negative_int(
                (item or {}).get("checked_only_count")
            )
            learned_count = normalize_non_negative_int((item or {}).get("learned_count"))
            transcription_typing_count = normalize_non_negative_int(
                (item or {}).get("transcription_typing_count")
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
                transcription_typing_count,
            )
