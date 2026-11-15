"""FastAPI main application entrypoint for MARSWALK."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.errors import (
    MarswalkException,
    marswalk_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from app.api import (
    routes_health,
    routes_regions,
    routes_layers,
    routes_observations,
    routes_terrain,
    routes_hazards,
    routes_routes,
    routes_missions,
    routes_environment,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("marswalk")

app = FastAPI(
    title="MARSWALK Backend API",
    version=settings.version,
    description="MARSWALK: Intelligent Mars Exploration & Mission Planning MVP API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers ensuring consistent error envelope
app.add_exception_handler(MarswalkException, marswalk_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include API routes under /api
app.include_router(routes_health.router, prefix="/api")
app.include_router(routes_regions.router, prefix="/api")
app.include_router(routes_layers.router, prefix="/api")
app.include_router(routes_observations.router, prefix="/api")
app.include_router(routes_terrain.router, prefix="/api")
app.include_router(routes_hazards.router, prefix="/api")
app.include_router(routes_routes.router, prefix="/api")
app.include_router(routes_missions.router, prefix="/api")
app.include_router(routes_environment.router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": "MARSWALK Backend API",
        "version": settings.version,
        "docs": "/docs",
        "health": "/api/health",
    }
