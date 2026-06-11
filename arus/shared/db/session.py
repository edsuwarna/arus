import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from arus.shared.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}",
    pool_size=10,
    max_overflow=5,
)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Run Alembic migrations to bring DB schema up to date."""
    from arus.shared.db.migrate import run_migrations
    run_migrations()
    logger.info("Database schema is up to date (Alembic)")
