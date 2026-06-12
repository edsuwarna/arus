"""
Arus — Data Pipeline Framework
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CDC & ETL framework, opinionated but flexible.
"""
__version__ = "0.1.0"

import logging
import sys

from arus.shared.config import settings


def _configure_logging():
    """Configure root logging for arus with structured format."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="[%(asctime)s] %(name)-45s → %(levelname)-5s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # Override uvicorn's config for our namespaces
    )

    # Set uvicorn access logs to match our level
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(level)

    # Keep SQLAlchemy quiet unless DEBUG
    if level > logging.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

    return logging.getLogger(__name__)


logger = _configure_logging()
