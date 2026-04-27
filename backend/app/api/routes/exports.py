"""Export routes — download PPTX."""
import uuid
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_user_id
from app.db.session import get_db
from app.db.models import ResearchRun, Project
from app.exports.pptx import generate_pptx

router = APIRouter()


@router.get("/{run_id}/pptx")
async def download_pptx(
    run_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    run = await db.get(ResearchRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    project = await db.get(Project, run.project_id)
    if not project or project.user_id != get_user_id(user):
        raise HTTPException(404, "Run not found")

    if run.status != "done":
        raise HTTPException(400, f"Run not ready. Status: {run.status}")
    if not run.result:
        raise HTTPException(400, "No result available")

    pptx_bytes = generate_pptx(run.result)

    company = (run.result.get("company_metadata") or {}).get("company_name", "report")
    filename = f"{company.replace(' ', '_')}_briefing.pptx".lower()

    return StreamingResponse(
        BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
