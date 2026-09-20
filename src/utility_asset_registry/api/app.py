"""FastAPI application factory. OpenAPI lives at /docs for the map vendor."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from utility_asset_registry.api.assets import router as assets_router
from utility_asset_registry.api.auth import router as auth_router
from utility_asset_registry.api.errors import invalid_payload
from utility_asset_registry.api.reports import router as reports_router
from utility_asset_registry.api.upload import router as upload_router
from utility_asset_registry.auth import AuthError, bootstrap_admin
from utility_asset_registry.cache import invalidate_summary_cache
from utility_asset_registry.config import get_settings
from utility_asset_registry.database import init_db, make_engine, make_session_factory
from utility_asset_registry.middleware import RateLimitMiddleware, RequestTimingMiddleware


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = get_settings()
    engine = make_engine()
    init_db(engine)
    factory = make_session_factory(engine)
    invalidate_summary_cache()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine
        app.state.session_factory = factory
        session = factory()
        try:
            bootstrap_admin(session)
        finally:
            session.close()
        yield
        engine.dispose()

    app = FastAPI(
        title="Utility Asset Registry",
        description=(
            "Back-end for a state electricity distribution utility. "
            "Staff and the web map load, search and update surveyed assets."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = factory

    # Outer middleware runs first on the way in. Timing should wrap everything.
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def _readable_validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"] if part != "body")
            fields[loc or "body"] = err["msg"]
        return invalid_payload(fields)

    @app.exception_handler(AuthError)
    async def _auth_error(_request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.content)

    @app.get("/health", tags=["status"], summary="Unprotected liveness check")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(assets_router)
    app.include_router(reports_router)
    app.include_router(upload_router)
    return app
