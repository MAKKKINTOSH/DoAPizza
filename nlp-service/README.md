# nlp-service

Minimal NLP microservice that extracts pizza order entities via any OpenAI-compatible LLM endpoint, including OpenRouter, LM Studio, Ollama, and similar services.

## Requirements
- Python 3.11+
- Any OpenAI-compatible LLM endpoint

## Setup (uv)
```bash
uv venv
uv pip install -e ".[dev]"
```

## Run
All runtime behavior is controlled by the same generic variables:
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_API_KEY`
- `LLM_PROMPT_MODE`
- `LLM_TRUST_ENV`

Alternatively, put the same variables in `nlp-service/.env`.

Prompt mode:
- `auto`: try `system+user`, then fallback to `user_only` if the provider rejects system instructions.
- `system_user`: always send separate `system` and `user` messages.
- `user_only`: merge instructions into one `user` message.
- `LLM_TRUST_ENV=false` disables `HTTP_PROXY` / `HTTPS_PROXY` inherited from the shell. This is recommended for local endpoints such as LM Studio.

Logging:
- `LOG_LEVEL` controls console verbosity. Recommended default: `INFO`.
- `LOG_FILE_LEVEL` controls file verbosity. Recommended default: `DEBUG`.
- `LOG_FILE_PATH` controls the rotating log file path. Default: `logs/nlp-service.log`.

Catalog sync:
- `CATALOG_API_URL` backend menu endpoint (default: `http://127.0.0.1:8000/api/restaurant/variants/`)
- `CATALOG_REFRESH_INTERVAL_SECONDS` sync interval in seconds (default: `300`)
- `CATALOG_HTTP_TIMEOUT_SECONDS` timeout for catalog API requests (default: `5`)
- `CATALOG_PIZZAS` fallback pizza list for cold start / API outages
- `CATALOG_SIZE_CM` fallback pizza sizes (default: `25,30,35`)

Optional metadata headers:
- `LLM_SITE_URL` -> sent as `HTTP-Referer`
- `LLM_SITE_NAME` -> sent as `X-Title`

Backward-compatible aliases are still supported:
- `OPENROUTER_SITE_URL`
- `OPENROUTER_SITE_NAME`

OpenRouter example:
```bash
set LLM_BASE_URL=https://openrouter.ai/api/v1
set LLM_API_KEY=your_api_key_here
set LLM_MODEL=mistralai/mistral-small-3.1-24b-instruct:free
set LLM_PROMPT_MODE=auto
set LLM_TRUST_ENV=false
uv run uvicorn nlp_service.app:app --reload --port 8000
```

LM Studio example:
```bash
set LLM_BASE_URL=http://localhost:1234/v1
set LLM_API_KEY=
set LLM_MODEL=Qwen2.5-7B-Instruct
set LLM_PROMPT_MODE=system_user
set LLM_TRUST_ENV=false
uv run uvicorn nlp_service.app:app --reload --port 8000
```

Any other OpenAI-compatible service works the same way:
```bash
set LLM_BASE_URL=https://your-provider.example/v1
set LLM_API_KEY=your_key_if_needed
set LLM_MODEL=provider-model-name
set LLM_PROMPT_MODE=auto
set LLM_TRUST_ENV=false
uv run uvicorn nlp_service.app:app --reload --port 8000
```

The logging setup is enabled both for:
```bash
uv run uvicorn nlp_service.app:app --reload --port 8000
```

and for:
```bash
uv run python main.py
```

Both run modes enable:
- concise console logs for requests and failures
- detailed rotating file logs for LLM request attempts, retries, and JSON repair

## API
- `GET /health` -> `ok`
- `POST /v1/parse` -> `{ action, message, entities, missing, choices?, state, confidence }`

## Behavior notes
- The parser keeps dialogue `state` between turns.
- Follow-up choices can be answered in a separate message.
- Optional modifier questions can be skipped with replies like `не надо` if the choice includes a skip option such as `Не добавлять`.
- When the user edits an existing order, the NLP layer can now replace the full current order state instead of only appending new items.

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
