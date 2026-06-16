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
from arus.modules.run_log.models import Run, RunTableStat
from arus.modules.pipeline.models import Pipeline, PipelineTable
from arus.modules.source.models import Source
from arus.modules.destination.models import Destination

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
        destination = db.query(Destination).filter(Destination.id == p.destination_id).first()
        tables = db.query(PipelineTable).filter(
            PipelineTable.pipeline_id == p.id, PipelineTable.enabled == True
        ).all()

        # Get last run and per-table stats
        last_run = (
            db.query(Run)
            .filter(Run.pipeline_id == str(p.id))
            .order_by(desc(Run.started_at))
            .first()
        )
        pipeline_status = last_run.status if last_run else "not_started"
        currently_running = last_run and last_run.status == "running"

        # Get per-table stats from the last completed run
        table_stats = {}
        if last_run:
            stats = db.query(RunTableStat).filter(RunTableStat.run_id == last_run.id).all()
            for s in stats:
                table_stats[s.table_name] = s

        def asset_status(table_name):
            """Derive per-asset status. If currently running, all show 'running'.
            Otherwise check per-table stat, fallback to pipeline-level status."""
            if currently_running:
                return "running"
            stat = table_stats.get(table_name)
            if stat:
                if stat.error_message:
                    return "failed"
                return "success"
            return pipeline_status

        safe_name = source.name.lower().replace("-", "_").replace(" ", "_") if source else "unknown"

        assets = []
        edges = []
        has_raw = False  # track if any table uses raw mode

        for t in tables:
            load_mode = getattr(t, "load_mode", None) or p.load_mode or "direct"
            status = asset_status(t.source_table)
            stat = table_stats.get(t.source_table)

            # ---- Source asset ----
            assets.append({
                "name": t.source_table,
                "layer": "source",
                "status": status,
                "table": t.source_table,
                "schema": t.source_schema,
                "sync_mode": t.sync_mode,
                "source_type": source.type if source else None,
                "source_host": source.host if source else None,
                "source_port": source.port if source else None,
                "source_database": source.database if source else None,
                "rows": stat.rows_extracted if stat else 0,
                "duration_ms": stat.duration_ms if stat else 0,
                "error": stat.error_message if stat else None,
            })

            if load_mode == "raw":
                # ---- Raw mode: source → raw → target ----
                has_raw = True
                raw_name = f"{safe_name}_{t.source_table}_raw"
                raw_status = asset_status(raw_name)
                raw_stat = table_stats.get(raw_name)

                assets.append({
                    "name": raw_name,
                    "layer": "raw",
                    "status": raw_status,
                    "table": t.source_table,
                    "schema": t.source_schema,
                    "sync_mode": t.sync_mode,
                    "raw_table": raw_name,
                    "raw_schema": destination.raw_schema if destination else "staging",
                    "rows": raw_stat.rows_loaded_raw if raw_stat else 0,
                    "duration_ms": raw_stat.duration_ms if raw_stat else 0,
                    "error": raw_stat.error_message if raw_stat else None,
                })

                target_status = asset_status(t.source_table)
                target_stat = table_stats.get(t.source_table)

                assets.append({
                    "name": t.source_table,
                    "layer": "target",
                    "status": target_status,
                    "table": t.source_table,
                    "schema": t.source_schema,
                    "sync_mode": t.sync_mode,
                    "target_table": t.source_table,
                    "target_schema": t.target_schema or (destination.target_schema if destination else None),
                    "rows": target_stat.rows_loaded_analytics if target_stat else 0,
                    "duration_ms": target_stat.duration_ms if target_stat else 0,
                    "error": target_stat.error_message if target_stat else None,
                })

                edges.append({"from": t.source_table, "to": raw_name})
                edges.append({"from": raw_name, "to": t.source_table})
            else:
                # ---- Direct mode: source → target ----
                assets.append({
                    "name": t.source_table,
                    "layer": "target",
                    "status": status,
                    "table": t.source_table,
                    "schema": t.source_schema,
                    "sync_mode": t.sync_mode,
                    "target_table": t.source_table,
                    "target_schema": t.target_schema or (destination.target_schema if destination else None),
                    "rows": stat.rows_loaded_analytics if stat else 0,
                    "duration_ms": stat.duration_ms if stat else 0,
                    "error": stat.error_message if stat else None,
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
