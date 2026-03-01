from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from .schemas import State


class ConversationSession(BaseModel):
    state: State = Field(default_factory=State)
    awaiting_confirmation: bool = False
    editing_field: str | None = None
    checkout_step: str = "draft"


class SessionStore(Protocol):
    def get(self, chat_id: int) -> ConversationSession:
        ...

    def save(self, chat_id: int, session: ConversationSession) -> None:
        ...

    def delete(self, chat_id: int) -> None:
        ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[int, ConversationSession] = {}

    def get(self, chat_id: int) -> ConversationSession:
        session = self._sessions.get(chat_id)
        if session is None:
            return ConversationSession()
        return session.model_copy(deep=True)

    def save(self, chat_id: int, session: ConversationSession) -> None:
        self._sessions[chat_id] = session.model_copy(deep=True)

    def delete(self, chat_id: int) -> None:
        self._sessions.pop(chat_id, None)
