"""ClickHouse Destination Connector — loads data into ClickHouse tables."""
from typing import Any

import clickhouse_connect

from arus.modules.connector.base_destination import BaseDestination

# Column-type mapping: source -> ClickHouse
CLICKHOUSE_TYPE_MAP = {
    "int": "Int32",
    "integer": "Int32",
    "smallint": "Int16",
    "bigint": "Int64",
    "tinyint": "UInt8",
    "serial": "Int64",
    "bigserial": "Int64",
    "decimal": "Decimal(38, 10)",
    "numeric": "Decimal(38, 10)",
    "float": "Float64",
    "double": "Float64",
    "real": "Float32",
    "varchar": "String",
    "char": "String",
    "text": "String",
    "longtext": "String",
    "mediumtext": "String",
    "boolean": "UInt8",
    "bool": "UInt8",
    "date": "Date",
    "datetime": "DateTime64(3)",
    "timestamp": "DateTime64(3)",
    "json": "String",
    "jsonb": "String",
    "blob": "String",
    "binary": "String",
    "uuid": "String",
    "enum": "String",
    "ObjectId": "String",
    "null": "String",
}


def map_clickhouse_type(source_type: str) -> str:
    """Map a source DB column type to a ClickHouse type."""
    base = source_type.lower().split("(")[0].split()[0]
    return CLICKHOUSE_TYPE_MAP.get(base, "String")


class ClickHouseDestination(BaseDestination):
    type = "clickhouse"

    def __init__(self):
        self.client = None
        self.config = {}

    def connect(self, config: dict) -> bool:
        self.config = config
        db_host = config.get("host", "localhost")
        db_port = config.get("port", 8123)
        # If port is 9000 (native) switch to 8123 (HTTP) automatically
        if db_port == 9000:
            db_port = 8123
        self.client = clickhouse_connect.get_client(
            host=db_host,
            port=db_port,
            username=config.get("username", "default"),
            password=config.get("password", ""),
            database=config.get("database", "default"),
        )
        return True

    def test_connection(self) -> bool:
        try:
            self.client.query("SELECT 1")
            return True
        except Exception:
            return False

    def _safe_name(self, name: str) -> str:
        return name.lower().replace("-", "_").replace(".", "_").replace(" ", "_")

    def _quote(self, name: str) -> str:
        """ClickHouse-safe backtick quoting."""
        return f"`{name.replace('`', '``')}`"

    def ensure_schema(self, source_name: str, table: str, columns: list[dict], target_schema: str = None) -> None:
        safe_source = self._safe_name(source_name)
        raw_db = self.config.get("raw_database", self.config.get("raw_schema", "staging"))
        analytics_db = target_schema or self.config.get("analytics_database",
                                       self.config.get("target_schema", "public"))
        raw_table = f"{safe_source}_{table}_raw"
        q_raw_db = self._quote(raw_db)
        q_analytics_db = self._quote(analytics_db)

        # Create databases
        self.client.command(f"CREATE DATABASE IF NOT EXISTS {q_raw_db}")
        self.client.command(f"CREATE DATABASE IF NOT EXISTS {q_analytics_db}")

        # Create raw (JSON-as-String) table
        q_raw_table = self._quote(raw_table)
        self.client.command(f"""
            CREATE TABLE IF NOT EXISTS {q_raw_db}.{q_raw_table} (
                _arus_id UUID DEFAULT generateUUIDv4(),
                _arus_run_id String,
                _data String,
                _arus_synced_at DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY (toStartOfHour(_arus_synced_at), _arus_id)
            TTL toStartOfHour(_arus_synced_at) + INTERVAL 7 DAY DELETE
        """)

        # Create analytics table
        col_defs = []
        for col in columns:
            ch_type = map_clickhouse_type(col["type"])
            col_defs.append(f"{self._quote(col['name'])} Nullable({ch_type})")

        col_defs.append("`_arus_run_id` String")
        col_defs.append("`_arus_synced_at` DateTime DEFAULT now()")

        q_table = self._quote(table)
        order_col = columns[0]["name"] if columns else "_arus_synced_at"
        self.client.command(f"""
            CREATE TABLE IF NOT EXISTS {q_analytics_db}.{q_table} (
                {', '.join(col_defs)}
            ) ENGINE = MergeTree()
            ORDER BY ({self._quote(order_col)}, `_arus_synced_at`)
        """)

    def load_raw(self, source_name: str, table: str,
                 rows: list[dict], run_id: str) -> int:
        import json

        safe_source = self._safe_name(source_name)
        raw_db = self.config.get("raw_database", self.config.get("raw_schema", "staging"))
        q_raw_db = self._quote(raw_db)
        q_raw_table = self._quote(f"{safe_source}_{table}_raw")

        data = [(run_id, json.dumps(row, default=str)) for row in rows]

        self.client.insert(
            f"{q_raw_db}.{q_raw_table}",
            data,
            column_names=["_arus_run_id", "_data"],
        )
        return len(rows)

    def load_normalized(self, source_name: str, table: str,
                        rows: list[dict], target_schema: str = None) -> int:
        analytics_db = target_schema or self.config.get("analytics_database",
                                       self.config.get("target_schema", "public"))
        q_analytics_db = self._quote(analytics_db)
        q_table = self._quote(table)

        if not rows:
            return 0

        columns = list(rows[0].keys())
        values = [[row.get(c, None) for c in columns] for row in rows]

        self.client.insert(
            f"{q_analytics_db}.{q_table}",
            values,
            column_names=columns,
        )
        return len(rows)

    def update_watermark(self, pipeline_id: str, table: str, value: Any) -> None:
        """Store watermark in ClickHouse arus_state DB (ReplacingMergeTree)."""
        self.client.command("CREATE DATABASE IF NOT EXISTS `arus_state`")
        self.client.command("""
            CREATE TABLE IF NOT EXISTS arus_state.watermarks (
                pipeline_id String,
                source_table String,
                watermark_value String,
                watermark_col String DEFAULT '',
                last_synced_at DateTime DEFAULT now()
            ) ENGINE = ReplacingMergeTree(last_synced_at)
            ORDER BY (pipeline_id, source_table)
        """)

        # ClickHouse has no UPSERT — use INSERT and rely on ReplacingMergeTree
        self.client.insert(
            "arus_state.watermarks",
            [(pipeline_id, table, str(value), self.config.get("watermark_col", ""),
              "now()")],
            column_names=["pipeline_id", "source_table", "watermark_value",
                          "watermark_col", "last_synced_at"],
        )
