from __future__ import annotations

from typing import Protocol


class ArticleRepository(Protocol):
    def get_article(self, article_id: str):
        ...

    def list_articles(self, *, limit: int, offset: int):
        ...

    def delete_article(self, article_id: str) -> bool:
        ...
