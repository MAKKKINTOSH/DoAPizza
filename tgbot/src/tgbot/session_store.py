"""
This module implements session store logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from .schemas import State


class ConversationSession(BaseModel):
    """
    Represents ConversationSession.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    state: State = Field(default_factory=State)
    awaiting_confirmation: bool = False
    editing_field: str | None = None
    checkout_step: str = "draft"


class SessionStore(Protocol):
    """
    Represents SessionStore.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    def get(self, chat_id: int) -> ConversationSession:
        """
        Execute get.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        ...

    def save(self, chat_id: int, session: ConversationSession) -> None:
        """
        Execute save.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - session: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        ...

    def delete(self, chat_id: int) -> None:
        """
        Execute delete.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        ...


class InMemorySessionStore:
    """
    Represents InMemorySessionStore.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    def __init__(self) -> None:
        """
        Execute init.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        self._sessions: dict[int, ConversationSession] = {}

    def get(self, chat_id: int) -> ConversationSession:
        """
        Execute get.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        session = self._sessions.get(chat_id)
        if session is None:
            return ConversationSession()
        return session.model_copy(deep=True)

    def save(self, chat_id: int, session: ConversationSession) -> None:
        """
        Execute save.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - session: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        self._sessions[chat_id] = session.model_copy(deep=True)

    def delete(self, chat_id: int) -> None:
        """
        Execute delete.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        self._sessions.pop(chat_id, None)
