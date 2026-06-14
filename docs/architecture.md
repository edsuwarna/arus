# System Architecture

Arus is a modular monolith — a single Python process organized into bounded-context modules that follow microservice boundaries.

## High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Host                              │
│                                                             │
│  ┌──────────────┐     ┌──────────────────┐  ┌────────────┐ │
│  │ Arus Console │     │   Backend API     │  │ PostgreSQL │ │
│  │    (SPA)     │◄───►│  (FastAPI +       │◄─►│  (15+)     │ │
│  │   :8082      │     │   APScheduler)    │  │  :5432     │ │
│  │              │     │  :8081            │  │            │ │
│  └──────┬───────┘     └────────┬──────────┘  └────────────┘ │
│         │                      │                             │
│         └──────HTTP API────────┘                             │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Source Databases (external)                   │   │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────────┐        │   │
│  │  │  MySQL  │  │ MariaDB  │  │ PostgreSQL   │  ...    │   │
│  │  └─────────┘  └──────────┘  └──────────────┘        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Component Stack

### Frontend — Arus Console
Vanilla HTML/CSS/JS SPA. Zero build step, no npm, single container. Communicates with the backend via REST API.

### Backend API — FastAPI
Python 3.11+ REST API with built-in APScheduler for pipeline scheduling. Handles both API requests and pipeline execution.

### Database — PostgreSQL 15+
Single instance for config, state, run logs, and warehouse data — separated by schemas. No external DB needed.

## Data Flow

```
1. APScheduler triggers pipeline (every N minutes)
         │
2. Read watermark from arus_state
         │
3. Extract from source:
   SELECT * FROM source_table
   WHERE updated_at > watermark_value
   ORDER BY updated_at LIMIT 10000
         │
4. Batch arrives as list[dict]
         │
5. Write to raw zone (JSONB):
   INSERT INTO raw.<source>_<table>_raw
         │
6. Normalize and upsert to target:
   INSERT INTO target.<table> ...
   ON CONFLICT (id) DO UPDATE SET ...
         │
7. Update watermark
         │
8. Log completion to arus_run_logs
```

### Incremental CDC (Watermark-based)
Arus uses watermark-based CDC — the most practical method for VPS-class infrastructure. Each table tracks a cursor (usually `updated_at`). On each run, Arus fetches rows newer than the stored watermark, processes them, and updates the cursor.

### Full Refresh
Alternatively, tables can be configured for full refresh — truncating the target and reloading all rows. Useful for small dimension tables or initial backfills.

### Schema Drift
When new columns appear in the source, the raw zone (JSONB) is unaffected. The target zone auto-runs `ALTER TABLE ADD COLUMN IF NOT EXISTS` — no pipeline breakage.

## Module Architecture

```
┌──────────────────────────────────────────────────────┐
│                 Backend Process (arus-api)           │
│                                                      │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Auth   │ │ Source │ │ Pipeline │ │ Connector │  │
│  │ Module │ │ Module │ │ Module   │ │ Module    │  │
│  └────────┘ └────────┘ └────┬─────┘ └───────────┘  │
│                              │                      │
│                    ┌────────▼────────┐              │
│                    │   APScheduler   │              │
│                    │  (in-process)   │              │
│                    └─────────────────┘              │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │           Shared Kernel                       │   │
│  │  config.py · db/session.py · crypto.py       │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

Each module follows a clean architecture pattern: **Router → Service → Repository**. Modules communicate through service interfaces (Python ABCs), not direct imports — making the system testable and future-proof for splitting into microservices.

## Container Layout

- **arus-console** — Nginx serving the static SPA. Port 8082.
- **arus-api** — FastAPI + APScheduler. Port 8081.
- **arus-db** — PostgreSQL 15+. Port 5432 (internal).

All inter-container communication happens over the Docker internal network. The database port is not exposed externally.
