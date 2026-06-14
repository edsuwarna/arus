# Pipeline System

The pipeline system is the core orchestration engine of Arus. It manages the complete lifecycle of data ingestion: extraction, transformation, loading, and state tracking.

---

## Pipeline Lifecycle

```
                  ┌──────────────┐
                  │  Scheduled   │ (APScheduler cron trigger)
                  │  or Manual   │ (UI "Sync Now" or API)
                  └──────┬───────┘
                         ▼
                  ┌──────────────┐
                  │ Dependency   │── No ──→ Status: SKIPPED
                  │ Satisfied?   │
                  └──────┬───────┘
                         │ Yes
                         ▼
                  ┌──────────────┐
                  │ Create Run   │ (arus_run_logs.runs)
                  │ Record       │
                  └──────┬───────┘
                         ▼
            ┌─────────────────────────┐
            │  For each enabled table │ ◀──────────────┐
            │  in the pipeline:       │                │
            │  1. Ensure schema       │                │
            │  2. Detect schema drift │                │
            │  3. Extract (with retry)│                │
            │  4. Apply transforms    │                │
            │  5. Load raw (if raw    │                │
            │     mode)               │                │
            │  6. Load normalized     │                │
            │  7. Update watermark    │                │
            │  8. Soft-delete sync    │                │
            │  9. Quality checks      │                │
            └──────────┬──────────────┘                │
                       │ More tables? ─────────────────┘
                       ▼ No
            ┌──────────────────┐
            │ Update Run       │
            │ Record           │
            └────────┬─────────┘
                     ▼
            ┌──────────────────┐
            │ Send Notification│ (success/failure)
            │ (if configured)  │
            └──────────────────┘
```

---

## Pipeline Executor

**File**: `arus/modules/pipeline/executor.py`

The `PipelineExecutor` class runs a single pipeline cycle. Key features:

### Retry with Exponential Backoff

Uses `tenacity` to retry failed extractions and loads:

```python
retry(
    stop=stop_after_attempt(settings.max_retries),     # default: 3
    wait=wait_exponential(
        multiplier=settings.initial_backoff,             # default: 2s
        min=settings.initial_backoff,
        max=settings.initial_backoff * 8,               # max: 16s
    ),
    reraise=True,
)
```

### Timeout

Each pipeline run is wrapped in a thread-based timeout:

```python
executor = ThreadPoolExecutor(max_workers=1)
future = executor.submit(self._run_inner, ...)
result = future.result(timeout=timeout_seconds)  # default: 300s (5 min)
```

### Pipeline Dependencies

Before executing, the executor checks if upstream dependencies are satisfied:

- If pipeline B depends on pipeline A, B waits for A's latest run to complete successfully
- If the dependency check fails, the run is marked as **skipped**
- Implemented in `arus/modules/pipeline/deps.py`

---

## Scheduler

**File**: `arus/modules/pipeline/scheduler.py`

Uses **APScheduler** for cron-based scheduling:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = BackgroundScheduler()

def start_scheduler():
    scheduler.start()

def add_pipeline_job(pipeline_id: str, cron_expression: str):
    trigger = CronTrigger.from_crontab(cron_expression)
    scheduler.add_job(
        func=run_pipeline_job,
        trigger=trigger,
        id=f"pipeline_{pipeline_id}",
        replace_existing=True,
        args=[pipeline_id],
    )

def remove_pipeline_job(pipeline_id: str):
    scheduler.remove_job(f"pipeline_{pipeline_id}")
```

On startup, the scheduler loads all active pipelines and registers their cron jobs:

```python
@app.on_event("startup")
async def startup():
    start_scheduler()
    load_scheduled_pipelines()  # Loads all active pipelines from DB
```

---

## Load Modes

### Direct Mode (Default)

```
Source Table ──→ analytics.<table> (typed columns)
```

Rows are loaded directly into the analytics schema without intermediate JSONB storage. Suitable for stable schemas where reprocessing isn't needed.

### Raw Mode

```
Source Table ──→ staging.<source>_<table>_raw (JSONB)
                     ──→ analytics.<table> (typed columns)
```

Rows are first stored as raw JSONB in staging, then normalized into the analytics schema. Useful for:
- Schema drift resilience (new columns don't break raw ingestion)
- Reprocessing/recovery
- Audit trails

---

## Schema Drift Detection

**Implemented in**: `PipelineExecutor._detect_schema_drift()`

During each pipeline run, the executor compares source columns against warehouse columns:

1. Query `information_schema.columns` for the target table
2. Compare with source column names (case-insensitive)
3. If new columns are found:
   - Log warning: `[SCHEMA DRIFT] Table <table> missing columns: <cols>`
   - Send alert if configured
   - If `auto_alter_schema` is enabled, execute `ALTER TABLE` to add new columns

---

## Soft-Delete Reconciliation

For tables with a `deleted_at` column:

1. After incremental extract, query for newly soft-deleted rows:
   - `WHERE deleted_at IS NOT NULL AND deleted_at > watermark`
2. Delete matching rows from the analytics table by primary key
3. Supported by MySQL and PostgreSQL sources (MongoDB via `extract_soft_deletes`)

---

## Dead Letter Queue

**File**: `arus/modules/pipeline/dead_letter.py`

When a row fails to load after all retries, it's saved to `staging._dead_letters`:

```sql
CREATE TABLE staging._dead_letters (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name     VARCHAR(255) NOT NULL,
    table_name      VARCHAR(255) NOT NULL,
    run_id          UUID NOT NULL,
    row_data        JSONB NOT NULL,
    error_text      TEXT,
    failed_at       TIMESTAMPTZ DEFAULT NOW()
);
```

Failed rows can be reviewed and reprocessed via the Console **Pipeline Detail** → **Dead Letters** view.

---

## Data Quality Checks

**File**: `arus/modules/pipeline/quality.py`

Two checks run after each table load:

### Row Count Validation

Compares extracted row count vs loaded row count:

```
discrepancy = abs(rows_extracted - rows_loaded) / rows_extracted * 100
passed = discrepancy <= threshold  # threshold default: 5%
```

### Null Check on Required Columns

For columns marked `NOT NULL` in the source, checks for null values in loaded rows. Nulls are flagged as a warning.

Results are persisted to `arus_config.data_quality_log` for auditability.

---

## Transform Engine

**File**: `arus/modules/transform/engine.py`

Transforms run between extraction and loading. Steps are applied sequentially:

```python
for step in transform_config:
    rows = handler(rows, step["config"])
```

### Built-in Step Types

| Type | Description |
|---|---|
| `rename` | Rename columns via mapping |
| `remove_fields` | Drop columns |
| `compute` | Compute new field from expression |
| `filter` | Filter rows by condition |
| `map_values` | Map column values via lookup |
| `type_cast` | Cast column types |
| `concat_fields` | Concatenate fields into one |

### Python Scripts

Custom transform scripts stored in the `arus_config.transform_scripts` table. Each script must define:

```python
def transform(row: dict) -> dict | None:
    # Modify row in place or return new dict
    # Return None to drop the row
    return row
```

---

## Pipeline Dependency Resolution

**File**: `arus/modules/pipeline/deps.py`

Pipelines can declare dependencies on other pipelines. The `DependencyResolver`:

1. Checks if the upstream pipeline has a successful run
2. If not, marks the dependent pipeline as **skipped**
3. Prevents circular dependencies

---

## Notification System

**File**: `arus/modules/notification/`

Notifications can be sent for these events:

| Event Type | Description |
|---|---|
| `failure` | Pipeline run failed |
| `success` | Pipeline run completed successfully |
| `dead_letter` | Rows moved to dead letter queue |
| `schema_drift` | New columns detected in source |
| `quality_breach` | Data quality check threshold breached |

### Notification Targets

| Target Type | Configuration |
|---|---|
| **Telegram** | Bot Token + Chat ID |
| **Discord** | Webhook URL |
| **Slack** | Webhook URL |

### Pipeline-Notification Linking

Each pipeline can be linked to multiple notification targets with specific event types. Managed via the **Notifications** page in the Console.

---

## API Endpoints

See [API Reference](/reference/api) for full endpoint documentation.

| Endpoint | Purpose |
|---|---|
| `GET /api/pipelines` | List all pipelines |
| `POST /api/pipelines` | Create pipeline |
| `GET /api/pipelines/{id}` | Get pipeline detail |
| `PUT /api/pipelines/{id}` | Update pipeline |
| `DELETE /api/pipelines/{id}` | Delete pipeline |
| `POST /api/pipelines/{id}/trigger` | Trigger manual run |
| `POST /api/pipelines/{id}/pause` | Pause schedule |
| `POST /api/pipelines/{id}/resume` | Resume schedule |
| `POST /api/pipelines/{id}/full-refresh` | Full refresh all tables |
| `POST /api/pipelines/{id}/backfill` | Backfill from date |
| `GET /api/pipelines/{id}/runs` | List pipeline runs |
| `GET /api/pipelines/{id}/dead-letters` | View dead letter rows |
| `GET /api/pipelines/{id}/scripts` | List transform scripts |
| `POST /api/pipelines/{id}/scripts` | Create transform script |
| `GET /api/runs` | List all runs (global) |
| `GET /api/runs/{id}` | Get run detail |
| `GET /api/runs/{id}/logs` | Get run logs |
| `POST /api/runs/{id}/cancel` | Cancel running run |
| `POST /api/runs/{id}/retry` | Retry failed run |
