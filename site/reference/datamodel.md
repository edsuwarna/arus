# Data Model

Arus uses a single PostgreSQL instance with multiple schemas to separate concerns.

---

## Schema Overview

```sql
arus_config      -- Configuration (auth, sources, pipelines, settings)
arus_state       -- Watermark/state tracking
arus_run_logs    -- Run history and logs
staging          -- Raw landing zone (JSONB tables)
analytics        -- Normalized typed tables
```

---

## Schema: `arus_config`

### users

User accounts for Arus Console authentication.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK, default `gen_random_uuid()` | User ID |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL, INDEX | Login email |
| `password_hash` | `VARCHAR(255)` | NOT NULL | bcrypt hash |
| `name` | `VARCHAR(255)` | NOT NULL | Display name |
| `role` | `VARCHAR(20)` | NOT NULL, default `viewer` | `admin`, `editor`, `viewer` |
| `is_active` | `BOOLEAN` | default `true` | Account enabled/disabled |
| `last_login` | `TIMESTAMPTZ` | nullable | Last login timestamp |
| `created_at` | `TIMESTAMPTZ` | default `NOW()` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | default `NOW()` | Last update timestamp |

### sources

Registered source database connections.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Source ID |
| `name` | `VARCHAR(255)` | NOT NULL | Display name |
| `type` | `VARCHAR(50)` | NOT NULL | `mysql`, `postgresql`, `mongodb`, `mariadb` |
| `host` | `VARCHAR(255)` | NOT NULL | Database host |
| `port` | `INTEGER` | NOT NULL | Database port |
| `database` | `VARCHAR(255)` | NOT NULL | Database name |
| `username` | `VARCHAR(255)` | NOT NULL | Database username |
| `password_enc` | `TEXT` | NOT NULL | Fernet-encrypted password |
| `ssl` | `BOOLEAN` | default `false` | SSL enabled |
| `uri` | `TEXT` | nullable | MongoDB connection string |
| `auth_source` | `VARCHAR(100)` | nullable | MongoDB auth database |
| `sync_method` | `VARCHAR(20)` | default `auto` | `auto`, `incremental`, `full_refresh` |
| `table_include` | `VARCHAR[]` | default `[]` | Include glob patterns |
| `table_exclude` | `VARCHAR[]` | default `[]` | Exclude glob patterns |
| `schema_include` | `VARCHAR[]` | default `[]` | PostgreSQL schemas to scan |
| `status` | `VARCHAR(20)` | default `registered` | `registered`, `connected`, `error` |
| `last_tested` | `TIMESTAMPTZ` | nullable | Last connection test |
| `created_at` | `TIMESTAMPTZ` | default `NOW()` | |
| `updated_at` | `TIMESTAMPTZ` | default `NOW()` | |

### destinations

Registered destination (warehouse) connections.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Destination ID |
| `name` | `VARCHAR(255)` | NOT NULL | Display name |
| `type` | `VARCHAR(50)` | NOT NULL | `postgresql`, `mysql`, `clickhouse` |
| `host` | `VARCHAR(255)` | nullable | Destination host |
| `port` | `INTEGER` | nullable | Destination port |
| `database` | `VARCHAR(255)` | nullable | Database name |
| `username` | `VARCHAR(255)` | nullable | Username |
| `password_enc` | `TEXT` | nullable | Encrypted password |
| `ssl` | `BOOLEAN` | default `false` | |
| `raw_schema` | `VARCHAR(255)` | default `staging` | Raw landing schema |
| `target_schema` | `VARCHAR(255)` | default `analytics` | Normalized target schema |
| `is_default` | `BOOLEAN` | default `false` | Default destination |
| `status` | `VARCHAR(20)` | default `registered` | |
| `created_at` | `TIMESTAMPTZ` | default `NOW()` | |
| `updated_at` | `TIMESTAMPTZ` | default `NOW()` | |

### pipelines

Pipeline configuration.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | Pipeline ID |
| `name` | `VARCHAR(255)` | NOT NULL | Pipeline name |
| `source_id` | `UUID` | FK → `sources.id` ON DELETE CASCADE | Source reference |
| `destination_id` | `UUID` | FK → `destinations.id` ON DELETE RESTRICT | Destination reference |
| `status` | `VARCHAR(20)` | default `active` | `active`, `paused`, `inactive` |
| `schedule` | `VARCHAR(100)` | nullable | Cron expression |
| `max_retries` | `INTEGER` | default `3` | Per-pipeline retry override |
| `timeout_seconds` | `INTEGER` | default `300` | Pipeline timeout |
| `depends_on` | `UUID` | FK → `pipelines.id` ON DELETE SET NULL | Pipeline dependency |
| `target_schema` | `VARCHAR(255)` | default `public` | Default target schema |
| `load_mode` | `VARCHAR(20)` | default `direct` | `direct` or `raw` |
| `created_at` | `TIMESTAMPTZ` | default `NOW()` | |
| `updated_at` | `TIMESTAMPTZ` | default `NOW()` | |

### pipeline_tables

Per-table configuration within a pipeline.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `pipeline_id` | `UUID` | FK → `pipelines.id` ON DELETE CASCADE | |
| `source_table` | `VARCHAR(255)` | NOT NULL | Table name in source |
| `source_schema` | `VARCHAR(255)` | default `public` | Source schema |
| `target_schema` | `VARCHAR(255)` | nullable | Per-table override |
| `sync_mode` | `VARCHAR(20)` | default `incremental` | `incremental` or `full_refresh` |
| `load_mode` | `VARCHAR(20)` | default `direct` | `direct` or `raw` |
| `watermark_column` | `VARCHAR(255)` | nullable | Override auto-detected column |
| `transform_config` | `JSON` | nullable | Array of transform step objects |
| `enabled` | `BOOLEAN` | default `true` | Enable/disable table |

### transform_scripts

Python transform scripts for pipelines.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `pipeline_id` | `UUID` | FK → `pipelines.id` ON DELETE CASCADE | |
| `name` | `VARCHAR(255)` | NOT NULL | Script name |
| `description` | `TEXT` | nullable | |
| `content` | `TEXT` | NOT NULL | Python source code |
| `created_at` | `TIMESTAMPTZ` | default `NOW()` | |
| `updated_at` | `TIMESTAMPTZ` | default `NOW()` | |

### notification_targets

Notification channels (Telegram, Discord, Slack).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `name` | `VARCHAR(255)` | NOT NULL | |
| `type` | `VARCHAR(50)` | NOT NULL | `telegram`, `discord`, `slack` |
| `config` | `JSONB` | NOT NULL | Type-specific config |
| `active` | `BOOLEAN` | default `true` | |
| `created_at` | `TIMESTAMPTZ` | default `NOW()` | |

### pipeline_notifications

Links between pipelines and notification targets.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `pipeline_id` | `UUID` | NOT NULL | |
| `target_id` | `UUID` | NOT NULL | |
| `events` | `JSONB` | default `[]` | Event types array |
| `created_at` | `TIMESTAMPTZ` | default `NOW()` | |

### runtime_settings

Key-value runtime settings (managed via UI).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `key` | `VARCHAR(100)` | UNIQUE, NOT NULL | Setting key |
| `value` | `TEXT` | nullable | Setting value |
| `updated_at` | `TIMESTAMPTZ` | default `NOW()` | |

### data_quality_log

Data quality check results.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `pipeline_id` | `UUID` | NOT NULL, INDEX | |
| `run_id` | `UUID` | NOT NULL, INDEX | |
| `table_name` | `VARCHAR(255)` | NOT NULL | |
| `check_type` | `VARCHAR(50)` | NOT NULL | `row_count`, `null_check` |
| `status` | `VARCHAR(20)` | NOT NULL | `passed`, `failed`, `warning` |
| `rows_extracted` | `INTEGER` | nullable | |
| `rows_loaded` | `INTEGER` | nullable | |
| `discrepancy_pct` | `FLOAT` | nullable | Row count discrepancy |
| `null_columns` | `TEXT` | nullable | Comma-separated null columns |
| `required_columns` | `TEXT` | nullable | |
| `message` | `TEXT` | nullable | |
| `passed` | `BOOLEAN` | default `true` | |
| `checked_at` | `TIMESTAMPTZ` | default `NOW()` | |

---

## Schema: `arus_state`

### watermarks

Incremental sync state tracking.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `pipeline_id` | `UUID` | NOT NULL | |
| `source_table` | `VARCHAR(255)` | NOT NULL | |
| `watermark_col` | `VARCHAR(255)` | nullable | Column used for watermark |
| `watermark_value` | `TEXT` | nullable | Current watermark value |
| `row_count` | `INTEGER` | default `0` | Last synced row count |
| `last_run_id` | `UUID` | nullable | Last run reference |
| `last_synced_at` | `TIMESTAMPTZ` | nullable | |
| `created_at` | `TIMESTAMPTZ` | default `NOW()` | |
| `updated_at` | `TIMESTAMPTZ` | default `NOW()` | |

**Unique constraint**: `(pipeline_id, source_table)`

---

## Schema: `arus_run_logs`

### runs

Individual pipeline run records.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `pipeline_id` | `UUID` | NOT NULL | |
| `status` | `VARCHAR(20)` | default `running` | `running`, `success`, `failed`, `cancelled`, `skipped` |
| `started_at` | `TIMESTAMPTZ` | default `NOW()` | |
| `finished_at` | `TIMESTAMPTZ` | nullable | |
| `duration_ms` | `INTEGER` | nullable | |
| `rows_synced` | `INTEGER` | default `0` | |
| `trigger_type` | `VARCHAR(20)` | default `scheduled` | `scheduled`, `manual`, `backfill`, `full_refresh` |
| `error_message` | `TEXT` | nullable | |
| `created_at` | `TIMESTAMPTZ` | default `NOW()` | |

### run_table_stats

Per-table statistics within a run.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `run_id` | `UUID` | FK → `runs.id` ON DELETE CASCADE | |
| `table_name` | `VARCHAR(255)` | NOT NULL | |
| `rows_extracted` | `INTEGER` | default `0` | |
| `rows_loaded_raw` | `INTEGER` | default `0` | Rows into staging |
| `rows_loaded_analytics` | `INTEGER` | default `0` | Rows into analytics |
| `rows_failed` | `INTEGER` | default `0` | |
| `watermark_before` | `TEXT` | nullable | |
| `watermark_after` | `TEXT` | nullable | |
| `duration_ms` | `INTEGER` | default `0` | |
| `error_message` | `TEXT` | nullable | |

### run_logs

Timestamped log entries for each run.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `BIGINT` | PK, autoincrement | Log entry ID |
| `run_id` | `UUID` | FK → `runs.id` ON DELETE CASCADE | |
| `timestamp` | `TIMESTAMPTZ` | default `NOW()` | |
| `level` | `VARCHAR(10)` | default `INFO` | `INFO`, `WARNING`, `ERROR`, `DEBUG` |
| `message` | `TEXT` | NOT NULL | Log message |

---

## Schema: `staging`

### `<source>_<table>_raw`

Auto-created raw landing tables (one per synced source table).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `_arus_id` | `BIGSERIAL` | PK | |
| `_arus_run_id` | `UUID` | NOT NULL | Run reference |
| `_arus_extracted` | `TIMESTAMPTZ` | default `NOW()` | Extraction timestamp |
| `_data` | `JSONB` | NOT NULL | Full source row as JSON |

### `_dead_letters`

Failed rows that couldn't be loaded after retries.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `source_name` | `VARCHAR(255)` | NOT NULL | |
| `table_name` | `VARCHAR(255)` | NOT NULL | |
| `run_id` | `UUID` | NOT NULL, INDEX | |
| `row_data` | `JSONB` | NOT NULL | Failed row data |
| `error_text` | `TEXT` | nullable | Error message |
| `failed_at` | `TIMESTAMPTZ` | default `NOW()` | |

---

## Schema: `analytics`

### `<table>`

Auto-created normalized tables mirroring source table structure.

Each table has:
- All source columns mapped to PostgreSQL types
- `_arus_run_id` UUID NOT NULL — reference to the run that synced this row
- `_arus_synced_at` TIMESTAMPTZ DEFAULT NOW() — when the row was loaded

---

## Entity Relationship

```
users ─────────── has many ──→ runs (via pipeline triggers)
     │
sources ──── has many ──→ pipelines ──── has many ──→ pipeline_tables
     │                          │
     │                          ├── has many ──→ transform_scripts
     │                          │
     │                          └── has many ──→ runs ──── has many ──→ run_logs
     │                                                    └── has many ──→ run_table_stats
     │
     │                          ┌── has many ──→ watermarks (arus_state)
     │                          │
     └── has many ──→ pipeline_notifications ──── has one ──→ notification_targets
```
