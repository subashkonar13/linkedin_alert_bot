import logging
import os
from datetime import datetime


def get_logger(name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Returns a configured logger that writes to both console and a timestamped log file.
    """
    os.makedirs("logs", exist_ok=True)
    log_filename = f"logs/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not logger.handlers:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File handler
        fh = logging.FileHandler(log_filename)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
