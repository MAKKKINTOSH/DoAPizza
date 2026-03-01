from fastapi.testclient import TestClient

from nlp_service.app import app
from nlp_service.llm import LLMClient, LLMResult
from nlp_service.schemas import Choice, EditOperation, Entities, Item, State, TimeInfo


def test_parse_ready(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(
                    items=[Item(name="Margherita", qty=1, size_cm=30)],
                    delivery_type="pickup",
                    phone="79991234567",
                    time=TimeInfo(type="asap", value=None),
                ),
                missing=[],
                choices=None,
                message="Готово.",
                confidence=0.9,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post("/v1/parse", json={"text": "1 маргарита"})
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "READY"
    assert data["entities"]["items"]


def test_llm_prompt_requires_literal_modifiers() -> None:
    prompt = LLMClient()._user_prompt("добавь в пепперони перец", State())

    assert "return 'перец'" in prompt
    assert "do not invent" in prompt


def test_llm_prompt_prioritizes_add_item_intent() -> None:
    prompt = LLMClient()._user_prompt("еще маргариту", State())

    assert "Intent priority rules are strict" in prompt
    assert "never convert an add-pizza request into replace_item" in prompt
    assert "phrases like 'еще маргариту'" in prompt


def test_llm_auto_falls_back_to_user_only_on_system_rejection(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROMPT_MODE", "auto")

    client = LLMClient()
    calls: list[str] = []

    def fake_request(payload):
        calls.append(payload["messages"][0]["role"])
        if payload["messages"][0]["role"] == "system":
            raise RuntimeError('unsupported role "system"')
        return "{}"

    monkeypatch.setattr(client, "_request_with_retries", fake_request)

    result = client._chat("system", "user")

    assert result == "{}"
    assert calls == ["system", "user"]


def test_llm_parse_json_extracts_embedded_object() -> None:
    client = LLMClient()

    parsed = client._parse_json_with_fix('prefix {"message":"ok","confidence":1} suffix', "system", "user")

    assert parsed == {"message": "ok", "confidence": 1}


def test_parse_replace_mode_updates_existing_order(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            assert state.entities.items[0].name == "Пепперони"
            return LLMResult(
                entities=Entities(items=[Item(name="Маргарита", qty=1)]),
                missing=[],
                choices=None,
                message="Заменил пиццу.",
                confidence=0.95,
                state_update_mode="replace",
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "замени на маргариту",
            "state": {
                "entities": {"items": [{"name": "Пепперони", "qty": 1, "size_cm": 30, "variant": None, "modifiers": []}]},
                "missing": [],
                "pending_choice": None,
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["items"] == [
        {"name": "Маргарита", "qty": 1, "size_cm": None, "variant": None, "modifiers": []}
    ]


def test_parse_skip_modifier_choice_without_llm(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            raise AssertionError("LLM should not be called for skip choice")

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "не надо",
            "state": State(
                entities=Entities(items=[Item(name="Пепперони", qty=1)]),
                missing=["modifiers"],
                pending_choice=Choice(field="modifiers", options=["Грибы", "Не добавлять"], item_index=0),
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "READY"
    assert data["entities"]["items"][0]["modifiers"] == []
    assert data["choices"] is None


def test_parse_enforces_size_question_when_llm_did_not_ask(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Пепперони", qty=1)]),
                missing=[],
                choices=None,
                message="",
                confidence=0.8,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post("/v1/parse", json={"text": "хочу пепперони"})
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "ASK"
    assert data["choices"]["field"] == "size_cm"
    assert data["choices"]["options"] == ["25 см", "30 см", "35 см"]
    assert "размер" in data["message"].lower()


def test_parse_replaces_generic_llm_message_with_followup(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Пепперони", qty=1)]),
                missing=[],
                choices=None,
                message="Готово.",
                confidence=0.8,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post("/v1/parse", json={"text": "хочу пепперони"})
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "ASK"
    assert data["message"] != "Готово."
    assert "размер" in data["message"].lower()


def test_parse_enforces_delivery_choice_and_address(monkeypatch) -> None:
    class DummyLLM:
        def __init__(self) -> None:
            self.calls = 0

        def extract(self, text, state):
            self.calls += 1
            if self.calls == 1:
                return LLMResult(
                    entities=Entities(items=[Item(name="Маргарита", qty=1, size_cm=30)]),
                    missing=[],
                    choices=None,
                    message="",
                    confidence=0.8,
                )
            raise AssertionError("LLM should not be called on simple delivery choice")

    import nlp_service.parser as parser

    dummy = DummyLLM()
    monkeypatch.setattr(parser, "LLM_CLIENT", dummy)
    client = TestClient(app)

    first = client.post("/v1/parse", json={"text": "маргарита 30 см"})
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["choices"]["field"] == "delivery_type"

    second = client.post("/v1/parse", json={"text": "доставка", "state": first_data["state"]})
    assert second.status_code == 200
    second_data = second.json()
    assert second_data["action"] == "ASK"
    assert second_data["entities"]["delivery_type"] == "delivery"
    assert second_data["missing"][0] == "address"
    assert "адрес" in second_data["message"].lower()


def test_parse_does_not_call_llm_for_exact_delivery_choice(monkeypatch) -> None:
    class DummyLLM:
        def __init__(self) -> None:
            self.calls = 0

        def extract(self, text, state):
            self.calls += 1
            if self.calls == 1:
                return LLMResult(
                    entities=Entities(items=[Item(name="Маргарита", qty=1, size_cm=30)]),
                    missing=[],
                    choices=None,
                    message="",
                    confidence=0.8,
                )
            raise AssertionError("LLM should not be called for exact choice reply")

    import nlp_service.parser as parser

    dummy = DummyLLM()
    monkeypatch.setattr(parser, "LLM_CLIENT", dummy)
    client = TestClient(app)

    first = client.post("/v1/parse", json={"text": "маргарита 30 см"})
    assert first.status_code == 200
    second = client.post("/v1/parse", json={"text": "Доставка", "state": first.json()["state"]})
    assert second.status_code == 200
    assert dummy.calls == 1
    assert second.json()["entities"]["delivery_type"] == "delivery"


def test_parse_invalid_size_returns_nearest_options(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=27)]),
                missing=[],
                choices=None,
                message="",
                confidence=0.82,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post("/v1/parse", json={"text": "пепперони 27 см"})
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "ASK"
    assert data["choices"]["field"] == "size_cm"
    assert data["choices"]["options"] == ["25 см", "30 см"]
    assert data["choices"]["requested_value"] == "27 см"
    assert "советую 30 см" in data["message"].lower()


def test_parse_ignores_hallucinated_items_for_address_reply(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(
                    items=[Item(name="Москва, Ленина, 5", qty=1)],
                    address="Москва, Ленина, 5",
                ),
                missing=[],
                choices=None,
                message="",
                confidence=0.7,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "Москва, Ленина, 5",
            "state": State(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=25)], delivery_type="delivery"),
                missing=["address"],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 1
    assert data["entities"]["items"][0]["name"] == "Пепперони"
    assert data["entities"]["address"] == "Москва, Ленина, 5"


def test_merge_ignores_exact_item_echo(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=25)]),
                missing=["address"],
                choices=None,
                message="",
                confidence=0.7,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "что дальше",
            "state": State(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=25)], delivery_type="delivery"),
                missing=["address"],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 1


def test_add_request_does_not_honor_replace_mode(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Маргарита", qty=1, size_cm=27)]),
                missing=[],
                choices=None,
                message="",
                confidence=0.78,
                state_update_mode="replace",
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "еще маргариту 27 см",
            "state": State(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=30)]),
                missing=["delivery_type"],
                pending_choice=Choice(field="delivery_type", options=["Доставка", "Самовывоз"]),
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 2
    assert data["entities"]["items"][0]["name"] == "Пепперони"
    assert data["choices"]["field"] == "size_cm"
    assert data["choices"]["requested_value"] == "27 см"


def test_parse_expected_phone_rejects_short_number_without_llm(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            raise AssertionError("LLM should not be called for obviously short phone input")

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "111",
            "state": State(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=30)], delivery_type="pickup"),
                missing=["phone"],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "ASK"
    assert data["entities"]["phone"] is None
    assert "телефон" in data["message"].lower() or "номер" in data["message"].lower()


def test_parse_expected_time_accepts_now_without_llm(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            raise AssertionError("LLM should not be called for simple asap time")

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "сейчас",
            "state": State(
                entities=Entities(
                    items=[Item(name="Пепперони", qty=1, size_cm=30)],
                    delivery_type="pickup",
                    phone="+777777777",
                ),
                missing=["time"],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "READY"
    assert data["entities"]["time"] == {"type": "asap", "value": None}


def test_parse_add_request_without_explicit_qty_keeps_single_added_item(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Маргарита", qty=2, size_cm=27)]),
                missing=[],
                choices=None,
                message="",
                confidence=0.78,
                state_update_mode="merge",
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "еще маргариту 27 см",
            "state": State(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=30)]),
                missing=["delivery_type"],
                pending_choice=Choice(field="delivery_type", options=["Доставка", "Самовывоз"]),
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["items"][1]["qty"] == 1


def test_parse_edit_operation_adds_modifier_to_existing_item(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(),
                edit_operations=[
                    EditOperation(
                        op="update_item",
                        item_index=0,
                        modifiers_add=["Ананасы"],
                    )
                ],
                missing=[],
                choices=None,
                message="Добавил ананасы.",
                confidence=0.91,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "в пепперони ананасы сверху добавь",
            "state": State(
                entities=Entities(
                    items=[
                        Item(name="Пепперони", qty=1, size_cm=35),
                        Item(name="Маргарита", qty=1, size_cm=25, modifiers=["Грибы"]),
                    ]
                ),
                missing=[],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 2
    assert data["entities"]["items"][0]["modifiers"] == ["Ананасы"]
    assert data["entities"]["items"][0]["size_cm"] == 35


def test_parse_realigns_update_operation_to_named_existing_item(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(),
                edit_operations=[
                    EditOperation(
                        op="update_item",
                        item_index=0,
                        modifiers_add=["Ананас"],
                    )
                ],
                missing=[],
                choices=None,
                message="Добавил ананас.",
                confidence=0.9,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "в маргариту добавить ананас",
            "state": State(
                entities=Entities(
                    items=[
                        Item(name="Пепперони", qty=1, size_cm=30, modifiers=["Грибы"]),
                        Item(name="Маргарита", qty=1, size_cm=35),
                    ]
                ),
                missing=[],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["items"][0]["modifiers"] == ["Грибы"]
    assert data["entities"]["items"][1]["modifiers"] == ["Ананас"]


def test_parse_falls_back_to_existing_item_update_when_llm_returns_item_snapshot(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Маргарита", qty=1, modifiers=["Ананас"])]),
                edit_operations=[],
                missing=[],
                choices=None,
                message="Добавил ананас.",
                confidence=0.88,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "в маргариту добавить ананас",
            "state": State(
                entities=Entities(
                    items=[
                        Item(name="Пепперони", qty=1, size_cm=30, modifiers=["Грибы"]),
                        Item(name="Маргарита", qty=1, size_cm=25),
                    ]
                ),
                missing=[],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 2
    assert data["entities"]["items"][1]["name"] == "Маргарита"
    assert data["entities"]["items"][1]["size_cm"] == 25
    assert data["entities"]["items"][1]["modifiers"] == ["Ананас"]


def test_parse_edit_operation_removes_first_item(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(),
                edit_operations=[EditOperation(op="remove_item", item_index=0)],
                missing=[],
                choices=None,
                message="Убрал первую пиццу.",
                confidence=0.93,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "удали первую пиццу",
            "state": State(
                entities=Entities(
                    items=[
                        Item(name="Пепперони", qty=1, size_cm=35),
                        Item(name="Маргарита", qty=1, size_cm=25, modifiers=["Грибы"]),
                        Item(name="Пепперони", qty=1, size_cm=35, modifiers=["Ананасы"]),
                    ]
                ),
                missing=[],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 2
    assert data["entities"]["items"][0]["name"] == "Маргарита"
    assert data["entities"]["items"][1]["modifiers"] == ["Ананасы"]


def test_add_item_request_ignores_replace_item_edit_operation(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Маргарита", qty=1)]),
                edit_operations=[
                    EditOperation(
                        op="replace_item",
                        item_index=0,
                        item=Item(name="Маргарита", qty=1),
                    )
                ],
                missing=[],
                choices=None,
                message="",
                confidence=0.88,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "еще маргариту",
            "state": State(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=30)]),
                missing=[],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 2
    assert data["entities"]["items"][0]["name"] == "Пепперони"
    assert data["entities"]["items"][1]["name"] == "Маргарита"


def test_add_item_request_ignores_update_item_edit_operation(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Пепперони", qty=1)]),
                edit_operations=[
                    EditOperation(
                        op="update_item",
                        item_index=0,
                        name="Пепперони",
                    )
                ],
                missing=[],
                choices=None,
                message="",
                confidence=0.84,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "добавь пепперони",
            "state": State(
                entities=Entities(items=[Item(name="Маргарита", qty=1, size_cm=30)]),
                missing=[],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 2
    assert data["entities"]["items"][0]["name"] == "Маргарита"
    assert data["entities"]["items"][1]["name"] == "Пепперони"


def test_add_item_request_aligns_item_name_with_catalog_text(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Пепперони", qty=1)]),
                missing=[],
                choices=None,
                message="",
                confidence=0.83,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "еще маргариту",
            "state": State(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=35)]),
                missing=[],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 2
    assert data["entities"]["items"][1]["name"] == "Маргарита"


def test_direct_order_request_aligns_item_name_with_catalog_text(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Маргарита", qty=1, size_cm=30)]),
                missing=[],
                choices=None,
                message="",
                confidence=0.83,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post("/v1/parse", json={"text": "хочу пеперони 30 см"})
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["items"][0]["name"] == "Пепперони"


def test_direct_order_request_aligns_phonetic_catalog_typo(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Маргарита", qty=1, size_cm=30)]),
                missing=[],
                choices=None,
                message="",
                confidence=0.83,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post("/v1/parse", json={"text": "хочу пипирони 30 см"})
    assert response.status_code == 200
    data = response.json()
    assert data["entities"]["items"][0]["name"] == "Пепперони"


def test_add_item_request_does_not_inherit_size_without_explicit_size(monkeypatch) -> None:
    class DummyLLM:
        def extract(self, text, state):
            return LLMResult(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=30)]),
                missing=[],
                choices=None,
                message="",
                confidence=0.83,
            )

    import nlp_service.parser as parser

    monkeypatch.setattr(parser, "LLM_CLIENT", DummyLLM())
    client = TestClient(app)
    response = client.post(
        "/v1/parse",
        json={
            "text": "еще маргариту",
            "state": State(
                entities=Entities(items=[Item(name="Пепперони", qty=1, size_cm=30)]),
                missing=[],
                pending_choice=None,
            ).model_dump(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["entities"]["items"]) == 2
    assert data["entities"]["items"][1]["name"] == "Маргарита"
    assert data["entities"]["items"][1]["size_cm"] is None
    assert data["choices"]["field"] == "size_cm"
