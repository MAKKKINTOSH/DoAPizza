"""Background catalog synchronization from backend API."""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Any, Callable

import httpx


logger = logging.getLogger(__name__)

DEFAULT_FALLBACK_SIZES_CM = (25, 30, 35)


@dataclass(frozen=True)
class CatalogSnapshot:
    """Immutable snapshot of catalog data used by runtime services."""

    pizza_names: tuple[str, ...]
    sizes_cm: tuple[int, ...]
    source: str


class CatalogSync:
    """Poll backend menu endpoint and publish latest valid catalog snapshot."""

    def __init__(
        self,
        api_url: str,
        refresh_interval_seconds: int,
        http_timeout_seconds: float,
        fallback_pizzas: tuple[str, ...],
        on_update: Callable[[CatalogSnapshot], None],
    ) -> None:
        self._api_url = api_url
        self._refresh_interval_seconds = max(refresh_interval_seconds, 1)
        self._http_timeout_seconds = http_timeout_seconds
        self._on_update = on_update
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._snapshot = CatalogSnapshot(
            pizza_names=_normalize_pizza_names(fallback_pizzas),
            sizes_cm=DEFAULT_FALLBACK_SIZES_CM,
            source="fallback",
        )

    def start(self) -> None:
        """Start background synchronization loop."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="catalog-sync", daemon=True)
            self._thread.start()

        self._publish_snapshot(self.get_snapshot(), reason="initial")

    def stop(self) -> None:
        """Stop background synchronization loop."""
        self._stop_event.set()
        with self._lock:
            thread = self._thread
            self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)

    def get_snapshot(self) -> CatalogSnapshot:
        """Return latest known catalog snapshot."""
        with self._lock:
            return self._snapshot

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
            current = self.get_snapshot()
            logger.warning(
                "Catalog sync failed source=%s api_url=%s detail=%s",
                current.source,
                self._api_url,
                exc,
            )
            return

        with self._lock:
            self._snapshot = snapshot
        self._publish_snapshot(snapshot, reason="refresh")

    def _publish_snapshot(self, snapshot: CatalogSnapshot, reason: str) -> None:
        try:
            self._on_update(snapshot)
        except Exception:
            logger.exception("Catalog sync callback failed reason=%s", reason)
            return

        logger.info(
            "Catalog sync updated reason=%s source=%s pizzas=%s sizes=%s",
            reason,
            snapshot.source,
            len(snapshot.pizza_names),
            len(snapshot.sizes_cm),
        )


def _snapshot_from_payload(payload: Any) -> CatalogSnapshot:
    if not isinstance(payload, list):
        raise ValueError("Catalog payload must be a list")

    pizzas: list[str] = []
    sizes_cm: set[int] = set()
    seen_names: set[str] = set()

    for dish in payload:
        if not isinstance(dish, dict):
            continue
        if not _is_pizza_category(dish.get("category")):
            continue

        raw_name = str(dish.get("dish_name", "")).strip()
        if not raw_name:
            continue
        normalized_name = _normalize_name(raw_name)
        if normalized_name and normalized_name not in seen_names:
            seen_names.add(normalized_name)
            pizzas.append(raw_name)

        variants = dish.get("variants")
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            size_value = str(variant.get("size_value", ""))
            parsed_size = _parse_size_cm(size_value)
            if parsed_size is not None:
                sizes_cm.add(parsed_size)

    normalized_pizzas = tuple(pizzas)
    if not normalized_pizzas:
        raise ValueError("Catalog API returned no pizzas")

    normalized_sizes = tuple(sorted(sizes_cm)) if sizes_cm else DEFAULT_FALLBACK_SIZES_CM
    return CatalogSnapshot(pizza_names=normalized_pizzas, sizes_cm=normalized_sizes, source="api")


def _normalize_pizza_names(values: tuple[str, ...]) -> tuple[str, ...]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for value in values:
        stripped = value.strip()
        if not stripped:
            continue
        normalized = _normalize_name(stripped)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduplicated.append(stripped)
    return tuple(deduplicated)


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
