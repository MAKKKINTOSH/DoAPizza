"""
This module implements test config logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

import os
from pathlib import Path

from nlp_service.config import load_dotenv_file


def test_load_dotenv_file(monkeypatch) -> None:
    """
    Execute test load dotenv file.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - monkeypatch: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    env_file = Path(__file__).resolve().parents[1] / ".env.example"

    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("CATALOG_PIZZAS", raising=False)
    monkeypatch.delenv("CATALOG_SIZE_CM", raising=False)
    monkeypatch.delenv("CATALOG_API_URL", raising=False)
    monkeypatch.delenv("DELIVERY_API_BASE_URL", raising=False)
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "99")

    load_dotenv_file(env_file)

    assert os.environ["PORT"] == "8000"
    assert os.environ["LLM_MODEL"] == "mistralai/mistral-small-3.1-24b-instruct:free"
    assert os.environ["LLM_BASE_URL"] == "https://openrouter.ai/api/v1"
    assert os.environ["CATALOG_PIZZAS"] == "Маргарита,Пепперони,Четыре сыра,Гавайская,Мясная,Карбонара"
    assert os.environ["CATALOG_SIZE_CM"] == "25,30,35"
    assert os.environ["CATALOG_API_URL"] == "http://127.0.0.1:8000/api/restaurant/variants/"
    assert os.environ["DELIVERY_API_BASE_URL"] == ""
    assert os.environ["LLM_TIMEOUT_SECONDS"] == "99"
