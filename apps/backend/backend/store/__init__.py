from __future__ import annotations

import os

from google.cloud import firestore

from ..config import settings
from .examples import EXAMPLE_CATEGORIES
from .firestore_store import AppFirestoreStore

def _normalize_emulator_host(raw_host: str | None) -> str | None:
    """FIRESTORE_EMULATOR_HOST で受け取ったホスト文字列を正規化する。

    スキームなしの `localhost:8080` でもクライアントオプションに渡せるよう、
    http:// を自動付与する。空文字や None は未設定として扱う。
    """

    host = (raw_host or "").strip()
    if not host:
        return None
    if host.startswith(("http://", "https://")):
        return host
    return f"http://{host}"


def _build_firestore_client() -> firestore.Client:
    """Firestore クライアントを構築する。

    - FIRESTORE_EMULATOR_HOST が指定されていればエミュレータ向けのエンドポイントを使用。
    - 未指定の場合は Cloud Firestore へ接続する。
    """

    emulator_host = _normalize_emulator_host(
        settings.firestore_emulator_host or os.environ.get("FIRESTORE_EMULATOR_HOST")
    )
    project_id = settings.firestore_project_id or settings.gcp_project_id
    if emulator_host:
        # google-cloud-firestore は FIRESTORE_EMULATOR_HOST を検知して匿名認証へ切り替える。
        os.environ.setdefault("FIRESTORE_EMULATOR_HOST", emulator_host.replace("http://", "").replace("https://", ""))
        return firestore.Client(project=project_id, client_options={"api_endpoint": emulator_host})
    return firestore.Client(project=project_id)


def _create_store() -> AppFirestoreStore:
    """アプリ全体で共有する Firestore ベースのストアを初期化する。"""

    client = _build_firestore_client()
    return AppFirestoreStore(client=client)


store = _create_store()

__all__ = [
    "AppFirestoreStore",
    "store",
    "EXAMPLE_CATEGORIES",
]
