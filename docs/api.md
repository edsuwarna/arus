# API Reference

REST API for the Arus backend. Base URL: `http://localhost:8081/api`

## Conventions

### Authentication
All endpoints except `/auth/login` require a Bearer token in the `Authorization` header:

```
Authorization: Bearer eyJhbG...
```

### Response Format

```json
{
  "status": "ok",
  "data": { ... }
}
```

### Error Format

```json
{
  "status": "error",
  "error": {
    "code": "NOT_FOUND",
    "message": "Source with id 'abc-123' not found"
  }
}
```

### Pagination

```
?page=1&per_page=20

{
  "data": [...],
  "pagination": {
    "page": 1, "per_page": 20,
    "total": 147, "total_pages": 8
  }
}
```

## Authentication

### `POST /api/auth/login`

Login with email + password. Returns access + refresh token pair and user profile.

```json
{ "email": "admin@arus.io", "password": "admin123" }
```

Response: `{ "access_token": "eyJ...", "refresh_token": "eyJ...", "expires_in": 900, "refresh_expires_in": 604800, "user": { "id", "email", "name", "role" }, "expires_at" }`

Access token expires in **15 minutes**. Use the refresh token to get a new pair.

### `POST /api/auth/logout`

Logout — invalidates session on client side. JWT tokens are stateless.

Requires Bearer token. Returns confirmation.

### `GET /api/auth/me`

Get current user profile.

Requires Bearer token.

### `POST /api/auth/refresh`

Refresh access token using a refresh token.

Pass refresh token in `X-Refresh-Token` header (no Bearer prefix). Returns a new access + refresh token pair.

## Sources

### `GET /api/sources`

List all registered source databases. Supports pagination, type filter, and search.

Query: `?page=1&per_page=20&type=mysql&search=prod`

### `POST /api/sources`

Register a new source database.

```json
{ "name": "Production MySQL", "type": "mysql", "host": "10.0.0.50", "port": 3306, "database": "ecommerce", "username": "reader", "password": "readonly_pass" }
```

### `GET /api/sources/{id}`

Get source details.

### `DELETE /api/sources/{id}`

Delete a source database.

### `POST /api/sources/{id}/test`

Test connection to source database. Returns latency and server version.

### `POST /api/sources/{id}/discover`

Scan source database and auto-detect all tables with their sync modes (incremental / full refresh).

### `POST /api/sources/{id}/schemas`

Discover available schemas in the source database. Returns a list of schema names.

### `PUT /api/sources/{id}/tables`

Update which tables are enabled/disabled and configure per-table settings.

```json
{ "tables": [{ "name": "orders", "enabled": true, "sync_mode": "incremental", "watermark_column": "updated_at" }] }
```

## Pipelines

### `GET /api/pipelines`

List all pipelines. Supports pagination and status filter.

### `POST /api/pipelines`

Create a new pipeline (one per source DB).

```json
{ "source_id": "src_001", "destination_id": "dest_001", "schedule": "*/5 * * * *", "target_schema": "target" }
```

### `GET /api/pipelines/{id}`

Get pipeline details with table configurations.

### `DELETE /api/pipelines/{id}`

Delete a pipeline and unschedule its jobs.

### `POST /api/pipelines/{id}/trigger`

Manually trigger a pipeline run.

### `POST /api/pipelines/{id}/pause`

Pause pipeline scheduler.

### `POST /api/pipelines/{id}/resume`

Resume pipeline scheduler.

## Transform Scripts

### `GET /api/pipelines/{pipeline_id}/scripts`

List transform scripts for a pipeline. Per-pipeline Python scripts run between raw and target load.

### `POST /api/pipelines/{pipeline_id}/scripts`

Create a transform script. Name must be unique per pipeline.

```json
{ "name": "normalize_users", "description": "Normalize user data", "content": "def transform(row):\n    row['email'] = row['email'].lower()\n    return row" }
```

### `GET /api/pipelines/{pipeline_id}/scripts/{script_id}`

Get a specific transform script by ID.

### `PUT /api/pipelines/{pipeline_id}/scripts/{script_id}`

Update a transform script.

### `DELETE /api/pipelines/{pipeline_id}/scripts/{script_id}`

Delete a transform script.

## Dashboard & Monitoring

### `GET /api/dashboard/summary`

Get dashboard stats: active sources, pipelines, rows synced, failures, uptime %, avg latency, and new sources this week.

### `GET /api/dashboard/recent-runs`

Get recent pipeline runs. Supports `?limit=10` (max 50). Returns run ID, status, rows synced, and duration.

### `GET /api/dag/{pipeline_id}`

Get DAG asset graph data (3-layer: Source → Raw → Target) with node statuses.

### `GET /api/runs`

List run history. Supports pagination and pipeline_id filter.

### `GET /api/runs/{id}`

Get run details with per-table results and logs.

### `GET /api/health`

Health check. Returns version, database status, and scheduler state.

```json
{ "status": "ok", "data": { "version": "0.1.0", "database": "connected", "scheduler": "running" } }
```

## Destinations

### `GET /api/destinations`

List all destinations. Supports pagination.

### `POST /api/destinations`

Register a new destination warehouse connection.

```json
{ "name": "Warehouse", "type": "postgresql", "host": "10.0.0.10", "port": 5432, "database": "warehouse", "username": "arus", "password": "secret", "raw_schema": "raw", "target_schema": "target" }
```

### `GET /api/destinations/{id}`

Get destination details.

### `PUT /api/destinations/{id}`

Update a destination.

### `POST /api/destinations/{id}/test`

Test connection to destination warehouse. Returns connected status and error message if failed.

### `DELETE /api/destinations/{id}`

Delete a destination.

## Notifications

### `GET /api/notifications/targets`

List all notification targets (Telegram, Discord, Slack).

### `POST /api/notifications/targets`

Create a notification target.

```json
{ "name": "Team Alerts", "type": "telegram", "config": { "bot_token": "...", "chat_id": "..." }, "is_active": true }
```

Supported types: `telegram`, `discord`, `slack`.

### `PUT /api/notifications/targets/{target_id}`

Update a notification target.

### `DELETE /api/notifications/targets/{target_id}`

Delete a notification target.

### `POST /api/notifications/targets/{target_id}/test`

Send a test notification. Optionally specify `event_type` in body to test a specific template.

```json
{ "event_type": "pipeline_failed" }
```

### `GET /api/notifications/links/{pipeline_id}`

List notification links for a pipeline — which targets get notified for which events.

### `POST /api/notifications/links`

Link a notification target to a pipeline with event types.

```json
{ "pipeline_id": "pl_001", "target_id": "nt_001", "event_types": ["pipeline_failed", "pipeline_success", "schema_drift"] }
```

### `PUT /api/notifications/links/{link_id}`

Update a pipeline notification link (event types).

### `DELETE /api/notifications/links/{link_id}`

Delete a pipeline notification link.

## Settings & Users

### `GET /api/settings`

Get all runtime settings (key-value from DB).

### `PUT /api/settings`

Update settings.

### `GET /api/auth/users`

List users (admin only). Supports pagination.

### `POST /api/auth/users`

Create user (admin only). Roles: viewer, editor, admin.

```json
{ "email": "newuser@example.com", "name": "New User", "password": "secret123", "role": "editor" }
```

### `PATCH /api/auth/users/{user_id}`

Update user fields (admin only). Email, name, role, password, or is_active.

```json
{ "name": "Updated Name", "role": "admin" }
```

---

📖 OpenAPI spec available via `/docs` when the API is running.
