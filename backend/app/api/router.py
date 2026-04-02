from fastapi import APIRouter

from app.api import health, projects, documents, sheets

api_router = APIRouter(prefix="/api")

api_router.include_router(health.router, tags=["health"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(sheets.router, tags=["sheets"])
