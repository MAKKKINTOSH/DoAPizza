"""Thread-safe runtime catalog snapshot used by parser and LLM prompt builder."""

from __future__ import annotations

import os
import re
import threading
from dataclasses import dataclass

DEFAULT_CATALOG_PIZZAS = (
    "Маргарита",
    "Пепперони",
    "Четыре сыра",
    "Гавайская",
    "Мясная",
    "Карбонара",
)
DEFAULT_CATALOG_SIZES_CM = (25, 30, 35)


@dataclass(frozen=True)
class CatalogSnapshot:
    pizza_names: tuple[str, ...]
    sizes_cm: tuple[int, ...]
    source: str


class CatalogRuntime:
    """Owns latest catalog snapshot with lock-protected reads/writes."""

    def __init__(self, initial_snapshot: CatalogSnapshot) -> None:
        self._lock = threading.RLock()
        self._snapshot = initial_snapshot

    def get_snapshot(self) -> CatalogSnapshot:
        with self._lock:
            return self._snapshot

    def update_snapshot(self, snapshot: CatalogSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot


def fallback_snapshot_from_env() -> CatalogSnapshot:
    return CatalogSnapshot(
        pizza_names=_parse_pizza_names(os.getenv("CATALOG_PIZZAS", "")) or DEFAULT_CATALOG_PIZZAS,
        sizes_cm=_parse_size_values(os.getenv("CATALOG_SIZE_CM", "")) or DEFAULT_CATALOG_SIZES_CM,
        source="fallback",
    )


def _parse_pizza_names(raw_value: str) -> tuple[str, ...]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for raw_item in raw_value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        normalized = _normalize_name(item)
        if normalized in seen:
            continue
        seen.add(normalized)
        deduplicated.append(item)
    return tuple(deduplicated)


def _parse_size_values(raw_value: str) -> tuple[int, ...]:
    values: set[int] = set()
    for raw_item in raw_value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        digits = re.findall(r"\d+", item)
        if not digits:
            continue
        parsed = int(digits[0])
        if parsed > 0:
            values.add(parsed)
    return tuple(sorted(values))


def _normalize_name(value: str) -> str:
    lowered = value.strip().lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", " ", lowered).strip()


catalog_runtime = CatalogRuntime(fallback_snapshot_from_env())
