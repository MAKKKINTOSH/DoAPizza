"""Logging setup with colored console and rotating file output."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


DEFAULT_LOG_FILE_PATH = "logs/nlp-service.log"


def configure_logging() -> None:
    """Configure root logger once for API process lifetime."""
    root_logger = logging.getLogger()
    # Prevent duplicate handlers when app re-imports in dev/hot-reload scenarios.
    if getattr(root_logger, "_nlp_service_configured", False):
        return

    # Console and file levels are split intentionally:
    # console = operator-friendly signal, file = full diagnostics.
    console_level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    file_level_name = os.getenv("LOG_FILE_LEVEL", "DEBUG").strip().upper()
    log_file_path = os.getenv("LOG_FILE_PATH", DEFAULT_LOG_FILE_PATH).strip() or DEFAULT_LOG_FILE_PATH

    console_level = getattr(logging, console_level_name, logging.INFO)
    file_level = getattr(logging, file_level_name, logging.DEBUG)

    # Rebuild handlers from scratch to avoid mixed formatters from previous setup.
    root_logger.handlers.clear()
    # Root must accept both targets, so use more permissive of the two levels.
    root_logger.setLevel(min(console_level, file_level))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(_build_console_formatter())

    file_handler = _build_file_handler(log_file_path, file_level)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger._nlp_service_configured = True  # type: ignore[attr-defined]

    # Keep noisy libraries under control.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def _build_file_handler(path_value: str, level: int) -> RotatingFileHandler:
    """Create rotating file handler and ensure target directory exists."""
    log_path = Path(path_value)
    # Relative path is resolved from current process working directory.
    if not log_path.is_absolute():
        log_path = Path.cwd() / log_path
    # Create directory once; safe if already exists.
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
    """Prefer uvicorn formatter; fallback to local ANSI formatter."""
    try:
        from uvicorn.logging import DefaultFormatter

        # Uvicorn formatter renders colored levelprefix consistently with ASGI logs.
        return DefaultFormatter(
            fmt="%(levelprefix)s [%(name)s] %(message)s",
            use_colors=True,
        )
    except Exception:
        # If uvicorn formatter is unavailable, keep readable color output ourselves.
        return _ColorFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")


class _ColorFormatter(logging.Formatter):
    """ANSI-colored formatter used when uvicorn formatter is unavailable."""
    COLORS = {
        logging.DEBUG: "\x1b[36m",
        logging.INFO: "\x1b[32m",
        logging.WARNING: "\x1b[33m",
        logging.ERROR: "\x1b[31m",
        logging.CRITICAL: "\x1b[35m",
    }
    RESET = "\x1b[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Wrap level name with color code and restore original record after formatting."""
        original_levelname = record.levelname
        color = self.COLORS.get(record.levelno)
        # Mutate record only temporarily; many handlers may share the same object.
        if color:
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        try:
            return super().format(record)
        finally:
            # Always restore original value to avoid color codes leaking to file logs.
            record.levelname = original_levelname
