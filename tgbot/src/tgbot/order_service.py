from __future__ import annotations

from dataclasses import dataclass
import html
import logging
import re

from .catalog import CatalogVerifier
from .nlp_client import NLPClientError, NLPClientProtocol
from .schemas import Choice, Entities, Item, ParseResponse, State, TimeInfo
from .session_store import SessionStore

START_COMMANDS = {"/start", "start", "/help", "help"}
RESET_COMMANDS = {"/reset", "сбросить заказ", "начать заново"}
PROCEED_COMMANDS = {"все выбрал", "всё выбрал", "готово", "дальше", "продолжить"}
ADD_MORE_COMMANDS = {"хочу еще заказать", "хочу ещё заказать", "добавить еще", "добавить ещё"}
BACK_COMMANDS = {"назад", "вернуться назад"}
CONFIRM_COMMANDS = {"подтвердить заказ", "подтвердить", "оформить заказ", "да"}
CANCEL_COMMANDS = {"отменить заказ", "отмена"}
EDIT_ITEMS_COMMANDS = {"изменить пиццы", "изменить состав", "изменить заказ"}
EDIT_ADDRESS_COMMANDS = {"изменить адрес"}
EDIT_PHONE_COMMANDS = {"изменить телефон"}
EDIT_TIME_COMMANDS = {"изменить время"}
EDIT_COMMENT_COMMANDS = {"изменить комментарий"}
FREEFORM_EDIT_MARKERS = (
    "еще",
    "ещё",
    "добав",
    "убери",
    "удали",
    "замени",
    "вместо",
    "без ",
    "измени",
    "исправ",
)

DRAFT_KEYBOARD = [
    ["Все выбрал"],
    ["Сбросить заказ"],
]
CONFIRM_KEYBOARD = [
    ["Подтвердить заказ"],
    ["Изменить пиццы", "Изменить адрес"],
    ["Изменить телефон", "Изменить время"],
    ["Изменить комментарий", "Хочу еще заказать"],
    ["Отменить заказ"],
]
RESET_KEYBOARD = [["Сбросить заказ"]]
POST_READY_KEYBOARD = CONFIRM_KEYBOARD
CHECKOUT_STEP_SEQUENCE = ["delivery_type", "address", "phone", "time", "confirm"]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BotReply:
    text: str
    reply_keyboard: list[list[str]] | None = None
    remove_keyboard: bool = False
    parse_mode: str | None = "HTML"


class OrderService:
    def __init__(
        self,
        nlp_client: NLPClientProtocol,
        session_store: SessionStore,
        catalog_verifier: CatalogVerifier,
    ) -> None:
        self._nlp_client = nlp_client
        self._session_store = session_store
        self._catalog_verifier = catalog_verifier

    def handle_message(self, chat_id: int, text: str) -> BotReply:
        stripped = text.strip()
        normalized = stripped.lower()
        logger.debug("Handling message chat_id=%s text_preview=%r", chat_id, self._preview_text(stripped))
        if not stripped:
            logger.info("Ignoring empty message chat_id=%s", chat_id)
            return BotReply(self._section("Что хотите заказать?", "Напишите заказ свободно. Например: две пепперони 30 см с доставкой."))

        if normalized in START_COMMANDS:
            self._session_store.delete(chat_id)
            logger.info("Started new dialog chat_id=%s", chat_id)
            return BotReply(
                self._section(
                    "Новый заказ",
                    "Я помогу оформить заказ как оператор.\n\n"
                    "Сначала спокойно соберем заказ. Когда все выберете, нажмите «Все выбрал» и перейдем к оформлению.",
                ),
                reply_keyboard=DRAFT_KEYBOARD,
                remove_keyboard=False,
            )

        if normalized in RESET_COMMANDS:
            self._session_store.delete(chat_id)
            logger.info("Reset current order chat_id=%s", chat_id)
            return BotReply(
                self._section("Заказ сброшен", "Напишите новый заказ одним сообщением или по шагам."),
                reply_keyboard=DRAFT_KEYBOARD,
            )

        session = self._session_store.get(chat_id)
        logger.debug(
            "Loaded session chat_id=%s items=%s missing=%s awaiting_confirmation=%s editing_field=%s checkout_step=%s",
            chat_id,
            len(session.state.entities.items),
            len(session.state.missing),
            session.awaiting_confirmation,
            session.editing_field,
            session.checkout_step,
        )

        if session.editing_field:
            return self._handle_manual_edit(chat_id, session, stripped)

        if normalized in ADD_MORE_COMMANDS and session.checkout_step != "draft":
            session.checkout_step = "draft"
            session.awaiting_confirmation = False
            self._session_store.save(chat_id, session)
            logger.info("Returned to draft step chat_id=%s", chat_id)
            return BotReply(
                self._section(
                    "Продолжим заказ",
                    f"{self._format_order_summary(session.state.entities, include_heading=False)}\n\n"
                    "Напишите, что еще добавить или изменить.",
                ),
                reply_keyboard=self._draft_keyboard(session.state),
            )

        if normalized in BACK_COMMANDS and session.checkout_step != "draft":
            return self._go_checkout_back(chat_id, session)

        if session.checkout_step == "draft" and normalized in PROCEED_COMMANDS:
            return self._begin_checkout(chat_id, session)

        if session.awaiting_confirmation and normalized in CONFIRM_COMMANDS:
            summary = self._format_order_summary(session.state.entities)
            self._session_store.delete(chat_id)
            logger.info("Order confirmed chat_id=%s items=%s", chat_id, len(session.state.entities.items))
            return BotReply(
                self._section("Заказ подтвержден", f"{summary}\n\nЗаказ передан в обработку."),
                remove_keyboard=True,
            )

        if session.awaiting_confirmation and normalized in CANCEL_COMMANDS:
            self._session_store.delete(chat_id)
            logger.info("Order canceled chat_id=%s", chat_id)
            return BotReply(
                self._section("Заказ отменен", "Если захотите оформить новый, просто напишите сообщение."),
                remove_keyboard=True,
            )

        if session.awaiting_confirmation and normalized in EDIT_ITEMS_COMMANDS:
            session.awaiting_confirmation = False
            session.checkout_step = "draft"
            self._session_store.save(chat_id, session)
            logger.info("Entered item editing mode chat_id=%s", chat_id)
            return BotReply(
                self._section(
                    "Редактирование заказа",
                    "Напишите, что изменить. Например: замени пепперони на маргариту, убери грибы или добавь еще одну 4 сыра.",
                )
                + "\n\n"
                + self._format_draft(session.state.entities),
                reply_keyboard=self._draft_keyboard(session.state),
            )

        if session.awaiting_confirmation and normalized in EDIT_ADDRESS_COMMANDS:
            return self._begin_manual_edit(chat_id, session, "address", "Напишите новый адрес доставки или самовывоза.")

        if session.awaiting_confirmation and normalized in EDIT_PHONE_COMMANDS:
            return self._begin_manual_edit(chat_id, session, "phone", "Напишите новый номер телефона.")

        if session.awaiting_confirmation and normalized in EDIT_TIME_COMMANDS:
            return self._begin_manual_edit(chat_id, session, "time", "Напишите новое время. Например: 'как можно скорее', 'к 19:30' или 'через 40 минут'.")

        if session.awaiting_confirmation and normalized in EDIT_COMMENT_COMMANDS:
            return self._begin_manual_edit(chat_id, session, "comment", "Напишите новый комментарий к заказу. Если комментарий не нужен, напишите 'без комментария'.")

        if session.awaiting_confirmation and self._looks_like_freeform_edit(normalized):
            session.awaiting_confirmation = False
            session.checkout_step = "draft"
            self._session_store.save(chat_id, session)
            logger.info("Detected freeform edit while awaiting confirmation chat_id=%s", chat_id)

        if session.checkout_step in {"delivery_type", "address", "phone", "time"} and self._looks_like_freeform_edit(normalized):
            logger.info("Prompting explicit return to draft chat_id=%s step=%s", chat_id, session.checkout_step)
            return BotReply(
                self._section(
                    "Сейчас оформляем заказ",
                    "Если хотите добавить или изменить пиццу, нажмите «Хочу еще заказать».\n"
                    "Потом вернемся к оформлению автоматически.",
                ),
                reply_keyboard=self._checkout_keyboard(session.checkout_step),
            )

        pending_choice_reply = self._try_apply_draft_pending_choice(chat_id, session, stripped)
        if pending_choice_reply is not None:
            return pending_choice_reply

        parse_state = self._prepare_state_for_parse(session)
        try:
            parse_result = self._nlp_client.parse(stripped, parse_state)
        except NLPClientError:
            logger.exception("Failed to parse user message via NLP chat_id=%s", chat_id)
            fallback_reply = self._try_start_order_without_nlp(chat_id, session, stripped)
            if fallback_reply is not None:
                logger.warning("Recovered order start without NLP chat_id=%s", chat_id)
                return fallback_reply
            return BotReply(
                self._section(
                    self._nlp_timeout_title(session.state),
                    self._nlp_timeout_body(session.state),
                )
            )

        checked_result, unknown_items = self._apply_catalog_check(parse_result)
        if session.checkout_step == "draft":
            checked_result = self._adapt_parse_result_for_draft(checked_result)
        logger.info(
            "Order state updated chat_id=%s action=%s items=%s missing=%s has_choice=%s unknown_items=%s",
            chat_id,
            checked_result.action,
            len(checked_result.entities.items),
            len(checked_result.missing),
            checked_result.choices is not None,
            len(unknown_items),
        )
        session.state = checked_result.state

        if unknown_items:
            session.awaiting_confirmation = False
            self._session_store.save(chat_id, session)
            logger.warning("Catalog rejected items chat_id=%s items=%s", chat_id, ", ".join(unknown_items))
            return BotReply(
                self._build_unknown_items_message(unknown_items, checked_result.state),
                reply_keyboard=self._keyboard_for_session(session, checked_result),
            )

        if session.checkout_step == "draft":
            session.awaiting_confirmation = False
            self._session_store.save(chat_id, session)
            return BotReply(
                self._build_draft_reply(checked_result),
                reply_keyboard=self._keyboard_for_session(session, checked_result),
            )

        return self._handle_checkout_progress(chat_id, session, checked_result)

    def _apply_catalog_check(self, parse_result: ParseResponse) -> tuple[ParseResponse, list[str]]:
        checked = self._catalog_verifier.check_state(parse_result.state)
        updated = parse_result.model_copy(deep=True)
        updated.state = checked.state
        updated.entities = checked.state.entities
        updated.missing = checked.state.missing
        updated.choices = checked.state.pending_choice
        updated.message = self._normalize_message_after_catalog(updated)
        if checked.unknown_items:
            updated.action = "ASK"
            updated.message = self._build_unknown_items_message(checked.unknown_items, checked.state)
        elif not checked.state.entities.items:
            updated.action = "ASK"
            if "items" not in updated.missing:
                updated.missing = ["items", *updated.missing]
                updated.state.missing = updated.missing
            updated.message = "Не вижу ни одной пиццы в заказе. Напишите, какую пиццу хотите заказать."
        return updated, checked.unknown_items

    def _prepare_state_for_parse(self, session) -> State:
        prepared = session.state.model_copy(deep=True)
        expected_field = self._current_checkout_field(session)
        if expected_field == "delivery_type":
            prepared.pending_choice = Choice(field="delivery_type", options=["Доставка", "Самовывоз"])
            prepared.missing = ["delivery_type"]
        elif expected_field in {"address", "phone", "time"}:
            prepared.pending_choice = None
            prepared.missing = [expected_field]
        return prepared

    def _adapt_parse_result_for_draft(self, parse_result: ParseResponse) -> ParseResponse:
        updated = parse_result.model_copy(deep=True)
        if updated.choices and updated.choices.field in {"size_cm", "variant", "modifiers"}:
            updated.action = "ASK"
            updated.missing = [updated.choices.field]
            updated.state.missing = updated.missing
            return updated

        updated.choices = None
        updated.state.pending_choice = None
        updated.missing = []
        updated.state.missing = []
        updated.action = "ASK"
        if not updated.entities.items:
            updated.message = "Напишите, какую пиццу хотите заказать."
        else:
            updated.message = ""
        return updated

    def _build_draft_reply(self, parse_result: ParseResponse) -> str:
        if parse_result.choices and parse_result.choices.field in {"size_cm", "variant", "modifiers"}:
            return self._build_progress_message(parse_result.message, parse_result.entities)

        if not parse_result.entities.items:
            return self._section("Соберем заказ", "Напишите, какую пиццу хотите заказать.")

        return self._section(
            "Сейчас в заказе",
            f"{self._format_order_summary(parse_result.entities, include_heading=False)}\n\n"
            "Можно добавить еще пиццу или поправить состав.\n"
            "Когда все выбрано, нажмите «Все выбрал».",
        )

    def _try_apply_draft_pending_choice(self, chat_id: int, session, text: str) -> BotReply | None:
        if session.checkout_step != "draft" or session.state.pending_choice is None:
            return None

        pending_choice = session.state.pending_choice
        if pending_choice.field not in {"size_cm", "variant", "modifiers"}:
            return None

        selected = self._match_choice_option(text, pending_choice.options)
        if selected is None:
            return None

        updated_state = session.state.model_copy(deep=True)
        self._apply_pending_choice_value(updated_state, pending_choice, selected)
        updated_state.pending_choice = None
        updated_state.missing = [field for field in updated_state.missing if field != pending_choice.field]
        updated_state = self._advance_draft_choice_state(updated_state)

        parse_result = ParseResponse(
            action="ASK",
            message="",
            entities=updated_state.entities,
            missing=updated_state.missing,
            choices=updated_state.pending_choice,
            state=updated_state,
            confidence=1.0,
        )
        parse_result.message = self._normalize_message_after_catalog(parse_result)

        session.state = updated_state
        session.awaiting_confirmation = False
        self._session_store.save(chat_id, session)
        logger.info("Applied pending draft choice locally chat_id=%s field=%s", chat_id, pending_choice.field)
        return BotReply(
            self._build_draft_reply(parse_result),
            reply_keyboard=self._keyboard_for_session(session, parse_result),
        )

    def _match_choice_option(self, text: str, options: list[str]) -> str | None:
        stripped = text.strip()
        if not stripped:
            return None

        if stripped.isdigit():
            index = int(stripped) - 1
            if 0 <= index < len(options):
                return options[index]

        normalized = self._normalize_choice_text(stripped)
        for option in options:
            if normalized == self._normalize_choice_text(option):
                return option

        digits = re.findall(r"\d+", stripped)
        if digits:
            for option in options:
                if re.findall(r"\d+", option) == digits:
                    return option

        if self._is_skip_choice_text(stripped):
            for option in options:
                if self._is_skip_choice_text(option):
                    return option
        return None

    def _apply_pending_choice_value(self, state: State, choice: Choice, selected: str) -> None:
        if choice.field not in {"size_cm", "variant", "modifiers"} or not state.entities.items:
            return

        item_index = choice.item_index if choice.item_index is not None else len(state.entities.items) - 1
        item_index = max(0, min(item_index, len(state.entities.items) - 1))
        item = state.entities.items[item_index]

        if choice.field == "size_cm":
            digits = re.findall(r"\d+", selected)
            if digits:
                item.size_cm = int(digits[0])
            return

        if choice.field == "variant":
            item.variant = selected
            return

        if self._is_skip_choice_text(selected):
            return
        if not any(self._normalize_choice_text(existing) == self._normalize_choice_text(selected) for existing in item.modifiers):
            item.modifiers.append(selected)

    def _advance_draft_choice_state(self, state: State) -> State:
        updated = state.model_copy(deep=True)
        if updated.pending_choice is not None:
            return updated

        for index, item in enumerate(updated.entities.items):
            if item.size_cm is not None:
                continue
            updated.pending_choice = Choice(
                field="size_cm",
                options=["25 см", "30 см", "35 см"],
                item_index=index,
            )
            updated.missing = ["size_cm", *[field for field in updated.missing if field != "size_cm"]]
            return updated

        updated.missing = [field for field in updated.missing if field not in {"size_cm", "variant", "modifiers"}]
        return updated

    def _keyboard_for_session(self, session, parse_result: ParseResponse | None = None) -> list[list[str]] | None:
        if session.checkout_step == "confirm":
            return POST_READY_KEYBOARD
        if session.checkout_step == "draft":
            if parse_result and parse_result.choices and parse_result.choices.field in {"size_cm", "variant", "modifiers"}:
                return [[option] for option in parse_result.choices.options] + RESET_KEYBOARD
            return self._draft_keyboard(session.state)
        return self._checkout_keyboard(session.checkout_step, parse_result)

    def _draft_keyboard(self, state: State) -> list[list[str]]:
        if state.entities.items:
            return DRAFT_KEYBOARD
        return RESET_KEYBOARD

    def _begin_checkout(self, chat_id: int, session) -> BotReply:
        if not session.state.entities.items:
            return BotReply(
                self._section("Сначала выберем пиццу", "Напишите, какую пиццу хотите заказать."),
                reply_keyboard=self._draft_keyboard(session.state),
            )

        if session.state.pending_choice and session.state.pending_choice.field in {"size_cm", "variant", "modifiers"}:
            return BotReply(
                self._build_progress_message("Сначала закончим с текущей пиццей.", session.state.entities),
                reply_keyboard=self._keyboard_for_session(session, ParseResponse(
                    action="ASK",
                    message="",
                    entities=session.state.entities,
                    missing=session.state.missing,
                    choices=session.state.pending_choice,
                    state=session.state,
                    confidence=0.0,
                )),
            )

        session.checkout_step = self._determine_next_checkout_step(session.state)
        session.awaiting_confirmation = session.checkout_step == "confirm"
        self._session_store.save(chat_id, session)
        logger.info("Checkout started chat_id=%s step=%s", chat_id, session.checkout_step)
        return self._reply_for_checkout_step(session)

    def _reply_for_checkout_step(self, session) -> BotReply:
        if session.checkout_step == "confirm":
            return BotReply(
                self._section(
                    "Проверьте заказ",
                    f"{self._format_order_summary(session.state.entities)}\n\n"
                    "Если все верно, нажмите «Подтвердить заказ».\n"
                    "Если нужно исправить, выберите пункт ниже.",
                ),
                reply_keyboard=POST_READY_KEYBOARD,
            )

        prompt = self._checkout_prompt(session.checkout_step, session.state)
        return BotReply(
            self._section("Оформление заказа", f"{self._format_order_summary(session.state.entities, include_heading=False)}\n\n{prompt}"),
            reply_keyboard=self._checkout_keyboard(session.checkout_step),
        )

    def _handle_checkout_progress(self, chat_id: int, session, parse_result: ParseResponse) -> BotReply:
        previous_step = session.checkout_step
        session.state = parse_result.state
        session.checkout_step = self._determine_next_checkout_step(session.state)
        session.awaiting_confirmation = session.checkout_step == "confirm"
        self._session_store.save(chat_id, session)
        logger.info("Checkout progress chat_id=%s next_step=%s", chat_id, session.checkout_step)

        if session.checkout_step == previous_step and parse_result.message:
            return BotReply(
                self._section(
                    "Оформление заказа",
                    f"{self._format_order_summary(session.state.entities, include_heading=False)}\n\n{html.escape(parse_result.message)}",
                ),
                reply_keyboard=self._checkout_keyboard(session.checkout_step, parse_result),
            )

        return self._reply_for_checkout_step(session)

    def _determine_next_checkout_step(self, state: State) -> str:
        entities = state.entities
        if not entities.delivery_type:
            return "delivery_type"
        if entities.delivery_type.strip().lower() in {"delivery", "доставка"} and not entities.address:
            return "address"
        if not entities.phone:
            return "phone"
        if not entities.time:
            return "time"
        return "confirm"

    def _current_checkout_field(self, session) -> str | None:
        if session.checkout_step in {"delivery_type", "address", "phone", "time"}:
            return session.checkout_step
        return None

    def _go_checkout_back(self, chat_id: int, session) -> BotReply:
        if session.checkout_step == "confirm":
            session.checkout_step = "time"
        elif session.checkout_step == "time":
            session.checkout_step = "phone"
        elif session.checkout_step == "phone":
            if session.state.entities.delivery_type and session.state.entities.delivery_type.strip().lower() in {"delivery", "доставка"}:
                session.checkout_step = "address"
            else:
                session.checkout_step = "delivery_type"
        elif session.checkout_step == "address":
            session.checkout_step = "delivery_type"
        elif session.checkout_step == "delivery_type":
            session.checkout_step = "draft"
            session.awaiting_confirmation = False
            self._session_store.save(chat_id, session)
            return BotReply(
                self._section(
                    "Вернулись к заказу",
                    f"{self._format_order_summary(session.state.entities, include_heading=False)}\n\n"
                    "Можно добавить еще пиццу или изменить состав.",
                ),
                reply_keyboard=self._draft_keyboard(session.state),
            )

        session.awaiting_confirmation = session.checkout_step == "confirm"
        self._session_store.save(chat_id, session)
        return self._reply_for_checkout_step(session)

    def _checkout_prompt(self, step: str, state: State) -> str:
        if step == "delivery_type":
            return "Как получить заказ?"
        if step == "address":
            return "Куда доставить заказ? Напишите адрес полностью."
        if step == "phone":
            return "Укажите номер телефона для связи."
        if step == "time":
            return "Когда вам удобно получить заказ? Например: сейчас, к 19:30 или через 40 минут."
        return "Проверьте заказ."

    def _checkout_keyboard(self, step: str, parse_result: ParseResponse | None = None) -> list[list[str]]:
        rows: list[list[str]] = []
        if step == "delivery_type":
            rows.append(["Доставка", "Самовывоз"])
        rows.append(["Хочу еще заказать"])
        rows.append(["Назад", "Сбросить заказ"])
        return rows

    def _build_unknown_items_message(self, unknown_items: list[str], state: State) -> str:
        names = ", ".join(html.escape(value) for value in unknown_items)
        preserved = ""
        if state.entities.items:
            preserved = "\nОстальное в заказе я сохранил."
        elif self._has_non_item_details(state.entities):
            preserved = "\nАдрес и остальные детали тоже сохранил."
        header = self._section(
            "Такой пиццы не нашел",
            f"Не вижу в каталоге: {names}.\n"
            "Напишите другое название или поправьте заказ."
            f"{preserved}",
        )
        return header + self._append_draft_if_needed(state.entities)

    def _build_reply_keyboard(self, parse_result: ParseResponse) -> list[list[str]] | None:
        if parse_result.choices and parse_result.choices.options:
            return [[option] for option in parse_result.choices.options] + RESET_KEYBOARD
        return RESET_KEYBOARD

    def _build_progress_message(self, message: str, entities: Entities) -> str:
        safe_message = html.escape(message)
        if not self._has_any_draft(entities):
            return self._section("Уточню один момент", safe_message)
        return self._format_draft(entities) + "\n\n" + safe_message

    def _append_draft_if_needed(self, entities: Entities) -> str:
        if not self._has_any_draft(entities):
            return ""
        return f"\n\n{self._format_draft(entities)}"

    def _format_draft(self, entities: Entities) -> str:
        return self._section("Сейчас в заказе", self._format_order_summary(entities, include_heading=False))

    def _format_order_summary(self, entities: Entities, include_heading: bool = True) -> str:
        lines: list[str] = []
        if include_heading:
            lines.append("<b>Состав:</b>")

        if entities.items:
            for index, item in enumerate(entities.items, start=1):
                lines.append(f"{index}. {self._format_item(item)}")
        else:
            lines.append("Пиццы пока не выбраны")

        if entities.delivery_type:
            lines.append(f"<b>Получение:</b> {html.escape(self._format_delivery_type(entities.delivery_type))}")
        if entities.address:
            lines.append(f"<b>Адрес:</b> {html.escape(entities.address)}")
        if entities.time:
            lines.append(f"<b>Время:</b> {html.escape(self._format_time(entities.time))}")
        if entities.phone:
            lines.append(f"<b>Телефон:</b> {html.escape(entities.phone)}")
        if entities.comment:
            lines.append(f"<b>Комментарий:</b> {html.escape(entities.comment)}")

        return "\n".join(lines)

    def _has_non_item_details(self, entities: Entities) -> bool:
        return any(
            value is not None and value != ""
            for value in [
                entities.delivery_type,
                entities.address,
                entities.time,
                entities.phone,
                entities.comment,
            ]
        )

    def _has_any_draft(self, entities: Entities) -> bool:
        return bool(entities.items) or self._has_non_item_details(entities)

    def _begin_manual_edit(
        self,
        chat_id: int,
        session,
        field: str,
        prompt: str,
    ) -> BotReply:
        session.editing_field = field
        session.awaiting_confirmation = False
        session.checkout_step = field
        self._session_store.save(chat_id, session)
        logger.info("Started manual edit chat_id=%s field=%s", chat_id, field)
        return BotReply(prompt, reply_keyboard=[["Назад", "Сбросить заказ"]])

    def _handle_manual_edit(self, chat_id: int, session, text: str) -> BotReply:
        field = session.editing_field
        session.editing_field = None
        logger.info("Applying manual edit chat_id=%s field=%s", chat_id, field)

        if field == "address":
            session.state.entities.address = text
        elif field == "phone":
            session.state.entities.phone = text
        elif field == "comment":
            session.state.entities.comment = None if text.lower() == "без комментария" else text
        elif field == "time":
            try:
                parse_result = self._nlp_client.parse(text, State())
            except NLPClientError:
                session.editing_field = field
                self._session_store.save(chat_id, session)
                logger.exception("Failed to parse manual time edit chat_id=%s", chat_id)
                return BotReply(
                    "Не удалось распознать время из-за ошибки NLP. Повторите чуть позже.",
                    reply_keyboard=RESET_KEYBOARD,
                )
            session.state.entities.time = parse_result.entities.time

        session.checkout_step = "confirm"
        session.awaiting_confirmation = True
        self._session_store.save(chat_id, session)
        logger.info("Manual edit applied chat_id=%s field=%s", chat_id, field)
        return BotReply(
            self._section(
                "Заказ обновлен",
                f"{self._format_order_summary(session.state.entities)}\n\n"
                "Проверьте итог. Если все верно, подтвердите заказ.",
            ),
            reply_keyboard=POST_READY_KEYBOARD,
        )

    def _format_item(self, item: Item) -> str:
        parts = [f"{item.qty} x {html.escape(item.name)}"]
        if item.size_cm:
            parts.append(f"{item.size_cm} см")
        if item.variant:
            parts.append(html.escape(item.variant))
        if item.modifiers:
            parts.append("дополнения: " + ", ".join(html.escape(value) for value in item.modifiers))
        return ", ".join(parts)

    def _format_time(self, time_info: TimeInfo) -> str:
        if time_info.type == "asap":
            return "как можно скорее"
        if time_info.type == "in_minutes":
            return f"через {time_info.value} минут"
        if time_info.type == "by_time":
            return str(time_info.value)
        return "не указано"

    def _format_delivery_type(self, delivery_type: str) -> str:
        normalized = delivery_type.strip().lower()
        if normalized == "delivery":
            return "доставка"
        if normalized == "pickup":
            return "самовывоз"
        return delivery_type

    def _preview_text(self, text: str, limit: int = 80) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."

    def _normalize_choice_text(self, value: str) -> str:
        return " ".join(value.strip().lower().split())

    def _is_skip_choice_text(self, value: str) -> bool:
        return self._normalize_choice_text(value) in {
            "нет",
            "не надо",
            "не нужно",
            "без",
            "пропустить",
            "никакие",
            "никаких",
            "не добавлять",
            "без добавок",
            "без топпингов",
            "без модификаторов",
        }

    def _section(self, title: str, body: str) -> str:
        return f"<b>{html.escape(title)}</b>\n{body}"

    def _looks_like_freeform_edit(self, normalized_text: str) -> bool:
        return any(marker in normalized_text for marker in FREEFORM_EDIT_MARKERS)

    def _normalize_message_after_catalog(self, parse_result: ParseResponse) -> str:
        choice = parse_result.choices
        if choice is None or choice.item_index is None:
            return parse_result.message
        if choice.item_index < 0 or choice.item_index >= len(parse_result.entities.items):
            return parse_result.message

        item = parse_result.entities.items[choice.item_index]
        if choice.field == "size_cm" and choice.requested_value is None:
            return f"Какой размер выбрать для '{item.name}'?"
        if choice.field == "modifiers":
            return f"Нужны ли добавки для '{item.name}'?"
        if choice.field == "variant":
            return f"Какой вариант выбрать для '{item.name}'?"
        return parse_result.message

    def _try_start_order_without_nlp(self, chat_id: int, session, text: str) -> BotReply | None:
        if session.state.entities.items or self._has_non_item_details(session.state.entities):
            return None

        pizza_names = self._catalog_verifier.extract_pizzas_from_text(text)
        if not pizza_names:
            return None

        recovered_state = State(
            entities=Entities(items=[Item(name=name, qty=1, size_cm=self._extract_single_size(text)) for name in pizza_names]),
            missing=[],
            pending_choice=None,
        )

        if all(item.size_cm is not None for item in recovered_state.entities.items):
            message = ""
        else:
            item_index = next(
                index for index, item in enumerate(recovered_state.entities.items) if item.size_cm is None
            )
            recovered_state.missing = ["size_cm"]
            recovered_state.pending_choice = Choice(
                field="size_cm",
                options=["25 см", "30 см", "35 см"],
                item_index=item_index,
            )
            message = f"Какой размер выбрать для '{recovered_state.entities.items[item_index].name}'?"

        session.state = recovered_state
        session.awaiting_confirmation = False
        session.checkout_step = "draft"
        self._session_store.save(chat_id, session)
        parse_result = ParseResponse(
            action="ASK",
            message=message,
            entities=recovered_state.entities,
            missing=recovered_state.missing,
            choices=recovered_state.pending_choice,
            state=recovered_state,
            confidence=0.0,
        )
        return BotReply(
            self._build_draft_reply(parse_result),
            reply_keyboard=self._keyboard_for_session(session, parse_result),
        )

    def _extract_single_size(self, text: str) -> int | None:
        matches = re.findall(r"\b(\d{2})\s*(?:см|cm|сантиметр(?:а|ов)?|сантиметров?)?\b", text.lower())
        if len(matches) != 1:
            return None
        value = int(matches[0])
        if value in {25, 30, 35}:
            return value
        return None

    def _nlp_timeout_title(self, state: State) -> str:
        if state.entities.items or self._has_non_item_details(state.entities):
            return "Не успел обработать изменение"
        return "Не успел обработать заказ"

    def _nlp_timeout_body(self, state: State) -> str:
        if state.entities.items or self._has_non_item_details(state.entities):
            return (
                "Попробуйте повторить фразу чуть короче.\n\n"
                "Например: «добавь маргариту», «убери грибы» или «измени адрес»."
            )
        return (
            "Попробуйте написать заказ чуть проще.\n\n"
            "Например: «хочу пепперони», «маргарита 30 см» или «две пиццы с собой»."
        )
