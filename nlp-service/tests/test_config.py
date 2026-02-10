import os
from pathlib import Path

from nlp_service.config import load_dotenv_file


def test_load_dotenv_file(monkeypatch) -> None:
    env_file = Path(__file__).resolve().parents[1] / ".env.example"

    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("DELIVERY_API_BASE_URL", raising=False)
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "99")

    load_dotenv_file(env_file)

    assert os.environ["PORT"] == "8000"
    assert os.environ["LLM_API_KEY"] == ""
    assert os.environ["OPENROUTER_API_KEY"] == ""
    assert os.environ["LLM_MODEL"] == "mistralai/mistral-small-3.1-24b-instruct:free"
    assert os.environ["DELIVERY_API_BASE_URL"] == ""
    assert os.environ["LLM_TIMEOUT_SECONDS"] == "99"
