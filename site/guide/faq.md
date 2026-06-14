# FAQ

Frequently asked questions about Arus.

---

## General

### What is Arus?

Arus is a lightweight, self-hosted **CDC & ETL framework** for teams running on VPS-class infrastructure (no Kubernetes needed). It ingests data from MySQL, MariaDB, PostgreSQL, and MongoDB, applies transformations, and lands them into a PostgreSQL, MySQL, or ClickHouse data warehouse.

### How is Arus different from Airbyte?

| | Airbyte | Arus |
|---|---|---|
| **Infrastructure** | Requires Kubernetes or Docker Compose with async worker | Single `docker compose up -d` |
| **Resources** | Minimum 4GB+ with separate worker | 2-core / 4GB RAM total |
| **CDC method** | Debezium/Kafka-based (log-based) | Watermark-based (batch SELECT) |
| **Complexity** | 10+ microservices | 3 containers (DB, API, Console) |
| **Setup time** | 30-60 minutes | 2-3 minutes |

### How is Arus different from Debezium?

Debezium requires Kafka as the transport layer — you need Zookeeper + Kafka + Kafka Connect + Debezium connectors. That's **4+ infrastructure components** before you sync a single row. Arus does everything in-process with just PostgreSQL + FastAPI. No Kafka, no Zookeeper, no Connect cluster.

### Do I need Kubernetes?

**No.** Arus is designed specifically for VPS-class infrastructure. It runs on a single Docker host with 2 CPU cores and 4GB RAM.

### Is Arus production-ready?

Phases 1 and 2 are complete — core ETL pipeline, connectors, auth, DAG UI, retry/backoff, dead letter queue, quality checks, schema drift detection, and notifications. Phase 3 (CLI tools, backfill UI, multi-env) is in progress.

### What license does Arus use?

Arus is currently a **private project**. Check the repository for licensing details.

---

## Technical

### What CDC methods does Arus support?

Arus uses **watermark-based batch CDC** — it polls source tables for new/updated rows using a timestamp column (e.g., `updated_at`). This approach:

- ✅ Works with read-replicas (no write access needed)
- ✅ Minimal database overhead (standard SELECT queries)
- ✅ No binlog/Write-Ahead Log (WAL) configuration needed
- ✅ Works across all supported databases

### Does Arus support real-time (streaming) CDC?

No. Arus is a **batch CDC** tool with configurable polling intervals (default: every 5 minutes). If you need sub-second real-time sync, consider Debezium + Kafka.

### Can Arus handle large tables?

Yes. Arus uses batched extraction (default: 10,000 rows per batch) with watermark tracking. Large tables are synced incrementally — only new/changed rows are transferred after the initial backfill.

### What happens if a pipeline run fails?

Arus automatically retries failed operations with exponential backoff (default: 3 attempts, 2s → 4s → 8s → 16s). After all retries are exhausted:

- The run is marked as **failed**
- Failed rows are saved to the **Dead Letter Queue** (DLQ)
- A notification is sent if configured (Telegram, Discord, or Slack)
- The next scheduled run picks up from the last successful watermark

### Does Arus handle schema changes in source tables?

Yes — **schema drift detection** is built in. During each pipeline run, Arus compares source columns against warehouse columns:

1. New columns are detected and logged
2. If `auto_alter_schema` is enabled, new columns are added to the warehouse table automatically
3. Notifications can be sent for schema drift events

### Can I run multiple pipelines concurrently?

Yes. The default configuration supports **5 concurrent pipelines** on 2-core / 4GB RAM. Each pipeline runs in its own thread with a 5-minute timeout.

### What databases can be destinations?

Currently supported destinations:
- **PostgreSQL** — full support (JSONB raw storage, UPSERT, typed analytics)
- **MySQL** — full support (JSON raw storage, batch insert)
- **ClickHouse** — with MergeTree engine and auto-TTL

---

## Setup & Configuration

### What are the minimum system requirements?

- **Minimum**: 2 CPU cores, 4GB RAM, 20GB disk
- **Recommended**: 4 CPU cores, 8GB RAM, 50GB SSD
- **Software**: Docker 24+ & Docker Compose v2+

### Do I need to expose Arus to the internet?

Not necessarily. Arus works perfectly on a local network or behind a VPN. For cloud deployments, we recommend using a **reverse proxy with HTTPS** (nginx, Caddy, or Cloudflare Tunnel).

### Can I use a source database that's behind a firewall?

Yes. As long as the Arus server can reach the source database host and port, it works. For additional security:

- Use **SSH tunnels** or **WireGuard** for connectivity
- Create a **read-only** database user for source connectors
- Restrict source access to the Arus server's IP address

### How do I secure Arus in production?

See the [Security Guide](/guide/security) for a comprehensive checklist. Key points:

1. Change default credentials immediately
2. Set strong `ARUS_JWT_SECRET` and `ARUS_ENCRYPTION_KEY`
3. Use HTTPS via reverse proxy
4. Bind Docker ports to localhost only
5. Use read-only accounts for source databases
6. Configure automated backups

### How do I update Arus?

```bash
# Pull new images
docker compose pull

# Restart with new images
docker compose up -d

# Verify health
curl http://localhost:8081/api/health
```

Database migrations run automatically on startup.

---

## Monitoring & Troubleshooting

### How do I check if Arus is running?

```bash
docker compose ps
curl http://localhost:8081/api/health
```

Expected response:
```json
{"status":"ok","data":{"version":"0.1.0","database":"connected","scheduler":"running"}}
```

### How do I view pipeline logs?

- **Via Console**: Pipeline Detail → Run History → Logs
- **Via API**: `GET /api/runs/{id}/logs`
- **Via Docker**: `docker compose logs arus-api`

### What should I do if a pipeline keeps failing?

1. Check **Run Logs** in the Console for error details
2. Verify source database credentials and connectivity
3. Check the **Dead Letter Queue** for failed rows
4. Ensure the source table has a proper `updated_at` index
5. Review source database load and connection limits

### How do I reset a stuck pipeline?

```bash
# Cancel the stuck run via API
curl -X POST http://localhost:8081/api/runs/{run_id}/cancel \
  -H "Authorization: Bearer ***"
```

If the scheduler itself is stuck:
```bash
docker compose restart arus-api
```

---

## Migration

### Can I migrate from Airbyte to Arus?

Yes. Since both tools use a common pattern (source connector → pipeline → destination), migration steps are:

1. Set up Arus with Docker Compose
2. Configure the same source databases in Arus
3. Configure the same destination
4. For each Airbyte connection, create a matching pipeline in Arus
5. Run a **Full Refresh** to backfill historical data
6. Disable Airbyte connections once Arus pipelines are running

### Can I migrate from custom ETL scripts to Arus?

Yes. Custom Python/Shell scripts can be replaced by:

1. Configure the source as an Arus Source connector
2. Set transforms in the pipeline for any data processing logic
3. Configure the existing database as an Arus Destination

### Will my existing warehouse tables be affected?

Arus creates tables in dedicated schemas (`analytics.*`, `staging.*`), so existing tables are not affected. You can run Arus alongside your current setup during migration.

---

## Limits & Scalability

### What's the maximum throughput?

Throughput depends on hardware and source/destination performance. Typical benchmarks:

- **2-core / 4GB RAM**: ~50K-100K rows/minute (single pipeline)
- **4-core / 8GB RAM**: ~200K-500K rows/minute (5 concurrent pipelines)
- **8-core / 16GB RAM**: ~1M+ rows/minute

### Is there a limit on the number of tables?

No hard limit. Each table is tracked by a watermark row in the database. Resource usage scales with the number of active tables and sync frequency.

### Can I use Arus with a data warehouse like Snowflake or BigQuery?

Not yet. Currently supported destinations are PostgreSQL, MySQL, and ClickHouse. Support for cloud warehouses is being evaluated for Phase 3.

### Does Arus support multi-tenancy?

Not directly. Each Arus instance manages its own set of connectors and pipelines. For multi-tenant setups, you can run separate instances or use schema-level isolation in the warehouse database.
