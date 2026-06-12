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

    def discover_schemas(self) -> list[str]:
        """List available schemas in the database."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT nspname FROM pg_catalog.pg_namespace
                WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                AND nspname NOT LIKE 'pg_%'
                ORDER BY nspname
                """
            )
            return [row[0] for row in cur.fetchall()]

    def discover_tables(self) -> list[TableSchema]:
        tables = []
        schema_filter = self.config.get("schema_include", [])
        with self.conn.cursor() as cur:
            query = """
                SELECT tablename, schemaname
                FROM pg_catalog.pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            """
            params = []
            if schema_filter:
                query += " AND schemaname = ANY(%s)"
                params.append(schema_filter)
            query += " ORDER BY schemaname, tablename"
            cur.execute(query, params)
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
        wm_col = None
        del_col = None

        for col in columns:
            if col["name"].lower() in ts_cols:
                wm_col = col["name"]
                break
        if not wm_col:
            for col in columns:
                if col["name"].lower() == "created_at":
                    wm_col = col["name"]
                    break

        for col in columns:
            if col["name"].lower() == "deleted_at":
                del_col = col["name"]
                break

        if wm_col:
            return SyncMode(mode="incremental", watermark_column=wm_col, deleted_at_column=del_col)
        return SyncMode(mode="full_refresh", watermark_column=None, deleted_at_column=None)

    def extract_soft_deletes(self, table: str, watermark: Any,
                              deleted_at_column: str, watermark_column: str,
                              batch_size: int = 10000) -> list[dict]:
        if not watermark:
            return []
        schema = "public"
        tbl = table
        if "." in table:
            parts = table.split(".")
            schema = parts[0]
            tbl = parts[1]
        sql = f'SELECT * FROM "{schema}"."{tbl}" WHERE "{deleted_at_column}" IS NOT NULL AND "{deleted_at_column}" > %s AND ("{watermark_column}" IS NULL OR "{watermark_column}" <= %s) LIMIT %s'
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, [watermark, watermark, batch_size])
            return [dict(r) for r in cur.fetchall()]

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
