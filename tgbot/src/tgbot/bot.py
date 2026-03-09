"""
This module implements bot logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from .catalog import CatalogVerifier
from .config import Settings
from .config import get_settings
from .nlp_client import NLPClient
from .order_service import BotReply, OrderService
from .session_store import InMemorySessionStore

logger = logging.getLogger(__name__)


def run_polling() -> None:
    """
    Execute run polling.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    settings = get_settings()
    logger.info(
        "Starting Telegram bot (aiogram) polling nlp_base_url=%s poll_timeout=%s nlp_timeout=%s catalog_size=%s",
        settings.nlp_service_base_url,
        settings.telegram_poll_timeout_seconds,
        settings.nlp_request_timeout_seconds,
        len(settings.catalog_pizzas),
    )
    order_service = OrderService(
        nlp_client=NLPClient(
            base_url=settings.nlp_service_base_url,
            timeout_seconds=settings.nlp_request_timeout_seconds,
        ),
        session_store=InMemorySessionStore(),
        catalog_verifier=CatalogVerifier(settings.catalog_pizzas),
    )
    asyncio.run(_run_polling_async(settings, order_service))


async def _run_polling_async(settings: Settings, order_service: OrderService) -> None:
    """
    Execute run polling async.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - settings: input consumed by this function while processing the current request.
    - order_service: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    bot = _build_bot(settings)
    dispatcher = Dispatcher()
    request_timeout = max(1, int(settings.http_timeout_seconds))

    @dispatcher.message(F.text)
    async def on_text_message(message: Message) -> None:
        """
        Execute on text message.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - message: input consumed by this function while processing the current request.
        """
        text = message.text
        if text is None:
            return

        chat_id = message.chat.id
        logger.debug(
            "Processing incoming message chat_id=%s update_id=%s text_preview=%r",
            chat_id,
            message.message_id,
            _preview_text(text),
        )
        reply = await asyncio.to_thread(order_service.handle_message, chat_id, text)
        await _send_reply(bot, chat_id, reply, request_timeout)

    try:
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Начать новый заказ"),
                BotCommand(command="reset", description="Сбросить текущий заказ"),
                BotCommand(command="help", description="Показать подсказку"),
            ],
            request_timeout=request_timeout,
        )
        logger.debug("Telegram bot commands registered")
    except TelegramAPIError:
        logger.exception("Failed to register Telegram bot commands")

    try:
        await dispatcher.start_polling(
            bot,
            polling_timeout=settings.telegram_poll_timeout_seconds,
            allowed_updates=["message"],
            handle_as_tasks=False,
            request_timeout=request_timeout,
        )
    finally:
        await bot.session.close()


def _build_bot(settings: Settings) -> Bot:
    """
    Execute build bot.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - settings: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    api_server = TelegramAPIServer.from_base(settings.telegram_api_base_url)
    session = AiohttpSession(api=api_server)
    return Bot(token=settings.telegram_bot_token, session=session)


async def _send_reply(bot: Bot, chat_id: int, reply: BotReply, request_timeout: int) -> None:
    """
    Execute send reply.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - bot: input consumed by this function while processing the current request.
    - chat_id: input consumed by this function while processing the current request.
    - reply: input consumed by this function while processing the current request.
    - request_timeout: input consumed by this function while processing the current request.
    """
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=reply.text,
            parse_mode=reply.parse_mode,
            reply_markup=_reply_markup(reply),
            request_timeout=request_timeout,
        )
        logger.debug(
            "Sent reply chat_id=%s remove_keyboard=%s has_keyboard=%s",
            chat_id,
            reply.remove_keyboard,
            bool(reply.reply_keyboard),
        )
    except TelegramAPIError:
        logger.exception("Failed to send Telegram reply chat_id=%s", chat_id)


def _reply_markup(reply: BotReply) -> ReplyKeyboardMarkup | ReplyKeyboardRemove | None:
    """
    Execute reply markup.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - reply: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    if reply.remove_keyboard:
        return ReplyKeyboardRemove(remove_keyboard=True)

    if not reply.reply_keyboard:
        return None

    keyboard_rows = [
        [KeyboardButton(text=button_text) for button_text in row]
        for row in reply.reply_keyboard
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


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
