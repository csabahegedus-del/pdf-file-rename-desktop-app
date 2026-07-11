"""
logger_setup.py – configures file and console logging for the program.
"""
import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(log_dir: Path | None = None, level: int = logging.DEBUG) -> logging.Logger:
    """Set up and return the root logger with both file and console handlers."""
    if log_dir is None:
        base = Path(__file__).parent.parent
        log_dir = base / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pdf_rename_{timestamp}.log"

    logger = logging.getLogger("pdf_rename")
    logger.setLevel(level)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger.info("Logging initialised → %s", log_file)
    return logger
