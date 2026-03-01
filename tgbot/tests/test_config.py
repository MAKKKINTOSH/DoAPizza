import os
from pathlib import Path

from tgbot.config import Settings, load_dotenv_file


def test_load_dotenv_file(monkeypatch) -> None:
    env_file = Path(__file__).resolve().parents[1] / ".env.example"

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("NLP_SERVICE_BASE_URL", raising=False)
    monkeypatch.delenv("CATALOG_PIZZAS", raising=False)
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "99")

    load_dotenv_file(env_file)

    assert os.environ["TELEGRAM_API_BASE_URL"] == "https://api.telegram.org"
    assert os.environ["NLP_SERVICE_BASE_URL"] == "http://127.0.0.1:8000"
    assert os.environ["CATALOG_PIZZAS"] == "Маргарита,Пепперони,Четыре сыра,Гавайская,Диабло"
    assert os.environ["LOG_LEVEL"] == "INFO"
    assert os.environ["NLP_REQUEST_TIMEOUT_SECONDS"] == "45"
    assert os.environ["HTTP_TIMEOUT_SECONDS"] == "99"


def test_settings_from_env_uses_catalog_override(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("CATALOG_PIZZAS", "Маргарита,Пепперони")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("NLP_REQUEST_TIMEOUT_SECONDS", "55")

    settings = Settings.from_env()

    assert settings.telegram_bot_token == "token"
    assert settings.catalog_pizzas == ("Маргарита", "Пепперони")
    assert settings.log_level == "DEBUG"
    assert settings.nlp_request_timeout_seconds == 55
