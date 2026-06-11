"""Arus migration runner — wraps Alembic for programmatic use."""

import os
import logging
from pathlib import Path

from alembic.config import Config
from alembic import command
import arus

logger = logging.getLogger(__name__)

# Project root = the directory containing arus package
_ARUS_PACKAGE = Path(arus.__file__).resolve().parent  # /app/arus/
_PROJECT_ROOT = _ARUS_PACKAGE.parent  # /app/
_ALEMBIC_CFG = str(_PROJECT_ROOT / "alembic.ini")


def run_migrations():
    """Run all pending Alembic migrations. Idempotent."""
    alembic_cfg = Config(_ALEMBIC_CFG)
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations up to date")


def stamp_head():
    """Stamp the current database as up-to-date without running migrations.
    Useful for first-time setup on an existing database."""
    alembic_cfg = Config(_ALEMBIC_CFG)
    command.stamp(alembic_cfg, "head")


def create_migration(message: str):
    """Auto-generate a new migration revision."""
    alembic_cfg = Config(_ALEMBIC_CFG)
    command.revision(alembic_cfg, autogenerate=True, message=message)
