from tgbot.catalog import CatalogVerifier
from tgbot.nlp_client import NLPClientError
from tgbot.order_service import OrderService
from tgbot.schemas import Choice, Entities, Item, ParseResponse, State, TimeInfo
from tgbot.session_store import ConversationSession, InMemorySessionStore


class FakeNLPClient:
    def __init__(self, responses: dict[str, ParseResponse]) -> None:
        self._responses = responses

    def parse(self, text: str, state: State | None) -> ParseResponse:
        return self._responses[text].model_copy(deep=True)


class FailingNLPClient:
    def parse(self, text: str, state: State | None) -> ParseResponse:
        raise NLPClientError("timed out")


def build_service(responses: dict[str, ParseResponse]) -> tuple[OrderService, InMemorySessionStore]:
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
    service, _ = build_service({})

    reply = service.handle_message(1, "/start")

    assert "Новый заказ" in reply.text
    assert reply.parse_mode == "HTML"
    assert reply.reply_keyboard == [["Все выбрал"], ["Сбросить заказ"]]


def test_ask_flow_returns_choice_keyboard() -> None:
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
    assert "Какой размер Маргариты?" in reply.text
    assert reply.reply_keyboard == [["25 см"], ["30 см"], ["Сбросить заказ"]]
    assert store.get(10).awaiting_confirmation is False


def test_pending_size_choice_is_applied_locally_without_nlp() -> None:
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


def test_unknown_pizza_is_blocked_by_catalog_stub() -> None:
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

    assert "Какой размер для Маргариты?" in reply.text
    assert store.get(60).awaiting_confirmation is False
    assert store.get(60).checkout_step == "draft"


def test_timeout_on_first_message_can_recover_from_catalog_text() -> None:
    service, store = build_service_with_client(FailingNLPClient())

    reply = service.handle_message(70, "мне надо пеперони")

    assert "Пепперони" in reply.text
    assert "Какой размер" in reply.text
    assert store.get(70).state.entities.items[0].name == "Пепперони"


def test_timeout_on_first_message_can_recover_from_phonetic_catalog_typo() -> None:
    service, store = build_service_with_client(FailingNLPClient())

    reply = service.handle_message(72, "мне надо пипирони")

    assert "Пепперони" in reply.text
    assert "Какой размер" in reply.text
    assert store.get(72).state.entities.items[0].name == "Пепперони"


def test_timeout_on_first_message_uses_order_wording_not_change_wording() -> None:
    service, _ = build_service_with_client(FailingNLPClient())

    reply = service.handle_message(71, "привет")

    assert "Не успел обработать заказ" in reply.text
    assert "изменение" not in reply.text.lower()


def test_draft_does_not_force_checkout_before_button() -> None:
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
