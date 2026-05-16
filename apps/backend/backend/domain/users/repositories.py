from __future__ import annotations

from datetime import datetime
from typing import Protocol


class UserRepository(Protocol):
    def record_user_login(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str,
        login_at: datetime | None = None,
    ) -> dict[str, str]:
        ...

    def get_user_by_google_sub(self, google_sub: str) -> dict[str, str] | None:
        ...

    def delete_user(self, google_sub: str) -> None:
        ...
