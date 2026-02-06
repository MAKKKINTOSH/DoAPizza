# nlp-service

Minimal NLP microservice that extracts pizza order entities via an OpenAI-compatible LLM (LM Studio).

## Requirements
- Python 3.11+
- LM Studio OpenAI-compatible server

## Setup (uv)
```bash
uv venv
uv pip install -e ".[dev]"
```

## Run
```bash
set LLM_BASE_URL=http://localhost:1234/v1
set LLM_MODEL=Qwen2.5-7B-Instruct
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
