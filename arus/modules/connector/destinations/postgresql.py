from typing import Any
import json

import psycopg2
import psycopg2.extras

from arus.modules.connector.base_destination import BaseDestination
from arus.shared.types import map_type


class PostgreSQLDestination(BaseDestination):
    type = "postgresql"

    def __init__(self):
        self.conn = None
        self.config = {}

    def connect(self, config: dict) -> bool:
        self.config = config
        self.conn = psycopg2.connect(
            host=config["host"],
            port=config.get("port", 5432),
            user=config["username"],
            password=config["password"],
            dbname=config["database"],
        )
        self.conn.autocommit = False
        return True

    def test_connection(self) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _safe_name(self, name: str) -> str:
        """Make a safe identifier for table/schema names."""
        return name.lower().replace("-", "_").replace(".", "_").replace(" ", "_")

    def ensure_schema(self, source_name: str, table: str, columns: list[dict], target_schema: str = None) -> None:
        safe_source = self._safe_name(source_name)
        raw_schema = self.config.get("raw_schema", "staging")
        target_schema = target_schema or self.config.get("target_schema", "public")
        raw_table = f"{safe_source}_{table}_raw"

        with self.conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{raw_schema}"')
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{target_schema}"')

            # Create raw (JSONB) table
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{raw_schema}"."{raw_table}" (
                    _arus_id BIGSERIAL PRIMARY KEY,
                    _arus_run_id UUID NOT NULL,
                    _arus_extracted TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    _data JSONB NOT NULL
                )
                """
            )

            # Create analytics table
            col_defs = []
            for col in columns:
                pg_type = map_type(col["type"])
                nullable = ""
                if not col.get("nullable", True):
                    nullable = " NOT NULL"
                col_defs.append(f'"{col["name"]}" {pg_type}{nullable}')

            col_defs.append('"_arus_run_id" UUID NOT NULL')
            col_defs.append('"_arus_synced_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()')

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{target_schema}"."{table}" (
                    {', '.join(col_defs)}
                )
                """
            )

        self.conn.commit()

    def load_raw(self, source_name: str, table: str, rows: list[dict], run_id: str) -> int:
        safe_source = self._safe_name(source_name)
        raw_schema = self.config.get("raw_schema", "staging")
        raw_table = f"{safe_source}_{table}_raw"

        with self.conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    f'INSERT INTO "{raw_schema}"."{raw_table}" (_arus_run_id, _data) VALUES (%s, %s)',
                    (run_id, json.dumps(row, default=str)),
                )
        self.conn.commit()
        return len(rows)

    def load_normalized(self, source_name: str, table: str, rows: list[dict], target_schema: str = None) -> int:
        target_schema = target_schema or self.config.get("target_schema", "public")

        if not rows:
            return 0

        columns = list(rows[0].keys())
        col_names = ', '.join(f'"{c}"' for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        values = [[row.get(c, None) for c in columns] for row in rows]

        with self.conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                f'INSERT INTO "{target_schema}"."{table}" ({col_names}) VALUES %s ON CONFLICT DO NOTHING',
                values,
            )
        self.conn.commit()
        return len(rows)

    def update_watermark(self, pipeline_id: str, table: str, value: Any) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO arus_state.watermarks (pipeline_id, source_table, watermark_value, last_synced_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (pipeline_id, source_table)
                DO UPDATE SET watermark_value = EXCLUDED.watermark_value, last_synced_at = NOW()
                """,
                (pipeline_id, table, str(value)),
            )
        self.conn.commit()
