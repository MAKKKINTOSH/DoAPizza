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
            "Ты — NLU/slot-filling движок для оформления заказа пиццы.\n"
            "Твоя задача: извлечь сущности из текста и решить, чего не хватает.\n"
            "Верни ТОЛЬКО валидный JSON (один объект), без markdown, без комментариев.\n"
            "ВСЕ строки в поле message — по-русски.\n"
            "\n"
            "КЛЮЧЕВЫЕ ПРАВИЛА:\n"
            "1) item.name — это НАЗВАНИЕ ПИЦЦЫ/позиции (например: 'Пепперони', '4 сыра').\n"
            "   НЕЛЬЗЯ ставить туда общие слова: 'пицца', 'пиццу', 'пиццы', 'заказ'.\n"
            "   Если название не указано явно — item.name = null и добавь missing 'items[0].name'.\n"
            "2) Нормализация модификаторов: приводи к нормальной форме.\n"
            "   Пример: 'ананасами' -> 'ананасы'. 'с чесночным соусом' -> 'чесночный соус'.\n"
            "3) Если missing НЕ пустой:\n"
            "   - message ОБЯЗАН быть ОДНИМ коротким вопросом про СЛЕДУЮЩЕЕ по приоритету поле.\n"
            "   - choices (если возможно) должен предлагать варианты для этого вопроса.\n"
            "4) Если missing пустой: message — короткое подтверждение распознанного заказа (не 'Заказ готов.').\n"
            "5) Не придумывай данные: не выдумывай адрес/телефон/время/размер/название.\n"
            "6) Объединяй с текущим state: уже заполненные поля не перетирай,\n"
            "   кроме случаев явного исправления пользователем ('не 26, а 30').\n"
            "\n"
            "ПРИОРИТЕТ ВОПРОСОВ (что спрашивать следующим):\n"
            "A) items[0].name (если null/непонятно)\n"
            "B) items[0].size_cm (если не указан)\n"
            "C) items[0].variant (если не указан, но пользователь намекнул на выбор 'тонкое/традиционное')\n"
            "D) delivery_type (если не указан)\n"
            "E) address (ТОЛЬКО если delivery_type='delivery' и адрес отсутствует)\n"
            "F) phone (если отсутствует)\n"
            "G) time (если отсутствует — можно оставить null и не обязательно спрашивать)\n"
            "\n"
            "СХЕМА JSON (строго эти ключи):\n"
            "{\n"
            '  "entities": {\n'
            '    "items": [{"name": string|null, "qty": int, "size_cm": int|null, "variant": string|null, "modifiers": [string]}],\n'
            '    "delivery_type": string|null,\n'
            '    "address": string|null,\n'
            '    "time": {"type": "asap"|"by_time"|"in_minutes", "value": string|int|null} | null,\n'
            '    "phone": string|null,\n'
            '    "comment": string|null\n'
            "  },\n"
            '  "missing": [string],\n'
            '  "choices": {"field": string, "options": [string], "item_index": int|null} | null,\n'
            '  "message": string,\n'
            '  "confidence": number\n'
            "}\n"
            "\n"
            "FEW-SHOT ПРИМЕР:\n"
            "Ввод: 'можно пиццу пепперони 26см с чесночным соусом и сверху с ананасами'\n"
            "Вывод:\n"
            "{\n"
            '  "entities": {\n'
            '    "items": [{"name":"Пепперони","qty":1,"size_cm":26,"variant":null,"modifiers":["чесночный соус","ананасы"]}],\n'
            '    "delivery_type": null, "address": null, "time": null, "phone": null, "comment": null\n'
            "  },\n"
            '  "missing": ["delivery_type"],\n'
            '  "choices": {"field":"delivery_type","options":["доставка","самовывоз"],"item_index": null},\n'
            '  "message": "Доставка или самовывоз?",\n'
            '  "confidence": 0.78\n'
            "}\n"
        ) 

    def _user_prompt(self, text: str, state: State) -> str:
        state_json = json.dumps(state.model_dump(), ensure_ascii=False)
        return (
            f"Текст пользователя: {text}\n"
            f"Текущее состояние (state) JSON: {state_json}\n"
            "Сделай merge со state по правилам из system.\n"
            "Верни только JSON по схеме."
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
        def try_load(s: str) -> dict[str, Any] | None:
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                # попытка вытащить первый JSON-объект из текста
                start = s.find("{")
                end = s.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(s[start:end+1])
                    except json.JSONDecodeError:
                        return None
                return None

        parsed = try_load(content)
        if parsed is not None:
            return parsed

        repair_system = system_prompt + "\n\n" + (
            "Твоя предыдущая выдача была НЕ валидным JSON.\n"
            "СРОЧНО: верни ТОЛЬКО валидный JSON по той же схеме, без лишних ключей и текста."
        )
        repair_content = self._chat(repair_system, f"Исходный user prompt:\n{user_prompt}\n\nНевалидный ответ:\n{content}")
        parsed2 = try_load(repair_content)
        if parsed2 is None:
            raise LLMError("LLM JSON repair failed")
        return parsed2
