"""MySQL Destination Connector — loads data into MySQL/MariaDB databases."""

from typing import Any
import json

import pymysql

from arus.modules.connector.base_destination import BaseDestination

# Column-type mapping: source -> MySQL
MYSQL_TYPE_MAP = {
    "int": "INT",
    "integer": "INT",
    "smallint": "SMALLINT",
    "bigint": "BIGINT",
    "tinyint": "TINYINT",
    "serial": "BIGINT",
    "bigserial": "BIGINT",
    "decimal": "DECIMAL",
    "numeric": "DECIMAL",
    "float": "FLOAT",
    "double": "DOUBLE",
    "real": "DOUBLE",
    "varchar": "VARCHAR(255)",
    "char": "CHAR",
    "text": "TEXT",
    "longtext": "LONGTEXT",
    "mediumtext": "MEDIUMTEXT",
    "boolean": "TINYINT(1)",
    "bool": "TINYINT(1)",
    "date": "DATE",
    "datetime": "DATETIME(3)",
    "timestamp": "DATETIME(3)",
    "json": "JSON",
    "jsonb": "JSON",
    "blob": "BLOB",
    "binary": "BINARY",
    "uuid": "VARCHAR(36)",
    "enum": "VARCHAR(255)",
    "ObjectId": "VARCHAR(24)",
    "null": "VARCHAR(255)",
}


def map_mysql_type(source_type: str) -> str:
    """Map a source DB column type to a MySQL type."""
    base = source_type.lower().split("(")[0].split()[0]
    return MYSQL_TYPE_MAP.get(base, "TEXT")


class MySQLDestination(BaseDestination):
    type = "mysql"

    def __init__(self):
        self.conn = None
        self.config = {}

    def connect(self, config: dict) -> bool:
        self.config = config
        self.conn = pymysql.connect(
            host=config.get("host", "localhost"),
            port=config.get("port", 3306),
            user=config.get("username", "root"),
            password=config.get("password", ""),
            database=config.get("database", "arus_warehouse"),
            charset="utf8mb4",
            autocommit=False,
        )
        return True

    def test_connection(self) -> bool:
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _safe_name(self, name: str) -> str:
        """Make a safe identifier for database/table names."""
        return name.lower().replace("-", "_").replace(".", "_").replace(" ", "_")

    def _quote(self, name: str) -> str:
        """MySQL-safe backtick quoting."""
        return f"`{name.replace('`', '``')}`"

    def ensure_schema(self, source_name: str, table: str, columns: list[dict]) -> None:
        safe_source = self._safe_name(source_name)
        raw_schema = self.config.get("raw_schema", "staging")
        target_schema = self.config.get("target_schema", "analytics")
        raw_table = f"{safe_source}_{table}_raw"

        with self.conn.cursor() as cur:
            # Create databases (schemas in MySQL)
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS {self._quote(raw_schema)}"
                f" CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS {self._quote(target_schema)}"
                f" CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )

            # Create raw (JSON) table
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._quote(raw_schema)}.{self._quote(raw_table)} (
                    _arus_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    _arus_run_id VARCHAR(36) NOT NULL,
                    _arus_extracted DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
                    _data JSON NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            # Create analytics table
            col_defs = []
            for col in columns:
                mysql_type = map_mysql_type(col["type"])
                nullable = ""
                if not col.get("nullable", True):
                    nullable = " NOT NULL"
                col_defs.append(f"{self._quote(col['name'])} {mysql_type}{nullable}")

            col_defs.append("`_arus_run_id` VARCHAR(36) NOT NULL")
            col_defs.append(
                "`_arus_synced_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3)"
            )

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._quote(target_schema)}.{self._quote(table)} (
                    {', '.join(col_defs)}
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

        self.conn.commit()

    def load_raw(
        self, source_name: str, table: str, rows: list[dict], run_id: str
    ) -> int:
        safe_source = self._safe_name(source_name)
        raw_schema = self.config.get("raw_schema", "staging")
        raw_table = f"{safe_source}_{table}_raw"
        q_table = f"{self._quote(raw_schema)}.{self._quote(raw_table)}"

        with self.conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    f"INSERT INTO {q_table} (_arus_run_id, _data) VALUES (%s, %s)",
                    (run_id, json.dumps(row, default=str)),
                )
        self.conn.commit()
        return len(rows)

    def load_normalized(
        self, source_name: str, table: str, rows: list[dict]
    ) -> int:
        target_schema = self.config.get("target_schema", "analytics")
        q_table = f"{self._quote(target_schema)}.{self._quote(table)}"

        if not rows:
            return 0

        columns = list(rows[0].keys())
        col_names = ", ".join(self._quote(c) for c in columns)
        placeholders = ", ".join(["%s"] * len(columns))
        values = [[row.get(c, None) for c in columns] for row in rows]

        with self.conn.cursor() as cur:
            # Batch insert using executemany
            sql = f"INSERT INTO {q_table} ({col_names}) VALUES ({placeholders})"
            cur.executemany(sql, values)
        self.conn.commit()
        return len(rows)

    def update_watermark(
        self, pipeline_id: str, table: str, value: Any
    ) -> None:
        with self.conn.cursor() as cur:
            # Ensure arus_state database and watermark table exist
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS `arus_state`"
                " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS `arus_state`.`watermarks` (
                    pipeline_id VARCHAR(255) NOT NULL,
                    source_table VARCHAR(255) NOT NULL,
                    watermark_value VARCHAR(255) NOT NULL,
                    watermark_col VARCHAR(255) DEFAULT '',
                    last_synced_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
                    PRIMARY KEY (pipeline_id, source_table)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

            cur.execute(
                """
                INSERT INTO `arus_state`.`watermarks`
                    (pipeline_id, source_table, watermark_value, last_synced_at)
                VALUES (%s, %s, %s, NOW(3))
                ON DUPLICATE KEY UPDATE
                    watermark_value = VALUES(watermark_value),
                    last_synced_at = NOW(3)
                """,
                (pipeline_id, table, str(value)),
            )
        self.conn.commit()
