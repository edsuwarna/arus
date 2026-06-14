# Documentation

Everything you need to set up, configure, and operate Arus — a lightweight CDC & ETL platform for VPS-class infrastructure.

## Getting Started

### [Quick Start](/docs/getting-started.md)
Get Arus running in under 5 minutes. Clone, configure, and start your first pipeline.

### [Configuration](/docs/setup.md)
Environment variables, docker-compose options, and runtime settings reference.

## Architecture

### [System Architecture](/docs/architecture.md)
Understand the modular monolith design, data flow, and component interactions.

### [Data Flow](/docs/architecture.md#data-flow)
See how data moves from source → raw → target with watermark-based incremental extraction.

## Reference

### [API Reference](/docs/api.md)
Complete REST API documentation for sources, pipelines, DAG, and monitoring endpoints.

### [GitHub Repository](https://github.com/edsuwarna/arus)
Source code, issues, and contribution guidelines.

---

## Quick overview

Arus is a **lightweight CDC & ETL platform** designed for teams running on VPS-class infrastructure. It ingests data from MySQL, MariaDB, and PostgreSQL sources, applies transformations, and lands them into a PostgreSQL data warehouse — with a visual DAG interface for monitoring and troubleshooting.

- **Zero Kubernetes** — runs on a single Docker host with `docker compose up`
- **No Kafka** — watermark-based incremental extraction, no event streaming infrastructure
- **Built-in DAG UI** — interactive asset graph with real-time pipeline status
- **Auto-discover** — register a source, system detects all tables automatically
- **Schema drift handling** — new columns detected without pipeline breakage
- **Notification alerts** — Telegram, Discord, Slack on failure

---

> **Need help?** Open an issue on [GitHub](https://github.com/edsuwarna/arus/issues).
