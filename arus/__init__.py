"""
Arus — Data Pipeline Framework
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CDC & ETL framework, opinionated but flexible.
"""
__version__ = "0.1.0"

import logging
import sys

from arus.shared.config import settings

LOG_FORMAT = "[%(asctime)s] %(name)-45s → %(levelname)-5s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


def configure_logging():
    """Configure logging.

    Must be called *after* uvicorn has finished its own config
    (i.e. inside the FastAPI lifespan / startup event) because
    uvicorn calls dictConfig at server start and would otherwise
    override our root logger setup.
    """
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATEFMT,
        stream=sys.stdout,
        force=True,
    )

    # Tame uvicorn's own access logger at INFO
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(level)

    # Keep SQLAlchemy quiet unless DEBUG
    if level > logging.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.info("Logging configured (level=%s)", settings.log_level)
    return logger


# Initialise at module level so loggers are ready before startup,
# but uvicorn will override; startup event calls configure_logging()
# again to re-apply after uvicorn's dictConfig.
_logger = configure_logging()
