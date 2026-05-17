"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import (
    account,
    alerts,
    analytics,
    auth,
    backtests,
    exchanges,
    health,
    markets,
    orders,
    portfolio,
    risk,
    strategies,
)
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(debug=settings.debug)
    log = get_logger("startup")
    log.info("application_starting", version=__version__, environment=settings.environment)
    yield
    log.info("application_stopping")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(exchanges.router)
    app.include_router(markets.router)
    app.include_router(strategies.router)
    app.include_router(risk.router)
    app.include_router(orders.router)
    app.include_router(account.router)
    app.include_router(backtests.router)
    app.include_router(portfolio.router)
    app.include_router(analytics.router)
    app.include_router(alerts.router)
    return app


app = create_app()
