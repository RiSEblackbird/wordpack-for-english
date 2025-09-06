from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def health_check() -> dict[str, str]:
    """Simple health check endpoint."""
    return {"status": "ok"}
