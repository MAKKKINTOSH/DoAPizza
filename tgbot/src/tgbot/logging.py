"""Minimal logging setup shared by bot modules."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configure root logging once at process startup."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
