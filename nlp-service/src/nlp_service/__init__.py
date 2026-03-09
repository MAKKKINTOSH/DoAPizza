"""
This module implements init logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from .config import load_dotenv_file

load_dotenv_file()

__all__ = ["app"]
