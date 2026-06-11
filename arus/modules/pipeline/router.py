from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from arus.shared.db.session import get_db
from arus.shared.exceptions import NotFoundError
from arus.modules.pipeline.schemas import PipelineCreate, PipelineUpdate
from arus.modules.pipeline.repository import PipelineRepository
from arus.modules.pipeline.service import PipelineService
from arus.modules.auth.router import get_current_user

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


def get_pipeline_service(db: Session = Depends(get_db)) -> PipelineService:
    return PipelineService(PipelineRepository(db), db)


@router.get("")
async def list_pipelines(
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    pipelines = service.list_pipelines()
    return {"status": "ok", "data": pipelines}


@router.post("")
async def create_pipeline(
    req: PipelineCreate,
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    result = service.create_pipeline(req.model_dump())
    return {"status": "ok", "data": result}


@router.get("/{pipeline_id}")
async def get_pipeline(
    pipeline_id: str,
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    result = service.get_pipeline(pipeline_id)
    if not result:
        raise NotFoundError(f"Pipeline {pipeline_id} not found")
    return {"status": "ok", "data": result}


@router.put("/{pipeline_id}")
async def update_pipeline(
    pipeline_id: str,
    req: PipelineUpdate,
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    data = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    result = service.update_pipeline(pipeline_id, data)
    return {"status": "ok", "data": result}


@router.delete("/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    service.delete_pipeline(pipeline_id)
    return {"status": "ok", "data": {"deleted": True}}


@router.post("/{pipeline_id}/trigger")
async def trigger_pipeline(
    pipeline_id: str,
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    result = service.trigger_pipeline(pipeline_id)
    return {"status": "ok", "data": result}


@router.post("/{pipeline_id}/pause")
async def pause_pipeline(
    pipeline_id: str,
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    result = service.update_pipeline(pipeline_id, {"status": "paused"})
    return {"status": "ok", "data": {"pipeline_id": pipeline_id, "status": "paused"}}


@router.post("/{pipeline_id}/resume")
async def resume_pipeline(
    pipeline_id: str,
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    result = service.update_pipeline(pipeline_id, {"status": "active"})
    return {"status": "ok", "data": {"pipeline_id": pipeline_id, "status": "active"}}
