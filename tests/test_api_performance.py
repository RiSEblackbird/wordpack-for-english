import math
import os
import time

import pytest
from fastapi.testclient import TestClient

from tests.firestore_fakes import FakeFirestoreClient
from tests.test_api import _reload_backend_app

_DEFAULT_P95_THRESHOLD_MS = 1500.0
_SAMPLE_COUNT = 20
_WARMUP_COUNT = 3


@pytest.fixture()
def firestore_client() -> FakeFirestoreClient:
    """各テストで独立した Firestore フェイクインスタンスを提供する。"""

    return FakeFirestoreClient()


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, firestore_client: FakeFirestoreClient) -> TestClient:
    """パフォーマンステスト向けにバックエンドを再初期化してから TestClient を返す。"""

    backend_main = _reload_backend_app(monkeypatch, strict=False, firestore_client=firestore_client)
    return TestClient(backend_main.app)


def _read_threshold_ms() -> float:
    """閾値は CI/ステージングで調整できるよう環境変数から取得する。"""

    raw = os.getenv("API_P95_THRESHOLD_MS")
    if raw is None:
        return _DEFAULT_P95_THRESHOLD_MS
    try:
        value = float(raw)
    except ValueError as exc:
        raise AssertionError("API_P95_THRESHOLD_MS must be a number") from exc
    if value <= 0:
        raise AssertionError("API_P95_THRESHOLD_MS must be greater than 0")
    return value


def _calculate_p95(values_ms: list[float]) -> float:
    """p95 を計算し、外れ値に引っ張られすぎない中央値寄りの指標を得る。"""

    if not values_ms:
        raise AssertionError("p95 calculation requires at least one sample")
    ordered = sorted(values_ms)
    # p95 は「95% がこの値以下」なので、切り上げで過小評価を防ぐ。
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _measure_endpoint(
    client: TestClient,
    *,
    method: str,
    path: str,
    payload: dict | None,
) -> list[float]:
    """Warm-up で初期化コストを吸収し、本計測は安定した指標を取る。"""

    for _ in range(_WARMUP_COUNT):
        response = client.request(method, path, json=payload)
        assert response.status_code == 200

    durations_ms: list[float] = []
    for _ in range(_SAMPLE_COUNT):
        started = time.perf_counter()
        response = client.request(method, path, json=payload)
        elapsed_ms = (time.perf_counter() - started) * 1000
        assert response.status_code == 200
        durations_ms.append(elapsed_ms)

    return durations_ms


@pytest.mark.parametrize(
    "label,method,path,payload",
    [
        ("healthz", "GET", "/healthz", None),
        ("word_pack", "POST", "/api/word/pack", {"lemma": "converge"}),
    ],
)
def test_api_p95_under_threshold(
    client: TestClient, label: str, method: str, path: str, payload: dict | None
) -> None:
    """主要エンドポイントの p95 が閾値以下であることを検証する。"""

    threshold_ms = _read_threshold_ms()
    samples_ms = _measure_endpoint(client, method=method, path=path, payload=payload)
    p95_ms = _calculate_p95(samples_ms)

    assert p95_ms <= threshold_ms, (
        f"p95 latency regression detected: endpoint={label} p95={p95_ms:.2f}ms "
        f"threshold={threshold_ms:.2f}ms"
    )
