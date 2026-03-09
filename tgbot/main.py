"""
This module implements main logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from tgbot.bot import run_polling
from tgbot.config import get_settings, load_dotenv_file
from tgbot.logging import configure_logging


def main() -> None:
    """
    Execute main.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    load_dotenv_file()
    configure_logging(get_settings().log_level)
    run_polling()


if __name__ == "__main__":
    main()
