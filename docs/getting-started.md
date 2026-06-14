# Quick Start

Get Arus running on your server in under 5 minutes.

## Prerequisites

- Docker Engine 24.x+
- Docker Compose v2.20+
- Minimum 2 CPU cores, 2GB RAM, 20GB free disk
- Linux (Ubuntu 22.04+ recommended)

## 1. Clone the repository

```bash
# HTTPS
git clone https://github.com/edsuwarna/arus.git
cd arus

# or SSH
git clone git@github.com:edsuwarna/arus.git
cd arus
```

## 2. Configure environment

Copy the example environment file and customize as needed:

```bash
cp .env.example .env
```

At minimum, you should change the default JWT secret for production:

```bash
# .env
ARUS_JWT_SECRET=your-strong-secret-here
ARUS_ENCRYPTION_KEY=your-encryption-key-here
```

## 3. Start the stack

```bash
docker compose up -d
```

This starts three containers:

- `arus-console` — Frontend SPA at **http://localhost:8082**
- `arus-api` — Backend API at **http://localhost:8081**
- `arus-db` — PostgreSQL database (internal only)

## 4. Verify installation

```bash
docker compose ps
curl http://localhost:8081/api/health
```

Expected response:

```json
{"status":"ok","data":{"version":"0.1.0","database":"connected","scheduler":"running"}}
```

## 5. Login

Open **http://localhost:8082** in your browser and log in with the default admin credentials:

- **Email:** admin@arus.io
- **Password:** admin123

> **⚠️ Change the default password immediately after first login.** Edit your profile in Settings > Users.

## 6. Create your first pipeline

1. Navigate to **Sources** → click **Add Source**
2. Enter your database connection details and click **Test Connection**
3. Click **Auto-discover** — Arus scans all tables and detects sync modes
4. Toggle the tables you want to sync and **Save**
5. Go to **Pipelines** — your pipeline is already created and running

## Next steps

- [Configuration Guide](/docs/setup.md) — all environment variables and settings
- [System Architecture](/docs/architecture.md) — understanding the design
- [API Reference](/docs/api.md) — programmatic access
