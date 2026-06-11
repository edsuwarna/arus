"""
Data Quality Checks
~~~~~~~~~~~~~~~~~~
After load, run row count validation and null checks on required columns.
Store quality check results in arus_config.data_quality_log table.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text as sa_text

from arus.shared.db.session import Base, engine as db_engine
from arus.shared.config import settings

logger = logging.getLogger(__name__)


class DataQualityLog(Base):
    """Model for data quality check results."""
    __tablename__ = "data_quality_log"
    __table_args__ = {"schema": "arus_config"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_id = Column(UUID, nullable=False)
    run_id = Column(UUID, nullable=False)
    table_name = Column(String(255), nullable=False)
    check_type = Column(String(50), nullable=False)  # "row_count", "null_check"
    status = Column(String(20), nullable=False)  # "passed", "failed", "warning"
    rows_extracted = Column(Integer, nullable=True)
    rows_loaded = Column(Integer, nullable=True)
    discrepancy_pct = Column(Float, nullable=True)
    null_columns = Column(Text, nullable=True)  # comma-separated column names
    required_columns = Column(Text, nullable=True)
    message = Column(Text, nullable=True)
    passed = Column(Boolean, default=True)
    checked_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class DataQualityChecker:
    """Runs data quality checks after pipeline load."""

    def __init__(self, db_session=None):
        self.db = db_session

    @staticmethod
    def ensure_table():
        """Create the data_quality_log table if it doesn't exist."""
        try:
            with db_engine.connect() as conn:
                conn.execute(sa_text("CREATE SCHEMA IF NOT EXISTS arus_config;"))
                conn.execute(sa_text("""
                    CREATE TABLE IF NOT EXISTS arus_config.data_quality_log (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        pipeline_id UUID NOT NULL,
                        run_id UUID NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        check_type VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        rows_extracted INTEGER,
                        rows_loaded INTEGER,
                        discrepancy_pct FLOAT,
                        null_columns TEXT,
                        required_columns TEXT,
                        message TEXT,
                        passed BOOLEAN DEFAULT TRUE,
                        checked_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """))
                conn.execute(sa_text("""
                    CREATE INDEX IF NOT EXISTS idx_data_quality_run_id
                    ON arus_config.data_quality_log (run_id);
                """))
                conn.execute(sa_text("""
                    CREATE INDEX IF NOT EXISTS idx_data_quality_pipeline_id
                    ON arus_config.data_quality_log (pipeline_id);
                """))
                conn.commit()
            logger.info("Ensured arus_config.data_quality_log table exists")
        except Exception as e:
            logger.error(f"Failed to create data_quality_log table: {e}")

    def check_row_count(
        self,
        pipeline_id: str,
        run_id: str,
        table_name: str,
        rows_extracted: int,
        rows_loaded: int,
    ) -> dict:
        """Check if row count discrepancy exceeds threshold."""
        threshold = settings.quality_check_threshold
        discrepancy = 0

        if rows_extracted > 0:
            discrepancy = abs(rows_extracted - rows_loaded) / rows_extracted * 100

        passed = discrepancy <= threshold
        status = "passed" if passed else "failed"
        message = (
            f"Row count check: extracted={rows_extracted}, loaded={rows_loaded}, "
            f"discrepancy={discrepancy:.2f}% (threshold={threshold}%)"
        )

        if not passed:
            logger.warning(
                f"[DATA QUALITY] {message} — pipeline={pipeline_id}, table={table_name}"
            )

        result = {
            "pipeline_id": pipeline_id,
            "run_id": run_id,
            "table_name": table_name,
            "check_type": "row_count",
            "status": status,
            "rows_extracted": rows_extracted,
            "rows_loaded": rows_loaded,
            "discrepancy_pct": round(discrepancy, 2),
            "null_columns": None,
            "required_columns": None,
            "message": message,
            "passed": passed,
        }

        self._log_result(result)
        return result

    def check_nulls(
        self,
        pipeline_id: str,
        run_id: str,
        table_name: str,
        rows: list[dict],
        required_columns: list[str] | None = None,
    ) -> dict:
        """Check for null values in required columns."""
        if not rows:
            return {
                "pipeline_id": pipeline_id,
                "run_id": run_id,
                "table_name": table_name,
                "check_type": "null_check",
                "status": "passed",
                "rows_extracted": 0,
                "rows_loaded": 0,
                "discrepancy_pct": None,
                "null_columns": None,
                "required_columns": ",".join(required_columns) if required_columns else None,
                "message": "No rows to check",
                "passed": True,
            }

        if not required_columns:
            required_columns = []

        null_cols = []
        for col in required_columns:
            null_count = sum(1 for row in rows if row.get(col) is None)
            if null_count > 0:
                null_cols.append(f"{col}({null_count})")

        passed = len(null_cols) == 0
        status = "passed" if passed else "warning"
        message = (
            f"Null check on required columns: {'none' if passed else ', '.join(null_cols)}"
        )

        if not passed:
            logger.warning(
                f"[DATA QUALITY] {message} — pipeline={pipeline_id}, table={table_name}"
            )

        result = {
            "pipeline_id": pipeline_id,
            "run_id": run_id,
            "table_name": table_name,
            "check_type": "null_check",
            "status": status,
            "rows_extracted": len(rows),
            "rows_loaded": len(rows),
            "discrepancy_pct": None,
            "null_columns": ",".join(null_cols) if null_cols else None,
            "required_columns": ",".join(required_columns) if required_columns else None,
            "message": message,
            "passed": passed,
        }

        self._log_result(result)
        return result

    def _log_result(self, result: dict):
        """Store quality check result in database."""
        try:
            from arus.shared.db.session import SessionLocal
            db = self.db or SessionLocal()
            try:
                entry = DataQualityLog(
                    pipeline_id=result["pipeline_id"],
                    run_id=result["run_id"],
                    table_name=result["table_name"],
                    check_type=result["check_type"],
                    status=result["status"],
                    rows_extracted=result.get("rows_extracted"),
                    rows_loaded=result.get("rows_loaded"),
                    discrepancy_pct=result.get("discrepancy_pct"),
                    null_columns=result.get("null_columns"),
                    required_columns=result.get("required_columns"),
                    message=result.get("message"),
                    passed=result.get("passed", True),
                )
                db.add(entry)
                db.commit()
            finally:
                if not self.db:
                    db.close()
        except Exception as e:
            logger.error(f"Failed to log data quality result: {e}")
