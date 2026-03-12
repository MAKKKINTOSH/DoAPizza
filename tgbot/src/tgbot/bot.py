"""Aiogram wiring: receives Telegram updates and delegates to `OrderService`."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand, KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

from .catalog import CatalogVerifier
from .catalog_sync import CatalogSync
from .config import Settings
from .config import get_settings
from .nlp_client import NLPClient
from .order_service import BotReply, OrderService
from .session_store import InMemorySessionStore

logger = logging.getLogger(__name__)


def run_polling() -> None:
    """Construct dependencies from settings and start async polling loop."""
    settings = get_settings()
    catalog_verifier = CatalogVerifier(settings.catalog_pizzas)
    catalog_sync = CatalogSync(
        api_url=settings.catalog_api_url,
        refresh_interval_seconds=settings.catalog_refresh_interval_seconds,
        http_timeout_seconds=settings.catalog_http_timeout_seconds,
        fallback_pizzas=settings.catalog_pizzas,
        on_update=lambda snapshot: catalog_verifier.update_catalog(snapshot.pizza_names),
    )
    catalog_sync.start()
    logger.info(
        "Starting Telegram bot (aiogram) polling nlp_base_url=%s poll_timeout=%s nlp_timeout=%s catalog_size=%s catalog_api_url=%s catalog_refresh=%s",
        settings.nlp_service_base_url,
        settings.telegram_poll_timeout_seconds,
        settings.nlp_request_timeout_seconds,
        len(settings.catalog_pizzas),
        settings.catalog_api_url,
        settings.catalog_refresh_interval_seconds,
    )
    # Compose all runtime dependencies once at startup.
    order_service = OrderService(
        nlp_client=NLPClient(
            base_url=settings.nlp_service_base_url,
            timeout_seconds=settings.nlp_request_timeout_seconds,
        ),
        session_store=InMemorySessionStore(),
        catalog_verifier=catalog_verifier,
    )
    try:
        asyncio.run(_run_polling_async(settings, order_service))
    finally:
        catalog_sync.stop()


async def _run_polling_async(settings: Settings, order_service: OrderService) -> None:
    """Run dispatcher and route text messages through synchronous order logic."""
    bot = _build_bot(settings)
    dispatcher = Dispatcher()
    request_timeout = max(1, int(settings.http_timeout_seconds))

    @dispatcher.message(F.text)
    async def on_text_message(message: Message) -> None:
        # Aiogram can deliver updates without text payload, ignore them here.
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
        # OrderService is sync by design; offload to thread to keep event loop responsive.
        reply = await asyncio.to_thread(order_service.handle_message, chat_id, text)
        await _send_reply(bot, chat_id, reply, request_timeout)

    try:
        # Register command hints shown in Telegram client UI.
        await bot.set_my_commands(
            [
                BotCommand(command="start", description="Начать новый заказ"),
                BotCommand(command="menu", description="Показать меню пицц"),
                BotCommand(command="reset", description="Сбросить текущий заказ"),
                BotCommand(command="help", description="Показать подсказку"),
            ],
            request_timeout=request_timeout,
        )
        logger.debug("Telegram bot commands registered")
    except TelegramAPIError:
        logger.exception("Failed to register Telegram bot commands")

    try:
        # Process updates sequentially to avoid race conditions in in-memory session store.
        await dispatcher.start_polling(
            bot,
            polling_timeout=settings.telegram_poll_timeout_seconds,
            allowed_updates=["message"],
            handle_as_tasks=False,
            request_timeout=request_timeout,
        )
    finally:
        # Ensure underlying HTTP session is always closed on shutdown/errors.
        await bot.session.close()


def _build_bot(settings: Settings) -> Bot:
    """Create `aiogram.Bot` with custom Telegram API base URL support."""
    # Custom API base is useful for local proxies or self-hosted Telegram API server.
    api_server = TelegramAPIServer.from_base(settings.telegram_api_base_url)
    session = AiohttpSession(api=api_server)
    return Bot(token=settings.telegram_bot_token, session=session)


async def _send_reply(bot: Bot, chat_id: int, reply: BotReply, request_timeout: int) -> None:
    """Safely send bot message and log failures without crashing polling."""
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
    """Build Telegram keyboard payload from service response metadata."""
    if reply.remove_keyboard:
        return ReplyKeyboardRemove(remove_keyboard=True)

    if not reply.reply_keyboard:
        return None

    keyboard_rows = [
        # Convert string matrix into Telegram button objects.
        [KeyboardButton(text=button_text) for button_text in row]
        for row in reply.reply_keyboard
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def _preview_text(text: str, limit: int = 80) -> str:
    """Compact message text for structured logs."""
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
