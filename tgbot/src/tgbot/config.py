"""Environment loading and strongly-typed bot settings."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


def _default_env_path() -> Path:
    """Return default `.env` location relative to the `tgbot` project root."""
    return Path(__file__).resolve().parents[2] / ".env"


def _strip_quotes(value: str) -> str:
    """Remove matching wrapping quotes from an env value."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv_file(path: Path | None = None) -> None:
    """Load key/value pairs from `.env` into `os.environ` without overriding existing vars."""
    # Explicit path is handy for tests; default path is used in normal startup.
    env_path = path or _default_env_path()
    # Missing `.env` is valid when env comes from container/orchestrator.
    if not env_path.is_file():
        return

    # Parse file manually to keep behavior identical in every runtime.
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        # Trim spaces/newlines before checking syntax.
        line = raw_line.strip()
        # Ignore empty and comment-only rows.
        if not line or line.startswith("#"):
            continue

        # Allow shell format: `export KEY=VALUE`.
        if line.startswith("export "):
            line = line[7:].lstrip()

        # Skip malformed rows without key-value separator.
        if "=" not in line:
            continue

        # Split on first '=' so value may also contain '='.
        key, value = line.split("=", 1)
        key = key.strip()
        # Empty key after trimming is invalid.
        if not key:
            continue

        value = value.strip()
        # For unquoted values support inline comments after ` #`.
        if value and value[0] not in {"'", '"'} and " #" in value:
            value = value.split(" #", 1)[0].rstrip()

        # Keep already exported vars intact (CLI/CI override file defaults).
        os.environ.setdefault(key, _strip_quotes(value))


class Settings(BaseModel):
    """Runtime configuration used by the bot and its external integrations."""
    telegram_bot_token: str = Field(min_length=1)
    telegram_api_base_url: str = "https://api.telegram.org"
    nlp_service_base_url: str = "http://127.0.0.1:8000"
    telegram_poll_timeout_seconds: int = 30
    http_timeout_seconds: float = 10.0
    nlp_request_timeout_seconds: float = 45.0
    log_level: str = "INFO"
    catalog_pizzas: tuple[str, ...] = (
        "Маргарита",
        "Пепперони",
        "Четыре сыра",
        "Гавайская",
        "Диабло",
    )

    @classmethod
    def from_env(cls) -> "Settings":
        """Build validated settings from environment variables."""
        raw_catalog = os.getenv("CATALOG_PIZZAS", "")
        # CATALOG_PIZZAS is comma-separated in env.
        catalog_items = tuple(item.strip() for item in raw_catalog.split(",") if item.strip())

        payload = {
            "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            "telegram_api_base_url": os.getenv("TELEGRAM_API_BASE_URL", "https://api.telegram.org").rstrip("/"),
            "nlp_service_base_url": os.getenv("NLP_SERVICE_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            "telegram_poll_timeout_seconds": int(os.getenv("TELEGRAM_POLL_TIMEOUT_SECONDS", "30")),
            "http_timeout_seconds": float(os.getenv("HTTP_TIMEOUT_SECONDS", "10")),
            "nlp_request_timeout_seconds": float(os.getenv("NLP_REQUEST_TIMEOUT_SECONDS", "45")),
            "log_level": os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        }
        if catalog_items:
            # Override default catalog only when non-empty custom list was provided.
            payload["catalog_pizzas"] = catalog_items
        return cls.model_validate(payload)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance for process lifetime."""
    return Settings.from_env()
