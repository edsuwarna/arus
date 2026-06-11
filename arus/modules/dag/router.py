"""
DAG Router — returns pipeline dependency graph data for DAG View.
Covers the three-layer asset model: Source → Staging (raw) → Analytics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from arus.shared.db.session import get_db
from arus.modules.auth.router import get_current_user
from arus.modules.run_log.models import Run
from arus.modules.pipeline.models import Pipeline, PipelineTable
from arus.modules.source.models import Source

router = APIRouter(prefix="/api/dag", tags=["dag"])


@router.get("")
async def get_dag_data(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return all pipelines with their asset nodes (source → staging → analytics)."""
    pipelines = db.query(Pipeline).all()
    result = []

    for p in pipelines:
        source = db.query(Source).filter(Source.id == p.source_id).first()
        tables = db.query(PipelineTable).filter(
            PipelineTable.pipeline_id == p.id, PipelineTable.enabled == True
        ).all()

        # Get last run status per table
        last_run = (
            db.query(Run)
            .filter(Run.pipeline_id == str(p.id))
            .order_by(desc(Run.started_at))
            .first()
        )

        pipeline_status = last_run.status if last_run else "not_started"
        safe_name = source.name.lower().replace("-", "_").replace(" ", "_") if source else "unknown"

        assets = []
        for t in tables:
            assets.append({
                "name": t.source_table,
                "layer": "source",
                "status": pipeline_status,
                "table": t.source_table,
            })
            assets.append({
                "name": f"stg_{t.source_table}",
                "layer": "staging",
                "status": pipeline_status,
                "table": t.source_table,
            })
            assets.append({
                "name": f"analytics.{t.source_table}",
                "layer": "analytics",
                "status": pipeline_status,
                "table": t.source_table,
            })

        # Build dependency edges
        edges = []
        for t in tables:
            edges.append({"from": t.source_table, "to": f"stg_{t.source_table}"})
            edges.append({"from": f"stg_{t.source_table}", "to": f"analytics.{t.source_table}"})

        result.append({
            "id": str(p.id),
            "name": p.name,
            "source_name": source.name if source else "Unknown",
            "status": p.status,
            "pipeline_status": pipeline_status,
            "assets": assets,
            "edges": edges,
            "table_count": len(tables),
            "last_run_status": pipeline_status,
        })

    return {"status": "ok", "data": result}
