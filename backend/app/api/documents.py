from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.dependencies import get_db, get_storage
from app.models.document import Document, ProcessingStatus
from app.models.project import Project
from app.models.sheet import Sheet
from app.schemas.document import (
    DocumentList,
    DocumentRead,
    DocumentStatusResponse,
    DocumentUploadResponse,
)
from app.services.ingestion import IngestionService
from app.services.storage import StorageService

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_ingestion(document_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        storage = StorageService()
        service = IngestionService(session, storage)
        await service.process_document(document_id)


@router.post(
    "/projects/{project_id}/documents/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_document(
    project_id: uuid.UUID,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage),
) -> DocumentUploadResponse:
    # Validate project exists
    proj_result = await session.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate PDF
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted",
        )
    if file.content_type not in ("application/pdf", "application/octet-stream", None):
        if file.content_type and "pdf" not in file.content_type.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content type must be application/pdf",
            )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    document_id = uuid.uuid4()
    stored_path = f"{project_id}/{document_id}/{filename}"

    # Upload to MinIO
    storage.upload_file(
        settings.bucket_original_pdfs,
        stored_path,
        content,
        content_type="application/pdf",
    )

    # Create document record
    document = Document(
        id=document_id,
        project_id=project_id,
        original_filename=filename,
        stored_path=stored_path,
        file_size_bytes=len(content),
        processing_status=ProcessingStatus.pending,
    )
    session.add(document)
    await session.flush()

    background_tasks.add_task(_run_ingestion, document_id)

    return DocumentUploadResponse(
        id=document_id,
        original_filename=filename,
        file_size_bytes=len(content),
        processing_status=ProcessingStatus.pending,
        message="Document uploaded. Processing started in background.",
    )


@router.get(
    "/projects/{project_id}/documents",
    response_model=DocumentList,
)
async def list_documents(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DocumentList:
    proj_result = await session.execute(select(Project).where(Project.id == project_id))
    if proj_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    total_result = await session.execute(
        select(func.count()).select_from(Document).where(Document.project_id == project_id)
    )
    total = total_result.scalar_one()
    result = await session.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
    )
    items = result.scalars().all()
    return DocumentList(
        items=[DocumentRead.model_validate(d) for d in items],
        total=total,
    )


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DocumentRead:
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentRead.model_validate(document)


@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> DocumentStatusResponse:
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    sheets_count_result = await session.execute(
        select(func.count()).select_from(Sheet).where(Sheet.document_id == document_id)
    )
    sheets_processed = sheets_count_result.scalar_one()

    return DocumentStatusResponse(
        id=document.id,
        processing_status=document.processing_status,
        page_count=document.page_count,
        processing_error=document.processing_error,
        sheets_processed=sheets_processed,
    )
