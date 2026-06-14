# Tutorial: MySQL → PostgreSQL Pipeline

This tutorial walks through setting up a complete data pipeline from **MySQL to PostgreSQL** using Arus. You'll sync real e-commerce tables from a production MySQL database into your PostgreSQL warehouse.

---

## Scenario

You run an e-commerce platform with a MySQL database containing:
- `orders` — order records (updates frequently)
- `order_items` — line items per order
- `products` — product catalog (rarely changes)
- `customers` — customer information

Goal: Sync these tables into a PostgreSQL warehouse for reporting, with **orders** synced incrementally every 5 minutes and **products** synced daily via full refresh.

---

## Prerequisites

- Arus installed and running (`docker compose up -d`)
- Access to a **MySQL source database** with a read-only user
- Default PostgreSQL warehouse (created during Arus setup)

---

## Step 1: Verify Arus is Running

```bash
curl http://localhost:8081/api/health
```

Expected:
```json
{"status":"ok","data":{"version":"0.1.0","database":"connected","scheduler":"running"}}
```

---

## Step 2: Add the Source Database

Open the Arus Console at **http://localhost:8082** and log in.

### Via Console

1. Navigate to **Sources** → **+ Add Source**
2. Fill in the form:
   - **Name**: `E-Commerce MySQL`
   - **Type**: `MySQL`
   - **Host**: `192.168.1.100` (your MySQL host)
   - **Port**: `3306`
   - **Database**: `ecommerce`
   - **Username**: `arus_reader`
   - **Password**: (read-only user password)
   - **Sync Method**: `Auto-detect`
3. Click **Test Connection** to verify
4. Click **Save**

### Via API

```bash
curl -X POST http://localhost:8081/api/sources \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E-Commerce MySQL",
    "type": "mysql",
    "host": "192.168.1.100",
    "port": 3306,
    "database": "ecommerce",
    "username": "arus_reader",
    "password": "your_password",
    "sync_method": "auto"
  }'
```

**Response:**
```json
{
  "status": "ok",
  "data": { "id": "src-uuid-here", "name": "E-Commerce MySQL" }
}
```

---

## Step 3: Auto-Discover Tables

### Via Console

1. Click **Rescan** on your new source
2. Arus scans all tables and auto-detects:
   - `orders` → **Incremental** (has `updated_at`)
   - `order_items` → **Incremental** (has `updated_at`)
   - `products` → **Incremental** (has `updated_at`)
   - `customers` → **Full Refresh** (no timestamp column)

### Table Selection

Decide which tables to sync and how:

| Table | Sync Mode | Load Mode | Reason |
|-------|-----------|-----------|--------|
| `orders` | Incremental | Raw → Normalize | Frequent updates, need audit trail |
| `order_items` | Incremental | Direct | Fast, no reprocessing needed |
| `products` | Full Refresh | Direct | Small table, rarely changes, full sync daily |
| `customers` | Full Refresh | Direct | Contains PII — exclude for now |

**Exclude `customers`** by unchecking its checkbox (or configure table exclusion patterns).

### Via API — Discover Tables

```bash
curl -X POST http://localhost:8081/api/sources/{source-id}/discover \
  -H "Authorization: Bearer ***"
```

Save the source ID from the response — you'll need it.

---

## Step 4: Save Table Selection & Create Pipeline

### Via Console

1. Set the **Load Mode** for `orders` to **Raw → Normalize**
2. Set **Load Mode** for `order_items` and `products` to **Direct**
3. Click **Save Table Selection**
4. Arus auto-creates a pipeline named `E-Commerce MySQL Pipeline`

### Via API

```bash
curl -X PUT http://localhost:8081/api/sources/{source-id}/tables \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{
    "tables": [
      {
        "name": "orders",
        "sync_mode": "incremental",
        "load_mode": "raw",
        "enabled": true
      },
      {
        "name": "order_items",
        "sync_mode": "incremental",
        "load_mode": "direct",
        "enabled": true
      },
      {
        "name": "products",
        "sync_mode": "full_refresh",
        "load_mode": "direct",
        "enabled": true
      }
    ]
  }'
```

---

## Step 5: Configure Schedules

Arus created one pipeline with a default schedule (`*/5 * * * *`). But `products` only needs daily sync. Let's create a separate pipeline for it.

### Via Console

1. Go to **Pipelines** → **Add Pipeline**
2. Select the same source (`E-Commerce MySQL`)
3. Select the same destination (your default warehouse)
4. Enable only **products** table
5. Set schedule to **Daily** (or custom cron `0 6 * * *`)
6. Set sync mode to **Full Refresh**
7. Click **Save**

Now you have two pipelines:

| Pipeline | Tables | Schedule | Load Mode |
|----------|--------|----------|-----------|
| E-Commerce MySQL Pipeline | `orders`, `order_items` | Every 5 min | Raw + Direct |
| Products Daily | `products` | Daily 6 AM | Full Refresh |

### Via API

```bash
curl -X POST http://localhost:8081/api/pipelines \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Products Daily",
    "source_id": "{source-id}",
    "destination_id": "{dest-id}",
    "schedule": "0 6 * * *",
    "load_mode": "direct",
    "tables": [
      {
        "name": "products",
        "sync_mode": "full_refresh",
        "load_mode": "direct"
      }
    ]
  }'
```

---

## Step 6: Run the Pipeline

### Trigger a Manual Run

1. Go to **Pipelines**
2. Click on **E-Commerce MySQL Pipeline**
3. Click **Sync Now**

### Monitor Progress

1. Watch the **Run History** table populate
2. Click **Logs** on the latest run to see per-table details
3. Each table shows: rows extracted, rows loaded, duration

### Expected Run Flow

```
orders → Extract 1,000 rows → Load to staging.orders_raw (JSONB) → Normalize to analytics.orders
order_items → Extract 5,000 rows → Load directly to analytics.order_items
```

---

## Step 7: Verify Data in Warehouse

```bash
# Connect to warehouse
docker exec -it arus-db psql -U arus -d arus_warehouse

# Check synced schemas
\dn
#   arus_config
#   arus_run_logs
#   arus_state
#   staging
#   analytics

# Check orders in raw landing zone
SELECT _data->>'id', _data->>'total', _data->>'status'
FROM staging.e_commerce_mysql_orders_raw
LIMIT 5;

# Check normalized orders
SELECT id, total, status, _arus_synced_at
FROM analytics.orders
LIMIT 5;

# Check watermarks
SELECT source_table, watermark_value, last_synced_at
FROM arus_state.watermarks
WHERE pipeline_id = '{pipeline-id}';
```

---

## Step 8: Add a Transform

Let's mask email addresses in the `customers` table and compute a `full_name` field.

### Via Console

1. Go to **Pipelines** → Open the E-Commerce MySQL Pipeline
2. Scroll to the **Tables** section
3. Click **Transform** next to `orders`
4. Add a **Compute Field** step:
   - Expression: `total_with_tax = total * 1.11`
5. Add a **Rename Fields** step:
   - Mapping: `status` → `order_status`
6. Reorder steps if needed
7. Click **Save**

### Via API

```bash
curl -X GET http://localhost:8081/api/pipelines/{pipeline-id} \
  -H "Authorization: Bearer ***"
# Note the pipeline_table_id for "orders"

curl -X POST http://localhost:8081/api/pipelines/{pipeline-id}/tables/{table-id}/transform \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{
    "steps": [
      {
        "type": "compute",
        "config": {
          "expression": "total_with_tax = total * 1.11"
        }
      },
      {
        "type": "rename",
        "config": {
          "mapping": { "status": "order_status" }
        }
      }
    ]
  }'
```

---

## Step 9: Set Up Notifications

1. Go to **Notifications** → **+ Add Target**
2. Choose **Telegram** (or Discord/Slack)
3. Enter your bot token and chat ID
4. Click **Save**
5. Go back to your pipeline → Click **Notifications**
6. Link the notification target and select events: **Failure**, **Dead Letter**

Now you'll get alerts when something goes wrong.

---

## Step 10: Backfill Historical Data

If you want to sync all historical data before the first incremental run:

1. Go to **Pipelines** → Open the E-Commerce MySQL Pipeline
2. Click the **dropdown menu** (⋮) → **Backfill**
3. Enter a start date: `2024-01-01`
4. Click **Confirm**

Arus will reset watermarks and re-sync all data from the specified date. After backfill completes, incremental sync continues from the latest watermark.

### Via API

```bash
curl -X POST http://localhost:8081/api/pipelines/{pipeline-id}/backfill \
  -H "Authorization: Bearer ***" \
  -H "Content-Type: application/json" \
  -d '{"from_date": "2024-01-01"}'
```

---

## Summary

You've successfully:

- ✅ Connected a MySQL source database
- ✅ Set up 2 pipelines with different schedules
- ✅ Configured Raw + Direct load modes
- ✅ Run a pipeline and verified data in the warehouse
- ✅ Added a transform to process data
- ✅ Configured notifications for failure alerts
- ✅ Performed a historical backfill

This same pattern applies to any source-destination combination. The key configuration decisions are:

1. **Sync mode**: Incremental for frequently updated tables, Full Refresh for small/static tables
2. **Load mode**: Raw → Normalize for tables needing audit trail, Direct for performance
3. **Schedule**: Frequent for critical tables, daily/weekly for reference data
4. **Transforms**: Applied per-table, after extraction and before loading

## Next Steps

- Explore the [Architecture](/guide/architecture) to understand system internals
- Read the [Connectors Guide](/guide/connectors) to learn about available source/destination types
- Check the [Config Reference](/reference/configuration) for all pipeline options
- Set up [Monitoring](/guide/monitoring) for production observability
