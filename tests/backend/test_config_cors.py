"""CORS 設定の読み込みと正規化を検証するテスト群。"""

from backend.config import Settings


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
