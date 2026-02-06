from fastapi.testclient import TestClient

from nlp_service.app import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.text == "ok"
