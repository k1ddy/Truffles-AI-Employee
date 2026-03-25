import asyncio
import json
import os
import re
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app import webhook as legacy_webhook_module
from app.contracts.decision import (
    DecisionOutcome,
    DecisionSignals,
    ExpectedReplyState,
    IntentDecompositionState,
)
from app.database import get_db
from app.main import app
from app.models import Branch, Client, ClientSettings, Conversation, Specialist, User
from app.routers.public_entrypoint_contract import PublicEntrypointMaterializationMode
from app.routers.webhook import _legacy as legacy_router
from app.routers.webhook import _legacy as webhook_router
from app.routers.webhook import booking as webhook_booking
from app.routers.webhook import http as http_router
from app.routers.webhook.context_manager import (
    _get_expected_reply_reason,
    _get_expected_reply_type,
    _is_asr_confirmation_active,
    _is_handover_confirmation_active,
    _set_expected_reply_type,
)
from app.routers.webhook import guards as webhook_guards
from app.routers.webhook import info as webhook_info
from app.routers.webhook import policy as webhook_policy
from app.routers.webhook import response as webhook_response
from app.routers.webhook.decision import (
    _classify_policy_core_degrade_reason,
    _detect_tool_contract_error,
    _extract_fact_evidence_refs,
    _fact_guard_reason,
    _policy_core_reason_supports_info_rescue,
    _policy_has_style_reference_hint,
    _resolve_specialist_name_hint_with_trace,
    _validate_policy_check_confirm_contract,
)
from app.routers.webhook.session_memory import _is_session_reset_only_message
from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.consult import ConsultControllerOutput
from app.schemas.message import MessageRequest, MessageResponse
from app.schemas.webhook import (
    WebhookBody,
    WebhookMetadata,
    WebhookRequest,
    WebhookResponse,
    WebhookTenantContext,
)
from app.services import escalation_service
from app.services import handover_owner_service
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities
from app.services.demo_salon_knowledge import (
    DemoSalonDecision,
    SemanticServiceMatch,
    get_demo_salon_decision,
    semantic_service_match,
)
from app.services.intent_service import (
    DomainIntent,
    Intent,
    classify_domain_with_scores,
    is_opt_out_message,
    is_strong_out_of_domain,
)
from app.services.knowledge_snapshot_consumer import ConsultSnapshotShadowResult
from app.services.knowledge_validation import MinimumDataContractStatus
from app.services.message_service import select_handover_user_message
from app.services.result import Result
from app.services.state_machine import ConversationState
from app.services.state_service import (
    PendingResumeBoundaryRuntimeHooks,
    _resolve_resolved_handoff_resume_boundary_restore,
)
from app.services.tool_registry_service import validate_tool_args_contract

MINIMUM_DATA_READY = MinimumDataContractStatus(ready=True, missing_fields=[])


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fake_intent_decomp():
    def _extract_service_query(normalized: str) -> str:
        patterns = [
            r"(?:сколько стоит|сколько стоят|стоимость|цена|прайс|почем)\s+([^?!.;,]+)",
            r"(?:сколько длится|сколько по времени|по времени|длительность|сколько времени)\s+([^?!.;,]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            candidate = re.sub(r"\s+", " ", match.group(1)).strip()
            if not candidate:
                continue
            tokens = candidate.split()
            return " ".join(tokens[:6])
        return ""

    def _detect_stub(text: str, **_kwargs):
        normalized = (text or "").casefold()
        intents: list[str] = []

        if re.search(r"\b(запис|запишите|запиши|записать|бронь|заброн)\b", normalized):
            intents.append("booking")
        if re.search(r"\b(сегодня|завтра|послезавтра)\b", normalized) and re.search(r"\b\d{1,2}\b", normalized):
            intents.append("booking")

        if any(keyword in normalized for keyword in ["цена", "стоим", "стоимость", "прайс", "сколько стоит", "почем"]):
            intents.append("pricing")
        if any(
            keyword in normalized
            for keyword in [
                "сколько длится",
                "длится",
                "длительность",
                "по времени",
                "сколько по времени",
                "сколько времени",
                "время процедуры",
            ]
        ):
            intents.append("duration")
        if any(keyword in normalized for keyword in ["работаете", "график", "режим работы", "часы", "во сколько"]):
            intents.append("hours")

        if not intents:
            intents = ["other"]

        primary = intents[0]
        secondary = [intent for intent in intents[1:] if intent != primary]
        service_query = _extract_service_query(normalized)
        return {
            "multi_intent": len(intents) > 1,
            "primary_intent": primary,
            "secondary_intents": secondary,
            "intents": intents,
            "service_query": service_query,
            "consult_intent": False,
            "consult_topic": "",
            "consult_question": "",
        }

    with patch("app.routers.webhook._legacy.detect_multi_intent", side_effect=_detect_stub):
        yield


@pytest.fixture(autouse=True)
def _disable_debounce_redis():
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.routers.webhook._legacy._get_debounce_redis", return_value=None)
        )
        stack.enter_context(
            patch("app.routers.webhook.dedup._get_debounce_redis", return_value=None)
        )
        yield


@pytest.fixture(autouse=True)
def _disable_quiet_hours_notices():
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.routers.webhook.decision.build_quiet_hours_notice", return_value=None)
        )
        stack.enter_context(
            patch("app.routers.webhook.decision.build_evening_greeting", return_value=None)
        )
        yield


@pytest.fixture(autouse=True)
def _disable_minimum_data_safe_mode():
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.routers.webhook.decision._build_minimum_data_contract_status",
                return_value=SimpleNamespace(ready=True, missing_fields=[]),
            )
        )
        yield


@pytest.fixture(autouse=True)
def _stub_generic_signal_lexicons():
    from app.services import demo_salon_knowledge as knowledge

    original = knowledge.get_signal_lexicon_list

    def _stub(client_slug: str | None, key: str):
        if client_slug == "generic":
            return []
        return original(client_slug, key)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.demo_salon_knowledge.get_signal_lexicon_list",
                side_effect=_stub,
            )
        )
        stack.enter_context(
            patch(
                "app.routers.webhook.info.get_signal_lexicon_list",
                side_effect=_stub,
            )
        )
        yield


@pytest.fixture(autouse=True)
def _stub_generic_policy_pack():
    from app.routers.webhook import policy as policy_router

    original = policy_router._load_policy_pack

    def _stub(*, policy_type: str | None, client_slug: str | None):
        if client_slug == "generic":
            return {}
        return original(policy_type=policy_type, client_slug=client_slug)

    with patch(
        "app.routers.webhook.policy._load_policy_pack",
        side_effect=_stub,
    ):
        yield


@pytest.fixture(autouse=True)
def _stub_generic_booking_request_lexicon():
    from app.routers.webhook import decision as decision_router

    original = decision_router._collect_booking_request_lexicon

    def _stub(client_slug: str | None):
        if client_slug == "generic":
            return {}
        return original(client_slug)

    with patch(
        "app.routers.webhook.decision._collect_booking_request_lexicon",
        side_effect=_stub,
    ):
        yield


@pytest.fixture(autouse=True)
def _stub_generic_service_hint():
    from app.routers.webhook import decision as decision_router

    original = decision_router._extract_service_hint

    def _stub(text: str | None, client_slug: str | None):
        if client_slug == "generic":
            return None
        return original(text, client_slug)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.routers.webhook.decision._extract_service_hint",
                side_effect=_stub,
            )
        )
        stack.enter_context(
            patch(
                "app.routers.webhook._legacy._extract_service_hint",
                side_effect=_stub,
            )
        )
        yield


@pytest.fixture(autouse=True)
def _stub_generic_datetime_lexicon():
    from app.routers.webhook import booking as booking_router

    original = booking_router._load_datetime_lexicon

    def _stub(client_slug: str | None):
        if client_slug == "generic":
            return {}
        return original(client_slug)

    with patch(
        "app.routers.webhook.booking._load_datetime_lexicon",
        side_effect=_stub,
    ):
        yield


@pytest.fixture(autouse=True)
def _stub_generic_truth_pack():
    from app.services import demo_salon_knowledge as knowledge

    original = knowledge.load_yaml_truth
    generic_truth = {
        "domain_pack": {},
        "services_catalog": {"services": []},
        "client_pack": {"policy": {}},
        "salon": {"timezone": "UTC"},
    }

    def _stub(client_slug: str | None = None):
        if client_slug == "generic":
            return dict(generic_truth)
        return original(client_slug)

    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.demo_salon_knowledge.load_yaml_truth",
                side_effect=_stub,
            )
        )
        stack.enter_context(
            patch(
                "app.routers.webhook.decision.load_yaml_truth",
                side_effect=_stub,
            )
        )
        yield


@pytest.fixture(autouse=True)
def _disable_consult_snapshot():
    with ExitStack() as stack:
        stack.enter_context(
            patch(
                "app.services.knowledge_snapshot_consumer.get_consult_snapshot_mode",
                return_value="shadow",
            )
        )
        stack.enter_context(
            patch(
                "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
                return_value=False,
            )
        )
        stack.enter_context(
            patch(
                "app.services.knowledge_snapshot_consumer.is_consult_snapshot_allowlisted",
                return_value=False,
            )
        )
        yield


DEMO_DOMAIN_ROUTER_CONFIG = {
    "anchors_in": [
        "запись на услугу",
        "записаться на маникюр",
        "запис",
        "услуг",
        "адрес салона",
        "адрес",
        "как добраться",
        "часы работы",
        "часы",
        "график работы",
        "график",
        "режим работы",
        "во сколько",
        "цены на услуги",
        "прайс салона",
        "маникюр педикюр",
        "стрижка окрашивание",
        "брови ресницы",
        "уход за лицом",
        "депиляция шугаринг",
        "макияж укладка",
        "макияж",
        "кошачий глаз",
        "референс прически",
        "прическа как у",
    ],
    "anchors_in_strict": [
        "запис",
        "услуг",
        "адрес",
        "часы",
        "график",
        "режим",
    ],
    "anchors_out": [
        "погода сегодня",
        "прогноз погоды",
        "анекдот",
        "стихотворение",
        "политика новости",
        "выборы президент",
        "рецепт",
        "как приготовить",
        "программирование",
        "напиши код",
        "python",
        "личные советы",
        "совет по отношениям",
        "ветеринар",
        "животн",
        "питомец",
        "питомц",
        "собак",
        "собач",
        "пес",
        "пёс",
        "кот",
        "кошка",
        "кошк",
        "стрижка собаки",
        "стрижка кошки",
        "постричь козу",
        "спасти сестру",
        "слепая сестра",
        "слепой сестре",
    ],
    "in_threshold": 0.55,
    "out_threshold": 0.55,
    "margin": 0.03,
}


def _fake_service_hint(text: str, client_slug: str | None) -> str | None:
    normalized = (text or "").casefold()
    if "маник" in normalized:
        return "маникюр"
    if "педик" in normalized:
        return "педикюр"
    if "стриж" in normalized:
        return "стрижка"
    if "массаж" in normalized and "ног" in normalized:
        return "массаж ног"
    if "бров" in normalized:
        return "брови"
    if "ресниц" in normalized:
        return "ресницы"
    return None


class TestMessageEndpoint:
    def test_message_request_validation(self, client):
        # Missing required fields
        response = client.post("/message", json={"content": "Привет!"})
        assert response.status_code == 422

    def test_message_with_invalid_uuid(self, client):
        response = client.post(
            "/message",
            json={"client_id": "not-a-uuid", "remote_jid": "77759841926@s.whatsapp.net", "content": "Привет!"},
        )
        assert response.status_code == 422

    def test_message_rejects_blank_content_before_reasoning_core(self, client):
        with patch(
            "app.routers.message.handle_public_webhook_payload",
            new_callable=AsyncMock,
        ) as mock_handle:
            response = client.post(
                "/message",
                json={
                    "client_id": str(uuid4()),
                    "remote_jid": "77759841926@s.whatsapp.net",
                    "content": "   ",
                },
            )

        assert response.status_code == 422
        mock_handle.assert_not_called()

    def test_message_routes_through_webhook_pipeline(self, client):
        conversation_id = uuid4()
        conversation = SimpleNamespace(id=conversation_id, state=ConversationState.BOT_ACTIVE.value)
        conversation_query = Mock()
        conversation_query.filter.return_value.first.return_value = conversation

        db = Mock()
        db.query.return_value = conversation_query

        def _override_get_db():
            yield db

        app.dependency_overrides[get_db] = _override_get_db
        try:
            with patch(
                "app.routers.message.get_client_slug", return_value="demo_salon"
            ), patch(
                "app.core.consultant_runtime.handle_webhook_payload",
                new_callable=AsyncMock,
            ) as mock_handle:
                mock_handle.return_value = WebhookResponse(
                    success=True,
                    message="ok",
                    conversation_id=conversation_id,
                    bot_response="reply",
                )

                response = client.post(
                    "/message",
                    json={
                        "client_id": str(uuid4()),
                        "remote_jid": "77759841926@s.whatsapp.net",
                        "content": "Привет!",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["bot_response"] == "reply"
                assert data["conversation_id"] == str(conversation_id)
                assert data["state"] == ConversationState.BOT_ACTIVE.value

                payload = mock_handle.call_args.args[0]
                assert payload.client_slug == "demo_salon"
                assert payload.body.message == "Привет!"
                assert payload.body.metadata.remoteJid == "77759841926@s.whatsapp.net"
                assert payload.body.metadata.messageId
                assert isinstance(payload.body.metadata.timestamp, int)
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_message_returns_422_for_blocked_no_conversation_response(self, client):
        db = Mock()

        def _override_get_db():
            yield db

        app.dependency_overrides[get_db] = _override_get_db
        try:
            with patch(
                "app.routers.message.get_client_slug", return_value="demo_salon"
            ), patch(
                "app.core.consultant_runtime.handle_webhook_payload",
                new_callable=AsyncMock,
            ) as mock_handle:
                mock_handle.return_value = WebhookResponse(
                    success=False,
                    message="Empty message",
                    conversation_id=None,
                )

                response = client.post(
                    "/message",
                    json={
                        "client_id": str(uuid4()),
                        "remote_jid": "77759841926@s.whatsapp.net",
                        "content": "Привет!",
                    },
                )

            assert response.status_code == 422
            assert response.json() == {"detail": "Empty message"}
            db.query.assert_not_called()
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_message_returns_503_for_success_without_conversation_id(self, client):
        db = Mock()

        def _override_get_db():
            yield db

        app.dependency_overrides[get_db] = _override_get_db
        try:
            with patch(
                "app.routers.message.get_client_slug", return_value="demo_salon"
            ), patch(
                "app.core.consultant_runtime.handle_webhook_payload",
                new_callable=AsyncMock,
            ) as mock_handle:
                mock_handle.return_value = WebhookResponse(
                    success=True,
                    message="Fallback response skipped",
                    conversation_id=None,
                    bot_response="Извините, произошла ошибка.",
                )

                response = client.post(
                    "/message",
                    json={
                        "client_id": str(uuid4()),
                        "remote_jid": "77759841926@s.whatsapp.net",
                        "content": "Привет!",
                    },
                )

            assert response.status_code == 503
            assert response.json() == {
                "detail": "Message pipeline returned no conversation_id: Fallback response skipped"
            }
            db.query.assert_not_called()
        finally:
            app.dependency_overrides.pop(get_db, None)


class TestMessageSchemas:
    def test_message_request_valid(self):
        req = MessageRequest(
            client_id=uuid4(), remote_jid="77759841926@s.whatsapp.net", content="Test", channel="whatsapp"
        )
        assert req.content == "Test"
        assert req.channel == "whatsapp"

    def test_message_request_trims_content(self):
        req = MessageRequest(
            client_id=uuid4(),
            remote_jid="77759841926@s.whatsapp.net",
            content="  Test  ",
            channel="whatsapp",
        )
        assert req.content == "Test"

    def test_message_response_valid(self):
        resp = MessageResponse(success=True, conversation_id=uuid4(), state="bot_active", bot_response="Test response")
        assert resp.success == True
        assert resp.state == "bot_active"




def _build_db(client_slug: str, webhook_secret: str | None):
    client = Mock()
    client.id = "client-123"
    client.name = client_slug

    settings = Mock()
    settings.webhook_secret = webhook_secret

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client

    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings

    db = Mock()
    db.query.side_effect = _build_query_side_effect(
        client_query=client_query,
        settings_query=settings_query,
    )
    return db


class TestWebhookAuth:
    def _client_with_db(self, db):
        def _override_get_db():
            yield db

        app.dependency_overrides[get_db] = _override_get_db
        return TestClient(app)

    def test_missing_secret_returns_401(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post("/webhook", json={"client_slug": "test", "body": {"message": "hi"}})
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_invalid_secret_returns_401(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            with patch("app.routers.webhook.http.report_integration_incident") as incident_mock:
                response = client.post(
                    "/webhook",
                    json={"client_slug": "test", "body": {"message": "hi"}},
                    headers={"X-Webhook-Secret": "wrong"},
                )
            assert response.status_code == 401
            incident_mock.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_valid_secret_returns_200(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post(
                "/webhook",
                json={"client_slug": "test", "body": {"message": "hi"}},
                headers={"X-Webhook-Secret": "secret"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @patch("app.routers.webhook.http.alert_warning")
    def test_missing_secret_allows_request_with_warning(self, mock_alert):
        db = _build_db("test", None)
        client = self._client_with_db(db)
        try:
            response = client.post(
                "/webhook",
                json={"client_slug": "test", "body": {"message": "hi"}},
            )
            assert response.status_code == 200
            mock_alert.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_query_secret_fallback_returns_200(self):
        db = _build_db("test", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post(
                "/webhook?webhook_secret=secret",
                json={"client_slug": "test", "body": {"message": "hi"}},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_direct_webhook_missing_secret_returns_401(self):
        db = _build_db("direct", "secret")
        client = self._client_with_db(db)
        try:
            response = client.post("/webhook/direct", json={"client_slug": "direct", "body": {"message": "hi"}})
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_legacy_webhook_compat_routes_through_public_entrypoint_contract():
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(message="hi"),
    )
    db = Mock()

    with patch(
        "app.webhook.handle_public_webhook_payload",
        new=AsyncMock(return_value=WebhookResponse(success=True, message="ok")),
    ) as mock_handle:
        response = await legacy_webhook_module.handle_webhook(payload, db)

    assert response.success is True
    assert response.message == "ok"
    mock_handle.assert_awaited_once()
    assert mock_handle.await_args.args[:2] == (payload, db)
    assert mock_handle.await_args.kwargs == {
        "entrypoint_name": "Legacy webhook",
        "materialization_mode": PublicEntrypointMaterializationMode.ALLOW_UNMATERIALIZED,
        "provided_secret": None,
        "enforce_secret": False,
        "enqueue_only": False,
    }


@pytest.mark.asyncio
async def test_direct_webhook_passes_non_secret_preflight_payload_to_public_entrypoint_contract(monkeypatch):
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message="hi",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId="msg-direct-preflight-1",
            ),
        ),
        tenant_context=WebhookTenantContext(
            client_slug="demo_salon",
            source="webhook",
        ),
    )
    preflight_payload = {
        "client": SimpleNamespace(id="client-123"),
        "resolved_branch_id": UUID("00000000-0000-0000-0000-000000000131"),
        "tenant_context": {
            "client_slug": "demo_salon",
            "source": "webhook",
            "branch_id": "00000000-0000-0000-0000-000000000131",
        },
    }
    db = _build_db("demo_salon", None)

    monkeypatch.setattr(http_router, "_parse_webhook_request", AsyncMock(return_value=payload))
    monkeypatch.setattr(http_router, "_get_request_webhook_secret", lambda request: None)
    monkeypatch.setattr(
        http_router,
        "_run_preflight",
        lambda *args, **kwargs: (None, preflight_payload),
    )

    with patch(
        "app.routers.public_entrypoint_contract.handle_public_webhook_payload",
        new=AsyncMock(return_value=WebhookResponse(success=True, message="ok")),
    ) as mock_handle:
        response = await http_router.handle_webhook_direct("demo_salon", Mock(), db)

    assert response.success is True
    assert response.message == "ok"
    assert mock_handle.await_args.args[:2] == (payload, db)
    assert mock_handle.await_args.kwargs["entrypoint_name"] == "Webhook direct"
    assert mock_handle.await_args.kwargs["provided_secret"] is None
    assert mock_handle.await_args.kwargs["enforce_secret"] is False
    assert mock_handle.await_args.kwargs["preflight_payload"] is preflight_payload


def _mock_db_with_messages(messages):
    query = Mock()
    query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = messages

    db = Mock()
    db.query.return_value = query
    return db


def _build_query_side_effect(
    *,
    client_query=None,
    settings_query=None,
    conversation_query=None,
    user_query=None,
    branch_query=None,
    specialist_query=None,
    branch_phone_query=None,
    marketing_query=None,
):
    def _default_first(value):
        query = Mock()
        query.filter.return_value.first.return_value = value
        return query

    def _default_all(values):
        query = Mock()
        query.filter.return_value.all.return_value = values
        return query

    def _default_marketing():
        query = Mock()
        query.join.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.first.return_value = None
        return query

    client_query = client_query or _default_first(None)
    settings_query = settings_query or _default_first(None)
    conversation_query = conversation_query or _default_first(None)
    user_query = user_query or _default_first(None)
    branch_query = branch_query or _default_first(None)
    specialist_query = specialist_query or _default_all([])
    branch_phone_query = branch_phone_query or _default_all([])
    marketing_query = marketing_query or _default_marketing()

    def _query(*models):
        if len(models) == 2:
            model_names = {getattr(model, "__name__", "") for model in models}
            if model_names == {"MarketingCampaignDelivery", "MarketingCampaign"}:
                return marketing_query
            return Mock()
        if len(models) != 1:
            return Mock()
        model = models[0]
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Specialist:
            return specialist_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    return _query


def test_marketing_campaign_query_side_effect_routes_delivery_join():
    class MarketingCampaignDelivery:
        pass

    class MarketingCampaign:
        pass

    marketing_query = Mock()
    query_side_effect = _build_query_side_effect(marketing_query=marketing_query)

    assert query_side_effect(MarketingCampaignDelivery, MarketingCampaign) is marketing_query


def test_marketing_campaign_query_side_effect_does_not_route_other_joins():
    class MarketingCampaign:
        pass

    class AnotherModel:
        pass

    marketing_query = Mock()
    query_side_effect = _build_query_side_effect(marketing_query=marketing_query)

    assert query_side_effect(AnotherModel, MarketingCampaign) is not marketing_query


def _booking_signal_snapshot(messages: list[str], *, client_slug: str = "demo_salon") -> dict:
    message_text = messages[-1] if messages else None
    client_config = {"domain_router": DEMO_DOMAIN_ROUTER_CONFIG}
    booking_block_meta = webhook_router._preflight_booking_block(
        message_text=message_text,
        client_config=client_config,
        booking_active=False,
    )
    if booking_block_meta:
        booking_signal = False
    else:
        booking_signal, booking_block_meta = webhook_router._evaluate_booking_signal(
            messages,
            client_slug=client_slug,
            message_text=message_text,
        )
    booking_snapshot = webhook_router._compact_signal_snapshot(
        {
            "signal": booking_signal,
            "blocked": bool(booking_block_meta),
            "blocked_reason": (
                booking_block_meta.get("booking_blocked_reason")
                if isinstance(booking_block_meta, dict)
                else None
            ),
            "active": False,
            "wants_flow": False,
            "expected_reply_type": None,
            "expected_reply_reason": None,
            "expected_reply_shortcircuit": False,
        }
    )
    saved_message = Mock()
    saved_message.message_metadata = {}
    webhook_router._update_message_signal_snapshot(saved_message, {"booking": booking_snapshot})
    decision_meta = (
        saved_message.message_metadata.get("decision_meta")
        if isinstance(saved_message.message_metadata, dict)
        else None
    )
    signal_snapshot = decision_meta.get("signal_snapshot") if isinstance(decision_meta, dict) else None
    return signal_snapshot.get("booking") if isinstance(signal_snapshot, dict) else {}


class TestSelectHandoverUserMessage:
    def test_uses_previous_meaningful_message(self):
        messages = [
            Mock(content="позови менеджера"),
            Mock(content="а вы можете сделать прическу как майкла джордана?"),
        ]
        db = _mock_db_with_messages(messages)

        result = select_handover_user_message(db, uuid4(), "позови менеджера")

        assert result == "а вы можете сделать прическу как майкла джордана?"

    def test_falls_back_when_no_better_message(self):
        messages = [
            Mock(content="позови менеджера"),
            Mock(content="ок"),
            Mock(content="спасибо"),
        ]
        db = _mock_db_with_messages(messages)

        result = select_handover_user_message(db, uuid4(), "позови менеджера")

        assert result == "позови менеджера"


class TestBatchBookingSignals:
    def test_booking_signal_across_messages(self):
        messages = ["сколько стоит маникюр", "на завтра в 5"]
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint):
            snapshot = _booking_signal_snapshot(messages)
            assert snapshot.get("signal") is True

    def test_booking_signal_blocked_for_info_question(self):
        messages = ["Вы сегодня работаете? Сколько стоит педикюр?"]
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint), patch(
            "app.routers.webhook._legacy.semantic_question_type",
            return_value=SimpleNamespace(kind="pricing", score=0.72, second_score=0.1),
        ):
            snapshot = _booking_signal_snapshot(messages)
            assert snapshot.get("signal") is False

    def test_booking_updates_across_messages(self):
        booking = {"active": True}
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint):
            updated = webhook_router._update_booking_from_messages(
                booking,
                ["маникюр", "на завтра в 5"],
                client_slug="demo_salon",
            )
        assert updated.get("service") == "маникюр"
        assert updated.get("datetime") == "в 5"


class TestBookingSlotGuards:
    def test_booking_name_skips_opt_out(self):
        booking = {"active": True, "last_question": "name"}
        updated = webhook_router._update_booking_from_messages(
            booking,
            ["не пиши мне"],
            client_slug="demo_salon",
        )
        assert updated.get("name") is None

    def test_booking_name_skips_frustration(self):
        booking = {"active": True, "last_question": "name"}
        updated = webhook_router._update_booking_from_messages(
            booking,
            ["иди нахуй"],
            client_slug="demo_salon",
        )
        assert updated.get("name") is None

    def test_booking_prompt_skips_name_when_refused(self):
        booking = {"service": "маникюр", "datetime": "завтра"}
        refusal_flags = {"name": {"value": True, "source": "explicit_refusal", "last_set_at": "2025-12-29T00:00:00Z"}}
        updated, prompt = webhook_router._next_booking_prompt(booking, refusal_flags=refusal_flags)
        assert isinstance(prompt, str)
        assert "точное время" in prompt.casefold()
        assert updated.get("last_question") == "datetime"

    def test_booking_prompt_accepts_weekday_daypart_as_grounded_datetime(self):
        booking = {"service": "маникюр", "datetime": "в субботу вечером"}
        updated, prompt = webhook_router._next_booking_prompt(booking, client_slug="demo_salon")
        assert updated.get("last_question") == "name"
        assert isinstance(prompt, str)
        assert webhook_router.MSG_BOOKING_ASK_NAME in prompt

    def test_booking_prompt_keeps_datetime_followup_for_daypart_without_date(self):
        booking = {"service": "маникюр", "datetime": "после обеда"}
        updated, prompt = webhook_router._next_booking_prompt(booking, client_slug="demo_salon")
        assert updated.get("last_question") == "datetime"
        assert isinstance(prompt, str)
        assert webhook_router.MSG_BOOKING_ASK_DATETIME in prompt

    def test_plan_has_complete_booking_slots_requires_grounded_datetime(self):
        incomplete = {
            "service": "маникюр",
            "datetime": "завтра",
            "name": "Айгуль",
        }
        grounded = {
            "service": "маникюр",
            "datetime": "завтра вечером",
            "name": "Айгуль",
        }

        assert (
            webhook_router._plan_has_complete_booking_slots(
                incomplete,
                client_slug="demo_salon",
            )
            is False
        )
        assert (
            webhook_router._plan_has_complete_booking_slots(
                grounded,
                client_slug="demo_salon",
            )
            is True
        )

    def test_apply_expected_reply_slot_merges_relative_day_and_daypart(self):
        context = {
            "booking": {
                "active": True,
                "service": "маникюр",
                "datetime": "завтра",
                "last_question": "datetime",
            }
        }

        updated = webhook_router._apply_expected_reply_slot(
            context,
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            value="утром",
        )

        assert updated.get("booking", {}).get("datetime") == "завтра утром"


class TestDatetimeExtraction:
    def test_extract_datetime_keeps_date_and_time(self):
        from app.routers.webhook import decision as decision_router

        value = decision_router._extract_datetime(
            "2026-02-13 11:00",
            client_slug="demo_salon",
            relative_base=datetime.now(timezone.utc),
        )

        assert isinstance(value, str)
        assert "2026-02-13" in value
        assert "11:00" in value

    def test_extract_datetime_rejects_invalid_clock_time(self):
        from app.routers.webhook import decision as decision_router

        value = decision_router._extract_datetime(
            "запишите в 45:38",
            client_slug="demo_salon",
            relative_base=datetime.now(timezone.utc),
        )

        assert value is None

    def test_validate_datetime_slot_parses_booking_hour_phrase(self):
        value = webhook_router._validate_datetime_slot(
            "Я хочу записаться на 3 часа.",
            allow_freeform=True,
            client_slug="demo_salon",
        )

        assert value == "03:00"

    def test_validate_datetime_slot_accepts_booking_daypart_phrase(self):
        value = webhook_router._validate_datetime_slot(
            "Может быть, на утро?",
            allow_freeform=True,
            client_slug="demo_salon",
        )

        assert value == "утром"

    def test_validate_datetime_slot_accepts_booking_daypart_adjective_phrase(self):
        value = webhook_router._validate_datetime_slot(
            "Мне подходят только утренние часы.",
            allow_freeform=True,
            client_slug="demo_salon",
        )

        assert value == "утром"

    def test_match_expected_reply_candidates_accepts_question_like_daypart_exact_time_fill(self):
        matched, value, flags = webhook_router._match_expected_reply_candidates(
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            message_text="А можно на утро, скажем, на 10 утра?",
            client_slug="demo_salon",
        )

        assert matched is True
        assert value == "10:00"
        assert "question_like_daypart_exact_time" in flags

    def test_validate_datetime_slot_rejects_same_day_info_phrase(self):
        value = webhook_router._validate_datetime_slot(
            "Можно ли совместить чистку лица и пилинг в один день?",
            allow_freeform=True,
            client_slug="demo_salon",
        )

        assert value is None

    def test_validate_datetime_slot_rejects_duration_question_without_booking_signal(self):
        value = webhook_router._validate_datetime_slot(
            "Сколько длится маникюр на 3 часа?",
            allow_freeform=True,
            client_slug="demo_salon",
        )

        assert value is None

    def test_question_like_hour_reply_not_blocked_for_expected_time(self):
        blocked = webhook_router._should_block_expected_reply_by_info(
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            message_text="Могу прийти в 5 часов?",
            client_slug="demo_salon",
        )

        assert blocked is False

    def test_question_like_daypart_reply_not_blocked_for_expected_time(self):
        blocked = webhook_router._should_block_expected_reply_by_info(
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            message_text="Может быть, на утро?",
            client_slug="demo_salon",
        )

        assert blocked is False

    def test_declarative_daypart_reply_not_blocked_for_expected_time(self):
        blocked = webhook_router._should_block_expected_reply_by_info(
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            message_text="Мне подходят только утренние часы.",
            client_slug="demo_salon",
        )

        assert blocked is False

    def test_question_like_daypart_exact_time_reply_not_blocked_for_expected_time(self):
        blocked = webhook_router._should_block_expected_reply_by_info(
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            message_text="А можно на утро, скажем, на 10 утра?",
            client_slug="demo_salon",
        )

        assert blocked is False

    def test_duration_question_without_booking_signal_stays_blocked_for_expected_time(self):
        blocked = webhook_router._should_block_expected_reply_by_info(
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            message_text="Сколько длится маникюр на 3 часа?",
            client_slug="demo_salon",
        )

        assert blocked is True


class TestServiceHints:
    def test_service_hint_within_window(self):
        now = datetime.now(timezone.utc)
        context = webhook_router._set_service_hint({}, "маникюр", now)

        hint = webhook_router._get_recent_service_hint(context, now + timedelta(minutes=30))

        assert hint == "маникюр"

    def test_service_hint_expires(self):
        now = datetime.now(timezone.utc)
        context = webhook_router._set_service_hint({}, "маникюр", now)

        hint = webhook_router._get_recent_service_hint(
            context,
            now + timedelta(minutes=webhook_router.SERVICE_HINT_WINDOW_MINUTES + 1),
        )

        assert hint is None

    def test_extract_service_hint_returns_none_without_client_slug(self):
        with patch("app.routers.webhook.decision.semantic_service_match") as semantic_match, patch(
            "app.routers.webhook.decision.get_pack_service_hint"
        ) as pack_hint:
            hint = webhook_router._extract_service_hint("хочу маникюр", None)

        assert hint is None
        semantic_match.assert_not_called()
        pack_hint.assert_not_called()


class TestReengageConfirmation:
    def test_handover_confirmation_active(self):
        now = datetime.now(timezone.utc)
        confirmation = {
            "asked_at": now.isoformat(),
            "status": "pending",
            "trigger_type": "low_confidence",
            "trigger_value": "low_confidence",
            "user_message": "помогите",
        }

        assert _is_handover_confirmation_active(
            confirmation,
            now + timedelta(minutes=5),
        )

    def test_asr_confirmation_active(self):
        now = datetime.now(timezone.utc)
        confirmation = {"asked_at": now.isoformat(), "transcript": "маникюр", "attempt": 1}

        assert _is_asr_confirmation_active(
            confirmation,
            now + timedelta(minutes=1),
        )

    def test_reengage_confirmation_active(self):
        now = datetime.now(timezone.utc)
        confirmation = {"asked_at": now.isoformat(), "booking_messages": ["запишите на завтра"]}

        assert webhook_router._is_reengage_confirmation_active(
            confirmation,
            now + timedelta(minutes=5),
        )

    def test_reengage_confirmation_expires(self):
        now = datetime.now(timezone.utc)
        confirmation = {"asked_at": now.isoformat(), "booking_messages": ["запишите на завтра"]}

        assert (
            webhook_router._is_reengage_confirmation_active(
                confirmation,
                now + timedelta(minutes=webhook_router.REENGAGE_CONFIRM_WINDOW_MINUTES + 1),
            )
            is False
        )




class TestRoutingPolicy:
    def test_routing_policy_bot_active(self):
        policy = webhook_router._get_routing_policy(ConversationState.BOT_ACTIVE.value)
        assert policy["allow_booking_flow"] is True
        assert policy["allow_handover_create"] is True
        assert policy["allow_bot_reply"] is True

    def test_routing_policy_pending(self):
        policy = webhook_router._get_routing_policy(ConversationState.PENDING.value)
        assert policy["allow_booking_flow"] is True
        assert policy["allow_handover_create"] is False
        assert policy["allow_truth_gate_reply"] is True
        assert policy["allow_bot_reply"] is True

    def test_routing_policy_manager_active(self):
        policy = webhook_router._get_routing_policy(ConversationState.MANAGER_ACTIVE.value)
        assert policy["allow_bot_reply"] is False
        assert policy["allow_truth_gate_reply"] is False

    def test_booking_flow_runs_with_signal_in_pending(self):
        policy = webhook_router._get_routing_policy(ConversationState.PENDING.value)
        should_run = webhook_router._should_run_booking_flow(
            policy,
            booking_active=False,
            booking_signal=True,
        )
        assert should_run is True

    def test_demo_truth_gate_skips_when_booking(self):
        policy = webhook_router._get_routing_policy(ConversationState.PENDING.value)
        assert webhook_router._should_run_demo_truth_gate(policy, booking_wants_flow=True) is False

    def test_escalate_gate_respects_policy(self):
        pending_policy = webhook_router._get_routing_policy(ConversationState.PENDING.value)
        active_policy = webhook_router._get_routing_policy(ConversationState.BOT_ACTIVE.value)

        assert webhook_router._should_escalate_to_pending(pending_policy, Intent.HUMAN_REQUEST) is False
        assert webhook_router._should_escalate_to_pending(active_policy, Intent.HUMAN_REQUEST) is True


class TestFastIntent:
    @pytest.mark.parametrize(
        "message,expect_action,expect_intent",
        [
            ("Сәлем!", "smalltalk", "greeting"),
            ("спасибо", "smalltalk", "thanks"),
            ("ок", "smalltalk", "ack"),
        ],
    )
    def test_fast_intent_matches(self, message, expect_action, expect_intent):
        decision = webhook_router._detect_fast_intent(
            message,
            policy_type="demo_salon",
            booking_wants_flow=False,
            bypass_domain_flows=False,
        )

        assert decision is not None
        assert decision.action == expect_action
        assert decision.intent == expect_intent

    def test_fast_intent_fallback_to_llm(self):
        message = "Есть ли у вас абонементы?"
        decision = webhook_router._detect_fast_intent(
            message,
            policy_type="demo_salon",
            booking_wants_flow=False,
            bypass_domain_flows=False,
        )

        assert decision is None

        with patch("app.routers.webhook._legacy.classify_intent", return_value=Intent.QUESTION) as mock_classify:
            signals = webhook_router._detect_intent_signals(message)
        assert signals.intent == Intent.QUESTION
        mock_classify.assert_called_once()

    def test_human_request_overrides_short_question_hint(self):
        signals = webhook_router._detect_intent_signals(
            "позовите менеджера",
            timing_context={"short_intent_hint": Intent.QUESTION.value},
        )

        assert signals.intent == Intent.HUMAN_REQUEST


def test_llm_first_firebreak_out_of_domain_routes_to_ai_response():
    policy = webhook_router._get_routing_policy(ConversationState.BOT_ACTIVE.value)
    signals = webhook_router.DecisionSignals(
        intent=Intent.OUT_OF_DOMAIN,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )

    reasons = webhook_router._llm_first_firebreak_semantic_reasons(
        routing=policy,
        signals=signals,
        out_of_domain_signal=True,
        rag_confident=False,
        llm_first_firebreak=True,
    )
    assert reasons == ["out_of_domain_signal"]

    outcome = webhook_router._resolve_action(
        routing=policy,
        state=ConversationState.BOT_ACTIVE.value,
        signals=signals,
        is_pending_status_question=False,
        style_reference=False,
        out_of_domain_signal=True,
        rag_confident=False,
        llm_first_firebreak=True,
    )
    assert outcome.action == "ai_response"


def test_llm_first_firebreak_rejection_keeps_legacy_path_when_disabled():
    policy = webhook_router._get_routing_policy(ConversationState.BOT_ACTIVE.value)
    signals = webhook_router.DecisionSignals(
        intent=Intent.REJECTION,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )

    legacy_outcome = webhook_router._resolve_action(
        routing=policy,
        state=ConversationState.BOT_ACTIVE.value,
        signals=signals,
        is_pending_status_question=False,
        style_reference=False,
        out_of_domain_signal=False,
        rag_confident=False,
        llm_first_firebreak=False,
    )
    assert legacy_outcome.action == "rejection"

    reasons = webhook_router._llm_first_firebreak_semantic_reasons(
        routing=policy,
        signals=signals,
        out_of_domain_signal=False,
        rag_confident=False,
        llm_first_firebreak=True,
    )
    assert reasons == ["rejection_intent"]

    firebreak_outcome = webhook_router._resolve_action(
        routing=policy,
        state=ConversationState.BOT_ACTIVE.value,
        signals=signals,
        is_pending_status_question=False,
        style_reference=False,
        out_of_domain_signal=False,
        rag_confident=False,
        llm_first_firebreak=True,
    )
    assert firebreak_outcome.action == "ai_response"




def test_policy_collect_interrupt_arbitration_rewrites_master_query_to_info():
    action, info_refs, reason_code = webhook_router._resolve_policy_collect_interrupt_arbitration(
        policy_tool_action="collect",
        policy_intent="master_query",
        policy_pack_refs=["master"],
        message_text="Подскажите по мастерам.",
        client_slug="demo_salon",
        booking_wants_flow=True,
        booking_active=True,
        policy_goal="other",
    )

    assert action == "info"
    assert "master" in info_refs
    assert reason_code == "policy_collect_info_interrupt_owner"


def test_policy_collect_interrupt_arbitration_rewrites_price_question_to_info():
    action, info_refs, reason_code = webhook_router._resolve_policy_collect_interrupt_arbitration(
        policy_tool_action="collect",
        policy_intent="booking",
        policy_capability="pricing",
        policy_pack_refs=[],
        message_text="Сколько стоит маникюр?",
        client_slug="demo_salon",
        booking_wants_flow=True,
        booking_active=True,
        policy_goal="booking",
    )

    assert action == "info"
    assert "pricing" in info_refs
    assert reason_code == "policy_collect_info_interrupt_owner"


def test_policy_collect_interrupt_arbitration_rewrites_choose_specialist_question_to_info():
    action, info_refs, reason_code = webhook_router._resolve_policy_collect_interrupt_arbitration(
        policy_tool_action="collect",
        policy_intent="booking",
        policy_pack_refs=[],
        message_text="Могу ли я выбрать специалиста?",
        client_slug="demo_salon",
        booking_wants_flow=True,
        booking_active=True,
        policy_goal="booking",
    )

    assert action == "info"
    assert "master" in info_refs
    assert reason_code == "policy_collect_info_interrupt_owner"


def test_policy_collect_interrupt_arbitration_preserves_specialist_availability_followup_owner():
    action, info_refs, reason_code = webhook_router._resolve_policy_collect_interrupt_arbitration(
        policy_tool_action="collect",
        policy_intent="booking",
        policy_subject_kind="specialist",
        policy_capability="live_availability",
        policy_pack_refs=[],
        policy_pending_question_target="specialist",
        policy_temporal_scope="date_range",
        policy_active_question_relation="specialist_availability_followup",
        message_text="Какой мастер свободен на этой неделе?",
        client_slug="demo_salon",
        service_query="Маникюр",
        booking_wants_flow=True,
        booking_active=True,
        policy_goal="booking",
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
    )

    assert action == "collect"
    assert info_refs == []
    assert reason_code is None


@pytest.mark.parametrize(
    ("pending_question_act", "active_question_relation"),
    [
        ("ask_about_requested_slot", "ask_about_requested_slot"),
        ("slot_constraint", "slot_constraint"),
        ("slot_compare", "slot_compare"),
    ],
)
def test_policy_collect_interrupt_arbitration_preserves_active_time_slot_question_owner(
    pending_question_act,
    active_question_relation,
):
    action, info_refs, reason_code = webhook_router._resolve_policy_collect_interrupt_arbitration(
        policy_tool_action="collect",
        policy_intent="booking",
        policy_capability="live_availability",
        policy_pack_refs=[],
        policy_pending_question_act=pending_question_act,
        policy_pending_question_target="time",
        policy_active_question_relation=active_question_relation,
        message_text="Во сколько у вас свободные слоты?",
        client_slug="demo_salon",
        booking_wants_flow=True,
        booking_active=True,
        policy_goal="booking",
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
    )

    assert action == "collect"
    assert info_refs == []
    assert reason_code is None


def test_policy_collect_interrupt_arbitration_rewrites_active_time_duration_question_to_info():
    action, info_refs, reason_code = webhook_router._resolve_policy_collect_interrupt_arbitration(
        policy_tool_action="collect",
        policy_intent="booking",
        policy_subject_kind="booking",
        policy_capability="duration",
        policy_pack_refs=[],
        policy_pending_question_act="ask_about_requested_slot",
        policy_pending_question_target="time",
        policy_active_question_relation="ask_about_requested_slot",
        message_text="Что насчет времени выполнения?",
        client_slug="demo_salon",
        service_query="Маникюр",
        booking_state={"active": True, "service": "Маникюр"},
        booking_wants_flow=True,
        booking_active=True,
        policy_goal="booking",
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
    )

    assert action == "info"
    assert "duration" in info_refs
    assert reason_code == "policy_collect_info_interrupt_owner"


def test_policy_collect_interrupt_arbitration_keeps_hours_interrupt_without_active_slot_question_owner():
    action, info_refs, reason_code = webhook_router._resolve_policy_collect_interrupt_arbitration(
        policy_tool_action="collect",
        policy_intent="booking",
        policy_capability="hours",
        policy_pack_refs=[],
        message_text="Во сколько вы работаете?",
        client_slug="demo_salon",
        booking_wants_flow=True,
        booking_active=True,
        policy_goal="booking",
    )

    assert action == "info"
    assert "hours" in info_refs
    assert reason_code == "policy_collect_info_interrupt_owner"


def test_specialist_availability_followup_owner_allows_grounded_name_transition():
    assert webhook_router._should_preserve_specialist_availability_followup_owner(
        policy_goal="booking",
        policy_collect_slot="name",
        policy_pending_question_target="specialist",
        policy_subject_kind="specialist",
        policy_capability="live_availability",
        policy_temporal_scope="specific_time",
        policy_active_question_relation="specialist_availability_followup",
    )
    assert not webhook_router._should_preserve_specialist_availability_followup_owner(
        policy_goal="booking",
        policy_collect_slot="name",
        policy_pending_question_target="specialist",
        policy_subject_kind="specialist",
        policy_capability="live_availability",
        policy_temporal_scope="date_range",
        policy_active_question_relation="specialist_availability_followup",
    )


def test_active_name_time_availability_followup_owner_requires_specific_time_name_resume():
    assert webhook_router._should_preserve_active_name_time_availability_followup_owner(
        policy_goal="booking",
        policy_collect_slot="name",
        expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
        policy_resolution_mode="referent_followup",
        policy_pending_question_act="ask_about_requested_slot",
        policy_pending_question_target="time",
        policy_subject_kind="booking",
        policy_capability="live_availability",
        policy_temporal_scope="specific_time",
        policy_active_question_relation="ask_about_requested_slot",
    )
    assert webhook_router._should_preserve_active_name_time_availability_followup_owner(
        policy_goal="booking",
        policy_collect_slot="name",
        expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
        policy_resolution_mode="referent_followup",
        policy_pending_question_act="ask_about_requested_slot",
        policy_pending_question_target="time",
        policy_subject_kind="booking",
        policy_capability="bookability",
        policy_temporal_scope="specific_time",
        policy_active_question_relation="ask_about_requested_slot",
    )
    assert not webhook_router._should_preserve_active_name_time_availability_followup_owner(
        policy_goal="booking",
        policy_collect_slot="name",
        expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
        policy_resolution_mode="referent_followup",
        policy_pending_question_act="ask_about_requested_slot",
        policy_pending_question_target="specialist",
        policy_subject_kind="booking",
        policy_capability="live_availability",
        policy_temporal_scope="specific_time",
        policy_active_question_relation="ask_about_requested_slot",
    )
    assert not webhook_router._should_preserve_active_name_time_availability_followup_owner(
        policy_goal="booking",
        policy_collect_slot="name",
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        policy_resolution_mode="referent_followup",
        policy_pending_question_act="ask_about_requested_slot",
        policy_pending_question_target="time",
        policy_subject_kind="booking",
        policy_capability="live_availability",
        policy_temporal_scope="specific_time",
        policy_active_question_relation="ask_about_requested_slot",
    )
    assert webhook_router._should_preserve_active_name_time_availability_followup_owner(
        policy_goal="booking",
        policy_collect_slot="name",
        expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
        policy_resolution_mode="referent_followup",
        policy_pending_question_act=None,
        policy_pending_question_target=None,
        policy_subject_kind="booking",
        policy_capability="live_availability",
        policy_temporal_scope="specific_time",
        policy_active_question_relation=None,
    )
    assert not webhook_router._should_preserve_active_name_time_availability_followup_owner(
        policy_goal="booking",
        policy_collect_slot="name",
        expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
        policy_resolution_mode="direct",
        policy_pending_question_act=None,
        policy_pending_question_target=None,
        policy_subject_kind="booking",
        policy_capability="live_availability",
        policy_temporal_scope="specific_time",
        policy_active_question_relation=None,
    )




def test_truth_gate_appends_booking_cta_for_info_reply():
    saved_message = SimpleNamespace(message_metadata={})
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})

    decision = DemoSalonDecision(action="reply", response="Работаем с 9:00 до 21:00.", intent="hours")

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return decision

    response = webhook_router._handle_truth_gate_fallback(
        db=Mock(),
        conversation=conversation,
        user=user,
        message_text="Когда вы работаете?",
        saved_message=saved_message,
        client_slug="demo_salon",
        routing={"allow_booking_flow": True, "allow_handover_create": False},
        booking_wants_flow=False,
        policy_handler={"policy_type": "demo_salon", "truth_gate": _truth_gate},
        policy_type="demo_salon",
        current_goal=None,
        intent_decomp_used=False,
        intent_decomp_intents=[],
        intent_decomp_payload=None,
        llm_primary_reason="low_confidence",
        message_count=1,
        now=datetime.now(timezone.utc),
        consult_return_pending=False,
        consult_return_prompt=None,
        consult_context=None,
        consult_return_reason=None,
        maybe_apply_fact_guard=lambda **_kwargs: None,
        send_and_save=lambda text: (text, True),
        log_timing=lambda *args, **_kwargs: None,
        record_escalation_metric=lambda *_args, **_kwargs: None,
    )

    assert response is not None
    assert decision.response in (response.bot_response or "")
    assert (response.bot_response or "").endswith(webhook_router.MSG_BOOKING_CTA)


def test_fact_guard_reason_ignores_missing_slot_tool_decisions():
    assert (
        _fact_guard_reason(
            {
                "fact_source": "truth",
                "tool_action": "catalog.service_query",
                "tool_decision": "missing_slot",
            }
        )
        is None
    )


def test_truth_gate_off_topic_handles_simplenamespace_message_metadata():
    saved_message = SimpleNamespace(
        message_metadata={"decision_meta": {"expected_reply_matched": False}}
    )
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={"expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE},
    )
    user = SimpleNamespace(id="user-123", context={})

    decision = DemoSalonDecision(
        action="reply",
        response="Извините, это не по теме.",
        intent="off_topic",
    )

    def _truth_gate(_message: str, *, client_slug: str | None = None, intent_decomp: dict | None = None):
        return decision

    response = webhook_router._handle_truth_gate_fallback(
        db=Mock(),
        conversation=conversation,
        user=user,
        message_text="ок",
        saved_message=saved_message,
        client_slug="demo_salon",
        routing={"allow_booking_flow": True, "allow_handover_create": False},
        booking_wants_flow=False,
        policy_handler={"policy_type": "demo_salon", "truth_gate": _truth_gate},
        policy_type="demo_salon",
        current_goal=None,
        intent_decomp_used=False,
        intent_decomp_intents=[],
        intent_decomp_payload=None,
        llm_primary_reason="low_confidence",
        message_count=1,
        now=datetime.now(timezone.utc),
        consult_return_pending=False,
        consult_return_prompt=None,
        consult_context=None,
        consult_return_reason=None,
        maybe_apply_fact_guard=lambda **_kwargs: None,
        send_and_save=lambda text: (text, True),
        log_timing=lambda *args, **_kwargs: None,
        record_escalation_metric=lambda *_args, **_kwargs: None,
    )

    assert response is not None
    assert webhook_router.MSG_EXPECTED_SERVICE_OFF_TOPIC in (response.bot_response or "")
    decision_meta = saved_message.message_metadata.get("decision_meta", {})
    assert decision_meta.get("expected_reply_guard") == "truth_gate_off_topic_override"


def test_strict_ood_sets_out_of_domain_without_in_signals():
    conversation = SimpleNamespace(
        id="conv-ood-1",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.OTHER,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(DomainIntent.UNKNOWN, 0.0, 0.0, {}),
    ):
        result = webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=None,
            message_text="какая погода?",
            client_slug="demo_salon",
            client_config={},
            remote_jid=None,
            timing_context={},
            info_class_intents=set(),
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    assert result.out_of_domain_signal is True
    assert "out_of_domain" in (result.class_router_result.get("classes") or [])


def test_strict_ood_skips_out_of_domain_with_in_signals():
    conversation = SimpleNamespace(
        id="conv-ood-2",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.OTHER,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(DomainIntent.UNKNOWN, 0.0, 0.0, {}),
    ):
        result = webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=None,
            message_text="когда работаете?",
            client_slug="demo_salon",
            client_config={},
            remote_jid=None,
            timing_context={},
            info_class_intents={"hours"},
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    assert result.out_of_domain_signal is False


def test_strict_ood_skips_out_of_domain_with_service_request_signal():
    conversation = SimpleNamespace(
        id="conv-ood-3",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.OTHER,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(
            DomainIntent.OUT_OF_DOMAIN,
            0.0,
            0.9,
            {"out_hits": 1, "strict_in_hits": 0},
        ),
    ):
        result = webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=None,
            message_text="Вырыть бассейн в холле",
            client_slug="demo_salon",
            client_config={},
            remote_jid=None,
            timing_context={},
            info_class_intents={"pricing"},
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    assert result.out_of_domain_signal is False
    assert "explicit_service" in (result.class_router_result.get("in_signals") or [])


def test_signal_snapshot_written_on_class_router():
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        id="conv-snapshot-1",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.QUESTION,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )
    domain_meta = {
        "in_threshold": 0.6,
        "out_threshold": 0.6,
        "margin": 0.1,
        "in_hits": 2,
        "out_hits": 0,
        "strict_in_hits": 1,
        "anchors_in": 12,
        "anchors_out": 6,
        "strict_in_anchors": 4,
    }
    class_router_result = {
        "out_of_domain_signal": False,
        "in_signals": ["explicit_service"],
        "out_signals": [],
        "classes": ["info_bundle"],
        "intents": ["location"],
        "carryover_intents": [],
        "carryover_class": None,
        "carryover_info_sections": None,
        "router_fallback_reason": None,
        "controller_fallback_reason": None,
        "router": {"eligible": True},
        "controller": {
            "used": True,
            "attempted": True,
            "fallback": False,
            "low_confidence": False,
            "confidence": 0.82,
            "goal": "info",
        },
    }

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(DomainIntent.IN_DOMAIN, 0.77, 0.12, domain_meta),
    ), patch(
        "app.routers.webhook._legacy._resolve_class_router_result",
        return_value=class_router_result,
    ), patch(
        "app.routers.webhook.decision._has_explicit_service_signal", return_value=True
    ):
        webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=saved_message,
            message_text="Где вы находитесь?",
            client_slug="demo_salon",
            client_config={},
            remote_jid=None,
            timing_context={},
            info_class_intents=set(),
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    meta = saved_message.message_metadata.get("decision_meta", {})
    snapshot = meta.get("signal_snapshot", {})
    assert snapshot.get("domain_router", {}).get("intent") == "in_domain"
    assert snapshot.get("class_router", {}).get("out_of_domain_signal") is False
    assert snapshot.get("intent_signals", {}).get("intent") == "question"


def test_signal_snapshot_records_pack_index_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        id="conv-snapshot-pack-index",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    signals = DecisionSignals(
        intent=Intent.QUESTION,
        is_greeting=False,
        is_thanks=False,
        is_ack=False,
        is_low_signal=False,
        is_status_question=False,
    )
    domain_meta = {
        "in_threshold": 0.6,
        "out_threshold": 0.6,
        "margin": 0.1,
        "in_hits": 1,
        "out_hits": 0,
        "strict_in_hits": 0,
        "anchors_in": 4,
        "anchors_out": 2,
        "strict_in_anchors": 0,
    }
    class_router_result = {
        "out_of_domain_signal": False,
        "in_signals": ["explicit_service"],
        "out_signals": [],
        "classes": ["info_bundle"],
        "intents": ["location"],
        "carryover_intents": [],
        "carryover_class": None,
        "carryover_info_sections": None,
        "router_fallback_reason": None,
        "controller_fallback_reason": None,
        "router": {"eligible": True},
        "controller": {
            "used": True,
            "attempted": True,
            "fallback": False,
            "low_confidence": False,
            "confidence": 0.82,
            "goal": "info",
        },
    }
    client_config = {
        "pack_index": {
            "schema_version": "pack_index.v1",
            "hash": "hash-123",
            "version_id": "version-123",
            "compiled_at": "2026-01-31T00:00:00+00:00",
            "source": "knowledge_publish",
        }
    }

    with patch(
        "app.routers.webhook.decision._detect_intent_signals", return_value=signals
    ), patch(
        "app.routers.webhook._legacy.classify_domain_with_scores",
        return_value=(DomainIntent.IN_DOMAIN, 0.77, 0.12, domain_meta),
    ), patch(
        "app.routers.webhook._legacy._resolve_class_router_result",
        return_value=class_router_result,
    ), patch(
        "app.routers.webhook.decision._has_explicit_service_signal", return_value=True
    ):
        webhook_router._run_class_router_stage(
            conversation=conversation,
            saved_message=saved_message,
            message_text="Где вы находитесь?",
            client_slug="demo_salon",
            client_config=client_config,
            remote_jid=None,
            timing_context={},
            info_class_intents=set(),
            info_class_meta={},
            booking_signal=False,
            class_carryover=None,
            router_state=None,
            intent_decomp_payload=None,
            expected_reply_shortcircuit=False,
            log_timing=lambda *args, **_kwargs: None,
        )

    meta = saved_message.message_metadata.get("decision_meta", {})
    snapshot = meta.get("signal_snapshot", {})
    pack_index = snapshot.get("pack_index", {})
    assert pack_index.get("hash") == "hash-123"
    assert pack_index.get("version_id") == "version-123"




def test_signal_snapshot_records_rag_meta():
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(id="conv-rag-1", context={})
    timing_context = {
        "rag_scores": {"vector_count": 1, "bm25_count": 0, "vector_score": 0.42},
        "rag_attempted": True,
        "rag_best_score": 0.42,
        "branch_id": "branch-1",
        "knowledge_tag": "tag-1",
    }

    webhook_response._record_rag_meta(
        conversation=conversation,
        saved_message=saved_message,
        timing_context=timing_context,
    )

    meta = saved_message.message_metadata.get("decision_meta", {})
    snapshot = meta.get("signal_snapshot", {})
    rag_snapshot = snapshot.get("rag", {})
    assert rag_snapshot.get("scores", {}).get("vector_count") == 1
    assert rag_snapshot.get("attempted") is True
    assert snapshot.get("knowledge", {}).get("knowledge_tag") == "tag-1"


























def test_session_reset_marker_is_stripped():
    text = "начнем сначала [LC:AUTO:CA05:RESET:20260126-123000]"
    assert _is_session_reset_only_message(text) is True


















def test_legacy_service_carryover_reads_from_canonical_dialog_state():
    context_manager = {
        "canonical_dialog_state": {
            "owner_id": "context_manager.dialog_state.v1",
            "version": "v1",
            "current_referents": {
                "service": {
                    "value": "маникюр",
                    "source": "semantic_match",
                    "score": 0.72,
                    "message_count": 4,
                    "ttl": 4,
                }
            },
        }
    }

    carryover = webhook_router._get_service_carryover(context_manager, message_count=5)

    assert carryover == {
        "service_query": "маникюр",
        "service_query_source": "semantic_match",
        "service_query_score": 0.72,
        "age": 1,
        "ttl": 4,
        "remaining": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }


def test_legacy_class_carryover_reads_from_canonical_dialog_state():
    context_manager = {
        "canonical_dialog_state": {
            "owner_id": "context_manager.dialog_state.v1",
            "version": "v1",
            "meta": {
                "class_carryover": {
                    "class": "info_bundle",
                    "intents": ["parking"],
                    "info_sections": ["parking"],
                    "message_count": 4,
                    "ttl": 4,
                }
            },
        }
    }

    carryover = webhook_router._get_class_carryover(context_manager, message_count=5)

    assert carryover == {
        "class": "info_bundle",
        "intents": ["parking"],
        "info_sections": ["parking"],
        "age": 1,
        "ttl": 4,
        "remaining": 4,
    }


def test_legacy_class_carryover_setter_syncs_canonical_dialog_state():
    context_manager = webhook_router._set_class_carryover(
        {},
        class_name="info_bundle",
        intents=[" parking ", "parking"],
        info_sections=[" parking ", ""],
        message_count=4,
    )

    assert context_manager.get(webhook_router.CLASS_CARRYOVER_KEY) == {
        "class": "info_bundle",
        "intents": ["parking"],
        "info_sections": ["parking"],
        "message_count": 4,
        "ttl": 4,
    }
    assert context_manager.get("canonical_dialog_state", {}).get("meta", {}).get("class_carryover") == {
        "class": "info_bundle",
        "intents": ["parking"],
        "info_sections": ["parking"],
        "message_count": 4,
        "ttl": 4,
    }


def test_legacy_consult_context_reads_from_canonical_dialog_state():
    context_manager = {
        "canonical_dialog_state": {
            "owner_id": "context_manager.dialog_state.v1",
            "version": "v1",
            "consult_state": {
                "topic": "nails_design",
                "question": "Что нравится в дизайне?",
                "questions": ["Что нравится в дизайне?"],
                "message_count": 4,
                "ttl": 4,
            },
        }
    }

    consult_context = webhook_router._get_consult_context(context_manager, message_count=5)

    assert consult_context == {
        "topic": "nails_design",
        "question": "Что нравится в дизайне?",
        "questions": ["Что нравится в дизайне?"],
        "age": 1,
        "ttl": 4,
        "remaining": 4,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }


def test_legacy_consult_context_setter_syncs_canonical_dialog_state():
    context_manager = webhook_router._set_consult_context(
        {},
        consult_meta={
            "consult_topic": " nails_design ",
            "consult_question": " Что нравится в дизайне? ",
            "consult_questions": [" Что нравится в дизайне ", " "],
        },
        message_count=4,
    )

    assert context_manager.get("consult_context") == {
        "questions": ["Что нравится в дизайне?"],
        "topic": "nails_design",
        "question": "Что нравится в дизайне?",
        "message_count": 4,
        "ttl": 6,
        "projection_source": "canonical_dialog_state",
        "canonical_state_owner": "context_manager.dialog_state.v1",
    }
    assert context_manager.get("canonical_dialog_state", {}).get("consult_state") == {
        "topic": "nails_design",
        "question": "Что нравится в дизайне?",
        "questions": ["Что нравится в дизайне?"],
        "message_count": 4,
        "ttl": 6,
    }


def test_canonical_dialog_state_preserves_current_service_across_consult_to_booking_followup():
    context_manager = {
        "message_count": 4,
        "canonical_dialog_state": {
            "owner_id": "context_manager.dialog_state.v1",
            "version": "v1",
            "current_referents": {
                "service": {
                    "value": "маникюр",
                    "source": "consult_context",
                    "score": 1.0,
                    "message_count": 4,
                    "ttl": 4,
                }
            },
            "consult_state": {
                "topic": "pricing",
                "question": "Сколько стоит маникюр?",
                "questions": ["Сколько стоит маникюр?"],
                "message_count": 4,
                "ttl": 4,
            },
        },
    }

    carryover = webhook_router._get_service_carryover(context_manager, message_count=5)
    assert carryover is not None
    assert carryover.get("service_query") == "маникюр"
    assert carryover.get("projection_source") == "canonical_dialog_state"
    assert carryover.get("canonical_state_owner") == "context_manager.dialog_state.v1"

    booking_state, prompt = webhook_router._next_booking_prompt(
        {
            "active": True,
            "service": carryover.get("service_query"),
        },
        refusal_flags=None,
        client_slug="demo_salon",
    )

    assert booking_state.get("service") == "маникюр"
    assert booking_state.get("last_question") == "datetime"
    assert prompt == webhook_router.MSG_BOOKING_ASK_DATETIME


def test_canonical_dialog_state_syncs_interaction_state_from_policy_contract():
    context_manager = {"message_count": 4}

    synced_manager = webhook_router._sync_canonical_dialog_state(
        context_manager,
        booking_state={
            "active": True,
            "service": "маникюр",
            "specialist_name": "Айгерим",
            "confirmation": {
                "slot": "datetime",
                "value": "2026-03-15T15:00:00+05:00",
                "source": "llm_slot",
            },
        },
        expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
        expected_reply_reason="booking_followup",
        message_count=5,
        branch_id="branch-1",
        interaction_target="time",
        interaction_relation="ask_about_requested_slot",
        degrade_reason="policy_validation:slot_followup_recovered",
    )

    canonical_state = webhook_router._get_canonical_dialog_state(synced_manager)
    assert canonical_state.get("pending_question_contract") == {
        "expected_reply_type": "name",
        "reason": "booking_followup",
        "next_question": "name",
        "open_questions": ["name"],
    }
    interaction_state = canonical_state.get("interaction_state") or {}

    assert interaction_state == {
        "resume_slot": "name",
        "interaction_target": "time",
        "interaction_relation": "ask_about_requested_slot",
        "interaction_owner": "llm_policy_core:ask_about_requested_slot",
        "grounded_referents": {
            "service": "маникюр",
            "specialist": "Айгерим",
            "branch": "branch-1",
        },
        "confirmation_state": {
            "required": True,
            "slot": "datetime",
            "value": "2026-03-15T15:00:00+05:00",
            "source": "llm_slot",
        },
        "degrade_reason": "policy_validation:slot_followup_recovered",
    }


def test_context_manager_expected_reply_getters_prefer_canonical_question_contract():
    context = {
        "expected_reply_type": webhook_router.EXPECTED_REPLY_SERVICE,
        "expected_reply_reason": "booking_prompt",
        "context_manager": {
            "canonical_dialog_state": {
                "pending_question_contract": {
                    "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
                    "reason": "booking_interrupt",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                }
            }
        },
    }

    assert _get_expected_reply_type(context) == webhook_router.EXPECTED_REPLY_TIME
    assert _get_expected_reply_reason(context) == "booking_interrupt"

    updated = _set_expected_reply_type(context, webhook_router.EXPECTED_REPLY_NAME)

    assert _get_expected_reply_type(updated) == webhook_router.EXPECTED_REPLY_NAME
    assert (
        updated.get("context_manager", {})
        .get("canonical_dialog_state", {})
        .get("pending_question_contract")
        == {
            "expected_reply_type": webhook_router.EXPECTED_REPLY_NAME,
            "next_question": "name",
            "open_questions": ["name"],
        }
    )

    cleared = _set_expected_reply_type(updated, None)

    assert _get_expected_reply_type(cleared) is None
    assert (
        cleared.get("context_manager", {})
        .get("canonical_dialog_state", {})
        .get("pending_question_contract")
        is None
    )


def test_set_expected_reply_context_records_canonical_pending_question_contract_in_evidence():
    now = datetime.now(timezone.utc)
    saved_message = SimpleNamespace(message_metadata={})
    conversation = SimpleNamespace(
        context={
            "context_manager": {
                "message_count": 4,
                "current_goal": "booking",
            },
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
        }
    )

    updated = webhook_router._set_expected_reply_context(
        conversation=conversation,
        saved_message=saved_message,
        context=conversation.context,
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        reason="booking_prompt",
        now=now,
    )

    expected_contract = {
        "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        "reason": "booking_prompt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }
    assert (
        updated.get("context_manager", {})
        .get("canonical_dialog_state", {})
        .get("pending_question_contract")
        == expected_contract
    )
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "question_contract"
        and entry.get("decision") == "set"
        and entry.get("pending_question_contract") == expected_contract
        for entry in trace
        if isinstance(entry, dict)
    )
    assert (
        saved_message.message_metadata.get("decision_meta", {}).get("pending_question_contract")
        == expected_contract
    )








def test_semantic_service_matcher_returns_not_found_on_empty_rag():
    saved_message = SimpleNamespace(message_metadata={})
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})
    timing_context = {
        "rag_attempted": True,
        "rag_scores": {"vector_count": 0, "bm25_count": 0},
        "llm_used": False,
        "llm_timeout": False,
        "llm_cache_hit": False,
    }
    llm_primary_result = SimpleNamespace(ok=True, value=(None, "low_confidence"))
    intent_decomp_payload = {
        "intents": ["other"],
        "service_query": "стрижка",
        "service_query_source": "intent_decomp",
    }

    with patch(
        "app.routers.webhook._legacy.semantic_service_match", return_value=None
    ), patch(
        "app.routers.webhook._legacy.rewrite_for_service_match", return_value=None
    ), patch(
        "app.routers.webhook._legacy._extract_service_hint", return_value=None
    ), patch(
        "app.routers.webhook._legacy._record_knowledge_backlog"
    ):
        outcome = webhook_response._handle_ai_response_action(
            db=Mock(),
            conversation=conversation,
            user=user,
            message_text="делаете стрижку?",
            saved_message=saved_message,
            client_slug="demo_salon",
            client_id="client-123",
            client_config={},
            routing={"allow_handover_create": False},
            intent=Intent.QUESTION,
            llm_primary_result=llm_primary_result,
            append_user_message=False,
            timing_context=timing_context,
            intent_decomp_payload=intent_decomp_payload,
            class_router_result={"in_signals": [], "anchors_in_hits": 0},
            expected_reply_shortcircuit=False,
            out_of_domain_signal=False,
            booking_signal=False,
            info_class_intents=set(),
            current_goal=None,
            now=datetime.now(timezone.utc),
            send_and_save=lambda text: (text, True),
            send_response=lambda text: True,
            finalize_response=lambda **_kwargs: None,
        )

    assert outcome.bot_response is not None
    assert "В списке услуг нет такой позиции" in outcome.bot_response
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("intent") == "service_not_found"
    assert meta.get("source") == "service_semantic_matcher"


def test_rag_rewrite_and_scores_logged():
    saved_message = SimpleNamespace(message_metadata={})
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    user = SimpleNamespace(id="user-123", user_metadata={})
    timing_context: dict = {}

    def fake_generate_bot_response(*args, **kwargs):
        timing_context = kwargs.get("timing_context")
        if isinstance(timing_context, dict):
            rag_scores = {
                "vector_max": 0.0,
                "bm25_max": 1.2,
                "hybrid_max": 0.8,
                "retrieval_mode": "sparse_only",
                "dense_unavailable_reason": "bge_dns_failure",
                "dense_available": False,
            }
            timing_context["rag_trace"] = [
                {
                    "stage": "rag_retrieve",
                    "phase": "generate",
                    "retry": False,
                    "query": "адрес салона",
                    "results": 1,
                    "rag_scores": rag_scores,
                }
            ]
            timing_context["rag_scores"] = rag_scores
            timing_context["rag_best_score"] = 0.6
            timing_context["rag_attempted"] = True
        return Result.success(("Адрес: Абая 150", "high"))

    intent_decomp_payload = {
        "intents": ["other"],
        "service_query": "",
    }

    with patch(
        "app.services.ai_service.rewrite_query_for_retrieval",
        return_value={"rewrite_used": True, "rewrite_text": "адрес салона", "reason": "rewritten"},
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        side_effect=fake_generate_bot_response,
    ):
        outcome = webhook_response._handle_ai_response_action(
            db=Mock(),
            conversation=conversation,
            user=user,
            message_text="чо по адресу",
            saved_message=saved_message,
            client_slug="demo_salon",
            client_id="client-123",
            client_config={},
            routing={"allow_handover_create": False},
            intent=Intent.QUESTION,
            llm_primary_result=None,
            append_user_message=False,
            timing_context=timing_context,
            intent_decomp_payload=intent_decomp_payload,
            class_router_result={"in_signals": [], "anchors_in_hits": 0},
            expected_reply_shortcircuit=False,
            out_of_domain_signal=False,
            booking_signal=False,
            info_class_intents=set(),
            current_goal=None,
            now=datetime.now(timezone.utc),
            send_and_save=lambda text, **_kwargs: (text, True),
            send_response=lambda text: True,
            finalize_response=lambda **_kwargs: None,
        )

    assert outcome.bot_response is not None
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("rewrite_used") is True
    assert meta.get("rewrite_text") == "адрес салона"
    assert meta.get("rag_scores") == {
        "vector_max": 0.0,
        "bm25_max": 1.2,
        "hybrid_max": 0.8,
        "retrieval_mode": "sparse_only",
        "dense_unavailable_reason": "bge_dns_failure",
        "dense_available": False,
    }
    assert meta.get("rag_confident") is True
    assert meta.get("rag_reason") is None
    trace = conversation.context.get("decision_trace", [])
    assert any(entry.get("stage") == "rewrite" for entry in trace if isinstance(entry, dict))
    assert any(entry.get("stage") == "rag_retrieve" for entry in trace if isinstance(entry, dict))


def test_record_rag_meta_sets_branch_id():
    conversation = SimpleNamespace(context={})
    saved_message = SimpleNamespace(message_metadata={})
    branch_id = "b7f75692-951e-421a-aae6-f5db97394799"
    timing_context = {
        "rag_scores": {"vector_max": 0.6, "bm25_max": 1.2, "hybrid_max": 0.8},
        "rag_best_score": 0.6,
        "rag_attempted": True,
        "branch_id": branch_id,
    }

    with patch("app.routers.webhook.response._record_llm_budget_trace"), patch(
        "app.routers.webhook.response._record_llm_degradation"
    ), patch("app.routers.webhook.response._record_decision_trace"):
        webhook_response._record_rag_meta(
            conversation=conversation,
            saved_message=saved_message,
            timing_context=timing_context,
        )

    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("branch_id") == branch_id


def test_semantic_service_matcher_allows_short_query_without_keywords():
    results = [
        {
            "score": 0.5,
            "payload": {"canonical_name": "Маникюр"},
        }
    ]

    with patch(
        "app.services.demo_salon_knowledge._search_services_index", return_value=results
    ), patch(
        "app.services.demo_salon_knowledge._format_semantic_service_reply",
        return_value="Маникюр — 2 500 ₸.",
    ):
        result = semantic_service_match("манник?", "demo_salon")

    assert result is not None
    assert result.action == "match"
    assert result.canonical_name == "Маникюр"
    assert isinstance(result.response, str) and result.response


def test_semantic_service_matcher_returns_suggestions_reply():
    results = [
        {"score": 0.35, "payload": {"canonical_name": "Маникюр"}},
        {"score": 0.32, "payload": {"canonical_name": "Педикюр"}},
    ]
    truth = {
        "services_catalog": {
            "not_found_reply": "В списке услуг нет такой позиции. Возможно, вы имели в виду: {suggestions}.",
        }
    }

    with patch(
        "app.services.demo_salon_knowledge._search_services_index", return_value=results
    ), patch(
        "app.services.demo_salon_knowledge.load_yaml_truth", return_value=truth
    ):
        result = semantic_service_match("маникюр?", "demo_salon")

    assert result is not None
    assert result.action == "suggest"
    assert result.canonical_name == "Маникюр"
    assert set(result.suggestions or []) == {"Маникюр", "Педикюр"}
    assert isinstance(result.response, str) and result.response


def test_semantic_question_type_routes_duration_and_price():
    import app.services.demo_salon_knowledge as demo_salon_knowledge

    def fake_embedding(text: str):
        normalized = text.casefold()
        if "дл" in normalized or "врем" in normalized:
            return [1.0, 0.0]
        if "стоит" in normalized or "цена" in normalized or "прайс" in normalized:
            return [0.0, 1.0]
        return [0.1, 0.1]

    def fake_search(text: str, client_slug: str, limit: int):
        normalized = text.casefold()
        if "маник" in normalized:
            return [{"score": 0.9, "payload": {"canonical_name": "Маникюр"}}]
        return []

    with patch("app.services.demo_salon_knowledge.get_embedding", side_effect=fake_embedding), patch(
        "app.services.demo_salon_knowledge._search_services_index", side_effect=fake_search
    ):
        demo_salon_knowledge._question_type_examples.cache_clear()
        demo_salon_knowledge._question_type_embeddings.cache_clear()

        decision = get_demo_salon_decision("Сколько длится процедура?")
        assert decision is not None
        assert decision.intent == "service_duration"
        assert decision.action == "reply"
        fact_intents = set(decision.meta.get("fact_intents") or [])
        assert "service_duration" in fact_intents
        assert decision.meta.get("question_type") == "duration"

        decision = get_demo_salon_decision("Сколько стоит процедура?")
        assert decision is not None
        assert decision.intent == "service_clarify"
        assert decision.action == "reply"
        fact_intents = set(decision.meta.get("fact_intents") or [])
        assert "service_clarify" in fact_intents

        decision = get_demo_salon_decision("Сколько по времени маникюр?")
        assert decision is not None
        assert decision.intent == "service_duration"
        assert decision.action == "reply"
        fact_intents = set(decision.meta.get("fact_intents") or [])
        assert "service_duration" in fact_intents
        assert (decision.meta.get("duration_item") or "").casefold() == "маникюр"






































def test_expected_reply_contract_bypasses_human_request():
    from app.routers.webhook import decision as decision_router

    now = datetime.now(timezone.utc)
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "session_memory": {
                "last_question_type": webhook_router.EXPECTED_REPLY_TIME,
                "unanswered_questions": [
                    webhook_router.EXPECTED_REPLY_TIME,
                    webhook_router.EXPECTED_REPLY_NAME,
                ],
                "pending_slots": {"datetime": "завтра 12:00", "name": "Лена"},
                "last_updated_at": now.isoformat(),
                "ttl_hours": 24,
            },
        },
        state=ConversationState.BOT_ACTIVE.value,
    )

    with patch("app.routers.webhook._legacy.interpret_expected_reply") as interpret_expected_reply:
        state = decision_router._apply_expected_reply_contract(
            conversation=conversation,
            saved_message=saved_message,
            message_text="позовите менеджера",
            batch_messages=["позовите менеджера"],
            context=conversation.context,
            context_manager={},
            now=now,
            current_goal="booking",
            class_carryover=None,
            message_count=1,
            policy_type=None,
            policy_pack=None,
            client_slug="demo_salon",
        )

    assert interpret_expected_reply.call_count == 0
    assert state.expected_reply_shortcircuit is False
    assert state.expected_reply_type is None
    assert conversation.context.get("expected_reply_type") is None
    session_memory = conversation.context.get("session_memory") or {}
    assert session_memory.get("last_question_type") is None
    assert webhook_router.EXPECTED_REPLY_TIME not in (session_memory.get("unanswered_questions") or [])
    pending_slots = session_memory.get("pending_slots") or {}
    assert "datetime" not in pending_slots
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_bypassed") == "human_request"
    assert meta.get("session_memory_expected_reply_cleared") is True


def test_expected_reply_contract_prefers_session_memory_pending_question_contract() -> None:
    from app.routers.webhook import decision as decision_router

    now = datetime.now(timezone.utc)
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        context={
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": webhook_router.EXPECTED_REPLY_SERVICE,
                "pending_question_contract": {
                    "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
                    "reason": "booking_interrupt",
                    "next_question": "datetime",
                    "open_questions": ["datetime"],
                },
                "last_updated_at": now.isoformat(),
                "ttl_hours": 24,
            },
        },
        state=ConversationState.BOT_ACTIVE.value,
    )

    with patch(
        "app.routers.webhook.decision._match_expected_reply_candidates",
        return_value=(False, None, []),
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
        return_value={"ok": False, "payload": {}, "error": "no_match", "raw": None},
    ):
        state = decision_router._apply_expected_reply_contract(
            conversation=conversation,
            saved_message=saved_message,
            message_text="завтра",
            batch_messages=["завтра"],
            context=conversation.context,
            context_manager={},
            now=now,
            current_goal="booking",
            class_carryover=None,
            message_count=1,
            policy_type=None,
            policy_pack=None,
            client_slug="demo_salon",
        )

    assert state.memory_expected_reply_type == webhook_router.EXPECTED_REPLY_TIME
    assert state.expected_reply_type is None
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("session_memory_expected_reply") == webhook_router.EXPECTED_REPLY_TIME
    assert meta.get("session_memory_expected_reply_reason") == "booking_interrupt"


def test_should_block_expected_reply_time_for_question_without_datetime():
    from app.routers.webhook import decision as decision_router

    blocked = decision_router._should_block_expected_reply_by_info(
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        message_text="Можно ли совместить чистку лица и пилинг в один день?",
        client_slug="demo_salon",
    )

    assert blocked is True


def test_should_not_block_expected_reply_time_for_grounded_datetime_reply():
    from app.routers.webhook import decision as decision_router

    blocked = decision_router._should_block_expected_reply_by_info(
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        message_text="Завтра в 18:00",
        client_slug="demo_salon",
    )

    assert blocked is False


def test_should_not_block_expected_reply_time_for_booking_question_with_datetime():
    from app.routers.webhook import decision as decision_router

    blocked = decision_router._should_block_expected_reply_by_info(
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        message_text="Можно сегодня записаться прямо сейчас?",
        client_slug="demo_salon",
    )

    assert blocked is False




def test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue():
    from app.routers.webhook import decision as decision_router

    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "intent_queue": ["pricing"],
            "booking": {
                "active": True,
                "service": "Женская стрижка",
                "datetime": "среду",
                "last_question": "datetime",
            },
        },
        state=ConversationState.BOT_ACTIVE.value,
    )

    expected_reply_result = {
        "ok": False,
        "payload": {"slot": "datetime", "value": "", "confidence": 0.0, "reason": "deterministic"},
        "error": "deterministic",
        "raw": None,
    }

    with patch(
        "app.routers.webhook.decision._match_expected_reply_candidates",
        return_value=(True, "19:00", []),
    ), patch(
        "app.routers.webhook.decision._is_booking_confirm_enabled",
        return_value=False,
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
        return_value=expected_reply_result,
    ):
        state = decision_router._apply_expected_reply_contract(
            conversation=conversation,
            saved_message=saved_message,
            message_text="19:00",
            batch_messages=["19:00"],
            context=conversation.context,
            context_manager={},
            now=datetime.now(timezone.utc),
            current_goal="booking",
            class_carryover=None,
            message_count=1,
            policy_type=None,
            policy_pack=None,
            client_slug="demo_salon",
        )

    booking_state = conversation.context.get("booking") or {}
    assert booking_state.get("datetime") == "среду 19:00"
    assert conversation.context.get("expected_reply_type") is None
    assert conversation.context.get("intent_queue") is None
    assert state.expected_reply_type is None
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_matched") is True
    assert meta.get("intent_queue_cleared") == "booking_expected_reply"


def test_expected_reply_time_question_like_info_does_not_match_deterministic():
    from app.routers.webhook import decision as decision_router

    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "booking": {
                "active": True,
                "service": "чистка лица",
                "last_question": "datetime",
            },
        },
        state=ConversationState.BOT_ACTIVE.value,
    )

    with patch(
        "app.routers.webhook.decision._match_expected_reply_candidates",
        return_value=(True, "в один день", []),
    ), patch(
        "app.routers.webhook.decision._is_booking_confirm_enabled",
        return_value=False,
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
    ) as interpret_expected_reply:
        state = decision_router._apply_expected_reply_contract(
            conversation=conversation,
            saved_message=saved_message,
            message_text="Можно ли совместить чистку лица и пилинг в один день?",
            batch_messages=["Можно ли совместить чистку лица и пилинг в один день?"],
            context=conversation.context,
            context_manager={},
            now=datetime.now(timezone.utc),
            current_goal="booking",
            class_carryover=None,
            message_count=1,
            policy_type=None,
            policy_pack=None,
            client_slug="demo_salon",
        )

    assert interpret_expected_reply.call_count == 0
    assert state.expected_reply_matched is False
    assert state.expected_reply_type == webhook_router.EXPECTED_REPLY_TIME
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_blocked_by_info") is True
    assert meta.get("expected_reply_matched") is False


def test_expected_reply_time_slot_mismatch_captures_alternate_name_without_clearing_time():
    from app.routers.webhook import decision as decision_router

    now = datetime.now(timezone.utc)
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "booking": {
                "active": True,
                "service": "Женская стрижка",
                "datetime": "2026-02-12 18:00",
                "last_question": "name",
            },
            "session_memory": {
                "last_question_type": webhook_router.EXPECTED_REPLY_TIME,
                "unanswered_questions": [
                    webhook_router.EXPECTED_REPLY_TIME,
                    webhook_router.EXPECTED_REPLY_NAME,
                ],
                "pending_slots": {"datetime": "2026-02-12 18:00"},
                "last_updated_at": now.isoformat(),
                "ttl_hours": 24,
            },
        },
        state=ConversationState.BOT_ACTIVE.value,
    )

    expected_reply_result = {
        "ok": False,
        "payload": {
            "slot": "datetime",
            "detected_slot": "name",
            "value": "Лена",
            "confidence": 0.0,
            "reason": "name_provided",
        },
        "error": "slot_mismatch",
        "raw": None,
    }

    with patch(
        "app.routers.webhook.decision._match_expected_reply_candidates",
        return_value=(False, None, []),
    ), patch(
        "app.routers.webhook.decision._is_booking_confirm_enabled",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
        return_value=expected_reply_result,
    ):
        state = decision_router._apply_expected_reply_contract(
            conversation=conversation,
            saved_message=saved_message,
            message_text="Меня зовут Лена.",
            batch_messages=["Меня зовут Лена."],
            context=conversation.context,
            context_manager={},
            now=now,
            current_goal="booking",
            class_carryover=None,
            message_count=1,
            policy_type=None,
            policy_pack=None,
            client_slug="demo_salon",
        )

    booking_state = conversation.context.get("booking") or {}
    session_memory = conversation.context.get("session_memory") or {}
    pending_slots = session_memory.get("pending_slots") or {}
    unanswered_questions = session_memory.get("unanswered_questions") or []
    assert booking_state.get("name") == "Лена"
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    assert state.expected_reply_type == webhook_router.EXPECTED_REPLY_TIME
    assert state.expected_reply_shortcircuit is False
    assert state.expected_reply_matched is False
    assert pending_slots.get("name") == "Лена"
    assert webhook_router.EXPECTED_REPLY_TIME in unanswered_questions
    assert webhook_router.EXPECTED_REPLY_NAME not in unanswered_questions
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("answer_error") == "slot_mismatch"
    assert meta.get("answer_detected_slot") == "name"
    assert meta.get("alternate_slot_captured") is True
    assert meta.get("alternate_slot") == "name"
    assert meta.get("alternate_value") == "Лена"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "slot_validate"
        and entry.get("decision") == "alternate_slot_captured"
        and entry.get("slot") == "name"
        and entry.get("value") == "Лена"
        for entry in trace
        if isinstance(entry, dict)
    )


def test_expected_reply_time_slot_mismatch_captures_alternate_name_without_booking_context():
    from app.routers.webhook import decision as decision_router

    now = datetime.now(timezone.utc)
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "session_memory": {
                "last_question_type": webhook_router.EXPECTED_REPLY_TIME,
                "unanswered_questions": [webhook_router.EXPECTED_REPLY_TIME],
                "pending_slots": {},
                "last_updated_at": now.isoformat(),
                "ttl_hours": 24,
            },
        },
        state=ConversationState.BOT_ACTIVE.value,
    )

    expected_reply_result = {
        "ok": False,
        "payload": {
            "slot": "datetime",
            "detected_slot": "name",
            "value": "Лена",
            "confidence": 0.0,
            "reason": "name_provided",
        },
        "error": "slot_mismatch",
        "raw": None,
    }

    with patch(
        "app.routers.webhook.decision._match_expected_reply_candidates",
        return_value=(False, None, []),
    ), patch(
        "app.routers.webhook.decision._is_booking_confirm_enabled",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
        return_value=expected_reply_result,
    ):
        state = decision_router._apply_expected_reply_contract(
            conversation=conversation,
            saved_message=saved_message,
            message_text="Меня зовут Лена.",
            batch_messages=["Меня зовут Лена."],
            context=conversation.context,
            context_manager={},
            now=now,
            current_goal="booking",
            class_carryover=None,
            message_count=1,
            policy_type=None,
            policy_pack=None,
            client_slug="demo_salon",
        )

    booking_state = conversation.context.get("booking") or {}
    assert booking_state.get("active") is True
    assert booking_state.get("name") == "Лена"
    assert conversation.context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    assert state.expected_reply_type == webhook_router.EXPECTED_REPLY_TIME
    assert state.expected_reply_matched is False
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("alternate_slot_captured") is True
    assert meta.get("alternate_slot") == "name"






































































































def test_llm_policy_core_booking_expected_reply_turn_skips_intent_decomp(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    conversation = SimpleNamespace(
        id=uuid4(),
        context={"booking": {"active": True, "service": "Маникюр"}},
    )
    saved_message = Mock()
    saved_message.message_metadata = {}

    with patch(
        "app.routers.webhook._legacy.detect_multi_intent",
        side_effect=AssertionError("detect_multi_intent should be skipped on booking expected-reply turn"),
    ):
        state = webhook_router._run_intent_decomposition(
            conversation=conversation,
            saved_message=saved_message,
            message_text="Лена",
            expected_reply_type=webhook_router.EXPECTED_REPLY_NAME,
            expected_reply_reason="booking_prompt",
            intent_queue=None,
            class_carryover=None,
            routing={"allow_bot_reply": True},
            bypass_domain_flows=False,
            booking_signal=False,
            booking_block_meta=None,
            booking_slot_signal=True,
            booking_context={"active": True, "service": "Маникюр"},
            booking={"active": True, "service": "Маникюр"},
            booking_active=True,
            expected_reply_shortcircuit=False,
            expected_reply_blocked_by_info=False,
            context={"booking": {"active": True, "service": "Маникюр"}},
            context_manager={},
            current_goal="booking",
            consult_context=None,
            message_count=1,
            now=datetime.now(timezone.utc),
            client_slug="demo_salon",
            timing_context={"pipeline_deadline": 10**12},
        )

    assert state.intent_decomp_used is False
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("intent_decomp_skipped_reason") == "booking_expected_reply_turn"
    assert meta.get("intent_decomp_expected_reply_type") == webhook_router.EXPECTED_REPLY_NAME
    assert meta.get("intent_decomp_expected_reply_reason") == "booking_prompt"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "intent_decomposition"
        and entry.get("decision") == "skipped"
        and entry.get("reason") == "booking_expected_reply_turn"
        for entry in trace
        if isinstance(entry, dict)
    )










def test_llm_policy_core_get_booking_invalid_reference_maps_to_booking_reference_slot():
    verifier_error, verifier_error_field = webhook_router._verify_policy_tool_args_contract(
        tool_action="calendar.get_booking",
        tool_args={"appointment_id": "not-a-uuid"},
        validate_tool_args_contract=validate_tool_args_contract,
    )

    assert verifier_error == "appointment_id_invalid"
    assert verifier_error_field == "appointment_id"
    assert (
        webhook_router.TOOL_VERIFIER_SLOT_BY_FIELD.get(verifier_error_field) == "booking_reference"
    )







































































































































































def test_has_explicit_location_or_hours_request_strict_mode_ignores_derived_hours(monkeypatch):
    from app.routers.webhook import decision as decision_router

    def _fake_detect(*_args, **_kwargs):
        return {
            "master",
            "hours",
        }, {
            "info_signals": {
                "master": True,
                "hours": True,
                "location": False,
                "parking": False,
                "location_address_hint": False,
            },
            "anchor_intents": [],
        }

    monkeypatch.setattr(decision_router, "_detect_info_class_intents", _fake_detect)

    assert (
        decision_router._has_explicit_location_or_hours_request(
            "У вас есть мастера, которые работают с долгими стрижками?",
            client_slug="demo_salon",
            strict=True,
        )
        is False
    )


def test_has_explicit_location_or_hours_request_strict_mode_ignores_anchor_hours_with_master(
    monkeypatch,
):
    from app.routers.webhook import decision as decision_router

    def _fake_detect(*_args, **_kwargs):
        return {
            "master",
            "hours",
        }, {
            "info_signals": {
                "master": True,
                "hours": True,
                "location": False,
                "parking": False,
                "location_address_hint": False,
            },
            "anchor_intents": ["hours"],
        }

    monkeypatch.setattr(decision_router, "_detect_info_class_intents", _fake_detect)

    assert (
        decision_router._has_explicit_location_or_hours_request(
            "У вас есть мастера, которые работают с долгими стрижками?",
            client_slug="demo_salon",
            strict=True,
        )
        is False
    )


def test_has_explicit_location_or_hours_request_strict_mode_real_phrase_no_false_positive():
    from app.routers.webhook import decision as decision_router

    assert (
        decision_router._has_explicit_location_or_hours_request(
            "У вас есть мастера, которые работают с долгими стрижками?",
            client_slug="demo_salon",
            strict=True,
        )
        is False
    )


def test_derive_policy_info_refs_mixed_master_hours_prefers_master_without_explicit_markers():
    from app.routers.webhook import decision as decision_router

    refs = decision_router._derive_policy_info_refs(
        policy_intent=None,
        message_text="У вас есть мастера, которые работают с долгими стрижками?",
        client_slug="demo_salon",
    )

    assert refs
    assert "master" in refs
    assert refs[0] == "master"


def test_derive_policy_info_refs_mixed_master_hours_keeps_hours_priority_when_explicit():
    from app.routers.webhook import decision as decision_router

    refs = decision_router._derive_policy_info_refs(
        policy_intent=None,
        message_text="Какие мастера работают до скольки?",
        client_slug="demo_salon",
    )

    assert "master" in refs
    assert "hours" in refs
    assert refs.index("hours") < refs.index("master")














































def test_truth_gate_fallback_escalation_passes_active_handover_hooks():
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    saved_message = SimpleNamespace(message_metadata={})
    user = SimpleNamespace(id="user-123")
    db = Mock()
    db.commit = Mock()

    def _reuse_active_handover(*, hooks, **_kwargs):
        assert isinstance(
            hooks,
            handover_owner_service.ActiveHandoverReuseRuntimeHooks,
        )
        return None, True, True

    truth_gate_decision = SimpleNamespace(
        action="escalate",
        response=legacy_router.MSG_ESCALATED,
        intent="clarify_limit",
        collect=None,
        meta={},
    )

    with patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        side_effect=_reuse_active_handover,
    ), patch(
        "app.routers.webhook._legacy._reset_low_confidence_retry"
    ), patch(
        "app.routers.webhook._legacy._record_decision_trace"
    ), patch(
        "app.routers.webhook._legacy._record_message_decision_meta"
    ), patch(
        "app.routers.webhook._legacy._update_message_decision_metadata"
    ), patch(
        "app.routers.webhook._legacy._maybe_store_class_carryover"
    ), patch(
        "app.routers.webhook._legacy._maybe_store_service_carryover"
    ):
        response = webhook_info._handle_truth_gate_fallback(
            db=db,
            conversation=conversation,
            user=user,
            message_text="нужен менеджер",
            saved_message=saved_message,
            client_slug="demo_salon",
            routing={"allow_booking_flow": False, "allow_handover_create": False},
            booking_wants_flow=False,
            policy_handler={"truth_gate": lambda *_args, **_kwargs: truth_gate_decision},
            policy_type=None,
            current_goal=None,
            intent_decomp_used=False,
            intent_decomp_intents=[],
            intent_decomp_payload=None,
            llm_primary_reason=None,
            message_count=1,
            now=datetime.now(timezone.utc),
            consult_return_pending=False,
            consult_return_prompt=None,
            consult_context=None,
            consult_return_reason=None,
            maybe_apply_fact_guard=lambda **_kwargs: None,
            send_and_save=lambda bot_response: (bot_response, True),
            log_timing=lambda *_args, **_kwargs: None,
            record_escalation_metric=lambda *_args, **_kwargs: None,
        )

    assert response is not None
    assert response.success is True
    assert response.bot_response == legacy_router.MSG_ESCALATED


def test_policy_escalation_passes_active_handover_hooks():
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=ConversationState.BOT_ACTIVE.value,
    )
    saved_message = SimpleNamespace(message_metadata={})
    user = SimpleNamespace(id="user-123")
    db = Mock()
    db.commit = Mock()
    decision = SimpleNamespace(
        action="escalate",
        response=legacy_router.MSG_ESCALATED,
        intent="payment",
    )

    def _reuse_active_handover(*, hooks, **_kwargs):
        assert isinstance(
            hooks,
            handover_owner_service.ActiveHandoverReuseRuntimeHooks,
        )
        return None, True, True

    with patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        side_effect=_reuse_active_handover,
    ), patch(
        "app.routers.webhook._legacy._reset_low_confidence_retry"
    ), patch(
        "app.routers.webhook._legacy._set_router_observability",
        return_value={},
    ), patch(
        "app.routers.webhook._legacy._record_decision_trace"
    ), patch(
        "app.routers.webhook._legacy._record_message_decision_meta"
    ), patch(
        "app.routers.webhook._legacy._update_message_decision_metadata"
    ):
        response = webhook_policy._apply_policy_decision(
            decision,
            db=db,
            conversation=conversation,
            user=user,
            message_text="нужен менеджер",
            saved_message=saved_message,
            policy_gate="payment_info",
            policy_section="payment_info",
            risk_level=None,
            sidecar=None,
            policy_t0=None,
            gate_label="payment_info",
            booking_wants_flow=False,
            policy_type=None,
            policy_source="policy_gate",
            policy_pack_missing=False,
            routing={"allow_handover_create": False},
            client_slug="demo_salon",
            send_and_save=lambda bot_response, allow_quiet_hours=False: (bot_response, True),
            record_policy_count=lambda *_args, **_kwargs: None,
            record_escalation_metric=lambda *_args, **_kwargs: None,
            log_timing=lambda *_args, **_kwargs: None,
        )

    assert response.success is True
    assert response.bot_response == legacy_router.MSG_ESCALATED


def test_clarify_limit_escalation_passes_active_handover_hooks():
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=ConversationState.BOT_ACTIVE.value,
    )
    saved_message = SimpleNamespace(message_metadata={})
    user = SimpleNamespace(id="user-123")
    db = Mock()
    db.commit = Mock()

    def _reuse_active_handover(*, hooks, **_kwargs):
        assert isinstance(
            hooks,
            handover_owner_service.ActiveHandoverReuseRuntimeHooks,
        )
        return None, True, True

    with patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        side_effect=_reuse_active_handover,
    ), patch(
        "app.routers.webhook._legacy._reset_low_confidence_retry"
    ), patch(
        "app.routers.webhook._legacy._record_decision_trace"
    ), patch(
        "app.routers.webhook._legacy._record_message_decision_meta"
    ), patch(
        "app.routers.webhook._legacy._update_message_decision_metadata"
    ), patch(
        "app.routers.webhook._legacy.save_message"
    ):
        response = webhook_guards._handle_clarify_limit_escalation(
            db=db,
            conversation=conversation,
            user=user,
            message_text="нужен человек",
            saved_message=saved_message,
            source="truth_gate",
            allow_handover=False,
            send_response=lambda *_args, **_kwargs: True,
        )

    assert response.success is True
    assert response.bot_response == legacy_router.MSG_ESCALATED


def test_llm_guard_escalation_passes_active_handover_hooks():
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    saved_message = SimpleNamespace(message_metadata={})
    user = SimpleNamespace(id="user-123")
    db = Mock()
    db.commit = Mock()

    def _reuse_active_handover(*, hooks, **_kwargs):
        assert isinstance(
            hooks,
            handover_owner_service.ActiveHandoverReuseRuntimeHooks,
        )
        return None, True, True

    with patch(
        "app.routers.webhook.response._ensure_rag_rewrite"
    ), patch(
        "app.routers.webhook.response._record_rag_meta"
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        return_value=Result.success(("медицинский ответ", "high")),
    ), patch(
        "app.routers.webhook._legacy._detect_llm_guard_topics",
        return_value=["medical"],
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        side_effect=_reuse_active_handover,
    ), patch(
        "app.routers.webhook._legacy._reset_low_confidence_retry"
    ), patch(
        "app.routers.webhook.response._record_decision_trace"
    ), patch(
        "app.routers.webhook.response._update_message_decision_metadata"
    ), patch(
        "app.routers.webhook.response._record_llm_signal_snapshot"
    ):
        outcome = webhook_response._handle_llm_primary(
            db=db,
            conversation=conversation,
            user=user,
            message_text="нужен совет",
            saved_message=saved_message,
            client_slug="demo_salon",
            policy_type=None,
            policy_pack=None,
            routing={"allow_bot_reply": True, "allow_handover_create": False},
            append_user_message=False,
            timing_context={},
            client_config=None,
            intent=None,
            multi_intent_other_followup=None,
            send_and_save=lambda bot_response, allow_quiet_hours=False: (bot_response, True),
            record_escalation_metric=lambda *_args, **_kwargs: None,
        )

    assert outcome.response is not None
    assert outcome.response.success is True
    assert outcome.response.bot_response == legacy_router.MSG_ESCALATED


def test_booking_interrupt_reschedule_passes_active_handover_hooks():
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    saved_message = SimpleNamespace(message_metadata={})
    user = SimpleNamespace(id="user-123")
    db = Mock()
    db.commit = Mock()

    def _reuse_active_handover(*, hooks, **_kwargs):
        assert isinstance(
            hooks,
            handover_owner_service.ActiveHandoverReuseRuntimeHooks,
        )
        return None, True, True

    with patch(
        "app.routers.webhook.booking._looks_like_booking_reschedule_request",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        side_effect=_reuse_active_handover,
    ), patch(
        "app.routers.webhook._legacy._record_decision_trace"
    ), patch(
        "app.routers.webhook._legacy._record_message_decision_meta"
    ):
        response = webhook_booking._handle_booking_interrupt(
            db=db,
            conversation=conversation,
            user=user,
            message_text="Хотелось бы перенести на следующий понедельник.",
            saved_message=saved_message,
            client_slug="demo_salon",
            routing={"allow_handover_create": True, "allow_truth_gate_reply": False},
            has_media=False,
            bypass_domain_flows=False,
            booking_wants_flow=False,
            consult_intent=None,
            intent_decomp_used=False,
            intent_decomp_set=set(),
            intent_decomp_payload=None,
            multi_intent_primary=None,
            info_class_intents=set(),
            early_domain_intent=None,
            expected_reply_type=None,
            expected_reply_matched=None,
            expected_reply_shortcircuit=False,
            expected_reply_blocked_by_info=False,
            pending_question_act=None,
            pending_question_target=None,
            batch_non_booking_message=None,
            booking_messages=[],
            booking_context={},
            booking={"active": True, "service": "Маникюр"},
            current_goal=None,
            basic_info_message=False,
            session_memory_reset_reason=None,
            memory_expected_reply_type=None,
            policy_handler=None,
            policy_type=None,
            now=datetime.now(timezone.utc),
            message_count=1,
            consult_return_pending=False,
            consult_return_prompt=None,
            consult_context=None,
            consult_return_reason=None,
            maybe_apply_fact_guard=lambda **_kwargs: None,
            send_and_save=lambda bot_response, allow_quiet_hours=False: (bot_response, True),
            send_response=lambda *_args, **_kwargs: None,
            finalize_response=lambda response: response,
        )

    assert response is not None
    assert response.success is True
    assert response.bot_response == legacy_router.MSG_ESCALATED


def test_booking_interrupt_info_escalation_passes_active_handover_hooks():
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    saved_message = SimpleNamespace(message_metadata={})
    user = SimpleNamespace(id="user-123")
    db = Mock()
    db.commit = Mock()
    info_decision = SimpleNamespace(
        action="escalate",
        response=legacy_router.MSG_ESCALATED,
        intent="pricing",
        meta={"fact_intents": ["pricing"]},
    )

    def _reuse_active_handover(*, hooks, **_kwargs):
        assert isinstance(
            hooks,
            handover_owner_service.ActiveHandoverReuseRuntimeHooks,
        )
        return None, True, True

    with patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        side_effect=_reuse_active_handover,
    ), patch(
        "app.routers.webhook._legacy._record_decision_trace"
    ), patch(
        "app.routers.webhook._legacy._record_message_decision_meta"
    ), patch(
        "app.routers.webhook._legacy._update_message_decision_metadata"
    ), patch(
        "app.routers.webhook._legacy._reset_low_confidence_retry"
    ):
        response = webhook_booking._handle_booking_interrupt(
            db=db,
            conversation=conversation,
            user=user,
            message_text="А сколько это стоит?",
            saved_message=saved_message,
            client_slug="demo_salon",
            routing={
                "allow_booking_flow": True,
                "allow_handover_create": True,
                "allow_truth_gate_reply": True,
            },
            has_media=False,
            bypass_domain_flows=False,
            booking_wants_flow=True,
            consult_intent=None,
            intent_decomp_used=False,
            intent_decomp_set=set(),
            intent_decomp_payload=None,
            multi_intent_primary=None,
            info_class_intents={"pricing"},
            early_domain_intent=None,
            expected_reply_type="time",
            expected_reply_matched=False,
            expected_reply_shortcircuit=False,
            expected_reply_blocked_by_info=False,
            pending_question_act=None,
            pending_question_target=None,
            batch_non_booking_message="А сколько это стоит?",
            booking_messages=[],
            booking_context={},
            booking={"active": True, "service": "Маникюр"},
            current_goal=None,
            basic_info_message=False,
            session_memory_reset_reason=None,
            memory_expected_reply_type=None,
            policy_handler={"truth_gate": lambda *_args, **_kwargs: info_decision},
            policy_type=None,
            now=datetime.now(timezone.utc),
            message_count=1,
            consult_return_pending=False,
            consult_return_prompt=None,
            consult_context=None,
            consult_return_reason=None,
            maybe_apply_fact_guard=lambda **_kwargs: None,
            send_and_save=lambda bot_response, allow_quiet_hours=False: (bot_response, True),
            send_response=lambda *_args, **_kwargs: None,
            finalize_response=lambda response: response,
        )

    assert response is not None
    assert response.success is True
    assert response.bot_response == legacy_router.MSG_ESCALATED


def test_booking_same_day_escalation_passes_active_handover_hooks():
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    saved_message = SimpleNamespace(message_metadata={})
    user = SimpleNamespace(id="user-123")
    db = Mock()
    db.commit = Mock()
    decision = SimpleNamespace(
        action="escalate",
        response=legacy_router.MSG_ESCALATED,
        intent="same_day_booking",
        meta={},
    )

    def _reuse_active_handover(*, hooks, **_kwargs):
        assert isinstance(
            hooks,
            handover_owner_service.ActiveHandoverReuseRuntimeHooks,
        )
        return None, True, True

    with patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        side_effect=_reuse_active_handover,
    ), patch(
        "app.routers.webhook._legacy._reset_low_confidence_retry"
    ), patch(
        "app.routers.webhook._legacy._record_decision_trace"
    ), patch(
        "app.routers.webhook._legacy._record_message_decision_meta"
    ), patch(
        "app.routers.webhook._legacy._update_message_decision_metadata"
    ):
        outcome = webhook_booking._handle_booking_flow(
            db=db,
            conversation=conversation,
            user=user,
            message_text="Можно сегодня вечером?",
            saved_message=saved_message,
            client_slug="demo_salon",
            routing={"allow_truth_gate_reply": True, "allow_handover_create": True},
            bypass_domain_flows=False,
            booking_wants_flow=True,
            booking_active=True,
            booking_signal=False,
            booking_messages=[],
            booking_context={},
            booking={"active": True, "service": "Маникюр"},
            expected_reply_type="time",
            expected_reply_matched=False,
            expected_reply_blocked_by_info=False,
            basic_info_message=False,
            session_memory_reset_reason=None,
            memory_expected_reply_type=None,
            policy_handler={"truth_gate": lambda *_args, **_kwargs: decision},
            policy_pack={},
            now=datetime.now(timezone.utc),
            message_count=1,
            multi_intent_booking_followup=None,
            consult_return_pending=False,
            consult_return_prompt=None,
            consult_context=None,
            consult_return_reason=None,
            send_and_save=lambda bot_response, allow_quiet_hours=False: (bot_response, True),
            send_response=lambda *_args, **_kwargs: None,
            finalize_response=lambda response: response,
            log_timing=lambda *_args, **_kwargs: None,
            record_escalation_metric=lambda *_args, **_kwargs: None,
        )

    assert outcome.response is not None
    assert outcome.response.success is True
    assert outcome.response.bot_response == legacy_router.MSG_ESCALATED


def test_booking_human_request_escalation_passes_active_handover_hooks():
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    saved_message = SimpleNamespace(message_metadata={})
    user = SimpleNamespace(id="user-123")
    db = Mock()
    db.commit = Mock()

    def _reuse_active_handover(*, hooks, **_kwargs):
        assert isinstance(
            hooks,
            handover_owner_service.ActiveHandoverReuseRuntimeHooks,
        )
        return None, True, True

    with patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        side_effect=_reuse_active_handover,
    ), patch(
        "app.routers.webhook._legacy.is_human_request_message",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._record_decision_trace"
    ), patch(
        "app.routers.webhook._legacy._record_message_decision_meta"
    ):
        outcome = webhook_booking._handle_booking_flow(
            db=db,
            conversation=conversation,
            user=user,
            message_text="Позовите, пожалуйста, менеджера",
            saved_message=saved_message,
            client_slug="demo_salon",
            routing={"allow_booking_flow": True, "allow_handover_create": True},
            bypass_domain_flows=False,
            booking_wants_flow=False,
            booking_active=True,
            booking_signal=False,
            booking_messages=[],
            booking_context={},
            booking={"active": True, "service": "Маникюр"},
            expected_reply_type="time",
            expected_reply_matched=False,
            expected_reply_blocked_by_info=False,
            basic_info_message=False,
            session_memory_reset_reason=None,
            memory_expected_reply_type=None,
            policy_handler=None,
            policy_pack=None,
            now=datetime.now(timezone.utc),
            message_count=1,
            multi_intent_booking_followup=None,
            consult_return_pending=False,
            consult_return_prompt=None,
            consult_context=None,
            consult_return_reason=None,
            send_and_save=lambda bot_response, allow_quiet_hours=False: (bot_response, True),
            send_response=lambda *_args, **_kwargs: None,
            finalize_response=lambda response: response,
            log_timing=lambda *_args, **_kwargs: None,
            record_escalation_metric=lambda *_args, **_kwargs: None,
        )

    assert outcome.response is not None
    assert outcome.response.success is True
    assert outcome.response.bot_response == legacy_router.MSG_ESCALATED














def test_timeout_pending_slot_question_helper_ignores_named_specialist_question():
    now = datetime.now(timezone.utc)

    assert (
        webhook_router._is_timeout_pending_time_slot_question(
            message_text="Могу ли я записаться к Айгерим?",
            client_slug="demo_salon",
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            expected_reply_matched=False,
            expected_reply_blocked_by_info=True,
            booking_service="Маникюр",
            intent_decomp_payload={},
            now=now,
    )
        is False
    )


def test_timeout_pending_slot_question_helper_accepts_v_kakoe_vremya_slots_question():
    now = datetime.now(timezone.utc)

    assert (
        webhook_router._is_timeout_pending_time_slot_question(
            message_text="В какое время у вас есть слоты?",
            client_slug="demo_salon",
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            expected_reply_matched=False,
            expected_reply_blocked_by_info=True,
            booking_service="Маникюр",
            intent_decomp_payload={},
            now=now,
        )
        is True
    )


def test_timeout_pending_slot_question_helper_accepts_generic_time_preference_statement():
    now = datetime.now(timezone.utc)

    assert (
        webhook_router._is_timeout_pending_time_slot_question(
            message_text="У меня есть предпочтения по времени.",
            client_slug="demo_salon",
            expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
            expected_reply_matched=False,
            expected_reply_blocked_by_info=True,
            booking_service="Маникюр",
            intent_decomp_payload={},
            now=now,
        )
        is True
    )


def test_timeout_slot_question_info_lock_surface_accepts_free_slots_phrase():
    assert (
        webhook_router._has_timeout_slot_question_info_lock_surface(
            message_text="Во сколько у вас свободные слоты?",
            client_slug="demo_salon",
        )
        is True
    )


def test_timeout_slot_question_info_lock_surface_rejects_hours_prompt():
    assert (
        webhook_router._has_timeout_slot_question_info_lock_surface(
            message_text="Когда вы работаете?",
            client_slug="demo_salon",
        )
        is False
    )














def test_resolve_specialist_name_hint_with_trace_prefers_branch_catalog_match():
    branch_id = uuid4()
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(branch_id=branch_id, context={})

    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = SimpleNamespace(
        id=branch_id,
        knowledge_tag="demo_salon",
    )
    specialist_query = Mock()
    specialist_query.filter.return_value.all.return_value = [
        SimpleNamespace(name="Айгерим"),
        SimpleNamespace(name="Алина"),
    ]

    db = Mock()
    db.query.side_effect = _build_query_side_effect(
        branch_query=branch_query,
        specialist_query=specialist_query,
    )

    with patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        side_effect=AssertionError("branch catalog match should short-circuit secondary llm"),
    ):
        specialist_name = _resolve_specialist_name_hint_with_trace(
            db=db,
            message_text="Можно записаться к Айгерим?",
            client_slug="demo_salon",
            timing_context={},
            conversation=conversation,
            saved_message=saved_message,
            tool_action="collect",
        )

    assert specialist_name == "Айгерим"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("specialist_hint_attempted") is False
    assert meta.get("specialist_hint_ok") is True
    assert meta.get("specialist_hint_error") is None
    assert meta.get("specialist_hint_source") == "branch_catalog"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "specialist_hint"
        and entry.get("decision") == "ok"
        and entry.get("source") == "branch_catalog"
        and entry.get("specialist_name") == "Айгерим"
        for entry in trace
        if isinstance(entry, dict)
    )


def test_resolve_specialist_name_hint_with_trace_prefers_unique_branch_catalog_first_name_match():
    branch_id = uuid4()
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(branch_id=branch_id, context={})

    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = SimpleNamespace(
        id=branch_id,
        knowledge_tag="demo_salon",
    )
    specialist_query = Mock()
    specialist_query.filter.return_value.all.return_value = [
        SimpleNamespace(name="Айгерим Болатова"),
        SimpleNamespace(name="Алина"),
    ]

    db = Mock()
    db.query.side_effect = _build_query_side_effect(
        branch_query=branch_query,
        specialist_query=specialist_query,
    )

    with patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        side_effect=AssertionError("unique branch first-name match should short-circuit secondary llm"),
    ):
        specialist_name = _resolve_specialist_name_hint_with_trace(
            db=db,
            message_text="А можно записаться к Айгерим?",
            client_slug="demo_salon",
            timing_context={},
            conversation=conversation,
            saved_message=saved_message,
            tool_action="collect",
        )

    assert specialist_name == "Айгерим Болатова"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("specialist_hint_attempted") is False
    assert meta.get("specialist_hint_ok") is True
    assert meta.get("specialist_hint_error") is None
    assert meta.get("specialist_hint_source") == "branch_catalog"
    assert meta.get("specialist_hint_match_mode") == "first_name_unique"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "specialist_hint"
        and entry.get("decision") == "ok"
        and entry.get("source") == "branch_catalog"
        and entry.get("match_mode") == "first_name_unique"
        and entry.get("specialist_name") == "Айгерим Болатова"
        for entry in trace
        if isinstance(entry, dict)
    )


def test_resolve_specialist_name_hint_with_trace_ambiguous_first_name_uses_llm():
    branch_id = uuid4()
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(branch_id=branch_id, context={})

    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = SimpleNamespace(
        id=branch_id,
        knowledge_tag="demo_salon",
    )
    specialist_query = Mock()
    specialist_query.filter.return_value.all.return_value = [
        SimpleNamespace(name="Айгерим Болатова"),
        SimpleNamespace(name="Айгерим Садыкова"),
    ]

    db = Mock()
    db.query.side_effect = _build_query_side_effect(
        branch_query=branch_query,
        specialist_query=specialist_query,
    )
    llm_hint = {
        "ok": True,
        "specialist_name": "Айгерим Садыкова",
        "confidence": 0.71,
        "error": None,
        "language": "ru",
        "attempted": True,
    }

    with patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        return_value=llm_hint,
    ) as specialist_hint_mock:
        specialist_name = _resolve_specialist_name_hint_with_trace(
            db=db,
            message_text="А можно записаться к Айгерим?",
            client_slug="demo_salon",
            timing_context={},
            conversation=conversation,
            saved_message=saved_message,
            tool_action="collect",
        )

    assert specialist_name == "Айгерим Садыкова"
    specialist_hint_mock.assert_called_once()
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("specialist_hint_source") == "llm"
    assert meta.get("specialist_hint_match_mode") is None


def test_resolve_specialist_name_hint_with_trace_prefers_message_surface_before_budget_skip():
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(branch_id=None, context={})
    db = Mock()

    with patch(
        "app.routers.webhook.decision.extract_specialist_hint_llm",
        side_effect=AssertionError("message surface hint should avoid secondary llm"),
    ), patch(
        "app.routers.webhook.decision._should_skip_secondary_llm_stage",
        return_value=(True, 150.0),
    ):
        specialist_name = _resolve_specialist_name_hint_with_trace(
            db=db,
            message_text="Можно к мастеру Мадина?",
            client_slug="demo_salon",
            timing_context={},
            conversation=conversation,
            saved_message=saved_message,
            tool_action="collect",
        )

    assert specialist_name == "Мадина"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("specialist_hint_attempted") is False
    assert meta.get("specialist_hint_ok") is True
    assert meta.get("specialist_hint_error") is None
    assert meta.get("specialist_hint_source") == "message_surface"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "specialist_hint"
        and entry.get("decision") == "ok"
        and entry.get("source") == "message_surface"
        and entry.get("specialist_name") == "Мадина"
        for entry in trace
        if isinstance(entry, dict)
    )
















def test_policy_core_reason_supports_info_rescue_prefixes():
    assert _policy_core_reason_supports_info_rescue("policy_error:invalid_schema") is True
    assert _policy_core_reason_supports_info_rescue("policy_validation:low_confidence") is True
    assert _policy_core_reason_supports_info_rescue("llm_degraded:llm_timeout") is True
    assert _policy_core_reason_supports_info_rescue("guard_not_eligible") is False
    assert _policy_core_reason_supports_info_rescue(None) is False


def test_classify_policy_core_degrade_reason_taxonomy():
    retryable_error = _classify_policy_core_degrade_reason("policy_error:timeout")
    assert retryable_error["category"] == "policy_error"
    assert retryable_error["code"] == "timeout"
    assert retryable_error["retryable"] is True
    assert retryable_error["info_rescue_eligible"] is True
    assert retryable_error["severity"] == "medium"

    hard_validation = _classify_policy_core_degrade_reason("policy_validation:invalid_schema")
    assert hard_validation["category"] == "policy_validation"
    assert hard_validation["code"] == "invalid_schema"
    assert hard_validation["retryable"] is False
    assert hard_validation["severity"] == "high"

    guard = _classify_policy_core_degrade_reason("guard_not_eligible")
    assert guard["category"] == "guard"
    assert guard["code"] == "guard_not_eligible"
    assert guard["retryable"] is False
    assert guard["info_rescue_eligible"] is False
    assert guard["severity"] == "low"


def test_policy_has_style_reference_hint_from_intent_or_reason():
    assert _policy_has_style_reference_hint(policy_intent="send_photo", policy_reason=None) is True
    assert _policy_has_style_reference_hint(policy_intent="get_popular_style", policy_reason=None) is True
    assert (
        _policy_has_style_reference_hint(
            policy_intent="other",
            policy_reason="style_reference_text",
        )
        is True
    )
    assert _policy_has_style_reference_hint(policy_intent="booking", policy_reason="booking_flow") is False


def test_derive_booking_followup_prompt_prefers_merged_datetime_over_stale_booking_state():
    expected_reply, prompt = webhook_router._derive_booking_followup_prompt(
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        booking_state={
            "active": True,
            "service": "Маникюр",
            "datetime": "2026-02-18 10:00",
        },
        merged_slots={
            "service": "Маникюр",
            "datetime": "2026-02-19",
        },
        client_slug="demo_salon",
    )

    assert expected_reply == webhook_router.EXPECTED_REPLY_TIME
    assert prompt is not None
    assert "2026-02-18" not in prompt


def test_validate_policy_check_confirm_contract_allows_valid_paths():
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="check_booking",
            policy_action="fact",
            policy_tool_action="calendar.get_booking",
        )
        is None
    )
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="confirm_booking",
            policy_action="collect",
            policy_tool_action="calendar.book_slot",
        )
        is None
    )
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="verify_booking",
            policy_action="handoff",
            policy_tool_action="handoff",
        )
        is None
    )


def test_validate_policy_check_confirm_contract_rejects_mismatch():
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="check_booking",
            policy_action="fact",
            policy_tool_action="calendar.book_slot",
        )
        == "check_confirm_tool_mismatch"
    )
    assert (
        _validate_policy_check_confirm_contract(
            policy_intent="confirm_booking",
            policy_action="handoff",
            policy_tool_action="calendar.book_slot",
        )
        == "check_confirm_action_mismatch"
    )


def test_detect_tool_contract_error_blocks_created_text_without_confirmed_status():
    error = _detect_tool_contract_error(
        tool_action="calendar.book_slot",
        tool_ok=True,
        response_text="Запись создана. Хотите что-то изменить?",
        decision_meta={
            "tool_decision": "ok",
            "appointment_id": "apt-1",
            "appointment_status": "PENDING_CONFIRMATION",
        },
    )
    assert error == "booking_confirmation_status_mismatch"


def test_detect_tool_contract_error_allows_created_text_for_confirmed_status():
    error = _detect_tool_contract_error(
        tool_action="calendar.book_slot",
        tool_ok=True,
        response_text="Запись подтверждена.",
        decision_meta={
            "tool_decision": "ok",
            "appointment_id": "apt-1",
            "appointment_status": "CONFIRMED",
        },
    )
    assert error is None


def test_detect_tool_contract_error_allows_services_overview_for_catalog_query():
    error = _detect_tool_contract_error(
        tool_action="catalog.service_query",
        tool_ok=True,
        response_text="Мы предлагаем: Маникюр, Педикюр.",
        decision_meta={
            "tool_decision": "services_overview",
        },
    )
    assert error is None






def test_extract_fact_evidence_refs_uses_pack_refs_tool_args_and_payload():
    refs = _extract_fact_evidence_refs(
        {
            "pack_refs": ["Hours", "location"],
            "tool_args": {
                "service_query": "Маникюр",
                "consult_ref": "contracts",
            },
            "llm_policy_core": {
                "payload": {
                    "pack_refs": ["parking"],
                }
            },
        }
    )

    assert refs == ["hours", "location", "contracts", "маникюр", "parking"]


def test_fact_guard_reason_requires_evidence_refs_for_fact_source():
    assert _fact_guard_reason({"fact_source": "truth"}) == "missing_evidence_refs"
    assert (
        _fact_guard_reason(
            {
                "fact_source": "truth",
                "fact_refs": ["aftercare_gel_lac"],
            }
        )
        is None
    )
    assert (
        _fact_guard_reason(
            {
                "fact_source": "truth",
                "info_sections": ["hours"],
            }
        )
        is None
    )


def test_fact_guard_reason_skips_calendar_tool_actions():
    assert (
        _fact_guard_reason(
            {
                "tool_action": "calendar.book_slot",
                "tool_decision": "ok",
                "appointment_id": "apt-123",
            }
        )
        is None
    )
    assert (
        _fact_guard_reason(
            {
                "tool_action": "calendar.get_booking",
                "tool_decision": "ok",
                "appointment_id": "apt-123",
            }
        )
        is None
    )
















































def test_style_reference_detects_send_photo_phrases():
    assert webhook_router._is_style_reference_request(
        "Я могу прислать фото своей прически.",
        has_media=False,
    )
    assert webhook_router._is_style_reference_request(
        "У вас есть возможность отправить фото?",
        has_media=False,
    )


def test_booking_verification_handoff_intent_detection():
    assert webhook_router._is_booking_verification_handoff_intent(
        "check_booking",
        "calendar.get_booking",
    )
    assert webhook_router._is_booking_verification_handoff_intent(
        "confirm_booking",
        "calendar.book_slot",
    )
    assert not webhook_router._is_booking_verification_handoff_intent(
        "booking",
        "calendar.get_booking",
    )
    assert webhook_router._looks_like_booking_verification_request(
        "Я хочу проверить свою запись.",
    )
    assert webhook_router._looks_like_booking_verification_request(
        "Подтвердите, пожалуйста, запись.",
    )
    assert not webhook_router._looks_like_booking_verification_request(
        "Мне нужно изменить время записи.",
    )
    assert webhook_router._looks_like_booking_verification_request(
        "Подтвердите, пожалуйста, новую дату.",
    )


def test_promo_code_request_detection():
    assert webhook_router._looks_like_promo_code_request(
        "Какой у вас специальный промо-код?",
        client_slug="demo_salon",
    )
    assert webhook_router._looks_like_promo_code_request(
        "Есть promo code?",
        client_slug="demo_salon",
    )
    assert not webhook_router._looks_like_promo_code_request(
        "Какие у вас акции на стрижку?",
        client_slug="demo_salon",
    )


def test_format_discounts_reply_for_message_handles_promo_code_without_declared_code():
    policy_pack = {
        "discounts": {
            "enabled": True,
            "items": [
                {"name": "Первое посещение", "discount_percent": 10, "eligibility": "на услуги"},
            ],
            "stacking": "Скидки не суммируются",
        }
    }

    reply = webhook_router._format_discounts_reply_for_message(
        message_text="Какой у вас специальный промо-код?",
        policy_pack=policy_pack,
        policy_type=None,
        client_slug="demo_salon",
    )

    assert isinstance(reply, str)
    assert "специальный промокод в правилах не указан" in reply.casefold()
    assert "официальные акции" in reply.casefold()


def test_format_discounts_reply_for_message_uses_declared_promo_code():
    policy_pack = {
        "discounts": {
            "enabled": True,
            "promo_code": "WELCOME10",
            "items": [
                {"name": "Первое посещение", "discount_percent": 10, "eligibility": "на услуги"},
            ],
        }
    }

    reply = webhook_router._format_discounts_reply_for_message(
        message_text="Есть промо код?",
        policy_pack=policy_pack,
        policy_type=None,
        client_slug="demo_salon",
    )

    assert isinstance(reply, str)
    assert "welcome10" in reply.casefold()
    assert "промокод" in reply.casefold()


def test_is_booking_request_detects_need_plus_service_with_datetime_without_lexicon_phrase():
    assert webhook_router._is_booking_request(
        "Здравствуйте, мне нужна маникюр завтра.",
        client_slug="demo_salon",
    )


def test_is_booking_request_rejects_need_plus_service_without_datetime_or_booking_lexicon():
    assert not webhook_router._is_booking_request(
        "Здравствуйте, мне нужна маникюр.",
        client_slug="demo_salon",
    )




def _load_golden_cases() -> list[dict]:
    path = Path(__file__).resolve().parent / "test_cases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    manual = data.get("manual_tests", {})
    cases = manual.get("test_cases", []) if isinstance(manual, dict) else []
    return [case for case in cases if isinstance(case, dict) and case.get("automation")]


@pytest.mark.parametrize(
    ("legacy_name", "owner_name"),
    [
        ("_reuse_active_handover", "_reuse_active_handover"),
        ("escalate_to_pending", "escalate_to_pending"),
        ("manager_resolve", "manager_resolve"),
    ],
)
def test_legacy_handover_adapter_exports_owner_surface_symbols(legacy_name, owner_name):
    assert getattr(legacy_router, legacy_name) is getattr(handover_owner_service, owner_name)


def test_escalation_reuses_active_handover():
    db = Mock()
    conversation = Mock()
    conversation.id = "conv-id"
    conversation.client_id = "client-id"
    conversation.state = ConversationState.BOT_ACTIVE.value
    conversation.escalated_at = None
    user = Mock()
    user.remote_jid = "77000000000@s.whatsapp.net"

    existing = Mock()
    existing.id = "handover-id"
    existing.status = "pending"

    materialize_result = SimpleNamespace(
        ok=True,
        handover=existing,
        mode="reuse",
        telegram_sent=True,
        handover_reopened=False,
    )

    with patch(
        "app.services.handover_owner_service.materialize_handover",
        return_value=materialize_result,
    ) as mock_materialize:
        handover, sent = escalation_service.escalate_conversation(
            db=db,
            conversation=conversation,
            user=user,
            trigger_type="intent",
            trigger_value="payment",
            user_message="по оплате уточню",
        )

        assert handover == existing
        assert sent is True
        mock_materialize.assert_called_once_with(
            db=db,
            conversation=conversation,
            user=user,
            message="по оплате уточню",
            source="escalation_service",
            intent="payment",
            trigger_type="intent",
            trigger_value="payment",
            allow_create=True,
        )


@pytest.mark.parametrize("case", _load_golden_cases())
def test_golden_cases(case):
    automation = case["automation"]
    check = automation.get("check")
    if check == "fast_intent":
        decision = webhook_router._detect_fast_intent(
            case.get("input", ""),
            policy_type=automation.get("policy_type", "demo_salon"),
            booking_wants_flow=automation.get("booking_wants_flow", False),
            bypass_domain_flows=automation.get("bypass_domain_flows", False),
        )
        if automation.get("expect_action") is not None:
            assert decision is not None
            assert decision.action == automation["expect_action"]
        if automation.get("expect_intent") is not None:
            assert decision is not None
            assert decision.intent == automation["expect_intent"]
        if automation.get("expect_match") is False:
            assert decision is None
        return
    if check == "domain_router":
        router_key = automation.get("domain_router")
        if router_key == "demo_salon":
            client_config = {"domain_router": DEMO_DOMAIN_ROUTER_CONFIG}
        else:
            client_config = automation.get("domain_router_config", {})
        domain_intent, in_score, out_score, _ = classify_domain_with_scores(
            case.get("input", ""),
            client_config,
        )
        strong_out, _ = is_strong_out_of_domain(
            case.get("input", ""),
            domain_intent,
            in_score,
            out_score,
            client_config,
        )
        if automation.get("expect_out_of_domain") is not None:
            assert strong_out is automation["expect_out_of_domain"]
        if automation.get("expect_domain_intent") is not None:
            assert domain_intent.value == automation["expect_domain_intent"]
        return
    if check == "decision":
        state = automation.get("state", ConversationState.BOT_ACTIVE.value)
        state_value = state.value if isinstance(state, ConversationState) else state
        policy = webhook_router._get_routing_policy(state_value)
        signals = webhook_router._detect_intent_signals(case.get("input", ""))
        outcome = webhook_router._resolve_action(
            routing=policy,
            state=state_value,
            signals=signals,
            is_pending_status_question=False,
            style_reference=False,
            out_of_domain_signal=False,
            rag_confident=False,
        )
        assert outcome.action == automation["expect_action"]
        return

    if check == "signals":
        messages = automation.get("messages") or ([case.get("input")] if case.get("input") else [])
        messages = [msg for msg in messages if isinstance(msg, str)]
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint):
            snapshot = _booking_signal_snapshot(messages)
            booking_signal = snapshot.get("signal")
        opt_out = any(is_opt_out_message(msg) for msg in messages)

        if "expect_booking_signal" in automation:
            assert booking_signal == automation["expect_booking_signal"]
        if "expect_opt_out" in automation:
            assert opt_out == automation["expect_opt_out"]
        return

    if check == "booking_flow":
        messages = automation.get("messages") or ([case.get("input")] if case.get("input") else [])
        messages = [msg for msg in messages if isinstance(msg, str)]
        with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint):
            snapshot = _booking_signal_snapshot(messages)
            booking_signal = snapshot.get("signal")
            booking_state = webhook_router._update_booking_from_messages(
                {},
                messages,
                client_slug="demo_salon",
            )

        if "expect_booking_signal" in automation:
            assert booking_signal == automation["expect_booking_signal"]
        if automation.get("expect_service"):
            assert booking_state.get("service")
        if automation.get("expect_datetime"):
            assert booking_state.get("datetime")
        return

    pytest.fail(f"Unknown golden automation check: {check}")


def test_reuse_active_handover_captures_interaction_state_in_pending_resume():
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "expected_reply_reason": "booking_prompt",
            "context_manager": {
                "current_goal": "booking",
                "canonical_dialog_state": {
                    "owner_id": "context_manager.dialog_state.v1",
                    "version": "v1",
                    "interaction_state": {
                        "resume_slot": "datetime",
                        "interaction_target": "time",
                        "interaction_relation": "ask_about_requested_slot",
                        "interaction_owner": "llm_policy_core:ask_about_requested_slot",
                        "grounded_referents": {"service": "Стрижка"},
                    },
                },
            },
            "booking": {
                "active": True,
                "service": "Стрижка",
                "last_question": "datetime",
            },
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": "time",
                "pending_slots": {"datetime": "15:00"},
                "interaction_state": {
                    "resume_slot": "datetime",
                    "interaction_target": "time",
                    "interaction_relation": "ask_about_requested_slot",
                    "interaction_owner": "llm_policy_core:ask_about_requested_slot",
                },
            },
            "branch_id": "branch-1",
        },
        escalated_at=None,
    )
    handover = SimpleNamespace(id=uuid4(), status="pending")
    user = SimpleNamespace(id="user-1")
    db = Mock()

    def _fake_transition(conv, target_state, **_kwargs):
        conv.state = target_state.value if hasattr(target_state, "value") else target_state
        return {
            "invalid_transition": False,
            "from_state": ConversationState.BOT_ACTIVE.value,
            "to_state": conv.state,
            "violations": [],
        }

    reused_handover, reused, telegram_sent = webhook_router._reuse_active_handover(
        db=db,
        conversation=conversation,
        user=user,
        message="Мне нужна помощь менеджера",
        source="test",
        intent="cancel_request",
        hooks=handover_owner_service.ActiveHandoverReuseRuntimeHooks(
            get_active_handover=lambda *args, **kwargs: handover,
            transition_state=_fake_transition,
            send_telegram_notification=lambda **kwargs: True,
            record_decision_trace=lambda *args, **kwargs: None,
        ),
    )

    assert reused_handover is handover
    assert reused is True
    assert telegram_sent is True
    assert conversation.state == ConversationState.PENDING.value
    assert conversation.escalated_at is not None

    context = conversation.context
    snapshot = context.get("pending_resume")
    assert isinstance(snapshot, dict)
    assert snapshot.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    assert snapshot.get("expected_reply_reason") == "booking_prompt"
    assert snapshot.get("booking", {}).get("service") == "Стрижка"
    assert snapshot.get("session_memory", {}).get("last_question_type") == "time"
    assert snapshot.get("session_memory", {}).get("interaction_state", {}).get("resume_slot") == "datetime"
    assert (
        snapshot.get("context_manager", {})
        .get("canonical_dialog_state", {})
        .get("interaction_state", {})
        .get("interaction_owner")
        == "llm_policy_core:ask_about_requested_slot"
    )
    assert snapshot.get("context_manager", {}).get("current_goal") == "booking"
    assert context.get("branch_id") == "branch-1"
    assert "expected_reply_type" not in context
    assert "booking" not in context
    assert "session_memory" not in context
    assert "context_manager" not in context


def test_reuse_active_handover_preserves_existing_pending_snapshot():
    existing_snapshot = {
        "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
        "booking": {"active": True, "service": "Стрижка"},
        "session_memory": {"last_question_type": "time"},
        "context_manager": {"current_goal": "booking"},
    }
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.PENDING.value,
        context={
            "pending_resume": existing_snapshot,
            "expected_reply_type": webhook_router.EXPECTED_REPLY_TIME,
            "booking": {"active": True, "service": "Стрижка"},
            "session_memory": {"last_question_type": "time"},
            "context_manager": {"current_goal": "booking"},
            "branch_id": "branch-1",
        },
        escalated_at=datetime.now(timezone.utc),
    )
    handover = SimpleNamespace(id=uuid4(), status="pending")
    user = SimpleNamespace(id="user-1")
    db = Mock()

    transition_mock = Mock()
    reused_handover, reused, telegram_sent = webhook_router._reuse_active_handover(
        db=db,
        conversation=conversation,
        user=user,
        message="Нужен менеджер",
        source="test",
        intent="cancel_request",
        hooks=handover_owner_service.ActiveHandoverReuseRuntimeHooks(
            get_active_handover=lambda *args, **kwargs: handover,
            transition_state=transition_mock,
            send_telegram_notification=lambda **kwargs: True,
            record_decision_trace=lambda *args, **kwargs: None,
        ),
    )

    assert reused_handover is handover
    assert reused is True
    assert telegram_sent is True
    transition_mock.assert_not_called()
    assert conversation.state == ConversationState.PENDING.value
    assert conversation.context.get("pending_resume") == existing_snapshot
    assert conversation.context.get("branch_id") == "branch-1"
    assert "expected_reply_type" not in conversation.context
    assert "booking" not in conversation.context
    assert "session_memory" not in conversation.context
    assert "context_manager" not in conversation.context

def _build_provider_unavailable_human_request_pending_resume_context(*, now: datetime) -> dict:
    seeded_manager = webhook_router._sync_canonical_dialog_state(
        {
            "message_count": 7,
            "current_goal": "booking",
        },
        booking_state={
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
        expected_reply_type=webhook_router.EXPECTED_REPLY_TIME,
        expected_reply_reason="booking_interrupt",
        message_count=7,
        interaction_target="time",
        interaction_relation="ask_about_requested_slot",
    )
    return {
        "context_manager": seeded_manager,
        "booking": {
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
        "session_memory": {
            "active_goal": "booking",
            "goal_stack": ["booking"],
            "ttl_hours": 24,
            "last_updated_at": (now - timedelta(minutes=1)).isoformat(),
            "interaction_state": {
                "resume_slot": "datetime",
                "interaction_target": "time",
                "interaction_relation": "ask_about_requested_slot",
                "interaction_owner": "question_contract:booking_interrupt",
            },
        },
        "re_entry_required": {
            "required": True,
            "reason": "pending_resume",
            "set_at": now.isoformat(),
        },
    }


def test_provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary():
    now = datetime.now(timezone.utc)
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context=_build_provider_unavailable_human_request_pending_resume_context(now=now),
    )

    restore = _resolve_resolved_handoff_resume_boundary_restore(
        conversation=conversation,
        saved_message=saved_message,
        context=conversation.context,
        conversation_state=conversation.state,
        now=now,
        prompt_builder=webhook_router._booking_prompt_for_expected_reply_type,
        hooks=PendingResumeBoundaryRuntimeHooks(
            set_booking_context=webhook_router._set_booking_context,
            set_expected_reply_context=webhook_router._set_expected_reply_context,
            set_conversation_context=webhook_router._set_conversation_context,
            record_decision_trace=webhook_router._record_decision_trace,
            update_message_decision_metadata=webhook_router._update_message_decision_metadata,
        ),
    )
    restored_context = restore.context
    restored = restore.restored

    assert restored is True
    assert restored_context.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    assert restored_context.get("expected_reply_reason") == "booking_interrupt"
    assert restored_context.get("booking", {}).get("last_question") == "datetime"
    assert restored_context.get("re_entry_required", {}).get("required") is False
    canonical_state = webhook_router._get_canonical_dialog_state(
        webhook_router._get_context_manager(restored_context)
    )
    assert canonical_state.get("pending_question_contract", {}).get("reason") == "booking_interrupt"
    trace = conversation.context.get("decision_trace", [])
    assert any(
        entry.get("stage") == "re_entry"
        and entry.get("decision") == "cleared"
        and entry.get("reason") == "booking_interrupt"
        for entry in trace
        if isinstance(entry, dict)
    )
    assert any(
        entry.get("stage") == "pending_resume"
        and entry.get("decision") == "restore_resolved_handoff_boundary"
        and entry.get("reason") == "resolved_handoff_resume_boundary"
        for entry in trace
        if isinstance(entry, dict)
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    assert meta.get("expected_reply_reason") == "booking_interrupt"
    assert meta.get("pending_resume_restored") is True
    assert meta.get("pending_resume_restore_reason") == "resolved_handoff_resume_boundary"
    assert meta.get("resolved_handoff_resume_boundary") is True


def test_provider_unavailable_human_request_pending_resume_skips_restore_without_booking_boundary():
    now = datetime.now(timezone.utc)
    saved_message = Mock()
    saved_message.message_metadata = {}
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={
            "context_manager": {"message_count": 7, "current_goal": "info"},
            "session_memory": {
                "active_goal": "info",
                "goal_stack": ["info"],
                "ttl_hours": 24,
                "last_updated_at": now.isoformat(),
            },
            "re_entry_required": {
                "required": True,
                "reason": "pending_resume",
                "set_at": now.isoformat(),
            },
        },
    )

    restore = _resolve_resolved_handoff_resume_boundary_restore(
        conversation=conversation,
        saved_message=saved_message,
        context=conversation.context,
        conversation_state=conversation.state,
        now=now,
        prompt_builder=webhook_router._booking_prompt_for_expected_reply_type,
        hooks=PendingResumeBoundaryRuntimeHooks(
            set_booking_context=webhook_router._set_booking_context,
            set_expected_reply_context=webhook_router._set_expected_reply_context,
            set_conversation_context=webhook_router._set_conversation_context,
            record_decision_trace=webhook_router._record_decision_trace,
            update_message_decision_metadata=webhook_router._update_message_decision_metadata,
        ),
    )
    restored_context = restore.context
    restored = restore.restored

    assert restored is False
    assert restored_context.get("expected_reply_type") is None
    assert restored_context.get("re_entry_required", {}).get("required") is True
    assert conversation.context.get("decision_trace") in (None, [])
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta == {}
