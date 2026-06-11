# Connector Roadmap — Arus

> **Version:** 1.0
> **Status:** 🔴 Draft
> **Last Updated:** June 2026

---

## 1. Architecture: Pluggable Connector SDK

Arus connectors follow a simple base-class interface. Every source or destination is a Python class that inherits from `BaseSource` or `BaseDestination`.

### Source Interface

```python
class BaseSource(ABC):
    """Implement this to add a new source type."""

    type: str  # unique identifier, e.g. "mysql", "mongodb"

    @abstractmethod
    def validate_connection(self) -> bool:
        """Test connection to the source. Returns True if reachable."""

    @abstractmethod
    def discover_tables(self) -> list[TableSchema]:
        """Scan source and return all tables with columns, types, estimates."""

    def detect_sync_mode(self, table: str) -> SyncMode:
        """
        Auto-detect best sync mode.
        Default: prefer `updated_at` column → incremental, else full refresh.
        """

    @abstractmethod
    def extract(self, table: str, watermark: Any = None, batch_size: int = 10000) -> Iterator[list[dict]]:
        """
        Extract rows from source.
        - Incremental: SELECT ... WHERE updated_at > watermark ORDER BY updated_at LIMIT batch_size
        - Full refresh: SELECT * FROM table (no watermark)
        Returns iterator of dict batches.
        """
```

### Destination Interface

```python
class BaseDestination(ABC):
    """Implement this to support a new warehouse / target."""

    type: str

    @abstractmethod
    def validate_connection(self) -> bool:
        """Test connection."""

    @abstractmethod
    def ensure_schema(self, source_name: str, table: str, columns: list[ColumnDef]) -> None:
        """Create raw + normalized tables if not exist."""

    @abstractmethod
    def load_raw(self, source_name: str, table: str, rows: list[dict]) -> int:
        """Insert JSONB rows into staging.<source>_<table>_raw."""

    @abstractmethod
    def load_normalized(self, source_name: str, table: str, rows: list[dict]) -> int:
        """Upsert typed rows into analytics.<table>."""

    @abstractmethod
    def update_watermark(self, source_name: str, table: str, value: Any) -> None:
        """Save watermark to arus_state."""
```

### Registration

Connectors register themselves via config:

```yaml
connectors:
  sources:
    mysql: arus.connectors.mysql.MySQLSource
    mongodb: arus.connectors.mongodb.MongoDBSource
  destinations:
    postgresql: arus.connectors.postgresql.PostgreSQLDestination
    clickhouse: arus.connectors.clickhouse.ClickHouseDestination
```

> New connector = 1 Python file + 1 config entry. No rebuild, no redeploy of other connectors.

---

## 2. Source Connector Priority Matrix

| Source | Phase | Priority | Driver | Notes |
|--------|-------|----------|--------|-------|
| **MySQL** | P1 | 🔴 Critical | `pymysql` | Primary CDC target — most common source |
| **MariaDB** | P1 | 🔴 Critical | `pymysql` | MySQL-compatible, same connector |
| **PostgreSQL** | P1 | 🔴 Critical | `psycopg2` / `asyncpg` | Primary + also the warehouse itself |
| **MongoDB** | P2 | 🟡 High | `pymongo` | NoSQL — different sync strategy (document-based) |
| **SQL Server** | P2 | 🟡 High | `pymssql` / `pyodbc` | Legacy enterprise, still widely used |
| **Google BigQuery (source)** | P2 | 🟡 High | `google-cloud-bigquery` | Pull data from cloud DW |
| **REST API framework** | P3 | 🟢 Medium | `httpx` | Generic: define endpoint + JSONPath mapping |
| **Stripe** | P3 | 🟢 Medium | `stripe` Python SDK | E-commerce / subscription data |
| **Shopify** | P3 | 🟢 Medium | `shopifyapi` | E-commerce orders, products, customers |
| **Google Analytics / Search Console** | P3 | 🟢 Medium | `google-analytics-data` | Marketing analytics source |
| **CSV / Parquet file** | P3 | 🟢 Medium | — | Upload file via UI → ingest to warehouse |
| **S3 / GCS** | P4 | 🔵 Nice-to-have | `boto3` | File-based ingestion from object storage |

---

## 3. Destination Priority Matrix

| Destination | Phase | Priority | Driver | Notes |
|-------------|-------|----------|--------|-------|
| **PostgreSQL** | P1 | 🔴 Critical | `psycopg2` | Default warehouse — built-in from day 1 |
| **ClickHouse** | P2 | 🟡 High | `clickhouse-driver` | Columnar analytics — light enough for VPS |
| **MySQL / MariaDB (dest)** | P2 | 🟡 High | `pymysql` | Reverse sync use cases |
| **Google BigQuery (dest)** | P2 | 🟡 High | `google-cloud-bigquery` | Scale to cloud DW |
| **Parquet / CSV export** | P3 | 🟢 Medium | `pyarrow` | Data lake / backup / ML |
| **SQLite** | P3 | 🟢 Medium | `sqlite3` | Testing, edge, local dev |
| **Webhook** | P3 | 🟢 Medium | `httpx` | Real-time push to external system |
| **Elasticsearch** | P4 | 🔵 Nice-to-have | `elasticsearch` | Logs / search analytics |
| **DuckDB** | P4 | 🔵 Nice-to-have | `duckdb` | Embedded analytics, lightweight alternative to ClickHouse |

---

## 4. Sync Modes per Source Type

| Source Type | Incremental Method | Full Refresh | Notes |
|-------------|-------------------|--------------|-------|
| MySQL | `updated_at` / `modified_at` column | ✅ | Falls back to auto-increment ID if no timestamp |
| MariaDB | Same as MySQL | ✅ | Compatible |
| PostgreSQL | `updated_at` or `pgoutput` (future) | ✅ | Logical replication planned for P3 |
| MongoDB | `_id` ObjectID (monotonic) or `updatedAt` | ✅ | Document-based extraction |
| SQL Server | `ModifiedDate` / `rowversion` | ✅ | |
| BigQuery | `TIMESTAMP` partition column | ✅ | Full table scan billed — incremental critical |
| REST API | Pagination cursor / timestamp param | ✅ | User defines cursor field |
| Stripe | `created.gte` pagination | ✅ | API-native pagination |
| CSV/Parquet | N/A | ✅ | Always full refresh (static files) |

---

## 5. Connector Implementation Effort Estimates

| Connector | Est. Effort | Complexity | Key Challenges |
|-----------|-------------|------------|----------------|
| MySQL | 1 day | Low | Well-known driver, simple SELECT pattern |
| MariaDB | 0.5 day | Low | Shares MySQL connector |
| PostgreSQL | 1 day | Low | Same pattern as MySQL |
| MongoDB | 2 days | Medium | Document flattening, array handling, no watermark col |
| SQL Server | 2 days | Medium | Driver quirks, type mapping edge cases |
| BigQuery (source) | 1.5 days | Medium | GCP auth, pagination, cost-aware extraction |
| REST API framework | 3 days | High | Generic YAML config, JSONPath mapping, pagination types |
| Stripe | 1 day | Low | Well-documented API, cursor pagination |
| ClickHouse (dest) | 1 day | Low | Columnar MERGE, type mapping |
| Parquet export | 1 day | Low | pyarrow, file rotation |
| Webhook | 0.5 day | Low | Simple POST with retry |

---

## 6. Default Connector Configurations

### Source Defaults

| Setting | Default | Connector Overridable |
|---------|---------|-----------------------|
| Batch size | 10,000 rows | ✅ |
| Connection timeout | 10s | ✅ |
| Max retries | 3 | ✅ |
| Retry delay | exponential (1s, 5s, 15s) | ✅ |
| Incremental column auto-detect | `updated_at`, `modified_at`, `last_modified`, `updated` | ✅ |
| Schema discovery interval | Every pipeline run | ✅ |

### Destination Defaults

| Setting | Default | Connector Overridable |
|---------|---------|-----------------------|
| Raw table suffix | `_raw` | ✅ |
| Normalized schema | `analytics` | ✅ |
| Staging schema | `staging` | ✅ |
| Upsert strategy | `ON CONFLICT DO UPDATE` by PK | ✅ |
| Batch commit | 1,000 rows per transaction | ✅ |

---

## 7. Community Contribution Guide (draft)

Arus connector SDK is designed so anyone can add a connector:

```
arus/connectors/
├── sources/
│   ├── __init__.py
│   ├── base.py              ← BaseSource abstract class
│   ├── mysql.py
│   ├── postgresql.py
│   ├── mongodb.py
│   └── ...
├── destinations/
│   ├── __init__.py
│   ├── base.py              ← BaseDestination abstract class
│   ├── postgresql.py
│   ├── clickhouse.py
│   └── ...
└── registry.py              ← Connector registry (YAML-based)
```

To contribute a connector:
1. Create `arus/connectors/sources/<name>.py`
2. Implement `BaseSource` or `BaseDestination`
3. Add to `connectors.yaml` registry
4. Add type mapping in `arus/connectors/types.py`
5. Write a 5-line test

---

*End of Connector Roadmap — Arus v1.0*
