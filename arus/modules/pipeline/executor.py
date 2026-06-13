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
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError
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
from arus.modules.notification.service import NotificationService
from arus.modules.notification.repository import NotificationRepository
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
        self.notif_svc = None
        if db_session:
            self.notif_svc = NotificationService(NotificationRepository(db_session))
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

    def run(self, pipeline_id: str, tables: list[dict], timeout_seconds: int = 300) -> dict:
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)
        results = []
        error = None
        pipeline_name = self.source_config.get("safe_name", self.source_config.get("name", "unknown"))

        # Wrap execution in a timeout
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._run_inner, pipeline_id, run_id, started_at, tables)

        try:
            result = future.result(timeout=timeout_seconds)
            return result
        except TimeoutError:
            error = f"Pipeline timed out after {timeout_seconds}s"
            logger.error(f"Pipeline {pipeline_id}: {error}")
            # Cancel the future (best-effort)
            future.cancel()
            # Send alert
            if self.alert_mgr.is_enabled():
                self.alert_mgr.alert_pipeline_failure(
                    pipeline_id=pipeline_id,
                    pipeline_name=pipeline_name,
                    run_id=run_id,
                    error=error,
                )
            if self.notif_svc:
                self.notif_svc.notify_pipeline_event(
                    pipeline_id=pipeline_id,
                    event_type="failure",
                    pipeline_name=pipeline_name,
                    run_id=run_id,
                    error=error,
                )
            return {
                "run_id": run_id,
                "status": "failed",
                "error": error,
                "results": results,
                "started_at": started_at.isoformat() if started_at else None,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": timeout_seconds * 1000,
            }
        except Exception as e:
            logger.error(f"Pipeline {pipeline_id} failed: {e}")
            error = str(e)
            if self.alert_mgr.is_enabled():
                self.alert_mgr.alert_pipeline_failure(
                    pipeline_id=pipeline_id,
                    pipeline_name=pipeline_name,
                    run_id=run_id,
                    error=error or "Unknown error",
                )
            if self.notif_svc:
                self.notif_svc.notify_pipeline_event(
                    pipeline_id=pipeline_id,
                    event_type="failure",
                    pipeline_name=pipeline_name,
                    run_id=run_id,
                    error=error or "Unknown error",
                )
            return {
                "run_id": run_id,
                "status": "failed",
                "error": error,
                "results": results,
                "started_at": started_at.isoformat() if started_at else None,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000),
            }
        finally:
            executor.shutdown(wait=False)

    def _run_inner(self, pipeline_id: str, run_id: str, started_at, tables: list[dict]) -> dict:
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
                per_table_target_schema = table_info.get("target_schema")

                # Ensure schema
                if columns:
                    try:
                        dest.ensure_schema(safe_name, table, columns, target_schema=per_table_target_schema)
                    except Exception as e:
                        logger.error(f"Schema creation failed for {table}: {e}")
                        results.append({
                            "table": table, "rows": 0, "status": "failed",
                            "error": f"Schema creation failed: {e}",
                        })
                        continue

                # --- Schema Drift Detection (Phase 2) ---
                try:
                    drift_cols = self._detect_schema_drift(dest, safe_name, table, columns, pipeline_id=pipeline_id, target_schema=per_table_target_schema)
                except Exception as e:
                    logger.warning(f"Schema drift detection skipped (unsupported dest type): {e}")
                    drift_cols = []
                if drift_cols:
                    if settings.auto_alter_schema:
                        try:
                            self._auto_alter_table(dest, safe_name, table, columns, drift_cols, target_schema=per_table_target_schema)
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

                # --- Transform (optional per table) ---
                transform_config = table_info.get("transform_config")
                if transform_config:
                    try:
                        from arus.modules.transform.engine import apply_transforms
                        all_rows = apply_transforms(
                            all_rows,
                            transform_config,
                            db_session=self.db_session,
                            pipeline_id=pipeline_id,
                        )
                    except Exception as e:
                        logger.error(f"Transform failed for {table}: {e}")
                        results.append({
                            "table": table, "rows": 0, "status": "failed",
                            "error": f"Transform failed: {e}",
                        })
                        continue

                # Check load_mode: direct or raw
                load_mode = table_info.get("load_mode", "direct") or "direct"

                # --- Load raw (only if load_mode=raw) ---
                loaded_raw = 0
                if load_mode == "raw":
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
                        if self.notif_svc:
                            self.notif_svc.notify_pipeline_event(
                                pipeline_id=pipeline_id,
                                event_type="dead_letter",
                                pipeline_name=pipeline_name,
                                run_id=run_id,
                                error=err_msg,
                                extra={"table": table, "row_count": len(all_rows)},
                            )
                            self.notif_svc.notify_pipeline_event(
                                pipeline_id=pipeline_id,
                                event_type="failure",
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
                    loaded_norm = dest.load_normalized(safe_name, table, all_rows, target_schema=per_table_target_schema)
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
                    # Notify for normalized load failure
                    if self.notif_svc:
                        self.notif_svc.notify_pipeline_event(
                            pipeline_id=pipeline_id,
                            event_type="dead_letter",
                            pipeline_name=pipeline_name,
                            run_id=run_id,
                            error=f"Normalized load failed: {e}",
                            extra={"table": table, "row_count": len(all_rows)},
                        )

                # --- Update watermark ---
                if sync_mode == "incremental" and all_rows:
                    wm_col = table_info.get("watermark_column")
                    if wm_col and wm_col in all_rows[-1]:
                        last_val = all_rows[-1][wm_col]
                        dest.update_watermark(pipeline_id, table, last_val)
                        # Also persist watermark in central DB so pipeline
                        # service can read it back on next run regardless of
                        # destination type (e.g. ClickHouse, MySQL).
                        if self.db_session:
                            try:
                                from arus.modules.pipeline.repository import PipelineRepository
                                wm_repo = PipelineRepository(self.db_session)
                                wm_repo.set_watermark(
                                    pipeline_id, table, wm_col, str(last_val)
                                )
                            except Exception as wm_err:
                                logger.warning(
                                    f"Central watermark persist failed: {wm_err}"
                                )

                # --- Soft-delete reconciliation ---
                if sync_mode == "incremental" and watermark:
                    del_col = None
                    for col in columns:
                        if col["name"].lower() == "deleted_at":
                            del_col = col["name"]
                            break
                    if del_col:
                        wm_col_name = table_info.get("watermark_column", "updated_at")
                        try:
                            deleted_rows = src.extract_soft_deletes(
                                table, watermark, del_col, wm_col_name,
                            )
                            if deleted_rows:
                                pk_cols = [c["name"] for c in columns if c.get("pk")]
                                if pk_cols:
                                    del_count = dest.delete_rows(
                                        safe_name, table, deleted_rows, pk_cols,
                                        target_schema=per_table_target_schema,
                                    )
                                    logger.info(
                                        f"Soft-delete sync: removed {del_count} rows from {table}"
                                    )
                        except NotImplementedError:
                            pass  # Source/destination doesn't support soft-delete
                        except Exception as e:
                            logger.warning(f"Soft-delete sync failed for {table}: {e}")

                # --- Data Quality Checks (Phase 2) ---
                quality_breach = None
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
                    # Check for quality breaches
                    if quality_results.get("row_count", {}).get("breach"):
                        quality_breach = f"Row count discrepancy: {quality_results['row_count'].get('details', 'threshold breached')}"
                    elif quality_results.get("null_check", {}).get("breach"):
                        quality_breach = f"Null check failed: {quality_results['null_check'].get('details', 'required columns have nulls')}"

                if quality_breach and self.notif_svc:
                    self.notif_svc.notify_pipeline_event(
                        pipeline_id=pipeline_id,
                        event_type="quality_breach",
                        pipeline_name=pipeline_name,
                        run_id=run_id,
                        error=quality_breach,
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
            if self.notif_svc:
                self.notif_svc.notify_pipeline_event(
                    pipeline_id=pipeline_id,
                    event_type="failure",
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
                    "rows_synced": total_rows,
                    "error_message": error,
                })
            except Exception as e:
                logger.warning(f"Could not update run_log: {e}")

        # Compute total rows for rows_synced
        total_rows = sum(r.get("rows", 0) for r in results)

        # Send success notification if pipeline didn't error
        if not error and self.notif_svc:
            self.notif_svc.notify_pipeline_event(
                pipeline_id=pipeline_id,
                event_type="success",
                pipeline_name=pipeline_name,
                run_id=run_id,
                extra={
                    "rows_synced": total_rows,
                    "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
                },
            )

        return {
            "run_id": run_id,
            "status": "failed" if error else "success",
            "error": error,
            "results": results,
            "started_at": started_at.isoformat() if started_at else None,
            "finished_at": finished_at.isoformat() if finished_at else None,
            "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
            "rows_synced": total_rows,
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

    def _detect_schema_drift(self, dest, source_name: str, table: str, source_columns: list[dict], pipeline_id: str = "N/A", target_schema: str = None) -> list[str]:
        """
        Compare source columns against warehouse table columns.
        Returns list of new column names not present in warehouse.
        """
        try:
            safe_source = source_name.lower().replace("-", "_").replace(" ", "_")
            target_schema = target_schema or dest.config.get("target_schema", "public")
            schema_table = f"{target_schema}.{table}"

            with dest.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    """,
                    (target_schema, table),
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
                        pipeline_id=pipeline_id,
                        pipeline_name=source_name,
                        table_name=table,
                        new_columns=list(new_cols),
                    )
                if self.notif_svc:
                    self.notif_svc.notify_pipeline_event(
                        pipeline_id=pipeline_id,
                        event_type="schema_drift",
                        pipeline_name=source_name,
                        extra={"table": table, "new_columns": list(new_cols)},
                    )

            return list(new_cols)
        except Exception as e:
            logger.warning(f"Schema drift detection failed for {table}: {e}")
            return []

    def _auto_alter_table(self, dest, source_name: str, table: str, source_columns: list[dict], new_cols: list[str], target_schema: str = None):
        """Automatically add new columns to the warehouse table."""
        target_schema = target_schema or dest.config.get("target_schema", "public")
        from arus.shared.types import map_type

        with dest.conn.cursor() as cur:
            for col in source_columns:
                if col["name"].lower() in new_cols:
                    pg_type = map_type(col["type"])
                    cur.execute(
                        f'ALTER TABLE "{target_schema}"."{table}" '
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
