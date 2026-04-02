from fastapi import APIRouter

from app.api import health, projects, documents, sheets
from app.api import extraction
from app.api import search

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(sheets.router, tags=["sheets"])
api_router.include_router(extraction.router)
api_router.include_router(search.router)
