from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text

from arus.shared.db.session import get_db
from arus.modules.auth.router import get_current_user
from arus.modules.run_log.models import Run
from arus.modules.source.models import Source
from arus.modules.pipeline.models import Pipeline

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    active_sources = db.query(Source).filter(Source.status == "connected").count()
    total_pipelines = db.query(Pipeline).count()
    active_pipelines = db.query(Pipeline).filter(Pipeline.status == "active").count()

    runs_24h = (
        db.query(Run)
        .filter(Run.started_at >= text("NOW() - INTERVAL '24 hours'"))
    )
    total_runs_24h = runs_24h.count()
    failed_runs_24h = runs_24h.filter(Run.status == "failed").count()

    # Sum of rows synced in last 24h (stored as duration_ms for simplicity)
    rows_24h = db.query(func.coalesce(func.sum(Run.duration_ms), 0)).filter(
        Run.started_at >= text("NOW() - INTERVAL '24 hours'")
    ).scalar() or 0

    # New sources this week
    sources_this_week = db.query(Source).filter(
        Source.created_at >= text("NOW() - INTERVAL '7 days'")
    ).count()

    # Pipeline health — count running/degraded/failed
    running_pipelines = db.query(Pipeline).filter(Pipeline.status == "active").count()
    failed_pipelines = db.query(Run).filter(
        Run.status == "failed",
        Run.started_at >= text("NOW() - INTERVAL '1 hour'"),
    ).distinct(Run.pipeline_id).count()

    return {
        "status": "ok",
        "data": {
            "active_sources": active_sources,
            "total_pipelines": total_pipelines,
            "active_pipelines": active_pipelines,
            "total_tables_synced": 0,
            "total_rows_synced": 0,
            "rows_synced_24h": rows_24h,
            "failed_runs_24h": failed_runs_24h,
            "total_runs_24h": total_runs_24h,
            "uptime_pct_7d": 100.0,
            "avg_latency_ms": 0,
            "new_sources_week": sources_this_week,
            "running_pipelines": running_pipelines,
            "degraded_pipelines": failed_pipelines,
        },
    }


@router.get("/recent-runs")
async def recent_runs(
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    runs = (
        db.query(Run)
        .order_by(desc(Run.started_at))
        .limit(limit)
        .all()
    )
    return {
        "status": "ok",
        "data": [
            {
                "run_id": str(r.id),
                "pipeline_id": str(r.pipeline_id),
                "pipeline_name": "",
                "status": r.status,
                "rows_synced": 0,
                "duration_ms": r.duration_ms,
                "started_at": r.started_at,
            }
            for r in runs
        ],
    }
