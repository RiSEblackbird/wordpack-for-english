from __future__ import annotations

from .base import UTC, datetime, firestore, FirestoreBaseRepository


class FirestoreUserRepository(FirestoreBaseRepository):
    """Firestore 上のユーザードキュメントを管理する。"""

    def record_user_login(
        self,
        *,
        google_sub: str,
        email: str,
        display_name: str,
        login_at: datetime | None = None,
    ) -> dict[str, str]:
        login_time = (login_at or datetime.now(UTC)).replace(microsecond=0)
        doc_ref = self._client.collection("users").document(google_sub)
        doc_ref.set(
            {
                "google_sub": google_sub,
                "email": email,
                "display_name": display_name,
                "last_login_at": login_time.isoformat(),
            },
            merge=True,
        )
        user = self.get_user_by_google_sub(google_sub)
        if user is None:  # pragma: no cover - defensive fallback
            raise RuntimeError("failed to persist user login")
        return user

    def get_user_by_google_sub(self, google_sub: str) -> dict[str, str] | None:
        doc = self._client.collection("users").document(google_sub).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        return {
            "google_sub": str(data.get("google_sub") or google_sub),
            "email": str(data.get("email") or ""),
            "display_name": str(data.get("display_name") or ""),
            "last_login_at": str(data.get("last_login_at") or ""),
        }

    def delete_user(self, google_sub: str) -> None:
        self._client.collection("users").document(google_sub).delete()


FirestoreUserStore = FirestoreUserRepository

__all__ = ["FirestoreUserRepository", "FirestoreUserStore"]
