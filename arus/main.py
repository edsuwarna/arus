from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from arus.shared.db.session import init_db, SessionLocal
from arus.shared.exceptions import ArusError
from arus.shared.crypto import encrypt_password
from arus.modules.auth.repository import UserRepository
from arus.modules.auth.service import AuthService
from arus.modules.auth.router import router as auth_router
from arus.modules.source.router import router as source_router
from arus.modules.destination.router import router as destination_router
from arus.modules.pipeline.router import router as pipeline_router
from arus.modules.run_log.router import router as run_log_router
from arus.modules.dashboard.router import router as dashboard_router
from arus.modules.settings.router import router as settings_router, seed_default_settings, ensure_settings_table
from arus.modules.dag.router import router as dag_router
from arus.modules.destination.repository import DestinationRepository
from arus.modules.pipeline.scheduler import start_scheduler

app = FastAPI(title="Arus API", version="0.1.0")


@app.on_event("startup")
async def startup():
    init_db()
    ensure_settings_table()
    _seed_admin()
    _seed_default_destination()
    _seed_settings()
    start_scheduler()


def _seed_admin():
    """Create default admin user if not exists."""
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        existing = repo.get_by_email("admin@arus.io")
        if not existing:
            service = AuthService(repo)
            hashed = service.hash_password("admin123")
            repo.create(email="admin@arus.io", name="Arus Admin", password_hash=hashed, role="admin")
    finally:
        db.close()


def _seed_default_destination():
    """Create default PostgreSQL destination if none exists."""
    db = SessionLocal()
    try:
        repo = DestinationRepository(db)
        existing = repo.get_default()
        if not existing:
            repo.create({
                "name": "Warehouse",
                "type": "postgresql",
                "host": "arus-db",
                "port": 5432,
                "database": "arus_warehouse",
                "username": "arus",
                "password_enc": encrypt_password("arus_secret"),
                "raw_schema": "staging",
                "analytics_schema": "analytics",
                "is_default": True,
                "status": "connected",
            })
    finally:
        db.close()


def _seed_settings():
    """Seed default runtime settings."""
    db = SessionLocal()
    try:
        seed_default_settings(db)
    finally:
        db.close()


@app.exception_handler(ArusError)
async def arus_error_handler(request: Request, exc: ArusError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "error": {"code": exc.code, "message": str(exc)}},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "data": {"version": "0.1.0", "database": "connected", "scheduler": "running"}}


# Register routers
app.include_router(auth_router)
app.include_router(source_router)
app.include_router(destination_router)
app.include_router(pipeline_router)
app.include_router(run_log_router)
app.include_router(dashboard_router)
app.include_router(settings_router)
app.include_router(dag_router)
