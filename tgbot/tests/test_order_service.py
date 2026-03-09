"""
This module implements test order service logic for the DoAPizza project.
Detailed docstrings are intentionally verbose so each code block is easier to explain during reviews.
"""

from tgbot.catalog import CatalogVerifier
from tgbot.nlp_client import NLPClientError
from tgbot.order_service import OrderService
from tgbot.schemas import Choice, Entities, Item, ParseResponse, State, TimeInfo
from tgbot.session_store import ConversationSession, InMemorySessionStore


class FakeNLPClient:
    """
    Represents FakeNLPClient.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    def __init__(self, responses: dict[str, ParseResponse]) -> None:
        """
        Execute init.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - responses: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        self._responses = responses

    def parse(self, text: str, state: State | None) -> ParseResponse:
        """
        Execute parse.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - text: input consumed by this function while processing the current request.
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        return self._responses[text].model_copy(deep=True)


class FailingNLPClient:
    """
    Represents FailingNLPClient.
    This class-level description documents why the type exists and how it should be used by other modules.
    """
    def parse(self, text: str, state: State | None) -> ParseResponse:
        """
        Execute parse.
        This function-level documentation is intentionally explicit to simplify line-by-line explanations.

        Parameters:
        - text: input consumed by this function while processing the current request.
        - state: input consumed by this function while processing the current request.

        Returns:
        - A value derived from the current function logic and its validated inputs.
        """
        raise NLPClientError("timed out")


def build_service(responses: dict[str, ParseResponse]) -> tuple[OrderService, InMemorySessionStore]:
    """
    Execute build service.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - responses: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    store = InMemorySessionStore()
    service = OrderService(
        nlp_client=FakeNLPClient(responses),
        session_store=store,
        catalog_verifier=CatalogVerifier(
            ("Маргарита", "Пепперони", "Четыре сыра", "Гавайская", "Диабло")
        ),
    )
    return service, store


def build_service_with_client(nlp_client) -> tuple[OrderService, InMemorySessionStore]:
    """
    Execute build service with client.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Parameters:
    - nlp_client: input consumed by this function while processing the current request.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    store = InMemorySessionStore()
    service = OrderService(
        nlp_client=nlp_client,
        session_store=store,
        catalog_verifier=CatalogVerifier(
            ("Маргарита", "Пепперони", "Четыре сыра", "Гавайская", "Диабло")
        ),
    )
    return service, store


def test_start_command_resets_session() -> None:
    """
    Execute test start command resets session.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    service, _ = build_service({})

    reply = service.handle_message(1, "/start")

    assert "Новый заказ" in reply.text
    assert reply.parse_mode == "HTML"
    assert reply.reply_keyboard == [["Все выбрал"], ["Сбросить заказ"]]


def test_ask_flow_returns_choice_keyboard() -> None:
    """
    Execute test ask flow returns choice keyboard.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    state = State(
        entities=Entities(items=[Item(name="Маргарита", qty=1)]),
        missing=["size_cm"],
        pending_choice=Choice(field="size_cm", options=["25 см", "30 см"], item_index=0),
    )
    response = ParseResponse(
        action="ASK",
        message="Какой размер Маргариты?",
        entities=state.entities,
        missing=state.missing,
        choices=state.pending_choice,
        state=state,
        confidence=0.92,
    )
    service, store = build_service({"Маргарита": response})

    reply = service.handle_message(10, "Маргарита")

    assert "Сейчас в заказе" in reply.text
    assert "позиции 1" in reply.text
    assert "Маргарита" in reply.text
    assert reply.reply_keyboard == [["25 см"], ["30 см"], ["Сбросить заказ"]]
    assert store.get(10).awaiting_confirmation is False


def test_pending_size_choice_is_applied_locally_without_nlp() -> None:
    """
    Execute test pending size choice is applied locally without nlp.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    service, store = build_service_with_client(FailingNLPClient())
    store.save(
        11,
        ConversationSession(
            state=State(
                entities=Entities(items=[Item(name="Пепперони", qty=1)]),
                missing=["size_cm"],
                pending_choice=Choice(field="size_cm", options=["25 см", "30 см", "35 см"], item_index=0),
            )
        ),
    )

    reply = service.handle_message(11, "30 см")
    saved = store.get(11)

    assert "Сейчас в заказе" in reply.text
    assert "30 см" in reply.text
    assert "Все выбрал" in reply.text
    assert saved.state.entities.items[0].size_cm == 30
    assert saved.state.pending_choice is None


def test_pending_size_choice_merges_identical_sized_lines() -> None:
    """
    Execute test pending size choice merges identical sized lines.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    service, store = build_service_with_client(FailingNLPClient())
    store.save(
        111,
        ConversationSession(
            state=State(
                entities=Entities(
                    items=[
                        Item(name="Пепперони", qty=1, size_cm=30),
                        Item(name="Пепперони", qty=1, size_cm=None),
                    ]
                ),
                missing=["size_cm"],
                pending_choice=Choice(field="size_cm", options=["25 см", "30 см", "35 см"], item_index=1),
            )
        ),
    )

    service.handle_message(111, "30 см")
    saved = store.get(111)

    assert len(saved.state.entities.items) == 1
    assert saved.state.entities.items[0].name == "Пепперони"
    assert saved.state.entities.items[0].size_cm == 30
    assert saved.state.entities.items[0].qty == 2
    assert saved.state.pending_choice is None


def test_pending_size_choice_ignores_unrelated_text_without_order_mutation() -> None:
    """
    Execute test pending size choice ignores unrelated text without order mutation.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    state = State(
        entities=Entities(items=[Item(name="Пепперони", qty=1)]),
        missing=["size_cm"],
        pending_choice=Choice(field="size_cm", options=["25 см", "30 см", "35 см"], item_index=0),
    )
    response = ParseResponse(
        action="ASK",
        message="Какой размер Пепперони?",
        entities=state.entities,
        missing=state.missing,
        choices=state.pending_choice,
        state=state,
        confidence=0.9,
    )
    service, store = build_service({"пеперони": response})

    service.handle_message(12, "пеперони")
    reply = service.handle_message(12, "моцарелла")
    saved = store.get(12)

    assert "Сначала выберите размер из предложенных вариантов." in reply.text
    assert reply.reply_keyboard == [["25 см"], ["30 см"], ["35 см"], ["Сбросить заказ"]]
    assert len(saved.state.entities.items) == 1
    assert saved.state.entities.items[0].name == "Пепперони"
    assert saved.state.entities.items[0].qty == 1
    assert saved.state.entities.items[0].size_cm is None
    assert saved.state.pending_choice is not None
    assert saved.state.pending_choice.field == "size_cm"


def test_draft_preserves_ask_message_without_choices() -> None:
    """
    Execute test draft preserves ask message without choices.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    state = State(
        entities=Entities(
            items=[
                Item(name="Пепперони", qty=1, size_cm=30),
                Item(name="Пепперони", qty=1, size_cm=35),
            ]
        ),
        missing=[],
        pending_choice=None,
    )
    response = ParseResponse(
        action="ASK",
        message="Уточните номер позиции для 'Пепперони': 1, 2.",
        entities=state.entities,
        missing=[],
        choices=None,
        state=state,
        confidence=0.9,
    )
    service, _ = build_service({"убери пепперони": response})

    reply = service.handle_message(112, "убери пепперони")

    assert "Уточните номер позиции" in reply.text
    assert "Пепперони" in reply.text


def test_hallucinated_addition_without_catalog_match_is_rejected() -> None:
    """
    Execute test hallucinated addition without catalog match is rejected.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    initial_state = State(
        entities=Entities(items=[Item(name="Пепперони", qty=1)]),
        missing=["size_cm"],
        pending_choice=Choice(field="size_cm", options=["25 см", "30 см", "35 см"], item_index=0),
    )
    initial_response = ParseResponse(
        action="ASK",
        message="Какой размер Пепперони?",
        entities=initial_state.entities,
        missing=initial_state.missing,
        choices=initial_state.pending_choice,
        state=initial_state,
        confidence=0.91,
    )

    hallucinated_state = State(
        entities=Entities(items=[Item(name="Пепперони", qty=1), Item(name="Маргарита", qty=2)]),
        missing=["size_cm"],
        pending_choice=Choice(field="size_cm", options=["25 см", "30 см", "35 см"], item_index=0),
    )
    hallucinated_response = ParseResponse(
        action="ASK",
        message="Какой размер Пепперони?",
        entities=hallucinated_state.entities,
        missing=hallucinated_state.missing,
        choices=hallucinated_state.pending_choice,
        state=hallucinated_state,
        confidence=0.62,
    )

    service, store = build_service({"пеперони": initial_response, "добавь моцареллу": hallucinated_response})

    service.handle_message(13, "пеперони")
    reply = service.handle_message(13, "добавь моцареллу")
    saved = store.get(13)

    assert "Не распознал пиццу" in reply.text
    assert len(saved.state.entities.items) == 1
    assert saved.state.entities.items[0].name == "Пепперони"
    assert saved.state.entities.items[0].qty == 1
    assert saved.state.pending_choice is not None
    assert saved.state.pending_choice.field == "size_cm"


def test_hallucinated_quantity_increase_without_catalog_match_is_rejected() -> None:
    """
    Execute test hallucinated quantity increase without catalog match is rejected.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    initial_state = State(
        entities=Entities(items=[Item(name="Пепперони", qty=1)]),
        missing=["size_cm"],
        pending_choice=Choice(field="size_cm", options=["25 см", "30 см", "35 см"], item_index=0),
    )
    initial_response = ParseResponse(
        action="ASK",
        message="Какой размер Пепперони?",
        entities=initial_state.entities,
        missing=initial_state.missing,
        choices=initial_state.pending_choice,
        state=initial_state,
        confidence=0.9,
    )

    hallucinated_state = State(
        entities=Entities(items=[Item(name="Пепперони", qty=3)]),
        missing=["size_cm"],
        pending_choice=Choice(field="size_cm", options=["25 см", "30 см", "35 см"], item_index=0),
    )
    hallucinated_response = ParseResponse(
        action="ASK",
        message="Какой размер Пепперони?",
        entities=hallucinated_state.entities,
        missing=hallucinated_state.missing,
        choices=hallucinated_state.pending_choice,
        state=hallucinated_state,
        confidence=0.51,
    )

    service, store = build_service({"пеперони": initial_response, "моцарелла": hallucinated_response})

    service.handle_message(15, "пеперони")
    reply = service.handle_message(15, "моцарелла")
    saved = store.get(15)

    assert "Не распознал пиццу" in reply.text
    assert len(saved.state.entities.items) == 1
    assert saved.state.entities.items[0].name == "Пепперони"
    assert saved.state.entities.items[0].qty == 1
    assert saved.state.pending_choice is not None
    assert saved.state.pending_choice.field == "size_cm"


def test_pending_size_choice_allows_add_intent_before_size_resolution() -> None:
    """
    Execute test pending size choice allows add intent before size resolution.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    initial_state = State(
        entities=Entities(items=[Item(name="Пепперони", qty=1)]),
        missing=["size_cm"],
        pending_choice=Choice(field="size_cm", options=["25 см", "30 см", "35 см"], item_index=0),
    )
    initial_response = ParseResponse(
        action="ASK",
        message="Какой размер Пепперони?",
        entities=initial_state.entities,
        missing=initial_state.missing,
        choices=initial_state.pending_choice,
        state=initial_state,
        confidence=0.9,
    )

    add_state = State(
        entities=Entities(items=[Item(name="Пепперони", qty=1), Item(name="Маргарита", qty=1)]),
        missing=["size_cm"],
        pending_choice=Choice(field="size_cm", options=["25 см", "30 см", "35 см"], item_index=0),
    )
    add_response = ParseResponse(
        action="ASK",
        message="Какой размер Пепперони?",
        entities=add_state.entities,
        missing=add_state.missing,
        choices=add_state.pending_choice,
        state=add_state,
        confidence=0.88,
    )

    service, store = build_service({"пеперони": initial_response, "еще маргариту": add_response})

    service.handle_message(14, "пеперони")
    reply = service.handle_message(14, "еще маргариту")
    saved = store.get(14)

    assert "Сначала выберите размер из предложенных вариантов." not in reply.text
    assert len(saved.state.entities.items) == 2
    assert saved.state.entities.items[0].name == "Пепперони"
    assert saved.state.entities.items[1].name == "Маргарита"
    assert saved.state.pending_choice is not None
    assert saved.state.pending_choice.field == "size_cm"
    assert saved.state.pending_choice.item_index == 0


def test_unknown_pizza_is_blocked_by_catalog_stub() -> None:
    """
    Execute test unknown pizza is blocked by catalog stub.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    state = State(
        entities=Entities(items=[Item(name="Супер мясная", qty=1)]),
        missing=[],
        pending_choice=None,
    )
    response = ParseResponse(
        action="READY",
        message="Заказ готов.",
        entities=state.entities,
        missing=[],
        choices=None,
        state=state,
        confidence=0.81,
    )
    service, store = build_service({"хочу супер мясную": response})

    reply = service.handle_message(20, "хочу супер мясную")
    saved = store.get(20)

    assert "Не нашел в каталоге" in reply.text
    assert saved.awaiting_confirmation is False
    assert saved.state.entities.items == []
    assert saved.state.missing[0] == "items"


def test_catalog_verifier_accepts_small_typos() -> None:
    """
    Execute test catalog verifier accepts small typos.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    state = State(
        entities=Entities(items=[Item(name="Пеперони", qty=1, size_cm=25)]),
        missing=[],
        pending_choice=None,
    )
    response = ParseResponse(
        action="ASK",
        message="Как получить заказ?",
        entities=state.entities,
        missing=["delivery_type"],
        choices=None,
        state=state,
        confidence=0.8,
    )
    service, store = build_service({"пеперони 25 см": response})

    reply = service.handle_message(50, "пеперони 25 см")

    assert "Пепперони" in store.get(50).state.entities.items[0].name
    assert "Такой пиццы не нашел" not in reply.text
    assert "Все выбрал" in reply.text


def test_ready_flow_requests_confirmation_and_confirms_order() -> None:
    """
    Execute test ready flow requests confirmation and confirms order.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    entities = Entities(
        items=[Item(name="Пепперони", qty=2, size_cm=30)],
        delivery_type="delivery",
        address="ул. Пушкина, 10",
        time=TimeInfo(type="asap", value=None),
        phone="79991234567",
    )
    state = State(entities=entities, missing=[], pending_choice=None)
    response = ParseResponse(
        action="READY",
        message="Заказ готов.",
        entities=entities,
        missing=[],
        choices=None,
        state=state,
        confidence=0.96,
    )
    service, store = build_service({"2 пепперони 30 см": response})

    draft_reply = service.handle_message(30, "2 пепперони 30 см")
    ready_reply = service.handle_message(30, "Все выбрал")
    confirm_reply = service.handle_message(30, "Подтвердить заказ")

    assert "Сейчас в заказе" in draft_reply.text
    assert "Все выбрал" in draft_reply.text
    assert "Проверьте заказ" in ready_reply.text
    assert ready_reply.reply_keyboard == [
        ["Подтвердить заказ"],
        ["Изменить пиццы", "Изменить адрес"],
        ["Изменить телефон", "Изменить время"],
        ["Изменить комментарий", "Хочу еще заказать"],
        ["Отменить заказ"],
    ]
    assert "Заказ подтвержден" in confirm_reply.text
    assert store.get(30).state.entities.items == []


def test_manual_address_edit_keeps_order_and_returns_to_confirmation() -> None:
    """
    Execute test manual address edit keeps order and returns to confirmation.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    entities = Entities(
        items=[Item(name="Пепперони", qty=1, size_cm=30)],
        delivery_type="delivery",
        address="ул. Старая, 1",
        phone="79991234567",
    )
    state = State(entities=entities, missing=[], pending_choice=None)
    response = ParseResponse(
        action="READY",
        message="Заказ готов.",
        entities=entities,
        missing=[],
        choices=None,
        state=state,
        confidence=0.94,
    )
    service, store = build_service({"пепперони": response})

    service.handle_message(40, "пепперони")
    service.handle_message(40, "Все выбрал")
    prompt_reply = service.handle_message(40, "Изменить адрес")
    done_reply = service.handle_message(40, "ул. Новая, 15")

    assert "Напишите новый адрес" in prompt_reply.text
    assert "Заказ обновлен" in done_reply.text
    assert "ул. Новая, 15" in done_reply.text
    assert store.get(40).awaiting_confirmation is True


def test_freeform_edit_leaves_confirmation_mode_before_parse() -> None:
    """
    Execute test freeform edit leaves confirmation mode before parse.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    entities = Entities(
        items=[Item(name="Пепперони", qty=1, size_cm=30)],
        delivery_type="delivery",
        address="ул. Старая, 1",
        phone="79991234567",
    )
    state = State(entities=entities, missing=[], pending_choice=None)
    ready_response = ParseResponse(
        action="READY",
        message="Заказ готов.",
        entities=entities,
        missing=[],
        choices=None,
        state=state,
        confidence=0.94,
    )
    updated_entities = Entities(
        items=[Item(name="Пепперони", qty=1, size_cm=30), Item(name="Маргарита", qty=1)],
        delivery_type="delivery",
        address="ул. Старая, 1",
        phone="79991234567",
    )
    updated_state = State(
        entities=updated_entities,
        missing=["size_cm"],
        pending_choice=Choice(field="size_cm", options=["25 см", "30 см"], item_index=1),
    )
    ask_response = ParseResponse(
        action="ASK",
        message="Какой размер для Маргариты?",
        entities=updated_entities,
        missing=["size_cm"],
        choices=updated_state.pending_choice,
        state=updated_state,
        confidence=0.93,
    )
    service, store = build_service({"пепперони": ready_response, "еще маргариту хочу": ask_response})

    service.handle_message(60, "пепперони")
    service.handle_message(60, "Все выбрал")
    reply = service.handle_message(60, "еще маргариту хочу")

    assert "позиции 2" in reply.text
    assert "Маргарита" in reply.text
    assert store.get(60).awaiting_confirmation is False
    assert store.get(60).checkout_step == "draft"


def test_timeout_on_first_message_can_recover_from_catalog_text() -> None:
    """
    Execute test timeout on first message can recover from catalog text.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    service, store = build_service_with_client(FailingNLPClient())

    reply = service.handle_message(70, "мне надо пеперони")

    assert "Пепперони" in reply.text
    assert "Какой размер" in reply.text
    assert store.get(70).state.entities.items[0].name == "Пепперони"


def test_timeout_on_first_message_can_recover_from_phonetic_catalog_typo() -> None:
    """
    Execute test timeout on first message can recover from phonetic catalog typo.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    service, store = build_service_with_client(FailingNLPClient())

    reply = service.handle_message(72, "мне надо пипирони")

    assert "Пепперони" in reply.text
    assert "Какой размер" in reply.text
    assert store.get(72).state.entities.items[0].name == "Пепперони"


def test_timeout_on_first_message_uses_order_wording_not_change_wording() -> None:
    """
    Execute test timeout on first message uses order wording not change wording.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    service, _ = build_service_with_client(FailingNLPClient())

    reply = service.handle_message(71, "привет")

    assert "Не успел обработать заказ" in reply.text
    assert "изменение" not in reply.text.lower()


def test_draft_does_not_force_checkout_before_button() -> None:
    """
    Execute test draft does not force checkout before button.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    state = State(
        entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=30)]),
        missing=["delivery_type"],
        pending_choice=Choice(field="delivery_type", options=["Доставка", "Самовывоз"]),
    )
    response = ParseResponse(
        action="ASK",
        message="Как получить заказ?",
        entities=state.entities,
        missing=state.missing,
        choices=state.pending_choice,
        state=state,
        confidence=0.9,
    )
    service, store = build_service({"пепперони 30 см": response})

    reply = service.handle_message(80, "пепперони 30 см")

    assert "Как получить заказ?" not in reply.text
    assert "Все выбрал" in reply.text
    assert store.get(80).checkout_step == "draft"


def test_checkout_asks_delivery_after_proceed_button() -> None:
    """
    Execute test checkout asks delivery after proceed button.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    state = State(
        entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=30)]),
        missing=["delivery_type"],
        pending_choice=Choice(field="delivery_type", options=["Доставка", "Самовывоз"]),
    )
    response = ParseResponse(
        action="ASK",
        message="Как получить заказ?",
        entities=state.entities,
        missing=state.missing,
        choices=state.pending_choice,
        state=state,
        confidence=0.9,
    )
    service, store = build_service({"пепперони 30 см": response})

    service.handle_message(81, "пепперони 30 см")
    reply = service.handle_message(81, "Все выбрал")

    assert "Как получить заказ?" in reply.text
    assert reply.reply_keyboard == [["Доставка", "Самовывоз"], ["Хочу еще заказать"], ["Назад", "Сбросить заказ"]]
    assert store.get(81).checkout_step == "delivery_type"


def test_checkout_can_return_to_draft_with_add_more_button() -> None:
    """
    Execute test checkout can return to draft with add more button.
    This function-level documentation is intentionally explicit to simplify line-by-line explanations.

    Returns:
    - A value derived from the current function logic and its validated inputs.
    """
    state = State(
        entities=Entities(
            items=[Item(name="Пепперони", qty=1, size_cm=30)],
            delivery_type="pickup",
        ),
        missing=["phone"],
        pending_choice=None,
    )
    response = ParseResponse(
        action="ASK",
        message="Укажите номер телефона.",
        entities=state.entities,
        missing=state.missing,
        choices=None,
        state=state,
        confidence=0.9,
    )
    service, store = build_service({"пепперони 30 см": response})

    service.handle_message(82, "пепперони 30 см")
    service.handle_message(82, "Все выбрал")
    reply = service.handle_message(82, "Хочу еще заказать")

    assert "Продолжим заказ" in reply.text
    assert store.get(82).checkout_step == "draft"
