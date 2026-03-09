"""
This module implements config logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


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


class Settings(BaseModel):
    """
    Represents Settings.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
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
        """
        Execute from env.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - cls: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        raw_catalog = os.getenv("CATALOG_PIZZAS", "")
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
            payload["catalog_pizzas"] = catalog_items
        return cls.model_validate(payload)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Execute get settings.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    return Settings.from_env()
