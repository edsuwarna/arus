# Arus — Product Requirements Document

> **Version:** 1.0
> **Status:** 🔴 Draft
> **Last Updated:** June 2026

---

## 1. Executive Summary

Arus is a lightweight CDC & ETL framework purpose-built for teams running on VPS-class infrastructure (no Kubernetes). It ingests data from MySQL, MariaDB, and PostgreSQL sources, applies transformations, and lands them into a PostgreSQL data warehouse — with a visual DAG interface for monitoring and troubleshooting.

Unlike Airbyte (requires Kube) or Debezium (resource-heavy), Arus uses watermark-based incremental extraction and runs on a single Docker host. It provides data engineers with a web dashboard to observe pipeline health, inspect runs, and manage schedules without SSH access.

**Tagline:** *Data flows without the cluster.*

---

## 2. Problem Statement

### 2.1 The Gap

| Need | Existing Solutions | Problem |
|------|-------------------|---------|
| CDC from MySQL/MariaDB/PG → Warehouse | Airbyte, Debezium, Fivetran | Airbyte needs Kubernetes, Debezium needs Kafka cluster, Fivetran is SaaS ($) |
| Visual DAG / pipeline monitoring | Airflow, Dagster | Airflow is heavy for small teams; custom UI is lighter |
| Lightweight, self-hosted | Custom scripts | No visibility, no retry, no watermark tracking — fragile |
| Team-friendly (not just one person's script) | In-house solution | Data engineers need UI, not just a cron job |

### 2.2 Who Feels This

- **Data Engineers** who manage ETL pipelines but don't have dedicated infra team
- **Startups / SMBs** running on 1-3 VPS, no Kubernetes budget
- **Teams transitioning from manual scripts** to a proper pipeline framework

---

## 3. Target Personas

### 3.1 Data Engineer (Primary)

| Aspek | Detail |
|-------|--------|
| **Role** | Data Engineer / Analytics Engineer |
| **Goal** | Ingest source data reliably into warehouse, monitor pipelines, troubleshoot failures |
| **Pain** | Managing cron scripts per table, no visibility when pipeline breaks, no retry logic |
| **Sees** | DAG visualizer, run history, logs, row counts, watermark state |

### 3.2 Analytics / BI Persona (Secondary)

| Aspek | Detail |
|-------|--------|
| **Role** | Data Analyst |
| **Goal** | Consume fresh data in warehouse for dashboards/reports |
| **Pain** | Didn't know pipeline was broken until dashboard looked wrong |
| **Sees** | Data freshness status, pipeline health (read-only) |

---

## 4. Product Overview

### 4.1 Vision

A self-hosted CDC & ETL platform that any team can run on a single VPS — no Kubernetes, no Kafka, no six-figure SaaS bill. Data engineers get visual pipeline observability, automated retry, and schema drift detection out of the box.

### 4.2 Success Metrics

| Metric | Target |
|--------|--------|
| Time to add new source table | < 30 minutes (write asset + config) |
| Pipeline uptime | > 99% (auto-retry handles transient failures) |
| Data freshness latency | < 5 minutes from source commit → warehouse |
| Setup time for new team | < 2 hours (docker compose up) |

### 4.3 Key Differentiators

| vs Airbyte | vs Debezium | vs Custom Script |
|-----------|-------------|-----------------|
| No Kube needed | No Kafka needed | Built-in DAG UI |
| 1 docker-compose.yml | 1 docker-compose.yml | Watermark tracking |
| Python-native connectors | Python-native connectors | Auto-retry + alerting |
| Fraction of the RAM | Fraction of the RAM | Schema drift detection |

---

## 5. Feature Requirements

### 5.1 Source Connector Framework (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| F-01 | Base `Source` class with `extract()` interface — implementers return iterator of dict batches | P1 |
| F-02 | MySQL source connector: incremental via `updated_at` watermark, full refresh, batch configurable | P1 |
| F-03 | MariaDB source connector: same pattern as MySQL (compatible driver) | P1 |
| F-04 | PostgreSQL source connector: same pattern, supports `pgoutput` logical replication slot (future) | P1 |
| F-05 | Column type mapping: auto-map source types → PostgreSQL types | P1 |
| F-06 | Connection config via environment variables (not hardcoded) | P1 |

### 5.2 Warehouse Destination (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| F-07 | Raw landing zone: `staging.<source>_<table>_raw` — JSONB + metadata columns | P1 |
| F-08 | Normalized zone: `analytics.<table>` — typed columns matching source schema | P1 |
| F-09 | Auto-create tables in warehouse on first run | P1 |
| F-10 | Idempotent loading: upsert or replace-window to avoid duplicates | P1 |
| F-11 | Schema drift detection: detect new columns in source, auto-ALTER warehouse | P2 |

### 5.3 Watermark / State Management (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| F-12 | `arus_state` table in warehouse: tracks source_name, table_name, watermark_col, watermark_value, row_count, updated_at | P1 |
| F-13 | Incremental: each run starts from last watermark | P1 |
| F-14 | Full refresh flag: `--full-refresh` resets watermark | P2 |
| F-15 | Manual backfill: specify `--backfill-from=2025-01-01` | P2 |

### 5.4 Orchestration & Scheduling (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| F-16 | `Pipeline` class: schedule, source, destination, list of tables — managed via API/UI | P1 |
| F-17 | Schedule per pipeline: cron expression via APScheduler | P1 |
| F-18 | Pipeline dependencies: if `orders` depends on `customers`, enforce order | P2 |
| F-19 | Manual trigger: via UI button or API — trigger pipeline with config override | P1 |

### 5.5 Error Handling & Resilience (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| F-20 | Retry with exponential backoff (3 attempts) via `tenacity` | P1 |
| F-21 | Dead letter queue: rows that fail load are saved to `staging._dead_letters` for manual reprocess | P2 |
| F-22 | Pipeline timeout: configurable max runtime per run | P1 |
| F-23 | Alert on failure: webhook / Telegram notification | P2 |

### 5.6 Data Quality (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| F-24 | Row count check: compare source rows extracted vs rows loaded — warn if mismatch > threshold | P2 |
| F-25 | Null check on required columns | P2 |
| F-26 | Unique key violation tracking — log but don't fail pipeline (configurable) | P2 |
| F-27 | Data quality checks: row count validation, null checks — visible in pipeline run logs | P2 |

### 5.7 Monitoring & Observability (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| F-28 | Arus DAG View: interactive asset graph of all pipelines with status (success/fail/running) | P1 |
| F-29 | Run history: duration, row counts, error messages per run | P1 |
| F-30 | Logs per pipeline run: expandable in UI — no SSH needed | P1 |
| F-31 | Pipeline state overview: watermark values, last run, row count per source table | P1 |

### 5.8 CLI Utilities (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| F-32 | `arusctl status` — quick overview of all pipelines | P2 |
| F-33 | `arusctl reset <source> <table>` — reset watermark | P2 |
| F-34 | `arusctl backfill <source> <table> --from=2025-01-01` | P2 |

---

## 6. Non-Functional Requirements

### 6.1 Performance

| Requirement | Target |
|-------------|--------|
| CDC batch latency | < 1 minute from source commit → warehouse for 100K row tables |
| Batch size | Configurable (default 10,000 rows per batch) |
| Concurrent pipelines | 5 pipelines simultaneously on 2-core / 4GB RAM |
| Scheduler overhead | < 100MB RAM idle |

### 6.2 Resource Constraints

- **Server:** Single VPS, 2-4 CPU, 4-8GB RAM, 50GB disk
- **PostgreSQL:** Single instance for warehouse + config + state (separate schemas)
- **No Kubernetes, No Kafka, No Redis**

### 6.3 Security

| Requirement | Detail |
|-------------|--------|
| Credential management | Database passwords via environment variables only — never in config files committed to git |
| Arus Console access | Behind reverse proxy (nginx / Cloudflare Tunnel) with basic auth or SSO |
| Network isolation | CDC reads are SELECT-only — no write access to sources |

### 6.4 Reliability

| Requirement | Detail |
|-------------|--------|
| Watermark durability | Stored in PostgreSQL, not in-memory — survives restarts |
| Run persistence | Run history stored in PostgreSQL — survives container restart |
| Graceful shutdown | In-flight pipeline completes current batch before aborting |

---

## 7. Technical Architecture

### 7.1 High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host                            │
│                                                          │
│  ┌──────────────────┐    ┌─────────────────────┐        │
│  │   Arus Console   │    │   Backend API       │        │
│  │   :8080           │    │   :8081              │       │
│  │   (SPA: HTML/    │    │   (FastAPI +        │        │
│  │    CSS/JS)       │    │    Python Core)     │        │
│  │   Auth: JWT       │    │                    │        │
│  └────────┬─────────┘    └────────┬────────────┘        │
│           │                       │                       │
│           ▼                       ▼                       │
│  ┌──────────────────────────────────────────────────┐    │
│  │            PostgreSQL (single instance)           │   │
│  │  ├─ arus_config.users     (auth)                   │  │
│  │  ├─ arus_config.sources   (source DB configs)      │  │
│  │  ├─ arus_config.pipelines (pipeline configs)       │  │
│  │  ├─ arus_state            (watermarks)             │  │
│  │  ├─ staging.*             (raw landing zone)       │  │
│  │  └─ analytics.*           (normalized tables)      │  │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Data Flow

```
Source DB → [Batch SELECT with watermark] → Python dict[]
   → [Column type mapping] → [Raw JSONB to staging.*_raw]
   → [Extract typed columns] → [Normalize] → [Upsert to analytics.*]
   → [Update arus_state watermark]
```

### 7.3 Component Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend API** | Python 3.11+ (FastAPI) | REST API for UI + data pipeline execution |
| **Orchestration** | Python scheduler (APScheduler / Celery Beat) | Lightweight scheduling without Dagster overhead |
| **Source connectors** | psycopg2, pymysql | Mature, well-tested drivers |
| **Warehouse** | PostgreSQL 15+ | Single DB engine for warehouse + config + state |
| **Infrastructure** | Docker Compose | Single host, no Kube |
| **Frontend** | Vanilla HTML/CSS/JS (SPA) | Zero build step, no npm, lightweight |
| **Retry** | tenacity | Battle-tested Python retry library |

---

## 8. UI/UX Design Guidelines

### 8.1 Arus Console (Custom SPA)

Arus Console is a single-page application (HTML/CSS/JS) that serves as the primary interface for data engineers. It runs as a standalone web app alongside the backend API in the same Docker network.

#### 8.1.1 Design System

| Element | Value |
|---------|-------|
| **Theme** | Dark mode (premium) — deep black (#0b0d11) background with emerald (#10b981) accents |
| **Typography** | Inter, system sans-serif |
| **Layout** | Fixed sidebar (240px) + scrollable content area |
| **Radius** | Cards: 10px, Buttons/Inputs: 6px |
| **Shadow** | Subtle card shadows, elevated modal shadows |
| **Status colors** | Emerald (success), Blue (running/running), Amber (stale/warning), Red (failed), Gray (disabled) |

#### 8.1.2 Screens

| Screen | Purpose |
|--------|---------|
| **Login** | Email + password authentication with persistent session |
| **Dashboard** | Pipeline health overview — stat cards (active sources, pipelines, rows synced, failures), 7-day sync performance chart, recent runs list, data sources overview table |
| **Sources** | List of registered source databases with auto-discovered table counts — add/edit/rescan sources. Modal for adding new source: type, connection string, sync method (auto-detect/incremental/full refresh), table filter patterns. Per-source table list with checkboxes to enable/disable individual tables |
| **Destinations** | List of configured data destinations (warehouse, data lake) with sync stats |
| **Pipelines** | Per-source pipeline cards with status indicator, throughput (rows/h), error count, avg latency. Pause/resume individual pipelines |
| **Pipeline Detail / Run History** | Data flow visualization (source → CDC → destination), pipeline meta stats (status, schedule, total rows, last sync), per-table run history table with timing and lag |
| **DAG View** | Interactive asset graph with three layers (Source → Staging → Analytics). Color-coded node statuses, zoom/pan controls, dependency edges. Click a node to see upstream/downstream assets and latest run history. Pipeline summary cards at bottom |
| **Settings** | General config (pipeline name prefix, default sync interval), toggle switches for auto-discover, schema drift detection, notifications. User management table with role assignment |

#### 8.1.3 Mockup Screenshots

> All mockups are in `sketches/arus-polished.html` — an interactive HTML prototype.

| Screen | Screenshot |
|--------|-----------|
| Login | `sketches/arus-login.png` |
| Dashboard | `sketches/arus-dashboard.png` |
| Sources | `sketches/arus-sources.png` |
| Destinations | `sketches/arus-destinations.png` |
| Pipelines | `sketches/arus-pipelines.png` |
| Pipeline Detail | `sketches/arus-pipeline-detail.png` |
| DAG View (graph) | `sketches/arus-dag-top.png` |
| DAG View (detail panel) | `sketches/arus-dag-bottom.png` |
| Settings | `sketches/arus-settings.png` |
| Add Source Modal | `sketches/arus-add-source.png` |

#### 8.1.4 Sidebar Navigation

```
Overview
├── Dashboard
Connect
├── Sources
├── Destinations
Orchestrate
├── Pipelines
├── Run History
├── DAG View
Configure
├── Settings
```

#### 8.1.5 Source & Pipeline Management Flow

```
[Add Source] → form: type, name, connection string, sync method, table filters
    ↓
[Test Connection] → cek koneksi ke source DB
    ↓
[Auto-discover] → system scans all tables in the source DB
    ↓
[Auto-detect sync mode] → per-table: incremental by updated_at (preferred) | full refresh | disabled
    ↓
[Enable/Disable Tables] → user toggles checkboxes for selected tables
    ↓
[Save] → config stored in `arus_config.*` tables
    ↓
[Auto-create Pipeline] → one pipeline per source → syncs all enabled tables on schedule
```

Data engineer **tidak perlu** SSH, CLI, or edit file config. Satu source register = semua table auto-detect.

#### 8.1.6 DAG / Asset Graph

The DAG View visualizes the pipeline as a three-layer asset graph:

```
SOURCE LAYER    |    STAGING LAYER    |    ANALYTICS LAYER
─────────────────┬──────────────────────┬───────────────────
users ───────────┼──> stg_users ───────┼──> analytics.users
transactions ────┼──> stg_transactions ┼──> analytics.transactions
orders ──────────┼──> stg_orders ──────┼──> analytics.orders
products ────────┼──> stg_products ────┼──> analytics.products
```

- **Color-coded nodes**: 🟢 Success / 🔵 Running / 🟠 Stale / 🔴 Failed / ⚪ Not Started
- **Dependency edges**: Dashed lines show upstream → downstream relationships
- **Click node**: Opens detail panel with upstream/downstream assets + latest run history
- **Zoom/Pan**: Standard graph navigation controls
- **Pipeline selector**: Dropdown to switch between all pipelines or a specific one

### 8.2 Authentication

Arus Console has built-in auth — not delegated to reverse proxy. All UI screens require authentication.

---

## 9. Implementation Roadmap

> **Connector roadmap detail:** See [`prd/connector-roadmap.md`](./connector-roadmap.md) for full source/destination priority matrix, sync modes, and implementation effort estimates.

### Phase 1 — Foundation (Week 1-2)

| Deliverable | Detail |
|-------------|--------|
| ✅ Project skeleton | Project structure, docker-compose.yml, requirements.txt |
| ✅ Base Source class | `extract()` interface, batch iterator |
| ✅ MySQL source connector | Watermark-based incremental SELECT |
| ✅ MariaDB source connector | Same pattern |
| ✅ PostgreSQL source connector | Same pattern |
| ✅ StateManager | Watermark CRUD in `arus_state` table |
| ✅ SchemaManager | Auto-create raw + normalized tables, type mapping |
| ✅ Arus Console (MVP) | SPA prototype based on `sketches/arus-polished.html` — Dashboard, Sources, Pipelines, DAG View |
| ✅ Auth | Login page, session JWT, `arus_config.users`, admin + viewer roles |
| ✅ First running pipeline | MariaDB `orders` → warehouse `analytics.orders` |
| ✅ DAG visualization | Three-layer asset graph (Source → Staging → Analytics) with status colors |
| ✅ Connector core | MySQL + MariaDB + PostgreSQL sources, PostgreSQL destination — see [`connector-roadmap.md`](./connector-roadmap.md#2-source-connector-priority-matrix) |

### Phase 2 — Reliability & Pipeline Management (Week 3-4)

| Deliverable | Detail |
|-------------|--------|
| Retry + exponential backoff | tenacity wrapper around extract/load |
| Dead letter queue | Failed rows saved to `staging._dead_letters` |
| Data quality checks | Row count validation, null checks |
| Schema drift detection | Auto-ALTER on new columns |
| Pipeline dependencies | `orders` after `customers` |
| Arus Console: Run History | Built-in run history UI with logs |
| Arus Console: Pipelines CRUD | Schedule, activate/deactivate, manual trigger |
| Alert integration | Telegram webhook on pipeline failure |
| Extended sources | MongoDB, SQL Server, BigQuery — see [`connector-roadmap.md`](./connector-roadmap.md) |
| Extended destinations | ClickHouse, MySQL (dest), BigQuery — see [`connector-roadmap.md`](./connector-roadmap.md) |

### Phase 3 — Production Hardening (Week 5-6)

| Deliverable | Detail |
|-------------|--------|
| CLI tools | `arusctl` for setup, user creation, troubleshooting |
| Backfill from UI | Date-range backfill via UI or API |
| Full refresh | `--full-refresh` flag |
| Multi-environment | Dev / staging / prod config separation |
| Secret management | Encrypted source passwords at rest |
| Performance tuning | Batch size optimization, connection pooling |
| Documentation | README, setup guide, connector authoring guide |
| API Connector Framework | Generic REST API connector + Stripe, Shopify, Google Analytics — see [`connector-roadmap.md`](./connector-roadmap.md) |
| Advanced destinations | Parquet/CSV export, Webhook, SQLite — see [`connector-roadmap.md`](./connector-roadmap.md) |

---

## 10. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Orchestrator** | Python scheduler (APScheduler) | Lighter than Airflow or Dagster. Runs in-process with the API, no separate daemon needed. Single-process mode for VPS |
| **CDC method** | Watermark-based (not binlog/WAL) | No Kafka needed, works with read-replica, minimal DB overhead. Future: optional logical replication |
| **Storage** | Single PostgreSQL | Warehouse + Arus config + state on one instance. Separated by schema/database. Saves infra complexity |
| **Raw + Normalized pattern** | Two-zone warehouse | Raw for reprocessing/recovery, normalized for analytics. Standard data warehouse pattern |
| **JSONB for raw** | Staging stores source row as JSONB + metadata | Schema-agnostic landing — source can add columns without breaking raw ingest |
| **Config via UI (not files)** | Source/pipeline config stored in PostgreSQL `arus_config.*` tables | Data engineers manage everything from browser — no SSH, no file editing, no redeploy |
| **Auth built-in** | JWT session in Arus Console, not delegated to reverse proxy | Keeps auth portable — works behind Cloudflare Tunnel, nginx, or without reverse proxy |

---

## 11. Glossary

| Term | Definition |
|------|-----------|
| **CDC** | Change Data Capture — incremental extraction of changed rows |
| **Watermark** | A tracked value (usually timestamp or auto-increment ID) marking the last extracted position |
| **DAG** | Directed Acyclic Graph — visual representation of pipeline dependencies |
| **Raw Zone** | `staging.*_raw` — landing tables storing source data as JSONB + metadata |
| **Normalized Zone** | `analytics.*` — typed columns matching source schema, ready for analysis |
| **Auto-discover** | Feature that scans a source database and detects all tables, columns, and compatible sync modes |
| **Source Group** | Collection of source databases with the same type and connection pattern |

---

## 12. Appendix

### 12.1 Comparison: Arus vs Alternatives

| Feature | Arus | Airbyte OSS | Debezium | Custom Script |
|---------|------|-------------|----------|---------------|
| Kubernetes required | ❌ | ✅ | ❌ (but Kafka needed) | ❌ |
| DAG UI | ✅ (Custom DAG View) | ✅ (basic) | ❌ | ❌ |
| CDC method | Watermark | CDC + Watermark | Log-based (WAL/binlog) | Usually none |
| Setup time | 2 hours | 1-2 days | 3-5 days | 1 hour (minus UI) |
| RAM usage | ~500MB | ~2GB | ~3GB+ | ~100MB |
| Connector SDK | Python class | Python connector | Java connector | N/A |
| Schema drift | ✅ Auto | ✅ | ✅ | ❌ |

### 12.2 Related Documents

- https://github.com/edsuwarna/arus — Project repository
- `sketches/arus-polished.html` — Interactive UI prototype with all screens
- `prd/connector-roadmap.md` — Source & destination connector priority matrix, implementation details
- `prd/api-spec.md` — REST API contract between Arus Console and Backend (all endpoints, request/response shapes)
- `prd/data-model.md` — PostgreSQL schema design (arus_config, state, staging, analytics, run logs)

---

*End of PRD — Arus v1.0*
