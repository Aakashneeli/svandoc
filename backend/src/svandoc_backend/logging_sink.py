"""Structured logging sink configuration."""

from __future__ import annotations

import logging
import os
from pathlib import Path

_CONFIGURED = False


def _build_sink_handler() -> logging.Handler:
    sink_path = os.getenv("STRUCTURED_LOG_SINK_PATH", "").strip()
    if sink_path:
        path = Path(sink_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return logging.FileHandler(path, mode="a", encoding="utf-8")
    return logging.StreamHandler()


def configure_structured_logging(*, force: bool = False) -> None:
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    for logger_name in ("svandoc.api", "svandoc.worker"):
        logger = logging.getLogger(logger_name)
        for existing_handler in list(logger.handlers):
            logger.removeHandler(existing_handler)
            existing_handler.close()
        handler = _build_sink_handler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(handler)

    _CONFIGURED = True
