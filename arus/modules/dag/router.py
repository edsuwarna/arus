"""
DAG Router — returns pipeline dependency graph data for DAG View.
Covers the three-layer asset model: Source → Raw (landing) → Target.
Or two-layer for direct mode: Source → Target.
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
    """Return all pipelines with their asset nodes (source → raw → target for raw mode, source → target for direct)."""
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
        edges = []
        has_raw = False  # track if any table uses raw mode

        for t in tables:
            load_mode = getattr(t, "load_mode", None) or p.load_mode or "direct"

            # Source asset always exists
            assets.append({
                "name": t.source_table,
                "layer": "source",
                "status": pipeline_status,
                "table": t.source_table,
            })

            if load_mode == "raw":
                # Raw mode: source → raw → target
                has_raw = True
                raw_name = f"{safe_name}_{t.source_table}_raw"
                assets.append({
                    "name": raw_name,
                    "layer": "raw",
                    "status": pipeline_status,
                    "table": t.source_table,
                })
                assets.append({
                    "name": t.source_table,
                    "layer": "target",
                    "status": pipeline_status,
                    "table": t.source_table,
                })
                edges.append({"from": t.source_table, "to": raw_name})
                edges.append({"from": raw_name, "to": t.source_table})
            else:
                # Direct mode: source → target
                assets.append({
                    "name": t.source_table,
                    "layer": "target",
                    "status": pipeline_status,
                    "table": t.source_table,
                })
                edges.append({"from": t.source_table, "to": t.source_table})

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
            "has_raw_mode": has_raw,
        })

    return {"status": "ok", "data": result}
