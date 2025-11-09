"""Settings におけるセッション Cookie Secure 既定値の挙動を検証するテスト。"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "backend"))

from backend.config import Settings


@pytest.fixture(autouse=True)
def clear_session_cookie_secure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """環境変数の影響を排除し、純粋な既定値を検証する。"""

    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)


def test_session_cookie_secure_defaults_to_false_in_development() -> None:
    """開発環境では Secure を無効化したまま Cookie を配信できる。"""

    config = Settings(environment="development", _env_file=None)
    assert config.session_cookie_secure is False


def test_session_cookie_secure_defaults_to_true_in_production() -> None:
    """本番環境では Secure 属性が既定で有効化される。"""

    config = Settings(environment="production", _env_file=None)
    assert config.session_cookie_secure is True


def test_session_cookie_secure_respects_explicit_override() -> None:
    """環境変数やコードで明示した値は本番でも優先される。"""

    config = Settings(environment="production", session_cookie_secure=False, _env_file=None)
    assert config.session_cookie_secure is False
