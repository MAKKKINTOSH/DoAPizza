"""
This module implements test health logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from fastapi.testclient import TestClient

from nlp_service.app import app


def test_health() -> None:
    """
    Execute test health.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.text == "ok"
