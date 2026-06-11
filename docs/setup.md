# Arus Setup Guide

> **Version:** 1.0
> **Status:** 🔴 Draft
> **Last Updated:** June 2026

---

## 1. Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Docker | 24.x | Latest |
| Docker Compose | v2.20+ | Latest |
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Disk | 20 GB free | 50 GB+ |
| OS | Linux (any) | Ubuntu 22.04+ |

**Network:** Outbound access to source databases (MySQL/MariaDB/PostgreSQL).

---

## 2. Quick Start

### 2.1 Clone & Configure

```bash
git clone https://github.com/edsuwarna/arus.git
cd arus
cp .env.example .env
# Edit .env with your settings
```

### 2.2 Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ARUS_DB_HOST` | `arus-db` | ✅ | PostgreSQL hostname (Docker service name) |
| `ARUS_DB_PORT` | `5432` | ✅ | PostgreSQL port |
| `ARUS_DB_USER` | `arus` | ✅ | PostgreSQL user |
| `ARUS_DB_PASSWORD` | `arus_secret` | ✅ | PostgreSQL password |
| `ARUS_DB_NAME` | `arus_warehouse` | ✅ | PostgreSQL database name |
| `ARUS_JWT_SECRET` | *(auto-generated)* | ❌ | JWT signing key. Auto-generated on first run if empty |
| `ARUS_ENCRYPTION_KEY` | *(auto-generated)* | ❌ | Fernet key for source password encryption. Auto-generated |
| `ARUS_CONSOLE_URL` | `http://localhost:8080` | ❌ | Console URL for CORS |
| `ARUS_LOG_LEVEL` | `INFO` | ❌ | Python log level (`DEBUG`, `INFO`, `WARN`, `ERROR`) |
| `ARUS_DEFAULT_SCHEDULE` | `*/5 * * * *` | ❌ | Default pipeline schedule (cron) |
| `ARUS_BATCH_SIZE` | `10000` | ❌ | Default rows per batch |
| `ARUS_RETRY_MAX` | `3` | ❌ | Max retry attempts |
| `TZ` | `UTC` | ❌ | Timezone |

### 2.3 Start Arus

```bash
docker compose up -d
```

This starts 3 containers:
- **arus-console** — Frontend SPA at `http://localhost:8080`
- **arus-api** — Backend API at `http://localhost:8081`
- **arus-db** — PostgreSQL

### 2.4 First Run Setup

On first startup, the backend automatically:

1. ✅ Creates PostgreSQL schemas (`arus_config`, `arus_state`, `staging`, `analytics`, `arus_run_logs`)
2. ✅ Creates required tables (users, sources, pipelines, etc.)
3. ✅ Seeds default settings
4. ✅ Creates the default admin user

**Default admin credentials:**
- **Email:** `admin@arus.io`
- **Password:** `admin123`

> ⚠️ **Change the default password immediately after first login!**

### 2.5 Verify Installation

```bash
# Check containers are running
docker compose ps

# Check API health
curl http://localhost:8081/api/health

# Expected response:
# {"status":"ok","data":{"version":"0.1.0","database":"connected","scheduler":"running"}}
```

---

## 3. docker-compose.yml Reference

```yaml
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
    build:
      context: .
      dockerfile: Dockerfile
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
    image: nginx:alpine
    container_name: arus-console
    volumes:
      - ./console:/usr/share/nginx/html:ro
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "8080:80"
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

---

## 4. Nginx Configuration

The Console uses Nginx to serve static files and proxy API requests to the backend.

```
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback — all routes served by index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://arus-api:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

> For production, add SSL termination via Cloudflare Tunnel or Let's Encrypt.

---

## 5. First Pipeline Walkthrough

### Step 1: Login
Open `http://localhost:8080` → Login with `admin@arus.io` / `admin123`

### Step 2: Add Source
1. Navigate to **Sources** → **Add Source**
2. Fill in:
   - **Name:** `Production MySQL`
   - **Type:** `MySQL`
   - **Host:** `10.0.0.50`
   - **Port:** `3306`
   - **Database:** `ecommerce`
   - **Username:** `reader`
   - **Password:** `readonly_pass`
   - **Sync Method:** `Auto-detect`
3. Click **Test Connection** → should return ✅
4. Click **Save & Discover**

### Step 3: Select Tables
1. Arus scans the source DB and shows all tables
2. Toggle checkboxes for tables you want to sync
3. Arus auto-detects sync mode per table:
   - ✅ Incremental (if `updated_at` column exists)
   - 🔄 Full refresh (no timestamp column)
4. Click **Save**

### Step 4: Pipeline Auto-Created
Arus automatically creates a pipeline named `Production MySQL → Warehouse` with:
- Schedule: Every 5 minutes (configurable)
- All enabled tables

### Step 5: Monitor
- **Dashboard** — see pipeline health, recent runs, sync performance chart
- **Pipelines** — pause/resume/trigger manually
- **DAG View** — see asset graph with real-time status
- **Run History** — per-run logs, row counts, errors

---

## 6. Production Deployment

### 6.1 Reverse Proxy with Cloudflare Tunnel

```bash
# On the VPS
cloudflared tunnel create arus
cloudflared tunnel route dns arus arus.yourdomain.com

# cloudflared config.yml
tunnel: <tunnel-id>
credentials-file: /home/ubuntu/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: arus.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404
```

### 6.2 Resource Tuning

| Scenario | Setting | Value |
|----------|---------|-------|
| Many source tables (50+) | `ARUS_BATCH_SIZE` | `5000` |
| Low-memory VPS (2GB) | PostgreSQL `shared_buffers` | `256MB` |
| High latency to source DB | `ARUS_RETRY_MAX` | `5` |
| Near-real-time needs | `ARUS_DEFAULT_SCHEDULE` | `*/1 * * * *` |

### 6.3 Backup

```bash
# Backup entire Arus database
docker exec arus-db pg_dump -U arus arus_warehouse > arus_backup_$(date +%Y%m%d).sql

# Restore
cat arus_backup.sql | docker exec -i arus-db psql -U arus arus_warehouse
```

---

## 7. Development Setup

### 7.1 Run Without Docker

```bash
# Python 3.11+ required
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start PostgreSQL (local or Docker)
docker run -d --name arus-db-dev \
  -e POSTGRES_USER=arus \
  -e POSTGRES_PASSWORD=arus_secret \
  -e POSTGRES_DB=arus_warehouse \
  -p 5432:5432 \
  postgres:15-alpine

# Run backend
ARUS_DB_HOST=localhost \
ARUS_DB_PASSWORD=arus_secret \
python -m arus.main

# Serve console separately
cd console && python -m http.server 8080
```

### 7.2 Running Tests

```bash
pytest tests/ -v
pytest tests/ --cov=arus  # with coverage
```

---

## 8. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY arus/ ./arus/

# Expose port
EXPOSE 8081

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8081/api/health || exit 1

# Run
CMD ["uvicorn", "arus.main:app", "--host", "0.0.0.0", "--port", "8081"]
```

---

## 9. Troubleshooting

### Container won't start

| Symptom | Cause | Fix |
|---------|-------|-----|
| `arus-db` keeps restarting | PostgreSQL data dir permission | `chown -R 999:999 ./data/postgres` |
| `arus-api` fails to connect to DB | DB not ready yet | Wait for `service_healthy` condition |
| `Connection refused` on source test | Source DB not reachable | Check network/firewall between containers and source |
| `JWT secret not set` | Missing env var | Set `ARUS_JWT_SECRET` or let auto-generate (restart) |

### Pipeline failing

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `Can't connect to source` | Source DB down or firewall | Check source connection from API container |
| `Column 'updated_at' not found` | Auto-detect wrong watermark column | Override sync mode to full refresh |
| `Duplicate key violation` | Upsert conflict | Check if source table has a PK |
| `Type cast error` | Column type mismatch | Check type mapping in `docs/architecture.md` |

### Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f arus-api

# View last N lines
docker compose logs --tail=50 arus-api
```

---

## 10. Upgrade

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose build --no-cache arus-api
docker compose up -d

# Run database migrations (if any)
docker exec arus-api alembic upgrade head
```

---

*End of Setup Guide — Arus v1.0*
