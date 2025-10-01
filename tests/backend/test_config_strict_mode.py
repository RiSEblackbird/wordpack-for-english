import pytest


def test_strict_mode_rejects_missing_session_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STRICT_MODE", "true")

    from backend.config import Settings

    with pytest.raises(ValueError, match="SESSION_SECRET must be set when STRICT_MODE=true"):
        Settings(strict_mode=True, session_secret=" ", google_oauth_client_id="client")


def test_strict_mode_rejects_missing_google_client_id(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STRICT_MODE", "true")

    from backend.config import Settings

    with pytest.raises(ValueError, match="GOOGLE_OAUTH_CLIENT_ID must be set when STRICT_MODE=true"):
        Settings(strict_mode=True, session_secret="secret", google_oauth_client_id="")


def test_non_strict_mode_allows_missing_auth_keys(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("STRICT_MODE", raising=False)

    from backend.config import Settings

    settings = Settings(strict_mode=False, session_secret="", google_oauth_client_id=None)

    assert settings.strict_mode is False
    assert settings.session_secret == ""
    assert settings.google_oauth_client_id is None

