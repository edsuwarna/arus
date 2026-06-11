# Arus Architecture

> **Version:** 1.0
> **Status:** 🔴 Draft
> **Last Updated:** June 2026

---

## 1. System Overview

Arus is a lightweight CDC & ETL platform designed for VPS-class infrastructure. It runs entirely within a **single Docker Compose stack** — no Kubernetes, no Kafka, no external dependencies beyond PostgreSQL.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Host                               │
│                                                                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌──────────────┐   │
│  │  Arus Console │    │  Backend API     │    │  PostgreSQL  │   │
│  │  (SPA)        │◄──►│  (FastAPI +      │◄──►│  (15+)       │   │
│  │  :8080        │    │   APScheduler)   │    │  :5432       │   │
│  │               │    │  :8081           │    │              │   │
│  └──────┬───────┘    └────────┬─────────┘    └──────────────┘   │
│         │                      │                                 │
│         └──────HTTP API────────┘                                 │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Source Databases (external)                              │   │
│  │  ┌──────┐  ┌────────┐  ┌────────────┐                   │   │
│  │  │MySQL │  │MariaDB │  │PostgreSQL  │  ...               │   │
│  │  └──────┘  └────────┘  └────────────┘                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Stack

| Layer | Component | Technology | Justification |
|-------|-----------|-----------|---------------|
| **Frontend** | Arus Console | Vanilla HTML/CSS/JS (SPA) | Zero build step, no npm, single container |
| **Backend API** | REST API | Python 3.11+ (FastAPI) | Async, auto OpenAPI docs, lightweight |
| **Scheduler** | APScheduler | `apscheduler` Python lib | In-process, no Redis/Celery needed |
| **ORM** | SQLAlchemy 2.0 | With Alembic migrations | Type-safe, async support |
| **Source Connectors** | `pymysql`, `psycopg2` | Mature, well-tested drivers | Minimal overhead |
| **Warehouse** | PostgreSQL 15+ | Single instance | Config + state + warehouse in one DB |
| **Container** | Docker Compose | `docker compose up` | Single host, no orchestration |
| **Reverse Proxy** | Nginx or Cloudflare Tunnel | Optional | Auth, TLS, routing |
| **Retry** | `tenacity` | Battle-tested | Exponential backoff |
| **Encryption** | `cryptography` (Fernet) | Source password at rest | Built-in Python crypto |

### Why Not...

| Alternative | Why Not |
|-------------|---------|
| **Kubernetes** | Overkill for 2-4 container stack. VPS target market doesn't have Kube. |
| **Airflow/Dagster** | Heavy daemon architecture. Airflow needs Celery + Redis + DB. Dagster needs Dagit + daemon. |
| **Celery** | Adds Redis/RabbitMQ dependency. APScheduler handles our scale (5-20 pipelines). |
| **Node.js/Go backend** | Data engineering ecosystem is Python. CDC libs, pandas, SQLAlchemy all Python. |
| **React/Vue/Svelte** | Adds build step, npm, node_modules. Vanilla SPA is < 50KB total. |

---

## 3. Service Architecture

### 3.1 Container Layout

```
arus-console
  - Port: 8080
  - Type: Static file server (Nginx or Python HTTP)
  - Content: Single HTML + CSS + JS
  - Dependencies: backend API (proxied)

arus-api
  - Port: 8081
  - Type: Python FastAPI + APScheduler
  - Processes: API server + scheduler (same process)
  - Dependencies: PostgreSQL
  - Healthcheck: GET /api/health

arus-db
  - Port: 5432 (internal only)
  - Type: PostgreSQL 15+
  - Volume: persistent data
  - Init: auto-create schemas on first run
```

### 3.2 Container Communication

```
arus-console ──HTTP──► arus-api:8081 ──SQL──► arus-db:5432
                                 ▲
                                 │
                  APScheduler (in-process)
                  │
                  ▼
            Source DBs (external, port 3306/5432)
```

All inter-container communication via Docker internal network. PostgreSQL port is not exposed externally.

---

## 4. Data Flow

### 4.1 Incremental CDC Flow (watermark-based)

```
1. APScheduler triggers pipeline (every N minutes)
         │
2. Read watermark from arus_state:
   'SELECT watermark_value FROM arus_state.watermarks
    WHERE pipeline_id = ? AND source_table = ?'
         │
3. Extract from source:
   'SELECT * FROM source_table
    WHERE updated_at > ?watermark_value
    ORDER BY updated_at
    LIMIT 10000'
         │
4. Batch arrives as list[dict]
         │
5. Write to staging raw zone (JSONB):
   INSERT INTO staging.<source>_<table>_raw (_data, _hash, _arus_run_id)
   VALUES (%s, %s, %s)
         │
6. Normalize and upsert to analytics:
   INSERT INTO analytics.<table> (id, col1, col2, ...)
   VALUES (%s, %s, %s, ...)
   ON CONFLICT (id) DO UPDATE SET ...
         │
7. Update watermark:
   UPDATE arus_state.watermarks
   SET watermark_value = ? , row_count = ?, last_synced_at = NOW()
   WHERE pipeline_id = ? AND source_table = ?
         │
8. Log completion to arus_run_logs
```

### 4.2 Full Refresh Flow

```
1. Extract ALL rows (no watermark filter)
2. TRUNCATE analytics.<table>
3. Bulk INSERT all rows
4. Reset watermark to earliest value
```

### 4.3 Schema Drift Flow

```
1. On extract, compare source columns vs analytics column cache
2. If new column detected:
   a. Raw zone: no-op (JSONB is schema-flexible)
   b. Analytics: ALTER TABLE ADD COLUMN IF NOT EXISTS
   c. Log schema version change
3. Continue with normal load
```

---

## 5. Modular Monolith Architecture

### 5.1 Rationale

Arus uses a **modular monolith** — the entire backend runs as a single Python process, but the codebase is organized into **bounded-context modules** that follow microservice boundaries. This gives the best of both worlds:

| Phase | Architecture | Why |
|-------|-------------|-----|
| **Now (MVP)** | Monolith in a single container | Fast iteration, simple deploy, one `docker compose up` |
| **Future (Scale)** | Split modules into microservices | Each module has clean interfaces — extract, containerize, done |

### 5.2 Module Architecture

```
┌───────────────────────────────────────────────────────────┐
│                    Backend Process (arus-api)               │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                 FastAPI App                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │ auth     │  │ source   │  │ pipeline          │  │  │
│  │  │ module   │  │ module   │  │ module            │  │  │
│  │  │          │  │          │  │  ┌──────────────┐│  │  │
│  │  │ router/  │  │ router/  │  │  │ router/      ││  │  │
│  │  │ service/ │  │ service/ │  │  │ service/     ││  │  │
│  │  │ models/  │  │ models/  │  │  │ executor/    ││  │  │
│  │  │ repo/    │  │ repo/    │  │  │ scheduler/   ││  │  │
│  │  │          │  │          │  │  │ models/      ││  │  │
│  │  │          │  │          │  │  │ repo/        ││  │  │
│  │  └────┬─────┘  └────┬─────┘  │  └──────────────┘│  │  │
│  │       │              │       └──────────────────┘  │  │
│  │       │              │                             │  │
│  │  ┌────▼──────────────▼──────────────────────────┐  │  │
│  │  │           connector module                     │  │  │
│  │  │  (base class + registry + all implementations)│  │  │
│  │  └───────────────────────────────────────────────┘  │  │
│  │                                                      │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │     Shared Kernel                              │   │  │
│  │  │  ├── config.py (env var loading)               │   │  │
│  │  │  ├── db/session.py (SQLAlchemy engine)         │   │  │
│  │  │  ├── crypto.py (Fernet wrapper)                │   │  │
│  │  │  └── types.py (type mapping)                   │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              APScheduler (in-process)                │  │
│  │  Triggers pipeline module — no API call needed       │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

### 5.3 Module Communication Rules

```
┌────────────┐        ┌──────────────┐        ┌──────────────┐
│  Module A  │───────►│  Service     │◄───────│  Module B    │
│  (router)  │  HTTP  │  Interface   │ Python │  (service)   │
└────────────┘        └──────────────┘        └──────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   PostgreSQL     │
                    │  (shared DB)     │
                    └──────────────────┘
```

**Rules:**

| Rule | Implementation |
|------|---------------|
| ✅ Module A **tidak boleh import** Module B langsung | Communication via **service interface** (Python ABC) |
| ✅ Tiap module punya **SQLAlchemy models sendiri** | Tabel per domain, bukan shared models |
| ✅ Module dependencies di-inject via constructor | `PipelineService(auth_service=AuthService(...))` |
| ✅ Tiap module bisa di-test independent | Mock service dependency, test domain logic sendiri |
| ❌ No circular imports | Explicit dependency direction |
| ❌ No `from pipeline.models import X` from auth module | Auth module gak perlu tau pipeline models |

### 5.4 Interface Pattern

Each module exposes a **service interface** (Abstract Base Class) that other modules consume:

```python
# modules/auth/service.py — Interface
class AuthService(ABC):
    @abstractmethod
    def login(self, email: str, password: str) -> TokenResult: ...
    @abstractmethod
    def verify_token(self, token: str) -> User: ...
    @abstractmethod
    def get_user(self, user_id: str) -> User: ...

# modules/auth/service.py — Implementation
class AuthServiceImpl(AuthService):
    def __init__(self, db_session, crypto_service):
        self.db = db_session
        self.crypto = crypto_service

    def login(self, email: str, password: str) -> TokenResult:
        user = self.db.query(User).filter_by(email=email).first()
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("Invalid credentials")
        token = create_jwt({"sub": user.id, "role": user.role})
        return TokenResult(token=token, user=user.to_dict())
```

### 5.5 Module Dependency Graph

```
┌──────────────────┐
│    dashboard     │──── (reads from all modules for aggregation)
└──────────────────┘
        │
┌───────▼────────────┐
│       dag          │──── (reads pipeline + source + state data)
└────────────────────┘
        │
┌───────▼────────────┐     ┌──────────────────┐
│     pipeline       │────►│    connector     │
│  (scheduler +      │     │  (extract/load)  │
│   executor +       │     └──────────────────┘
│   state)           │
└───────┬────────────┘
        │
┌───────▼────────────┐
│      source        │
└────────────────────┘
        │
┌───────▼────────────┐     ┌──────────────────┐
│       auth         │     │    settings      │
└────────────────────┘     └──────────────────┘

destination ─── (standalone, referenced by pipeline)
```

**Key observations:**
- `pipeline` is the **most complex module** — contains scheduler, executor, state management
- `dashboard` and `dag` are **read-only aggregation modules**
- `auth` and `settings` are **leaf modules** — no dependencies on other modules
- `connector` is **pure library** — no router, no DB models, just base classes + implementations

---

## 6. Security Architecture

### 6.1 Auth Flow

```
Login ──► POST /api/auth/login ──► verify bcrypt ──► issue JWT (24h)
                                                       │
Request ──► Authorization: Bearer <token> ──► verify JWT ──► role check ──► response
```

- **Password hashing:** bcrypt via `passlib`
- **JWT signing:** HS256 with configurable secret
- **Token expiry:** 24 hours, no refresh token for MVP
- **Roles:** `admin` (full access) / `viewer` (read-only)

### 6.2 Credential Management

- Source database passwords stored encrypted (Fernet symmetric encryption)
- Encryption key stored in `arus_config.settings`
- Key generated on first run, backed up to file
- **Never** source passwords in git, env vars, or plaintext in DB

### 6.3 Network Security

- **Source DBs:** SELECT-only access, read-only user
- **PostgreSQL:** Internal Docker network only (port not exposed)
- **Arus Console:** Behind reverse proxy (Nginx / CF Tunnel) with optional basic auth
- **API:** JWT required on all endpoints except `/api/health` and `/api/auth/login`

---

## 7. Directory Structure

```
arus/
├── docker-compose.yml          ← Single file deployment
├── Dockerfile                  ← Backend API container
├── requirements.txt            ← Python dependencies
├── .env.example                ← Environment template
├── .gitignore
│
├── arus/                       ← Backend Python package (modular monolith)
│   ├── __init__.py
│   ├── main.py                 ← FastAPI app entry point — register all modules
│   ├── di.py                   ← Dependency injection container (wiring modules)
│   │
│   ├── shared/                 ← Shared Kernel — used by ALL modules
│   │   ├── __init__.py
│   │   ├── config.py           ← Settings from env vars (pydantic-settings)
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py      ← SQLAlchemy engine + session factory
│   │   │   └── migrations/     ← Alembic migrations (shared)
│   │   ├── crypto.py           ← Fernet encryption
│   │   ├── types.py            ← Type mapping (source → PostgreSQL)
│   │   └── exceptions.py       ← Base exception classes
│   │
│   ├── modules/                ← Bounded-context modules
│   │   ├── auth/               ← AUTH module — could be standalone service
│   │   │   ├── __init__.py
│   │   │   ├── router.py       ← FastAPI router: /api/auth/login, /me
│   │   │   ├── service.py      ← AuthService interface + AuthServiceImpl
│   │   │   ├── models.py       ← SQLAlchemy: User model
│   │   │   ├── repository.py   ← UserRepository (DB access)
│   │   │   ├── schemas.py      ← Pydantic request/response models
│   │   │   └── tests/
│   │   │
│   │   ├── source/             ← SOURCE module — could be standalone service
│   │   │   ├── __init__.py
│   │   │   ├── router.py       ← /api/sources CRUD + test + discover
│   │   │   ├── service.py      ← SourceService interface + impl
│   │   │   ├── models.py       ← SQLAlchemy: Source model
│   │   │   ├── repository.py
│   │   │   ├── discovery.py    ← Auto-detect tables logic
│   │   │   ├── schemas.py
│   │   │   └── tests/
│   │   │
│   │   ├── destination/        ← DESTINATION module
│   │   │   ├── __init__.py
│   │   │   ├── router.py       ← /api/destinations CRUD
│   │   │   ├── service.py
│   │   │   ├── models.py       ← SQLAlchemy: Destination model
│   │   │   ├── repository.py
│   │   │   ├── schemas.py
│   │   │   └── tests/
│   │   │
│   │   ├── pipeline/           ← PIPELINE module — core (most complex)
│   │   │   ├── __init__.py
│   │   │   ├── router.py       ← /api/pipelines CRUD + trigger + pause + resume
│   │   │   ├── service.py      ← PipelineService interface + impl
│   │   │   ├── models.py       ← SQLAlchemy: Pipeline, PipelineTable
│   │   │   ├── repository.py
│   │   │   ├── executor.py     ← Run pipeline: extract → load → normalize → update watermark
│   │   │   ├── scheduler.py    ← APScheduler wrapper (cron triggers)
│   │   │   ├── state.py        ← Watermark read/write (arus_state)
│   │   │   ├── schemas.py
│   │   │   └── tests/
│   │   │
│   │   ├── connector/          ← CONNECTOR module — pure library, no router
│   │   │   ├── __init__.py
│   │   │   ├── base_source.py      ← BaseSource abstract class
│   │   │   ├── base_destination.py ← BaseDestination abstract class
│   │   │   ├── registry.py     ← Connector registry (YAML or dict)
│   │   │   ├── sources/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── mysql.py
│   │   │   │   ├── mariadb.py
│   │   │   │   └── postgresql.py
│   │   │   └── destinations/
│   │   │       ├── __init__.py
│   │   │       └── postgresql.py
│   │   │
│   │   ├── run_log/            ← RUN LOG module — run history + logs
│   │   │   ├── __init__.py
│   │   │   ├── router.py       ← /api/pipelines/{id}/runs, /api/runs/{id}/logs
│   │   │   ├── service.py
│   │   │   ├── models.py       ← SQLAlchemy: Run, RunTableStats, RunLog
│   │   │   ├── repository.py
│   │   │   ├── schemas.py
│   │   │   └── tests/
│   │   │
│   │   ├── dag/                ← DAG module — asset graph queries
│   │   │   ├── __init__.py
│   │   │   ├── router.py       ← /api/dag, /api/dag/node/{id}
│   │   │   ├── service.py      ← DAGService — reads from pipeline + source + run_log
│   │   │   └── tests/
│   │   │
│   │   ├── dashboard/          ← DASHBOARD module — aggregation
│   │   │   ├── __init__.py
│   │   │   ├── router.py       ← /api/dashboard/summary, /recent-runs, /sync-chart
│   │   │   ├── service.py      ← DashboardService
│   │   │   └── tests/
│   │   │
│   │   └── settings/           ← SETTINGS module
│   │       ├── __init__.py
│   │       ├── router.py       ← /api/settings GET + PUT
│   │       ├── service.py
│   │       ├── models.py       ← SQLAlchemy: Settings (key-value)
│   │       ├── repository.py
│   │       └── tests/
│   │
│   └── utils/                  ← Utility helpers (cross-cutting)
│       ├── __init__.py
│       └── pagination.py       ← Pagination helper for list endpoints
│
├── console/                    ← Frontend SPA
│   ├── index.html              ← Single HTML file
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js              ← SPA router + state
│       ├── api.js              ← HTTP client (fetch wrapper)
│       ├── pages/
│       │   ├── login.js
│       │   ├── dashboard.js
│       │   ├── sources.js
│       │   ├── destinations.js
│       │   ├── pipelines.js
│       │   ├── pipeline-detail.js
│       │   ├── dag.js
│       │   └── settings.js
│       └── components/
│           ├── sidebar.js
│           ├── status-badge.js
│           └── chart.js
│
├── nginx/
│   └── default.conf            ← Reverse proxy config (optional)
│
├── prd/                        ← Product requirements
│   ├── PRD.md
│   ├── api-spec.md
│   ├── data-model.md
│   └── connector-roadmap.md
│
└── docs/
    ├── architecture.md         ← This file
    └── setup.md                ← Deployment guide
```

---

## 8. Scalability & Performance

### 8.1 Target Performance

| Metric | Target | Notes |
|--------|--------|-------|
| **Batch size** | 10,000 rows | Configurable per connector |
| **Pipeline concurrency** | 5 simultaneous | 3 pipelines reading + 2 writing |
| **Latency (source → DW)** | < 1 minute | For tables < 1M rows |
| **Scheduler overhead** | ~50MB RAM | APScheduler in-process |
| **API response time** | < 100ms | For CRUD operations |
| **DAG render** | < 500ms | For up to 200 nodes |

### 8.2 Bottleneck Limits

| Bottleneck | Limit | Mitigation |
|------------|-------|------------|
| Single process | CPU-bound on normalize step | I/O bound mostly (network + DB) |
| PostgreSQL connections | 20 concurrent | Connection pooling via SQLAlchemy |
| Source DB load | Depends on source | Configurable batch size + read-only user |
| Disk I/O (JSONB writes) | 10MB/s per table | Sequential writes, no contention |

---

## 9. Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Orchestrator** | APScheduler (in-process) | No Redis/Celery. Single process = simple deploy. |
| **CDC method** | Watermark-based | No binlog/WAL needed. Works with read-replica. |
| **Storage** | Single PostgreSQL | Warehouse + config + state in one DB. Separate schemas. |
| **Raw zone** | JSONB | Schema-agnostic, fast ingest, replayable. |
| **Normalized zone** | Typed columns | BI-ready, type-safe, queryable. |
| **Config via UI** | PostgreSQL tables | No file editing. Everything via browser. |
| **Auth built-in** | JWT in Arus Console | Works behind any proxy (or without one). |
| **Pluggable connectors** | Python base class | Add connector in 1 file + 1 config entry. |
| **Modular monolith** | Domain modules with service interfaces | MVP runs in one container. Future: extract to microservices. |

---

## 10. Microservice Extraction Strategy

Each module in the modular monolith is **extract-ready**. When Arus outgrows a single container, any module can become a standalone microservice with minimal code changes.

### 10.1 Extraction Pattern

```python
# BEFORE (modular monolith) — AuthService injected via interface:
class PipelineService:
    def __init__(self, auth_service: AuthService):
        self.auth = auth_service

# AFTER (microservice) — same interface, different transport:
class AuthServiceHTTP(AuthService):
    """Calls the real auth microservice over HTTP."""
    def __init__(self, base_url: str):
        self.client = httpx.Client(base_url=base_url)

    def verify_token(self, token: str) -> User:
        resp = self.client.post("/internal/verify", json={"token": token})
        return User(**resp.json())
```

**Zero code change** in PipelineService — just swap the injected implementation in `di.py`.

### 10.2 Extraction Priority

| Order | Module | Why Extract | Complexity |
|-------|--------|-------------|------------|
| 1st | **auth** | Independent leaf module. Shared user store across services. High security boundary. | Low — stateless, simple API. |
| 2nd | **source** + **destination** | Configuration-heavy, read-mostly. Can be cached aggressively. | Medium — needs event on change to notify pipeline. |
| 3rd | **connector** | CPU-bound extract/normalize tasks. Scales independently from API. | Medium — needs message queue for job dispatch. |
| 4th | **pipeline** | Scheduler + executor are the heaviest. Separate = independent scaling. | High — stateful, has DB dependency on source/destination configs. |

### 10.3 Communication Evolution

```
Phase 1 (MVP): In-process function calls via interface
   Module A ──function()──► Module B

Phase 2 (First split): Internal HTTP for auth
   Module A ──HTTP(/internal/verify)──► Auth Microservice

Phase 3 (Full split): Event-driven for pipeline
   Source Config Changed ──► Redis Pub/Sub ──► Pipeline Service
   Pipeline Complete ──► Run Log Service (HTTP)
```

### 10.4 DB Evolution

```
Phase 1: Single PostgreSQL (arus_warehouse)
   └─ All modules share one DB instance

Phase 2: Separate schemas (still one DB, but isolated)
   └─ auth module ──► arus_auth schema
   └─ pipeline module ──► arus_pipeline schema
   └─ run_log module ──► arus_logs schema

Phase 3: Separate DB per microservice
   └─ auth service ──► PostgreSQL (auth only)
   └─ pipeline service ──► PostgreSQL (pipeline + state)
   └─ run log service ──► TimescaleDB or ClickHouse
```

### 10.5 When to Extract

**Don't** extract until you see concrete pain:

| Symptom | Action |
|---------|--------|
| Auth changes require full backend redeploy | Extract auth first |
| Connector CPU usage slows API responses | Extract connector to worker container |
| Need different scaling for scheduler vs API | Split pipeline module |
| Team grows beyond 3 devs on backend | Extract by ownership boundary |
| CI/CD deploys take > 10 minutes | Extract by deployment domain |

> **Rule of thumb:** Don't extract until module has clear ownership boundary AND measurable pain from monolith. Premature microservices add more complexity than they solve.

---

*End of Architecture Document — Arus v1.0*
