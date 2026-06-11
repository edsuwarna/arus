# Arus Data Model

> **Version:** 1.0
> **Status:** 🔴 Draft
> **Last Updated:** June 2026
> **Database:** PostgreSQL 15+
> **Schema Convention:** One PostgreSQL instance, multiple schemas

---

## 1. Schema Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL Instance                          │
│                                                                  │
│  ┌─ arus_config ──────────────────────────────────────────────┐ │
│  │  users, sources, pipelines, pipeline_tables,               │ │
│  │  destinations, settings, schema_versions                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ arus_state ───────────────────────────────────────────────┐ │
│  │  watermarks                                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ staging ──────────────────────────────────────────────────┐ │
│  │  <source>_<table>_raw, _dead_letters                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─ analytics ────────────────────────────────────────────────┐ │
│  │  <table> — normalized, typed columns                     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- **Single PostgreSQL instance** — warehouse + config + state, no extra infra
- **Separate schemas** — clear separation of concerns, easy backup
- **`arus_` prefix** for system schemas — visible but distinct from user data
- **`staging` + `analytics`** — standard ELT two-zone pattern

---

## 2. `arus_config` Schema (System Configuration)

### 2.1 `arus_config.users`

User accounts for Arus Console access.

```sql
CREATE TABLE arus_config.users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name          VARCHAR(255) NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'viewer'
                      CHECK (role IN ('admin', 'viewer')),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON arus_config.users(email);
```

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Auto-generated |
| `email` | VARCHAR(255) | Unique, used for login |
| `password_hash` | VARCHAR(255) | bcrypt hash |
| `name` | VARCHAR(255) | Display name |
| `role` | `admin` or `viewer` | Admin: full access. Viewer: read-only |
| `is_active` | BOOLEAN | Soft-delete / disable account |
| `last_login` | TIMESTAMPTZ | Updated on each login |
| `created_at` / `updated_at` | TIMESTAMPTZ | Audit timestamps |

### 2.2 `arus_config.sources`

Registered source database connections.

```sql
CREATE TABLE arus_config.sources (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             VARCHAR(255) NOT NULL,
    type             VARCHAR(50)  NOT NULL
                         CHECK (type IN ('mysql', 'mariadb', 'postgresql', 'mongodb', 'sqlserver', 'bigquery', 'api')),
    host             VARCHAR(255) NOT NULL,
    port             INTEGER      NOT NULL,
    database         VARCHAR(255) NOT NULL,
    username         VARCHAR(255) NOT NULL,
    password_enc     TEXT         NOT NULL,
    ssl              BOOLEAN      NOT NULL DEFAULT FALSE,
    sync_method      VARCHAR(20)  NOT NULL DEFAULT 'auto'
                         CHECK (sync_method IN ('auto', 'incremental', 'full_refresh')),
    table_include    TEXT[]       DEFAULT '{}',   -- glob patterns, e.g. {"orders*", "users"}
    table_exclude    TEXT[]       DEFAULT '{}',   -- glob patterns, e.g. {"*_temp"}
    status           VARCHAR(20)  NOT NULL DEFAULT 'registered'
                         CHECK (status IN ('registered', 'connected', 'disconnected', 'error')),
    last_tested      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sources_type ON arus_config.sources(type);
```

| Column | Notes |
|--------|-------|
| `password_enc` | Encrypted at rest (Fernet or AES-GCM) |
| `sync_method` | `auto` = detect per-table. `incremental` / `full_refresh` = force all tables |
| `table_include/exclude` | Postgres TEXT array of glob patterns |

### 2.3 `arus_config.destinations`

Data destinations (default: PostgreSQL warehouse). Future: multiple destinations.

```sql
CREATE TABLE arus_config.destinations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(255) NOT NULL,
    type              VARCHAR(50)  NOT NULL
                          CHECK (type IN ('postgresql', 'clickhouse', 'bigquery', 'mysql')),
    host              VARCHAR(255),
    port              INTEGER,
    database          VARCHAR(255),
    username          VARCHAR(255),
    password_enc      TEXT,
    ssl               BOOLEAN      NOT NULL DEFAULT FALSE,
    raw_schema        VARCHAR(255) NOT NULL DEFAULT 'staging',
    analytics_schema  VARCHAR(255) NOT NULL DEFAULT 'analytics',
    is_default        BOOLEAN      NOT NULL DEFAULT FALSE,
    status            VARCHAR(20)  NOT NULL DEFAULT 'registered'
                          CHECK (status IN ('registered', 'connected', 'disconnected', 'error')),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Exactly one default destination
CREATE UNIQUE INDEX idx_destinations_default ON arus_config.destinations(is_default) WHERE is_default = TRUE;
```

### 2.4 `arus_config.pipelines`

Pipeline definitions — one pipeline per source in MVP.

```sql
CREATE TABLE arus_config.pipelines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    source_id       UUID         NOT NULL REFERENCES arus_config.sources(id) ON DELETE CASCADE,
    destination_id  UUID         NOT NULL REFERENCES arus_config.destinations(id) ON DELETE RESTRICT,
    status          VARCHAR(20)  NOT NULL DEFAULT 'active'
                        CHECK (status IN ('active', 'paused', 'error', 'inactive')),
    schedule        VARCHAR(100),           -- cron expression, NULL = manual only
    max_retries     INTEGER      NOT NULL DEFAULT 3,
    retry_delay_ms  INTEGER      NOT NULL DEFAULT 5000,
    timeout_seconds INTEGER      NOT NULL DEFAULT 300,
    parallelism     INTEGER      NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pipelines_source ON arus_config.pipelines(source_id);
CREATE INDEX idx_pipelines_status ON arus_config.pipelines(status);
```

### 2.5 `arus_config.pipeline_tables`

Per-pipeline table configuration (join table with metadata).

```sql
CREATE TABLE arus_config.pipeline_tables (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id      UUID         NOT NULL REFERENCES arus_config.pipelines(id) ON DELETE CASCADE,
    source_table     VARCHAR(255) NOT NULL,           -- original table name in source
    source_schema    VARCHAR(255) DEFAULT 'public',
    sync_mode        VARCHAR(20)  NOT NULL DEFAULT 'incremental'
                         CHECK (sync_mode IN ('incremental', 'full_refresh')),
    watermark_column VARCHAR(255),                     -- NULL = full refresh
    enabled          BOOLEAN      NOT NULL DEFAULT TRUE,

    UNIQUE(pipeline_id, source_table)
);

CREATE INDEX idx_pipeline_tables_pipe ON arus_config.pipeline_tables(pipeline_id);
```

### 2.6 `arus_config.settings`

Key-value settings store for Arus-wide configuration.

```sql
CREATE TABLE arus_config.settings (
    key         VARCHAR(255) PRIMARY KEY,
    value       JSONB        NOT NULL,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

**Seed data:**

| Key | Default Value | Description |
|-----|---------------|-------------|
| `default_sync_interval` | `"*/5 * * * *"` | Default pipeline schedule |
| `auto_discover` | `true` | Auto-scan new sources on add |
| `schema_drift_detection` | `true` | Auto-ALTER on new source columns |
| `notifications_enabled` | `false` | Master toggle for alerts |
| `telegram_bot_token` | `null` | Telegram bot token |
| `telegram_chat_id` | `null` | Telegram notification target |
| `webhook_url` | `null` | Generic webhook URL |
| `retry_max_attempts` | `3` | Max retries per run |
| `batch_size` | `10000` | Rows per batch |
| `secret_key` | `null` | Fernet key for password encryption |

---

## 3. `arus_state` Schema (Runtime State)

### 3.1 `arus_state.watermarks`

Tracks incremental extraction progress per table.

```sql
CREATE TABLE arus_state.watermarks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID         NOT NULL REFERENCES arus_config.pipelines(id) ON DELETE CASCADE,
    source_table    VARCHAR(255) NOT NULL,
    watermark_col   VARCHAR(255),           -- NULL = full refresh mode
    watermark_value TEXT,                     -- stored as text, cast depends on column type
    row_count       BIGINT       NOT NULL DEFAULT 0,
    last_run_id     UUID,                    -- FK to run_history
    last_synced_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    UNIQUE(pipeline_id, source_table)
);

CREATE INDEX idx_watermarks_pipeline ON arus_state.watermarks(pipeline_id);
```

**Watermark value examples:**

| Column Type | `watermark_value` stored as | Cast Example |
|-------------|----------------------------|--------------|
| `TIMESTAMP` | `"2026-06-12T09:05:00Z"` | `'2026-06-12T09:05:00Z'::timestamptz` |
| `INTEGER` (auto-inc) | `"154723"` | `154723::bigint` |
| `VARCHAR` | `"LAST_PROCESSED_ID_XYZ"` | Direct comparison |
| `ObjectID` (MongoDB) | `"6658a1b2c3d4e5f6a7b8c9d0"` | Special handling |

---

## 4. `staging` Schema (Raw Landing Zone)

### 4.1 `staging.<source>_<table>_raw`

One raw table per source table. Created automatically on first pipeline run.

```sql
-- Auto-generated DDL pattern:
CREATE TABLE staging.prod_mysql_orders_raw (
    _arus_id         BIGSERIAL PRIMARY KEY,
    _arus_run_id     UUID         NOT NULL,          -- FK to run_history
    _arus_extracted  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    _arus_loaded     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    _data            JSONB        NOT NULL,           -- full source row as JSONB
    _hash            VARCHAR(64),                     -- SHA-256 for dedup
    _error           TEXT                              -- NULL if OK, populated by DLQ
);

CREATE INDEX idx_orders_raw_run ON staging.prod_mysql_orders_raw(_arus_run_id);
CREATE INDEX idx_orders_raw_hash ON staging.prod_mysql_orders_raw(_hash);
```

**Why JSONB for raw?**
- Schema-agnostic — source can add columns, raw tier never breaks
- Fast ingest — no column mapping needed at write time
- Replay capability — re-process any raw batch into normalized
- Lightweight — no schema change = no ALTER TABLE on the hot path

### 4.2 `staging._dead_letters`

Failed rows that couldn't be loaded into normalized zone.

```sql
CREATE TABLE staging._dead_letters (
    id              BIGSERIAL PRIMARY KEY,
    pipeline_id     UUID         NOT NULL,
    run_id          UUID         NOT NULL,
    source_table    VARCHAR(255) NOT NULL,
    raw_data        JSONB        NOT NULL,
    error_message   TEXT         NOT NULL,
    error_type      VARCHAR(100),           -- e.g. "TYPE_MISMATCH", "NULL_CONSTRAINT", "PK_DUPLICATE"
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    reprocessed     BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_dead_letters_pipeline ON staging._dead_letters(pipeline_id);
CREATE INDEX idx_dead_letters_unprocessed ON staging._dead_letters(reprocessed) WHERE reprocessed = FALSE;
```

---

## 5. `analytics` Schema (Normalized Zone)

### 5.1 `analytics.<table>`

Typed, normalized tables ready for BI/analytics consumption.

```sql
-- Auto-generated DDL based on source schema:
CREATE TABLE analytics.orders (
    -- Source columns with proper types:
    id            BIGINT        PRIMARY KEY,
    user_id       BIGINT        NOT NULL,
    total         DECIMAL(12,2) NOT NULL,
    status        VARCHAR(50)   NOT NULL,
    created_at    TIMESTAMPTZ   NOT NULL,
    updated_at    TIMESTAMPTZ,

    -- Arus metadata columns:
    _arus_run_id      UUID         NOT NULL,
    _arus_synced_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    _arus_version     INTEGER      NOT NULL DEFAULT 1  -- incremented on schema drift
);

CREATE INDEX idx_orders_synced ON analytics.orders(_arus_synced_at);
```

**Type Mapping (Source → PostgreSQL):**

| Source Type | PostgreSQL Type |
|-------------|-----------------|
| `INT` / `INTEGER` | `INTEGER` |
| `BIGINT` / `SERIAL` | `BIGINT` |
| `SMALLINT` | `SMALLINT` |
| `DECIMAL(p,s)` / `NUMERIC(p,s)` | `DECIMAL(p,s)` |
| `FLOAT` / `DOUBLE` | `DOUBLE PRECISION` |
| `VARCHAR(n)` / `CHAR(n)` | `VARCHAR(n)` |
| `TEXT` / `LONGTEXT` | `TEXT` |
| `BOOLEAN` / `TINYINT(1)` | `BOOLEAN` |
| `DATE` | `DATE` |
| `DATETIME` / `TIMESTAMP` | `TIMESTAMPTZ` |
| `JSON` / `JSONB` | `JSONB` |
| `BLOB` / `BINARY` | `BYTEA` |
| `ENUM('a','b')` | `VARCHAR(255)` + CHECK |
| `UUID` | `UUID` |
| Unmapped / Unknown | `TEXT` (fallback) |

---

## 6. `arus_run_logs` Schema (Run History)

### 6.1 `arus_run_logs.runs`

One row per pipeline execution.

```sql
CREATE TABLE arus_run_logs.runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID         NOT NULL REFERENCES arus_config.pipelines(id) ON DELETE CASCADE,
    status          VARCHAR(20)  NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running', 'success', 'failed', 'cancelled')),
    started_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER,
    trigger_type    VARCHAR(20)  NOT NULL DEFAULT 'scheduled'
                        CHECK (trigger_type IN ('scheduled', 'manual', 'backfill')),
    config_override JSONB,           -- if triggered with custom params
    error_message   TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_runs_pipeline ON arus_run_logs.runs(pipeline_id);
CREATE INDEX idx_runs_status ON arus_run_logs.runs(status);
CREATE INDEX idx_runs_started ON arus_run_logs.runs(started_at DESC);
CREATE INDEX idx_runs_cleanup ON arus_run_logs.runs(started_at) WHERE status IN ('success', 'failed', 'cancelled');
-- Cleanup: DELETE FROM arus_run_logs.runs WHERE started_at < NOW() - INTERVAL '90 days'
-- (Runs older than 90 days are archived or purged)
```

### 6.2 `arus_run_logs.run_table_stats`

Per-table stats within a run.

```sql
CREATE TABLE arus_run_logs.run_table_stats (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id               UUID         NOT NULL REFERENCES arus_run_logs.runs(id) ON DELETE CASCADE,
    table_name           VARCHAR(255) NOT NULL,
    rows_extracted       INTEGER      NOT NULL DEFAULT 0,
    rows_loaded_raw      INTEGER      NOT NULL DEFAULT 0,
    rows_loaded_analytics INTEGER     NOT NULL DEFAULT 0,
    rows_failed          INTEGER      NOT NULL DEFAULT 0,
    watermark_before     TEXT,
    watermark_after      TEXT,
    duration_ms          INTEGER      NOT NULL DEFAULT 0,
    error_message        TEXT,

    UNIQUE(run_id, table_name)
);

CREATE INDEX idx_run_stats_run ON arus_run_logs.run_table_stats(run_id);
```

### 6.3 `arus_run_logs.run_logs`

Individual log lines for each run.

```sql
CREATE TABLE arus_run_logs.run_logs (
    id          BIGSERIAL PRIMARY KEY,
    run_id      UUID         NOT NULL REFERENCES arus_run_logs.runs(id) ON DELETE CASCADE,
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    level       VARCHAR(10)  NOT NULL DEFAULT 'INFO'
                    CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR')),
    logger      VARCHAR(100) NOT NULL DEFAULT 'arus',
    message     TEXT         NOT NULL
);

CREATE INDEX idx_run_logs_run ON arus_run_logs.run_logs(run_id, id);
-- Auto-cleanup: DELETE FROM arus_run_logs.run_logs WHERE timestamp < NOW() - INTERVAL '30 days'
```

---

## 7. Schema Drift Handling

When a new column is detected in the source table:

```sql
-- Phase 1: Raw zone (always safe, JSONB is flexible)
-- No change needed — new column is already in _data JSONB.

-- Phase 2: Analytics zone — auto-ALTER
ALTER TABLE analytics.orders
    ADD COLUMN IF NOT EXISTS new_column VARCHAR(255);

-- Track schema version
INSERT INTO arus_config.schema_versions (table_name, version, columns, applied_at)
VALUES ('analytics.orders', 2, '["id","user_id","total","status","created_at","updated_at","new_column"]', NOW());
```

### 7.1 `arus_config.schema_versions`

```sql
CREATE TABLE arus_config.schema_versions (
    id          BIGSERIAL PRIMARY KEY,
    table_name  VARCHAR(255) NOT NULL,
    version     INTEGER      NOT NULL,
    columns     JSONB        NOT NULL,       -- ["col1", "col2", ...]
    applied_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    UNIQUE(table_name, version)
);
```

---

## 8. Entity Relationship Summary

```
arus_config.users          ──┐
                              │
arus_config.sources ──────┐  │
     │                    │  │
     ├── arus_config.pipelines ──── arus_config.pipeline_tables
     │         │                          │
     │         ├── arus_state.watermarks  │
     │         ├── arus_run_logs.runs     │
     │         │       └── run_table_stats│
     │         │       └── run_logs       │
     │         └── arus_config.destinations
     │
     └── staging.<source>_<table>_raw
     └── staging._dead_letters
     └── analytics.<table>
```

---

## 9. Data Retention & Cleanup

| Table | Retention | Cleanup Strategy |
|-------|-----------|------------------|
| `arus_run_logs.runs` | 90 days | Periodic DELETE via APScheduler |
| `arus_run_logs.run_logs` | 30 days | Periodic DELETE, older than logs in retained runs |
| `arus_run_logs.run_table_stats` | 90 days | Cascade delete with runs |
| `staging._dead_letters` | Indefinite | Manual review + reprocess |
| `staging.*_raw` | Indefinite | Re-process source of truth |
| `analytics.*` | Indefinite | Primary data product |
| `arus_state.watermarks` | Indefinite | Current state only |

**Cleanup job (APScheduler, runs daily at 02:00):**
```sql
DELETE FROM arus_run_logs.runs WHERE started_at < NOW() - INTERVAL '90 days';
DELETE FROM arus_run_logs.run_logs WHERE timestamp < NOW() - INTERVAL '30 days';
-- run_table_stats cascade-deleted with runs
```

---

## 10. Indexing Strategy

| Table | Index | Purpose |
|-------|-------|---------|
| `runs` | `(pipeline_id, started_at DESC)` | Dashboard recent runs |
| `runs` | `(started_at) WHERE status <> 'running'` | Cleanup queries |
| `run_logs` | `(run_id, id)` | Log retrieval per run |
| `watermarks` | `(pipeline_id)` | State lookup per pipeline run |
| `pipeline_tables` | `(pipeline_id, enabled)` | Active tables per pipeline |
| `dead_letters` | `(reprocessed) WHERE reprocessed = FALSE` | Unprocessed failures |
| `staging.*_raw` | `(_hash)` | Dedup check |

---

*End of Data Model — Arus v1.0*
