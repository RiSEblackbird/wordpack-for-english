from __future__ import annotations

from typing import Protocol


class ArticleRepository(Protocol):
    def get_article(self, article_id: str):
        ...

    def list_articles(self, *, limit: int, offset: int, public_only: bool = False):
        ...

    def count_articles(self, *, public_only: bool = False) -> int:
        ...

    def update_article_guest_public(self, article_id: str, guest_public: bool) -> bool | None:
        ...

    def delete_article(self, article_id: str) -> bool:
        ...
