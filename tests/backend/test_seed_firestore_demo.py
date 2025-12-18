from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import sys

import pytest

# ルート（apps/backend 配下）を解決できるようにパスを調整。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "backend"))

from backend.seed_firestore_demo import seed_firestore_from_sqlite  # noqa: E402
from backend.store.firestore_store import AppFirestoreStore  # noqa: E402
from tests.firestore_fakes import FakeFirestoreClient  # noqa: E402


def _prepare_demo_sqlite(tmp_path: Path) -> Path:
    """最小限のデモデータを含む SQLite DB を生成する。"""

    db_path = tmp_path / "demo.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE word_packs (
            id TEXT PRIMARY KEY,
            lemma TEXT NOT NULL,
            sense_title TEXT NOT NULL DEFAULT '',
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            checked_only_count INTEGER NOT NULL DEFAULT 0,
            learned_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE word_pack_examples (
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
            checked_only_count INTEGER NOT NULL DEFAULT 0,
            learned_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE articles (
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
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE article_word_packs (
            article_id TEXT NOT NULL,
            word_pack_id TEXT NOT NULL,
            lemma TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(article_id, word_pack_id)
        )
        """
    )

    core_payload = {
        "lemma": "bottleneck",
        "sense_title": "ボトルネック",
        "examples": {"Dev": []},
    }
    conn.execute(
        """
        INSERT INTO word_packs (id, lemma, sense_title, data, created_at, updated_at, checked_only_count, learned_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "wp-1",
            "bottleneck",
            "bottleneck",
            json.dumps(core_payload, ensure_ascii=False),
            "2024-01-01T00:00:00+00:00",
            "2024-01-02T00:00:00+00:00",
            2,
            1,
        ),
    )
    conn.execute(
        """
        INSERT INTO word_pack_examples (word_pack_id, category, position, en, ja, grammar_ja, llm_model, llm_params, created_at, checked_only_count, learned_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "wp-1",
            "Dev",
            0,
            "Resolve the bottleneck in the pipeline.",
            "パイプラインのボトルネックを解消する。",
            "grammar note",
            "gpt-4o-mini",
            '{"temperature":0.1}',
            "2024-01-02T00:00:00+00:00",
            1,
            0,
        ),
    )

    conn.execute(
        """
        INSERT INTO articles (id, title_en, body_en, body_ja, notes_ja, llm_model, llm_params, generation_category, created_at, updated_at, generation_started_at, generation_completed_at, generation_duration_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "article-1",
            "Demo Article",
            "Body EN",
            "Body JA",
            "note",
            "gpt-4o-mini",
            "{}",
            "demo",
            "2024-01-03T00:00:00+00:00",
            "2024-01-04T00:00:00+00:00",
            "2024-01-03T00:00:00+00:00",
            "2024-01-04T00:00:00+00:00",
            1200,
        ),
    )
    conn.execute(
        """
        INSERT INTO article_word_packs (article_id, word_pack_id, lemma, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("article-1", "wp-1", "bottleneck", "existing", "2024-01-03T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()
    return db_path


def test_seed_firestore_from_sqlite_moves_wordpacks_and_articles(tmp_path: Path) -> None:
    """SQLite デモ DB の内容が Firestore ストアへ移行されることを確認する。"""

    db_path = _prepare_demo_sqlite(tmp_path)
    store = AppFirestoreStore(client=FakeFirestoreClient())

    wp_count, article_count = seed_firestore_from_sqlite(db_path, store)

    assert wp_count == 1
    assert article_count == 1

    stored = store.get_word_pack("wp-1")
    assert stored is not None
    lemma, data_json, created_at, updated_at = stored
    assert lemma == "bottleneck"
    assert created_at <= updated_at
    payload = json.loads(data_json)
    assert payload["checked_only_count"] == 2
    assert payload["learned_count"] == 1
    assert payload["examples"]["Dev"][0]["en"] == "Resolve the bottleneck in the pipeline."
    assert payload["examples"]["Dev"][0]["llm_model"] == "gpt-4o-mini"
    article = store.articles.get_article("article-1")
    assert article is not None
    assert article[0] == "Demo Article"
    assert article[-1] == [("wp-1", "bottleneck", "existing")]

