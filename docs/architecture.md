# Architecture

Arus follows a **modular, service-oriented architecture** with clear separation of concerns. The system consists of three Docker services working together.

---

## System Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Network (arus-net)                     │
│                                                                      │
│  ┌──────────────────────┐        ┌──────────────────────────────┐   │
│  │   arus-console        │        │        arus-api              │   │
│  │   nginx:80            │        │   FastAPI :8081              │   │
│  │   │                   │        │                              │   │
│  │   SPA: HTML/CSS/JS    │───────▶│  ┌────────────────────────┐ │   │
│  │   (vanilla, no build) │ HTTP   │  │  Auth Module            │ │   │
│  └──────────────────────┘        │  │  Source Module          │ │   │
│                                   │  │  Destination Module     │ │   │
│  ┌──────────────────────┐        │  │  Pipeline Module        │ │   │
│  │   arus-db             │        │  │    - Executor           │ │   │
│  │   PostgreSQL 15       │◀───────│  │    - Scheduler          │ │   │
│  │                      │ SQL    │  │    - Dead Letter        │ │   │
│  │   ├─ arus_config     │        │  │    - Quality Checks     │ │   │
│  │   ├─ arus_state      │        │  │    - Deps               │ │   │
│  │   ├─ arus_run_logs   │        │  │  Connector Module       │ │   │
│  │   ├─ staging         │        │  │    - BaseSource         │ │   │
│  │   └─ analytics       │        │  │    - BaseDestination    │ │   │
│  └──────────────────────┘        │  │  Run Log Module         │ │   │
│                                   │  │  Dashboard Module       │ │   │
│                                   │  │  DAG Module             │ │   │
│                                   │  │  Transform Module       │ │   │
│                                   │  │  Notification Module    │ │   │
│                                   │  │  Settings Module        │ │   │
│                                   │  └────────────────────────┘ │   │
│                                   └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Layers

### 1. Backend API (`arus-api`)

**Framework**: Python 3.11+ / FastAPI
**Port**: 8081

The backend is organized into a **module-per-domain** structure:

```
arus/
├── main.py                    # FastAPI app, middleware, startup, routers
├── models.py                  # Central model imports for Alembic
├── modules/
│   ├── auth/                  # JWT authentication, user management
│   ├── connector/             # Source/destination connector framework
│   │   ├── base_source.py     # Abstract BaseSource class
│   │   ├── base_destination.py# Abstract BaseDestination class
│   │   ├── registry.py        # Connector plugin registry
│   │   ├── sources/           # MySQL, MariaDB, PostgreSQL, MongoDB
│   │   └── destinations/      # PostgreSQL, MySQL, ClickHouse
│   ├── pipeline/              # Pipeline orchestration
│   │   ├── executor.py        # Extract → transform → load → watermark
│   │   ├── scheduler.py       # APScheduler cron management
│   │   ├── dead_letter.py     # DLQ for failed rows
│   │   ├── quality.py         # Row count & null checks
│   │   └── deps.py            # Dependency resolution
│   ├── source/                # Source CRUD API
│   ├── destination/           # Destination CRUD API
│   ├── run_log/               # Run history & per-run logs
│   ├── dag/                   # DAG visualization data
│   ├── dashboard/             # Dashboard summary endpoints
│   ├── transform/             # Transform engine (built-in steps + scripts)
│   ├── notification/          # Notification targets (Telegram, Discord, Slack)
│   ├── settings/              # Runtime settings management
│   └── alert/                 # Telegram alert manager
├── shared/
│   ├── config.py              # Pydantic Settings (env-prefixed)
│   ├── crypto.py              # Fernet encryption for stored passwords
│   ├── types.py               # Column type mapping
│   ├── db/                    # SQLAlchemy engine, session, migrations
│   └── exceptions.py          # ArusError hierarchy
└── utils/
    ├── schema_manager.py      # Warehouse schema management
    └── state_manager.py       # Watermark state management
```

#### Module Pattern

Each module follows a consistent pattern:

```
module/
├── models.py       # SQLAlchemy ORM models
├── schemas.py      # Pydantic request/response schemas
├── repository.py   # Database access layer
├── service.py      # Business logic layer
├── router.py       # FastAPI route definitions
└── __init__.py
```

### 2. Web Console (`arus-console`)

**Technology**: Vanilla HTML/CSS/JS (zero build step, no npm)
**Server**: nginx serving static files
**Port**: 80 (exposed as 8082)

The console is a single-page application with hash-based routing:

```
console/
├── index.html               # Entry point
├── css/
│   ├── style.css            # Main stylesheet (dark theme)
│   └── mobile.css           # Responsive styles
└── js/
    ├── app.js               # SPA router, App singleton, toast/modal helpers
    ├── api.js               # Fetch wrapper with auto token refresh
    ├── components/
    │   └── sidebar.js       # Navigation sidebar
    └── pages/
        ├── login.js         # Login page
        ├── dashboard.js     # Dashboard with stats and charts
        ├── sources.js       # Source management
        ├── pipelines.js     # Pipelines, destinations, settings
        ├── pipeline-detail.js # Pipeline detail, run history, transforms
        ├── runs.js          # Global run history
        ├── dag.js           # DAG visualization
        ├── users.js         # User management (admin)
        └── notifications.js # Notification targets & linking
```

### 3. Database (`arus-db`)

**Technology**: PostgreSQL 15+
**Port**: 5432
**Schemas**:

| Schema | Purpose |
|---|---|
| `arus_config` | Auth users, sources, destinations, pipelines, settings |
| `arus_state` | Watermark tracking per pipeline table |
| `arus_run_logs` | Run history, per-table stats, log entries |
| `staging` | Raw landing zone (`*_raw` tables with JSONB data) |
| `analytics` | Normalized typed tables |

---

## Data Flow Detail

### Incremental Sync (Watermark-based)

```
1. Read last watermark from arus_state.watermarks
       │
2. Connect to source DB
       │
3. SELECT * FROM source_table
   WHERE watermark_col > last_watermark
   [AND deleted_at IS NULL]
   ORDER BY watermark_col
   LIMIT batch_size
       │
4. For each batch of rows:
       ├── [Optional: Apply transforms]
       ├── Insert raw JSONB into staging.*_raw (if load_mode=raw)
       ├── Insert typed columns into analytics.*
       └── Update watermark in arus_state
       │
5. [Optional] Soft-delete reconciliation
       │
6. Run data quality checks
       │
7. Update run_log with results
```

### Full Refresh Sync

```
1. Reset watermark (delete from arus_state)
       │
2. SELECT * FROM source_table
   [WHERE deleted_at IS NULL]
   LIMIT batch_size
       │
3. Truncate and reload destination tables
       │
4. Update run_log with results
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Orchestrator** | APScheduler (in-process) | Lighter than Airflow/Dagster. Runs in-process with API, no separate daemon. |
| **CDC method** | Watermark-based | No Kafka/binlog needed, works with read-replicas, minimal DB overhead. |
| **Storage** | Single PostgreSQL | Warehouse + config + state on one instance. Separated by schemas. |
| **Raw + Normalized** | Two-zone warehouse | Raw for reprocessing/recovery, normalized for analytics. |
| **JSONB for raw** | Schema-agnostic landing | Source can add columns without breaking raw ingest. |
| **Config via UI** | DB-stored config | Data engineers manage everything from browser — no SSH/file edits. |
| **Auth built-in** | JWT in FastAPI | Portable — works behind Cloudflare Tunnel, nginx, or standalone. |
| **Frontend** | Vanilla JS SPA | Zero build step, no npm, lightweight (< 2MB total). |

---

## Security Architecture

### Authentication Flow

```
Client                     API Server
  │                            │
  │── POST /api/auth/login ───▶│  Validate email + password
  │◀─── {access_token,         │  Generate JWT pair
  │      refresh_token}        │  access: 15 min, refresh: 7 days
  │                            │
  │── GET /api/sources ───────▶│  Authorization: Bearer <access_token>
  │◀─── sources[]             │  Verify JWT, extract role
  │                            │
  │── POST /api/auth/refresh ─▶│  X-Refresh-Token header
  │◀─── {new_access_token}    │  Verify refresh token, issue new pair
```

### Role-Based Access Control

| Role | Permissions |
|---|---|
| `viewer` | Read-only access to all pages |
| `editor` | Can create/edit sources, pipelines, destinations; trigger runs |
| `admin` | Full access including user management and settings |

### Password Storage

- Passwords hashed with **bcrypt** via `passlib`
- Source/destination credentials encrypted with **Fernet** (AES-128-CBC)
- Encryption key derived from `ARUS_ENCRYPTION_KEY` or `ARUS_JWT_SECRET`

### Rate Limiting

- Login endpoint rate-limited: 10 attempts per 60 seconds per IP
- In-memory tracking (resets on API restart)
