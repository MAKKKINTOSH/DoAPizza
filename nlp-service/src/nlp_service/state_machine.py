"""
This module implements state machine logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

import re
from collections import Counter
from typing import Iterable

from .schemas import Entities, Item, State


def apply_pending_choice(state: State, text: str) -> tuple[State, bool, str | None]:
    """
    Execute apply pending choice.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - state: input consumed by this function while processing the current request.
    - text: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    if not state.pending_choice:
        return state, False, None

    selected = _match_choice(text, state.pending_choice.options)
    if selected is None:
        return state, False, None

    updated = state.model_copy(deep=True)
    _apply_choice_value(updated, state.pending_choice.field, selected, state.pending_choice.item_index)
    updated.pending_choice = None
    updated.missing = [m for m in updated.missing if m != state.pending_choice.field]
    return updated, True, selected


def merge_entities(base: Entities, incoming: Entities) -> Entities:
    """
    Execute merge entities.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - base: input consumed by this function while processing the current request.
    - incoming: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    merged = base.model_copy(deep=True)

    if incoming.items:
        if _is_same_items(base.items, incoming.items):
            pass
        elif _looks_like_full_state_echo(base.items, incoming.items):
            merged.items = [item.model_copy(deep=True) for item in incoming.items]
        elif _only_repeats_existing_items(base.items, incoming.items):
            pass
        else:
            merged.items.extend(incoming.items)

    for field in ["delivery_type", "address", "time", "phone", "comment"]:
        value = getattr(incoming, field)
        if value is not None and value != "":
            setattr(merged, field, value)

    return merged


def is_choice_only(text: str) -> bool:
    """
    Execute is choice only.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - text: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    stripped = text.strip()
    if not stripped:
        return True
    if _is_skip_text(stripped):
        return True
    if re.fullmatch(r"\d+", stripped):
        return True
    if re.fullmatch(r"\d+\s*(cm|sm|cm\.)?", stripped, re.IGNORECASE):
        return True
    if re.fullmatch(r"\d+\s*(см)?", stripped, re.IGNORECASE):
        return True
    return False


def is_exact_choice_reply(text: str, selected: str | None) -> bool:
    """
    Execute is exact choice reply.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - text: input consumed by this function while processing the current request.
    - selected: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    if selected is None:
        return False

    stripped = text.strip()
    if not stripped:
        return True

    if _normalize(stripped) == _normalize(selected):
        return True

    digits = re.findall(r"\d+", stripped)
    if digits and re.findall(r"\d+", selected) == digits:
        return True

    return False


def _match_choice(text: str, options: Iterable[str]) -> str | None:
    """
    Execute match choice.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - text: input consumed by this function while processing the current request.
    - options: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    stripped = text.strip()
    opts = list(options)
    if stripped.isdigit():
        idx = int(stripped) - 1
        if 0 <= idx < len(opts):
            return opts[idx]

    if _is_skip_text(stripped):
        for opt in opts:
            if _is_skip_option(opt):
                return opt

    normalized = _normalize(stripped)
    for opt in opts:
        if normalized == _normalize(opt):
            return opt

    digits = re.findall(r"\d+", stripped)
    if digits:
        for opt in opts:
            if re.findall(r"\d+", opt) == digits:
                return opt

    return None


def _normalize(value: str) -> str:
    """
    Execute normalize.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - value: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    return re.sub(r"\s+", " ", value.strip().lower())


def _apply_choice_value(state: State, field: str, selected: str, item_index: int | None) -> None:
    """
    Execute apply choice value.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - state: input consumed by this function while processing the current request.
    - field: input consumed by this function while processing the current request.
    - selected: input consumed by this function while processing the current request.
    - item_index: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    if _is_skip_option(selected):
        return

    if field in {"size_cm", "variant", "modifiers"}:
        if not state.entities.items:
            return
        idx = item_index if item_index is not None else len(state.entities.items) - 1
        idx = max(0, min(idx, len(state.entities.items) - 1))
        item = state.entities.items[idx]
        if field == "size_cm":
            digits = re.findall(r"\d+", selected)
            item.size_cm = int(digits[0]) if digits else item.size_cm
        elif field == "variant":
            item.variant = selected
        else:
            item.modifiers.append(selected)
        return

    if hasattr(state.entities, field):
        if field == "delivery_type":
            normalized = _normalize(selected)
            if normalized in {"доставка", "delivery"}:
                setattr(state.entities, field, "delivery")
            elif normalized in {"самовывоз", "pickup"}:
                setattr(state.entities, field, "pickup")
            else:
                setattr(state.entities, field, selected)
            return
        setattr(state.entities, field, selected)


def _is_skip_text(value: str) -> bool:
    """
    Execute is skip text.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - value: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    normalized = _normalize(value)
    return normalized in {
        "нет",
        "не надо",
        "не нужно",
        "без",
        "пропустить",
        "никакие",
        "никаких",
    }


def _is_skip_option(value: str) -> bool:
    """
    Execute is skip option.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - value: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    normalized = _normalize(value)
    return normalized in {
        "не добавлять",
        "без добавок",
        "без топпингов",
        "без модификаторов",
        "нет",
        "не нужно",
        "не надо",
        "пропустить",
    }


def _is_same_items(base_items: list[Item], incoming_items: list[Item]) -> bool:
    """
    Execute is same items.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - base_items: input consumed by this function while processing the current request.
    - incoming_items: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    return [_item_signature(item) for item in base_items] == [_item_signature(item) for item in incoming_items]


def _looks_like_full_state_echo(base_items: list[Item], incoming_items: list[Item]) -> bool:
    """
    Execute looks like full state echo.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - base_items: input consumed by this function while processing the current request.
    - incoming_items: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    if not base_items or len(incoming_items) < len(base_items):
        return False
    base_signatures = [_item_signature(item) for item in base_items]
    incoming_prefix = [_item_signature(item) for item in incoming_items[: len(base_items)]]
    return base_signatures == incoming_prefix


def _only_repeats_existing_items(base_items: list[Item], incoming_items: list[Item]) -> bool:
    """
    Execute only repeats existing items.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - base_items: input consumed by this function while processing the current request.
    - incoming_items: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    if not base_items or not incoming_items:
        return False
    base_counter = Counter(_item_signature(item) for item in base_items)
    incoming_counter = Counter(_item_signature(item) for item in incoming_items)
    return set(incoming_counter).issubset(set(base_counter))


def _item_signature(item: Item) -> tuple[str, int, int | None, str | None, tuple[str, ...]]:
    """
    Execute item signature.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - item: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    return (
        _normalize(item.name),
        item.qty,
        item.size_cm,
        _normalize(item.variant or "") if item.variant else None,
        tuple(_normalize(value) for value in item.modifiers),
    )
