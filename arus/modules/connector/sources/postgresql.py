from typing import Iterator, Any
import psycopg2
import psycopg2.extras

from arus.modules.connector.base_source import BaseSource, TableSchema, SyncMode


class PostgreSQLSource(BaseSource):
    type = "postgresql"

    def __init__(self):
        self.conn = None
        self.config = {}
        self.db_name = ""

    def connect(self, config: dict) -> bool:
        self.config = config
        self.db_name = config["database"]
        self.conn = psycopg2.connect(
            host=config["host"],
            port=config.get("port", 5432),
            user=config["username"],
            password=config["password"],
            dbname=config["database"],
        )
        return True

    def test_connection(self) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception:
            return False

    def discover_tables(self) -> list[TableSchema]:
        tables = []
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename, schemaname
                FROM pg_catalog.pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schemaname, tablename
                """
            )
            for row in cur.fetchall():
                columns = self.get_table_columns(row[0], row[1])
                tables.append(
                    TableSchema(
                        name=row[0],
                        schema_name=row[1] or "public",
                        columns=columns,
                    )
                )
        return tables

    def get_table_columns(self, table: str, schema: str = "public") -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable, 
                       COALESCE(character_maximum_length, 0) as char_len
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema, table),
            )
            return [
                {
                    "name": r[0],
                    "type": r[1] + (f"({r[3]})" if r[3] > 0 and r[1] in ("character varying", "character") else ""),
                    "nullable": r[2] == "YES",
                    "pk": False,
                }
                for r in cur.fetchall()
            ]

    def detect_sync_mode(self, table: str, columns: list[dict]) -> SyncMode:
        ts_cols = {"updated_at", "modified_at", "last_modified", "updated"}
        for col in columns:
            if col["name"].lower() in ts_cols:
                return SyncMode(mode="incremental", watermark_column=col["name"])
        for col in columns:
            if col["name"].lower() == "created_at":
                return SyncMode(mode="incremental", watermark_column=col["name"])
        return SyncMode(mode="full_refresh", watermark_column=None)

    def extract(self, table: str, watermark: Any = None, batch_size: int = 10000) -> Iterator[list[dict]]:
        schema = "public"
        if "." in table:
            parts = table.split(".")
            schema = parts[0]
            table = parts[1]

        if watermark:
            columns = self.get_table_columns(table, schema)
            wm_col = None
            ts_candidates = {"updated_at", "modified_at", "last_modified", "updated", "created_at"}
            for col in columns:
                if col["name"].lower() in ts_candidates:
                    wm_col = col["name"]
                    break

            if wm_col:
                sql = f'SELECT * FROM "{schema}"."{table}" WHERE {wm_col} > %s ORDER BY {wm_col} LIMIT %s'
                params = [watermark, batch_size]
            else:
                sql = f'SELECT * FROM "{schema}"."{table}" LIMIT %s'
                params = [batch_size]
        else:
            sql = f'SELECT * FROM "{schema}"."{table}" LIMIT %s'
            params = [batch_size]

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            batch = [dict(r) for r in cur.fetchall()]
            if batch:
                yield batch
