"""
Main FastAPI application.

Provides REST API endpoints for:
- Credential management
- Health check analysis execution
- Result retrieval
- WebSocket live updates
"""

from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cribl_hc import __version__
from cribl_hc.utils.logger import get_logger

# Import routers
from cribl_hc.api.routers import credentials, analysis, analyzers, system

log = get_logger(__name__)


# In-memory storage for analysis tasks (will be replaced with proper storage later)
analysis_storage: Dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    log.info("api_startup", version=__version__)

    yield

    # Shutdown
    log.info("api_shutdown")


# Create FastAPI application
app = FastAPI(
    title="Cribl Health Check API",
    description="REST API for Cribl Stream health monitoring and analysis",
    version=__version__,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(system.router, prefix="/api/v1", tags=["system"])
app.include_router(credentials.router, prefix="/api/v1/credentials", tags=["credentials"])
app.include_router(analyzers.router, prefix="/api/v1/analyzers", tags=["analyzers"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to API docs."""
    return JSONResponse({
        "message": "Cribl Health Check API",
        "version": __version__,
        "docs": "/api/docs",
        "health": "/api/v1/health"
    })


@app.get("/health", include_in_schema=False)
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "version": __version__,
        "service": "cribl-health-check"
    }
