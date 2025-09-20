import os
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


os.environ.setdefault("STRICT_MODE", "false")


@pytest.fixture(scope="module")
def app_client():
    # src を import パスに追加
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "backend"))
    os.environ["STRICT_MODE"] = "false"
    import importlib
    importlib.invalidate_caches()
    for name in list(sys.modules.keys()):
        if name == "backend" or name.startswith("backend."):
            sys.modules.pop(name)
    # langgraph を最小スタブ化（バックエンドのみのE2Eに留める）
    lg_mod = types.ModuleType("langgraph")
    graph_mod = types.ModuleType("langgraph.graph")
    graph_mod.StateGraph = object
    lg_mod.graph = graph_mod
    sys.modules.setdefault("langgraph", lg_mod)
    sys.modules.setdefault("langgraph.graph", graph_mod)

    from backend.main import app
    return TestClient(app)

def test_basic_health_only(app_client):
    # 健全性のみ確認
    r = app_client.get("/healthz")
    assert r.status_code == 200


