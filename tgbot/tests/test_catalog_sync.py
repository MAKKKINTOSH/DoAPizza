"""Tests for runtime catalog synchronization in tgbot."""

from __future__ import annotations

from tgbot.catalog import CatalogVerifier
from tgbot.catalog_sync import CatalogSync


class _FakeResponse:
    def __init__(self, payload) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class _FakeClient:
    def __init__(self, payload) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str) -> _FakeResponse:
        return _FakeResponse(self._payload)


def test_catalog_sync_updates_verifier_from_api_payload(monkeypatch) -> None:
    verifier = CatalogVerifier(("Маргарита",))
    payload = [
        {
            "dish_name": "Карбонара",
            "category": {"id": 1, "name": "Пицца"},
            "variants": [{"id": 17, "size_value": "30 см"}],
        },
        {
            "dish_name": "Кока-Кола",
            "category": {"id": 3, "name": "Напитки"},
            "variants": [{"id": 26, "size_value": "500 мл"}],
        },
    ]

    monkeypatch.setattr("tgbot.catalog_sync.httpx.Client", lambda **kwargs: _FakeClient(payload))

    sync = CatalogSync(
        api_url="http://example.test/api/restaurant/variants/",
        refresh_interval_seconds=300,
        http_timeout_seconds=5.0,
        fallback_pizzas=("Маргарита",),
        on_update=lambda snapshot: verifier.update_catalog(snapshot.pizza_names),
    )

    sync._refresh_once()

    assert verifier.extract_pizzas_from_text("хочу карбонара") == ["Карбонара"]
    assert verifier.extract_pizzas_from_text("хочу колу") == []
    assert sync.get_snapshot().sizes_cm == (30,)


def test_catalog_sync_keeps_previous_snapshot_on_failure(monkeypatch) -> None:
    snapshots = []

    payload = [
        {
            "dish_name": "Мясная",
            "category": {"id": 1, "name": "Пицца"},
            "variants": [{"id": 13, "size_value": "25 см"}, {"id": 14, "size_value": "30 см"}],
        }
    ]
    sync = CatalogSync(
        api_url="http://example.test/api/restaurant/variants/",
        refresh_interval_seconds=300,
        http_timeout_seconds=5.0,
        fallback_pizzas=("Маргарита",),
        on_update=lambda snapshot: snapshots.append(snapshot),
    )

    monkeypatch.setattr("tgbot.catalog_sync.httpx.Client", lambda **kwargs: _FakeClient(payload))
    sync._refresh_once()
    first = sync.get_snapshot()

    def _raising_client(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("tgbot.catalog_sync.httpx.Client", _raising_client)
    sync._refresh_once()
    second = sync.get_snapshot()

    assert first == second
    assert first.source == "api"
    assert first.pizza_names == ("Мясная",)
    assert len(snapshots) == 1
