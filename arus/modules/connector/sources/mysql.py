from typing import Iterator, Any
import pymysql
import pymysql.cursors

from arus.modules.connector.base_source import BaseSource, TableSchema, SyncMode


class MySQLSource(BaseSource):
    type = "mysql"

    def __init__(self):
        self.conn = None
        self.config = {}
        self.db_name = ""

    def connect(self, config: dict) -> bool:
        self.config = config
        self.db_name = config["database"]
        self.conn = pymysql.connect(
            host=config["host"],
            port=config.get("port", 3306),
            user=config["username"],
            password=config["password"],
            database=config["database"],
            ssl=config.get("ssl", False),
            cursorclass=pymysql.cursors.DictCursor,
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
                SELECT TABLE_NAME, TABLE_ROWS
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
                """,
                (self.db_name,),
            )
            for row in cur.fetchall():
                columns = self.get_table_columns(row["TABLE_NAME"])
                tables.append(
                    TableSchema(
                        name=row["TABLE_NAME"],
                        row_count_estimate=row["TABLE_ROWS"] or 0,
                        columns=columns,
                    )
                )
        return tables

    def get_table_columns(self, table: str) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_KEY
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                (self.db_name, table),
            )
            return [
                {
                    "name": r["COLUMN_NAME"],
                    "type": r["COLUMN_TYPE"],
                    "nullable": r["IS_NULLABLE"] == "YES",
                    "pk": r["COLUMN_KEY"] == "PRI",
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
        sql = f"SELECT * FROM {table} WHERE {deleted_at_column} IS NOT NULL AND {deleted_at_column} > %s AND ({watermark_column} IS NULL OR {watermark_column} <= %s) LIMIT %s"
        with self.conn.cursor() as cur:
            cur.execute(sql, [watermark, watermark, batch_size])
            return list(cur.fetchall())

    def extract(self, table: str, watermark: Any = None, batch_size: int = 10000) -> Iterator[list[dict]]:
        if watermark:
            columns = self.get_table_columns(table)
            # Find the watermark column
            wm_col = None
            ts_candidates = {"updated_at", "modified_at", "last_modified", "updated", "created_at"}
            for col in columns:
                if col["name"].lower() in ts_candidates:
                    wm_col = col["name"]
                    break

            if wm_col:
                sql = f"SELECT * FROM {table} WHERE {wm_col} > %s ORDER BY {wm_col} LIMIT %s"
                params = [watermark, batch_size]
            else:
                sql = f"SELECT * FROM {table} LIMIT %s"
                params = [batch_size]
        else:
            sql = f"SELECT * FROM {table} LIMIT %s"
            params = [batch_size]

        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            batch = cur.fetchall()
            if batch:
                yield batch
