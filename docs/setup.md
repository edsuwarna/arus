# Configuration

All environment variables, docker-compose options, and runtime settings for Arus.

## Environment Variables

Create a `.env` file in the project root. Copy from `.env.example`:

```bash
cp .env.example .env
```

### Database

| Variable | Default | Description |
|---|---|---|
| `ARUS_DB_HOST` | arus-db | PostgreSQL hostname (Docker service name) |
| `ARUS_DB_PORT` | 5432 | PostgreSQL port |
| `ARUS_DB_USER` | arus | PostgreSQL user |
| `ARUS_DB_PASSWORD` | arus_secret | PostgreSQL password |
| `ARUS_DB_NAME` | arus_warehouse | PostgreSQL database name |

### Security

| Variable | Default | Description |
|---|---|---|
| `ARUS_JWT_SECRET` | auto-generated | JWT signing key. Auto-generated on first run if empty. |
| `ARUS_ENCRYPTION_KEY` | auto-generated | Fernet key for source password encryption. Auto-generated. |

### Runtime

| Variable | Default | Description |
|---|---|---|
| `ARUS_LOG_LEVEL` | INFO | Python log level (DEBUG, INFO, WARN, ERROR) |
| `ARUS_DEFAULT_SCHEDULE` | `*/5 * * * *` | Default pipeline schedule (cron) |
| `ARUS_BATCH_SIZE` | 10000 | Rows per batch for extraction |
| `ARUS_RETRY_MAX` | 3 | Maximum retry attempts per run |
| `ARUS_AUTO_ALTER_SCHEMA` | false | Auto-ALTER target table on schema drift (recommended: true) |
| `ARUS_QUALITY_CHECK_THRESHOLD` | 5.0 | Max % row count deviation before alert |
| `ARUS_TELEGRAM_BOT_TOKEN` | - | Telegram bot token for notification alerts |
| `ARUS_TELEGRAM_CHAT_ID` | - | Telegram chat ID for notification alerts |
| `TZ` | UTC | Timezone |

## docker-compose.yml

The stack consists of 3 services defined in `docker-compose.yml`:

```yaml
# Services
services:
  arus-db:
    image: postgres:15-alpine
    volumes: [ pgdata:/var/lib/postgresql/data ]
    environment:
      POSTGRES_USER: ${ARUS_DB_USER:-arus}
      POSTGRES_PASSWORD: ${ARUS_DB_PASSWORD:-arus_secret}
      POSTGRES_DB: ${ARUS_DB_NAME:-arus_warehouse}

  arus-api:
    build: .
    ports: [ "8081:8081" ]
    depends_on: [ arus-db ]
    env_file: .env

  arus-console:
    build:
      context: .
      dockerfile: Dockerfile.console
    ports: [ "8082:80" ]
    depends_on: [ arus-api ]
```

## First Run Setup

On first startup, the backend automatically:

- Creates PostgreSQL schemas (arus_config, arus_state, raw, target)
- Creates required tables (users, sources, pipelines, etc.)
- Seeds default settings
- Creates the default admin user (admin@arus.io / admin123)

## Database Migrations

Arus uses Alembic for schema migrations. Manual workflow:

```bash
# Write migration file on host at alembic/versions/
# Copy into running container and execute:
docker cp alembic/versions/NNN_name.py arus-api:/app/alembic/versions/
docker exec arus-api alembic upgrade head
```

---

📖 For the full setup guide, see [Quick Start](/docs/getting-started.md).
