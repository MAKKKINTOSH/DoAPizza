"""Pydantic models exchanged between bot, NLP service and session store."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Item(BaseModel):
    """One pizza line in the order."""
    name: str
    qty: int = Field(default=1, ge=1)
    size_cm: int | None = Field(default=None, ge=1)
    variant: str | None = None
    modifiers: list[str] = Field(default_factory=list)


class TimeInfo(BaseModel):
    """Normalized time request for delivery/pickup."""
    type: Literal["asap", "by_time", "in_minutes"] | None = None
    value: str | int | None = None


class Entities(BaseModel):
    """Structured order payload extracted from user dialogue."""
    items: list[Item] = Field(default_factory=list)
    delivery_type: str | None = None
    address: str | None = None
    time: TimeInfo | None = None
    phone: str | None = None
    comment: str | None = None


class Choice(BaseModel):
    """Question that must be answered before order can proceed."""
    field: str
    options: list[str] = Field(default_factory=list)
    item_index: int | None = None
    requested_value: str | None = None


class State(BaseModel):
    """Mutable dialogue state persisted between messages."""
    entities: Entities = Field(default_factory=Entities)
    missing: list[str] = Field(default_factory=list)
    pending_choice: Choice | None = None


class ParseResponse(BaseModel):
    """NLP response consumed by the bot workflow."""
    action: Literal["READY", "ASK"]
    message: str
    entities: Entities
    missing: list[str]
    choices: Choice | None = None
    state: State
    confidence: float = 0.0
