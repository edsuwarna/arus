from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from arus.shared.db.session import get_db
from arus.shared.exceptions import NotFoundError
from arus.modules.pipeline.schemas import PipelineCreate, PipelineUpdate
from arus.modules.pipeline.repository import PipelineRepository
from arus.modules.pipeline.service import PipelineService
from arus.modules.auth.router import get_current_user
from arus.modules.source.models import Source

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
    req: dict = {},
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    force_full = req.get("full_refresh", False) if req else False
    result = service.trigger_pipeline(pipeline_id, force_full_refresh=force_full)
    return {"status": "ok", "data": result}


@router.post("/{pipeline_id}/full-refresh")
async def full_refresh_pipeline(
    pipeline_id: str,
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    """Trigger a full refresh — resets all watermarks and re-syncs all data."""
    result = service.trigger_pipeline(pipeline_id, force_full_refresh=True)
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


@router.post("/pause-all")
async def pause_all_pipelines(
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    pipelines = service.list_pipelines()
    results = []
    for p in pipelines:
        if p["status"] == "active":
            service.update_pipeline(p["id"], {"status": "paused"})
            results.append({"id": p["id"], "name": p["source_name"], "status": "paused"})
    return {"status": "ok", "data": {"paused_count": len(results), "pipelines": results}}


@router.post("/{pipeline_id}/backfill")
async def backfill_pipeline(
    pipeline_id: str,
    req: dict = {},
    service: PipelineService = Depends(get_pipeline_service),
    user: dict = Depends(get_current_user),
):
    """Trigger a backfill from a specific date. Resets watermark then runs.
    POST body: {"from": "2025-01-01"} or empty for full refresh.
    """
    from_date = req.get("from") if req else None
    result = service.trigger_pipeline(pipeline_id, force_full_refresh=True, backfill_from=from_date)
    return {"status": "ok", "data": result}


@router.get("/{pipeline_id}/dead-letters")
async def list_dead_letters(
    pipeline_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List dead letter rows for a pipeline (via its source name)."""
    from arus.modules.pipeline.models import Pipeline
    from sqlalchemy import text as sa_text

    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise NotFoundError(f"Pipeline {pipeline_id} not found")

    source = db.query(Source).filter(Source.id == pipeline.source_id).first()
    source_name = source.name.lower().replace("-", "_").replace(" ", "_") if source else ""

    if not source_name:
        return {"status": "ok", "data": []}

    rows = db.execute(
        sa_text(f"""
            SELECT id, source_name, table_name, run_id, row_data, error_text, failed_at
            FROM staging._dead_letters
            WHERE source_name = :source_name
            ORDER BY failed_at DESC
            LIMIT :lim OFFSET :off
        """),
        {"source_name": source_name, "lim": limit, "off": offset},
    ).fetchall()

    return {
        "status": "ok",
        "data": [
            {
                "id": str(r[0]),
                "source_name": r[1],
                "table_name": r[2],
                "run_id": str(r[3]) if r[3] else None,
                "row_data": r[4],
                "error_text": r[5],
                "failed_at": str(r[6]) if r[6] else None,
            }
            for r in rows
        ],
    }
