import json
import os
import time
from typing import Any
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from .schemas import Choice, EditOperation, Entities, State


class LLMError(RuntimeError):
    pass


class LLMResult(BaseModel):
    entities: Entities = Field(default_factory=Entities)
    edit_operations: list[EditOperation] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    choices: Choice | None = None
    message: str = ""
    confidence: float = 0.0
    state_update_mode: Literal["merge", "replace"] = "merge"


class LLMClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1").rstrip("/")
        self.model = os.getenv("LLM_MODEL", "Qwen2.5-7B-Instruct")
        self.timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
        self.retries = int(os.getenv("LLM_RETRIES", "2"))

    def extract(self, text: str, state: State) -> LLMResult:
        system_prompt = self._system_prompt()
        user_prompt = self._user_prompt(text, state)
        content = self._chat(system_prompt, user_prompt)
        data = self._parse_json_with_fix(content, system_prompt, user_prompt)
        try:
            return LLMResult.model_validate(data)
        except ValidationError as exc:
            raise LLMError(f"LLM JSON schema validation failed: {exc}") from exc

    def _system_prompt(self) -> str:
        return (
            "You extract pizza order entities. "
            "Return only strict JSON, no markdown. "
            "All user-facing messages must be in Russian. "
            "Speak like a calm pizza operator for ordinary people. "
            "Ask only one short clear question at a time. "
            "Schema: {"
            "\"entities\": {"
            "\"items\": [{\"name\": string, \"qty\": int, \"size_cm\": int|null, "
            "\"variant\": string|null, \"modifiers\": [string]}], "
            "\"delivery_type\": string|null, \"address\": string|null, "
            "\"time\": {\"type\": \"asap\"|\"by_time\"|\"in_minutes\"|null, "
            "\"value\": string|int|null}, \"phone\": string|null, \"comment\": string|null}, "
            "\"edit_operations\": [{"
            "\"op\": \"add_item\"|\"remove_item\"|\"replace_item\"|\"update_item\", "
            "\"item_index\": int|null, "
            "\"item\": {\"name\": string, \"qty\": int, \"size_cm\": int|null, \"variant\": string|null, \"modifiers\": [string]}|null, "
            "\"name\": string|null, \"qty\": int|null, \"size_cm\": int|null, \"variant\": string|null, "
            "\"modifiers_add\": [string], \"modifiers_remove\": [string], \"modifiers_replace\": [string]|null"
            "}], "
            "\"missing\": [string], "
            "\"choices\": {\"field\": string, \"options\": [string], \"item_index\": int|null, \"requested_value\": string|null} | null, "
            "\"message\": string, "
            "\"confidence\": number, "
            "\"state_update_mode\": \"merge\"|\"replace\"}"
        )

    def _user_prompt(self, text: str, state: State) -> str:
        state_json = json.dumps(state.model_dump(), ensure_ascii=True)
        catalog = os.getenv("CATALOG_PIZZAS", "Маргарита,Пепперони,Четыре сыра,Гавайская,Диабло")
        return (
            "Text: " + text + "\n"
            "Current state JSON: " + state_json + "\n"
            "Pizza catalog: " + catalog + "\n"
            "Rules: merge with current state; only fill values you can extract; "
            "item_index is zero-based and refers to the current state items order; "
            "pizza names must be chosen from the pizza catalog or matched to the closest catalog pizza name; "
            "do not randomly swap one catalog pizza for another; "
            "Intent priority rules are strict and more important than everything else: "
            "1) if the user asks to add another pizza or one more pizza, use add_item only; never use replace_item or update_item for that; "
            "phrases like 'еще маргариту', 'добавь пепперони', 'хочу еще одну пиццу', 'и еще 1 маргариту' mean add_item; "
            "2) if the user asks to change toppings or properties of an existing pizza, use update_item only; "
            "phrases like 'в пепперони добавь ананасы', 'убери грибы из маргариты', 'сделай первую 35 см' mean update_item; "
            "3) if the user explicitly says replace/substitute one pizza with another, use replace_item only; "
            "phrases like 'замени пепперони на маргариту', 'вместо первой пиццы маргариту' mean replace_item; "
            "4) if the user explicitly says remove/delete a pizza, use remove_item only; "
            "phrases like 'удали первую пиццу', 'убери вторую' mean remove_item; "
            "if the user edits an existing pizza, prefer edit_operations and point to the exact existing item_index instead of duplicating pizzas; "
            "for phrases like 'удали первую пиццу' use remove_item with item_index 0; "
            "for phrases like 'в пепперони добавь ананасы' use update_item with the matching existing item_index and modifiers_add; "
            "for phrases like 'убери грибы из маргариты' use update_item with modifiers_remove; "
            "for phrases like 'замени пепперони на маргариту' use replace_item with the existing item_index and the new item; "
            "use add_item only for genuinely new pizzas the user wants to add; "
            "never convert an add-pizza request into replace_item; "
            "never rewrite an existing pizza when the user asked to add a new one; "
            "if edit_operations are enough, keep entities.items empty unless you also extracted scalar fields like phone/address/time; "
            "use state_update_mode=replace only as a last resort if you cannot express the edit with edit_operations; "
            "if the user adds new data without replacing old data, set state_update_mode to merge and return only the new or changed fragments, never repeat unchanged items from current state; "
            "for modifiers/toppings, copy the user's Russian wording as literally as possible; do not invent, beautify, translate, autocorrect, or substitute words; "
            "if the user wrote 'перец', return 'перец', not 'пеле' and not another word; "
            "if you are not confident about a modifier word, do not guess it; instead ask a short clarification question; "
            "do not put possible pizza names into modifiers; modifiers are only toppings/add-ons explicitly requested for a pizza; "
            "when a word likely names a new pizza, use add_item or replace_item, not modifiers_add; "
            "if the intent is ambiguous between add_item and update_item, ask a clarification question and do not mutate the order aggressively; "
            "if the user mentions a numeric pizza size, preserve the exact mentioned number in size_cm even if it may be unsupported by the menu; "
            "if a choice is needed (size/variant/etc), return choices with options and put that field in missing; "
            "for optional add-ons/modifiers include a skip option like 'Не добавлять'; "
            "if nothing is missing, missing must be empty; return valid JSON only."
        )

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
        }
        data = self._post_with_retries(url, payload)
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM response format: {data}") from exc

    def _post_with_retries(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                last_exc = exc
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise LLMError(f"LLM request failed after retries: {exc}") from exc
        raise LLMError(f"LLM request failed: {last_exc}")

    def _parse_json_with_fix(self, content: str, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            fix_prompt = (
                "Your previous reply was invalid JSON. "
                "Return only valid JSON that matches the schema, no markdown, no extra text."
            )
            repair_content = self._chat(fix_prompt, f"Original prompt: {user_prompt}\nInvalid JSON: {content}")
            try:
                return json.loads(repair_content)
            except json.JSONDecodeError as exc:
                raise LLMError("LLM JSON repair failed") from exc
