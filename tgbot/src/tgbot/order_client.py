"""HTTP client for submitting confirmed orders to the backend API."""

from __future__ import annotations

import logging
import re
import threading

import httpx

from .catalog_sync import CatalogSnapshot
from .schemas import Entities

logger = logging.getLogger(__name__)


def _normalize_name(value: str) -> str:
    """Canonical form for catalog key lookup (must match catalog_sync._normalize_name)."""
    lowered = value.strip().lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", " ", lowered).strip()


class OrderClient:
    """Resolves pizza variants and submits orders to POST /api/orders/create."""

    def __init__(self, api_url: str, timeout_seconds: float) -> None:
        self._api_url = api_url
        self._timeout = timeout_seconds
        self._lock = threading.RLock()
        self._variant_map: dict[tuple[str, int], int] = {}

    def update_catalog(self, snapshot: CatalogSnapshot) -> None:
        """Replace variant map from a fresh catalog snapshot."""
        with self._lock:
            self._variant_map = dict(snapshot.variant_map)
        logger.debug("OrderClient catalog updated variant_map_size=%s", len(snapshot.variant_map))

    def resolve_variant_id(self, name: str, size_cm: int | None) -> int | None:
        """Return dish_variant_id for a canonical pizza name and size, or None if unknown."""
        if size_cm is None:
            return None
        key = (_normalize_name(name), size_cm)
        with self._lock:
            return self._variant_map.get(key)

    def submit(self, entities: Entities) -> int | None:
        """POST order to the backend. Returns order id on success, None on failure."""
        items = []
        for item in entities.items:
            variant_id = self.resolve_variant_id(item.name, item.size_cm)
            if variant_id is None:
                logger.warning(
                    "Cannot resolve variant_id for item name=%r size_cm=%s — item skipped",
                    item.name,
                    item.size_cm,
                )
                continue
            items.append({"dish_variant_id": variant_id, "quantity": item.qty})

        if not items:
            logger.error("Order submission skipped: no resolvable items")
            return None

        payload: dict = {"phone_number": entities.phone, "items": items}
        if entities.address:
            payload["address"] = entities.address
        if entities.comment:
            payload["comment"] = entities.comment

        logger.info(
            "Submitting order to backend api_url=%s phone=%s items=%s",
            self._api_url,
            entities.phone,
            len(items),
        )
        try:
            with httpx.Client(timeout=self._timeout, trust_env=False) as client:
                response = client.post(self._api_url, json=payload)
            response.raise_for_status()
            order_id: int | None = response.json().get("id")
            logger.info("Order submitted successfully order_id=%s", order_id)
            return order_id
        except httpx.HTTPError as exc:
            logger.exception("Order submission failed: %s", exc)
            return None
