import logging
import sys
from logging.handlers import RotatingFileHandler

from backend.app.config import app_configuration


def setup_logger(name: str = None) -> logging.Logger:
    """Configure and return logger with rotating file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(app_configuration.LOG_LEVEL.upper())

    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    handlers = [
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            'app.log',
            maxBytes=5242880,  # 5MB
            backupCount=3
        )
    ]

    # Add handlers to the logger (console and file)
    if not logger.handlers:
        for handler in handlers:
            handler.setFormatter(fmt)
            logger.addHandler(handler)

    return logger


logger = setup_logger()
