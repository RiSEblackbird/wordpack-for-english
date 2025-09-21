from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "apps" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from backend.main import create_app
from backend.routers import tts


class _DummyStream:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def __enter__(self) -> "_DummyStream":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def iter_bytes(self) -> Iterator[bytes]:
        yield from self._chunks


class _DummyClient:
    def __init__(self, chunks: list[bytes]) -> None:
        self.audio = type(
            "_Audio",
            (),
            {
                "speech": type(
                    "_Speech",
                    (),
                    {
                        "with_streaming_response": type(
                            "_WithStreaming",
                            (),
                            {"create": staticmethod(lambda **_: _DummyStream(chunks))},
                        )()
                    },
                )()
            },
        )()


def test_tts_synth_streams_audio(monkeypatch) -> None:
    original_client = tts.client
    dummy_client = _DummyClient([b"foo", b"bar"])
    tts.client = dummy_client  # type: ignore[assignment]
    try:
        app = create_app()
        with TestClient(app) as client:
            response = client.post("/api/tts", json={"text": "Hello", "voice": "verse"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("audio/mpeg")
        assert response.content == b"foobar"
    finally:
        tts.client = original_client  # type: ignore[assignment]


def test_tts_synth_unconfigured(monkeypatch) -> None:
    original_client = tts.client
    tts.client = None  # type: ignore[assignment]
    try:
        app = create_app()
        with TestClient(app) as client:
            response = client.post("/api/tts", json={"text": "Hi"})
        assert response.status_code == 500
        assert response.json()["detail"].startswith("OpenAI client is not configured")
    finally:
        tts.client = original_client  # type: ignore[assignment]
