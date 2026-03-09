"""
This module implements logging logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


DEFAULT_LOG_FILE_PATH = "logs/nlp-service.log"


def configure_logging() -> None:
    """
    Execute configure logging.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    root_logger = logging.getLogger()
    if getattr(root_logger, "_nlp_service_configured", False):
        return

    console_level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    file_level_name = os.getenv("LOG_FILE_LEVEL", "DEBUG").strip().upper()
    log_file_path = os.getenv("LOG_FILE_PATH", DEFAULT_LOG_FILE_PATH).strip() or DEFAULT_LOG_FILE_PATH

    console_level = getattr(logging, console_level_name, logging.INFO)
    file_level = getattr(logging, file_level_name, logging.DEBUG)

    root_logger.handlers.clear()
    root_logger.setLevel(min(console_level, file_level))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(_build_console_formatter())

    file_handler = _build_file_handler(log_file_path, file_level)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger._nlp_service_configured = True  # type: ignore[attr-defined]

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def _build_file_handler(path_value: str, level: int) -> RotatingFileHandler:
    """
    Execute build file handler.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - path_value: input consumed by this function while processing the current request.
    - level: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    log_path = Path(path_value)
    if not log_path.is_absolute():
        log_path = Path.cwd() / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s "
            "(file=%(pathname)s line=%(lineno)d)"
        )
    )
    return handler


def _build_console_formatter() -> logging.Formatter:
    """
    Execute build console formatter.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    try:
        from uvicorn.logging import DefaultFormatter

        return DefaultFormatter(
            fmt="%(levelprefix)s [%(name)s] %(message)s",
            use_colors=True,
        )
    except Exception:
        return _ColorFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")


class _ColorFormatter(logging.Formatter):
    """
    Represents ColorFormatter.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    COLORS = {
        logging.DEBUG: "\x1b[36m",
        logging.INFO: "\x1b[32m",
        logging.WARNING: "\x1b[33m",
        logging.ERROR: "\x1b[31m",
        logging.CRITICAL: "\x1b[35m",
    }
    RESET = "\x1b[0m"

    def format(self, record: logging.LogRecord) -> str:
        """
        Execute format.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - record: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        original_levelname = record.levelname
        color = self.COLORS.get(record.levelno)
        if color:
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original_levelname
