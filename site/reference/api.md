# API Reference

Arus exposes a **REST API** on port 8081. All endpoints return JSON with a consistent response envelope.

---

## Response Format

### Success

```json
{
  "status": "ok",
  "data": { ... }
}
```

### Error

```json
{
  "status": "error",
  "error": {
    "code": "AUTH_FAILED",
    "message": "Invalid email or password"
  }
}
```

### Error Codes

| HTTP Status | Code | Description |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Invalid request body |
| 401 | `AUTH_FAILED` | Authentication failure |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Resource conflict |
| 422 | `VALIDATION_ERROR` | Request validation failure |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 502 | `CONNECTION_FAILED` | Database connection error |

---

## Authentication

All endpoints except `/api/auth/login` and `/api/health` require JWT authentication.

### Headers

```
Authorization: Bearer <access_token>
X-Refresh-Token: <refresh_token>   (for refresh endpoint)
```

### POST /api/auth/login

Authenticate and receive JWT tokens.

**Request:**
```json
{
  "email": "admin@arus.io",
  "password": "admin123"
}
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "access_token": "eyJhbGci...",
    "refresh_token": "eyJhbGci...",
    "expires_in": 900,
    "refresh_expires_in": 604800,
    "user": {
      "id": "uuid",
      "email": "admin@arus.io",
      "name": "Arus Admin",
      "role": "admin"
    },
    "expires_at": "2026-01-01T00:00:00+00:00"
  }
}
```

### POST /api/auth/refresh

Refresh an expired access token.

**Headers:** `X-Refresh-Token: <refresh_token>`

### GET /api/auth/me

Get current user info from the access token.

### POST /api/auth/logout

Stateless logout (client-side token removal).

---

## User Management (Admin Only)

### GET /api/auth/users

List all users. Query params: `limit`, `offset`.

### POST /api/auth/users

Create a new user.

```json
{
  "email": "user@example.com",
  "name": "User Name",
  "password": "secure_pass",
  "role": "viewer"
}
```

### PATCH /api/auth/users/`{id}`

Update user fields. Fields are optional.

```json
{
  "name": "New Name",
  "role": "editor",
  "is_active": true
}
```

### DELETE /api/auth/users/`{id}`

Delete a user (cannot delete self).

---

## Sources

### GET /api/sources

List all source connections. Query params: `limit`, `offset`.

### POST /api/sources

Create a new source connection.

```json
{
  "name": "Production DB",
  "type": "mysql",
  "host": "db.example.com",
  "port": 3306,
  "database": "mydb",
  "username": "reader",
  "password": "secret",
  "sync_method": "auto",
  "table_include": ["+orders*", "+users*"],
  "table_exclude": ["-audit_*"]
}
```

### GET /api/sources/`{id}`

Get source connection details.

### PUT /api/sources/`{id}`

Update source connection. All fields optional.

### DELETE /api/sources/`{id}`

Delete source connection.

### POST /api/sources/`{id}`/test

Test the source connection.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "connected": true
  }
}
```

### POST /api/sources/`{id}`/discover

Auto-discover tables and detect sync modes.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "source_id": "uuid",
    "tables": [
      {
        "name": "orders",
        "schema": "public",
        "row_count_estimate": 50000,
        "columns": [...],
        "detected_sync": "incremental",
        "watermark_column": "updated_at",
        "enabled": true
      }
    ]
  }
}
```

### POST /api/sources/`{id}`/schemas

Discover available schemas (PostgreSQL only).

### PUT /api/sources/`{id}`/tables

Update table selection and auto-create pipeline.

```json
{
  "tables": [
    {
      "name": "orders",
      "sync_mode": "incremental",
      "load_mode": "direct",
      "enabled": true
    }
  ]
}
```

---

## Destinations

### GET /api/destinations

List all destinations.

### POST /api/destinations

Create a destination.

```json
{
  "name": "Warehouse",
  "type": "postgresql",
  "host": "arus-db",
  "port": 5432,
  "database": "arus_warehouse",
  "username": "arus",
  "password": "arus_secret",
  "raw_schema": "staging",
  "target_schema": "analytics",
  "is_default": true
}
```

### GET /api/destinations/`{id}`

Get destination details.

### PUT /api/destinations/`{id}`

Update destination.

### DELETE /api/destinations/`{id}`

Delete destination.

### POST /api/destinations/`{id}`/test

Test destination connection.

---

## Pipelines

### GET /api/pipelines

List all pipelines. Query params: `limit`, `offset`.

### POST /api/pipelines

Create a pipeline.

```json
{
  "name": "Orders Pipeline",
  "source_id": "uuid",
  "destination_id": "uuid",
  "schedule": "*/5 * * * *",
  "target_schema": "analytics",
  "load_mode": "direct",
  "tables": [
    {
      "name": "orders",
      "load_mode": "direct",
      "sync_mode": "incremental",
      "watermark_column": "updated_at"
    }
  ],
  "depends_on": null
}
```

### GET /api/pipelines/`{id}`

Get pipeline detail with tables, stats, and last run info.

### PUT /api/pipelines/`{id}`

Update pipeline configuration.

### DELETE /api/pipelines/`{id}`

Delete pipeline.

### POST /api/pipelines/`{id}`/trigger

Trigger an immediate pipeline run.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "run_id": "uuid",
    "status": "running",
    "started_at": "2026-01-01T00:00:00Z"
  }
}
```

### POST /api/pipelines/`{id}`/pause

Pause the pipeline schedule.

### POST /api/pipelines/`{id}`/resume

Resume the pipeline schedule.

### POST /api/pipelines/`{id}`/full-refresh

Trigger a full refresh (reset watermarks, re-sync all data).

### POST /api/pipelines/`{id}`/backfill

Trigger a backfill from a specific date.

```json
{
  "from_date": "2024-01-01"
}
```

### GET /api/pipelines/`{id}`/dead-letters

Get dead letter queue entries for this pipeline. Query params: `limit`.

### POST /api/pipelines/pause-all

Pause all pipelines.

### POST /api/pipelines/resume-all

Resume all pipelines.

---

## Runs & Run Logs

### GET /api/pipelines/`{id}`/runs

List runs for a specific pipeline. Query params: `limit`, `offset`.

### GET /api/runs

List all runs globally. Query params: `limit`, `offset`, `status` (success/failed/running), `pipeline_id`.

### GET /api/runs/`{id}`

Get run details.

### GET /api/runs/`{id}`/logs

Get run log entries. Query params: `limit`, `offset`.

### POST /api/runs/`{id}`/cancel

Cancel a running/pending run.

### POST /api/runs/`{id}`/retry

Retry a failed/cancelled run.

### GET /api/runs/stats/daily

Get daily run statistics for dashboard chart. Query params: `days` (default: 7).

---

## Dashboard

### GET /api/dashboard/summary

Get dashboard summary stats.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "total_sources": 3,
    "total_pipelines": 5,
    "active_pipelines": 4,
    "total_rows_synced": 1500000,
    "rows_synced_24h": 50000,
    "failed_runs_24h": 0,
    "unique_tables": 12
  }
}
```

### GET /api/dashboard/recent-runs

Get latest runs for the dashboard feed.

---

## DAG

### GET /api/dag

Get the full pipeline dependency graph with three-layer asset structure (Source → Raw → Target or Source → Target for direct mode).

---

## Settings (Admin Only)

### GET /api/settings

Get all runtime settings as key-value map.

### PUT /api/settings

Update runtime settings.

```json
{
  "pipeline_name_prefix": "arus-prod-",
  "max_retries": "3"
}
```

---

## Transform Scripts

### GET /api/pipelines/`{id}`/scripts

List transform scripts for a pipeline.

### POST /api/pipelines/`{id}`/scripts

Create a transform script.

```json
{
  "name": "clean_orders",
  "description": "Cleans order data",
  "content": "def transform(row):\n    row['email_domain'] = row['email'].split('@')[1] if row.get('email') else None\n    return row"
}
```

### GET /api/pipelines/`{id}`/scripts/`{script_id}`

Get script details.

### PUT /api/pipelines/`{id}`/scripts/`{script_id}`

Update script.

### DELETE /api/pipelines/`{id}`/scripts/`{script_id}`

Delete script.

---

## Notifications

### GET /api/notifications/targets

List notification targets.

### POST /api/notifications/targets

Create a notification target.

```json
{
  "name": "Team Alerts",
  "type": "telegram",
  "config": {
    "bot_token": "123456:ABC-DEF",
    "chat_id": "-123456789"
  },
  "active": true
}
```

### PUT /api/notifications/targets/`{id}`

Update notification target.

### DELETE /api/notifications/targets/`{id}`

Delete notification target.

### POST /api/notifications/targets/`{id}`/test

Send a test notification.

### GET /api/notifications/links/{pipeline_id}

Get notification links for a pipeline.

### POST /api/notifications/links

Create a pipeline-notification link.

```json
{
  "pipeline_id": "uuid",
  "target_id": "uuid",
  "events": ["failure", "dead_letter", "schema_drift"]
}
```

### PUT /api/notifications/links/`{id}`

Update notification link.

### DELETE /api/notifications/links/`{id}`

Delete notification link.

---

## Health

### GET /api/health

Simple health check.

**Response:**
```json
{
  "status": "ok",
  "data": {
    "version": "0.1.0",
    "database": "connected",
    "scheduler": "running"
  }
}
```
