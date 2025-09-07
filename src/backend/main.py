from fastapi import FastAPI

from .config import settings  # noqa: F401 - imported for side effects or future use
from .logging import configure_logging
from .routers import health, review, sentence, text, word

configure_logging()
app = FastAPI(title="WordPack API", version="0.3.0")

app.include_router(word.router, prefix="/api/word")  # 語彙関連エンドポイント
app.include_router(sentence.router, prefix="/api/sentence")  # 例文チェック関連
app.include_router(text.router, prefix="/api/text")  # リーディング支援関連
app.include_router(review.router, prefix="/api/review")  # 復習（SRS）関連
app.include_router(health.router)  # ヘルスチェック
