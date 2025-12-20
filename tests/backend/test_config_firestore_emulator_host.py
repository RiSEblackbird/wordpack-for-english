import os
import types

from backend import config as backend_config
from backend import store as backend_store


def test_normalize_accepts_docker_service_host():
    """Docker Compose の service 名ホストでも http:// 付きに正規化されることを担保する。"""

    assert (
        backend_store._normalize_emulator_host("firestore-emulator:8080")
        == "http://firestore-emulator:8080"
    )


def test_build_client_uses_service_host(monkeypatch):
    """Docker Compose 用の service ホストを設定したときに api_endpoint へ反映されることを確認する。"""

    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.setattr(backend_config.settings, "firestore_project_id", "wordpack-local")
    monkeypatch.setattr(
        backend_config.settings,
        "firestore_emulator_host",
        "firestore-emulator:8080",
    )

    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, project=None, client_options=None):
            captured["project"] = project
            captured["client_options"] = client_options

    dummy_firestore = types.SimpleNamespace(Client=DummyClient)
    monkeypatch.setattr(backend_store, "firestore", dummy_firestore)

    backend_store._build_firestore_client()

    assert captured["client_options"] == {"api_endpoint": "http://firestore-emulator:8080"}
    # google-cloud-firestore がエミュレータへ向くよう、スキーム無しの値を環境変数へ設定していることも確認
    assert os.environ["FIRESTORE_EMULATOR_HOST"] == "firestore-emulator:8080"

