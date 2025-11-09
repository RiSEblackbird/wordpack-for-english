from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import sqlite3
from typing import ContextManager


def ensure_tables(conn: sqlite3.Connection) -> None:
    """ユーザー情報テーブルを初期化する。"""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            google_sub TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            display_name TEXT NOT NULL,
            last_login_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_users_email_ci ON users(lower(email));"
    )


class UserStore:
    """Google OAuth 由来のユーザー情報を扱う。"""

    def __init__(self, conn_provider: Callable[[], ContextManager[sqlite3.Connection]]):
        self._conn_provider = conn_provider

    def record_user_login(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str,
        login_at: datetime | None = None,
    ) -> dict[str, str]:
        """ログイン情報を upsert し、保存結果を返す。

        Google 側のプロファイルは随時変化するため、subject をキーとした upsert によって
        最新のメールアドレス/表示名を常に保持する。"""

        login_time = (login_at or datetime.now(UTC)).replace(microsecond=0)
        with self._conn_provider() as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO users (google_sub, email, display_name, last_login_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(google_sub) DO UPDATE SET
                        email = excluded.email,
                        display_name = excluded.display_name,
                        last_login_at = excluded.last_login_at;
                    """,
                    (
                        google_sub,
                        email,
                        display_name,
                        login_time.isoformat(),
                    ),
                )
        user = self.get_user_by_google_sub(google_sub)
        if user is None:  # pragma: no cover - defensive fallback
            raise RuntimeError("failed to persist user login")
        return user

    def get_user_by_google_sub(self, google_sub: str) -> dict[str, str] | None:
        """subject でユーザーを取得する。"""

        with self._conn_provider() as conn:
            cur = conn.execute(
                "SELECT google_sub, email, display_name, last_login_at FROM users WHERE google_sub = ?;",
                (google_sub,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return {
            "google_sub": str(row["google_sub"]),
            "email": str(row["email"]),
            "display_name": str(row["display_name"]),
            "last_login_at": str(row["last_login_at"]),
        }

    def delete_user(self, google_sub: str) -> None:
        """subject をキーにユーザーを削除する。"""

        with self._conn_provider() as conn:
            with conn:
                conn.execute(
                    "DELETE FROM users WHERE google_sub = ?;",
                    (google_sub,),
                )
