"""
This module implements config logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

import os
from pathlib import Path


def _default_env_path() -> Path:
    """
    Execute default env path.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    return Path(__file__).resolve().parents[2] / ".env"


def _strip_quotes(value: str) -> str:
    """
    Execute strip quotes.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - value: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv_file(path: Path | None = None) -> None:
    """
    Execute load dotenv file.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - path: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    env_path = path or _default_env_path()
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue

        value = value.strip()
        if value and value[0] not in {"'", '"'} and " #" in value:
            value = value.split(" #", 1)[0].rstrip()

        os.environ.setdefault(key, _strip_quotes(value))
