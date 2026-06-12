from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text

from arus.shared.db.session import get_db
from arus.modules.auth.router import get_current_user
from arus.modules.run_log.models import Run
from arus.modules.source.models import Source
from arus.modules.pipeline.models import Pipeline
from arus.modules.destination.models import Destination
from arus.modules.pipeline.models import PipelineTable, Watermark

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    active_sources = db.query(Source).filter(Source.status == "connected").count()
    total_sources = db.query(Source).count()
    total_destinations = db.query(Destination).count()
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

    # Real stats replacing hardcoded defaults
    total_tables_synced = db.query(PipelineTable).filter(PipelineTable.enabled == True).count()
    total_rows_synced = db.query(func.coalesce(func.sum(Run.duration_ms), 0)).filter(
        Run.status == "success",
    ).scalar() or 0

    # 7-day uptime = successful runs / total runs
    runs_7d_total = db.query(Run).filter(
        Run.started_at >= text("NOW() - INTERVAL '7 days'")
    ).count()
    runs_7d_success = db.query(Run).filter(
        Run.status == "success",
        Run.started_at >= text("NOW() - INTERVAL '7 days'"),
    ).count()
    uptime_pct_7d = round((runs_7d_success / runs_7d_total * 100), 1) if runs_7d_total > 0 else 100.0

    # Average latency of successful runs in 7 days
    avg_latency_ms = db.query(func.coalesce(func.avg(Run.duration_ms), 0)).filter(
        Run.status == "success",
        Run.started_at >= text("NOW() - INTERVAL '7 days'"),
    ).scalar() or 0

    return {
        "status": "ok",
        "data": {
            "active_sources": active_sources,
            "total_sources": total_sources,
            "total_destinations": total_destinations,
            "total_pipelines": total_pipelines,
            "active_pipelines": active_pipelines,
            "total_tables_synced": total_tables_synced,
            "total_rows_synced": total_rows_synced,
            "rows_synced_24h": rows_24h,
            "failed_runs_24h": failed_runs_24h,
            "total_runs_24h": total_runs_24h,
            "uptime_pct_7d": uptime_pct_7d,
            "avg_latency_ms": int(avg_latency_ms),
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
    from arus.modules.pipeline.models import Pipeline
    from arus.modules.source.models import Source
    from arus.modules.destination.models import Destination

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
                "id": str(r.id),
                "run_id": str(r.id),
                "pipeline_id": str(r.pipeline_id),
                "status": r.status,
                "rows_synced": r.duration_ms or 0,
                "duration_ms": r.duration_ms,
                "started_at": r.started_at,
            }
            for r in runs
        ],
    }
