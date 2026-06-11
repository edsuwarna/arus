"""
Pipeline executor — runs a single pipeline cycle:
  extract → load raw → normalize → update watermark

Phase 2 features:
  - Retry + exponential backoff (tenacity)
  - Dead Letter Queue for failed rows
  - Schema Drift Detection
  - Pipeline Dependency Checks
  - Data Quality Checks
  - Alert Integration (Telegram)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log, retry_if_exception_type

from arus.shared.crypto import decrypt_password
from arus.shared.config import settings
from arus.modules.connector.registry import get_source, get_destination
from arus.modules.pipeline.dead_letter import DeadLetterManager
from arus.modules.pipeline.quality import DataQualityChecker
from arus.modules.pipeline.deps import DependencyResolver
from arus.modules.alert import AlertManager
from arus.modules.run_log.models import Run, RunTableStat
from arus.modules.run_log.repository import RunLogRepository

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when extraction fails after retries."""
    pass


class LoadError(Exception):
    """Raised when loading fails after retries."""
    pass


class PipelineExecutor:
    def __init__(self, source_config: dict, dest_config: dict, db_session=None):
        self.source_config = source_config
        self.dest_config = dest_config
        self.db_session = db_session
        self.dead_letter_mgr = DeadLetterManager(db_session)
        self.quality_checker = DataQualityChecker(db_session)
        self.alert_mgr = AlertManager()
        self.run_log_repo = None
        if db_session:
            self.run_log_repo = RunLogRepository(db_session)

    def _make_retry_decorator(self, desc: str):
        """Create a tenacity retry decorator with exponential backoff."""
        return retry(
            stop=stop_after_attempt(settings.max_retries),
            wait=wait_exponential(
                multiplier=settings.initial_backoff,
                min=settings.initial_backoff,
                max=settings.initial_backoff * 8,
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    def run(self, pipeline_id: str, tables: list[dict]) -> dict:
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        results = []
        error = None
        pipeline_name = self.source_config.get("safe_name", self.source_config.get("name", "unknown"))

        # Create run_log entry if db_session is available
        run_record = None
        if self.run_log_repo:
            try:
                run_record = self.run_log_repo.create_run(pipeline_id, trigger_type="manual")
                self.run_log_repo.add_log(str(run_record.id), "INFO", "Pipeline run started")
            except Exception as e:
                logger.warning(f"Could not create run_log entry: {e}")

        try:
            # Check pipeline dependencies
            if self.db_session:
                resolver = DependencyResolver(self.db_session)
                dep_check = resolver.check_dependency_satisfied(pipeline_id)
                if not dep_check["satisfied"]:
                    msg = (
                        f"Dependency not satisfied for pipeline {pipeline_id}: "
                        f"{dep_check.get('reason', 'unknown')}"
                    )
                    logger.warning(msg)
                    if self.run_log_repo and run_record:
                        self.run_log_repo.add_log(str(run_record.id), "WARNING", msg)
                    return {
                        "run_id": run_id,
                        "status": "skipped",
                        "error": msg,
                        "results": results,
                        "started_at": started_at.isoformat() if started_at else None,
                        "finished_at": datetime.now(timezone.utc).isoformat(),
                        "duration_ms": 0,
                    }

            # Connect to destination
            dest_class = get_destination(self.dest_config["type"])
            dest = dest_class()
            dest.connect(self.dest_config)

            # Connect to source
            src_class = get_source(self.source_config["type"])
            src = src_class()
            src_config = dict(self.source_config)
            src_config["password"] = decrypt_password(src_config.pop("password_enc", src_config.get("password", "")))
            src.connect(src_config)

            safe_name = self.source_config.get("safe_name", self.source_config.get("name", "source"))

            for table_info in tables:
                table = table_info["source_table"]
                watermark = table_info.get("watermark_value")
                sync_mode = table_info.get("sync_mode", "incremental")
                columns = table_info.get("columns", [])

                # Ensure schema
                if columns:
                    try:
                        dest.ensure_schema(safe_name, table, columns)
                    except Exception as e:
                        logger.error(f"Schema creation failed for {table}: {e}")
                        results.append({
                            "table": table, "rows": 0, "status": "failed",
                            "error": f"Schema creation failed: {e}",
                        })
                        continue

                # --- Schema Drift Detection (Phase 2) ---
                drift_cols = self._detect_schema_drift(dest, safe_name, table, columns)
                if drift_cols:
                    if settings.auto_alter_schema:
                        try:
                            self._auto_alter_table(dest, safe_name, table, columns, drift_cols)
                            logger.info(f"Auto-altered table {table} with columns: {drift_cols}")
                        except Exception as e:
                            logger.error(f"Auto-alter failed for {table}: {e}")

                # --- RETRY: Extract with exponential backoff (Phase 2) ---
                try:
                    rows_batches = self._extract_with_retry(src, table, watermark, sync_mode)
                except ExtractionError as e:
                    err_msg = f"Extraction failed for {table}: {e}"
                    logger.error(err_msg)
                    results.append({
                        "table": table, "rows": 0, "status": "failed", "error": err_msg,
                    })
                    continue

                all_rows = []
                for batch in rows_batches:
                    all_rows.extend(batch)

                if not all_rows:
                    results.append({
                        "table": table, "rows": 0, "status": "success", "duration_ms": 0,
                    })
                    continue

                # --- RETRY: Load raw with exponential backoff (Phase 2) ---
                try:
                    loaded_raw = self._load_raw_with_retry(dest, safe_name, table, all_rows, run_id)
                except LoadError as e:
                    err_msg = f"Raw load failed for {table}: {e}"
                    logger.error(err_msg)
                    # Dead Letter Queue (Phase 2) — save failed rows
                    self.dead_letter_mgr.write_failed_rows(
                        source_name=safe_name,
                        table_name=table,
                        run_id=run_id,
                        rows=all_rows,
                        error_text=err_msg,
                    )
                    # Send alert
                    if self.alert_mgr.is_enabled():
                        self.alert_mgr.alert_dead_letter(
                            pipeline_id=pipeline_id,
                            pipeline_name=pipeline_name,
                            run_id=run_id,
                            table_name=table,
                            row_count=len(all_rows),
                            error=err_msg,
                        )
                    if self.alert_mgr.is_enabled():
                        self.alert_mgr.alert_pipeline_failure(
                            pipeline_id=pipeline_id,
                            pipeline_name=pipeline_name,
                            run_id=run_id,
                            error=err_msg,
                        )
                    results.append({
                        "table": table, "rows": 0, "status": "failed", "error": err_msg,
                    })
                    continue

                # --- Load normalized ---
                try:
                    loaded_norm = dest.load_normalized(safe_name, table, all_rows)
                except Exception as e:
                    logger.error(f"Normalized load failed for {table}: {e}")
                    # Dead letter for normalized load failures
                    self.dead_letter_mgr.write_failed_rows(
                        source_name=safe_name,
                        table_name=table,
                        run_id=run_id,
                        rows=all_rows,
                        error_text=f"Normalized load failed: {e}",
                    )
                    loaded_norm = 0

                # --- Update watermark ---
                if sync_mode == "incremental" and all_rows:
                    wm_col = table_info.get("watermark_column")
                    if wm_col and wm_col in all_rows[-1]:
                        last_val = all_rows[-1][wm_col]
                        dest.update_watermark(pipeline_id, table, last_val)

                # --- Data Quality Checks (Phase 2) ---
                if self.db_session:
                    quality_results = self._run_quality_checks(
                        pipeline_id=pipeline_id,
                        run_id=run_id,
                        table_name=table,
                        rows_extracted=len(all_rows),
                        rows_loaded=loaded_raw,
                        rows=all_rows,
                        required_columns=[c["name"] for c in columns if not c.get("nullable", True)],
                    )

                results.append({
                    "table": table,
                    "rows": len(all_rows),
                    "status": "success",
                })

        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} failed: {e}")
            error = str(e)
            # Send alert on pipeline failure
            if self.alert_mgr.is_enabled():
                self.alert_mgr.alert_pipeline_failure(
                    pipeline_id=pipeline_id,
                    pipeline_name=pipeline_name,
                    run_id=run_id,
                    error=error or "Unknown error",
                )

        finished_at = datetime.now(timezone.utc)

        # Update run_log if applicable
        if self.run_log_repo and run_record:
            try:
                self.run_log_repo.update_run(str(run_record.id), {
                    "status": "failed" if error else "success",
                    "finished_at": finished_at,
                    "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
                    "error_message": error,
                })
            except Exception as e:
                logger.warning(f"Could not update run_log: {e}")

        return {
            "run_id": run_id,
            "status": "failed" if error else "success",
            "error": error,
            "results": results,
            "started_at": started_at.isoformat() if started_at else None,
            "finished_at": finished_at.isoformat() if finished_at else None,
            "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
        }

    # ---- Retry wrappers (Phase 2) ----

    def _extract_with_retry(self, src, table: str, watermark, sync_mode: str):
        """Extract data with tenacity retry."""
        extract_retry = self._make_retry_decorator(f"extract {table}")

        @extract_retry
        def _do_extract():
            logger.info(f"Extracting {table} (watermark={watermark})")
            return list(
                src.extract(
                    table,
                    watermark=watermark if watermark and sync_mode == "incremental" else None,
                )
            )

        try:
            return _do_extract()
        except Exception as e:
            raise ExtractionError(f"Extraction failed after {settings.max_retries} retries: {e}") from e

    def _load_raw_with_retry(self, dest, source_name: str, table: str, rows: list[dict], run_id: str) -> int:
        """Load raw data with tenacity retry."""
        load_retry = self._make_retry_decorator(f"load_raw {table}")

        loaded = 0

        @load_retry
        def _do_load():
            nonlocal loaded
            logger.info(f"Loading {len(rows)} rows into raw table {table}")
            loaded = dest.load_raw(source_name, table, rows, run_id)
            return loaded

        try:
            return _do_load()
        except Exception as e:
            raise LoadError(f"Raw load failed after {settings.max_retries} retries: {e}") from e

    # ---- Schema Drift Detection (Phase 2) ----

    def _detect_schema_drift(self, dest, source_name: str, table: str, source_columns: list[dict]) -> list[str]:
        """
        Compare source columns against warehouse table columns.
        Returns list of new column names not present in warehouse.
        """
        try:
            safe_source = source_name.lower().replace("-", "_").replace(" ", "_")
            analytics_schema = dest.config.get("analytics_schema", "analytics")
            schema_table = f"{analytics_schema}.{table}"

            with dest.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    """,
                    (analytics_schema, table),
                )
                existing_cols = {row[0].lower() for row in cur.fetchall()}

            # Filter out metadata columns (starting with _)
            existing_cols = {c for c in existing_cols if not c.startswith("_")}
            source_names = {c["name"].lower() for c in source_columns}

            new_cols = source_names - existing_cols
            if new_cols:
                logger.warning(
                    f"[SCHEMA DRIFT] Table {schema_table} missing columns: {new_cols}"
                )
                if self.alert_mgr.is_enabled():
                    self.alert_mgr.alert_schema_drift(
                        pipeline_id="N/A",
                        pipeline_name=source_name,
                        table_name=table,
                        new_columns=list(new_cols),
                    )

            return list(new_cols)
        except Exception as e:
            logger.warning(f"Schema drift detection failed for {table}: {e}")
            return []

    def _auto_alter_table(self, dest, source_name: str, table: str, source_columns: list[dict], new_cols: list[str]):
        """Automatically add new columns to the warehouse table."""
        analytics_schema = dest.config.get("analytics_schema", "analytics")
        from arus.shared.types import map_type

        with dest.conn.cursor() as cur:
            for col in source_columns:
                if col["name"].lower() in new_cols:
                    pg_type = map_type(col["type"])
                    cur.execute(
                        f'ALTER TABLE "{analytics_schema}"."{table}" '
                        f'ADD COLUMN "{col["name"]}" {pg_type}'
                    )
                    logger.info(f"  → Added column: {col['name']} ({pg_type})")
        dest.conn.commit()

    # ---- Data Quality Checks (Phase 2) ----

    def _run_quality_checks(
        self,
        pipeline_id: str,
        run_id: str,
        table_name: str,
        rows_extracted: int,
        rows_loaded: int,
        rows: list[dict],
        required_columns: list[str],
    ) -> dict:
        """Run row count and null checks, return combined result."""
        results = {}

        # Row count validation
        count_result = self.quality_checker.check_row_count(
            pipeline_id=pipeline_id,
            run_id=run_id,
            table_name=table_name,
            rows_extracted=rows_extracted,
            rows_loaded=rows_loaded,
        )
        results["row_count"] = count_result

        # Null checks on required columns
        null_result = self.quality_checker.check_nulls(
            pipeline_id=pipeline_id,
            run_id=run_id,
            table_name=table_name,
            rows=rows,
            required_columns=required_columns,
        )
        results["null_check"] = null_result

        return results
