from fastapi.testclient import TestClient

from nlp_service.app import app
from nlp_service.llm import LLMResult
from nlp_service.schemas import Entities, Item


def test_parse_ready(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Margherita", qty=1)]),
                missing=[],
                choices=None,
                message="Готово.",
                confidence=0.9,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post("/v1/parse", json={"text": "1 маргарита"})
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "READY"
    assert data["entities"]["items"]