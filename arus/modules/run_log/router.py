from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text as sa_text

from arus.shared.db.session import get_db
from arus.modules.run_log.repository import RunLogRepository
from arus.modules.run_log.models import Run
from arus.modules.auth.router import get_current_user, require_editor_or_admin

router = APIRouter(prefix="/api", tags=["runs"])


def get_run_log_repo(db: Session = Depends(get_db)) -> RunLogRepository:
    return RunLogRepository(db)


@router.get("/pipelines/{pipeline_id}/runs")
async def list_runs(
    pipeline_id: str,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    repo: RunLogRepository = Depends(get_run_log_repo),
    user: dict = Depends(get_current_user),
):
    runs = repo.get_runs(pipeline_id, limit=limit, offset=offset)
    return {
        "status": "ok",
        "data": [
            {
                "id": str(r.id),
                "pipeline_id": str(r.pipeline_id),
                "status": r.status,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "duration_ms": r.duration_ms,
                "trigger_type": r.trigger_type,
                "error_message": r.error_message,
            }
            for r in runs
        ],
    }


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    repo: RunLogRepository = Depends(get_run_log_repo),
    user: dict = Depends(get_current_user),
):
    from arus.modules.run_log.models import Run
    run = repo.db.query(Run).filter(Run.id == run_id).first()
    if not run:
        from arus.shared.exceptions import NotFoundError
        raise NotFoundError(f"Run {run_id} not found")

    return {
        "status": "ok",
        "data": {
            "id": str(run.id),
            "pipeline_id": str(run.pipeline_id),
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "duration_ms": run.duration_ms,
            "trigger_type": run.trigger_type,
            "error_message": run.error_message,
        },
    }


@router.get("/runs/{run_id}/logs")
async def get_run_logs(
    run_id: str,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    repo: RunLogRepository = Depends(get_run_log_repo),
    user: dict = Depends(get_current_user),
):
    logs = repo.get_logs(run_id, limit=limit, offset=offset)
    return {
        "status": "ok",
        "data": {
            "run_id": run_id,
            "logs": [
                {"timestamp": log.timestamp, "level": log.level, "message": log.message}
                for log in logs
            ],
            "total": len(logs),
            "offset": offset,
            "limit": limit,
        },
    }


@router.get("/runs")
async def list_all_runs(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query(None, description="Filter by status: success, failed, running"),
    pipeline_id: str = Query(None, description="Filter by pipeline ID"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all runs across all pipelines with optional filters."""
    from arus.modules.pipeline.models import Pipeline

    q = db.query(Run, Pipeline.name.label("pipeline_name")).join(
        Pipeline, Run.pipeline_id == Pipeline.id, isouter=True
    )
    if status:
        q = q.filter(Run.status == status)
    if pipeline_id:
        q = q.filter(Run.pipeline_id == pipeline_id)

    total = q.count()
    runs = q.order_by(desc(Run.started_at)).offset(offset).limit(limit).all()

    return {
        "status": "ok",
        "data": {
            "runs": [
                {
                    "id": str(r.Run.id),
                    "pipeline_id": str(r.Run.pipeline_id),
                    "pipeline_name": r.pipeline_name or "",
                    "status": r.Run.status,
                    "started_at": r.Run.started_at,
                    "finished_at": r.Run.finished_at,
                    "duration_ms": r.Run.duration_ms,
                    "trigger_type": r.Run.trigger_type,
                    "error_message": r.Run.error_message,
                }
                for r in runs
            ],
            "total": total,
            "offset": offset,
            "limit": limit,
        },
    }


@router.get("/runs/stats/daily")
async def daily_run_stats(
    days: int = Query(7, le=30),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Daily rows synced stats for dashboard chart."""
    from arus.modules.pipeline.models import Pipeline

    rows = (
        db.query(
            func.date_trunc("day", Run.started_at).label("day"),
            func.count(Run.id).label("run_count"),
            func.coalesce(func.sum(Run.duration_ms), 0).label("total_rows"),
        )
        .filter(Run.started_at >= sa_text(f"NOW() - INTERVAL '{days} days'"))
        .group_by(func.date_trunc("day", Run.started_at))
        .order_by(func.date_trunc("day", Run.started_at))
        .all()
    )

    return {
        "status": "ok",
        "data": [
            {
                "date": str(r.day),
                "run_count": r.run_count,
                "total_rows": r.total_rows,
            }
            for r in rows
        ],
    }


@router.post("/runs/{run_id}/cancel")
async def cancel_run(
    run_id: str,
    repo: RunLogRepository = Depends(get_run_log_repo),
    user: dict = Depends(get_current_user),
):
    """Cancel a running/pending/queued run."""
    try:
        cancelled = repo.cancel_run(run_id)
        if not cancelled:
            from arus.shared.exceptions import NotFoundError
            raise NotFoundError(f"Run {run_id} not found")
        return {"status": "ok", "data": {"run_id": run_id, "status": "cancelled"}}
    except ValueError as e:
        from arus.shared.exceptions import ConflictError
        raise ConflictError(str(e))


@router.post("/runs/{run_id}/retry")
async def retry_run(
    run_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(require_editor_or_admin),
):
    """Retry a failed run — re-triggers the pipeline."""
    from arus.shared.exceptions import NotFoundError, ConflictError
    from arus.modules.pipeline.repository import PipelineRepository
    from arus.modules.pipeline.service import PipelineService

    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise NotFoundError(f"Run {run_id} not found")
    if run.status not in ("failed", "cancelled"):
        raise ConflictError(f"Cannot retry run with status '{run.status}'")

    pipe_service = PipelineService(PipelineRepository(db), db)
    result = pipe_service.trigger_pipeline(str(run.pipeline_id))

    return {"status": "ok", "data": result}
