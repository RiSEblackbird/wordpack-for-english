from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .store.common import normalize_non_negative_int
from .store.examples import EXAMPLE_CATEGORIES
from .store.firestore_store import AppFirestoreStore


# なぜ: WordPack 本体スキーマを変更せず、Firestore 側の metadata でゲスト用データを識別するため。
_GUEST_DEMO_METADATA = {"guest_demo": True}


@dataclass(frozen=True)
class DemoWordPack:
    """SQLite デモデータから組み立てた WordPack 1 件分のペイロード。"""

    word_pack_id: str
    lemma: str
    payload_json: str


@dataclass(frozen=True)
class DemoArticle:
    """SQLite デモデータから復元した記事データ。"""

    article_id: str
    payload: dict[str, Any]
    related_word_packs: list[tuple[str, str, str]]


def _build_examples_map(conn: sqlite3.Connection, word_pack_id: str) -> dict[str, list[dict[str, Any]]]:
    """WordPack に紐付く例文をカテゴリ別にまとめる。

    なぜ: Firestore 側はカテゴリごとの配列を受け取る形なので、SQLite の行データを
    事前にカテゴリ単位へグルーピングしておくと変換処理が明瞭になるため。
    """

    grouped: dict[str, list[dict[str, Any]]] = {cat: [] for cat in EXAMPLE_CATEGORIES}
    cursor = conn.execute(
        """
        SELECT category, position, en, ja, grammar_ja, llm_model, llm_params,
               checked_only_count, learned_count
        FROM word_pack_examples
        WHERE word_pack_id = ?
        ORDER BY category, position, id
        """,
        (word_pack_id,),
    )
    for row in cursor.fetchall():
        category = str(row[0] or "")
        entry = {
            "en": str(row[2] or "").strip(),
            "ja": str(row[3] or "").strip(),
            "grammar_ja": (row[4] or "") or None,
            "llm_model": (row[5] or "") or None,
            "llm_params": (row[6] or "") or None,
            "checked_only_count": normalize_non_negative_int(row[7]),
            "learned_count": normalize_non_negative_int(row[8]),
            # SQLite には未保存だが Firestore 側の型と整合させるために 0 で初期化。
            "transcription_typing_count": 0,
        }
        grouped.setdefault(category, []).append(entry)
    for category in EXAMPLE_CATEGORIES:
        grouped.setdefault(category, [])
    return grouped


def _merge_payload(
    raw_json: str,
    examples: dict[str, list[dict[str, Any]]],
    *,
    checked_only_count: int,
    learned_count: int,
) -> str:
    """SQLite 側のコア JSON と例文を合成し、Firestore 格納用に整形する。"""

    try:
        payload = json.loads(raw_json) if raw_json else {}
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload["examples"] = examples
    payload["checked_only_count"] = normalize_non_negative_int(checked_only_count)
    payload["learned_count"] = normalize_non_negative_int(learned_count)
    if not payload.get("sense_title"):
        payload["sense_title"] = payload.get("lemma") or ""
    payload.setdefault("lemma", "")
    return json.dumps(payload, ensure_ascii=False)


def _load_word_packs(conn: sqlite3.Connection) -> list[DemoWordPack]:
    """SQLite から WordPack 行を読み込み、Firestore へ送れる形へまとめる。"""

    packs: list[DemoWordPack] = []
    cursor = conn.execute(
        """
        SELECT id, lemma, data, checked_only_count, learned_count
        FROM word_packs
        ORDER BY created_at ASC
        """
    )
    for row in cursor.fetchall():
        pack_id = str(row[0])
        lemma = str(row[1] or "")
        raw_json = str(row[2] or "{}")
        checked_only_count = row[3]
        learned_count = row[4]
        examples = _build_examples_map(conn, pack_id)
        payload = _merge_payload(
            raw_json,
            examples,
            checked_only_count=checked_only_count,
            learned_count=learned_count,
        )
        packs.append(DemoWordPack(word_pack_id=pack_id, lemma=lemma, payload_json=payload))
    return packs


def _load_articles(conn: sqlite3.Connection) -> list[DemoArticle]:
    """記事テーブルと紐付きを Firestore 移行用にまとめる。"""

    related: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    link_cursor = conn.execute(
        """
        SELECT article_id, word_pack_id, lemma, status
        FROM article_word_packs
        ORDER BY created_at ASC
        """
    )
    for row in link_cursor.fetchall():
        article_id = str(row[0])
        related[article_id].append((str(row[1]), str(row[2] or ""), str(row[3] or "")))

    articles: list[DemoArticle] = []
    cursor = conn.execute(
        """
        SELECT id, title_en, body_en, body_ja, notes_ja, llm_model, llm_params,
               generation_category, created_at, updated_at,
               generation_started_at, generation_completed_at, generation_duration_ms
        FROM articles
        ORDER BY created_at ASC
        """
    )
    for row in cursor.fetchall():
        article_id = str(row[0])
        payload = {
            "title_en": row[1],
            "body_en": row[2],
            "body_ja": row[3],
            "notes_ja": row[4],
            "llm_model": row[5],
            "llm_params": row[6],
            "generation_category": row[7],
            "created_at": row[8],
            "updated_at": row[9],
            "generation_started_at": row[10],
            "generation_completed_at": row[11],
            "generation_duration_ms": row[12],
        }
        articles.append(
            DemoArticle(
                article_id=article_id,
                payload=payload,
                related_word_packs=related.get(article_id, []),
            )
        )
    return articles


def seed_firestore_from_sqlite(
    sqlite_path: Path,
    store: AppFirestoreStore,
    *,
    reset_example_counter: bool = True,
) -> tuple[int, int]:
    """SQLite デモ DB から Firestore（本番/エミュレータ）へデータを流し込む。

    - reset_example_counter=true の場合、example_counters を 1 に戻して ID を安定化。
    - 返り値は (WordPack 件数, Article 件数)。
    """

    if not sqlite_path.exists():
        msg = f"SQLite demo file not found: {sqlite_path}"
        raise FileNotFoundError(msg)

    with closing(sqlite3.connect(sqlite_path)) as conn:
        conn.row_factory = sqlite3.Row
        word_packs = _load_word_packs(conn)
        articles = _load_articles(conn)

    if reset_example_counter:
        store.wordpacks._metadata.document("example_counters").set({"next_id": 1})

    for pack in word_packs:
        store.save_word_pack(
            pack.word_pack_id,
            pack.lemma,
            pack.payload_json,
            metadata=_GUEST_DEMO_METADATA,
        )

    for article in articles:
        store.articles.save_article(
            article.article_id,
            **article.payload,
            related_word_packs=article.related_word_packs,
        )

    return len(word_packs), len(articles)


def seed_firestore_from_sqlite_if_missing_guest_demo(
    sqlite_path: Path,
    store: AppFirestoreStore,
    *,
    reset_example_counter: bool = True,
) -> tuple[int, int]:
    """ゲスト用のデモデータが未投入の場合のみ SQLite デモデータを反映する。"""

    if store.has_guest_demo_word_pack():
        return 0, 0

    return seed_firestore_from_sqlite(
        sqlite_path,
        store,
        reset_example_counter=reset_example_counter,
    )
