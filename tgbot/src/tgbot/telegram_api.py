from __future__ import annotations

import logging
from typing import Any

import httpx


class TelegramAPIError(RuntimeError):
    pass


logger = logging.getLogger(__name__)


class TelegramAPI:
    def __init__(self, token: str, base_url: str, timeout_seconds: float) -> None:
        self._timeout_seconds = timeout_seconds
        self._base_url = f"{base_url.rstrip('/')}/bot{token}"

    def get_updates(self, offset: int | None, timeout_seconds: int) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout_seconds, "allowed_updates": ["message"]}
        if offset is not None:
            payload["offset"] = offset
        data = self._post("getUpdates", payload)
        return data.get("result", [])

    def send_message(
        self,
        chat_id: int,
        text: str,
        reply_keyboard: list[list[str]] | None = None,
        remove_keyboard: bool = False,
        parse_mode: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if remove_keyboard:
            payload["reply_markup"] = {"remove_keyboard": True}
        elif reply_keyboard:
            payload["reply_markup"] = {
                "keyboard": [[{"text": button} for button in row] for row in reply_keyboard],
                "resize_keyboard": True,
                "one_time_keyboard": False,
            }
        self._post("sendMessage", payload)

    def set_my_commands(self, commands: list[dict[str, str]]) -> None:
        self._post("setMyCommands", {"commands": commands})

    def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}/{method}"
        logger.debug("Telegram API call method=%s", method)
        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.exception("Telegram API request failed method=%s", method)
            raise TelegramAPIError(f"Telegram API request failed for {method}: {exc}") from exc

        if not data.get("ok"):
            logger.error("Telegram API returned non-ok response method=%s", method)
            raise TelegramAPIError(f"Telegram API returned error for {method}: {data}")
        return data
