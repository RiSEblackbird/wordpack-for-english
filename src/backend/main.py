from fastapi import FastAPI

from .config import settings  # noqa: F401 - imported for side effects or future use
from .logging import configure_logging
from .routers import health, review, sentence, text, word

configure_logging()
app = FastAPI()

app.include_router(word.router, prefix="/api/word")
app.include_router(sentence.router, prefix="/api/sentence")
app.include_router(text.router, prefix="/api/text")
app.include_router(review.router, prefix="/api/review")
app.include_router(health.router)
