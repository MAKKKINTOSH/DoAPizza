import json
import os
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from .schemas import Choice, Entities, State


class LLMError(RuntimeError):
    pass


class LLMResult(BaseModel):
    entities: Entities = Field(default_factory=Entities)
    missing: list[str] = Field(default_factory=list)
    choices: Choice | None = None
    message: str = ""
    confidence: float = 0.0


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
            "Schema: {"
            "\"entities\": {"
            "\"items\": [{\"name\": string, \"qty\": int, \"size_cm\": int|null, "
            "\"variant\": string|null, \"modifiers\": [string]}], "
            "\"delivery_type\": string|null, \"address\": string|null, "
            "\"time\": {\"type\": \"asap\"|\"by_time\"|\"in_minutes\"|null, "
            "\"value\": string|int|null}, \"phone\": string|null, \"comment\": string|null}, "
            "\"missing\": [string], "
            "\"choices\": {\"field\": string, \"options\": [string], \"item_index\": int|null} | null, "
            "\"message\": string, "
            "\"confidence\": number}"
        )

    def _user_prompt(self, text: str, state: State) -> str:
        state_json = json.dumps(state.model_dump(), ensure_ascii=True)
        return (
            "Text: " + text + "\n"
            "Current state JSON: " + state_json + "\n"
            "Rules: merge with current state; only fill values you can extract; "
            "if a choice is needed (size/variant/etc), return choices with options and put that field in missing; "
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
