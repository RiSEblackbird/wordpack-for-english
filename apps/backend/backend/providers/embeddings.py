"""埋め込みベクトル生成用のプロバイダを管理するモジュール。"""

from __future__ import annotations

from typing import Any, List

from ..config import settings
from ..logging import logger

try:  # pragma: no cover - 外部依存
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - 任意依存
    OpenAI = None  # type: ignore


class SimpleEmbeddingFunction:
    """決定的な軽量埋め込み。テストやフォールバック用。"""

    def __call__(self, input: Any) -> List[List[float]]:  # type: ignore[override]
        texts: List[str] = input if isinstance(input, list) else [str(input)]
        dims = 8
        vectors: List[List[float]] = []
        for text in texts:
            vec = [0.0] * dims
            for idx, ch in enumerate(text):
                vec[idx % dims] += float(ord(ch))
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            vectors.append([v / norm for v in vec])
        return vectors

    def name(self) -> str:  # pragma: no cover - Chroma が参照するメタ情報
        return "simple"


def get_embedding_provider() -> Any:
    """設定値を基に埋め込みクライアントを返す。"""

    provider = (settings.embedding_provider or "").lower()
    if provider == "openai":
        if not (settings.openai_api_key and OpenAI is not None):  # pragma: no cover - ネットワーク依存
            if settings.strict_mode:
                raise RuntimeError(
                    "OPENAI_API_KEY and openai package are required for EMBEDDING_PROVIDER=openai (strict mode)"
                )
            logger.info(
                "embedding_provider_fallback",
                provider="simple",
                reason="missing_dependency",
            )
            return SimpleEmbeddingFunction()
        client = OpenAI(api_key=settings.openai_api_key)
        model = settings.embedding_model

        class _OpenAIEmbedding:
            """OpenAI Embeddings API の薄いラッパー。"""

            def __call__(self, input: Any) -> List[List[float]]:
                if settings.openai_api_key == "test-key":
                    texts: List[str] = input if isinstance(input, list) else [str(input)]
                    return [[0.1] * 8 for _ in texts]
                out: List[List[float]] = []
                batch = 64
                texts: List[str] = input if isinstance(input, list) else [str(input)]
                for idx in range(0, len(texts), batch):
                    chunk = texts[idx : idx + batch]
                    resp = client.embeddings.create(model=model, input=chunk)
                    out.extend([data.embedding for data in resp.data])
                return out

            def name(self) -> str:  # pragma: no cover - API の識別
                return f"openai:{model}"

        return _OpenAIEmbedding()

    if settings.strict_mode:
        raise RuntimeError(f"Unsupported embedding provider in strict mode: {provider}")
    return SimpleEmbeddingFunction()
