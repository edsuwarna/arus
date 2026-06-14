# Arus — Data Pipeline Platform

> _Data flows without the cluster._

Arus is a lightweight, self-hosted **CDC & ETL framework** purpose-built for teams running on VPS-class infrastructure (no Kubernetes). It ingests data from MySQL, MariaDB, PostgreSQL, and MongoDB sources, applies transformations, and lands them into a PostgreSQL, MySQL, or ClickHouse data warehouse — with a visual DAG interface for monitoring and troubleshooting.

---

## Features

### Connector Framework

Pluggable source and destination connectors based on abstract base classes.

| Feature | Description | Documentation |
|---------|-------------|---------------|
| **Source Connectors** | MySQL, MariaDB, PostgreSQL, MongoDB — watermark-based batch extraction | [Connectors Guide →](/guide/connectors) |
| **Destination Connectors** | PostgreSQL, MySQL, ClickHouse — raw + normalized load modes | [Connectors Guide →](/guide/connectors) |
| **Auto-discover Tables** | Scan source databases, detect tables, columns, and sync modes automatically | [Console Guide →](/guide/console) |
| **Column Type Mapping** | Auto-map source types to destination types (e.g., MySQL `TINYINT` → PostgreSQL `BOOLEAN`) | [Connectors Guide →](/guide/connectors) |
| **Custom Connectors** | Implement `BaseSource` / `BaseDestination` for any database | [Development Guide →](/guide/development) |

### Pipeline Orchestration

Core engine for scheduling, executing, and monitoring data syncs.

| Feature | Description | Documentation |
|---------|-------------|---------------|
| **Incremental Sync** | Watermark-based batch CDC using timestamp columns (`updated_at`, `created_at`) | [Pipelines →](/guide/pipelines) |
| **Full Refresh** | Truncate and reload entire tables on demand or on schedule | [Pipelines →](/guide/pipelines) |
| **Backfill** | Re-sync historical data from a specific date | [Pipelines →](/guide/pipelines) |
| **Scheduling** | APScheduler cron-based with configurable intervals (default: every 5 minutes) | [Pipelines →](/guide/pipelines) |
| **Pipeline Dependencies** | Chain pipelines — B waits for A's successful run | [Pipelines →](/guide/pipelines) |
| **Load Modes** | Direct (source → analytics) or Raw → Normalize (staging JSONB → analytics) | [Pipelines →](/guide/pipelines) |

### Transform Engine

Process data between extraction and loading.

| Feature | Description | Documentation |
|---------|-------------|---------------|
| **Built-in Steps** | Rename, remove, compute, filter, map values, type cast, concat fields | [Pipelines →](/guide/pipelines) |
| **Python Scripts** | Custom `transform(row)` functions per pipeline | [Pipelines →](/guide/pipelines) |
| **Re-orderable Steps** | Drag-and-drop step ordering in the Console UI | [Console Guide →](/guide/console) |

### Reliability & Quality

Production-grade error handling and data validation.

| Feature | Description | Documentation |
|---------|-------------|---------------|
| **Retry with Backoff** | Exponential backoff via `tenacity` (default: 3 attempts, 2s → 16s max) | [Pipelines →](/guide/pipelines) |
| **Dead Letter Queue** | Failed rows stored in `staging._dead_letters` for review and reprocessing | [Pipelines →](/guide/pipelines) |
| **Data Quality Checks** | Row count validation + null checks on NOT NULL columns (threshold: 5%) | [Pipelines →](/guide/pipelines) |
| **Schema Drift Detection** | Detect new columns in source, optionally auto-ALTER warehouse tables | [Pipelines →](/guide/pipelines) |
| **Soft-Delete Reconciliation** | Track `deleted_at` columns and propagate deletions to warehouse | [Pipelines →](/guide/pipelines) |

### Alerting & Notifications

Stay informed about pipeline health.

| Feature | Description | Documentation |
|---------|-------------|---------------|
| **Notification Targets** | Telegram, Discord, Slack — configurable per pipeline | [Pipelines →](/guide/pipelines) |
| **Alert Events** | Failure, success, dead letter, schema drift, quality breach | [Pipelines →](/guide/pipelines) |
| **Pipeline Linking** | Link multiple targets to a pipeline with specific event types | [Console Guide →](/guide/console) |

### Web Console

Browser-based management UI.

| Feature | Description | Documentation |
|---------|-------------|---------------|
| **Dashboard** | Stats cards, sync performance chart, recent runs feed, sources overview | [Console Guide →](/guide/console) |
| **Source Management** | Add, test, rescale, edit, delete source connections | [Console Guide →](/guide/console) |
| **Pipeline Management** | Create, configure, pause, resume, trigger pipelines | [Console Guide →](/guide/console) |
| **Pipeline Detail** | Run history, logs, transforms, dead letters, notifications per pipeline | [Console Guide →](/guide/console) |
| **DAG View** | Interactive SVG asset graph with zoom/pan and color-coded status | [Console Guide →](/guide/console) |
| **Run History** | Global view of all pipeline runs with filters and actions | [Console Guide →](/guide/console) |
| **User Management** | CRUD users with Admin/Editor/Viewer roles (admin only) | [Console Guide →](/guide/console) |
| **Settings** | Global runtime settings — schedule, retry, quality, notifications (admin only) | [Console Guide →](/guide/console) |

### Authentication & Security

| Feature | Description | Documentation |
|---------|-------------|---------------|
| **JWT Authentication** | Access token (15 min) + refresh token (7 days) | [Architecture →](/guide/architecture) |
| **Role-Based Access** | Admin, Editor, Viewer roles with granular permissions | [Architecture →](/guide/architecture) |
| **Password Hashing** | bcrypt via `passlib` | [Architecture →](/guide/architecture) |
| **Credential Encryption** | Fernet AES-128-CBC for stored source/destination passwords | [Security →](/guide/security) |
| **Rate Limiting** | Login: 10 attempts per 60 seconds per IP | [Security →](/guide/security) |

---

## Quick Comparison

| Feature | Arus | Airbyte OSS | Debezium | Custom Scripts |
|---------|------|-------------|----------|----------------|
| Infrastructure | Docker Compose (3 containers) | Kubernetes or Docker + workers | Kafka + Zookeeper + Connect | Anything |
| Setup time | ~2 minutes | 30-60 minutes | 1-2 hours | Varies |
| RAM idle | ~200MB | ~2GB | ~3GB+ | ~100MB |
| CDC method | Watermark-based batch | Watermark + log-based | Log-based (WAL/binlog) | Custom |
| Schema drift | ✅ Auto | ✅ Auto | ✅ | ❌ |
| Dead letter queue | ✅ | ✅ | ❌ | ❌ |
| DAG / Pipeline UI | ✅ Built-in | ✅ Basic | ❌ | ❌ |
| Transform engine | ✅ Built-in steps + Python | ✅ Basic | ❌ | ❌ |

---

## Getting Started

```bash
# Deploy Arus in under 2 minutes
docker compose up -d

# Access the console
open http://localhost:8082
```

**New to Arus?** Start with the [Quickstart Guide →](/guide/quickstart)

---

## Architecture at a Glance

```
                    Docker Host
                    ┌─────────────────────────────────────────┐
                    │  arus-console    arus-api               │
                    │  :8082 (nginx)   :8081 (FastAPI)        │
                    │       │               │                  │
                    │       └───────┬───────┘                  │
                    │               ▼                          │
                    │  arus-db (PostgreSQL)                    │
                    │  ├─ arus_config.*    (auth, sources,     │
                    │  │                   pipelines, settings)│
                    │  ├─ arus_state.*     (watermarks)        │
                    │  ├─ arus_run_logs.*  (run history)       │
                    │  ├─ staging.*        (raw landing zone)  │
                    │  └─ analytics.*      (normalized tables) │
                    └─────────────────────────────────────────┘
```

See the [Architecture Guide →](/guide/architecture) for a deep dive.

---

## Project Status

| Phase | Focus | Status |
|-------|-------|--------|
| **Phase 1** | Foundation — connectors, auth, console, core pipelines | ✅ Complete |
| **Phase 2** | Reliability — retry, DLQ, quality checks, schema drift, transforms, notifications | ✅ Complete |
| **Phase 3** | Production hardening — CLI, backfill UI, secrets, multi-env | 🔄 In Progress |
| **Phase 4** | Advanced — log-based CDC, cloud warehouses, BI integration | 📋 Planned |

See the [Roadmap →](/guide/roadmap) for details.
