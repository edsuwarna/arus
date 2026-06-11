"""
PipelineService — manages pipeline lifecycle:
  create, update, delete, trigger, auto-create from source
"""
import logging
from datetime import datetime, timezone

from arus.shared.exceptions import NotFoundError
from arus.shared.crypto import decrypt_password
from arus.modules.pipeline.repository import PipelineRepository
from arus.modules.pipeline.executor import PipelineExecutor
from arus.modules.connector.registry import get_source

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(self, repo: PipelineRepository, db_session):
        self.repo = repo
        self.db = db_session

    def list_pipelines(self) -> list[dict]:
        pipelines = self.repo.list_all()
        result = []
        for p in pipelines:
            source = self._get_source(p.source_id)
            tables = self.repo.get_tables(str(p.id))
            result.append({
                "id": str(p.id),
                "name": p.name,
                "source_id": str(p.source_id) if p.source_id else "",
                "source_name": source.name if source else "",
                "status": p.status,
                "schedule": p.schedule,
                "depends_on": str(p.depends_on) if p.depends_on else None,
                "enabled_table_count": len(tables),
                "total_rows_synced": 0,
                "error_count_7d": 0,
                "last_run": None,
                "created_at": p.created_at,
            })
        return result

    def get_pipeline(self, pipeline_id: str) -> dict | None:
        p = self.repo.get_by_id(pipeline_id)
        if not p:
            return None

        source = self._get_source(p.source_id)
        dest = self._get_destination(p.destination_id)
        tables = self.repo.get_tables(str(p.id))

        table_details = []
        for t in tables:
            wm = self.repo.get_watermark(str(p.id), t.source_table)
            table_details.append({
                "name": t.source_table,
                "sync_mode": t.sync_mode,
                "watermark_column": t.watermark_column,
                "watermark_value": wm.watermark_value if wm else None,
                "enabled": t.enabled,
            })

        return {
            "id": str(p.id),
            "name": p.name,
            "source": {"id": str(source.id), "name": source.name, "type": source.type} if source else {},
            "destination": {"id": str(dest.id), "name": dest.name, "type": dest.type} if dest else {},
            "status": p.status,
            "schedule": p.schedule,
            "tables": table_details,
            "stats": {
                "total_rows_synced": 0,
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
            },
            "created_at": p.created_at,
        }

    def create_pipeline(self, data: dict) -> dict:
        tables = data.pop("tables", None)
        p = self.repo.create(data)
        if tables:
            table_list = [{"source_table": t, "sync_mode": "incremental", "enabled": True} for t in tables]
            self.repo.set_tables(str(p.id), table_list)
        return {"id": str(p.id)}

    def update_pipeline(self, pipeline_id: str, data: dict) -> dict:
        p = self.repo.get_by_id(pipeline_id)
        if not p:
            raise NotFoundError(f"Pipeline {pipeline_id} not found")

        tables = data.pop("tables", None)
        self.repo.update(p, data)
        if tables is not None:
            table_list = [{"source_table": t, "sync_mode": "incremental", "enabled": True} for t in tables]
            self.repo.set_tables(pipeline_id, table_list)
        return {"updated": True}

    def delete_pipeline(self, pipeline_id: str) -> None:
        p = self.repo.get_by_id(pipeline_id)
        if not p:
            raise NotFoundError(f"Pipeline {pipeline_id} not found")
        self.repo.delete(p)

    def trigger_pipeline(self, pipeline_id: str) -> dict:
        """Manually trigger a pipeline run."""
        p = self.repo.get_by_id(pipeline_id)
        if not p:
            raise NotFoundError(f"Pipeline {pipeline_id} not found")

        source = self._get_source(p.source_id)
        dest = self._get_destination(p.destination_id)
        tables = self.repo.get_tables(str(p.id))

        if not tables:
            return {"run_id": None, "status": "skipped", "error": "No enabled tables"}

        # Check if pipeline is active
        if p.status != "active":
            return {"run_id": None, "status": "skipped", "error": f"Pipeline status is {p.status}"}

        # Build table configs with watermark info
        table_configs = []
        for t in tables:
            wm = self.repo.get_watermark(str(p.id), t.source_table)
            columns = self._get_source_columns(source, t.source_table)
            table_configs.append({
                "source_table": t.source_table,
                "sync_mode": t.sync_mode,
                "watermark_column": t.watermark_column,
                "watermark_value": wm.watermark_value if wm else None,
                "columns": columns,
            })

        # Build connector configs
        source_config = {
            "type": source.type,
            "host": source.host,
            "port": source.port,
            "username": source.username,
            "password_enc": source.password_enc,
            "database": source.database,
            "ssl": source.ssl,
            "name": source.name,
            "safe_name": source.name.lower().replace("-", "_").replace(" ", "_"),
        }

        dest_config = {
            "type": dest.type,
            "host": dest.host,
            "port": dest.port,
            "username": dest.username,
            "password": decrypt_password(dest.password_enc),
            "database": dest.database,
            "raw_schema": dest.raw_schema,
            "analytics_schema": dest.analytics_schema,
        }

        # Execute with db_session for Phase 2 features
        executor = PipelineExecutor(source_config, dest_config, db_session=self.db)
        result = executor.run(str(p.id), table_configs)

        return result

    def auto_create_from_source(self, source_id: str, destination_id: str, tables: list[dict]) -> dict:
        """
        Auto-create a pipeline from discovered tables.
        Called after source discovery + table selection.
        """
        source = self._get_source(source_id)
        existing = self.repo.get_by_source(source_id)
        if existing:
            # Update existing pipeline tables
            table_list = []
            for t in tables:
                table_list.append({
                    "source_table": t["name"],
                    "source_schema": t.get("schema", "public"),
                    "sync_mode": t.get("detected_sync", "incremental"),
                    "watermark_column": t.get("watermark_column"),
                    "enabled": t.get("enabled", True),
                })
            self.repo.set_tables(str(existing.id), table_list)
            return {"id": str(existing.id), "updated": True, "auto_created": False}

        # Create new pipeline
        pipeline_data = {
            "name": f"{source.name} → Warehouse",
            "source_id": source_id,
            "destination_id": destination_id,
            "schedule": "*/5 * * * *",
            "status": "active",
        }
        result = self.create_pipeline(pipeline_data)
        if tables:
            table_list = []
            for t in tables:
                table_list.append({
                    "source_table": t["name"],
                    "source_schema": t.get("schema", "public"),
                    "sync_mode": t.get("detected_sync", "incremental"),
                    "watermark_column": t.get("watermark_column"),
                    "enabled": t.get("enabled", True),
                })
            self.repo.set_tables(result["id"], table_list)
        return {"id": result["id"], "updated": False, "auto_created": True}

    def _get_source(self, source_id):
        from arus.modules.source.models import Source
        return self.db.query(Source).filter(Source.id == source_id).first()

    def _get_destination(self, dest_id):
        from arus.modules.destination.models import Destination
        return self.db.query(Destination).filter(Destination.id == dest_id).first()

    def _get_source_columns(self, source, table: str) -> list[dict]:
        try:
            connector_class = get_source(source.type)
            connector = connector_class()
            connector.connect({
                "host": source.host,
                "port": source.port,
                "username": source.username,
                "password": decrypt_password(source.password_enc),
                "database": source.database,
                "ssl": source.ssl,
            })
            return connector.get_table_columns(table)
        except Exception:
            return []
