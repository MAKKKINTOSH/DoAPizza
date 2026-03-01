from __future__ import annotations

import logging
import time

from .catalog import CatalogVerifier
from .config import get_settings
from .nlp_client import NLPClient
from .order_service import OrderService
from .session_store import InMemorySessionStore
from .telegram_api import TelegramAPI, TelegramAPIError

logger = logging.getLogger(__name__)


def run_polling() -> None:
    settings = get_settings()
    logger.info(
        "Starting Telegram bot polling nlp_base_url=%s poll_timeout=%s nlp_timeout=%s catalog_size=%s",
        settings.nlp_service_base_url,
        settings.telegram_poll_timeout_seconds,
        settings.nlp_request_timeout_seconds,
        len(settings.catalog_pizzas),
    )
    telegram_api = TelegramAPI(
        token=settings.telegram_bot_token,
        base_url=settings.telegram_api_base_url,
        timeout_seconds=settings.http_timeout_seconds,
    )
    order_service = OrderService(
        nlp_client=NLPClient(
            base_url=settings.nlp_service_base_url,
            timeout_seconds=settings.nlp_request_timeout_seconds,
        ),
        session_store=InMemorySessionStore(),
        catalog_verifier=CatalogVerifier(settings.catalog_pizzas),
    )

    try:
        telegram_api.set_my_commands(
            [
                {"command": "start", "description": "Начать новый заказ"},
                {"command": "reset", "description": "Сбросить текущий заказ"},
                {"command": "help", "description": "Показать подсказку"},
            ]
        )
        logger.info("Telegram bot commands registered")
    except TelegramAPIError:
        logger.exception("Failed to register Telegram bot commands")
        pass

    offset: int | None = None
    backoff_seconds = 1.0

    while True:
        try:
            updates = telegram_api.get_updates(
                offset=offset,
                timeout_seconds=settings.telegram_poll_timeout_seconds,
            )
            backoff_seconds = 1.0
        except TelegramAPIError:
            logger.exception("Failed to fetch Telegram updates; backing off for %.1fs", backoff_seconds)
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 15.0)
            continue

        if updates:
            logger.info("Received Telegram updates count=%s", len(updates))

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message")
            if not message:
                logger.debug("Skipping non-message update update_id=%s", update.get("update_id"))
                continue

            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            text = message.get("text")
            if chat_id is None or text is None:
                logger.debug("Skipping message without chat_id/text update_id=%s", update.get("update_id"))
                continue

            logger.debug(
                "Processing incoming message chat_id=%s update_id=%s text_preview=%r",
                chat_id,
                update.get("update_id"),
                _preview_text(text),
            )
            reply = order_service.handle_message(chat_id, text)
            try:
                telegram_api.send_message(
                    chat_id=chat_id,
                    text=reply.text,
                    reply_keyboard=reply.reply_keyboard,
                    remove_keyboard=reply.remove_keyboard,
                    parse_mode=reply.parse_mode,
                )
                logger.info(
                    "Sent reply chat_id=%s remove_keyboard=%s has_keyboard=%s",
                    chat_id,
                    reply.remove_keyboard,
                    bool(reply.reply_keyboard),
                )
            except TelegramAPIError:
                logger.exception("Failed to send Telegram reply chat_id=%s", chat_id)
                continue


def _preview_text(text: str, limit: int = 80) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
