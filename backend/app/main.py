"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config import settings
from app.api.routes import projects, research, exports
from app.db.session import engine

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("starting_app", env=settings.APP_ENV)
    yield
    await engine.dispose()
    logger.info("app_shutdown")


app = FastAPI(
    title="ResearchPilot API",
    description="AI-powered McKinsey-style research tool",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(exports.router, prefix="/api/exports", tags=["exports"])


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.APP_ENV}
