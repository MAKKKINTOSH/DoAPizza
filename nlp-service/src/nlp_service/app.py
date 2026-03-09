"""FastAPI endpoints for health checks and parse requests."""

import os
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from .catalog_runtime import catalog_runtime
from .catalog_sync import CatalogSync
from .logging import configure_logging
from .parser import LLMError, parse_text
from .schemas import ParseRequest, ParseResponse

app = FastAPI(title="nlp-service")
logger = logging.getLogger(__name__)
_catalog_sync: CatalogSync | None = None


@app.on_event("startup")
def on_startup() -> None:
    """Initialize logging once the ASGI app starts."""
    global _catalog_sync
    configure_logging()
    if _catalog_sync is None:
        _catalog_sync = CatalogSync(
            api_url=os.getenv("CATALOG_API_URL", "http://127.0.0.1:8000/api/restaurant/variants/"),
            refresh_interval_seconds=int(os.getenv("CATALOG_REFRESH_INTERVAL_SECONDS", "300")),
            http_timeout_seconds=float(os.getenv("CATALOG_HTTP_TIMEOUT_SECONDS", "5")),
        )
    _catalog_sync.start()
    snapshot = catalog_runtime.get_snapshot()
    logger.info(
        "Catalog snapshot active source=%s pizzas=%s sizes=%s",
        snapshot.source,
        len(snapshot.pizza_names),
        len(snapshot.sizes_cm),
    )
    logger.info("nlp-service startup completed")


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Stop background workers gracefully."""
    if _catalog_sync is not None:
        _catalog_sync.stop()


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    """Liveness endpoint used by probes and tests."""
    return "ok"


@app.post("/v1/parse", response_model=ParseResponse)
def parse(request: ParseRequest) -> ParseResponse:
    """Parse user text into structured order state via parser pipeline."""
    # Log compact request metadata first, so failures still have minimal trace.
    logger.info(
        "Parse request received text_preview=%r has_state=%s items=%s missing=%s",
        _preview_text(request.text),
        request.state is not None,
        len(request.state.entities.items) if request.state is not None else 0,
        len(request.state.missing) if request.state is not None else 0,
    )
    try:
        # Core pipeline: deterministic heuristics + optional LLM extraction.
        response = parse_text(request.text, request.state)
        # High-level result metrics for dashboards/alerts.
        logger.info(
            "Parse request completed action=%s items=%s missing=%s has_choice=%s confidence=%.2f",
            response.action,
            len(response.entities.items),
            len(response.missing),
            response.choices is not None,
            response.confidence,
        )
        # Deep state dump stays in debug level only.
        logger.debug(
            "Parse response state entities=%s missing=%s pending_choice=%s",
            response.state.entities.model_dump(),
            response.state.missing,
            response.state.pending_choice.model_dump() if response.state.pending_choice is not None else None,
        )
        return response
    except LLMError as exc:
        # LLM failures are surfaced as 502 because parser itself is healthy,
        # but upstream model dependency failed for this request.
        logger.error("Parse request failed with LLMError detail=%s", exc)
        logger.debug("Parse request stack", exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def get_port() -> int:
    """Read HTTP port from env with default for local runs."""
    return int(os.getenv("PORT", "8000"))


def _preview_text(text: str, limit: int = 120) -> str:
    """Compact log-safe representation of incoming text."""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
