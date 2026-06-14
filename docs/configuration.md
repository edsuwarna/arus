# Configuration Reference

Arus uses a combination of **environment variables** (for infrastructure-level config) and **runtime settings** (for user-level config managed through the UI).

---

## Environment Variables

Set these in `.env` or pass them to the `arus-api` container.

### Database

| Variable | Default | Description |
|---|---|---|
| `ARUS_DB_HOST` | `localhost` | PostgreSQL host for warehouse + config |
| `ARUS_DB_PORT` | `5432` | PostgreSQL port |
| `ARUS_DB_USER` | `arus` | PostgreSQL user |
| `ARUS_DB_PASSWORD` | `arus_secret` | PostgreSQL password |
| `ARUS_DB_NAME` | `arus_warehouse` | PostgreSQL database name |

### Authentication & Security

| Variable | Default | Description |
|---|---|---|
| `ARUS_JWT_SECRET` | `change-me-in-production` | JWT signing secret. **Must be changed in production.** |
| `ARUS_ENCRYPTION_KEY` | (derived from JWT secret) | Fernet encryption key for stored credentials. **Set a unique value in production.** |

### Logging

| Variable | Default | Description |
|---|---|---|
| `ARUS_LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `TZ` | `UTC` | Timezone for logs and scheduling |

### Pipeline Defaults

| Variable | Default | Description |
|---|---|---|
| `ARUS_DEFAULT_SCHEDULE` | `*/5 * * * *` | Default cron expression for new pipelines |
| `ARUS_BATCH_SIZE` | `10000` | Rows per batch when extracting from sources |
| `ARUS_RETRY_MAX` | `3` | Maximum retry attempts for failed extractions/loads |
| `ARUS_AUTO_ALTER_SCHEMA` | `false` | Auto-add new columns to warehouse tables on schema drift |
| `ARUS_QUALITY_CHECK_THRESHOLD` | `5.0` | Max allowed row count discrepancy percentage |

### Alerts (Telegram)

| Variable | Default | Description |
|---|---|---|
| `ARUS_TELEGRAM_BOT_TOKEN` | (empty) | Telegram bot token for pipeline failure alerts |
| `ARUS_TELEGRAM_CHAT_ID` | (empty) | Telegram chat ID to receive alerts |

### Docker Compose Defaults

| Variable | Default | Description |
|---|---|---|
| `ARUS_DB_USER` (docker) | `arus` | PostgreSQL user (separate env for Docker) |
| `ARUS_DB_PASSWORD` (docker) | `arus_secret` | PostgreSQL password (separate env for Docker) |
| `ARUS_DB_NAME` (docker) | `arus_warehouse` | PostgreSQL database (separate env for Docker) |

---

## Runtime Settings (UI-Managed)

These settings are stored in the `arus_config.runtime_settings` table and can be modified through the Console **Settings** page (admin only). They override environment variable defaults.

### General

| Key | Default | Description |
|---|---|---|
| `pipeline_name_prefix` | `arus-prod-` | Prefix for auto-generated pipeline names |
| `default_schedule` | `*/5 * * * *` | Default cron expression for new pipelines |
| `auto_discover_tables` | `true` | Enable auto-discovery of tables when adding sources |
| `schema_drift_detection` | `true` | Enable schema drift detection during pipeline runs |
| `auto_alter_schema` | `false` | Auto-add new columns when schema drift is detected |

### Quality & Retry

| Key | Default | Description |
|---|---|---|
| `max_retries` | `3` | Maximum retry attempts for failed operations |
| `initial_backoff` | `2` | Initial backoff in seconds (doubles each retry) |
| `quality_check_threshold` | `5.0` | Max allowed row count discrepancy as percentage |

### Notifications

| Key | Default | Description |
|---|---|---|
| `notify_pipeline_failures` | `true` | Send alerts on pipeline failures |
| `notify_schema_drift` | `true` | Send alerts on schema drift detection |
| `notify_dead_letter` | `true` | Send alerts when rows are moved to dead letter queue |

---

## Connector Configuration

### Source Connector Config

| Field | Type | Description |
|---|---|---|
| `name` | string | Display name for the source |
| `type` | string | `mysql`, `mariadb`, `postgresql`, `mongodb` |
| `host` | string | Source database host |
| `port` | integer | Source database port |
| `database` | string | Source database name |
| `username` | string | Source database username |
| `password` | string | Source database password (encrypted at rest) |
| `ssl` | boolean | Enable SSL connection |
| `uri` | string (MongoDB only) | MongoDB connection string |
| `auth_source` | string (MongoDB only) | MongoDB authentication database |
| `sync_method` | string | `auto`, `incremental`, `full_refresh` |
| `table_include` | string[] | Glob patterns for including tables (e.g., `+orders*`) |
| `table_exclude` | string[] | Glob patterns for excluding tables (e.g., `-audit_*`) |
| `schema_include` | string[] | PostgreSQL schemas to scan |

### Destination Connector Config

| Field | Type | Description |
|---|---|---|
| `name` | string | Display name for the destination |
| `type` | string | `postgresql`, `mysql`, `clickhouse` |
| `host` | string | Destination host |
| `port` | integer | Destination port |
| `database` | string | Destination database name |
| `username` | string | Destination username |
| `password` | string | Destination password (encrypted at rest) |
| `raw_schema` | string | Schema for raw landing zone (default: `staging`) |
| `target_schema` | string | Schema for normalized tables (default: `analytics`) |
| `is_default` | boolean | Set as default destination for auto-created pipelines |

---

## Pipeline Config

| Parameter | Default | Description |
|---|---|---|
| `name` | — | Pipeline display name |
| `source_id` | — | Reference to configured source |
| `destination_id` | — | Reference to configured destination |
| `schedule` | `*/5 * * * *` | Cron expression |
| `target_schema` | `public` | Target analytics schema |
| `load_mode` | `direct` | `direct` (source → analytics) or `raw` (source → staging → analytics) |
| `depends_on` | `null` | Pipeline dependency (pipeline ID) |
| `max_retries` | `3` | Per-pipeline retry override |
| `timeout_seconds` | `300` | Pipeline timeout in seconds |

### Per-Table Config

| Parameter | Default | Description |
|---|---|---|
| `source_table` | — | Table name in source database |
| `sync_mode` | `incremental` | `incremental` or `full_refresh` |
| `load_mode` | `direct` | `direct` or `raw` |
| `watermark_column` | auto-detected | Column used for incremental tracking |
| `target_schema` | pipeline default | Override target schema per table |
| `transform_config` | `null` | Array of transform step objects |
| `enabled` | `true` | Enable/disable table sync |

---

## Transform Step Config

Each transform step has a `type` and `config` object:

### Rename Fields

```json
{
  "type": "rename",
  "config": {
    "mapping": {
      "first_name": "fname",
      "last_name": "lname"
    }
  }
}
```

### Remove Fields

```json
{
  "type": "remove_fields",
  "config": {
    "fields": ["internal_note", "temp_field"]
  }
}
```

### Compute Field

```json
{
  "type": "compute",
  "config": {
    "expression": "full_name = first_name + ' ' + last_name"
  }
}
```

### Filter Rows

```json
{
  "type": "filter",
  "config": {
    "condition": "status != 'deleted'"
  }
}
```

### Map Values

```json
{
  "type": "map_values",
  "config": {
    "column": "status",
    "mapping": {
      "1": "active",
      "0": "inactive"
    }
  }
}
```

### Type Cast

```json
{
  "type": "type_cast",
  "config": {
    "columns": {
      "price": "float",
      "is_active": "bool",
      "count": "int"
    }
  }
}
```

### Concat Fields

```json
{
  "type": "concat_fields",
  "config": {
    "fields": ["first_name", "last_name"],
    "separator": " ",
    "target": "full_name",
    "drop_source": false
  }
}
```

### Python Script

```json
{
  "type": "script",
  "config": {
    "script_name": "clean_orders"
  }
}
```

The script must define a function `transform(row: dict) -> dict | None`:
```python
def transform(row):
    row["email_domain"] = row["email"].split("@")[1] if row.get("email") else None
    return row
```
