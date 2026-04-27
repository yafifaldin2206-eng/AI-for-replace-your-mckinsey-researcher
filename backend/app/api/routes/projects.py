"""Project CRUD routes."""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_user_id
from app.db.session import get_db
from app.db.models import Project
from app.api.schemas.project import ProjectCreate, ProjectOut

router = APIRouter()


@router.post("", response_model=ProjectOut)
async def create_project(
    body: ProjectCreate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = Project(
        user_id=get_user_id(user),
        name=body.name,
        description=body.description,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Project)
        .where(Project.user_id == get_user_id(user))
        .order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != get_user_id(user):
        raise HTTPException(404, "Project not found")
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    project = await db.get(Project, project_id)
    if not project or project.user_id != get_user_id(user):
        raise HTTPException(404, "Project not found")
    await db.delete(project)
    await db.commit()
