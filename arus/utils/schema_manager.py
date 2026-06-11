"""
Schema Manager
~~~~~~~~~~~~~~
Auto-creates and tracks warehouse table schemas.

Landing zone (raw): `staging.<source>_<table>_raw` — JSONB + metadata
Normalized zone: `analytics.<table>` — typed columns

Also performs schema drift detection: compares source columns vs warehouse.
"""

from typing import Any
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Map Python/MySQL types to PostgreSQL
TYPE_MAP = {
    "int": "BIGINT",
    "integer": "BIGINT",
    "bigint": "BIGINT",
    "smallint": "INTEGER",
    "tinyint": "SMALLINT",
    "varchar": "TEXT",
    "char": "TEXT",
    "text": "TEXT",
    "longtext": "TEXT",
    "mediumtext": "TEXT",
    "datetime": "TIMESTAMPTZ",
    "timestamp": "TIMESTAMPTZ",
    "date": "DATE",
    "decimal": "NUMERIC(38, 10)",
    "numeric": "NUMERIC(38, 10)",
    "float": "DOUBLE PRECISION",
    "double": "DOUBLE PRECISION",
    "boolean": "BOOLEAN",
    "bit": "BOOLEAN",
    "blob": "BYTEA",
    "json": "JSONB",
}


class SchemaManager:
    """Manages warehouse schema: create landing + normalized tables."""

    def __init__(self, conn_string: str):
        self._conn_string = conn_string

    def _get_raw_table_name(self, source: str, table: str) -> str:
        """Raw table: staging.<source>_<table>_raw"""
        safe = f"{source}_{table}".replace("-", "_").replace(".", "_").lower()
        return f"staging.{safe}_raw"

    def ensure_raw_table(self, source: str, table: str):
        """Creates landing zone raw table if not exists."""
        raw_full = self._get_raw_table_name(source, table)
        raw_short = raw_full.split(".")[1]
        conn = psycopg2.connect(self._conn_string)
        try:
            with conn.cursor() as cur:
                # Create staging schema if needed
                cur.execute("CREATE SCHEMA IF NOT EXISTS staging;")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {raw_full} (
                        id              BIGSERIAL PRIMARY KEY,
                        _source         VARCHAR(64) NOT NULL,
                        _table          VARCHAR(128) NOT NULL,
                        _loaded_at      TIMESTAMPTZ DEFAULT NOW(),
                        _watermark      TEXT,
                        _checksum       VARCHAR(64),
                        data            JSONB NOT NULL
                    );
                    """
                )
                # Index on loaded_at for efficient queries
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{raw_short}_loaded
                    ON {raw_full} (_loaded_at DESC);
                    """
                )
            conn.commit()
        finally:
            conn.close()
        return raw_full

    def ensure_normalized_table(
        self, table: str, columns: list[dict]
    ):
        """Creates normalized table in `analytics` schema if not exists.

        `columns`: [{"name": "id", "type": "int"}, {"name": "email", "type": "varchar"}]
        """
        schema_table = f"analytics.{table}"
        conn = psycopg2.connect(self._conn_string)
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE SCHEMA IF NOT EXISTS analytics;")
                # Check if table exists
                cur.execute(
                    "SELECT to_regclass(%s) IS NOT NULL AS exists",
                    (schema_table,),
                )
                exists = cur.fetchone()[0]

                if not exists:
                    col_defs = ', '.join(
                        f'"{c["name"]}" {TYPE_MAP.get(c["type"].lower(), "TEXT")}'
                        for c in columns
                    )
                    # Add metadata columns
                    full_cols = (
                        col_defs + ', '
                        '_source VARCHAR(64), '
                        '_watermark TEXT, '
                        '_loaded_at TIMESTAMPTZ DEFAULT NOW()'
                    )
                    cur.execute(
                        f"CREATE TABLE {schema_table} ({full_cols});"
                    )
                else:
                    # Schema drift detection (basic)
                    self._detect_drift(conn, schema_table, columns)
            conn.commit()
        finally:
            conn.close()
        return schema_table

    def _detect_drift(
        self,
        conn: Any,
        schema_table: str,
        source_cols: list[dict],
    ):
        """Logs columns present in source but missing in warehouse."""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s",
                (schema_table.split(".")[0], schema_table.split(".")[1]),
            )
            existing = {r["column_name"]: r["data_type"] for r in cur.fetchall()}

            source_names = {c["name"].lower() for c in source_cols}
            # Skip metadata columns
            existing_names = {k for k in existing if not k.startswith("_")}

            missing = source_names - existing_names
            if missing:
                print(
                    f"[SCHEMA DRIFT] Table {schema_table} missing columns: {missing}"
                )
                for col in source_cols:
                    if col["name"] not in existing:
                        pg_type = TYPE_MAP.get(col["type"].lower(), "TEXT")
                        with conn.cursor() as cur2:
                            cur2.execute(
                                f'ALTER TABLE {schema_table} ADD COLUMN "{col["name"]}" {pg_type};'
                            )
                        print(f"  → Added column: {col['name']} ({pg_type})")

    def list_pipelines(self) -> list[dict]:
        """Shows pipeline status with row counts."""
        conn = psycopg2.connect(self._conn_string)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        s.source_name,
                        s.table_name,
                        s.watermark_col,
                        s.watermark_value,
                        s.row_count,
                        s.updated_at
                    FROM public.arus_state s
                    ORDER BY s.updated_at DESC
                    """
                )
                return cur.fetchall()
        finally:
            conn.close()
