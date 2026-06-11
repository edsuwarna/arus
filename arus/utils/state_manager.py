"""
Watermark / State Manager
~~~~~~~~~~~~~~~~~~~~~~~~~
Tracks incremental extraction state per source table.
State stored in warehouse PostgreSQL: public.arus_state
"""

import datetime
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS public.arus_state (
    id              SERIAL PRIMARY KEY,
    source_name     VARCHAR(128) NOT NULL,
    table_name      VARCHAR(128) NOT NULL,
    watermark_col   VARCHAR(64),
    watermark_value TEXT,
    row_count       INTEGER DEFAULT 0,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_name, table_name)
);
"""


class StateManager:
    """Manages watermark/bookmark state for CDC pipelines."""

    def __init__(self, conn_string: str):
        self._conn_string = conn_string
        self._ensure_table()

    def _ensure_table(self) -> None:
        conn = psycopg2.connect(self._conn_string)
        try:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
            conn.commit()
        finally:
            conn.close()

    def get_watermark(
        self, source_name: str, table_name: str
    ) -> Optional[str]:
        """Returns current watermark value or None if first run."""
        conn = psycopg2.connect(self._conn_string)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT watermark_value FROM public.arus_state "
                    "WHERE source_name = %s AND table_name = %s",
                    (source_name, table_name),
                )
                row = cur.fetchone()
                return row["watermark_value"] if row else None
        finally:
            conn.close()

    def set_watermark(
        self,
        source_name: str,
        table_name: str,
        watermark_col: str,
        watermark_value: str,
        row_count: int = 0,
    ) -> None:
        """Update or insert watermark."""
        conn = psycopg2.connect(self._conn_string)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.arus_state
                        (source_name, table_name, watermark_col, watermark_value, row_count, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (source_name, table_name)
                    DO UPDATE SET
                        watermark_col  = EXCLUDED.watermark_col,
                        watermark_value = EXCLUDED.watermark_value,
                        row_count       = EXCLUDED.row_count,
                        updated_at      = NOW()
                    """,
                    (source_name, table_name, watermark_col, str(watermark_value), row_count),
                )
            conn.commit()
        finally:
            conn.close()

    def reset_watermark(self, source_name: str, table_name: str) -> None:
        """Reset watermark for full refresh."""
        conn = psycopg2.connect(self._conn_string)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.arus_state "
                    "WHERE source_name = %s AND table_name = %s",
                    (source_name, table_name),
                )
            conn.commit()
        finally:
            conn.close()

    def list_state(self) -> list[dict]:
        """List all tracked pipeline states."""
        conn = psycopg2.connect(self._conn_string)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM public.arus_state ORDER BY source_name, table_name"
                )
                return cur.fetchall()
        finally:
            conn.close()
