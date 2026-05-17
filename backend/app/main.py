"""FastAPI application entrypoint."""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app import __version__
from app.api import (
    account,
    alerts,
    analytics,
    audit,
    auth,
    backtests,
    exchanges,
    health,
    markets,
    orders,
    portfolio,
    risk,
    routing,
    strategies,
)
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY


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
    app.include_router(routing.router)
    app.include_router(audit.router)

    @app.middleware("http")
    async def _metrics_middleware(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        REQUEST_LATENCY.labels(request.method, path).observe(time.perf_counter() - start)
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        return response

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
