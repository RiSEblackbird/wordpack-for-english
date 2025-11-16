"""SESSION_SECRET_KEY の検証をテストするモジュール。"""

import hashlib
import os

import pytest
from pydantic import ValidationError

_SAFE_SECRET = "hP5K7x1zQ9sN4v2L8wY3tB6mR0cJ7dF1"  # 32文字の擬似乱数

os.environ.setdefault("SESSION_SECRET_KEY", _SAFE_SECRET)

from backend.config import Settings


def test_settings_rejects_placeholder_session_secret() -> None:
    """change-me など既知のプレースホルダー値は受け入れない。"""

    with pytest.raises(ValidationError) as exc:
        Settings(session_secret_key="change-me", _env_file=None)

    errors = exc.value.errors()
    assert errors[0]["type"] == "value_error"
    assert errors[0]["loc"] == ("session_secret_key",)
    assert "placeholder" in errors[0]["msg"]


def test_settings_rejects_too_short_session_secret() -> None:
    """短いシークレットはブルートフォースに弱いため拒否する。"""

    with pytest.raises(ValidationError) as exc:
        Settings(session_secret_key="short-secret", _env_file=None)

    errors = exc.value.errors()
    assert errors[0]["type"] == "value_error"
    assert "at least 32 characters" in errors[0]["msg"]


def test_settings_accepts_long_random_session_secret() -> None:
    """十分な長さの乱数風文字列であれば初期化に成功する。"""

    config = Settings(session_secret_key=_SAFE_SECRET, _env_file=None)

    assert config.session_secret_key == _SAFE_SECRET


def test_settings_rejects_known_leaked_session_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """過去に公開したシークレットのハッシュと一致する値は拒否する。"""

    leaked_hash = hashlib.sha256(_SAFE_SECRET.encode("utf-8")).hexdigest()
    monkeypatch.setattr(
        "backend.config._KNOWN_LEAKED_SESSION_SECRET_SHA256",
        frozenset({leaked_hash}),
        raising=False,
    )

    with pytest.raises(ValidationError) as exc:
        Settings(session_secret_key=_SAFE_SECRET, _env_file=None)

    errors = exc.value.errors()
    assert errors[0]["type"] == "value_error"
    assert "published sample" in errors[0]["msg"]


def test_settings_raises_when_session_secret_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """環境変数が未設定のまま起動した場合は即座に例外を送出する。"""

    monkeypatch.delenv("SESSION_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None)

    errors = exc.value.errors()
    assert errors[0]["loc"] == ("session_secret_key",)
    assert "must be a non-empty" in errors[0]["msg"]
