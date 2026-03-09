"""
This module implements nlp client logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from __future__ import annotations

import logging
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx

from .schemas import ParseResponse, State


class NLPClientError(RuntimeError):
    """
    Represents NLPClientError.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    pass


logger = logging.getLogger(__name__)


class NLPClientProtocol(Protocol):
    """
    Represents NLPClientProtocol.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    def parse(self, text: str, state: State | None) -> ParseResponse:
        """
        Execute parse.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - text: input consumed by this function while processing the current request.
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        ...


class NLPClient:
    """
    Represents NLPClient.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        """
        Execute init.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - base_url: input consumed by this function while processing the current request.
        - timeout_seconds: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        self._base_url = _normalize_local_base_url(base_url.rstrip("/"))
        self._timeout_seconds = timeout_seconds

    def parse(self, text: str, state: State | None) -> ParseResponse:
        """
        Execute parse.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - text: input consumed by this function while processing the current request.
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        url = f"{self._base_url}/v1/parse"
        payload = {"text": text}
        if state is not None:
            payload["state"] = state.model_dump()
        logger.debug(
            "Calling NLP parse text_preview=%r has_state=%s items=%s missing=%s",
            _preview_text(text),
            state is not None,
            len(state.entities.items) if state is not None else 0,
            len(state.missing) if state is not None else 0,
        )

        try:
            with httpx.Client(timeout=self._timeout_seconds, trust_env=False) as client:
                response = client.post(url, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("NLP request failed base_url=%s", self._base_url)
            raise NLPClientError(f"NLP service request failed: {exc}") from exc

        try:
            parsed = ParseResponse.model_validate(response.json())
            logger.debug(
                "NLP parse completed action=%s items=%s missing=%s has_choice=%s confidence=%.2f",
                parsed.action,
                len(parsed.entities.items),
                len(parsed.missing),
                parsed.choices is not None,
                parsed.confidence,
            )
            return parsed
        except ValueError as exc:
            logger.exception("NLP returned invalid JSON")
            raise NLPClientError("NLP service returned invalid JSON") from exc


def _preview_text(text: str, limit: int = 80) -> str:
    """
    Execute preview text.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - text: input consumed by this function while processing the current request.
    - limit: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _normalize_local_base_url(base_url: str) -> str:
    """
    Execute normalize local base url.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - base_url: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    parts = urlsplit(base_url)
    if parts.hostname != "0.0.0.0":
        return base_url

    netloc = parts.netloc.replace("0.0.0.0", "127.0.0.1", 1)
    normalized = urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    logger.warning(
        "NLP_SERVICE_BASE_URL uses 0.0.0.0; replacing with 127.0.0.1 for client requests normalized_base_url=%s",
        normalized,
    )
    return normalized
