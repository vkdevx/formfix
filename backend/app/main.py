from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.models.database import init_db
from app.api import api_router
from app.core.errors import (
    FormSaathiException,
    formsaathi_exception_handler,
    http_exception_handler
)

# Ensure database schema is initialized
init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables on startup
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Powered Government Form Pre-Submission Assistant and Validation Engine (UP Scholarship MVP)",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(FormSaathiException, formsaathi_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# Mount API Routers (supports both /api/v1 and /api prefix for frontend/script compatibility)
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router, prefix="/api")

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/healthz", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

# Check for production frontend build
frontend_dist_dir = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
)

if os.path.isdir(frontend_dist_dir):
    assets_dir = os.path.join(frontend_dist_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        target_file = os.path.join(frontend_dist_dir, full_path)
        if full_path and os.path.isfile(target_file):
            return FileResponse(target_file)
        return FileResponse(os.path.join(frontend_dist_dir, "index.html"))
else:
    @app.get("/", tags=["Root"])
    def root():
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "scope": "UP Scholarship Pre-Submission Audit",
            "disclaimer": "FormFix is an independent assistive tool. It is not affiliated with, endorsed by, or connected to any government department or portal. Results are advisory and do not guarantee acceptance."
        }
