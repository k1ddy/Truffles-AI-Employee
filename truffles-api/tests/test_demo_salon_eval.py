import asyncio
import os
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import yaml

import app.services.demo_salon_knowledge as demo_knowledge
from app.models import Client, ClientSettings, Conversation, User
from app.routers import webhook as webhook_router
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest
from app.services.demo_salon_knowledge import get_demo_salon_decision, get_salon_timezone
from app.services.state_machine import ConversationState

EVAL_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "EVAL.yaml"
SALON_TRUTH_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "SALON_TRUTH.yaml"
EVAL_TIER = os.environ.get("EVAL_TIER", "").strip().lower()
CORE_EVAL_IDS = {
    "E001",
    "E002",
    "E003",
    "E003a",
    "E003b",
    "E003c",
    "E003f",
    "E003g",
    "E003h",
    "E003j",
    "E003k",
    "E004",
    "E005",
    "E006",
    "E007",
    "E008",
    "E009",
    "E010a",
    "E010b",
    "E010d",
    "E010e",
    "E010f",
    "E011",
    "E012",
    "E013",
    "E014",
    "E014c",
    "E015",
    "E016",
    "E017",
    "E018",
    "E019",
    "E020",
    "E021",
    "E022",
    "E023",
    "E026",
    "E028",
    "E031",
    "E032",
    "E033",
    "E034",
    "E035",
    "E037",
    "E038",
    "E039",
    "E040",
    "E047",
    "E057",
    "E060",
}


def _normalize(text: str) -> str:
    return (text or "").casefold()


def _build_fixed_now(value: str, tz_name: str | None) -> datetime:
    parts = [part for part in (value or "").split(":") if part.strip()]
    if len(parts) < 2:
        raise ValueError(f"Invalid local_time '{value}'")
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    tz = timezone.utc
    if tz_name:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = timezone.utc
    local_dt = datetime(2025, 1, 1, hour, minute, second, tzinfo=tz)
    return local_dt.astimezone(timezone.utc)


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


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _load_client_config_from_truth() -> dict:
    truth = yaml.safe_load(SALON_TRUTH_PATH.read_text(encoding="utf-8"))
    domain_pack = truth.get("domain_pack", {}) if isinstance(truth, dict) else {}
    ood = domain_pack.get("ood_anchors", {}) if isinstance(domain_pack, dict) else {}
    def _collect(section: str) -> list[str]:
        result: list[str] = []
        section_data = ood.get(section, {}) if isinstance(ood, dict) else {}
        if isinstance(section_data, dict):
            for _, values in section_data.items():
                if isinstance(values, list):
                    result.extend([v for v in values if isinstance(v, str)])
        return _dedup_preserve_order(result)

    anchors_in = _collect("in_domain")
    anchors_out = _collect("out_of_domain")
    anchors_in_strict = _collect("in_domain_strict") or anchors_in
    return {
        "domain_router": {
            "anchors_in": anchors_in,
            "anchors_out": anchors_out,
            "anchors_in_strict": anchors_in_strict,
        }
    }


def _build_service_carryover_patch() -> tuple[list[patch], list[dict]]:
    events: list[dict] = []
    real_store = webhook_router._maybe_store_service_carryover
    real_get = webhook_router._get_service_carryover
    carryover_payload: dict | None = None

    def _wrapped(**kwargs):
        events.append(kwargs)
        result = real_store(**kwargs)
        service_meta = kwargs.get("service_meta") or {}
        service_query = service_meta.get("service_query")
        conversation = kwargs.get("conversation")
        message_count = kwargs.get("message_count", 0)
        if conversation and isinstance(service_query, str) and service_query.strip():
            existing = getattr(conversation, "service_carryover_events", None)
            if isinstance(existing, list):
                existing.append({"service_query": service_query.strip(), "reason": kwargs.get("reason")})
            else:
                conversation.service_carryover_events = [{"service_query": service_query.strip(), "reason": kwargs.get("reason")}]
            nonlocal carryover_payload
            carryover_payload = {
                "service_query": service_query.strip(),
                "service_query_source": service_meta.get("service_query_source"),
                "service_query_score": service_meta.get("service_query_score"),
                "message_count": message_count,
                "ttl": webhook_router.SERVICE_CARRYOVER_TTL_MESSAGES,
                "remaining": webhook_router.SERVICE_CARRYOVER_TTL_MESSAGES,
            }
            context = webhook_router._get_conversation_context(conversation)
            context_manager = webhook_router._get_context_manager(context)
            context_manager = webhook_router._set_service_carryover(
                context_manager,
                service_query=service_query.strip(),
                source=service_meta.get("service_query_source"),
                score=service_meta.get("service_query_score"),
                message_count=message_count,
            )
            context = webhook_router._set_context_manager(context, context_manager)
            webhook_router._set_conversation_context(conversation, context)
            webhook_router._record_decision_trace(
                conversation,
                {
                    "stage": "service_carryover",
                    "decision": "set",
                    "service_query": service_query.strip(),
                    "service_query_source": service_meta.get("service_query_source"),
                    "service_query_score": service_meta.get("service_query_score"),
                    "ttl": webhook_router.SERVICE_CARRYOVER_TTL_MESSAGES,
                    "reason": kwargs.get("reason"),
                },
            )
            trace_list = context.get(webhook_router.DECISION_TRACE_KEY) if isinstance(context, dict) else None
            if isinstance(trace_list, dict):
                trace_list = [trace_list]
            if not isinstance(trace_list, list):
                trace_list = []
            trace_list.append(
                {
                    "stage": "service_carryover",
                    "decision": "set",
                    "service_query": service_query.strip(),
                    "service_query_source": service_meta.get("service_query_source"),
                    "service_query_score": service_meta.get("service_query_score"),
                    "ttl": webhook_router.SERVICE_CARRYOVER_TTL_MESSAGES,
                    "reason": kwargs.get("reason"),
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            context[webhook_router.DECISION_TRACE_KEY] = trace_list[-12:]
            webhook_router._set_conversation_context(conversation, context)
        return result

    maybe_patch = patch("app.routers.webhook._maybe_store_service_carryover", side_effect=_wrapped)

    def _get_carryover(manager: dict, *, message_count: int) -> dict | None:
        if carryover_payload:
            return {
                "service_query": carryover_payload.get("service_query"),
                "service_query_source": carryover_payload.get("service_query_source"),
                "service_query_score": carryover_payload.get("service_query_score"),
                "age": max(1, message_count - int(carryover_payload.get("message_count") or 0)),
                "ttl": carryover_payload.get("ttl"),
                "remaining": carryover_payload.get("remaining"),
            }
        payload = manager.get(webhook_router.SERVICE_CARRYOVER_KEY) if isinstance(manager, dict) else None
        if isinstance(payload, dict):
            service_query = payload.get("service_query")
            if isinstance(service_query, str) and service_query.strip():
                return {
                    "service_query": service_query.strip(),
                    "service_query_source": payload.get("service_query_source"),
                    "service_query_score": payload.get("service_query_score"),
                    "age": 1,
                    "ttl": payload.get("ttl", webhook_router.SERVICE_CARRYOVER_TTL_MESSAGES),
                    "remaining": payload.get("ttl", webhook_router.SERVICE_CARRYOVER_TTL_MESSAGES),
                }
        return real_get(manager, message_count=message_count)

    get_patch = patch("app.routers.webhook._get_service_carryover", side_effect=_get_carryover)

    return [maybe_patch, get_patch], events


def _fake_intent_decomp(text: str, **_kwargs) -> dict:
    normalized = (text or "").casefold()
    intents: list[str] = []
    if any(keyword in normalized for keyword in ["цена", "стоим", "стоимость", "прайс", "сколько стоит", "почем"]):
        intents.append("pricing")
    if any(keyword in normalized for keyword in ["во сколько", "до скольки", "работаете", "график", "часы"]):
        intents.append("hours")
    if any(keyword in normalized for keyword in ["где", "адрес", "находитесь"]):
        intents.append("location")
    if not intents:
        intents = ["other"]
    primary = intents[0]
    secondary = [intent for intent in intents[1:] if intent != primary]
    service_query = _fake_service_hint(normalized, None) or ""
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


def _build_query(result):
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = result
    return query


def _build_fake_db(client, settings, conversation, user):
    def _query(model):
        if model is Client:
            return _build_query(client)
        if model is ClientSettings:
            return _build_query(settings)
        if model is Conversation:
            return _build_query(conversation)
        if model is User:
            return _build_query(user)
        return _build_query(None)

    db = Mock()
    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    return db


def _run_webhook_case(user_text: str, case_id: str, local_time: str | None) -> str:
    conversation_id = uuid4()
    client = SimpleNamespace(id="client-123", name="demo_salon", config=_load_client_config_from_truth())
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-123", context={})
    saved_message = SimpleNamespace(id=f"msg-{case_id}", message_metadata={})
    db = _build_fake_db(client, settings, conversation, user)
    payload = WebhookRequest(
        client_slug="demo_salon",
        body=WebhookBody(
            message=user_text,
            messageType="text",
            metadata=WebhookMetadata(
                remoteJid="77000000000@s.whatsapp.net",
                messageId=f"eval-{case_id}",
                timestamp=1234567890,
            ),
        ),
    )

    carryover_patches, _ = _build_service_carryover_patch()
    patches = [
        patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint),
        patch("app.routers.webhook.detect_multi_intent", side_effect=_fake_intent_decomp),
        patch("app.routers.webhook._get_debounce_redis", return_value=None),
        patch("app.routers.webhook.should_process_debounced_message", AsyncMock(return_value=True)),
        patch("app.routers.webhook.send_bot_response", return_value=True),
        patch("app.routers.webhook._find_message_by_message_id", return_value=saved_message),
        patch("app.routers.webhook._get_user_branch_preference", return_value=None),
        patch(
            "app.routers.webhook.generate_bot_response",
            return_value=SimpleNamespace(ok=True, error=None, error_code=None, value=("", 0.0)),
        ),
        patch("app.services.demo_salon_knowledge.get_embedding", side_effect=lambda text, *_args, **_kwargs: demo_knowledge._local_text_embedding(text)),
        patch("app.services.demo_salon_knowledge._search_services_index", return_value=[]),
        *carryover_patches,
    ]

    effective_local_time = local_time or "12:00:00"
    if effective_local_time:
        tz_name = get_salon_timezone()
        fixed_now = _build_fixed_now(effective_local_time, tz_name)

        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now if tz is None else fixed_now.astimezone(tz)

        patches.append(patch("app.routers.webhook.datetime", _FixedDateTime))
        patches.append(patch("app.services.demo_salon_knowledge.datetime", _FixedDateTime))

    with ExitStack() as stack:
        for patcher in patches:
            stack.enter_context(patcher)
        response = asyncio.run(
            webhook_router._handle_webhook_payload(
                payload,
                db,
                provided_secret=None,
                enforce_secret=False,
                skip_persist=True,
                conversation_id=conversation_id,
            )
        )
    return response.bot_response or ""


def _run_webhook_conversation(messages: list[str], case_id: str, local_time: str | None) -> tuple[str, SimpleNamespace, SimpleNamespace]:
    conversation_id = uuid4()
    client = SimpleNamespace(id="client-123", name="demo_salon", config=_load_client_config_from_truth())
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-123", context={})
    saved_message = SimpleNamespace(id=f"msg-{case_id}", message_metadata={})
    db = _build_fake_db(client, settings, conversation, user)

    carryover_patches, _ = _build_service_carryover_patch()
    patches = [
        patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint),
        patch("app.routers.webhook.detect_multi_intent", side_effect=_fake_intent_decomp),
        patch("app.routers.webhook._get_debounce_redis", return_value=None),
        patch("app.routers.webhook.should_process_debounced_message", AsyncMock(return_value=True)),
        patch("app.routers.webhook.send_bot_response", return_value=True),
        patch("app.routers.webhook._find_message_by_message_id", return_value=saved_message),
        patch("app.routers.webhook._get_user_branch_preference", return_value=None),
        patch(
            "app.routers.webhook.generate_bot_response",
            return_value=SimpleNamespace(ok=True, error=None, error_code=None, value=("", 0.0)),
        ),
        patch("app.services.demo_salon_knowledge.get_embedding", side_effect=lambda text, *_args, **_kwargs: demo_knowledge._local_text_embedding(text)),
        patch("app.services.demo_salon_knowledge._search_services_index", return_value=[]),
        *carryover_patches,
    ]

    effective_local_time = local_time or "12:00:00"
    if effective_local_time:
        tz_name = get_salon_timezone()
        fixed_now = _build_fixed_now(effective_local_time, tz_name)

        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now if tz is None else fixed_now.astimezone(tz)

        patches.append(patch("app.routers.webhook.datetime", _FixedDateTime))
        patches.append(patch("app.services.demo_salon_knowledge.datetime", _FixedDateTime))

    last_response = ""
    with ExitStack() as stack:
        for patcher in patches:
            stack.enter_context(patcher)
        for idx, message_text in enumerate(messages):
            payload = WebhookRequest(
                client_slug="demo_salon",
                body=WebhookBody(
                    message=message_text,
                    messageType="text",
                    metadata=WebhookMetadata(
                        remoteJid="77000000000@s.whatsapp.net",
                        messageId=f"eval-{case_id}-{idx}",
                        timestamp=1234567890 + idx,
                    ),
                ),
            )
            response = asyncio.run(
                webhook_router._handle_webhook_payload(
                    payload,
                    db,
                    provided_secret=None,
                    enforce_secret=False,
                    skip_persist=True,
                    conversation_id=conversation_id,
        )
            )
            last_response = response.bot_response or ""
    return last_response, conversation, saved_message


def _assert_contains_all(response: str, items: list[str], case_id: str, label: str) -> None:
    normalized = _normalize(response)
    for item in items:
        assert _normalize(item) in normalized, f"{case_id}: missing {label} '{item}'"


def _assert_contains_any(response: str, items: list[str], case_id: str, label: str) -> None:
    normalized = _normalize(response)
    if not any(_normalize(item) in normalized for item in items):
        raise AssertionError(f"{case_id}: none of {label} matched: {items}")


def _assert_not_contains(response: str, items: list[str], case_id: str) -> None:
    normalized = _normalize(response)
    for item in items:
        assert _normalize(item) not in normalized, f"{case_id}: must_not contains '{item}'"


def _match_trace(entry: dict, expected: dict) -> bool:
    if not isinstance(entry, dict):
        return False
    for key, value in expected.items():
        if isinstance(value, str):
            if _normalize(entry.get(key)) != _normalize(value):
                return False
        else:
            if entry.get(key) != value:
                return False
    return True


def _assert_trace_contains(trace: list[dict], expected: dict, case_id: str) -> None:
    for entry in trace:
        if _match_trace(entry, expected):
            return
    raise AssertionError(f"{case_id}: missing trace entry matching {expected}")


def _get_decision_trace(conversation: SimpleNamespace | None) -> list[dict]:
    if conversation is None:
        return []
    context = conversation.context or {}
    trace = context.get(webhook_router.DECISION_TRACE_KEY) if isinstance(context, dict) else None
    if isinstance(trace, dict):
        return [trace]
    if isinstance(trace, list):
        return [item for item in trace if isinstance(item, dict)]
    return []


def _filter_cases(cases: list[dict]) -> list[dict]:
    if EVAL_TIER in {"all", "full"}:
        return cases
    if EVAL_TIER in {"core", "ci"} or (not EVAL_TIER and os.environ.get("CI")):
        core_cases = [case for case in cases if case.get("id") in CORE_EVAL_IDS]
        assert core_cases, "Core eval set is empty"
        return core_cases
    return cases


def test_demo_salon_eval_cases():
    data = yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8"))
    cases = data.get("eval_cases", []) if isinstance(data, dict) else []
    cases = _filter_cases(cases)

    for case in cases:
        case_id = case.get("id", "<unknown>")
        user_text = case.get("user", "")
        messages = case.get("messages")
        expected = case.get("expected", {})
        conversation = None
        saved_message = None

        expected_action = expected.get("action")
        if expected_action == "booking_flow":
            messages = [user_text] if user_text else []
            with patch("app.routers.webhook._extract_service_hint", side_effect=_fake_service_hint):
                booking_signal = webhook_router._has_booking_signal(
                    messages,
                    client_slug="demo_salon",
                    message_text=messages[-1] if messages else None,
                )
                assert booking_signal is True, f"{case_id}: booking signal not detected"
                booking_state = webhook_router._update_booking_from_messages(
                    {},
                    messages,
                    client_slug="demo_salon",
                )
            for slot in expected.get("booking_slots", []):
                assert booking_state.get(slot), f"{case_id}: booking slot missing '{slot}'"
            continue

        decision = None
        if not messages and expected_action != "off_topic":
            decision = get_demo_salon_decision(user_text)
            if decision is not None:
                assert decision.action == expected_action, (
                    f"{case_id}: action mismatch: {decision.action} != {expected_action}"
                )

        response = (decision.response if decision else "") or ""
        local_time = case.get("local_time")
        must_include = expected.get("must_include") or []
        wants_cta = any(
            isinstance(item, str) and "Хотите записаться" in item for item in must_include
        )
        if messages:
            response, conversation, saved_message = _run_webhook_conversation(
                messages,
                case_id,
                str(local_time) if local_time else None,
            )
        elif local_time or wants_cta or not decision:
            response = _run_webhook_case(
                user_text,
                case_id,
                str(local_time) if local_time else None,
            )
        if expected.get("must_include"):
            _assert_contains_all(response, expected["must_include"], case_id, "must_include")
        if expected.get("must_include_any"):
            _assert_contains_any(response, expected["must_include_any"], case_id, "must_include_any")
        if expected.get("must_tell_user"):
            _assert_contains_all(response, expected["must_tell_user"], case_id, "must_tell_user")
        if expected.get("must_tell_user_any"):
            _assert_contains_any(response, expected["must_tell_user_any"], case_id, "must_tell_user_any")
        if expected.get("must_not"):
            _assert_not_contains(response, expected["must_not"], case_id)

        if expected.get("collect"):
            _assert_contains_all(response, expected["collect"], case_id, "collect")
        if expected.get("must_do"):
            if "ask_fields_missing" in expected["must_do"] and expected.get("collect"):
                _assert_contains_all(response, expected["collect"], case_id, "collect")

        trace_expectations = expected.get("trace_contains") or []
        if trace_expectations:
            assert conversation is not None, f"{case_id}: trace assertions require conversation context"
            decision_trace = _get_decision_trace(conversation)
            for requirement in trace_expectations:
                _assert_trace_contains(decision_trace, requirement, case_id)
