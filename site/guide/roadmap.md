# Roadmap

Arus development status and planned features.

---

## Current Status: v0.1.0 (Alpha)

Arus is under active development. The current release covers the core ETL pipeline with basic reliability features.

---

## Phase 1 — Foundation ✅

The foundation layer — connectors, auth, and basic pipeline operations.

**Status: Complete**

- ✅ **Source Connectors**: MySQL, MariaDB, PostgreSQL, MongoDB
- ✅ **Destination Connectors**: PostgreSQL, MySQL, ClickHouse
- ✅ **Watermark-based Incremental Sync** with batch processing
- ✅ **Full Refresh & Backfill** support
- ✅ **Pipeline Scheduling** via APScheduler (cron expressions)
- ✅ **Web Console** — Dashboard, DAG View, Pipeline Management
- ✅ **JWT Authentication** — Admin/Editor/Viewer roles
- ✅ **Source/Destination CRUD** — manage connections via Console or API
- ✅ **Schema Discovery** — auto-detect tables, columns, sync modes

---

## Phase 2 — Reliability ✅

Production hardening — error handling, data quality, notifications, and schema management.

**Status: Complete**

- ✅ **Retry with Exponential Backoff** (tenacity)
- ✅ **Dead Letter Queue** for failed rows
- ✅ **Data Quality Checks** (row count validation, null checks)
- ✅ **Schema Drift Detection** with auto-ALTER support
- ✅ **Soft-Delete Reconciliation** — track and propagate deletions
- ✅ **Pipeline Dependency Resolution** — chain pipelines
- ✅ **Transform Engine** — built-in steps + Python script support
- ✅ **Notification Targets** — Telegram, Discord, Slack
- ✅ **Pipeline-Notification Linking** — per-pipeline event selection
- ✅ **Pull-based Images** — deploy from `ghcr.io/edsuwarna`
- ✅ **Documentation** — architecture, guides, API reference, deployment

---

## Phase 3 — Production Hardening 🔄

Tools and features for day-2 operations, scaling, and advanced use cases.

**Status: In Progress**

| Feature | Status | Description |
|---------|--------|-------------|
| **CLI Tools (`arusctl`)** | 🔄 In Progress | Command-line interface for pipeline management |
| **Backfill UI** | 🔄 In Progress | Date picker and progress tracking in Console |
| **Secrets Management** | 🔄 In Progress | Integration with external vaults (HashiCorp Vault, AWS Secrets Manager) |
| **Multi-Environment Support** | 📋 Planned | Dev/staging/prod config separation |
| **Enhanced Monitoring** | 📋 Planned | Built-in metrics endpoint, Prometheus integration |
| **Pipeline Templates** | 📋 Planned | Reusable pipeline configurations |
| **S3 Destination** | 📋 Planned | Parquet/CSV export to AWS S3 / MinIO |
| **Batch Operations UI** | 📋 Planned | Pause/resume/trigger multiple pipelines at once |
| **Run Log Retention Policy** | 📋 Planned | Configurable log retention and cleanup |

---

## Phase 4 — Advanced Features

Vision for future releases.

| Feature | Description |
|---------|-------------|
| **Log-based CDC** | Optional Debezium-style change data capture via WAL/binlog parsing |
| **Kafka Destination** | Stream synced data to Kafka topics |
| **Webhook Source** | Ingest data via HTTP webhooks |
| **Dashboard Charts** | Built-in visualization of synced data (charts, tables) |
| **Schema Mapping UI** | Visual column mapping between source and destination |
| **Role-Based Dashboard** | Per-role custom dashboard views |
| **Alert History** | View and manage past alert events |
| **SMTP/Email Notifications** | Email-based notification targets |
| **API Rate Limiting** | Configurable per-endpoint rate limits |
| **Audit Logging** | Track all configuration changes |
| **Tableau / Metabase Integration** | Direct query federation for BI tools |
| **Cloud Warehouse Destinations** | Snowflake, BigQuery, Redshift support |

---

## Feature Requests

Have an idea or use case not listed here? Open a feature request or contribute to the discussion.

The roadmap is driven by real-world usage and community needs. Priorities may shift based on feedback.
