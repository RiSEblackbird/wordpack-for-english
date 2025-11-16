from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from ..config import settings
from . import articles, examples, users, wordpacks
from .firestore_store import AppFirestoreStore
from .examples import EXAMPLE_CATEGORIES


class AppSQLiteStore:
    """SQLite を用いた WordPack 向け永続化レイヤーのファサード。"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_dirs()
        self._init_db()
        self.users = users.UserStore(self._conn)
        self.wordpacks = wordpacks.WordPackStore(self._conn)
        self.examples = examples.ExampleStore(self._conn)
        self.articles = articles.ArticleStore(self._conn)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path, timeout=10.0, isolation_level=None, check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        with conn:
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

    def _init_db(self) -> None:
        with self._conn() as conn:
            with conn:
                users.ensure_tables(conn)
                wordpacks.ensure_tables(conn)
                examples.ensure_tables(conn)
                articles.ensure_tables(conn)

    # --- Users ---
    def record_user_login(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str,
        login_at: datetime | None = None,
    ) -> dict[str, str]:
        return self.users.record_user_login(
            google_sub=google_sub,
            email=email,
            display_name=display_name,
            login_at=login_at,
        )

    def get_user_by_google_sub(self, google_sub: str) -> dict[str, str] | None:
        return self.users.get_user_by_google_sub(google_sub)

    def delete_user(self, google_sub: str) -> None:
        self.users.delete_user(google_sub)

    # --- WordPacks ---
    def save_word_pack(self, word_pack_id: str, lemma: str, data: str) -> None:
        self.wordpacks.save_word_pack(word_pack_id, lemma, data)

    def get_word_pack(self, word_pack_id: str) -> tuple[str, str, str, str] | None:
        return self.wordpacks.get_word_pack(word_pack_id)

    def list_word_packs(
        self, limit: int = 50, offset: int = 0
    ) -> list[tuple[str, str, str, str, str]]:
        return self.wordpacks.list_word_packs(limit=limit, offset=offset)

    def count_word_packs(self) -> int:
        return self.wordpacks.count_word_packs()

    def list_word_packs_with_flags(
        self, limit: int = 50, offset: int = 0
    ) -> list[tuple[str, str, str, str, str, bool, dict[str, int], int, int]]:
        return [
            (
                item[0],
                item[1],
                item[2],
                item[3],
                item[4],
                item[5],
                dict(item[6]),
                item[7],
                item[8],
            )
            for item in self.wordpacks.list_word_packs_with_flags(limit=limit, offset=offset)
        ]

    def delete_word_pack(self, word_pack_id: str) -> bool:
        return self.wordpacks.delete_word_pack(word_pack_id)

    def update_word_pack_study_progress(
        self, word_pack_id: str, checked_increment: int, learned_increment: int
    ) -> tuple[int, int] | None:
        return self.wordpacks.update_word_pack_study_progress(
            word_pack_id, checked_increment, learned_increment
        )

    def find_word_pack_id_by_lemma(self, lemma: str) -> str | None:
        return self.wordpacks.find_word_pack_id_by_lemma(lemma)

    def find_word_pack_by_lemma_ci(
        self, lemma: str
    ) -> tuple[str, str, str] | None:
        return self.wordpacks.find_word_pack_by_lemma_ci(lemma)

    # --- Examples ---
    def update_example_study_progress(
        self, example_id: int, checked_increment: int, learned_increment: int
    ) -> tuple[str, int, int] | None:
        return self.examples.update_example_study_progress(
            example_id, checked_increment, learned_increment
        )

    def delete_example(
        self, word_pack_id: str, category: str, index: int
    ) -> int | None:
        return self.examples.delete_example(word_pack_id, category, index)

    def delete_examples_by_ids(
        self, example_ids: Iterable[int]
    ) -> tuple[int, list[int]]:
        return self.examples.delete_examples_by_ids(example_ids)

    def append_examples(
        self, word_pack_id: str, category: str, items: Sequence[Mapping[str, Any]]
    ) -> int:
        return self.examples.append_examples(word_pack_id, category, items)

    def count_examples(
        self,
        *,
        search: str | None = None,
        search_mode: str = "contains",
        category: str | None = None,
    ) -> int:
        return self.examples.count_examples(
            search=search, search_mode=search_mode, category=category
        )

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
        return self.examples.list_examples(
            limit=limit,
            offset=offset,
            order_by=order_by,
            order_dir=order_dir,
            search=search,
            search_mode=search_mode,
            category=category,
        )

    def update_example_transcription_typing(
        self, example_id: int, input_length: int
    ) -> int | None:
        """例文の文字起こし練習カウンタを更新するラッパー。"""

        return self.examples.update_example_transcription_typing(example_id, input_length)

    # --- Articles ---
    def save_article(self, article_id: str, **kwargs: Any) -> None:
        self.articles.save_article(article_id, **kwargs)

    # --- Internal compatibility helpers for tests ---
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
        """`WordPackStore._upsert_lemma` への委譲ラッパー。

        既存テストが AppSQLiteStore 経由でプライベートAPIを参照しているため、
        backend.providers の再構成後も互換性を維持するために残している。
        """

        return self.wordpacks._upsert_lemma(  # type: ignore[attr-defined]
            conn,
            label=label,
            sense_title=sense_title,
            llm_model=llm_model,
            llm_params=llm_params,
            now=now,
        )

    def get_article(
        self, article_id: str
    ) -> tuple[
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
    ] | None:
        return self.articles.get_article(article_id)

    def list_articles(self, limit: int = 50, offset: int = 0) -> list[tuple[str, str, str, str]]:
        return self.articles.list_articles(limit=limit, offset=offset)

    def count_articles(self) -> int:
        return self.articles.count_articles()

    def delete_article(self, article_id: str) -> bool:
        return self.articles.delete_article(article_id)


def _create_store() -> AppSQLiteStore | AppFirestoreStore:
    env = (settings.environment or "").strip().lower()
    if env == "production":
        return AppFirestoreStore()
    return AppSQLiteStore(db_path=settings.wordpack_db_path)


store = _create_store()

__all__ = [
    "AppSQLiteStore",
    "AppFirestoreStore",
    "store",
    "EXAMPLE_CATEGORIES",
]
