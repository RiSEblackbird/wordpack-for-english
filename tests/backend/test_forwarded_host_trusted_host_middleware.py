"""ForwardedHostTrustedHostMiddleware のホスト検証を網羅するテスト群。"""

import logging
import sys
from pathlib import Path
from typing import Callable

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

import backend.middleware.host as host_module  # noqa: E402  # isort:skip
from backend.middleware.host import ForwardedHostTrustedHostMiddleware  # noqa: E402  # isort:skip


@pytest.fixture()
def host_app_factory() -> Callable[..., FastAPI]:
    """ForwardedHostTrustedHostMiddleware を適用したシンプルなアプリを生成する。

    なぜ: 信頼済みプロキシや許可ホストを変更しながら挙動を検証できるよう、
    軽量な FastAPI アプリを毎回立ち上げて安全にテストするため。
    """

    def _build(*, allowed_hosts: tuple[str, ...], trusted_proxies: tuple[str, ...]) -> FastAPI:
        """指定した許可ホスト/信頼プロキシでヘルスチェックのみ持つアプリを構築。"""

        app = FastAPI()

        @app.get("/healthz")
        async def healthz() -> dict[str, str]:
            """ミドルウェアを通過した場合のみ到達するヘルスチェック。"""

            return {"status": "ok"}

        app.add_middleware(
            ForwardedHostTrustedHostMiddleware,
            allowed_hosts=allowed_hosts,
            trusted_proxy_ips=trusted_proxies,
        )
        return app

    return _build


def test_accepts_cloud_run_host(host_app_factory: Callable[..., FastAPI]) -> None:
    """Cloud Run 既定ホストを Host に指定したリクエストが 200 となる。"""

    app = host_app_factory(
        allowed_hosts=("wordpack-backend-726124335049.asia-northeast1.run.app",),
        trusted_proxies=("127.0.0.1",),
    )

    with TestClient(app) as client:
        response = client.get(
            "/healthz",
            headers={"Host": "wordpack-backend-726124335049.asia-northeast1.run.app"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_accepts_web_app_host_via_wildcard(host_app_factory: Callable[..., FastAPI]) -> None:
    """ALLOWED_HOSTS に *.web.app を含めれば Firebase Hosting のドメインも許可される。"""

    app = host_app_factory(
        allowed_hosts=("*.web.app",),
        trusted_proxies=("127.0.0.1",),
    )

    with TestClient(app) as client:
        response = client.get(
            "/healthz",
            headers={"Host": "wordpack-for-english.web.app"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_prefers_forwarded_host_from_trusted_proxy(host_app_factory: Callable[..., FastAPI]) -> None:
    """信頼済みプロキシ経由では X-Forwarded-Host を優先し 200 を返す。"""

    app = host_app_factory(
        allowed_hosts=("forwarded.wordpack-backend-726124335049.asia-northeast1.run.app",),
        trusted_proxies=("203.0.113.0/24",),
    )

    with TestClient(app) as client:
        response = client.get(
            "/healthz",
            headers={
                "Host": "placeholder.invalid",  # 直接の Host は許可リスト外
                "X-Forwarded-Host": "forwarded.wordpack-backend-726124335049.asia-northeast1.run.app",
                "X-Forwarded-For": "203.0.113.42",  # trusted_proxies 内
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_rejects_unlisted_host_with_warning_log(
    host_app_factory: Callable[..., FastAPI],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """許可されていないホストは 400 を返し、WARNING ログを必ず出力する。"""

    captured_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    original_warning = host_module.logger.warning

    def _capture_warning(*args: object, **kwargs: object) -> object:
        """WARNING ログの引数を保存しつつ元のロガーにも委譲する。"""

        captured_calls.append((args, kwargs))
        return original_warning(*args, **kwargs)

    monkeypatch.setattr(host_module.logger, "warning", _capture_warning)

    app = host_app_factory(
        allowed_hosts=(
            "wordpack-backend-726124335049.asia-northeast1.run.app",
            "*.web.app",
        ),
        trusted_proxies=("*",),
    )

    with TestClient(app) as client:
        response = client.get(
            "/healthz",
            headers={"Host": "evil.example.com"},
        )

    assert response.status_code == 400
    assert len(captured_calls) == 1
    args, kwargs = captured_calls[0]
    assert args[0] == "host_not_allowed"
    assert kwargs.get("host") == "evil.example.com"
    captured = capsys.readouterr()
    log_output = (captured.out + captured.err).lower()
    assert "host_not_allowed" in log_output
    assert "warning" in log_output
