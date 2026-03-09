"""
This module implements order service logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from __future__ import annotations

from collections import Counter
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
    """
    Represents BotReply.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    text: str
    reply_keyboard: list[list[str]] | None = None
    remove_keyboard: bool = False
    parse_mode: str | None = "HTML"


class OrderService:
    """
    Represents OrderService.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    def __init__(
        self,
        nlp_client: NLPClientProtocol,
        session_store: SessionStore,
        catalog_verifier: CatalogVerifier,
    ) -> None:
        """
        Execute init.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - nlp_client: input consumed by this function while processing the current request.
        - session_store: input consumed by this function while processing the current request.
        - catalog_verifier: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        self._nlp_client = nlp_client
        self._session_store = session_store
        self._catalog_verifier = catalog_verifier

    def handle_message(self, chat_id: int, text: str) -> BotReply:
        """
        Execute handle message.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - text: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        stripped = text.strip()
        normalized = stripped.lower()
        logger.debug("Handling message chat_id=%s text_preview=%r", chat_id, self._preview_text(stripped))
        if not stripped:
            logger.debug("Ignoring empty message chat_id=%s", chat_id)
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
            logger.debug("Returned to draft step chat_id=%s", chat_id)
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
            logger.debug("Detected freeform edit while awaiting confirmation chat_id=%s", chat_id)

        if session.checkout_step in {"delivery_type", "address", "phone", "time"} and self._looks_like_freeform_edit(normalized):
            logger.debug("Prompting explicit return to draft chat_id=%s step=%s", chat_id, session.checkout_step)
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

        if session.checkout_step == "draft" and self._has_suspicious_auto_addition(
            stripped,
            session.state,
            checked_result.state,
        ):
            logger.warning("Rejected suspicious auto-addition chat_id=%s text_preview=%r", chat_id, self._preview_text(stripped))
            self._session_store.save(chat_id, session)
            return BotReply(
                self._section(
                    "Не распознал пиццу",
                    "Не понял, какую пиццу добавить. Напишите название пиццы из меню, например: «маргарита» или «пепперони».",
                )
                + self._append_draft_if_needed(session.state.entities),
                reply_keyboard=self._draft_keyboard(session.state),
            )
        logger.debug(
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
        """
        Execute apply catalog check.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - parse_result: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute prepare state for parse.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - session: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute adapt parse result for draft.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - parse_result: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        elif updated.action == "ASK" and updated.message.strip():
            updated.message = updated.message.strip()
        else:
            updated.message = ""
        return updated

    def _build_draft_reply(self, parse_result: ParseResponse) -> str:
        """
        Execute build draft reply.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - parse_result: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if parse_result.choices and parse_result.choices.field in {"size_cm", "variant", "modifiers"}:
            return self._build_progress_message(parse_result.message, parse_result.entities)

        if not parse_result.entities.items:
            return self._section("Соберем заказ", "Напишите, какую пиццу хотите заказать.")

        if parse_result.message.strip():
            return self._build_progress_message(parse_result.message, parse_result.entities)

        return self._section(
            "Сейчас в заказе",
            f"{self._format_order_summary(parse_result.entities, include_heading=False)}\n\n"
            "Можно добавить еще пиццу или поправить состав.\n"
            "Когда все выбрано, нажмите «Все выбрал».",
        )

    def _try_apply_draft_pending_choice(self, chat_id: int, session, text: str) -> BotReply | None:
        """
        Execute try apply draft pending choice.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - session: input consumed by this function while processing the current request.
        - text: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if session.checkout_step != "draft" or session.state.pending_choice is None:
            return None

        pending_choice = session.state.pending_choice
        if pending_choice.field not in {"size_cm", "variant", "modifiers"}:
            return None

        selected = self._match_choice_option(text, pending_choice.options)
        if selected is None:
            # Avoid sending unrelated free text to NLP while we are explicitly waiting for size choice.
            # Numeric answers (e.g. "27 см") are still passed to NLP so it can suggest nearest valid sizes.
            if pending_choice.field == "size_cm" and not self._is_choice_only_text(text):
                normalized_text = self._normalize_choice_text(text)
                has_edit_intent = self._looks_like_freeform_edit(normalized_text)
                mentions_catalog_pizza = bool(self._catalog_verifier.extract_pizzas_from_text(text))
                if has_edit_intent or mentions_catalog_pizza:
                    return None
                pending_result = ParseResponse(
                    action="ASK",
                    message="",
                    entities=session.state.entities,
                    missing=session.state.missing,
                    choices=pending_choice,
                    state=session.state,
                    confidence=0.0,
                )
                prompt = self._normalize_message_after_catalog(pending_result)
                return BotReply(
                    self._build_progress_message(
                        f"Сначала выберите размер из предложенных вариантов.\n{prompt}",
                        session.state.entities,
                    ),
                    reply_keyboard=self._keyboard_for_session(session, pending_result),
                )
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
        logger.debug("Applied pending draft choice locally chat_id=%s field=%s", chat_id, pending_choice.field)
        return BotReply(
            self._build_draft_reply(parse_result),
            reply_keyboard=self._keyboard_for_session(session, parse_result),
        )

    def _match_choice_option(self, text: str, options: list[str]) -> str | None:
        """
        Execute match choice option.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - text: input consumed by this function while processing the current request.
        - options: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute apply pending choice value.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - state: input consumed by this function while processing the current request.
        - choice: input consumed by this function while processing the current request.
        - selected: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute advance draft choice state.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        updated = state.model_copy(deep=True)
        updated.entities.items = self._consolidate_sized_items(updated.entities.items)
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

    def _consolidate_sized_items(self, items: list[Item]) -> list[Item]:
        """
        Execute consolidate sized items.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - items: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        consolidated: list[Item] = []
        by_key: dict[tuple[str, int, str | None, tuple[str, ...]], int] = {}
        for item in items:
            candidate = item.model_copy(deep=True)
            candidate.qty = max(candidate.qty, 1)
            if candidate.size_cm is None:
                consolidated.append(candidate)
                continue

            key = (
                self._normalize_choice_text(candidate.name),
                candidate.size_cm,
                self._normalize_choice_text(candidate.variant) if candidate.variant else None,
                tuple(sorted(self._normalize_choice_text(value) for value in candidate.modifiers)),
            )
            existing_index = by_key.get(key)
            if existing_index is None:
                by_key[key] = len(consolidated)
                consolidated.append(candidate)
                continue
            consolidated[existing_index].qty += candidate.qty
        return consolidated

    def _keyboard_for_session(self, session, parse_result: ParseResponse | None = None) -> list[list[str]] | None:
        """
        Execute keyboard for session.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - session: input consumed by this function while processing the current request.
        - parse_result: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if session.checkout_step == "confirm":
            return POST_READY_KEYBOARD
        if session.checkout_step == "draft":
            if parse_result and parse_result.choices and parse_result.choices.field in {"size_cm", "variant", "modifiers"}:
                return [[option] for option in parse_result.choices.options] + RESET_KEYBOARD
            return self._draft_keyboard(session.state)
        return self._checkout_keyboard(session.checkout_step, parse_result)

    def _draft_keyboard(self, state: State) -> list[list[str]]:
        """
        Execute draft keyboard.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if state.entities.items:
            return DRAFT_KEYBOARD
        return RESET_KEYBOARD

    def _begin_checkout(self, chat_id: int, session) -> BotReply:
        """
        Execute begin checkout.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - session: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute reply for checkout step.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - session: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute handle checkout progress.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - session: input consumed by this function while processing the current request.
        - parse_result: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        previous_step = session.checkout_step
        session.state = parse_result.state
        session.checkout_step = self._determine_next_checkout_step(session.state)
        session.awaiting_confirmation = session.checkout_step == "confirm"
        self._session_store.save(chat_id, session)
        logger.debug("Checkout progress chat_id=%s next_step=%s", chat_id, session.checkout_step)

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
        """
        Execute determine next checkout step.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute current checkout field.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - session: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if session.checkout_step in {"delivery_type", "address", "phone", "time"}:
            return session.checkout_step
        return None

    def _go_checkout_back(self, chat_id: int, session) -> BotReply:
        """
        Execute go checkout back.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - session: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute checkout prompt.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - step: input consumed by this function while processing the current request.
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute checkout keyboard.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - step: input consumed by this function while processing the current request.
        - parse_result: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        rows: list[list[str]] = []
        if step == "delivery_type":
            rows.append(["Доставка", "Самовывоз"])
        rows.append(["Хочу еще заказать"])
        rows.append(["Назад", "Сбросить заказ"])
        return rows

    def _build_unknown_items_message(self, unknown_items: list[str], state: State) -> str:
        """
        Execute build unknown items message.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - unknown_items: input consumed by this function while processing the current request.
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute build reply keyboard.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - parse_result: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if parse_result.choices and parse_result.choices.options:
            return [[option] for option in parse_result.choices.options] + RESET_KEYBOARD
        return RESET_KEYBOARD

    def _build_progress_message(self, message: str, entities: Entities) -> str:
        """
        Execute build progress message.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - message: input consumed by this function while processing the current request.
        - entities: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        safe_message = html.escape(message)
        if not self._has_any_draft(entities):
            return self._section("Уточню один момент", safe_message)
        return self._format_draft(entities) + "\n\n" + safe_message

    def _append_draft_if_needed(self, entities: Entities) -> str:
        """
        Execute append draft if needed.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - entities: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if not self._has_any_draft(entities):
            return ""
        return f"\n\n{self._format_draft(entities)}"

    def _format_draft(self, entities: Entities) -> str:
        """
        Execute format draft.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - entities: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        return self._section("Сейчас в заказе", self._format_order_summary(entities, include_heading=False))

    def _format_order_summary(self, entities: Entities, include_heading: bool = True) -> str:
        """
        Execute format order summary.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - entities: input consumed by this function while processing the current request.
        - include_heading: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute has non item details.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - entities: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute has any draft.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - entities: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        return bool(entities.items) or self._has_non_item_details(entities)

    def _begin_manual_edit(
        self,
        chat_id: int,
        session,
        field: str,
        prompt: str,
    ) -> BotReply:
        """
        Execute begin manual edit.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - session: input consumed by this function while processing the current request.
        - field: input consumed by this function while processing the current request.
        - prompt: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        session.editing_field = field
        session.awaiting_confirmation = False
        session.checkout_step = field
        self._session_store.save(chat_id, session)
        logger.info("Started manual edit chat_id=%s field=%s", chat_id, field)
        return BotReply(prompt, reply_keyboard=[["Назад", "Сбросить заказ"]])

    def _handle_manual_edit(self, chat_id: int, session, text: str) -> BotReply:
        """
        Execute handle manual edit.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - session: input consumed by this function while processing the current request.
        - text: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        field = session.editing_field
        session.editing_field = None
        logger.debug("Applying manual edit chat_id=%s field=%s", chat_id, field)

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
        """
        Execute format item.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - item: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        parts = [f"{item.qty} x {html.escape(item.name)}"]
        if item.size_cm:
            parts.append(f"{item.size_cm} см")
        if item.variant:
            parts.append(html.escape(item.variant))
        if item.modifiers:
            parts.append("дополнения: " + ", ".join(html.escape(value) for value in item.modifiers))
        return ", ".join(parts)

    def _format_time(self, time_info: TimeInfo) -> str:
        """
        Execute format time.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - time_info: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if time_info.type == "asap":
            return "как можно скорее"
        if time_info.type == "in_minutes":
            return f"через {time_info.value} минут"
        if time_info.type == "by_time":
            return str(time_info.value)
        return "не указано"

    def _format_delivery_type(self, delivery_type: str) -> str:
        """
        Execute format delivery type.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - delivery_type: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        normalized = delivery_type.strip().lower()
        if normalized == "delivery":
            return "доставка"
        if normalized == "pickup":
            return "самовывоз"
        return delivery_type

    def _preview_text(self, text: str, limit: int = 80) -> str:
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

    def _normalize_choice_text(self, value: str) -> str:
        """
        Execute normalize choice text.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - value: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        return " ".join(value.strip().lower().split())

    def _is_skip_choice_text(self, value: str) -> bool:
        """
        Execute is skip choice text.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - value: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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

    def _is_choice_only_text(self, text: str) -> bool:
        """
        Execute is choice only text.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - text: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        stripped = text.strip()
        if not stripped:
            return True
        if self._is_skip_choice_text(stripped):
            return True
        if re.fullmatch(r"\d+", stripped):
            return True
        if re.fullmatch(r"\d+\s*(см|cm)?", stripped, flags=re.IGNORECASE):
            return True
        return False

    def _section(self, title: str, body: str) -> str:
        """
        Execute section.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - title: input consumed by this function while processing the current request.
        - body: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        return f"<b>{html.escape(title)}</b>\n{body}"

    def _looks_like_freeform_edit(self, normalized_text: str) -> bool:
        """
        Execute looks like freeform edit.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - normalized_text: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        return any(marker in normalized_text for marker in FREEFORM_EDIT_MARKERS)

    def _has_suspicious_auto_addition(self, text: str, before: State, after: State) -> bool:
        """
        Execute has suspicious auto addition.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - text: input consumed by this function while processing the current request.
        - before: input consumed by this function while processing the current request.
        - after: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        before_qty_by_name: Counter[str] = Counter()
        for item in before.entities.items:
            name_key = self._normalize_choice_text(item.name)
            before_qty_by_name[name_key] += max(item.qty, 1)

        after_qty_by_name: Counter[str] = Counter()
        for item in after.entities.items:
            name_key = self._normalize_choice_text(item.name)
            after_qty_by_name[name_key] += max(item.qty, 1)

        if sum(after_qty_by_name.values()) <= sum(before_qty_by_name.values()):
            return False

        mentioned_catalog = self._catalog_verifier.extract_pizzas_from_text(text)
        if mentioned_catalog:
            return False

        normalized = self._normalize_choice_text(text)
        duplicate_markers = ("еще", "ещё", "добавь еще", "добавь ещё", "еще одну", "ещё одну")
        if any(marker in normalized for marker in duplicate_markers):
            # Allow "add one more" only when NLP duplicates an already existing pizza.
            for name, qty in after_qty_by_name.items():
                if qty > before_qty_by_name.get(name, 0) and name not in before_qty_by_name:
                    return True
            return False

        return True

    def _normalize_message_after_catalog(self, parse_result: ParseResponse) -> str:
        """
        Execute normalize message after catalog.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - parse_result: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        choice = parse_result.choices
        if choice is None or choice.item_index is None:
            return parse_result.message
        if choice.item_index < 0 or choice.item_index >= len(parse_result.entities.items):
            return parse_result.message

        item = parse_result.entities.items[choice.item_index]
        position = choice.item_index + 1
        if choice.field == "size_cm" and choice.requested_value is None:
            return f"Какой размер выбрать для позиции {position} ('{item.name}')?"
        if choice.field == "modifiers":
            return f"Нужны ли добавки для позиции {position} ('{item.name}')?"
        if choice.field == "variant":
            return f"Какой вариант выбрать для позиции {position} ('{item.name}')?"
        return parse_result.message

    def _try_start_order_without_nlp(self, chat_id: int, session, text: str) -> BotReply | None:
        """
        Execute try start order without nlp.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - chat_id: input consumed by this function while processing the current request.
        - session: input consumed by this function while processing the current request.
        - text: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
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
        """
        Execute extract single size.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - text: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        matches = re.findall(r"\b(\d{2})\s*(?:см|cm|сантиметр(?:а|ов)?|сантиметров?)?\b", text.lower())
        if len(matches) != 1:
            return None
        value = int(matches[0])
        if value in {25, 30, 35}:
            return value
        return None

    def _nlp_timeout_title(self, state: State) -> str:
        """
        Execute nlp timeout title.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if state.entities.items or self._has_non_item_details(state.entities):
            return "Не успел обработать изменение"
        return "Не успел обработать заказ"

    def _nlp_timeout_body(self, state: State) -> str:
        """
        Execute nlp timeout body.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        if state.entities.items or self._has_non_item_details(state.entities):
            return (
                "Попробуйте повторить фразу чуть короче.\n\n"
                "Например: «добавь маргариту», «убери грибы» или «измени адрес»."
            )
        return (
            "Попробуйте написать заказ чуть проще.\n\n"
            "Например: «хочу пепперони», «маргарита 30 см» или «две пиццы с собой»."
        )
