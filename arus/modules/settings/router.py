"""
Settings Router — store/retrieve Arus runtime config via UI.
Overrides environment-based defaults with DB-persisted settings.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

from arus.shared.db.session import Base, get_db, engine as db_engine
from arus.shared.config import settings as env_settings
from arus.modules.auth.router import get_current_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class RuntimeSetting(Base):
    """Per-key runtime settings stored in DB."""
    __tablename__ = "runtime_settings"
    __table_args__ = {"schema": "arus_config"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))


def ensure_settings_table():
    """Ensure arus_config schema exists (migration handles the rest)."""
    try:
        with db_engine.connect() as conn:
            conn.execute('CREATE SCHEMA IF NOT EXISTS arus_config;')
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to create arus_config schema: {e}")


DEFAULT_SETTINGS = {
    "pipeline_name_prefix": "arus-prod-",
    "default_schedule": "*/5 * * * *",
    "auto_discover_tables": "true",
    "schema_drift_detection": "true",
    "auto_alter_schema": "false",
    "max_retries": "3",
    "initial_backoff": "2",
    "quality_check_threshold": "5.0",
    "notify_pipeline_failures": "true",
    "notify_schema_drift": "true",
    "notify_dead_letter": "true",
}


def seed_default_settings(db: Session):
    """Insert default settings if they don't exist."""
    for key, default_value in DEFAULT_SETTINGS.items():
        existing = db.query(RuntimeSetting).filter(RuntimeSetting.key == key).first()
        if not existing:
            db.add(RuntimeSetting(key=key, value=default_value))
    db.commit()


@router.get("")
async def get_settings(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Return all settings as a key-value map."""
    rows = db.query(RuntimeSetting).all()
    settings_dict = dict(DEFAULT_SETTINGS)
    for r in rows:
        settings_dict[r.key] = r.value
    return {"status": "ok", "data": settings_dict}


@router.put("")
async def update_settings(
    updates: dict,
    db: Session = Depends(get_db),
    user: dict = Depends(require_admin),
):
    """Update one or more settings. Only accepts keys in DEFAULT_SETTINGS."""
    for key, value in updates.items():
        if key not in DEFAULT_SETTINGS:
            continue
        existing = db.query(RuntimeSetting).filter(RuntimeSetting.key == key).first()
        if existing:
            existing.value = str(value)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.add(RuntimeSetting(key=key, value=str(value)))
    db.commit()
    return await get_settings(db=db, user=user)
