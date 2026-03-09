"""
This module implements logging logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """
    Execute configure logging.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - level: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
