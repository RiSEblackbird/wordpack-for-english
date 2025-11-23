"""Debug endpoints for quickly inspecting forwarded headers.

このモジュールは Cloud Run/Firebase Hosting 経由で到達した際に、
FastAPI がどの Host / X-Forwarded-* ヘッダを受け取っているかを
即座に確認するための開発用 API を提供する。運用中に問題が発生した
場合でも、/_debug/headers へアクセスするだけで実際の値を確認できる。
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/_debug", tags=["debug"])


@router.get("/headers")
async def inspect_forwarded_headers(request: Request) -> JSONResponse:
    """Echo the effective host and forwarding headers for troubleshooting.

    なぜ: Firebase Hosting -> Cloud Run の経路では複数のプロキシが介在し、
    FastAPI から見える Host / X-Forwarded-* が想定どおりか判断しづらい。
    このエンドポイントで受信ヘッダと URL/クライアント IP をそのまま
    返すことで、設定漏れやプロキシ順序を素早く検証できる。
    """

    headers = request.headers
    client_host = request.client.host if request.client else None
    payload = {
        "host": headers.get("host"),
        "x_forwarded_host": headers.get("x-forwarded-host"),
        "x_forwarded_proto": headers.get("x-forwarded-proto"),
        "x_forwarded_for": headers.get("x-forwarded-for"),
        "url": str(request.url),
        "client_host": client_host,
    }
    return JSONResponse(payload)
