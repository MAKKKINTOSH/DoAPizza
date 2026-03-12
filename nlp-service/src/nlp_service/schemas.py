"""Schema contracts for NLP parser input/output and intermediate operations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Item(BaseModel):
    """One pizza line item."""
    name: str
    qty: int = Field(default=1, ge=1)
    size_cm: int | None = Field(default=None, ge=1)
    variant: str | None = None
    modifiers: list[str] = Field(default_factory=list)


class TimeInfo(BaseModel):
    """Normalized time expression."""
    type: Literal["asap", "by_time", "in_minutes"] | None = None
    value: str | int | None = None


class Entities(BaseModel):
    """Structured order fields extracted from text."""
    items: list[Item] = Field(default_factory=list)
    delivery_type: str | None = None
    address: str | None = None
    time: TimeInfo | None = None
    phone: str | None = None
    comment: str | None = None


class Choice(BaseModel):
    """Follow-up question for unresolved field."""
    field: str
    options: list[str] = Field(default_factory=list)
    item_index: int | None = None
    requested_value: str | None = None

    @field_validator("options", mode="before")
    @classmethod
    def _normalize_options(cls, value: object) -> object:
        """Normalize option list to trimmed strings."""
        if value is None:
            return []
        # If upstream already sent non-list type, let pydantic handle validation error.
        if not isinstance(value, list):
            return value

        normalized: list[str] = []
        for option in value:
            # Drop null options from partial model outputs.
            if option is None:
                continue
            if isinstance(option, str):
                # Trim spaces around user-facing option labels.
                normalized.append(option.strip())
                continue
            # Non-string values are stringified to keep schema tolerant.
            normalized.append(str(option))
        return normalized

    @field_validator("requested_value", mode="before")
    @classmethod
    def _normalize_requested_value(cls, value: object) -> object:
        """Normalize requested value to string for stable prompts."""
        if value is None:
            return None
        if isinstance(value, str):
            # Keep explicit user-provided token but trim noise.
            return value.strip()
        return str(value)


class EditOperation(BaseModel):
    """Atomic operation to mutate existing item list."""
    op: Literal["add_item", "remove_item", "replace_item", "update_item"]
    item_index: int | None = None
    item: Item | None = None
    name: str | None = None
    qty: int | None = Field(default=None, ge=1)
    size_cm: int | None = Field(default=None, ge=1)
    variant: str | None = None
    modifiers_add: list[str] = Field(default_factory=list)
    modifiers_remove: list[str] = Field(default_factory=list)
    modifiers_replace: list[str] | None = None


class State(BaseModel):
    """Conversation state passed between parser calls."""
    entities: Entities = Field(default_factory=Entities)
    missing: list[str] = Field(default_factory=list)
    pending_choice: Choice | None = None


class ParseRequest(BaseModel):
    """HTTP payload for `/v1/parse`."""
    text: str
    state: State | None = None


class ParseResponse(BaseModel):
    """Parser response returned to bot."""
    action: Literal["READY", "ASK"]
    message: str
    entities: Entities
    missing: list[str]
    choices: Choice | None = None
    state: State
    confidence: float = 0.0
