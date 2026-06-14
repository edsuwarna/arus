# Development Guide

Guide for setting up a local development environment and contributing to Arus.

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 15+**
- **Docker & Docker Compose** (for running dependencies)
- **Git**

---

## Local Setup

### 1. Clone and Install Dependencies

```bash
# This repository is private — clone with appropriate access
git clone https://github.com/edsuwarna/arus.git
cd arus

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-asyncio httpx
```

### 2. Start PostgreSQL

```bash
# Using Docker for the database
docker run -d \
  --name arus-db-dev \
  -e POSTGRES_USER=arus \
  -e POSTGRES_PASSWORD=arus_secret \
  -e POSTGRES_DB=arus_warehouse \
  -p 5432:5432 \
  postgres:15-alpine
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env as needed (defaults work for local dev)
```

### 4. Run Migrations

```bash
# Run Alembic migrations
python -c "from arus.shared.db.migrate import run_migrations; run_migrations()"
```

### 5. Start the API Server

```bash
uvicorn arus.main:app --reload --host 0.0.0.0 --port 8081
```

### 6. Start the Frontend Console

```bash
# Option 1: Using nginx
docker compose up arus-console -d

# Option 2: Using Python HTTP server (for development)
cd console
python -m http.server 8082
```

The console at `http://localhost:8082` will proxy API requests to `http://localhost:8081` via nginx.

---

## Project Structure

```
arus/
├── arus/                          # Backend Python package
│   ├── main.py                    # FastAPI application entry point
│   ├── models.py                  # Central model imports for Alembic
│   ├── modules/                   # Feature modules
│   │   ├── auth/                  # Authentication & user management
│   │   ├── connector/             # Source/destination connector framework
│   │   ├── pipeline/              # Pipeline orchestration engine
│   │   ├── source/                # Source CRUD API
│   │   ├── destination/           # Destination CRUD API
│   │   ├── run_log/               # Run history & logging
│   │   ├── dag/                   # DAG visualization data
│   │   ├── dashboard/             # Dashboard summary endpoints
│   │   ├── transform/             # Transform engine
│   │   ├── notification/          # Notification targets
│   │   ├── settings/              # Runtime settings
│   │   └── alert/                 # Telegram alert manager
│   ├── shared/                    # Shared utilities
│   │   ├── config.py              # Environment-based configuration
│   │   ├── crypto.py              # Fernet encryption
│   │   ├── types.py               # Column type mapping
│   │   ├── db/                    # Database session, engine, migrations
│   │   └── exceptions.py          # Error hierarchy
│   └── utils/                     # Legacy utilities
│       ├── schema_manager.py
│       └── state_manager.py
├── console/                       # Frontend SPA
│   ├── index.html                 # Entry point
│   ├── css/                       # Stylesheets
│   └── js/                        # JavaScript modules
│       ├── app.js                 # SPA router, App singleton
│       ├── api.js                 # API client with auth
│       ├── components/            # Reusable components
│       └── pages/                 # Page-specific scripts
├── docs/                          # Documentation
├── prd/                           # Product requirements
├── tests/                         # Test suite
├── alembic/                       # Database migrations
├── scripts/                       # Utility scripts
├── nginx/                         # nginx configuration
├── docker-compose.yml             # Docker Compose setup
├── Dockerfile                     # API container build
├── Dockerfile.console             # Console container build
├── requirements.txt               # Python dependencies
└── .env.example                   # Environment template
```

---

## Module Development Pattern

Each module follows a consistent layered architecture:

```
module/
├── models.py        # SQLAlchemy ORM models (data layer)
├── schemas.py       # Pydantic models (validation layer)
├── repository.py    # Database operations (data access)
├── service.py       # Business logic (service layer)
├── router.py        # FastAPI routes (presentation layer)
└── __init__.py
```

### Example: Adding a new field to Source

1. **`models.py`**: Add the column to the SQLAlchemy model
   ```python
   new_field = Column(String(100), nullable=True)
   ```

2. **`schemas.py`**: Add the field to Pydantic create/update schemas

3. **`repository.py`**: Update queries if needed (usually no changes for simple fields)

4. **`router.py`**: The field is automatically included in API responses

5. **Migration**: Create an Alembic migration:
   ```bash
   python -c "from arus.shared.db.migrate import create_migration; create_migration('add new_field to sources')"
   ```

---

## Connector Development

### Creating a New Source Connector

1. Create `arus/modules/connector/sources/<name>.py`
2. Implement `BaseSource` interface:
   ```python
   from arus.modules.connector.base_source import BaseSource, TableSchema, SyncMode

   class MySource(BaseSource):
       type = "my_source"

       def connect(self, config: dict) -> bool: ...
       def test_connection(self) -> bool: ...
       def discover_tables(self) -> list[TableSchema]: ...
       def get_table_columns(self, table: str) -> list[dict]: ...
       def detect_sync_mode(self, table: str, columns: list[dict]) -> SyncMode: ...
       def extract(self, table, watermark=None, batch_size=10000): ...
   ```

3. Register in `arus/modules/connector/registry.py`:
   ```python
   from arus.modules.connector.sources.my_source import MySource
   register_source("my_source", MySource)
   ```

4. Add type to `Source` model's type field validation

5. Add a database icon in `console/js/api.js` `getDbIcon()` function

### Creating a New Destination Connector

1. Create `arus/modules/connector/destinations/<name>.py`
2. Implement `BaseDestination` interface
3. Register in registry
4. Add type mapping in the destination module
5. Add database icon

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_connector_soft_delete.py -v

# Run with coverage
pytest tests/ --cov=arus --cov-report=term-missing
```

### Test Structure

```
tests/
├── conftest.py                   # Fixtures and mock setup
├── test_connector_soft_delete.py # Connector soft-delete tests
└── test_executor.py              # Pipeline executor tests
```

Tests use **pytest** with mocked database drivers. The `conftest.py` registers mock modules for `pymysql`, `pymongo`, and `clickhouse_driver` so tests can run without real database connections.

### Writing Tests

```python
import pytest
from unittest.mock import MagicMock, patch


def test_extract_with_watermark():
    """Test that extract filters by watermark correctly."""
    from arus.modules.connector.sources.postgresql import PostgreSQLSource

    source = PostgreSQLSource()
    source.conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
    source.conn.cursor.return_value = mock_cursor

    source._has_deleted_at_column = MagicMock(return_value=False)
    source.get_table_columns = MagicMock(
        return_value=[{"name": "id", "type": "integer"}]
    )

    batches = list(source.extract("my_table", watermark="2024-01-01"))
    assert len(batches) == 1
    assert batches[0][0]["id"] == 1
```

---

## Database Migrations

Arus uses **Alembic** for database migration management.

### Migration Commands

```bash
# Auto-generate a migration from model changes
python -c "from arus.shared.db.migrate import create_migration; create_migration('description of changes')"

# Run pending migrations
python -c "from arus.shared.db.migrate import run_migrations; run_migrations()"

# Stamp current DB as up-to-date (for existing databases)
python -c "from arus.shared.db.migrate import stamp_head; stamp_head()"
```

### Migration Files

Migrations are stored in `alembic/versions/`. They are auto-detected by Alembic via the `arus/models.py` imports which load all ORM models.

---

## Frontend Development

### Architecture

The frontend is a vanilla JS SPA with no build step:

- **Router**: Hash-based (`window.location.hash` + `hashchange` event)
- **State**: `App` singleton object + `_state` key-value store
- **API Layer**: `API` object with auto token refresh
- **Rendering**: Template literals (no virtual DOM)
- **Styling**: Global CSS with dark theme design system

### Adding a New Page

1. Create `console/js/pages/<name>.js`
2. Export a render function:
   ```javascript
   async function renderMyPage(container) {
     container.innerHTML = `<div>...</div>`;
   }
   ```
3. Add the route in `console/js/app.js`:
   ```javascript
   case 'mypage': await renderMyPage(content); break;
   ```
4. Add the script tag in `console/index.html`
5. Add sidebar nav item in `console/js/components/sidebar.js`

### CSS Conventions

- CSS variables for theming: `--bg-primary`, `--text-primary`, `--accent`, etc.
- Dark theme: deep black `#0b0d11` background with emerald `#10b981` accents
- BEM-like class naming
- Mobile-responsive via `mobile.css`

---

## Code Style

### Python

- Follow **PEP 8**
- Type hints required for all function signatures
- Docstrings for public APIs (Google style)
- Use `**kwargs` sparingly; prefer explicit parameters

### JavaScript

- ES6+ syntax
- `const`/`let` instead of `var`
- Template literals for HTML rendering
- Async/await for API calls

### Commit Messages

Follow conventional commits:
```
feat: add MongoDB connector
fix: correct watermark update on empty batch
docs: update API reference
refactor: extract retry logic into decorator
```

---

## Debugging

### API Logs

```bash
# View API logs
docker compose logs -f arus-api

# Set debug level
ARUS_LOG_LEVEL=DEBUG uvicorn arus.main:app --reload
```

### Database

```bash
# Connect to PostgreSQL
docker exec -it arus-db psql -U arus -d arus_warehouse

# View recent runs
SELECT * FROM arus_run_logs.runs ORDER BY started_at DESC LIMIT 5;

# Check watermarks
SELECT * FROM arus_state.watermarks;

# View dead letters
SELECT * FROM staging._dead_letters;
```

### Console

- Browser DevTools (F12) for network requests, console logs
- `App.toast()` for in-app notifications
- API responses logged to console when `DEBUG` level is set
