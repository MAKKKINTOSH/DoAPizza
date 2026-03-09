# tgbot

Telegram bot service for pizza ordering. It uses `nlp-service` as the dialogue brain and adds:

- Telegram transport via `aiogram`
- per-chat conversation state
- confirmation step before final submission
- placeholder catalog validation for pizza names

See product behavior rules in [`PRODUCT_SPEC.md`](./PRODUCT_SPEC.md).

## What the bot does

1. Accepts a free-form order message like an operator would.
2. Sends each user message together with the current dialogue `state` to `nlp-service`.
3. Repeats follow-up questions returned by NLP (`ASK`, `message`, `choices`).
4. When NLP returns `READY`, shows an order summary and asks for confirmation.
5. Rejects pizzas that are not present in the temporary local catalog stub.
6. Supports `/menu` command to show currently available pizzas without interrupting current order flow.

## Requirements

- Python 3.11+
- Running `nlp-service`
- Telegram bot token from BotFather

## Setup

```bash
uv venv
uv pip install -e ".[dev]"
cp .env.example .env
```

Required env vars:

- `TELEGRAM_BOT_TOKEN`
- `NLP_SERVICE_BASE_URL`

Optional env vars:

- `TELEGRAM_API_BASE_URL`
- `TELEGRAM_POLL_TIMEOUT_SECONDS`
- `HTTP_TIMEOUT_SECONDS`
- `NLP_REQUEST_TIMEOUT_SECONDS`
- `CATALOG_API_URL`
- `CATALOG_REFRESH_INTERVAL_SECONDS`
- `CATALOG_HTTP_TIMEOUT_SECONDS`
- `CATALOG_PIZZAS`
- `LOG_LEVEL`

## Run

```bash
uv run python main.py
```

The bot uses long polling (`aiogram`) and stores chat sessions in memory. If the process restarts, active conversations are lost.

## Logging

The bot writes runtime logs to stdout via Python `logging`.

- `LOG_LEVEL=INFO` for normal operation
- `LOG_LEVEL=DEBUG` to see incoming message previews, Telegram API calls, and NLP request flow

## Local NLP connectivity

For local `NLP_SERVICE_BASE_URL`, use `127.0.0.1`, not `0.0.0.0`.

- correct: `http://127.0.0.1:8182`
- avoid: `http://0.0.0.0:8182`

The NLP client also ignores proxy environment variables on purpose, so local proxy settings do not interfere with bot-to-NLP traffic.

## Catalog source

The bot refreshes pizza catalog from backend `CATALOG_API_URL` every `CATALOG_REFRESH_INTERVAL_SECONDS`.
If backend is unavailable, bot keeps last successful snapshot and falls back to local `CATALOG_PIZZAS` on cold start.

## Tests

```bash
uv run pytest
```
