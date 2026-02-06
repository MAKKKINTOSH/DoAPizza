from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Item(BaseModel):
    name: str
    qty: int = Field(default=1, ge=1)
    size_cm: int | None = Field(default=None, ge=1)
    variant: str | None = None
    modifiers: list[str] = Field(default_factory=list)


class TimeInfo(BaseModel):
    type: Literal["asap", "by_time", "in_minutes"] | None = None
    value: str | int | None = None


class Entities(BaseModel):
    items: list[Item] = Field(default_factory=list)
    delivery_type: str | None = None
    address: str | None = None
    time: TimeInfo | None = None
    phone: str | None = None
    comment: str | None = None


class Choice(BaseModel):
    field: str
    options: list[str] = Field(default_factory=list)
    item_index: int | None = None


class State(BaseModel):
    entities: Entities = Field(default_factory=Entities)
    missing: list[str] = Field(default_factory=list)
    pending_choice: Choice | None = None


class ParseRequest(BaseModel):
    text: str
    state: State | None = None


class ParseResponse(BaseModel):
    action: Literal["READY", "ASK"]
    message: str
    entities: Entities
    missing: list[str]
    choices: Choice | None = None
    state: State
    confidence: float = 0.0