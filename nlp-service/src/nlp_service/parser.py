"""Core NLP parsing pipeline.

This module combines deterministic heuristics with an LLM call:
1) quickly handle explicit choice/scalar replies without model call;
2) classify user intent and constrain allowed mutations;
3) run LLM extraction when needed;
4) normalize/guard results and enforce required checkout flow.
"""

from __future__ import annotations

import os
import re
from typing import Literal

import httpx

from .catalog_runtime import catalog_runtime
from .llm import LLMClient, LLMError
from .schemas import Choice, EditOperation, Entities, Item, ParseResponse, State, TimeInfo
from .state_machine import apply_pending_choice, is_choice_only, is_exact_choice_reply, merge_entities

LLM_CLIENT = LLMClient()


def parse_text(text: str, state: State | None) -> ParseResponse:
    """Convert free-form message + previous state into next structured parse response."""
    # Always isolate mutable working copy from caller state.
    current_state = state.model_copy(deep=True) if state else State()

    message = ""
    confidence = 0.0

    # Fast path: pending choice answer can often be applied without LLM.
    choice_applied = False
    selected_choice: str | None = None
    if current_state.pending_choice:
        # Reuse shared matcher for buttons/"25 см"/"не нужно" style replies.
        current_state, choice_applied, selected_choice = apply_pending_choice(current_state, text)
        if choice_applied:
            message = "Принял выбор."

    # Heuristic stage: for some expected fields we trust local parsing first.
    call_llm = True
    intent: IntentKind = _classify_request_intent(text, current_state)
    if choice_applied and (is_choice_only(text) or is_exact_choice_reply(text, selected_choice)):
        call_llm = False
        intent = "choice_reply"

    size_choice_handled, size_message = _apply_expected_size_choice_input(current_state, text)
    if size_choice_handled:
        # Unsupported numeric size (e.g. 27 см) is handled locally by nearest options.
        call_llm = False
        intent = "choice_reply"
        message = size_message or message

    scalar_applied, scalar_message = _apply_expected_scalar_input(current_state, text)
    if scalar_applied:
        # Address/phone/time replies can be accepted without model latency.
        call_llm = False
        intent = "checkout_scalar"
        message = scalar_message or message

    # If user edits ambiguous duplicate positions, ask clarification before LLM.
    if call_llm:
        ambiguous_prompt = _build_ambiguous_item_prompt(text, current_state, intent)
        if ambiguous_prompt is not None:
            return _build_ask_response(current_state, ambiguous_prompt, confidence)

    # LLM stage with local post-processing to keep state transitions safe.
    if call_llm:
        # Catalog alignment reduces random renames ("пеперони" -> "Пепперони").
        llm_result = LLM_CLIENT.extract(text, current_state)
        llm_result = _align_result_with_catalog(text, llm_result, intent)
        llm_result = _align_edit_operations_with_state(text, current_state, llm_result)
        llm_result = _strip_implicit_size_from_additions(text, current_state, llm_result, intent)
        filtered_operations = _filter_edit_operations_for_text(current_state, llm_result.edit_operations, text, intent)
        fallback_operations = _infer_item_update_operations(current_state, llm_result.entities, text, intent)
        # For "add item" intent, reject destructive mutations and only accept additions.
        if intent == "add_item":
            updated_entities, applied_additions, had_unsafe_mutation = _apply_safe_add_intent_entities(
                current_state.entities,
                llm_result,
                text,
            )
            if applied_additions == 0:
                clarification = (
                    "Не понял, какую пиццу добавить. "
                    "Уточните название пиццы и, если нужно, размер."
                )
                if had_unsafe_mutation:
                    clarification = "Для добавления новой позиции напишите только, что добавить: название, количество и размер."
                return _build_ask_response(current_state, clarification, llm_result.confidence or confidence)
            current_state.entities = _merge_scalar_fields(updated_entities, llm_result.entities)
            current_state.pending_choice = None
            current_state.missing = []
        elif filtered_operations:
            current_state.entities = _apply_edit_operations(current_state.entities, filtered_operations)
            current_state.entities = _merge_scalar_fields(current_state.entities, llm_result.entities)
        elif fallback_operations:
            current_state.entities = _apply_edit_operations(current_state.entities, fallback_operations)
            current_state.entities = _merge_scalar_fields(current_state.entities, llm_result.entities)
        elif llm_result.state_update_mode == "replace" and _looks_like_explicit_edit(text):
            # Replace mode is allowed only for explicit edit language.
            current_state.entities = llm_result.entities.model_copy(deep=True)
        else:
            # Default merge path keeps existing order stable and adds extracted deltas.
            sanitized_entities = _sanitize_incoming_entities(current_state, llm_result.entities, text)
            current_state.entities = merge_entities(current_state.entities, sanitized_entities)
            current_state.missing = list(llm_result.missing or [])
            current_state.pending_choice = llm_result.choices
        if intent != "add_item":
            current_state.missing = list(llm_result.missing or [])
            current_state.pending_choice = llm_result.choices
        message = llm_result.message or message
        confidence = llm_result.confidence or confidence

    # Consolidate same-config line items after any mutation path.
    current_state.entities.items = _consolidate_line_items(current_state.entities.items)

    _maybe_call_delivery_api(current_state.entities)

    # Normalize missing/choices according to strict checkout flow contract.
    current_state = _enforce_required_order_flow(current_state)

    choices = current_state.pending_choice
    missing = current_state.missing
    # Contract: if choice exists, its field must also be present in missing list.
    if choices and choices.field not in missing:
        missing = missing + [choices.field]

    action = "ASK" if (missing or choices) else "READY"

    if action == "ASK" and _should_replace_ask_message(message, current_state):
        message = _build_followup_message(current_state)
    elif not message:
        message = "Заказ готов."

    current_state.missing = missing

    return ParseResponse(
        action=action,
        message=message,
        entities=current_state.entities,
        missing=current_state.missing,
        choices=choices,
        state=current_state,
        confidence=confidence,
    )


def _maybe_call_delivery_api(entities: Entities) -> None:
    """Optional side-effect hook for external delivery verification API."""
    base_url = os.getenv("DELIVERY_API_BASE_URL", "").strip()
    if not base_url:
        return

    # Fire-and-forget hook: parser result must not depend on external API availability.
    url = base_url.rstrip("/") + "/v1/nlp/verify"
    payload = entities.model_dump()
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(url, json=payload)
    except httpx.RequestError:
        # Swallow network errors intentionally to keep parser deterministic.
        return


def _build_ask_response(state: State, message: str, confidence: float) -> ParseResponse:
    """Return ASK response with deep-copied state snapshot."""
    snapshot = state.model_copy(deep=True)
    return ParseResponse(
        action="ASK",
        message=message,
        entities=snapshot.entities,
        missing=snapshot.missing,
        choices=snapshot.pending_choice,
        state=snapshot,
        confidence=confidence,
    )


def _classify_request_intent(text: str, state: State) -> IntentKind:
    """Classify high-level user intent to constrain following mutation strategy."""
    if state.pending_choice is not None and is_choice_only(text):
        # While waiting for a choice, short replies are treated as choice first.
        return "choice_reply"

    expected_scalar = _expected_scalar_field(state)
    if expected_scalar == "address" and _looks_like_address(text):
        return "checkout_scalar"
    if expected_scalar == "phone" and _looks_like_phone(text):
        return "checkout_scalar"
    if expected_scalar == "time" and _looks_like_time(text):
        return "checkout_scalar"

    if _looks_like_remove_or_replace_request(text):
        return "remove_or_replace"
    if _looks_like_existing_item_update_request(text):
        return "edit_existing"
    if _looks_like_add_item_request(text) or _looks_like_bare_catalog_add_request(text, state):
        return "add_item"
    # Unknown intent still goes through LLM but with stricter guard logic later.
    return "unknown"


def _looks_like_remove_or_replace_request(text: str) -> bool:
    normalized = _normalize_text(text)
    mentioned_catalog = _extract_catalog_pizzas_from_text(text)
    if "замени" in normalized or "вместо" in normalized:
        return True
    if (
        ("удали" in normalized or "убери" in normalized)
        and mentioned_catalog
        and " из " not in normalized
    ):
        return True
    if ("удали" in normalized or "убери" in normalized) and any(
        marker in normalized for marker in ("пицц", "позиц", "перв", "втор", "треть", "четвер", "#")
    ):
        return True
    return False


def _looks_like_bare_catalog_add_request(text: str, state: State) -> bool:
    if not state.entities.items:
        return False
    if _looks_like_remove_or_replace_request(text):
        return False
    if _looks_like_existing_item_update_request(text):
        return False
    if is_choice_only(text):
        return False
    return bool(_extract_catalog_pizzas_from_text(text))


def _build_ambiguous_item_prompt(text: str, state: State, intent: IntentKind) -> str | None:
    if intent not in {"edit_existing", "remove_or_replace"}:
        return None
    if len(state.entities.items) < 2:
        return None

    explicit_index = _extract_explicit_item_index(text, len(state.entities.items))
    if explicit_index is not None:
        return None

    mentioned = _extract_catalog_pizzas_from_text(text)
    if len(mentioned) == 1:
        target_name = mentioned[0]
        # Build candidate indexes for duplicate pizza names in current order.
        duplicate_indexes = [
            index
            for index, item in enumerate(state.entities.items)
            if _normalize_name_for_catalog(item.name) == _normalize_name_for_catalog(target_name)
        ]
        if len(duplicate_indexes) <= 1:
            return None
        readable_indexes = ", ".join(str(index + 1) for index in duplicate_indexes)
        return (
            f"Уточните номер позиции для '{target_name}': {readable_indexes}. "
            "Например: «измени 2-ю пиццу»."
        )

    if not mentioned:
        return "Уточните номер позиции (1, 2, ...), которую нужно изменить."
    return None


def _extract_explicit_item_index(text: str, items_count: int) -> int | None:
    normalized = _normalize_text(text)

    # Support "#2" style explicit references from power users.
    hash_match = re.search(r"#\s*(\d+)", normalized)
    if hash_match:
        index = int(hash_match.group(1)) - 1
        if 0 <= index < items_count:
            return index

    # Support natural-language ordinals: "первую", "вторую", etc.
    ordinal_words = (
        (r"\bперв\w*\b", 0),
        (r"\bвтор\w*\b", 1),
        (r"\bтреть\w*\b", 2),
        (r"\bчетвер\w*\b", 3),
        (r"\bпят\w*\b", 4),
    )
    for pattern, index in ordinal_words:
        if re.search(pattern, normalized) and 0 <= index < items_count:
            return index

    # Support "2-я пицца"/"2 позицию" forms.
    numeric_match = re.search(r"\b(\d+)\s*[-]?(?:я|й|ю|ая|ую)?\s*(?:пицц\w*|позиц\w*)", normalized)
    if numeric_match:
        index = int(numeric_match.group(1)) - 1
        if 0 <= index < items_count:
            return index

    return None


def _apply_safe_add_intent_entities(base: Entities, llm_result, text: str) -> tuple[Entities, int, bool]:
    """Extract additive delta for add-intent without allowing destructive side effects."""
    unsafe = any(operation.op != "add_item" for operation in llm_result.edit_operations)

    additions = _extract_multisize_additions(text)
    if additions:
        # Multisize syntax ("размеры 25,30,35") may intentionally add multiple lines.
        additions = _normalize_addition_items_for_text(additions, text, allow_large_qty=True)
    else:
        # Prefer explicit add_item operations emitted by LLM.
        op_additions = [operation.item.model_copy(deep=True) for operation in llm_result.edit_operations if operation.op == "add_item" and operation.item is not None]
        if op_additions:
            additions = _normalize_addition_items_for_text(op_additions, text, allow_large_qty=False)
        else:
            # Fallback: infer pure additive delta by comparing entities snapshots.
            entity_additions, entity_unsafe = _extract_entity_additions(base.items, llm_result.entities.items)
            unsafe = unsafe or entity_unsafe
            additions = _normalize_addition_items_for_text(entity_additions, text, allow_large_qty=False)

    if not additions:
        return base.model_copy(deep=True), 0, unsafe

    mentioned = _extract_catalog_pizzas_from_text(text)
    if len(mentioned) == 1:
        # If user named exactly one catalog pizza, enforce that name on all additions.
        for addition in additions:
            addition.name = mentioned[0]

    updated = base.model_copy(deep=True)
    total_added_qty = 0
    for addition in additions:
        # Aggregate for confidence checks in caller and diagnostics.
        total_added_qty += max(addition.qty, 1)
        _apply_addition(updated.items, addition)
    return updated, total_added_qty, unsafe


def _extract_multisize_additions(text: str) -> list[Item]:
    mentioned = _extract_catalog_pizzas_from_text(text)
    if len(mentioned) != 1:
        return []

    normalized = _normalize_text(text)
    marker_match = re.search(r"(?:размер(?:ы)?|:)\s*([0-9,\s;/и]+)", normalized)
    if marker_match is None:
        return []

    # Need at least two sizes to treat as explicit "multi-size expansion".
    sizes = [int(value) for value in re.findall(r"\d{2,3}", marker_match.group(1))]
    if len(sizes) < 2:
        return []

    return [Item(name=mentioned[0], qty=1, size_cm=size) for size in sizes]


def _extract_entity_additions(base_items: list[Item], incoming_items: list[Item]) -> tuple[list[Item], bool]:
    base_qty, _ = _build_config_qty_map(base_items)
    incoming_qty, incoming_samples = _build_config_qty_map(incoming_items)

    unsafe = False
    additions: list[Item] = []
    for key, qty in incoming_qty.items():
        # Positive delta means genuinely added quantity for given item configuration.
        delta = qty - base_qty.get(key, 0)
        if delta <= 0:
            continue
        sample = incoming_samples[key].model_copy(deep=True)
        sample.qty = delta
        additions.append(sample)

    for key, qty in base_qty.items():
        # Any reduction indicates destructive mutation, unsafe for add-intent.
        if incoming_qty.get(key, 0) < qty:
            unsafe = True
            break

    return additions, unsafe


def _build_config_qty_map(items: list[Item]) -> tuple[dict[tuple[str, int | None, str | None, tuple[str, ...]], int], dict[tuple[str, int | None, str | None, tuple[str, ...]], Item]]:
    qty_map: dict[tuple[str, int | None, str | None, tuple[str, ...]], int] = {}
    sample_map: dict[tuple[str, int | None, str | None, tuple[str, ...]], Item] = {}
    for item in items:
        # Key includes size/variant/modifiers, so quantities merge only identical configs.
        key = _item_config_key(item)
        qty_map[key] = qty_map.get(key, 0) + max(item.qty, 1)
        # Keep first sample for reconstructing delta item later.
        sample_map.setdefault(key, item)
    return qty_map, sample_map


def _item_config_key(item: Item) -> tuple[str, int | None, str | None, tuple[str, ...]]:
    normalized_variant = _normalize_text(item.variant) if item.variant else None
    normalized_modifiers = tuple(sorted(_normalize_text(value) for value in item.modifiers))
    return (_normalize_name_for_catalog(item.name), item.size_cm, normalized_variant, normalized_modifiers)


def _normalize_addition_items_for_text(items: list[Item], text: str, allow_large_qty: bool) -> list[Item]:
    normalized: list[Item] = []
    has_explicit_qty = _has_explicit_item_quantity(text)
    for item in items:
        updated = item.model_copy(deep=True)
        updated.qty = max(updated.qty, 1)
        # Without explicit quantity language cap inferred qty to 1 to avoid inflation.
        if updated.qty > 1 and not allow_large_qty and not has_explicit_qty:
            updated.qty = 1
        normalized.append(updated)
    return normalized


def _apply_addition(items: list[Item], addition: Item) -> None:
    if addition.size_cm is not None:
        key = _item_config_key(addition)
        for existing in items:
            # Sized pizzas with same config are merged by quantity.
            if _item_config_key(existing) == key and existing.size_cm is not None:
                existing.qty = max(existing.qty, 1) + max(addition.qty, 1)
                return
    # Unsized or unmatched items are appended as separate order lines.
    items.append(addition.model_copy(deep=True))


def _consolidate_line_items(items: list[Item]) -> list[Item]:
    consolidated: list[Item] = []
    index_by_key: dict[tuple[str, int | None, str | None, tuple[str, ...]], int] = {}
    for item in items:
        candidate = item.model_copy(deep=True)
        candidate.qty = max(candidate.qty, 1)
        # Keep unsized items as-is: size question may still split them later.
        if candidate.size_cm is None:
            consolidated.append(candidate)
            continue

        key = _item_config_key(candidate)
        if key in index_by_key:
            # Existing same-config line found: sum quantities.
            existing = consolidated[index_by_key[key]]
            existing.qty = max(existing.qty, 1) + candidate.qty
            continue

        # First occurrence of this config, remember its position.
        index_by_key[key] = len(consolidated)
        consolidated.append(candidate)

    return consolidated


__all__ = ["parse_text", "LLMError"]


DELIVERY_TYPE_OPTIONS = ["Доставка", "Самовывоз"]
IntentKind = Literal["add_item", "edit_existing", "remove_or_replace", "choice_reply", "checkout_scalar", "unknown"]


def _allowed_size_cm() -> list[int]:
    snapshot = catalog_runtime.get_snapshot()
    if snapshot.sizes_cm:
        return list(snapshot.sizes_cm)
    return [25, 30, 35]


def _size_options() -> list[str]:
    return [f"{value} см" for value in _allowed_size_cm()]


def _enforce_required_order_flow(state: State) -> State:
    """Ensure state always asks next required field in canonical order."""
    updated = state.model_copy(deep=True)
    # Normalize incomplete choices before any checks.
    updated.pending_choice = _normalize_pending_choice(updated.pending_choice)

    # Without items we always restart from "what pizza?".
    if not updated.entities.items:
        updated.pending_choice = None
        updated.missing = ["items"]
        return updated

    # If model produced unsupported size, replace it with nearest valid options.
    invalid_size_choice = _build_invalid_size_choice(updated)
    if invalid_size_choice is not None:
        updated.pending_choice = invalid_size_choice
        updated.missing = _ensure_field_in_missing(updated.missing, invalid_size_choice.field)
        return updated

    # Existing pending choice has highest priority over all other missing fields.
    if updated.pending_choice:
        updated.missing = _ensure_field_in_missing(updated.missing, updated.pending_choice.field)
        return updated

    for index, item in enumerate(updated.entities.items):
        # Force explicit size for every item before moving to checkout scalars.
        if item.size_cm is None:
            updated.pending_choice = Choice(field="size_cm", options=_size_options(), item_index=index)
            updated.missing = _ensure_field_in_missing(updated.missing, "size_cm")
            return updated

    # Then request delivery method.
    if not updated.entities.delivery_type:
        updated.pending_choice = Choice(field="delivery_type", options=DELIVERY_TYPE_OPTIONS, item_index=None)
        updated.missing = _ensure_field_in_missing(updated.missing, "delivery_type")
        return updated

    updated.missing = [field for field in updated.missing if field != "delivery_type"]

    # Address is required only for delivery (not pickup).
    if _requires_address(updated.entities.delivery_type) and not updated.entities.address:
        updated.missing = _ensure_field_in_missing(updated.missing, "address")
        return updated
    updated.missing = [field for field in updated.missing if field != "address"]

    # Finish with phone and requested time.
    if not updated.entities.phone:
        updated.missing = _ensure_field_in_missing(updated.missing, "phone")
        return updated
    updated.missing = [field for field in updated.missing if field != "phone"]

    if updated.entities.time is None:
        updated.missing = _ensure_field_in_missing(updated.missing, "time")
        return updated
    updated.missing = [field for field in updated.missing if field != "time"]

    updated.missing = []
    return updated


def _normalize_pending_choice(choice: Choice | None) -> Choice | None:
    if choice is None:
        return None

    normalized = choice.model_copy(deep=True)
    # Backfill options when model set only field name.
    if normalized.field == "size_cm" and not normalized.options:
        normalized.options = _size_options()
    if normalized.field == "delivery_type" and not normalized.options:
        normalized.options = list(DELIVERY_TYPE_OPTIONS)
    return normalized


def _ensure_field_in_missing(missing: list[str], field: str) -> list[str]:
    # Keep requested field at the front and unique.
    without_field = [value for value in missing if value != field]
    return [field, *without_field]


def _requires_address(delivery_type: str | None) -> bool:
    if delivery_type is None:
        return False
    normalized = delivery_type.strip().lower()
    return normalized in {"delivery", "доставка"}


def _build_followup_message(state: State) -> str:
    # Human-facing fallback prompts when model message is too generic/technical.
    if not state.entities.items:
        return "Какую пиццу хотите заказать?"

    if state.pending_choice:
        return _choice_message(state)

    if not state.missing:
        return "Нужна дополнительная информация."

    field = state.missing[0]
    item = state.entities.items[-1]
    if field == "address":
        return "Куда доставить заказ? Напишите адрес полностью."
    if field == "phone":
        return "Укажите номер телефона для связи."
    if field == "time":
        return "Когда вам удобно получить заказ? Например: 'как можно скорее', 'к 19:30' или 'через 40 минут'."
    if field == "size_cm":
        return f"Какой размер для пиццы '{item.name}'?"
    if field == "delivery_type":
        return "Как получить заказ: доставка или самовывоз?"
    return "Нужна дополнительная информация по заказу."


def _should_replace_ask_message(message: str, state: State) -> bool:
    normalized = " ".join(message.strip().lower().split())
    if not normalized:
        return True

    if state.pending_choice and state.pending_choice.requested_value is not None:
        # For invalid-size retry we always prefer deterministic local prompt.
        return True

    generic_messages = {
        "готово",
        "готово.",
        "заказ готов",
        "заказ готов.",
        "принял выбор",
        "принял выбор.",
        "нужна дополнительная информация.",
        "нужна дополнительная информация",
    }
    if normalized in generic_messages:
        return True

    technical_markers = {"size_cm", "delivery_type", "modifiers", "variant", "items"}
    if any(marker in normalized for marker in technical_markers):
        return True

    return False


def _choice_message(state: State) -> str:
    assert state.pending_choice is not None
    choice = state.pending_choice
    item = None
    if choice.item_index is not None and 0 <= choice.item_index < len(state.entities.items):
        item = state.entities.items[choice.item_index]

    if choice.field == "size_cm":
        if choice.requested_value is not None:
            # requested_value appears when user asked unsupported size.
            recommended = choice.options[-1] if choice.options else None
            options = " или ".join(choice.options)
            if recommended:
                return (
                    f"{choice.requested_value} не делаем. Могу предложить {options}. "
                    f"Советую {recommended}."
                )
        if item and choice.item_index is not None:
            return f"Какой размер выбрать для позиции {choice.item_index + 1} ('{item.name}')?"
        name = item.name if item else "этой пиццы"
        return f"Какой размер выбрать для '{name}'?"
    if choice.field == "delivery_type":
        return "Как получить заказ?"
    if choice.field == "variant":
        if item and choice.item_index is not None:
            return f"Какой вариант выбрать для позиции {choice.item_index + 1} ('{item.name}')?"
        name = item.name if item else "пиццы"
        return f"Какой вариант выбрать для '{name}'?"
    if choice.field == "modifiers":
        if item and choice.item_index is not None:
            return f"Нужны ли добавки для позиции {choice.item_index + 1} ('{item.name}')?"
        name = item.name if item else "пиццы"
        return f"Нужны ли добавки для '{name}'?"
    if choice.options:
        return "Выберите вариант: " + ", ".join(choice.options)
    return "Выберите подходящий вариант."


def _build_invalid_size_choice(state: State) -> Choice | None:
    allowed_sizes = _allowed_size_cm()
    for index, item in enumerate(state.entities.items):
        # Keep valid/missing sizes unchanged.
        if item.size_cm is None or item.size_cm in allowed_sizes:
            continue

        # Convert invalid concrete size into explicit follow-up choice.
        invalid_size = item.size_cm
        item.size_cm = None
        nearest = _nearest_size_options(invalid_size)
        return Choice(
            field="size_cm",
            options=[f"{value} см" for value in nearest],
            item_index=index,
            requested_value=f"{invalid_size} см",
        )
    return None


def _nearest_size_options(value: int) -> list[int]:
    # Rank by distance, then prefer larger option on equal distance.
    ranked = sorted(_allowed_size_cm(), key=lambda option: (abs(option - value), -option))
    first = ranked[0]
    second = ranked[1] if len(ranked) > 1 else ranked[0]
    pair = sorted({first, second})
    return pair


def _sanitize_incoming_entities(current_state: State, incoming: Entities, text: str) -> Entities:
    """Drop accidental item mutations when user likely answered scalar checkout field."""
    sanitized = incoming.model_copy(deep=True)
    if not incoming.items:
        return sanitized

    _normalize_addition_item_qty(sanitized, text)

    expected_field = _expected_scalar_field(current_state)
    # When user answers scalar question, drop accidental item mutations from model.
    if expected_field == "address" and incoming.address and _looks_like_address(text):
        sanitized.items = []
    elif expected_field == "phone" and incoming.phone and _looks_like_phone(text):
        sanitized.items = []
    elif expected_field == "time" and incoming.time and _looks_like_time(text):
        sanitized.items = []
    return sanitized


def _apply_edit_operations(entities: Entities, operations: list[EditOperation]) -> Entities:
    """Apply item-level operations emitted by LLM to current entities."""
    updated = entities.model_copy(deep=True)
    for operation in operations:
        # add_item does not require existing index.
        if operation.op == "add_item":
            if operation.item is not None:
                updated.items.append(operation.item.model_copy(deep=True))
            continue

        # Ignore malformed indexes to keep parser resilient.
        if operation.item_index is None or not (0 <= operation.item_index < len(updated.items)):
            continue

        # Other operations target an existing item by index.
        if operation.op == "remove_item":
            updated.items.pop(operation.item_index)
            continue

        if operation.op == "replace_item":
            if operation.item is not None:
                updated.items[operation.item_index] = operation.item.model_copy(deep=True)
            continue

        if operation.op == "update_item":
            _apply_item_update(updated.items[operation.item_index], operation)

    return updated


def _align_result_with_catalog(text: str, llm_result, intent: IntentKind) -> object:
    mentioned = _extract_catalog_pizzas_from_text(text)
    if not mentioned:
        return llm_result

    aligned = llm_result.model_copy(deep=True)
    if intent == "add_item":
        # For add-intent, single explicit catalog mention is authoritative.
        if len(mentioned) == 1 and len(aligned.entities.items) == 1:
            aligned.entities.items[0].name = mentioned[0]
        for operation in aligned.edit_operations:
            if operation.op == "add_item" and operation.item is not None and len(mentioned) == 1:
                operation.item.name = mentioned[0]
    elif len(mentioned) == 1 and _looks_like_direct_order_request(text) and len(aligned.entities.items) == 1:
        aligned.entities.items[0].name = mentioned[0]
    return aligned


def _align_edit_operations_with_state(text: str, state: State, llm_result) -> object:
    if not llm_result.edit_operations or not state.entities.items:
        return llm_result

    target_index = _extract_explicit_item_index(text, len(state.entities.items))
    if target_index is None:
        # If no explicit index, try to resolve by mentioned pizza name.
        mentioned = _extract_catalog_pizzas_from_text(text)
        if len(mentioned) != 1:
            return llm_result
        target_index = _find_matching_existing_item_index(state.entities.items, mentioned[0])
        if target_index is None:
            return llm_result

    aligned = llm_result.model_copy(deep=True)
    for operation in aligned.edit_operations:
        # Only item-mutating operations need target index rewrite.
        if operation.op not in {"update_item", "replace_item", "remove_item"}:
            continue
        operation.item_index = target_index
    return aligned


def _strip_implicit_size_from_additions(text: str, state: State, llm_result, intent: IntentKind) -> object:
    if intent != "add_item":
        return llm_result

    if _has_explicit_size_mention(text) or _looks_like_explicit_edit(text):
        # Respect explicit user size/edit wording.
        return llm_result

    # Remove implicit sizes that model may hallucinate for newly added items.
    stripped = llm_result.model_copy(deep=True)
    changed = _strip_size_from_new_incoming_items(state.entities.items, stripped.entities.items)

    for operation in stripped.edit_operations:
        if operation.op == "add_item" and operation.item is not None:
            if operation.item.size_cm is not None:
                operation.item.size_cm = None
                changed = True

    if not changed:
        return llm_result
    return stripped


def _strip_size_from_new_incoming_items(current_items: list[Item], incoming_items: list[Item]) -> bool:
    existing_counts: dict[tuple[str, int, str | None, tuple[str, ...]], int] = {}
    for item in current_items:
        # Build multiset without size to distinguish old vs genuinely new lines.
        key = _item_key_without_size(item)
        existing_counts[key] = existing_counts.get(key, 0) + 1

    changed = False
    for item in incoming_items:
        key = _item_key_without_size(item)
        if existing_counts.get(key, 0) > 0:
            # Consume existing key occurrence, do not alter original items.
            existing_counts[key] -= 1
            continue
        # New item without explicit size mention should stay size=None.
        if item.size_cm is not None:
            item.size_cm = None
            changed = True
    return changed


def _item_key_without_size(item: Item) -> tuple[str, int, str | None, tuple[str, ...]]:
    normalized_variant = _normalize_text(item.variant) if item.variant else None
    normalized_modifiers = tuple(_normalize_text(value) for value in item.modifiers)
    return (_normalize_text(item.name), item.qty, normalized_variant, normalized_modifiers)


def _filter_edit_operations_for_text(
    state: State,
    operations: list[EditOperation],
    text: str,
    intent: IntentKind,
) -> list[EditOperation]:
    if not operations:
        return operations

    if intent != "add_item":
        return operations

    # For "add another pizza" requests, never let model rewrite or delete existing items.
    filtered = [operation for operation in operations if operation.op == "add_item"]
    if filtered:
        return filtered

    # If the model produced only destructive/edit operations for an add-intent,
    # ignore them completely and let normal merge fallback handle extracted entities.
    return []


def _infer_item_update_operations(state: State, incoming: Entities, text: str, intent: IntentKind) -> list[EditOperation]:
    if intent == "add_item":
        return []
    if not _looks_like_existing_item_update_request(text):
        return []
    if len(incoming.items) != 1 or not state.entities.items:
        return []

    incoming_item = incoming.items[0]
    # Resolve target item either by explicit index or by best name match.
    item_index = _extract_explicit_item_index(text, len(state.entities.items))
    if item_index is None:
        item_index = _find_matching_existing_item_index(state.entities.items, incoming_item.name)
    if item_index is None:
        return []

    existing_item = state.entities.items[item_index]
    operation = EditOperation(op="update_item", item_index=item_index)

    if incoming_item.size_cm is not None and incoming_item.size_cm != existing_item.size_cm:
        operation.size_cm = incoming_item.size_cm
    if incoming_item.variant is not None and incoming_item.variant != existing_item.variant:
        operation.variant = incoming_item.variant

    if incoming_item.modifiers:
        additions = [
            modifier
            for modifier in incoming_item.modifiers
            if not any(_normalize_text(existing) == _normalize_text(modifier) for existing in existing_item.modifiers)
        ]
        # Keep only modifiers that are truly new for this item.
        if additions:
            operation.modifiers_add = additions

    if operation.size_cm is None and operation.variant is None and not operation.modifiers_add:
        return []
    return [operation]


def _apply_item_update(item: Item, operation: EditOperation) -> None:
    # Apply scalar replacements first.
    if operation.name:
        item.name = operation.name
    if operation.qty is not None:
        item.qty = operation.qty
    if operation.size_cm is not None:
        item.size_cm = operation.size_cm
    if operation.variant is not None:
        item.variant = operation.variant
    if operation.modifiers_replace is not None:
        item.modifiers = list(operation.modifiers_replace)
    if operation.modifiers_remove:
        # Remove by normalized token to survive spelling/case variation.
        remove_set = {_normalize_text(value) for value in operation.modifiers_remove}
        item.modifiers = [value for value in item.modifiers if _normalize_text(value) not in remove_set]
    for modifier in operation.modifiers_add:
        # Avoid duplicate modifiers by normalized comparison.
        if not any(_normalize_text(existing) == _normalize_text(modifier) for existing in item.modifiers):
            item.modifiers.append(modifier)


def _merge_scalar_fields(base: Entities, incoming: Entities) -> Entities:
    merged = base.model_copy(deep=True)
    for field in ["delivery_type", "address", "time", "phone", "comment"]:
        # Fill only non-empty values extracted this turn.
        value = getattr(incoming, field)
        if value is not None and value != "":
            setattr(merged, field, value)
    return merged


def _looks_like_add_item_request(text: str) -> bool:
    normalized = _normalize_text(text)
    add_markers = ("еще", "ещё", "добавь", "добавить", "хочу еще", "хочу ещё")
    if not any(marker in normalized for marker in add_markers):
        return False

    # "в пепперони добавь грибы" is not add-item, it's update existing item.
    if normalized.startswith("в ") or normalized.startswith("во "):
        return False
    if " в " in normalized and any(word in normalized for word in ("добавь", "добавить")):
        return False

    return True


def _looks_like_existing_item_update_request(text: str) -> bool:
    normalized = _normalize_text(text)
    update_markers = ("добав", "убери", "удали", "без ", "замени", "измени", "исправ", "сделай")
    if not any(marker in normalized for marker in update_markers):
        return False

    if normalized.startswith("в ") or normalized.startswith("во "):
        return True
    if " в " in normalized:
        return True
    if " из " in normalized:
        return True
    return False


def _has_explicit_size_mention(text: str) -> bool:
    normalized = _normalize_text(text)
    if re.search(r"\b\d{2}\s*(см|cm|сантиметр(?:а|ов)?|сантиметров?)?\b", normalized):
        return True
    size_words = {"маленькую", "среднюю", "большую", "small", "medium", "large"}
    return any(word in normalized.split() for word in size_words)


def _looks_like_direct_order_request(text: str) -> bool:
    normalized = _normalize_text(text)
    order_markers = ("хочу", "мне", "надо", "будет", "нужна", "нужно", "закажи")
    return any(marker in normalized for marker in order_markers)


def _extract_catalog_pizzas_from_text(text: str) -> list[str]:
    catalog = _catalog_pizzas()
    normalized_catalog = {_normalize_name_for_catalog(name): name for name in catalog}
    # Try longer catalog names first ("четыре сыра" before "сыра").
    token_lengths = sorted({len(normalized.split()) for normalized in normalized_catalog}, reverse=True)
    tokens = _normalize_name_for_catalog(text).split()
    if not tokens:
        return []

    matches: list[str] = []
    index = 0
    while index < len(tokens):
        matched_name: str | None = None
        matched_length = 0
        for length in token_lengths:
            if index + length > len(tokens):
                continue
            candidate = " ".join(tokens[index : index + length])
            resolved = _resolve_catalog_name(candidate, normalized_catalog)
            if resolved is None:
                continue
            matched_name = resolved
            matched_length = length
            break

        if matched_name is None:
            # No catalog phrase from this token; shift window by one.
            index += 1
            continue

        if matched_name not in matches:
            # Keep first occurrence order and de-duplicate results.
            matches.append(matched_name)
        index += matched_length

    return matches


def _catalog_pizzas() -> tuple[str, ...]:
    return catalog_runtime.get_snapshot().pizza_names


def _resolve_catalog_name(item_name: str, normalized_catalog: dict[str, str]) -> str | None:
    normalized = _normalize_name_for_catalog(item_name)
    exact = normalized_catalog.get(normalized)
    if exact is not None:
        return exact

    soft_normalized = _soft_normalize_name_for_catalog(item_name)
    best_match: str | None = None
    best_distance: int | None = None
    for candidate_normalized, candidate_name in normalized_catalog.items():
        # Compare both strict and "soft" (collapsed repeated chars) distances.
        distance = min(
            _levenshtein_distance(normalized, candidate_normalized),
            _levenshtein_distance(soft_normalized, _soft_normalize_name_for_catalog(candidate_name)),
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


def _normalize_name_for_catalog(value: str) -> str:
    lowered = value.strip().lower().replace("ё", "е")
    return re.sub(r"[^a-zа-я0-9]+", " ", lowered).strip()


def _soft_normalize_name_for_catalog(value: str) -> str:
    normalized = _normalize_name_for_catalog(value)
    return re.sub(r"(.)\1+", r"\1", normalized)


def _levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous_row = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        # Standard dynamic-programming row update.
        current_row = [i]
        for j, right_char in enumerate(right, start=1):
            insertions = previous_row[j] + 1
            deletions = current_row[j - 1] + 1
            substitutions = previous_row[j - 1] + (left_char != right_char)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def _catalog_match_threshold(length: int) -> int:
    if length <= 5:
        return 1
    if length <= 9:
        return 2
    return 3


def _find_matching_existing_item_index(items: list[Item], item_name: str) -> int | None:
    normalized_target = _normalize_name_for_catalog(item_name)
    soft_normalized_target = _soft_normalize_name_for_catalog(item_name)

    # Prefer unique exact normalized name.
    exact_matches = [
        index for index, item in enumerate(items) if _normalize_name_for_catalog(item.name) == normalized_target
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]

    # Fallback to soft normalization for minor spelling noise.
    soft_matches = [
        index for index, item in enumerate(items) if _soft_normalize_name_for_catalog(item.name) == soft_normalized_target
    ]
    if len(soft_matches) == 1:
        return soft_matches[0]

    return None


def _expected_scalar_field(state: State) -> str | None:
    # Delivery type may live in pending choice even when missing list is outdated.
    if state.pending_choice and state.pending_choice.field in {"delivery_type"}:
        return state.pending_choice.field
    if not state.missing:
        return None
    field = state.missing[0]
    if field in {"address", "phone", "time"}:
        return field
    return None


def _looks_like_address(text: str) -> bool:
    normalized = text.strip().lower()
    address_markers = ["ул", "улица", "дом", "д.", "просп", "пр-т", "переул", "шоссе", "бульвар", ","]
    return any(marker in normalized for marker in address_markers) or bool(re.search(r"\d", normalized))


def _looks_like_phone(text: str) -> bool:
    digits = re.sub(r"\D", "", text)
    return 9 <= len(digits) <= 15


def _looks_like_time(text: str) -> bool:
    normalized = text.strip().lower()
    return bool(re.search(r"\b\d{1,2}:\d{2}\b", normalized)) or "через" in normalized or "как можно скорее" in normalized


def _looks_like_explicit_edit(text: str) -> bool:
    normalized = text.strip().lower()
    edit_markers = (
        "замени",
        "вместо",
        "убери",
        "удали",
        "без ",
        "измени",
        "исправ",
        "поменяй",
        "замени ",
    )
    return any(marker in normalized for marker in edit_markers)


def _apply_expected_scalar_input(state: State, text: str) -> tuple[bool, str]:
    expected_field = _expected_scalar_field(state)
    if expected_field == "address" and _looks_like_address(text):
        # Mutate state in place to keep caller references unchanged.
        updated = state.model_copy(deep=True)
        updated.entities.address = text.strip()
        updated.missing = [field for field in updated.missing if field != "address"]
        state.entities = updated.entities
        state.missing = updated.missing
        state.pending_choice = updated.pending_choice
        return True, "Записал адрес."

    if expected_field == "phone":
        parsed_phone = _parse_phone(text)
        if parsed_phone is not None:
            updated = state.model_copy(deep=True)
            updated.entities.phone = parsed_phone
            updated.missing = [field for field in updated.missing if field != "phone"]
            state.entities = updated.entities
            state.missing = updated.missing
            state.pending_choice = updated.pending_choice
            return True, "Записал телефон."

        digits = re.sub(r"\D", "", text)
        if digits:
            # We treat short digit sequence as handled with correction prompt.
            return True, "Номер выглядит коротким. Напишите телефон полностью, например: +79991234567."

    if expected_field == "time":
        parsed_time = _parse_time(text)
        if parsed_time is not None:
            updated = state.model_copy(deep=True)
            updated.entities.time = parsed_time
            updated.missing = [field for field in updated.missing if field != "time"]
            state.entities = updated.entities
            state.missing = updated.missing
            state.pending_choice = updated.pending_choice
            return True, "Записал время."

    return False, ""


def _apply_expected_size_choice_input(state: State, text: str) -> tuple[bool, str]:
    if state.pending_choice is None or state.pending_choice.field != "size_cm":
        return False, ""
    if not is_choice_only(text):
        return False, ""

    parsed_size = _parse_size_choice_input(text)
    if parsed_size is None:
        return False, ""

    current_options = _extract_size_values_from_options(state.pending_choice.options)
    if parsed_size in current_options:
        # Valid option, let normal pending-choice logic apply it.
        return False, ""

    updated_choice = state.pending_choice.model_copy(deep=True)
    nearest = _nearest_size_options(parsed_size)
    # Replace options with nearest available sizes and remember requested one.
    updated_choice.options = [f"{value} см" for value in nearest]
    updated_choice.requested_value = f"{parsed_size} см"
    state.pending_choice = updated_choice
    state.missing = _ensure_field_in_missing(state.missing, "size_cm")
    return True, ""


def _parse_size_choice_input(text: str) -> int | None:
    numbers = re.findall(r"\d{1,3}", text)
    if len(numbers) != 1:
        return None
    return int(numbers[0])


def _extract_size_values_from_options(options: list[str]) -> list[int]:
    values: list[int] = []
    for option in options:
        # Options are human-readable strings; extract first numeric token.
        digits = re.findall(r"\d+", option)
        if digits:
            values.append(int(digits[0]))
    return values


def _parse_phone(text: str) -> str | None:
    # Preserve leading '+' while removing separators/spaces.
    compact = re.sub(r"[^\d+]+", "", text.strip())
    digits = re.sub(r"\D", "", compact)
    if 9 <= len(digits) <= 15:
        return compact or digits
    return None


def _parse_time(text: str) -> TimeInfo | None:
    normalized = " ".join(text.strip().lower().split())
    # Fast mapping of common ASAP aliases.
    if normalized in {
        "сейчас",
        "прямо сейчас",
        "как можно скорее",
        "поскорее",
        "побыстрее",
        "скорее",
    }:
        return TimeInfo(type="asap", value=None)

    by_time_match = re.search(r"\bк\s*(\d{1,2}:\d{2})\b", normalized)
    if by_time_match:
        return TimeInfo(type="by_time", value=by_time_match.group(1))

    minutes_match = re.search(r"\bчерез\s*(\d{1,3})\s*мин", normalized)
    if minutes_match:
        return TimeInfo(type="in_minutes", value=int(minutes_match.group(1)))

    return None


def _normalize_addition_item_qty(entities: Entities, text: str) -> None:
    # Guard against model producing qty>1 for vague "добавь ..." phrasing.
    if len(entities.items) != 1 or not _looks_like_addition(text):
        return

    item = entities.items[0]
    if item.qty <= 1 or _has_explicit_item_quantity(text):
        return

    item.qty = 1


def _looks_like_addition(text: str) -> bool:
    normalized = text.strip().lower()
    addition_markers = ("еще", "ещё", "добав", "и ")
    return any(marker in normalized for marker in addition_markers)


def _has_explicit_item_quantity(text: str) -> bool:
    normalized = text.strip().lower()
    # Remove size mentions first so "30 см" is not treated as item quantity.
    without_size = re.sub(r"\b\d+\s*(см|cm|сантиметр(?:а|ов)?|сантиметров?)\b", " ", normalized)

    if re.search(r"\b\d+\b", without_size):
        return True

    quantity_words = {
        "один",
        "одна",
        "одно",
        "два",
        "две",
        "три",
        "четыре",
        "пять",
        "шесть",
        "семь",
        "восемь",
        "девять",
        "десять",
    }
    return any(word in quantity_words for word in without_size.split())


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())
