"""Low-level state transition helpers shared by parser pipeline."""

import re
from collections import Counter
from typing import Iterable

from .schemas import Entities, Item, State


def apply_pending_choice(state: State, text: str) -> tuple[State, bool, str | None]:
    """Apply explicit choice answer (size/variant/etc.) to current state."""
    # If there is no open question, caller should continue with normal parsing path.
    if not state.pending_choice:
        return state, False, None

    # Try to map user text to one of the predefined options.
    selected = _match_choice(text, state.pending_choice.options)
    if selected is None:
        return state, False, None

    # Work on deep copy to keep state updates explicit and side-effect-safe.
    updated = state.model_copy(deep=True)
    _apply_choice_value(updated, state.pending_choice.field, selected, state.pending_choice.item_index)
    # Choice is resolved, so clear pending question and missing marker for that field.
    updated.pending_choice = None
    updated.missing = [m for m in updated.missing if m != state.pending_choice.field]
    return updated, True, selected


def merge_entities(base: Entities, incoming: Entities) -> Entities:
    """Merge incremental entities into base state while avoiding obvious duplicates."""
    merged = base.model_copy(deep=True)

    if incoming.items:
        # 1) Same list already present -> ignore to avoid duplicates.
        if _is_same_items(base.items, incoming.items):
            pass
        # 2) Some providers echo full prior state + new tail -> trust incoming snapshot.
        elif _looks_like_full_state_echo(base.items, incoming.items):
            merged.items = [item.model_copy(deep=True) for item in incoming.items]
        # 3) Incoming contains only already known items -> keep current list unchanged.
        elif _only_repeats_existing_items(base.items, incoming.items):
            pass
        # 4) Default additive behavior: append new items.
        else:
            merged.items.extend(incoming.items)

    # Scalar fields are merged as "latest non-empty value wins".
    for field in ["delivery_type", "address", "time", "phone", "comment"]:
        value = getattr(incoming, field)
        if value is not None and value != "":
            setattr(merged, field, value)

    return merged


def is_choice_only(text: str) -> bool:
    """Heuristic: message likely answers a pending choice and nothing else."""
    stripped = text.strip()
    # Empty reply is treated as "choice-like" so caller can keep asking.
    if not stripped:
        return True
    # Skip words also represent valid choice answers in optional questions.
    if _is_skip_text(stripped):
        return True
    # Pure number often means "option index".
    if re.fullmatch(r"\d+", stripped):
        return True
    # And number with size suffix means direct size choice.
    if re.fullmatch(r"\d+\s*(cm|sm|cm\.)?", stripped, re.IGNORECASE):
        return True
    if re.fullmatch(r"\d+\s*(см)?", stripped, re.IGNORECASE):
        return True
    return False


def is_exact_choice_reply(text: str, selected: str | None) -> bool:
    """Check whether raw user text matches chosen option semantically."""
    if selected is None:
        return False

    stripped = text.strip()
    # If user replied with blank but parser still selected option, treat as exact.
    if not stripped:
        return True

    # Compare normalized text first (case/space-insensitive).
    if _normalize(stripped) == _normalize(selected):
        return True

    # Fallback: compare only numeric core (e.g. "30", "30 см").
    digits = re.findall(r"\d+", stripped)
    if digits and re.findall(r"\d+", selected) == digits:
        return True

    return False


def _match_choice(text: str, options: Iterable[str]) -> str | None:
    stripped = text.strip()
    opts = list(options)
    # Numeric shortcut: "1", "2", ... maps to option index.
    if stripped.isdigit():
        idx = int(stripped) - 1
        if 0 <= idx < len(opts):
            return opts[idx]

    # Skip answer should map to explicit skip option if provided by caller.
    if _is_skip_text(stripped):
        for opt in opts:
            if _is_skip_option(opt):
                return opt

    # Exact text match after normalization.
    normalized = _normalize(stripped)
    for opt in opts:
        if normalized == _normalize(opt):
            return opt

    # Last chance: match by number inside option (size cases).
    digits = re.findall(r"\d+", stripped)
    if digits:
        for opt in opts:
            if re.findall(r"\d+", opt) == digits:
                return opt

    return None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _apply_choice_value(state: State, field: str, selected: str, item_index: int | None) -> None:
    """Mutate target field/item in state according to selected choice option."""
    # Skip option intentionally leaves state unchanged.
    if _is_skip_option(selected):
        return

    # Item-scoped fields require at least one item in order.
    if field in {"size_cm", "variant", "modifiers"}:
        if not state.entities.items:
            return
        # If item index is missing/out of range, clamp to existing bounds.
        idx = item_index if item_index is not None else len(state.entities.items) - 1
        idx = max(0, min(idx, len(state.entities.items) - 1))
        item = state.entities.items[idx]
        if field == "size_cm":
            # Size options may include units; extract numeric part only.
            digits = re.findall(r"\d+", selected)
            item.size_cm = int(digits[0]) if digits else item.size_cm
        elif field == "variant":
            item.variant = selected
        else:
            # Modifiers are additive by design for dialogue UX.
            item.modifiers.append(selected)
        return

    # Scalar choice field maps directly to entities attribute.
    if hasattr(state.entities, field):
        if field == "delivery_type":
            # Normalize delivery aliases to stable internal values.
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
    return [_item_signature(item) for item in base_items] == [_item_signature(item) for item in incoming_items]


def _looks_like_full_state_echo(base_items: list[Item], incoming_items: list[Item]) -> bool:
    if not base_items or len(incoming_items) < len(base_items):
        return False
    # Compare only prefix of incoming: many models emit base state first.
    base_signatures = [_item_signature(item) for item in base_items]
    incoming_prefix = [_item_signature(item) for item in incoming_items[: len(base_items)]]
    return base_signatures == incoming_prefix


def _only_repeats_existing_items(base_items: list[Item], incoming_items: list[Item]) -> bool:
    if not base_items or not incoming_items:
        return False
    # Counter-based inclusion checks that incoming doesn't introduce new signatures.
    base_counter = Counter(_item_signature(item) for item in base_items)
    incoming_counter = Counter(_item_signature(item) for item in incoming_items)
    return set(incoming_counter).issubset(set(base_counter))


def _item_signature(item: Item) -> tuple[str, int, int | None, str | None, tuple[str, ...]]:
    return (
        _normalize(item.name),
        item.qty,
        item.size_cm,
        _normalize(item.variant or "") if item.variant else None,
        tuple(_normalize(value) for value in item.modifiers),
    )
