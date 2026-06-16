# Quickstart Guide

Get Arus up and running in under 5 minutes.

---

## Prerequisites

- **Docker** & **Docker Compose** (v2+)
- At least **2 CPU cores** and **4GB RAM**

---

## Installation

### 1. Save the Docker Compose File

Create a file named `docker-compose.yml` with the following content:

```yaml
# docker-compose.yml
version: "3.8"

services:
  arus-db:
    image: postgres:15-alpine
    container_name: arus-db
    environment:
      POSTGRES_USER: ${ARUS_DB_USER:-arus}
      POSTGRES_PASSWORD: ${ARUS_DB_PASSWORD:-arus_secret}
      POSTGRES_DB: ${ARUS_DB_NAME:-arus_warehouse}
    volumes:
      - arus-db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U arus"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - arus-net
    restart: unless-stopped

  arus-api:
    image: ghcr.io/edsuwarna/arus/api:latest
    container_name: arus-api
    environment:
      ARUS_DB_HOST: arus-db
      ARUS_DB_PORT: "5432"
      ARUS_DB_USER: ${ARUS_DB_USER:-arus}
      ARUS_DB_PASSWORD: ${ARUS_DB_PASSWORD:-arus_secret}
      ARUS_DB_NAME: ${ARUS_DB_NAME:-arus_warehouse}
      ARUS_JWT_SECRET: ${ARUS_JWT_SECRET:-}
      ARUS_ENCRYPTION_KEY: ${ARUS_ENCRYPTION_KEY:-}
      ARUS_LOG_LEVEL: ${ARUS_LOG_LEVEL:-INFO}
      ARUS_DEFAULT_SCHEDULE: ${ARUS_DEFAULT_SCHEDULE:-*/5 * * * *}
      ARUS_BATCH_SIZE: ${ARUS_BATCH_SIZE:-10000}
      ARUS_RETRY_MAX: ${ARUS_RETRY_MAX:-3}
      ARUS_AUTO_ALTER_SCHEMA: ${ARUS_AUTO_ALTER_SCHEMA:-false}
      ARUS_QUALITY_CHECK_THRESHOLD: ${ARUS_QUALITY_CHECK_THRESHOLD:-5.0}
      ARUS_TELEGRAM_BOT_TOKEN: ${ARUS_TELEGRAM_BOT_TOKEN:-}
      ARUS_TELEGRAM_CHAT_ID: ${ARUS_TELEGRAM_CHAT_ID:-}
      TZ: ${TZ:-UTC}
    ports:
      - "8081:8081"
    depends_on:
      arus-db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - arus-net
    restart: unless-stopped

  arus-console:
    image: ghcr.io/edsuwarna/arus/console:latest
    container_name: arus-console
    ports:
      - "8082:80"
    depends_on:
      arus-api:
        condition: service_healthy
    networks:
      - arus-net
    restart: unless-stopped

volumes:
  arus-db-data:

networks:
  arus-net:
    driver: bridge
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your preferred values:

```bash
# Required: Change these in production
ARUS_JWT_SECRET=your-secret-key-change-me
ARUS_ENCRYPTION_KEY=your-encryption-key-change-me

# Optional overrides
ARUS_DB_PASSWORD=arus_secret
ARUS_LOG_LEVEL=INFO
ARUS_DEFAULT_SCHEDULE=*/5 * * * *
ARUS_BATCH_SIZE=10000
ARUS_RETRY_MAX=3
ARUS_AUTO_ALTER_SCHEMA=false
ARUS_QUALITY_CHECK_THRESHOLD=5.0
```

### 3. Start Services

```bash
docker compose up -d
```

This starts three containers:

| Container | Port | Purpose |
|---|---|---|
| `arus-db` | 5432 | PostgreSQL 15 (warehouse + config + state) |
| `arus-api` | 8081 | FastAPI backend |
| `arus-console` | 8082 | nginx + SPA frontend |

### 4. Verify Installation

```bash
# Check all containers are running
docker compose ps

# Check API health
curl http://localhost:8081/api/health

# Expected response:
# {"status":"ok","data":{"version":"0.1.0","database":"connected","scheduler":"running"}}
```

### 5. Access the Console

Open **http://localhost:8082** in your browser.

**Default credentials:**
- **Email:** `admin@arus.io`
- **Password:** `admin123`

---

## First Pipeline in 5 Minutes

### Step 1: Add a Source Database

1. Log in to the Arus Console
2. Navigate to **Sources** in the sidebar
3. Click **+ Add Source**
4. Fill in connection details:
   - **Name**: `My Production DB`
   - **Type**: `MySQL` (or PostgreSQL/MariaDB)
   - **Host**: your database host
   - **Port**: 3306 (MySQL default)
   - **Database**: database name
   - **Username** / **Password**: database credentials
   - **Sync Method**: `Auto-detect`
5. Click **Test Connection** ✅
6. Click **Save**

### Step 2: Auto-Discover Tables

1. Click **Rescan** on your new source
2. Arus scans all tables and auto-detects sync modes:
   - Tables with `updated_at`/`created_at` → **Incremental**
   - Tables without timestamps → **Full Refresh**
   - Tables with `deleted_at` → Soft-delete tracking enabled
3. Toggle table checkboxes to select which tables to sync
4. For each table, choose **Load Mode**:
   - **Direct** (default): Source → Analytics (typed columns)
   - **Raw → Normalize**: Source → Staging (JSONB) → Analytics

### Step 3: Save and Create Pipeline

1. Click **Save Table Selection**
2. Arus auto-creates a pipeline:
   - One pipeline per source
   - Schedule: every 5 minutes (`*/5 * * * *`)
   - Destination: default warehouse (auto-configured)
3. Navigate to **Pipelines** to see your new pipeline

### Step 4: Run the Pipeline

1. Click on your pipeline to open Pipeline Detail
2. Click **Sync Now** to trigger an immediate run
3. Watch the Run History table populate with results
4. Click **Logs** on any run to see detailed execution logs

### Step 5: View Data in Warehouse

```bash
# Connect to the warehouse PostgreSQL
docker exec -it arus-db psql -U arus -d arus_warehouse

# List synced tables
\dt analytics.*
\dt staging.*

# Query normalized data
SELECT * FROM analytics.<your_table> LIMIT 10;

# Check watermark state
SELECT * FROM arus_state.watermarks;
```

---

## Setting Up Notifications

### Telegram

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather)
2. Set environment variables:
   ```bash
   ARUS_TELEGRAM_BOT_TOKEN=your_bot_token
   ARUS_TELEGRAM_CHAT_ID=your_chat_id
   ```
3. Restart the API container:
   ```bash
   docker compose restart arus-api
   ```
4. In the Console, go to **Notifications** → **Add Target**
5. Configure which events to receive alerts for

### Discord / Slack

1. Go to **Notifications** → **Add Target**
2. Select **Discord** or **Slack**
3. Enter your webhook URL
4. Save and test the connection

---

## Creating Your First Transform

1. Open your pipeline detail page
2. Click on the **Transform** button next to a table
3. Add a transform step:
   - **Rename Fields**: `first_name` → `fname`, `last_name` → `lname`
   - **Compute Field**: `full_name = first_name + ' ' + last_name`
   - **Filter Rows**: `status != 'deleted'`
   - **Type Cast**: `price` → `float`, `is_active` → `bool`
4. Or write a **Python Script**:
   ```python
   def transform(row):
       row["email_domain"] = row["email"].split("@")[1] if row.get("email") else None
       row["full_name"] = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
       return row
   ```

---

## Common Operations

### Trigger a Backfill

```bash
curl -X POST http://localhost:8081/api/pipelines/{id}/backfill \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"from_date": "2024-01-01"}'
```

### Trigger a Full Refresh

```bash
curl -X POST http://localhost:8081/api/pipelines/{id}/full-refresh \
  -H "Authorization: Bearer <token>"
```

### Check Pipeline Status via API

```bash
curl http://localhost:8081/api/pipelines \
  -H "Authorization: Bearer <token>"
```

---

## Troubleshooting

| Symptom | Solution |
|---|---|
| Console shows "Loading Arus..." forever | Check `arus-api` is healthy: `docker compose logs arus-api` |
| Pipeline status "Failed" with connection error | Verify source DB credentials and network connectivity |
| Tables not appearing after Rescan | Check table filter patterns in source configuration |
| Watermark not advancing | Ensure `updated_at` column exists and is being populated |
| Dead letter rows accumulating | Check error details in Run Logs or Dead Letter viewer |
| Console API errors (401) | Token expired — log out and log back in |
