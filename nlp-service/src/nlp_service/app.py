import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

from .parser import LLMError, parse_text
from .schemas import ParseRequest, ParseResponse

app = FastAPI(title="nlp-service")


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.post("/v1/parse", response_model=ParseResponse)
def parse(request: ParseRequest) -> ParseResponse:
    try:
        return parse_text(request.text, request.state)
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def get_port() -> int:
    return int(os.getenv("PORT", "8000"))
