# Monitoring & Observability

Guide for monitoring Arus in production, understanding pipeline health, and setting up observability.

---

## Health Check

Arus exposes a simple health endpoint for load balancers and uptime monitors:

```bash
curl http://localhost:8081/api/health
```

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

**Health dimensions:**
- `database` — PostgreSQL connectivity
- `scheduler` — APScheduler background process status

---

## Container Health

Each container has Docker-level health checks:

```bash
# Check all container status
docker compose ps

# View health check logs
docker inspect --format '{{json .State.Health}}' arus-api
# docker inspect --format '{{json .State.Health}}' arus-db
```

The health endpoint is:
- **arus-api**: `curl -f http://localhost:8081/api/health` (every 30s)
- **arus-db**: `pg_isready -U arus` (every 5s)

---

## Resource Monitoring

### Container Resource Usage

```bash
# Real-time resource usage
docker stats

# Disk usage
df -h /var/lib/docker

# Memory usage per container
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}"
```

### Recommended Alerts

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Memory usage | > 70% | > 85% | Reduce batch size or add RAM |
| CPU usage | > 70% (sustained) | > 90% | Reduce concurrent pipelines |
| Disk usage | > 70% | > 85% | Prune old Docker images, logs |
| API response time | > 500ms | > 2s | Check DB load or scale |
| Failed pipelines | 1 failure | 3+ consecutive | Check source DB / network |

---

## Pipeline-Level Monitoring

### Dashboard

The Arus Console **Dashboard** provides a high-level overview:

- **Active Sources** — total configured source connections
- **Pipelines Active** — currently running or scheduled
- **Rows Synced (24h)** — total throughput
- **Failed Runs (24h)** — failure count

### Pipeline Run Logs

Each pipeline run produces detailed logs:

```bash
# Via API — get recent runs for a pipeline
curl http://localhost:8081/api/pipelines/{id}/runs \
  -H "Authorization: Bearer ***"

# View detailed logs for a specific run
curl http://localhost:8081/api/runs/{run-id}/logs \
  -H "Authorization: Bearer ***"
```

### API Monitoring Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `GET /api/dashboard/summary` | Aggregate stats (sources, pipelines, rows, failures) | Dashboard monitoring |
| `GET /api/dashboard/recent-runs` | Latest 5 runs across all pipelines | Quick health check |
| `GET /api/runs` | Global run history with filters | Troubleshooting |
| `GET /api/runs/stats/daily?days=7` | Daily row count for charting | Trend monitoring |

---

## Notification Alerts

Configure alerts for pipeline events to receive proactive notifications.

### Available Alert Events

| Event | Trigger | Recommended Action |
|-------|---------|-------------------|
| `failure` | Pipeline run failed after retries | Investigate source DB / credentials |
| `success` | Pipeline run completed successfully | Optional — track completion |
| `dead_letter` | Rows moved to Dead Letter Queue | Review failed rows in Console |
| `schema_drift` | New columns detected in source table | Review and update warehouse schema |
| `quality_breach` | Data quality threshold exceeded | Check row count discrepancies |

### Setting Up Notifications

1. Go to **Notifications** → **+ Add Target**
2. Configure Telegram, Discord, or Slack
3. Link targets to specific pipelines with selected event types

See [Quickstart → Setting Up Notifications](/guide/quickstart#setting-up-notifications) for detailed setup.

---

## Log Management

### Docker Logs

```bash
# Follow all Arus logs
docker compose logs -f

# Follow specific service
docker compose logs -f arus-api

# Filter by expression
docker compose logs arus-api | grep "ERROR\|WARNING"

# Recent N lines
docker compose logs --tail=100 arus-api
```

### Log Levels

Set `ARUS_LOG_LEVEL` in `.env`:

| Level | When to Use |
|-------|-------------|
| `ERROR` | Production — only errors and critical issues |
| `WARNING` | Production — errors + warnings (default) |
| `INFO` | General — startup messages, run summaries |
| `DEBUG` | Development — detailed per-operation logging |

### Log Aggregation

For production deployments, configure Docker's json-file logging driver with rotation:

```yaml
# docker-compose.yml
x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

services:
  arus-api:
    logging: *default-logging
  arus-console:
    logging: *default-logging
  arus-db:
    logging: *default-logging
```

For centralized log management, forward logs to your platform of choice:

- **Loki / Grafana**: Use `docker compose plugin` for log shipping
- **Datadog**: Install Datadog agent and configure log collection
- **Papertrail / Logtail**: Use Docker log driver plugins

---

## Database Monitoring

### Warehouse Size

```bash
docker exec arus-db psql -U arus -d arus_warehouse -c "
SELECT schemaname, pg_size_pretty(sum(pg_total_relation_size(schemaname||'.'||tablename))::bigint) as size
FROM pg_tables
WHERE schemaname IN ('arus_config', 'arus_state', 'arus_run_logs', 'staging', 'analytics')
GROUP BY schemaname
ORDER BY schemaname;
"
```

### Dead Letter Queue

Monitor DLQ size — growing DLQ indicates persistent load failures:

```bash
# Count dead letter rows
docker exec arus-db psql -U arus -d arus_warehouse -c "
SELECT source_name, table_name, count(*), max(failed_at) as last_failure
FROM staging._dead_letters
GROUP BY source_name, table_name
ORDER BY count(*) DESC;
"
```

### Run Log Retention

Run logs accumulate over time. Monitor the `arus_run_logs` schema size:

```bash
docker exec arus-db psql -U arus -d arus_warehouse -c "
SELECT pg_size_pretty(pg_total_relation_size('arus_run_logs.runs')) as runs_size,
       pg_size_pretty(pg_total_relation_size('arus_run_logs.run_logs')) as logs_size;
"
```

---

## Uptime Monitoring

Configure external uptime monitoring for the API health endpoint:

### Using Uptime Kuma

```yaml
# docker-compose.uptime.yml
services:
  uptime-kuma:
    image: louislam/uptime-kuma:latest
    container_name: arus-uptime
    ports:
      - "3001:3001"
    volumes:
      - uptime-kuma-data:/app/data
    restart: unless-stopped

volumes:
  uptime-kuma-data:
```

Monitor: `https://arus.example.com/api/health`

### Using curl-based Monitoring

```bash
# Simple cron-based health check
#!/bin/bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/api/health)
if [ "$RESPONSE" != "200" ]; then
  echo "Arus API unhealthy — HTTP $RESPONSE" | mail -s "Arus Alert" admin@example.com
fi
```

---

## Key Metrics Summary

| Metric | Source | What It Tells You |
|--------|--------|-------------------|
| API health | `GET /api/health` | System is alive |
| Dashboard summary | `GET /api/dashboard/summary` | Pipeline health at a glance |
| Run success rate | `GET /api/runs?status=failed` | Failure trend |
| Recent runs | `GET /api/dashboard/recent-runs` | Latest activity |
| Daily rows synced | `GET /api/runs/stats/daily` | Throughput trend |
| Dead letter count | DLQ query | Data quality issues |
| Container resources | `docker stats` | Resource pressure |
| DB size | `pg_total_relation_size` | Storage growth |
