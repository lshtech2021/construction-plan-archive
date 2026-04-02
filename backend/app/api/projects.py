from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectList, ProjectRead, ProjectUpdate

router = APIRouter()


@router.post("/projects", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_db),
) -> ProjectRead:
    project = Project(**payload.model_dump(exclude_none=False))
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return ProjectRead.model_validate(project)


@router.get("/projects", response_model=ProjectList)
async def list_projects(
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
) -> ProjectList:
    offset = (page - 1) * page_size
    total_result = await session.execute(select(func.count()).select_from(Project))
    total = total_result.scalar_one()
    result = await session.execute(
        select(Project).order_by(Project.created_at.desc()).offset(offset).limit(page_size)
    )
    items = result.scalars().all()
    return ProjectList(
        items=[ProjectRead.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> ProjectRead:
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectRead.model_validate(project)


@router.put("/projects/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    session: AsyncSession = Depends(get_db),
) -> ProjectRead:
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await session.flush()
    await session.refresh(project)
    return ProjectRead.model_validate(project)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> None:
    result = await session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await session.delete(project)
