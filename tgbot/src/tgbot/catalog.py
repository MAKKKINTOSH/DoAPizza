"""Catalog verification and fuzzy matching of pizza names."""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass

from .schemas import Choice, Item, State


def _normalize_name(value: str) -> str:
    # Canonical form for fuzzy matching: trim, lowercase, map "ё" -> "е", drop punctuation.
    lowered = value.strip().lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", " ", lowered).strip()


def _soft_normalize_name(value: str) -> str:
    # Collapse repeated chars ("пееепперони" -> "пеперони") to soften typos.
    normalized = _normalize_name(value)
    return re.sub(r"(.)\1+", r"\1", normalized)


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        # De-duplicate by normalized value while preserving first-seen original spelling.
        normalized = _normalize_name(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


@dataclass(frozen=True)
class CatalogCheckResult:
    """Result of catalog validation for a parsed dialogue state."""
    state: State
    unknown_items: list[str]


class CatalogVerifier:
    """Resolve pizza names to canonical catalog values and prune unknown items."""
    def __init__(self, available_pizzas: tuple[str, ...]) -> None:
        self._lock = threading.RLock()
        self._available_pizzas: tuple[str, ...] = ()
        self._normalized_catalog: dict[str, str] = {}
        self._catalog_token_lengths: list[int] = []
        self.update_catalog(available_pizzas)

    def update_catalog(self, available_pizzas: tuple[str, ...]) -> None:
        """Atomically replace runtime catalog snapshot."""
        deduplicated: list[str] = []
        seen: set[str] = set()
        for item in available_pizzas:
            stripped = item.strip()
            if not stripped:
                continue
            normalized = _normalize_name(stripped)
            if normalized in seen:
                continue
            seen.add(normalized)
            deduplicated.append(stripped)

        if not deduplicated:
            # Keep existing catalog untouched when update payload is empty.
            return

        with self._lock:
            self._available_pizzas = tuple(deduplicated)
            # Map normalized catalog token -> canonical menu label shown to users.
            self._normalized_catalog = {_normalize_name(item): item for item in self._available_pizzas}
            # Precompute candidate phrase lengths; longer phrases are checked first.
            self._catalog_token_lengths = sorted(
                {len(normalized.split()) for normalized in self._normalized_catalog},
                reverse=True,
            )

    def check_state(self, state: State) -> CatalogCheckResult:
        """Return state with only known catalog items and remapped pending choices."""
        with self._lock:
            updated = state.model_copy(deep=True)
            valid_items: list[Item] = []
            index_map: dict[int, int] = {}
            unknown_items: list[str] = []

            for old_index, item in enumerate(updated.entities.items):
                # Resolve parser-provided item name to canonical catalog position.
                canonical_name = self._resolve_catalog_name(item.name)
                if canonical_name is not None:
                    item.name = canonical_name
                    # Remember old->new index map to keep pending choice aligned.
                    index_map[old_index] = len(valid_items)
                    valid_items.append(item)
                    continue
                # Keep list of rejected names for user-facing clarification.
                unknown_items.append(item.name)

            updated.entities.items = valid_items
            updated.pending_choice = self._remap_pending_choice(updated.pending_choice, index_map)
            updated.missing = self._sanitize_missing(updated, unknown_items)
            return CatalogCheckResult(state=updated, unknown_items=_deduplicate(unknown_items))

    def list_pizzas(self) -> tuple[str, ...]:
        """Return current catalog snapshot for menu display."""
        with self._lock:
            return self._available_pizzas

    def extract_pizzas_from_text(self, text: str) -> list[str]:
        """Extract canonical pizza names from free-form text."""
        with self._lock:
            tokens = _normalize_name(text).split()
            if not tokens:
                return []

            matches: list[str] = []
            index = 0
            while index < len(tokens):
                matched_name: str | None = None
                matched_length = 0
                for length in self._catalog_token_lengths:
                    # Skip phrase lengths that overflow current token window.
                    if index + length > len(tokens):
                        continue
                    candidate = " ".join(tokens[index : index + length])
                    resolved = self._resolve_catalog_name(candidate)
                    if resolved is None:
                        continue
                    matched_name = resolved
                    matched_length = length
                    break

                if matched_name is None:
                    # No match from current token, shift by one.
                    index += 1
                    continue

                matches.append(matched_name)
                # Greedy consume of matched token span.
                index += matched_length

            return _deduplicate(matches)

    def _resolve_catalog_name(self, item_name: str) -> str | None:
        """Resolve exact/typoed name to catalog item using adaptive Levenshtein threshold."""
        normalized = _normalize_name(item_name)
        exact = self._normalized_catalog.get(normalized)
        if exact is not None:
            return exact

        soft_normalized = _soft_normalize_name(item_name)
        best_match: str | None = None
        best_distance: int | None = None
        for candidate_normalized, candidate_name in self._normalized_catalog.items():
            # Compare strict and soft variants; choose the closer distance.
            distance = min(
                _levenshtein_distance(normalized, candidate_normalized),
                _levenshtein_distance(soft_normalized, _soft_normalize_name(candidate_name)),
            )
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_match = candidate_name

        if best_match is None or best_distance is None:
            return None

        threshold = _catalog_match_threshold(len(soft_normalized))
        # Adaptive threshold prevents over-matching short noisy words.
        if best_distance <= threshold:
            return best_match
        return None

    def _remap_pending_choice(self, choice: Choice | None, index_map: dict[int, int]) -> Choice | None:
        # Choice without item index is scalar question, nothing to remap.
        if choice is None or choice.item_index is None:
            return choice

        # If item was dropped as unknown, pending choice must also be dropped.
        if choice.item_index not in index_map:
            return None

        updated = choice.model_copy(deep=True)
        updated.item_index = index_map[choice.item_index]
        return updated

    def _sanitize_missing(self, state: State, unknown_items: list[str]) -> list[str]:
        missing = list(state.missing)

        if unknown_items and state.pending_choice is None:
            missing = [field for field in missing if field not in {"size_cm", "variant", "modifiers"}]

        if not state.entities.items and "items" not in missing:
            missing.insert(0, "items")

        return missing


def _levenshtein_distance(left: str, right: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous_row = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        # Dynamic-programming row computes min cost to align prefixes.
        current_row = [i]
        for j, right_char in enumerate(right, start=1):
            insertions = previous_row[j] + 1
            deletions = current_row[j - 1] + 1
            substitutions = previous_row[j - 1] + (left_char != right_char)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def _catalog_match_threshold(length: int) -> int:
    """Distance threshold grows with token length to reduce false positives."""
    if length <= 5:
        return 1
    if length <= 9:
        return 2
    return 3
