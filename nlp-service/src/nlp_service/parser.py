import os

import httpx

from .llm import LLMClient, LLMError
from .schemas import Entities, ParseResponse, State
from .state_machine import apply_pending_choice, is_choice_only, merge_entities

LLM_CLIENT = LLMClient()


def parse_text(text: str, state: State | None) -> ParseResponse:
    current_state = state.model_copy(deep=True) if state else State()

    message = ""
    confidence = 0.0

    choice_applied = False
    if current_state.pending_choice:
        current_state, choice_applied, _ = apply_pending_choice(current_state, text)
        if choice_applied:
            message = "Принял выбор."

    call_llm = True
    if choice_applied and is_choice_only(text):
        call_llm = False

    if call_llm:
        llm_result = LLM_CLIENT.extract(text, current_state)
        current_state.entities = merge_entities(current_state.entities, llm_result.entities)
        current_state.missing = list(llm_result.missing or [])
        current_state.pending_choice = llm_result.choices
        message = llm_result.message or message
        confidence = llm_result.confidence or confidence

    _maybe_call_delivery_api(current_state.entities)

    choices = current_state.pending_choice
    missing = current_state.missing
    if choices and choices.field not in missing:
        missing = missing + [choices.field]

    action = "ASK" if (missing or choices) else "READY"

    if not message:
        if action == "ASK":
            if choices and choices.options:
                message = "Выберите вариант: " + ", ".join(choices.options)
            elif missing:
                message = "Нужно уточнить: " + ", ".join(missing)
            else:
                message = "Нужна дополнительная информация."
        else:
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