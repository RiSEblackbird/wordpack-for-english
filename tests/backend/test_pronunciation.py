import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def reload_pronunciation_module(monkeypatch: pytest.MonkeyPatch):
    """各テストの独立性確保のため発音モジュールをリロードする。"""
    backend_root = Path(__file__).resolve().parents[2] / "apps" / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    module = importlib.import_module("backend.pronunciation")
    importlib.reload(module)
    return module


def test_generate_pronunciation_reuses_single_g2p_instance(monkeypatch, reload_pronunciation_module):
    module = reload_pronunciation_module
    monkeypatch.setattr(module, "cmudict", None)
    module._CMU_CACHE = None  # type: ignore[attr-defined]
    module._g2p_phones.cache_clear()  # type: ignore[attr-defined]
    module._G2P_INSTANCE = None  # type: ignore[attr-defined]

    init_count = 0

    class DummyG2p:
        """g2p_en.G2p の軽量スタブ。インスタンス生成回数のみを観測する。"""

        def __init__(self):
            nonlocal init_count
            init_count += 1

        def __call__(self, word: str):
            return ["T", "EH1", "S", "T"]

    monkeypatch.setattr(module, "G2p", DummyG2p)

    module.generate_pronunciation("alpha")
    module.generate_pronunciation("bravo")

    assert init_count == 1
