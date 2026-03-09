"""
This module implements main logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

import uvicorn

from nlp_service.app import app, get_port
from nlp_service.logging import configure_logging


def main() -> None:
    """
    Execute main.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    configure_logging()
    uvicorn.run(app, host="0.0.0.0", port=get_port(), log_config=None)


if __name__ == "__main__":
    main()
