# Arus — CDC & ETL Platform

> **Arus** (Indonesian: *flow*) — Lightweight, self-hosted **CDC & ETL** platform. Data flows without the cluster.

[![License](https://img.shields.io/badge/License-Apache%202.0-eab308.svg)](LICENSE)

## Quick Start

```bash
# Docker Compose
git clone https://github.com/edsuwarna/arus.git
cd arus
docker compose up -d
```

## Features

- **CDC & ETL** — Built-in change data capture with watermark-based incremental sync
- **Auto-discover Tables** — Automatically detects source tables, maps columns and types
- **Scheduling** — APScheduler cron-based scheduling with auto-retry
- **Schema Drift Detection** — Automatic detection of column changes with auto-ALTER
- **Alerting** — Notifications to Telegram, Discord, or Slack
- **Run History & Logs** — Full audit trail with structured logs
- **Dead Letter Queue** — Failed rows captured without blocking execution

## Documentation

📚 [Full Documentation →](https://arus-data.pages.dev)

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Go, Chi router, pgx |
| Database | PostgreSQL 17 |
| Frontend (Console) | HTML/SVG dashboard |
| Deployment | Docker Compose, Docker images at `ghcr.io/edsuwarna` |

## License

Apache License 2.0 — see [LICENSE](LICENSE).
