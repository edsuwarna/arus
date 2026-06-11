# Arus API Specification

> **Version:** 1.0
> **Status:** 🔴 Draft
> **Last Updated:** June 2026
> **Base URL:** `http://localhost:8081/api`

---

## 1. Conventions

### 1.1 Base URL
All API endpoints are prefixed with `/api/v1` in the backend. The Console SPA is reverse-proxied so API calls go to `/api/...`.

### 1.2 Authentication
- **Login:** `POST /api/auth/login` → returns JWT token
- **Token via:** `Authorization: Bearer <token>` header
- **Expiry:** 24 hours from issue
- **Refresh:** `POST /api/auth/refresh`

### 1.3 Response Format

**Success:**
```json
{
  "status": "ok",
  "data": { ... }
}
```

**Error:**
```json
{
  "status": "error",
  "error": {
    "code": "SOURCE_NOT_FOUND",
    "message": "Source with id 'abc-123' not found"
  }
}
```

**Error Codes:**
| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `AUTH_REQUIRED` | 401 | Missing or expired token |
| `FORBIDDEN` | 403 | Insufficient role |
| `VALIDATION_ERROR` | 422 | Invalid request body |
| `NOT_FOUND` | 404 | Resource not found |
| `CONNECTION_FAILED` | 502 | Source DB unreachable |
| `DISCOVERY_FAILED` | 500 | Table scan failed |
| `INTERNAL_ERROR` | 500 | Unexpected error |

### 1.4 Pagination
List endpoints support pagination via query params: `?page=1&per_page=20`

**Response:**
```json
{
  "status": "ok",
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 147,
    "total_pages": 8
  }
}
```

### 1.5 Status Enums

**Pipeline status:**
| Value | Label | Color |
|-------|-------|-------|
| `active` | Active | Emerald |
| `paused` | Paused | Amber |
| `error` | Error | Red |
| `inactive` | Inactive | Gray |

**Run status:**
| Value | Label | Color |
|-------|-------|-------|
| `running` | Running | Blue |
| `success` | Success | Emerald |
| `failed` | Failed | Red |
| `cancelled` | Cancelled | Gray |

**Node status (DAG):**
| Value | Label | Color |
|-------|-------|-------|
| `success` | Success | Emerald |
| `running` | Running | Blue |
| `stale` | Stale | Amber |
| `failed` | Failed | Red |
| `pending` | Not Started | Gray |

---

## 2. Auth Endpoints

### POST /api/auth/login
Login with email + password.

**Request:**
```json
{
  "email": "data.engineer@company.com",
  "password": "supersecret123"
}
```

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": "usr_abc123",
      "email": "data.engineer@company.com",
      "name": "Budi Santoso",
      "role": "admin"
    },
    "expires_at": "2026-06-13T10:00:00Z"
  }
}
```

**Error (401):**
```json
{
  "status": "error",
  "error": { "code": "AUTH_FAILED", "message": "Invalid email or password" }
}
```

### POST /api/auth/logout
Invalidate current session.

**Response (200):** `{ "status": "ok", "data": null }`

### GET /api/auth/me
Get current user profile.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "id": "usr_abc123",
    "email": "data.engineer@company.com",
    "name": "Budi Santoso",
    "role": "admin",
    "created_at": "2026-06-01T08:00:00Z"
  }
}
```

---

## 3. Source Endpoints

### GET /api/sources
List all registered source databases.

**Query params:** `?page=1&per_page=20&type=mysql&search=prod`

**Response (200):**
```json
{
  "status": "ok",
  "data": [
    {
      "id": "src_001",
      "name": "Production MySQL",
      "type": "mysql",
      "host": "10.0.0.50",
      "port": 3306,
      "database": "ecommerce",
      "username": "reader",
      "sync_method": "auto",
      "table_count": 27,
      "enabled_table_count": 12,
      "status": "connected",
      "last_tested": "2026-06-12T09:00:00Z",
      "created_at": "2026-06-01T08:00:00Z"
    }
  ],
  "pagination": { "page": 1, "per_page": 20, "total": 3, "total_pages": 1 }
}
```

### POST /api/sources
Register a new source database.

**Request:**
```json
{
  "name": "Production MySQL",
  "type": "mysql",
  "host": "10.0.0.50",
  "port": 3306,
  "database": "ecommerce",
  "username": "reader",
  "password": "readonly_pass",
  "ssl": false,
  "sync_method": "auto",
  "table_include_patterns": ["orders*", "users", "products*"],
  "table_exclude_patterns": ["*_temp", "*_backup"]
}
```

**Response (201):**
```json
{
  "status": "ok",
  "data": {
    "id": "src_002",
    "name": "Production MySQL",
    "type": "mysql",
    "status": "registered",
    "message": "Source registered. Run discover to scan tables."
  }
}
```

### POST /api/sources/{id}/test
Test connection to source database.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "connected": true,
    "latency_ms": 12,
    "server_version": "8.0.35",
    "database_count": 4
  }
}
```

**Error (502):**
```json
{
  "status": "error",
  "error": { "code": "CONNECTION_FAILED", "message": "Can't connect to MySQL (10.0.0.50:3306) — connection timed out" }
}
```

### POST /api/sources/{id}/discover
Scan source database and detect tables + sync modes.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "source_id": "src_002",
    "tables": [
      {
        "name": "orders",
        "schema": "public",
        "row_count_estimate": 154723,
        "columns": ["id", "user_id", "total", "status", "created_at", "updated_at"],
        "detected_sync": "incremental",
        "watermark_column": "updated_at",
        "enabled": true
      },
      {
        "name": "users",
        "schema": "public",
        "row_count_estimate": 28451,
        "columns": ["id", "email", "name", "created_at"],
        "detected_sync": "incremental",
        "watermark_column": "created_at",
        "enabled": true
      },
      {
        "name": "sessions",
        "schema": "public",
        "row_count_estimate": 890234,
        "columns": ["id", "user_id", "token", "expires_at", "created_at"],
        "detected_sync": "full_refresh",
        "watermark_column": null,
        "enabled": false
      }
    ]
  }
}
```

### PUT /api/sources/{id}/tables
Update which tables are enabled/disabled after discover.

**Request:**
```json
{
  "tables": [
    { "name": "orders", "enabled": true },
    { "name": "users", "enabled": true },
    { "name": "sessions", "enabled": false }
  ]
}
```

**Response (200):** `{ "status": "ok", "data": { "updated": 3, "pipeline": "auto-created" } }`

> **Note:** When tables are saved and at least one is enabled, Arus auto-creates a pipeline for this source (or updates the existing one). See Section 5.

### PUT /api/sources/{id}
Update source configuration.

**Response (200):** `{ "status": "ok", "data": { "id": "src_002", "updated": true } }`

### DELETE /api/sources/{id}
Delete source and all associated pipelines, run history, and staging data.

**Response (200):** `{ "status": "ok", "data": { "deleted": "source", "cascaded": ["pipeline", "runs", "staging_tables"] } }`

---

## 4. Destination Endpoints

### GET /api/destinations
List all configured destinations.

**Response (200):**
```json
{
  "status": "ok",
  "data": [
    {
      "id": "dest_001",
      "name": "Warehouse",
      "type": "postgresql",
      "host": "localhost",
      "port": 5432,
      "database": "arus_warehouse",
      "status": "connected",
      "raw_schema": "staging",
      "analytics_schema": "analytics",
      "total_tables": 24,
      "total_rows": 2450000,
      "disk_usage_mb": 1800,
      "last_synced": "2026-06-12T09:05:00Z"
    }
  ]
}
```

### POST /api/destinations
Register a destination. (Future: support multiple destinations.)

**Request:**
```json
{
  "name": "Warehouse",
  "type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "arus_warehouse",
  "username": "arus",
  "password": "arus_pass",
  "raw_schema": "staging",
  "analytics_schema": "analytics",
  "default": true
}
```

**Response (201):** `{ "status": "ok", "data": { "id": "dest_001" } }`

### POST /api/destinations/{id}/test
Test connection to destination.

**Response (200):** `{ "status": "ok", "data": { "connected": true, "latency_ms": 3 } }`

---

## 5. Pipeline Endpoints

### GET /api/pipelines
List all pipelines.

**Query params:** `?page=1&per_page=20&status=active`

**Response (200):**
```json
{
  "status": "ok",
  "data": [
    {
      "id": "pipe_001",
      "name": "ecommerce → Warehouse",
      "source_id": "src_002",
      "source_name": "Production MySQL",
      "status": "active",
      "schedule": "*/5 * * * *",
      "schedule_label": "Every 5 minutes",
      "tables": ["orders", "users", "products"],
      "enabled_table_count": 3,
      "last_run": {
        "status": "success",
        "started_at": "2026-06-12T09:05:00Z",
        "duration_ms": 3400,
        "rows_synced": 1523
      },
      "total_rows_synced": 2450000,
      "error_count_7d": 1,
      "avg_latency_ms": 2850,
      "created_at": "2026-06-01T08:00:00Z"
    }
  ],
  "pagination": { "page": 1, "per_page": 20, "total": 5, "total_pages": 1 }
}
```

### GET /api/pipelines/{id}
Pipeline detail.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "id": "pipe_001",
    "name": "ecommerce → Warehouse",
    "source": {
      "id": "src_002",
      "name": "Production MySQL",
      "type": "mysql"
    },
    "destination": {
      "id": "dest_001",
      "name": "Warehouse",
      "type": "postgresql"
    },
    "status": "active",
    "schedule": "*/5 * * * *",
    "tables": [
      {
        "name": "orders",
        "sync_mode": "incremental",
        "watermark_column": "updated_at",
        "watermark_value": "2026-06-12T09:05:00Z",
        "row_count_raw": 154723,
        "row_count_analytics": 154700,
        "enabled": true
      },
      {
        "name": "users",
        "sync_mode": "incremental",
        "watermark_column": "created_at",
        "watermark_value": "2026-06-12T09:00:00Z",
        "row_count_raw": 28450,
        "row_count_analytics": 28450,
        "enabled": true
      }
    ],
    "stats": {
      "total_rows_synced": 2450000,
      "total_runs": 2842,
      "successful_runs": 2835,
      "failed_runs": 7,
      "avg_duration_ms": 2800,
      "uptime_pct": 99.75
    },
    "created_at": "2026-06-01T08:00:00Z",
    "updated_at": "2026-06-12T09:05:00Z"
  }
}
```

### POST /api/pipelines
Create a pipeline manually (alternative to auto-create).

**Request:**
```json
{
  "name": "ecommerce → Warehouse",
  "source_id": "src_002",
  "destination_id": "dest_001",
  "schedule": "*/5 * * * *",
  "tables": ["orders", "users", "products"]
}
```

### PUT /api/pipelines/{id}
Update pipeline config (schedule, name, tables).

### DELETE /api/pipelines/{id}
Delete pipeline and its run history.

### POST /api/pipelines/{id}/trigger
Manually trigger a pipeline run.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "run_id": "run_abc123",
    "status": "running",
    "started_at": "2026-06-12T09:10:00Z"
  }
}
```

### POST /api/pipelines/{id}/pause
Pause scheduled pipeline. In-flight run completes first.

**Response (200):** `{ "status": "ok", "data": { "pipeline_id": "pipe_001", "status": "paused" } }`

### POST /api/pipelines/{id}/resume
Resume paused pipeline.

**Response (200):** `{ "status": "ok", "data": { "pipeline_id": "pipe_001", "status": "active" } }`

---

## 6. Run History Endpoints

### GET /api/pipelines/{id}/runs
List runs for a specific pipeline.

**Query params:** `?page=1&per_page=20&status=failed&from=2026-06-01&to=2026-06-12`

**Response (200):**
```json
{
  "status": "ok",
  "data": [
    {
      "id": "run_abc123",
      "pipeline_id": "pipe_001",
      "status": "success",
      "started_at": "2026-06-12T09:05:00Z",
      "finished_at": "2026-06-12T09:05:03s",
      "duration_ms": 3400,
      "tables_synced": 3,
      "rows_extracted": 1523,
      "rows_loaded": 1523,
      "rows_failed": 0,
      "error_message": null
    }
  ],
  "pagination": { "page": 1, "per_page": 20, "total": 2842, "total_pages": 143 }
}
```

### GET /api/runs/{run_id}
Run detail.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "id": "run_abc123",
    "pipeline_id": "pipe_001",
    "pipeline_name": "ecommerce → Warehouse",
    "status": "success",
    "started_at": "2026-06-12T09:05:00Z",
    "finished_at": "2026-06-12T09:05:03s",
    "duration_ms": 3400,
    "per_table": [
      {
        "table": "orders",
        "rows_extracted": 1200,
        "rows_loaded_raw": 1200,
        "rows_loaded_analytics": 1200,
        "rows_failed": 0,
        "watermark_before": "2026-06-12T09:00:00Z",
        "watermark_after": "2026-06-12T09:05:00Z",
        "duration_ms": 2100
      },
      {
        "table": "users",
        "rows_extracted": 320,
        "rows_loaded_raw": 320,
        "rows_loaded_analytics": 320,
        "rows_failed": 0,
        "watermark_before": "2026-06-12T09:00:00Z",
        "watermark_after": "2026-06-12T09:05:00Z",
        "duration_ms": 900
      }
    ],
    "error_message": null
  }
}
```

### GET /api/runs/{run_id}/logs
Get raw log lines for a run.

**Query params:** `?offset=0&limit=100`

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "run_id": "run_abc123",
    "logs": [
      {"timestamp": "2026-06-12T09:05:00.123Z", "level": "INFO", "message": "Pipeline 'ecommerce → Warehouse' started"},
      {"timestamp": "2026-06-12T09:05:00.200Z", "level": "INFO", "message": "Extracting orders where updated_at > '2026-06-12T09:00:00Z'..."},
      {"timestamp": "2026-06-12T09:05:01.100Z", "level": "INFO", "message": "Extracted 1200 rows from orders in 900ms"},
      {"timestamp": "2026-06-12T09:05:01.200Z", "level": "INFO", "message": "Loading 1200 rows to staging.orders_raw..."},
      {"timestamp": "2026-06-12T09:05:02.000Z", "level": "INFO", "message": "Loaded 1200 rows to staging.orders_raw"},
      {"timestamp": "2026-06-12T09:05:02.100Z", "level": "INFO", "message": "Normalizing staging.orders_raw → analytics.orders..."},
      {"timestamp": "2026-06-12T09:05:02.800Z", "level": "INFO", "message": "Upserted 1200 rows to analytics.orders"},
      {"timestamp": "2026-06-12T09:05:03.000Z", "level": "INFO", "message": "Pipeline finished — 3 tables, 1523 rows, 3400ms"}
    ],
    "total": 9,
    "offset": 0,
    "limit": 100
  }
}
```

---

## 7. DAG / Asset Graph Endpoints

### GET /api/dag
Get full asset graph for all pipelines.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "nodes": [
      {
        "id": "source.prod_mysql.orders",
        "type": "source_table",
        "label": "orders",
        "source_name": "Production MySQL",
        "layer": "source",
        "status": "success",
        "last_run_status": "success",
        "last_synced": "2026-06-12T09:05:00Z"
      },
      {
        "id": "staging.orders_raw",
        "type": "stage_table",
        "label": "orders_raw",
        "layer": "staging",
        "status": "success",
        "row_count": 154723,
        "last_synced": "2026-06-12T09:05:00Z"
      },
      {
        "id": "analytics.orders",
        "type": "analytics_table",
        "label": "orders",
        "layer": "analytics",
        "status": "success",
        "row_count": 154700,
        "last_synced": "2026-06-12T09:05:00Z"
      }
    ],
    "edges": [
      { "from": "source.prod_mysql.orders", "to": "staging.orders_raw" },
      { "from": "staging.orders_raw", "to": "analytics.orders" }
    ],
    "pipelines": [
      {
        "id": "pipe_001",
        "name": "ecommerce → Warehouse",
        "status": "active"
      }
    ]
  }
}
```

### GET /api/dag/node/{node_id}
Get detail for a specific DAG node.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "id": "analytics.orders",
    "type": "analytics_table",
    "label": "orders",
    "layer": "analytics",
    "schema": "analytics",
    "columns": [
      {"name": "id", "type": "bigint", "nullable": false, "primary_key": true},
      {"name": "user_id", "type": "bigint", "nullable": false},
      {"name": "total", "type": "decimal(12,2)", "nullable": false},
      {"name": "status", "type": "varchar(50)", "nullable": false},
      {"name": "created_at", "type": "timestamp", "nullable": false},
      {"name": "updated_at", "type": "timestamp", "nullable": true}
    ],
    "row_count": 154700,
    "size_mb": 45,
    "last_synced": "2026-06-12T09:05:00Z",
    "upstream_nodes": [
      {"id": "staging.orders_raw", "label": "orders_raw", "layer": "staging", "status": "success"}
    ],
    "downstream_nodes": [],
    "latest_runs": [
      {"run_id": "run_abc123", "status": "success", "finished_at": "2026-06-12T09:05:03s", "rows_loaded": 1200}
    ]
  }
}
```

---

## 8. Dashboard Endpoints

### GET /api/dashboard/summary
Dashboard overview stats.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "active_sources": 3,
    "total_pipelines": 5,
    "active_pipelines": 4,
    "total_tables_synced": 24,
    "total_rows_synced": 2450000,
    "rows_synced_24h": 185000,
    "failed_runs_24h": 2,
    "total_runs_24h": 288,
    "uptime_pct_7d": 99.75,
    "avg_latency_ms": 2800
  }
}
```

### GET /api/dashboard/recent-runs
Recent pipeline runs for dashboard.

**Query params:** `?limit=10`

**Response (200):**
```json
{
  "status": "ok",
  "data": [
    {
      "run_id": "run_abc123",
      "pipeline_name": "ecommerce → Warehouse",
      "status": "success",
      "rows_synced": 1523,
      "duration_ms": 3400,
      "started_at": "2026-06-12T09:05:00Z"
    }
  ]
}
```

### GET /api/dashboard/sync-chart
7-day sync performance data.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "daily": [
      {"date": "2026-06-06", "rows_synced": 175000, "runs": 285, "failed": 1},
      {"date": "2026-06-07", "rows_synced": 180000, "runs": 288, "failed": 0},
      {"date": "2026-06-08", "rows_synced": 120000, "runs": 240, "failed": 3},
      {"date": "2026-06-09", "rows_synced": 190000, "runs": 288, "failed": 0},
      {"date": "2026-06-10", "rows_synced": 185000, "runs": 287, "failed": 1},
      {"date": "2026-06-11", "rows_synced": 178000, "runs": 286, "failed": 0},
      {"date": "2026-06-12", "rows_synced": 95000, "runs": 144, "failed": 0}
    ]
  }
}
```

---

## 9. Settings Endpoints

### GET /api/settings
Get current settings.

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "general": {
      "pipeline_name_prefix": "",
      "default_sync_interval": "*/5 * * * *",
      "auto_discover": true,
      "schema_drift_detection": true,
      "notifications_enabled": false,
      "retry_max_attempts": 3
    },
    "schedules": {
      "monitoring_check_interval": "*/1 * * * *"
    },
    "notifications": {
      "telegram_bot_token": null,
      "telegram_chat_id": null,
      "webhook_url": null
    }
  }
}
```

### PUT /api/settings
Update settings.

**Request:**
```json
{
  "default_sync_interval": "*/10 * * * *",
  "notifications_enabled": true,
  "telegram_bot_token": "bot123:abc",
  "telegram_chat_id": "-1001234567890"
}
```

**Response (200):** `{ "status": "ok", "data": { "updated": 4 } }`

---

## 10. User Management Endpoints (Admin)

### GET /api/users
List users.

**Response (200):**
```json
{
  "status": "ok",
  "data": [
    {
      "id": "usr_abc123",
      "email": "data.engineer@company.com",
      "name": "Budi Santoso",
      "role": "admin",
      "created_at": "2026-06-01T08:00:00Z",
      "last_login": "2026-06-12T08:30:00Z"
    }
  ]
}
```

### POST /api/users
Create user (admin only).

**Request:**
```json
{
  "email": "analyst@company.com",
  "name": "Siti Rahayu",
  "password": "temp12345",
  "role": "viewer"
}
```

**Response (201):** `{ "status": "ok", "data": { "id": "usr_xyz789" } }`

### PUT /api/users/{id}
Update user role, name.

### DELETE /api/users/{id}
Delete user.

---

## 11. Health Endpoint

### GET /api/health
Backend health check (used by Docker healthcheck).

**Response (200):**
```json
{
  "status": "ok",
  "data": {
    "version": "0.1.0",
    "uptime_seconds": 86400,
    "database": "connected",
    "scheduler": "running"
  }
}
```

---

## 12. Rate Limiting

| Endpoint Group | Limit |
|----------------|-------|
| `/api/auth/*` | 10 req/min per IP |
| `/api/dashboard/*` | 60 req/min |
| `/api/dag/*` | 30 req/min |
| `/api/{sources,pipelines}/*` | 120 req/min |
| `/api/*/trigger` | 10 req/min per pipeline |

---

*End of API Specification — Arus v1.0*
