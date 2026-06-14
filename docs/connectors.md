# Connector Framework

Arus provides a **pluggable connector framework** based on abstract base classes. Connectors implement a standard interface and are auto-registered at startup.

---

## Architecture

```
BaseSource (abstract)          BaseDestination (abstract)
       │                               │
       ├── MySQLSource                 ├── PostgreSQLDestination
       ├── PostgreSQLSource            ├── MySQLDestination
       ├── MongoDBSource               ├── ClickHouseDestination
       └── (MariaDB = MySQLSource)     └── (MariaDB = MySQLDestination)

Registry
  _source_registry = {"mysql": MySQLSource, "postgresql": PostgreSQLSource, ...}
  _dest_registry  = {"postgresql": PostgreSQLDestination, ...}
```

---

## BaseSource Interface

All source connectors inherit from `BaseSource` (`arus/modules/connector/base_source.py`):

```python
from abc import ABC, abstractmethod
from typing import Iterator, Any
from dataclasses import dataclass, field


class BaseSource(ABC):
    type: str = ""

    @abstractmethod
    def connect(self, config: dict) -> bool:
        """Establish connection to the source database."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify the connection is working."""

    @abstractmethod
    def discover_tables(self) -> list[TableSchema]:
        """Return all discoverable tables with schema info."""

    @abstractmethod
    def get_table_columns(self, table: str) -> list[dict]:
        """Return column metadata for a specific table."""

    @abstractmethod
    def detect_sync_mode(self, table: str, columns: list[dict]) -> SyncMode:
        """Auto-detect incremental vs full refresh sync mode."""

    @abstractmethod
    def extract(self, table: str, watermark: Any = None,
                batch_size: int = 10000) -> Iterator[list[dict]]:
        """Extract rows from source table, yielding batches."""

    def extract_soft_deletes(self, table: str, watermark: Any,
                              deleted_at_column: str, watermark_column: str,
                              batch_size: int = 10000) -> list[dict]:
        """Extract soft-deleted rows since last watermark.
        Default: returns empty list (no soft-delete tracking).
        """
```

### Supporting Types

```python
@dataclass
class TableSchema:
    name: str
    schema_name: str = "public"
    columns: list[dict] = field(default_factory=list)
    row_count_estimate: int = 0

@dataclass
class SyncMode:
    mode: str = "incremental"  # "incremental" or "full_refresh"
    watermark_column: str | None = None
    deleted_at_column: str | None = None
```

---

## BaseDestination Interface

All destination connectors inherit from `BaseDestination` (`arus/modules/connector/base_destination.py`):

```python
from abc import ABC, abstractmethod
from typing import Any


class BaseDestination(ABC):
    type: str = ""

    @abstractmethod
    def connect(self, config: dict) -> bool:
        """Establish connection to the destination database."""

    @abstractmethod
    def ensure_schema(self, source_name: str, table: str,
                       columns: list[dict], target_schema: str = None) -> None:
        """Create schemas/tables if they don't exist."""

    @abstractmethod
    def load_raw(self, source_name: str, table: str,
                  rows: list[dict], run_id: str) -> int:
        """Load rows into raw landing zone (JSONB). Returns count."""

    @abstractmethod
    def load_normalized(self, source_name: str, table: str,
                         rows: list[dict], target_schema: str = None) -> int:
        """Load rows into normalized typed table. Returns count."""

    @abstractmethod
    def update_watermark(self, pipeline_id: str, table: str, value: Any) -> None:
        """Persist watermark value for incremental tracking."""

    def delete_rows(self, source_name: str, table: str, rows: list[dict],
                    pk_columns: list[str], target_schema: str = None) -> int:
        """Delete rows from target by primary key (soft-delete support)."""
```

---

## Built-in Source Connectors

### MySQLSource

| Property | Value |
|---|---|
| **Type** | `mysql` |
| **Driver** | `pymysql` |
| **Port** | 3306 |
| **Features** | Incremental via `updated_at`/`created_at`, full refresh, soft-delete filter (`deleted_at`), SSD |

#### Sync Mode Detection

Auto-detects watermark column by searching (in order):
1. `updated_at`, `modified_at`, `last_modified`, `updated`
2. `created_at`
3. Falls back to `full_refresh` if no timestamp column found

If `deleted_at` column is present, extract automatically adds `AND deleted_at IS NULL` to exclude soft-deleted rows.

#### Extract SQL (Incremental)

```sql
SELECT * FROM table
WHERE watermark_col > %s
  [AND deleted_at IS NULL]
ORDER BY watermark_col
LIMIT %s
```

### PostgreSQLSource

| Property | Value |
|---|---|
| **Type** | `postgresql` |
| **Driver** | `psycopg2` |
| **Port** | 5432 |
| **Features** | Schema discovery, incremental via timestamp, full refresh, soft-delete filter |

#### Schema Discovery

PostgreSQL connector supports `discover_schemas()` which lists all non-system schemas. The `schema_include` config filter limits which schemas are scanned.

#### Extract SQL (Incremental)

```sql
SELECT * FROM "schema"."table"
WHERE watermark_col > %s
  [AND "deleted_at" IS NULL]
ORDER BY watermark_col
LIMIT %s
```

### MongoDBSource

| Property | Value |
|---|---|
| **Type** | `mongodb` |
| **Driver** | `pymongo` |
| **Port** | 27017 |
| **Features** | URI-based or host-based connect, schema inference via document sampling, BSON serialization |

#### Connection

Supports two connection methods:
1. **Full URI**: `mongodb://user:pass@host:27017/db?authSource=admin`
2. **Individual fields**: host, port, username, password, database

#### Schema Inference

Column types are inferred by sampling one document via `find_one()`:

| BSON Type | Mapped Type |
|---|---|
| `datetime` | `timestamp` |
| `bool` | `boolean` |
| `int` | `bigint` |
| `float` | `double` |
| `dict`, `list` | `json` |
| `ObjectId` | `varchar(48)` |
| Other | `text` |

### MariaDBSource

| Property | Value |
|---|---|
| **Type** | `mariadb` |
| **Driver** | `pymysql` (MySQL protocol compatible) |
| **Implementation** | Aliased to `MySQLSource` |

---

## Built-in Destination Connectors

### PostgreSQLDestination

| Property | Value |
|---|---|
| **Type** | `postgresql` |
| **Driver** | `psycopg2` |
| **Raw Schema** | `staging` (configurable via `raw_schema`) |
| **Target Schema** | `analytics` (configurable via `target_schema`) |
| **Features** | JSONB raw storage, typed analytics tables, UPSERT via `ON CONFLICT DO NOTHING` |

#### Raw Table Schema

```sql
CREATE TABLE staging.<source>_<table>_raw (
    _arus_id        BIGSERIAL PRIMARY KEY,
    _arus_run_id    UUID NOT NULL,
    _arus_extracted TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    _data           JSONB NOT NULL
);
```

#### Analytics Table Schema

```sql
CREATE TABLE analytics.<table> (
    <column1> <pg_type> [NOT NULL],
    <column2> <pg_type> [NOT NULL],
    ...
    _arus_run_id    UUID NOT NULL,
    _arus_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### MySQLDestination

| Property | Value |
|---|---|
| **Type** | `mysql` |
| **Driver** | `pymysql` |
| **Raw Schema** | `staging` (as MySQL database) |
| **Target Schema** | `analytics` (as MySQL database) |
| **Features** | JSON raw storage, typed tables, batch `executemany` insert |

#### Type Mapping

| Source Type | MySQL Type |
|---|---|
| `int`, `integer` | `INT` |
| `bigint` | `BIGINT` |
| `varchar` | `VARCHAR(255)` |
| `text` | `TEXT` |
| `boolean`, `bool` | `TINYINT(1)` |
| `datetime`, `timestamp` | `DATETIME(3)` |
| `json`, `jsonb` | `JSON` |

### ClickHouseDestination

| Property | Value |
|---|---|
| **Type** | `clickhouse` |
| **Driver** | `clickhouse-connect` |
| **Port** | 8123 (HTTP, auto-converts from 9000) |
| **Engine** | `MergeTree` with auto-TTL (7 days for raw data) |
| **Features** | UUID-based raw storage, ReplacingMergeTree for watermarks |

#### Raw Table Schema

```sql
CREATE TABLE staging.<source>_<table>_raw (
    _arus_id         UUID DEFAULT generateUUIDv4(),
    _arus_run_id     String,
    _data            String,
    _arus_synced_at  DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (toStartOfHour(_arus_synced_at), _arus_id)
TTL toStartOfHour(_arus_synced_at) + INTERVAL 7 DAY DELETE
```

---

## Column Type Mapping

Source column types are mapped to destination types via `arus/shared/types.py`:

### PostgreSQL Type Map

| Source Type | PostgreSQL Type |
|---|---|
| `int`, `integer` | `INTEGER` |
| `bigint`, `serial`, `bigserial` | `BIGINT` |
| `smallint` | `SMALLINT` |
| `decimal`, `numeric` | `DECIMAL` |
| `float`, `double` | `DOUBLE PRECISION` |
| `varchar`, `char` | `VARCHAR` |
| `text`, `longtext`, `mediumtext` | `TEXT` |
| `boolean`, `tinyint` | `BOOLEAN` |
| `date` | `DATE` |
| `datetime`, `timestamp` | `TIMESTAMPTZ` |
| `json`, `jsonb` | `JSONB` |
| `blob`, `binary` | `BYTEA` |

---

## Adding a New Connector

### Source Connector

1. Create `arus/modules/connector/sources/<name>.py`
2. Implement `BaseSource`:
   ```python
   from arus.modules.connector.base_source import BaseSource, TableSchema, SyncMode

   class MyCustomSource(BaseSource):
       type = "my_custom"

       def connect(self, config): ...
       def test_connection(self): ...
       def discover_tables(self): ...
       def get_table_columns(self, table): ...
       def detect_sync_mode(self, table, columns): ...
       def extract(self, table, watermark=None, batch_size=10000): ...
   ```
3. Register it in `arus/modules/connector/registry.py`:
   ```python
   from arus.modules.connector.sources.my_custom import MyCustomSource
   register_source("my_custom", MyCustomSource)
   ```

### Destination Connector

1. Create `arus/modules/connector/destinations/<name>.py`
2. Implement `BaseDestination`:
   ```python
   from arus.modules.connector.base_destination import BaseDestination

   class MyCustomDestination(BaseDestination):
       type = "my_custom"

       def connect(self, config): ...
       def ensure_schema(self, source_name, table, columns, target_schema=None): ...
       def load_raw(self, source_name, table, rows, run_id): ...
       def load_normalized(self, source_name, table, rows, target_schema=None): ...
       def update_watermark(self, pipeline_id, table, value): ...
   ```
3. Register it in `arus/modules/connector/registry.py`:
   ```python
   from arus.modules.connector.destinations.my_custom import MyCustomDestination
   register_destination("my_custom", MyCustomDestination)
   ```
