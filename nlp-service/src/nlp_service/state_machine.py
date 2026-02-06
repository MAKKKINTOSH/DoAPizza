import re
from typing import Iterable

from .schemas import Entities, State


def apply_pending_choice(state: State, text: str) -> tuple[State, bool, str | None]:
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
    merged = base.model_copy(deep=True)

    if incoming.items:
        merged.items.extend(incoming.items)

    for field in ["delivery_type", "address", "time", "phone", "comment"]:
        value = getattr(incoming, field)
        if value is not None and value != "":
            setattr(merged, field, value)

    return merged


def is_choice_only(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if re.fullmatch(r"\d+", stripped):
        return True
    if re.fullmatch(r"\d+\s*(cm|sm|cm\.)?", stripped, re.IGNORECASE):
        return True
    if re.fullmatch(r"\d+\s*(см)?", stripped, re.IGNORECASE):
        return True
    return False


def _match_choice(text: str, options: Iterable[str]) -> str | None:
    stripped = text.strip()
    if stripped.isdigit():
        idx = int(stripped) - 1
        opts = list(options)
        if 0 <= idx < len(opts):
            return opts[idx]

    normalized = _normalize(stripped)
    for opt in options:
        if normalized == _normalize(opt):
            return opt

    digits = re.findall(r"\d+", stripped)
    if digits:
        for opt in options:
            if re.findall(r"\d+", opt) == digits:
                return opt

    return None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _apply_choice_value(state: State, field: str, selected: str, item_index: int | None) -> None:
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
        setattr(state.entities, field, selected)
