import os
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from .logging import configure_logging
from .parser import LLMError, parse_text
from .schemas import ParseRequest, ParseResponse

app = FastAPI(title="nlp-service")
logger = logging.getLogger(__name__)


@app.on_event("startup")
def on_startup() -> None:
    configure_logging()
    logger.info("nlp-service startup completed")


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.post("/v1/parse", response_model=ParseResponse)
def parse(request: ParseRequest) -> ParseResponse:
    logger.info(
        "Parse request received text_preview=%r has_state=%s items=%s missing=%s",
        _preview_text(request.text),
        request.state is not None,
        len(request.state.entities.items) if request.state is not None else 0,
        len(request.state.missing) if request.state is not None else 0,
    )
    try:
        response = parse_text(request.text, request.state)
        logger.info(
            "Parse request completed action=%s items=%s missing=%s has_choice=%s confidence=%.2f",
            response.action,
            len(response.entities.items),
            len(response.missing),
            response.choices is not None,
            response.confidence,
        )
        logger.debug(
            "Parse response state entities=%s missing=%s pending_choice=%s",
            response.state.entities.model_dump(),
            response.state.missing,
            response.state.pending_choice.model_dump() if response.state.pending_choice is not None else None,
        )
        return response
    except LLMError as exc:
        logger.error("Parse request failed with LLMError detail=%s", exc)
        logger.debug("Parse request stack", exc_info=True)
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def get_port() -> int:
    return int(os.getenv("PORT", "8000"))


def _preview_text(text: str, limit: int = 120) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
