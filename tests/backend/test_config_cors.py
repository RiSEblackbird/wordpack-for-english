"""CORS 設定の読み込みと正規化を検証するテスト群。"""

import os

import pytest

_SAFE_SECRET = "T1yYz0vL3nQ6rP9sD4wX7bC2fH5kJ8mN"  # 32文字の擬似乱数

os.environ.setdefault("SESSION_SECRET_KEY", _SAFE_SECRET)

from backend.config import Settings


@pytest.fixture(autouse=True)
def _ensure_session_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """セッション鍵を安全な値に上書きし、検証エラーを回避する。"""

    monkeypatch.setenv("SESSION_SECRET_KEY", _SAFE_SECRET)


def test_settings_reads_cors_origins_from_env(monkeypatch):
    """`CORS_ALLOWED_ORIGINS` から値を読み込み、トリムと重複排除を行う。"""

    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        " https://app.example.com ,https://admin.example.com,https://app.example.com ",
    )

    config = Settings(_env_file=None)

    assert config.allowed_cors_origins == (
        "https://app.example.com",
        "https://admin.example.com",
    )
