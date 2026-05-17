"""Health and readiness endpoints."""

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/v1/system/version")
async def version() -> dict[str, str]:
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
        "paper_trading_default": str(settings.paper_trading_default),
    }
