"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    actions,
    analysis,
    audio,
    auth,
    meetings,
)
from app.config import get_settings
from app.db.mongodb import close_mongo_connection, connect_to_mongo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("iwasist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    await connect_to_mongo(settings)
    yield
    await close_mongo_connection()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Meeting Assistant API",
        version="0.1.0",
        description="REST API for the Meeting Assistant agentic application.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
    app.include_router(audio.router, prefix="/api/audio", tags=["audio"])
    app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
    app.include_router(actions.router, prefix="/api/actions", tags=["actions"])

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
