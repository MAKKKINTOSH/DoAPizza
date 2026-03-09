"""
This module implements schemas logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Item(BaseModel):
    """
    Represents Item.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    name: str
    qty: int = Field(default=1, ge=1)
    size_cm: int | None = Field(default=None, ge=1)
    variant: str | None = None
    modifiers: list[str] = Field(default_factory=list)


class TimeInfo(BaseModel):
    """
    Represents TimeInfo.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    type: Literal["asap", "by_time", "in_minutes"] | None = None
    value: str | int | None = None


class Entities(BaseModel):
    """
    Represents Entities.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    items: list[Item] = Field(default_factory=list)
    delivery_type: str | None = None
    address: str | None = None
    time: TimeInfo | None = None
    phone: str | None = None
    comment: str | None = None


class Choice(BaseModel):
    """
    Represents Choice.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    field: str
    options: list[str] = Field(default_factory=list)
    item_index: int | None = None
    requested_value: str | None = None

    @field_validator("options", mode="before")
    @classmethod
    def _normalize_options(cls, value: object) -> object:
        """
        Execute normalize options.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - value: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if value is None:
            return []
        if not isinstance(value, list):
            return value

        normalized: list[str] = []
        for option in value:
            if option is None:
                continue
            if isinstance(option, str):
                normalized.append(option.strip())
                continue
            normalized.append(str(option))
        return normalized

    @field_validator("requested_value", mode="before")
    @classmethod
    def _normalize_requested_value(cls, value: object) -> object:
        """
        Execute normalize requested value.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - value: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip()
        return str(value)


class EditOperation(BaseModel):
    """
    Represents EditOperation.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
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
    """
    Represents State.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    entities: Entities = Field(default_factory=Entities)
    missing: list[str] = Field(default_factory=list)
    pending_choice: Choice | None = None


class ParseRequest(BaseModel):
    """
    Represents ParseRequest.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    text: str
    state: State | None = None


class ParseResponse(BaseModel):
    """
    Represents ParseResponse.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    action: Literal["READY", "ASK"]
    message: str
    entities: Entities
    missing: list[str]
    choices: Choice | None = None
    state: State
    confidence: float = 0.0
