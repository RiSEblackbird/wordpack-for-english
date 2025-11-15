"""SESSION_SECRET_KEY の検証をテストするモジュール。"""

import os

import pytest

_SAFE_SECRET = "hP5K7x1zQ9sN4v2L8wY3tB6mR0cJ7dF1"  # 32文字の擬似乱数

os.environ.setdefault("SESSION_SECRET_KEY", _SAFE_SECRET)

from backend.config import Settings


def test_settings_rejects_placeholder_session_secret() -> None:
    """change-me など既知のプレースホルダー値は受け入れない。"""

    with pytest.raises(ValueError) as exc:
        Settings(session_secret_key="change-me", _env_file=None)

    assert "SESSION_SECRET_KEY" in str(exc.value)


def test_settings_rejects_too_short_session_secret() -> None:
    """短いシークレットはブルートフォースに弱いため拒否する。"""

    with pytest.raises(ValueError) as exc:
        Settings(session_secret_key="short-secret", _env_file=None)

    assert "at least 32 characters" in str(exc.value)


def test_settings_accepts_long_random_session_secret() -> None:
    """十分な長さの乱数風文字列であれば初期化に成功する。"""

    config = Settings(session_secret_key=_SAFE_SECRET, _env_file=None)

    assert config.session_secret_key == _SAFE_SECRET
