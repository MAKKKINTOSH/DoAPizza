# nlp-service

Minimal NLP microservice that extracts pizza order entities via OpenRouter (OpenAI-compatible API).

## Requirements
- Python 3.11+
- OpenRouter API key

## Setup (uv)
```bash
uv venv
uv pip install -e ".[dev]"
```

## Run
```bash
set LLM_API_KEY=your_api_key_here
set LLM_BASE_URL=https://openrouter.ai/api/v1
set LLM_MODEL=mistralai/mistral-small-3.1-24b-instruct:free
set LLM_PROMPT_MODE=auto
uv run uvicorn nlp_service.app:app --reload --port 8000
```

Alternatively, put the same variables in `nlp-service/.env`.

Auth rules:
- `LLM_API_KEY` is used first (provider-agnostic).
- If `LLM_API_KEY` is empty, `OPENROUTER_API_KEY` is used.
- For local OpenAI-compatible servers, API key can stay empty.

Prompt mode (`LLM_PROMPT_MODE`):
- `auto` (default): try `system+user`, fallback to `user_only` if model rejects system/developer instructions.
- `system_user`: always send separate `system` and `user` messages.
- `user_only`: merge service instructions into a single `user` message (useful for strict providers/models).

Optional OpenRouter headers for ranking:
- `OPENROUTER_SITE_URL` -> sent as `HTTP-Referer`
- `OPENROUTER_SITE_NAME` -> sent as `X-Title`

Local LLM example (LM Studio/Ollama OpenAI-compatible):
```bash
set LLM_BASE_URL=http://localhost:1234/v1
set LLM_API_KEY=
set LLM_MODEL=Qwen2.5-7B-Instruct
set LLM_PROMPT_MODE=system_user
uv run uvicorn nlp_service.app:app --reload --port 8000
```

## API
- `GET /health` -> `ok`
- `POST /v1/parse` -> `{ action, message, entities, missing, choices?, state, confidence }`

## Curl examples
1) Full order (likely READY)
```bash
curl -s -X POST http://localhost:8000/v1/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"Две пепперони 30 см, доставка на Пушкина 10, телефон 79991234567"}'
```

2) Missing info (likely ASK)
```bash
curl -s -X POST http://localhost:8000/v1/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"Пицца маргарита"}'
```

3) Apply choice with state
```bash
curl -s -X POST http://localhost:8000/v1/parse \
  -H "Content-Type: application/json" \
  -d '{"text":"30","state":{"entities":{"items":[{"name":"Маргарита","qty":1,"size_cm":null,"variant":null,"modifiers":[]}],"delivery_type":null,"address":null,"time":null,"phone":null,"comment":null},"missing":["size_cm"],"pending_choice":{"field":"size_cm","options":["25","30"],"item_index":0}}}'
```

## Tests
```bash
uv run pytest
```
