from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import sqlite3
from typing import ContextManager


def ensure_tables(conn: sqlite3.Connection) -> None:
    """記事テーブルと関連 WordPack リンクテーブルを初期化する。"""

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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS article_word_packs (
            article_id TEXT NOT NULL,
            word_pack_id TEXT NOT NULL,
            lemma TEXT NOT NULL,
            status TEXT NOT NULL,
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


class ArticleStore:
    """記事本文と WordPack リンクの永続化を担当する。"""

    def __init__(self, conn_provider: Callable[[], ContextManager[sqlite3.Connection]]):
        self._conn_provider = conn_provider

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
        """記事を upsert し、リンクテーブルも一括置換する。

        生成中に再保存されても作成時刻を固定し、リンクは置き換えで整合性を保つ。"""

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
        with self._conn_provider() as conn:
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
    ) -> (
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
        | None
    ):
        """記事と関連 WordPack の情報を返す。"""

        with self._conn_provider() as conn:
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

    def list_articles(self, limit: int = 50, offset: int = 0) -> list[tuple[str, str, str, str]]:
        """記事一覧のサマリーを返す。"""

        with self._conn_provider() as conn:
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
        """記事件数を返す。"""

        with self._conn_provider() as conn:
            cur = conn.execute("SELECT COUNT(1) AS c FROM articles;")
            row = cur.fetchone()
            return int(row["c"] or 0)

    def delete_article(self, article_id: str) -> bool:
        """記事を削除する。関連レコードは外部キー制約で自動削除される。"""

        with self._conn_provider() as conn:
            with conn:
                cur = conn.execute("DELETE FROM articles WHERE id = ?;", (article_id,))
                return cur.rowcount > 0
