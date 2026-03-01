import os
import re

import httpx

from .llm import LLMClient, LLMError
from .schemas import Choice, EditOperation, Entities, Item, ParseResponse, State, TimeInfo
from .state_machine import apply_pending_choice, is_choice_only, is_exact_choice_reply, merge_entities

LLM_CLIENT = LLMClient()
DEFAULT_CATALOG_PIZZAS = ("Маргарита", "Пепперони", "Четыре сыра", "Гавайская", "Диабло")


def parse_text(text: str, state: State | None) -> ParseResponse:
    current_state = state.model_copy(deep=True) if state else State()

    message = ""
    confidence = 0.0

    choice_applied = False
    selected_choice: str | None = None
    if current_state.pending_choice:
        current_state, choice_applied, selected_choice = apply_pending_choice(current_state, text)
        if choice_applied:
            message = "Принял выбор."

    call_llm = True
    if choice_applied and (is_choice_only(text) or is_exact_choice_reply(text, selected_choice)):
        call_llm = False

    scalar_applied, scalar_message = _apply_expected_scalar_input(current_state, text)
    if scalar_applied:
        call_llm = False
        message = scalar_message or message

    if call_llm:
        llm_result = LLM_CLIENT.extract(text, current_state)
        llm_result = _align_result_with_catalog(text, llm_result)
        llm_result = _align_edit_operations_with_state(text, current_state, llm_result)
        llm_result = _strip_implicit_size_from_additions(text, llm_result)
        filtered_operations = _filter_edit_operations_for_text(current_state, llm_result.edit_operations, text)
        fallback_operations = _infer_item_update_operations(current_state, llm_result.entities, text)
        if filtered_operations:
            current_state.entities = _apply_edit_operations(current_state.entities, filtered_operations)
            current_state.entities = _merge_scalar_fields(current_state.entities, llm_result.entities)
        elif fallback_operations:
            current_state.entities = _apply_edit_operations(current_state.entities, fallback_operations)
            current_state.entities = _merge_scalar_fields(current_state.entities, llm_result.entities)
        elif llm_result.state_update_mode == "replace" and _looks_like_explicit_edit(text):
            current_state.entities = llm_result.entities.model_copy(deep=True)
        else:
            sanitized_entities = _sanitize_incoming_entities(current_state, llm_result.entities, text)
            current_state.entities = merge_entities(current_state.entities, sanitized_entities)
        current_state.missing = list(llm_result.missing or [])
        current_state.pending_choice = llm_result.choices
        message = llm_result.message or message
        confidence = llm_result.confidence or confidence

    _maybe_call_delivery_api(current_state.entities)

    current_state = _enforce_required_order_flow(current_state)

    choices = current_state.pending_choice
    missing = current_state.missing
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
    base_url = os.getenv("DELIVERY_API_BASE_URL", "").strip()
    if not base_url:
        return

    url = base_url.rstrip("/") + "/v1/nlp/verify"
    payload = entities.model_dump()
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(url, json=payload)
    except httpx.RequestError:
        return


__all__ = ["parse_text", "LLMError"]


SIZE_OPTIONS = ["25 см", "30 см", "35 см"]
DELIVERY_TYPE_OPTIONS = ["Доставка", "Самовывоз"]
ALLOWED_SIZE_CM = [25, 30, 35]


def _enforce_required_order_flow(state: State) -> State:
    updated = state.model_copy(deep=True)
    updated.pending_choice = _normalize_pending_choice(updated.pending_choice)

    if not updated.entities.items:
        updated.pending_choice = None
        updated.missing = ["items"]
        return updated

    invalid_size_choice = _build_invalid_size_choice(updated)
    if invalid_size_choice is not None:
        updated.pending_choice = invalid_size_choice
        updated.missing = _ensure_field_in_missing(updated.missing, invalid_size_choice.field)
        return updated

    if updated.pending_choice:
        updated.missing = _ensure_field_in_missing(updated.missing, updated.pending_choice.field)
        return updated

    for index, item in enumerate(updated.entities.items):
        if item.size_cm is None:
            updated.pending_choice = Choice(field="size_cm", options=SIZE_OPTIONS, item_index=index)
            updated.missing = _ensure_field_in_missing(updated.missing, "size_cm")
            return updated

    if not updated.entities.delivery_type:
        updated.pending_choice = Choice(field="delivery_type", options=DELIVERY_TYPE_OPTIONS, item_index=None)
        updated.missing = _ensure_field_in_missing(updated.missing, "delivery_type")
        return updated

    updated.missing = [field for field in updated.missing if field != "delivery_type"]

    if _requires_address(updated.entities.delivery_type) and not updated.entities.address:
        updated.missing = _ensure_field_in_missing(updated.missing, "address")
        return updated
    updated.missing = [field for field in updated.missing if field != "address"]

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
    if normalized.field == "size_cm" and not normalized.options:
        normalized.options = list(SIZE_OPTIONS)
    if normalized.field == "delivery_type" and not normalized.options:
        normalized.options = list(DELIVERY_TYPE_OPTIONS)
    return normalized


def _ensure_field_in_missing(missing: list[str], field: str) -> list[str]:
    without_field = [value for value in missing if value != field]
    return [field, *without_field]


def _requires_address(delivery_type: str | None) -> bool:
    if delivery_type is None:
        return False
    normalized = delivery_type.strip().lower()
    return normalized in {"delivery", "доставка"}


def _build_followup_message(state: State) -> str:
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
            recommended = choice.options[-1] if choice.options else None
            options = " или ".join(choice.options)
            if recommended:
                return (
                    f"{choice.requested_value} не делаем. Могу предложить {options}. "
                    f"Советую {recommended}."
                )
        name = item.name if item else "этой пиццы"
        return f"Какой размер выбрать для '{name}'?"
    if choice.field == "delivery_type":
        return "Как получить заказ?"
    if choice.field == "variant":
        name = item.name if item else "пиццы"
        return f"Какой вариант выбрать для '{name}'?"
    if choice.field == "modifiers":
        name = item.name if item else "пиццы"
        return f"Нужны ли добавки для '{name}'?"
    if choice.options:
        return "Выберите вариант: " + ", ".join(choice.options)
    return "Выберите подходящий вариант."


def _build_invalid_size_choice(state: State) -> Choice | None:
    for index, item in enumerate(state.entities.items):
        if item.size_cm is None or item.size_cm in ALLOWED_SIZE_CM:
            continue

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
    ranked = sorted(ALLOWED_SIZE_CM, key=lambda option: (abs(option - value), -option))
    first = ranked[0]
    second = ranked[1] if len(ranked) > 1 else ranked[0]
    pair = sorted({first, second})
    return pair


def _sanitize_incoming_entities(current_state: State, incoming: Entities, text: str) -> Entities:
    sanitized = incoming.model_copy(deep=True)
    if not incoming.items:
        return sanitized

    _normalize_addition_item_qty(sanitized, text)

    expected_field = _expected_scalar_field(current_state)
    if expected_field == "address" and incoming.address and _looks_like_address(text):
        sanitized.items = []
    elif expected_field == "phone" and incoming.phone and _looks_like_phone(text):
        sanitized.items = []
    elif expected_field == "time" and incoming.time and _looks_like_time(text):
        sanitized.items = []
    return sanitized


def _apply_edit_operations(entities: Entities, operations: list[EditOperation]) -> Entities:
    updated = entities.model_copy(deep=True)
    for operation in operations:
        if operation.op == "add_item":
            if operation.item is not None:
                updated.items.append(operation.item.model_copy(deep=True))
            continue

        if operation.item_index is None or not (0 <= operation.item_index < len(updated.items)):
            continue

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


def _align_result_with_catalog(text: str, llm_result) -> object:
    mentioned = _extract_catalog_pizzas_from_text(text)
    if not mentioned:
        return llm_result

    aligned = llm_result.model_copy(deep=True)
    if _looks_like_add_item_request(text):
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

    mentioned = _extract_catalog_pizzas_from_text(text)
    if len(mentioned) != 1:
        return llm_result

    target_index = _find_matching_existing_item_index(state.entities.items, mentioned[0])
    if target_index is None:
        return llm_result

    aligned = llm_result.model_copy(deep=True)
    for operation in aligned.edit_operations:
        if operation.op not in {"update_item", "replace_item", "remove_item"}:
            continue
        operation.item_index = target_index
    return aligned


def _strip_implicit_size_from_additions(text: str, llm_result) -> object:
    if not _looks_like_add_item_request(text) or _has_explicit_size_mention(text):
        return llm_result

    stripped = llm_result.model_copy(deep=True)
    for item in stripped.entities.items:
        item.size_cm = None

    for operation in stripped.edit_operations:
        if operation.op == "add_item" and operation.item is not None:
            operation.item.size_cm = None

    return stripped


def _filter_edit_operations_for_text(state: State, operations: list[EditOperation], text: str) -> list[EditOperation]:
    if not operations:
        return operations

    if not _looks_like_add_item_request(text):
        return operations

    # For "add another pizza" requests, never let model rewrite or delete existing items.
    filtered = [operation for operation in operations if operation.op == "add_item"]
    if filtered:
        return filtered

    # If the model produced only destructive/edit operations for an add-intent,
    # ignore them completely and let normal merge fallback handle extracted entities.
    return []


def _infer_item_update_operations(state: State, incoming: Entities, text: str) -> list[EditOperation]:
    if _looks_like_add_item_request(text):
        return []
    if not _looks_like_existing_item_update_request(text):
        return []
    if len(incoming.items) != 1 or not state.entities.items:
        return []

    incoming_item = incoming.items[0]
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
        if additions:
            operation.modifiers_add = additions

    if operation.size_cm is None and operation.variant is None and not operation.modifiers_add:
        return []
    return [operation]


def _apply_item_update(item: Item, operation: EditOperation) -> None:
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
        remove_set = {_normalize_text(value) for value in operation.modifiers_remove}
        item.modifiers = [value for value in item.modifiers if _normalize_text(value) not in remove_set]
    for modifier in operation.modifiers_add:
        if not any(_normalize_text(existing) == _normalize_text(modifier) for existing in item.modifiers):
            item.modifiers.append(modifier)


def _merge_scalar_fields(base: Entities, incoming: Entities) -> Entities:
    merged = base.model_copy(deep=True)
    for field in ["delivery_type", "address", "time", "phone", "comment"]:
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
            index += 1
            continue

        if matched_name not in matches:
            matches.append(matched_name)
        index += matched_length

    return matches


def _catalog_pizzas() -> tuple[str, ...]:
    raw_catalog = os.getenv("CATALOG_PIZZAS", "")
    catalog = tuple(item.strip() for item in raw_catalog.split(",") if item.strip())
    return catalog or DEFAULT_CATALOG_PIZZAS


def _resolve_catalog_name(item_name: str, normalized_catalog: dict[str, str]) -> str | None:
    normalized = _normalize_name_for_catalog(item_name)
    exact = normalized_catalog.get(normalized)
    if exact is not None:
        return exact

    soft_normalized = _soft_normalize_name_for_catalog(item_name)
    best_match: str | None = None
    best_distance: int | None = None
    for candidate_normalized, candidate_name in normalized_catalog.items():
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

    exact_matches = [
        index for index, item in enumerate(items) if _normalize_name_for_catalog(item.name) == normalized_target
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]

    soft_matches = [
        index for index, item in enumerate(items) if _soft_normalize_name_for_catalog(item.name) == soft_normalized_target
    ]
    if len(soft_matches) == 1:
        return soft_matches[0]

    return None


def _expected_scalar_field(state: State) -> str | None:
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


def _parse_phone(text: str) -> str | None:
    compact = re.sub(r"[^\d+]+", "", text.strip())
    digits = re.sub(r"\D", "", compact)
    if 9 <= len(digits) <= 15:
        return compact or digits
    return None


def _parse_time(text: str) -> TimeInfo | None:
    normalized = " ".join(text.strip().lower().split())
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
