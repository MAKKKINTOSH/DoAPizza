"""
This module implements catalog logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .schemas import Choice, Item, State


def _normalize_name(value: str) -> str:
    """
    Execute normalize name.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - value: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    lowered = value.strip().lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", " ", lowered).strip()


def _soft_normalize_name(value: str) -> str:
    """
    Execute soft normalize name.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - value: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    normalized = _normalize_name(value)
    return re.sub(r"(.)\1+", r"\1", normalized)


def _deduplicate(values: list[str]) -> list[str]:
    """
    Execute deduplicate.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - values: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = _normalize_name(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


@dataclass(frozen=True)
class CatalogCheckResult:
    """
    Represents CatalogCheckResult.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    state: State
    unknown_items: list[str]


class CatalogVerifier:
    """
    Represents CatalogVerifier.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    def __init__(self, available_pizzas: tuple[str, ...]) -> None:
        """
        Execute init.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - available_pizzas: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        self._available_pizzas = available_pizzas
        self._normalized_catalog = {_normalize_name(item): item for item in available_pizzas}
        self._catalog_token_lengths = sorted(
            {len(normalized.split()) for normalized in self._normalized_catalog},
            reverse=True,
        )

    def check_state(self, state: State) -> CatalogCheckResult:
        """
        Execute check state.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        updated = state.model_copy(deep=True)
        valid_items: list[Item] = []
        index_map: dict[int, int] = {}
        unknown_items: list[str] = []

        for old_index, item in enumerate(updated.entities.items):
            canonical_name = self._resolve_catalog_name(item.name)
            if canonical_name is not None:
                item.name = canonical_name
                index_map[old_index] = len(valid_items)
                valid_items.append(item)
                continue
            unknown_items.append(item.name)

        updated.entities.items = valid_items
        updated.pending_choice = self._remap_pending_choice(updated.pending_choice, index_map)
        updated.missing = self._sanitize_missing(updated, unknown_items)
        return CatalogCheckResult(state=updated, unknown_items=_deduplicate(unknown_items))

    def extract_pizzas_from_text(self, text: str) -> list[str]:
        """
        Execute extract pizzas from text.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - text: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        tokens = _normalize_name(text).split()
        if not tokens:
            return []

        matches: list[str] = []
        index = 0
        while index < len(tokens):
            matched_name: str | None = None
            matched_length = 0
            for length in self._catalog_token_lengths:
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
                index += 1
                continue

            matches.append(matched_name)
            index += matched_length

        return _deduplicate(matches)

    def _resolve_catalog_name(self, item_name: str) -> str | None:
        """
        Execute resolve catalog name.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - item_name: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        normalized = _normalize_name(item_name)
        exact = self._normalized_catalog.get(normalized)
        if exact is not None:
            return exact

        soft_normalized = _soft_normalize_name(item_name)
        best_match: str | None = None
        best_distance: int | None = None
        for candidate_normalized, candidate_name in self._normalized_catalog.items():
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
        if best_distance <= threshold:
            return best_match
        return None

    def _remap_pending_choice(self, choice: Choice | None, index_map: dict[int, int]) -> Choice | None:
        """
        Execute remap pending choice.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - choice: input consumed by this function while processing the current request.
        - index_map: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if choice is None or choice.item_index is None:
            return choice

        if choice.item_index not in index_map:
            return None

        updated = choice.model_copy(deep=True)
        updated.item_index = index_map[choice.item_index]
        return updated

    def _sanitize_missing(self, state: State, unknown_items: list[str]) -> list[str]:
        """
        Execute sanitize missing.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - state: input consumed by this function while processing the current request.
        - unknown_items: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        missing = list(state.missing)

        if unknown_items and state.pending_choice is None:
            missing = [field for field in missing if field not in {"size_cm", "variant", "modifiers"}]

        if not state.entities.items and "items" not in missing:
            missing.insert(0, "items")

        return missing


def _levenshtein_distance(left: str, right: str) -> int:
    """
    Execute levenshtein distance.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - left: input consumed by this function while processing the current request.
    - right: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous_row = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current_row = [i]
        for j, right_char in enumerate(right, start=1):
            insertions = previous_row[j] + 1
            deletions = current_row[j - 1] + 1
            substitutions = previous_row[j - 1] + (left_char != right_char)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def _catalog_match_threshold(length: int) -> int:
    """
    Execute catalog match threshold.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - length: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    if length <= 5:
        return 1
    if length <= 9:
        return 2
    return 3
