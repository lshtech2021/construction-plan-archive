from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.document import Document
from app.models.sheet import Discipline, Sheet, SheetType
from app.schemas.sheet import SheetDetail, SheetList, SheetRead

router = APIRouter()


@router.get("/documents/{document_id}/sheets", response_model=SheetList)
async def list_sheets(
    document_id: uuid.UUID,
    discipline: Optional[Discipline] = None,
    sheet_type: Optional[SheetType] = None,
    session: AsyncSession = Depends(get_db),
) -> SheetList:
    doc_result = await session.execute(select(Document).where(Document.id == document_id))
    if doc_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    query = select(Sheet).where(Sheet.document_id == document_id)
    if discipline is not None:
        query = query.where(Sheet.discipline == discipline)
    if sheet_type is not None:
        query = query.where(Sheet.sheet_type == sheet_type)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_q)).scalar_one()

    result = await session.execute(query.order_by(Sheet.page_number))
    items = result.scalars().all()
    return SheetList(
        items=[SheetRead.model_validate(s) for s in items],
        total=total,
    )


@router.get("/sheets/{sheet_id}", response_model=SheetDetail)
async def get_sheet(
    sheet_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> SheetDetail:
    result = await session.execute(select(Sheet).where(Sheet.id == sheet_id))
    sheet = result.scalar_one_or_none()
    if sheet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sheet not found")
    return SheetDetail.model_validate(sheet)
