"""Shared dotenv loader for NLP service processes."""

import os
from pathlib import Path


def _default_env_path() -> Path:
    """Return default `.env` location relative to service root."""
    return Path(__file__).resolve().parents[2] / ".env"


def _strip_quotes(value: str) -> str:
    """Remove wrapping single/double quotes when present."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv_file(path: Path | None = None) -> None:
    """Load `.env` values without overriding already exported variables."""
    # Use explicit path if provided (tests), otherwise default project `.env`.
    env_path = path or _default_env_path()
    # Missing `.env` is not an error: production often injects env vars externally.
    if not env_path.is_file():
        return

    # Process file line-by-line to keep parsing rules simple and predictable.
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        # Remove surrounding whitespace/newlines before any checks.
        line = raw_line.strip()
        # Skip empty rows and full-line comments.
        if not line or line.startswith("#"):
            continue

        # Support shell-style `export KEY=VALUE` rows.
        if line.startswith("export "):
            line = line[7:].lstrip()

        # Ignore malformed rows without key/value separator.
        if "=" not in line:
            continue

        # Split only on first '=' so values may contain '=' later.
        key, value = line.split("=", 1)
        key = key.strip()
        # Ignore rows with empty key after trimming.
        if not key:
            continue

        value = value.strip()
        # For unquoted values allow inline comments: `KEY=value # comment`.
        if value and value[0] not in {"'", '"'} and " #" in value:
            value = value.split(" #", 1)[0].rstrip()

        # Do not overwrite existing process env (CLI/CI values take precedence).
        os.environ.setdefault(key, _strip_quotes(value))
