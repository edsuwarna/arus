"""
Dead Letter Queue Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~
Saves rows that fail to load after all retries to staging._dead_letters.

Columns: id UUID, source_name, table_name, run_id, row_data JSONB,
         error_text, failed_at TIMESTAMP
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text as sa_text

from arus.shared.db.session import Base, engine as db_engine

logger = logging.getLogger(__name__)


class DeadLetter(Base):
    """Model for the dead letter queue table."""
    __tablename__ = "_dead_letters"
    __table_args__ = {"schema": "staging"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_name = Column(String(255), nullable=False)
    table_name = Column(String(255), nullable=False)
    run_id = Column(UUID, nullable=False)
    row_data = Column(JSONB, nullable=False)
    error_text = Column(Text, nullable=True)
    failed_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class DeadLetterManager:
    """Manages writing failed rows to the dead letter queue."""

    def __init__(self, db_session=None):
        self.db = db_session

    @staticmethod
    def ensure_table():
        """Create the _dead_letters table if it doesn't exist."""
        try:
            with db_engine.connect() as conn:
                conn.execute(sa_text("CREATE SCHEMA IF NOT EXISTS staging;"))
                conn.execute(sa_text("""
                    CREATE TABLE IF NOT EXISTS staging._dead_letters (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        source_name VARCHAR(255) NOT NULL,
                        table_name VARCHAR(255) NOT NULL,
                        run_id UUID NOT NULL,
                        row_data JSONB NOT NULL,
                        error_text TEXT,
                        failed_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """))
                conn.execute(sa_text("""
                    CREATE INDEX IF NOT EXISTS idx_dead_letters_run_id
                    ON staging._dead_letters (run_id);
                """))
                conn.commit()
            logger.info("Ensured staging._dead_letters table exists")
        except Exception as e:
            logger.error(f"Failed to create _dead_letters table: {e}")

    def write_failed_rows(
        self,
        source_name: str,
        table_name: str,
        run_id: str,
        rows: list[dict],
        error_text: str,
    ) -> int:
        """Write failed rows to dead letter queue. Returns count written."""
        if not rows:
            return 0

        count = 0
        try:
            from arus.shared.db.session import SessionLocal
            db = self.db or SessionLocal()
            try:
                for row in rows:
                    dl = DeadLetter(
                        source_name=source_name,
                        table_name=table_name,
                        run_id=run_id,
                        row_data=row,
                        error_text=error_text,
                    )
                    db.add(dl)
                    count += 1
                db.commit()
            finally:
                if not self.db:
                    db.close()
        except Exception as e:
            logger.error(f"Failed to write to dead letter queue: {e}")

        # Also attempt direct SQL insert as fallback
        if count == 0:
            try:
                with db_engine.connect() as conn:
                    for row in rows:
                        conn.execute(
                            sa_text("""
                                INSERT INTO staging._dead_letters
                                    (source_name, table_name, run_id, row_data, error_text)
                                VALUES (:source, :table, :run, :data::jsonb, :error)
                            """),
                            {
                                "source": source_name,
                                "table": table_name,
                                "run": run_id,
                                "data": str(row),
                                "error": error_text,
                            },
                        )
                    conn.commit()
                    count = len(rows)
            except Exception as e2:
                logger.error(f"Dead letter SQL fallback also failed: {e2}")

        logger.warning(
            f"Wrote {count}/{len(rows)} failed rows to dead letter queue "
            f"(source={source_name}, table={table_name}, run={run_id})"
        )
        return count
