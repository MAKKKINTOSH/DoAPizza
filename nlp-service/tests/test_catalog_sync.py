"""Tests for nlp-service catalog background synchronization."""

from __future__ import annotations

from nlp_service.catalog_runtime import CatalogSnapshot, catalog_runtime
from nlp_service.catalog_sync import CatalogSync


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


def test_catalog_sync_updates_runtime_snapshot(monkeypatch) -> None:
    previous = catalog_runtime.get_snapshot()
    payload = [
        {
            "dish_name": "Карбонара",
            "category": {"id": 1, "name": "Пицца"},
            "variants": [{"id": 17, "size_value": "30 см"}],
        }
    ]
    monkeypatch.setattr("nlp_service.catalog_sync.httpx.Client", lambda **kwargs: _FakeClient(payload))

    sync = CatalogSync(
        api_url="http://example.test/api/restaurant/variants/",
        refresh_interval_seconds=300,
        http_timeout_seconds=5.0,
    )

    try:
        sync._refresh_once()
        snapshot = catalog_runtime.get_snapshot()
        assert snapshot.source == "api"
        assert snapshot.pizza_names == ("Карбонара",)
        assert snapshot.sizes_cm == (30,)
    finally:
        catalog_runtime.update_snapshot(previous)


def test_catalog_sync_keeps_previous_snapshot_on_failure(monkeypatch) -> None:
    previous = catalog_runtime.get_snapshot()
    catalog_runtime.update_snapshot(
        CatalogSnapshot(
            pizza_names=("Маргарита",),
            sizes_cm=(25, 30, 35),
            source="api",
        )
    )

    def _raising_client(**kwargs):
        raise RuntimeError("unavailable")

    monkeypatch.setattr("nlp_service.catalog_sync.httpx.Client", _raising_client)
    sync = CatalogSync(
        api_url="http://example.test/api/restaurant/variants/",
        refresh_interval_seconds=300,
        http_timeout_seconds=5.0,
    )

    try:
        sync._refresh_once()
        snapshot = catalog_runtime.get_snapshot()
        assert snapshot.source == "api"
        assert snapshot.pizza_names == ("Маргарита",)
        assert snapshot.sizes_cm == (25, 30, 35)
    finally:
        catalog_runtime.update_snapshot(previous)
