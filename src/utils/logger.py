"""Per-job rotating file logger. Every job appends to data/logs/<job>.log and stdout."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from src.config import CONFIG, data_path

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(getattr(logging, CONFIG.log_level.upper(), logging.INFO))
    formatter = logging.Formatter(_LOG_FORMAT)

    log_file = data_path("logs", f"{name.replace('.', '_')}.log")
    fh = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    logger.propagate = False
    return logger
