"""Transform scripts router — CRUD for per-pipeline Python transform scripts."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from arus.shared.db.session import get_db
from arus.shared.exceptions import NotFoundError, ConflictError
from arus.modules.transform.schemas import (
    TransformScriptCreate,
    TransformScriptUpdate,
    TransformScriptResponse,
)
from arus.modules.transform.repository import TransformScriptRepository
from arus.modules.auth.router import get_current_user, require_editor_or_admin

router = APIRouter(prefix="/api/pipelines/{pipeline_id}/scripts", tags=["transform"])


def get_repo(db: Session = Depends(get_db)) -> TransformScriptRepository:
    return TransformScriptRepository(db)


@router.get("")
async def list_scripts(
    pipeline_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    repo: TransformScriptRepository = Depends(get_repo),
    user: dict = Depends(get_current_user),
):
    scripts = repo.list_by_pipeline(pipeline_id, limit=limit, offset=offset)
    total = repo.count_by_pipeline(pipeline_id)
    return {
        "status": "ok",
        "data": {
            "scripts": [
                TransformScriptResponse(
                    id=str(s.id),
                    pipeline_id=str(s.pipeline_id),
                    name=s.name,
                    description=s.description,
                    content=s.content,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                ).model_dump()
                for s in scripts
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.post("")
async def create_script(
    pipeline_id: str,
    req: TransformScriptCreate,
    repo: TransformScriptRepository = Depends(get_repo),
    user: dict = Depends(require_editor_or_admin),
):
    # Check name uniqueness
    existing = repo.get_by_name(pipeline_id, req.name)
    if existing:
        raise ConflictError(f"Script '{req.name}' already exists for this pipeline")

    script = repo.create(pipeline_id, req.model_dump())
    return {
        "status": "ok",
        "data": TransformScriptResponse(
            id=str(script.id),
            pipeline_id=str(script.pipeline_id),
            name=script.name,
            description=script.description,
            content=script.content,
            created_at=script.created_at,
            updated_at=script.updated_at,
        ).model_dump(),
    }


@router.get("/{script_id}")
async def get_script(
    pipeline_id: str,
    script_id: str,
    repo: TransformScriptRepository = Depends(get_repo),
    user: dict = Depends(get_current_user),
):
    script = repo.get_by_id(script_id)
    if not script:
        raise NotFoundError(f"Transform script {script_id} not found")

    return {
        "status": "ok",
        "data": TransformScriptResponse(
            id=str(script.id),
            pipeline_id=str(script.pipeline_id),
            name=script.name,
            description=script.description,
            content=script.content,
            created_at=script.created_at,
            updated_at=script.updated_at,
        ).model_dump(),
    }


@router.put("/{script_id}")
async def update_script(
    pipeline_id: str,
    script_id: str,
    req: TransformScriptUpdate,
    repo: TransformScriptRepository = Depends(get_repo),
    user: dict = Depends(require_editor_or_admin),
):
    script = repo.get_by_id(script_id)
    if not script:
        raise NotFoundError(f"Transform script {script_id} not found")

    data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    if data.get("name"):
        # Check name uniqueness if renaming
        existing = repo.get_by_name(pipeline_id, data["name"])
        if existing and str(existing.id) != script_id:
            raise ConflictError(f"Script name '{data['name']}' already exists")

    script = repo.update(script, data)
    return {
        "status": "ok",
        "data": TransformScriptResponse(
            id=str(script.id),
            pipeline_id=str(script.pipeline_id),
            name=script.name,
            description=script.description,
            content=script.content,
            created_at=script.created_at,
            updated_at=script.updated_at,
        ).model_dump(),
    }


@router.delete("/{script_id}")
async def delete_script(
    pipeline_id: str,
    script_id: str,
    repo: TransformScriptRepository = Depends(get_repo),
    user: dict = Depends(require_editor_or_admin),
):
    script = repo.get_by_id(script_id)
    if not script:
        raise NotFoundError(f"Transform script {script_id} not found")

    repo.delete(script)
    return {"status": "ok", "data": {"deleted": True}}
