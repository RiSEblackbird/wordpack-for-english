"""プロバイダー向けの共有ステート初期化と公開APIを管理するパッケージ。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

# 共有キャッシュ: ベクターストアや埋め込みプロバイダのインスタンスをモジュール間で再利用する。
_CLIENT_CACHE: dict[str, Any] = {}
# LLM クライアントのシングルトン。オーバーライド付き呼び出しでは再生成される。
_LLM_INSTANCE: Any | None = None
# LLM 呼び出しをタイムアウト制御付きで実行するためのスレッドプール。
_llm_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=4)


def _get_client_cache() -> dict[str, Any]:
    """内部モジュールにキャッシュへの参照を提供する。"""

    return _CLIENT_CACHE


def _get_llm_instance() -> Any | None:
    """LLM シングルトンの現在値を返す。"""

    return _LLM_INSTANCE


def _set_llm_instance(instance: Any | None) -> None:
    """LLM シングルトンを更新する。テストでは None へ戻し再初期化する。"""

    global _LLM_INSTANCE
    _LLM_INSTANCE = instance


def _get_llm_executor() -> ThreadPoolExecutor:
    """LLM ラッパーが共有するスレッドプールを返す。"""

    return _llm_executor


from .embeddings import get_embedding_provider
from .factory import ChromaClientFactory
from .llm import get_llm_provider, shutdown_providers
from .vector import COL_DOMAIN_TERMS, COL_WORD_SNIPPETS

__all__ = [
    "ChromaClientFactory",
    "COL_DOMAIN_TERMS",
    "COL_WORD_SNIPPETS",
    "get_embedding_provider",
    "get_llm_provider",
    "shutdown_providers",
]
