"""NLP service package.

Loads `.env` on import so local runs and tests have the same env initialization path.
"""

from .config import load_dotenv_file

load_dotenv_file()

__all__ = ["app"]
