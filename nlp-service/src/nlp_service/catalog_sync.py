"""Background catalog synchronization for nlp-service runtime snapshot."""

from __future__ import annotations

import logging
import re
import threading
from typing import Any

import httpx

from .catalog_runtime import CatalogSnapshot, catalog_runtime, fallback_snapshot_from_env


logger = logging.getLogger(__name__)


class CatalogSync:
    """Periodically fetch backend catalog and keep latest valid snapshot."""

    def __init__(
        self,
        api_url: str,
        refresh_interval_seconds: int,
        http_timeout_seconds: float,
    ) -> None:
        self._api_url = api_url
        self._refresh_interval_seconds = max(refresh_interval_seconds, 1)
        self._http_timeout_seconds = http_timeout_seconds
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="nlp-catalog-sync", daemon=True)
            self._thread.start()

        # Always publish fallback on startup before first API refresh.
        fallback = fallback_snapshot_from_env()
        catalog_runtime.update_snapshot(fallback)
        logger.info(
            "Catalog sync initialized source=%s pizzas=%s sizes=%s",
            fallback.source,
            len(fallback.pizza_names),
            len(fallback.sizes_cm),
        )

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            thread = self._thread
            self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self._refresh_once()
            self._stop_event.wait(self._refresh_interval_seconds)

    def _refresh_once(self) -> None:
        try:
            with httpx.Client(timeout=self._http_timeout_seconds, trust_env=False) as client:
                response = client.get(self._api_url)
            response.raise_for_status()
            snapshot = _snapshot_from_payload(response.json())
        except Exception as exc:
            current = catalog_runtime.get_snapshot()
            logger.warning(
                "Catalog sync failed source=%s api_url=%s detail=%s",
                current.source,
                self._api_url,
                exc,
            )
            return

        catalog_runtime.update_snapshot(snapshot)
        logger.info(
            "Catalog sync updated source=%s pizzas=%s sizes=%s",
            snapshot.source,
            len(snapshot.pizza_names),
            len(snapshot.sizes_cm),
        )


def _snapshot_from_payload(payload: Any) -> CatalogSnapshot:
    if not isinstance(payload, list):
        raise ValueError("Catalog payload must be a list")

    pizzas: list[str] = []
    seen_names: set[str] = set()
    sizes_cm: set[int] = set()

    for dish in payload:
        if not isinstance(dish, dict):
            continue
        if not _is_pizza_category(dish.get("category")):
            continue

        raw_name = str(dish.get("dish_name", "")).strip()
        if not raw_name:
            continue
        normalized_name = _normalize_name(raw_name)
        if normalized_name not in seen_names:
            seen_names.add(normalized_name)
            pizzas.append(raw_name)

        variants = dish.get("variants")
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            parsed_size = _parse_size_cm(str(variant.get("size_value", "")))
            if parsed_size is not None:
                sizes_cm.add(parsed_size)

    if not pizzas:
        raise ValueError("Catalog API returned no pizza items")

    return CatalogSnapshot(
        pizza_names=tuple(pizzas),
        sizes_cm=tuple(sorted(sizes_cm)) or fallback_snapshot_from_env().sizes_cm,
        source="api",
    )


def _is_pizza_category(value: Any) -> bool:
    if isinstance(value, dict):
        category_name = str(value.get("name", "")).strip().lower().replace("ё", "е")
        return category_name == "пицца"
    if isinstance(value, str):
        return value.strip().lower().replace("ё", "е") == "пицца"
    return False


def _parse_size_cm(value: str) -> int | None:
    match = re.search(r"\d+", value)
    if match is None:
        return None
    return int(match.group(0))


def _normalize_name(value: str) -> str:
    lowered = value.strip().lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", " ", lowered).strip()
