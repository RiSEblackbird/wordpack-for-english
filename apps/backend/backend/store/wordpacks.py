from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, ContextManager

from ..sense_title import choose_sense_title
from .common import normalize_non_negative_int
from .examples import EXAMPLE_CATEGORIES, iter_example_rows


def ensure_tables(conn: sqlite3.Connection) -> None:
    """見出し語と WordPack 本体のテーブルを初期化する。"""

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


class WordPackStore:
    """WordPack 本体と付随するメタ情報を扱う。"""

    def __init__(self, conn_provider: Callable[[], ContextManager[sqlite3.Connection]]):
        self._conn_provider = conn_provider

    def save_word_pack(self, word_pack_id: str, lemma: str, data: str) -> None:
        """WordPack を保存する。

        例文は UI 側で細かく更新されるため、JSON から抽出して正規化テーブルへ格納し、
        本体の JSON には再利用可能なコア情報のみを残す。"""

        now = datetime.now(UTC).isoformat()
        (
            core_json,
            examples,
            sense_title_raw,
            sense_candidates,
            (checked_only_count, learned_count),
            (lemma_llm_model, lemma_llm_params),
        ) = split_examples_from_payload(data)
        sense_title = choose_sense_title(
            sense_title_raw,
            sense_candidates,
            lemma=lemma,
            limit=40,
        )

        with self._conn_provider() as conn:
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
                        checked_count,
                        learned_count,
                        transcription_typing_count,
                    ) in iter_example_rows(examples):
                        conn.execute(
                            """
                            INSERT INTO word_pack_examples(
                                word_pack_id, category, position, en, ja, grammar_ja, llm_model, llm_params,
                                checked_only_count, learned_count, transcription_typing_count, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
                                checked_count,
                                learned_count,
                                transcription_typing_count,
                                now,
                            ),
                        )

    def get_word_pack(self, word_pack_id: str) -> tuple[str, str, str, str] | None:
        """WordPack を取得し、例文をマージした JSON を返す。"""

        with self._conn_provider() as conn:
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
            data_json = merge_core_with_examples(row["data"], rows)
            try:
                data_dict = json.loads(data_json) if data_json else {}
            except Exception:
                data_dict = {}
            data_dict["checked_only_count"] = normalize_non_negative_int(
                row["checked_only_count"]
            )
            data_dict["learned_count"] = normalize_non_negative_int(row["learned_count"])
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
        """WordPack のメタ情報を一覧で返す。"""

        with self._conn_provider() as conn:
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
        """WordPack 件数を返す。"""

        with self._conn_provider() as conn:
            cur = conn.execute("SELECT COUNT(1) AS c FROM word_packs;")
            row = cur.fetchone()
            return int(row["c"]) if row is not None else 0

    def list_word_packs_with_flags(
        self, limit: int = 50, offset: int = 0
    ) -> list[tuple[str, str, str, str, str, bool, Mapping[str, int], int, int]]:
        """一覧表示に必要なフラグを付与して返す。

        `is_empty` は例文件数のみで概算しており、一覧を高速化しつつ UI 側の
        表示崩れを防ぐための妥協である。カテゴリ別件数も同時に返し、空判定を
        後段のサービスで細かく再評価できるようにしている。"""

        with self._conn_provider() as conn:
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
            items: list[tuple[str, str, str, str, str, bool, Mapping[str, int], int, int]] = []
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
                checked_only = normalize_non_negative_int(row["checked_only_count"])
                learned = normalize_non_negative_int(row["learned_count"])
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
        """WordPack を削除する。"""

        with self._conn_provider() as conn:
            with conn:
                cur = conn.execute(
                    "DELETE FROM word_packs WHERE id = ?;", (word_pack_id,)
                )
                return cur.rowcount > 0

    def update_word_pack_study_progress(
        self, word_pack_id: str, checked_increment: int, learned_increment: int
    ) -> tuple[int, int] | None:
        """WordPack 単位の学習進捗カウンタを更新する。

        学習記録のグラフは累積値を前提としているため、サーバー側で非負に正規化し
        過去の履歴を壊さないようにしている。"""

        with self._conn_provider() as conn:
            with conn:
                cur = conn.execute(
                    """
                    SELECT checked_only_count, learned_count
                    FROM word_packs
                    WHERE id = ?;
                    """,
                    (word_pack_id,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                current_checked = normalize_non_negative_int(
                    row["checked_only_count"]
                )
                current_learned = normalize_non_negative_int(row["learned_count"])
                next_checked = max(0, current_checked + int(checked_increment))
                next_learned = max(0, current_learned + int(learned_increment))
                if next_checked != current_checked or next_learned != current_learned:
                    conn.execute(
                        "UPDATE word_packs SET checked_only_count = ?, learned_count = ? WHERE id = ?;",
                        (next_checked, next_learned, word_pack_id),
                    )
                return next_checked, next_learned

    def find_word_pack_id_by_lemma(
        self, lemma: str, *, diagnostics: bool = False
    ) -> str | None | tuple[str | None, bool]:
        """見出し語に対応する最新 WordPack ID を返す。"""

        normalized_lemma = str(lemma or "").strip()
        # SQLite 側でも Firestore 側と同様に大文字小文字を無視した検索を行うため、
        # 正規化した見出し語を lower 比較に揃えて検索する。
        with self._conn_provider() as conn:
            cur = conn.execute(
                """
                SELECT wp.id
                FROM word_packs AS wp
                JOIN lemmas AS lm ON lm.id = wp.lemma_id
                WHERE lower(lm.label) = lower(?)
                ORDER BY wp.updated_at DESC
                LIMIT 1;
                """,
                (normalized_lemma,),
            )
            row = cur.fetchone()
            result = row["id"] if row is not None else None
            return (result, False) if diagnostics else result

    def find_word_pack_by_lemma_ci(
        self, lemma: str
    ) -> tuple[str, str, str] | None:
        """大文字小文字を無視して WordPack を探す。"""

        with self._conn_provider() as conn:
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
                learned_count,
                transcription_typing_count
            FROM word_pack_examples
            WHERE word_pack_id = ?
            ORDER BY category ASC, position ASC, id ASC;
            """,
            (word_pack_id,),
        )
        return cur.fetchall()

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
        new_label = stored_label if stored_label.lower() == original_label.lower() else original_label or stored_label
        stripped_sense = str(sense_title or "").strip()
        stored_sense_title = str(row["sense_title"] or "")
        new_sense_title = stored_sense_title or stripped_sense
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


def split_examples_from_payload(
    data: str | Mapping[str, Any]
) -> tuple[
    str,
    Mapping[str, Any] | None,
    str,
    list[str],
    tuple[int, int],
    tuple[str | None, str | None],
]:
    """JSON から例文を抽出し、本体とメタ情報を分離する。"""

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
        checked_only_count = normalize_non_negative_int((parsed or {}).get("checked_only_count"))
    except Exception:
        checked_only_count = 0
    try:
        learned_count = normalize_non_negative_int((parsed or {}).get("learned_count"))
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


def merge_core_with_examples(
    core_json: str, rows: Sequence[Mapping[str, Any] | sqlite3.Row]
) -> str:
    """WordPack 本体 JSON に例文を合成して返す。"""

    try:
        core = json.loads(core_json) if core_json else {}
    except Exception:
        core = {}
    examples: dict[str, list[dict[str, Any]]] = {cat: [] for cat in EXAMPLE_CATEGORIES}
    for r in rows:
        category = r["category"]
        item: dict[str, Any] = {"en": r["en"], "ja": r["ja"]}
        if r["grammar_ja"]:
            item["grammar_ja"] = r["grammar_ja"]
        if r["llm_model"]:
            item["llm_model"] = r["llm_model"]
        if r["llm_params"]:
            item["llm_params"] = r["llm_params"]
        item["checked_only_count"] = normalize_non_negative_int(r["checked_only_count"])
        item["learned_count"] = normalize_non_negative_int(r["learned_count"])
        item["transcription_typing_count"] = normalize_non_negative_int(
            r["transcription_typing_count"]
        )
        examples.setdefault(category, []).append(item)
    for cat in EXAMPLE_CATEGORIES:
        examples.setdefault(cat, [])
    core["examples"] = examples
    return json.dumps(core, ensure_ascii=False)
