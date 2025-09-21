from __future__ import annotations

import os
from typing import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, constr

from backend.config import settings

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - openai SDK が無い環境では初期化しない
    OpenAI = None  # type: ignore[assignment]


router = APIRouter(prefix="/api/tts", tags=["tts"])


def _init_client() -> OpenAI | None:  # type: ignore[valid-type]
    if OpenAI is None:  # pragma: no cover - SDK 未導入環境
        return None
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _iter_audio_bytes(response: object) -> Iterator[bytes]:
    if hasattr(response, "iter_bytes"):
        yield from response.iter_bytes()  # type: ignore[misc]
    else:  # pragma: no cover - 想定外フォーマット
        raise RuntimeError("streaming response does not provide iter_bytes")


client = _init_client()


class TTSIn(BaseModel):
    text: constr(min_length=1)
    voice: str = "alloy"


@router.post("", response_class=StreamingResponse)
def synth(req: TTSIn) -> StreamingResponse:
    global client

    if client is None:
        client = _init_client()

    if client is None:
        raise HTTPException(status_code=500, detail="OpenAI client is not configured")

    try:
        def stream() -> Iterator[bytes]:
            with client.audio.speech.with_streaming_response.create(  # type: ignore[union-attr]
                model="gpt-4o-mini-tts",
                voice=req.voice,
                input=req.text,
            ) as resp:
                yield from _iter_audio_bytes(resp)

        return StreamingResponse(stream(), media_type="audio/mpeg")
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - SDK からの例外をそのまま伝播
        raise HTTPException(status_code=500, detail=str(exc)) from exc
