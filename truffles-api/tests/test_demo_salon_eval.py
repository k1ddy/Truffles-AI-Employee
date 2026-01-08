import asyncio
import os
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import yaml

import app.services.demo_salon_knowledge as demo_knowledge
import app.services.reminder_service as reminder_service
from app.models import Client, ClientSettings, Conversation, Handover, User
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
    "E362",
    "E363",
    "E435",
    "E436",
    "E437",
    "E438",
    "E439",
    "E440",
    "E441",
    "E442",
    "E443",
    "E444",
    "E445",
    "E446",
    "E447",
    "E448",
    "E449",
    "E450",
    "E451",
    "E452",
    "E453",
    "E454",
    "E455",
    "E456",
    "E457",
    "E458",
    "E459",
    "E460",
    "E461",
    "E462",
    "E463",
    "E464",
    "E465",
    "E466",
    "E467",
    "E468",
    "E469",
    "E470",
    "E471",
    "E472",
    "E473",
    "E474",
    "E475",
    "E476",
    "E477",
    "E478",
    "E479",
    "E480",
    "E481",
    "E482",
    "E483",
    "E484",
    "E485",
    "E486",
    "E487",
    "E488",
    "E489",
    "E490",
    "E491",
    "E492",
    "E493",
    "E494",
    "E495",
    "E496",
    "E497",
    "E498",
    "E499",
    "E500",
    "E501",
    "E502",
    "E503",
    "E504",
    "E505",
    "E506",
    "E507",
    "E508",
    "E509",
    "E510",
    "E511",
    "E512",
    "E513",
    "E514",
    "E515",
    "E516",
    "E517",
    "E518",
    "E519",
    "E520",
    "E521",
    "E522",
    "E523",
    "E524",
    "E525",
    "E526",
    "E527",
    "E528",
    "E529",
    "E530",
    "E571",
    "E572",
    "E573",
    "E574",
    "E575",
    "E576",
    "E577",
    "E578",
    "E579",
    "E580",
    "E581",
    "E582",
    "E583",
    "E584",
    "E585",
    "E586",
    "E587",
    "E588",
    "E589",
    "E590",
    "E591",
    "E592",
    "E593",
    "E594",
    "E595",
    "E596",
    "E597",
    "E598",
    "E599",
    "E600",
    "E601",
    "E602",
    "E603",
    "E604",
    "E605",
    "E606",
    "E607",
    "E608",
    "E609",
    "E610",
    "E611",
    "E612",
    "E613",
    "E614",
    "E615",
    "E616",
    "E617",
    "E618",
    "E619",
    "E620",
    "E621",
    "E622",
    "E623",
    "E624",
    "E625",
    "E626",
    "E627",
    "E628",
    "E629",
    "E630",
    "E631",
    "E632",
    "E633",
    "E634",
    "E635",
    "E636",
    "E637",
    "E638",
    "E639",
    "E640",
    "E641",
    "E642",
    "E643",
    "E644",
    "E645",
    "E646",
    "E647",
    "E648",
    "E649",
    "E650",
    "E651",
    "E652",
    "E653",
    "E654",
    "E655",
    "E656",
    "E657",
    "E658",
    "E659",
    "E660",
    "E661",
    "E662",
    "E663",
    "E664",
    "E665",
    "E666",
    "E667",
    "E668",
    "E669",
    "E670",
    "E671",
    "E672",
    "E673",
    "E674",
    "E675",
    "E676",
    "E677",
    "E678",
    "E679",
    "E680",
    "E681",
    "E682",
    "E683",
    "E684",
    "E685",
    "E686",
    "E687",
    "E688",
    "E689",
    "E690",
    "E691",
    "E692",
    "E693",
    "E694",
    "E695",
    "E696",
    "E697",
    "E698",
    "E699",
    "E700",
    "E701",
    "E702",
    "E703",
    "E704",
    "E705",
    "E706",
    "E707",
    "E708",
    "E709",
    "E710",
    "E711",
    "E744",
    "E745",
}
TURNS_EXAMPLE_CASE = {
    "id": "EX_TURNS_001",
    "tier": "long",
    "turns": [
        {"user": "What are your hours?", "expected": {"must_include_any": ["hours", "open"]}},
        {"user": "Thanks", "expected": {"must_not": ["price"]}},
    ],
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

    maybe_patch = patch("app.routers.webhook._legacy._maybe_store_service_carryover", side_effect=_wrapped)

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

    get_patch = patch("app.routers.webhook._legacy._get_service_carryover", side_effect=_get_carryover)

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
    if isinstance(result, list):
        query.first.return_value = result[0] if result else None
        query.all.return_value = result
    else:
        query.first.return_value = result
        query.all.return_value = [] if result is None else [result]
    return query


def _build_fake_db(client, settings, conversation, user, handovers=None):
    handovers = handovers or []

    def _query(model):
        if model is Client:
            return _build_query(client)
        if model is ClientSettings:
            return _build_query(settings)
        if model is Conversation:
            return _build_query(conversation)
        if model is Handover:
            return _build_query(handovers)
        if model is User:
            return _build_query(user)
        return _build_query(None)

    db = Mock()
    db.query.side_effect = _query

    def _add(item):
        if isinstance(item, Handover):
            item.conversation = conversation
            handovers.append(item)

    db.add = Mock(side_effect=_add)
    db.flush = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    return db


def _trigger_pending_sla(
    db: Mock,
    conversation: SimpleNamespace,
    handovers: list[Handover],
    fixed_now: datetime,
) -> None:
    if not handovers or conversation.state != ConversationState.PENDING.value:
        return

    backdated = fixed_now - timedelta(minutes=20)
    for handover in handovers:
        handover.conversation = conversation
        handover.created_at = backdated
        handover.status = "pending"
    conversation.escalated_at = backdated

    class _FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    patches = [
        patch("app.services.reminder_service.datetime", _FixedDateTime),
        patch("app.services.reminder_service.send_bot_response", return_value=True),
        patch("app.services.reminder_service.save_message", return_value=None),
        patch("app.services.reminder_service.get_pending_reminders", return_value=[]),
    ]
    with ExitStack() as stack:
        for patcher in patches:
            stack.enter_context(patcher)
        reminder_service.process_reminders(db)


def _run_webhook_case(user_text: str, case_id: str, local_time: str | None) -> str:
    conversation_id = uuid4()
    client = SimpleNamespace(id="client-123", name="demo_salon", config=_load_client_config_from_truth())
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
        enable_reminders=True,
        reminder_timeout_1=30,
        reminder_timeout_2=60,
        telegram_chat_id=None,
        telegram_bot_token=None,
        owner_telegram_id=None,
        enable_owner_escalation=True,
        auto_close_timeout=0,
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
    user = SimpleNamespace(id="user-123", context={}, remote_jid="77000000000@s.whatsapp.net")
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
        patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint),
        patch("app.routers.webhook._legacy.detect_multi_intent", side_effect=_fake_intent_decomp),
        patch("app.routers.webhook._legacy._get_debounce_redis", return_value=None),
        patch("app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)),
        patch("app.routers.webhook._legacy.send_bot_response", return_value=True),
        patch("app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message),
        patch("app.routers.webhook._legacy._get_user_branch_preference", return_value=None),
        patch(
            "app.routers.webhook._legacy.generate_bot_response",
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

        patches.append(patch("app.routers.webhook._legacy.datetime", _FixedDateTime))
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


def _run_webhook_conversation_turns(
    messages: list[str],
    case_id: str,
    local_time: str | None,
    pending_sla_expected: bool = False,
) -> tuple[list[str], SimpleNamespace, SimpleNamespace]:
    conversation_id = uuid4()
    client = SimpleNamespace(id="client-123", name="demo_salon", config=_load_client_config_from_truth())
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
        enable_reminders=True,
        reminder_timeout_1=30,
        reminder_timeout_2=60,
        telegram_chat_id=None,
        telegram_bot_token=None,
        owner_telegram_id=None,
        enable_owner_escalation=True,
        auto_close_timeout=0,
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
    user = SimpleNamespace(id="user-123", context={}, remote_jid="77000000000@s.whatsapp.net")
    saved_message = SimpleNamespace(id=f"msg-{case_id}", message_metadata={})
    handovers: list[Handover] = []
    db = _build_fake_db(client, settings, conversation, user, handovers)

    carryover_patches, _ = _build_service_carryover_patch()
    patches = [
        patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint),
        patch("app.routers.webhook._legacy.detect_multi_intent", side_effect=_fake_intent_decomp),
        patch("app.routers.webhook._legacy._get_debounce_redis", return_value=None),
        patch("app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)),
        patch("app.routers.webhook._legacy.send_bot_response", return_value=True),
        patch("app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message),
        patch("app.routers.webhook._legacy._get_user_branch_preference", return_value=None),
        patch(
            "app.routers.webhook._legacy.generate_bot_response",
            return_value=SimpleNamespace(ok=True, error=None, error_code=None, value=("", 0.0)),
        ),
        patch("app.services.demo_salon_knowledge.get_embedding", side_effect=lambda text, *_args, **_kwargs: demo_knowledge._local_text_embedding(text)),
        patch("app.services.demo_salon_knowledge._search_services_index", return_value=[]),
        *carryover_patches,
    ]

    effective_local_time = local_time or "12:00:00"
    fixed_now = datetime.now(timezone.utc)
    if effective_local_time:
        tz_name = get_salon_timezone()
        fixed_now = _build_fixed_now(effective_local_time, tz_name)

        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now if tz is None else fixed_now.astimezone(tz)

        patches.append(patch("app.routers.webhook._legacy.datetime", _FixedDateTime))
        patches.append(patch("app.services.demo_salon_knowledge.datetime", _FixedDateTime))

    responses: list[str] = []
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
            responses.append(response.bot_response or "")
            if pending_sla_expected and idx == 0:
                _trigger_pending_sla(db, conversation, handovers, fixed_now)
    return responses, conversation, saved_message


def _run_webhook_conversation(messages: list[str], case_id: str, local_time: str | None) -> tuple[str, SimpleNamespace, SimpleNamespace]:
    responses, conversation, saved_message = _run_webhook_conversation_turns(
        messages,
        case_id,
        local_time,
    )
    last_response = responses[-1] if responses else ""
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


def _coerce_expected(expected: object, case_id: str) -> dict:
    if expected is None:
        return {}
    if not isinstance(expected, dict):
        raise AssertionError(f"{case_id}: expected must be a mapping")
    return expected


def _normalize_turns(turns: object, case_id: str) -> list[dict]:
    if not turns:
        return []
    if not isinstance(turns, list):
        raise AssertionError(f"{case_id}: turns must be a list")
    normalized: list[dict] = []
    for idx, turn in enumerate(turns, start=1):
        if isinstance(turn, str):
            user_text = turn
            expected = None
        elif isinstance(turn, dict):
            user_text = turn.get("user") or turn.get("message") or turn.get("text")
            expected = turn.get("expected")
        else:
            raise AssertionError(f"{case_id}: turn {idx} must be a string or mapping")
        if not isinstance(user_text, str) or not user_text.strip():
            raise AssertionError(f"{case_id}: turn {idx} missing user text")
        if expected is not None and not isinstance(expected, dict):
            raise AssertionError(f"{case_id}: turn {idx} expected must be a mapping")
        normalized.append({"user": user_text, "expected": expected})
    return normalized


def _assert_expected_response(response: str, expected: dict, case_id: str) -> None:
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


def _collect_trace_expectations(expected: dict, trace_expectations: list[dict]) -> None:
    items = expected.get("trace_contains") or []
    if isinstance(items, list):
        trace_expectations.extend(items)


def _filter_cases(cases: list[dict]) -> list[dict]:
    if EVAL_TIER in {"all", "full"}:
        return cases
    if EVAL_TIER == "long":
        long_cases = [case for case in cases if str(case.get("tier", "")).strip().lower() == "long"]
        assert long_cases, "Long eval set is empty"
        return long_cases
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
        case_expected = _coerce_expected(case.get("expected"), case_id)
        pending_sla_expected = bool(
            case.get("pending_sla_expected") or case_expected.get("pending_sla_expected")
        )
        turns = _normalize_turns(case.get("turns"), case_id)
        messages = case.get("messages")
        conversation = None
        saved_message = None
        trace_expectations: list[dict] = []

        if turns and messages:
            raise AssertionError(f"{case_id}: use turns or messages, not both")
        if turns:
            messages = [turn["user"] for turn in turns]

        expected_action = case_expected.get("action")
        if expected_action == "booking_flow":
            booking_messages = messages if messages else ([user_text] if user_text else [])
            with patch("app.routers.webhook._legacy._extract_service_hint", side_effect=_fake_service_hint):
                booking_signal = webhook_router._has_booking_signal(
                    booking_messages,
                    client_slug="demo_salon",
                    message_text=booking_messages[-1] if booking_messages else None,
                )
                assert booking_signal is True, f"{case_id}: booking signal not detected"
                booking_state = webhook_router._update_booking_from_messages(
                    {},
                    booking_messages,
                    client_slug="demo_salon",
                )
            for slot in case_expected.get("booking_slots", []):
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
        must_include = case_expected.get("must_include") or []
        wants_cta = any(
            isinstance(item, str) and "Хотите записаться" in item for item in must_include
        )
        if turns:
            responses, conversation, saved_message = _run_webhook_conversation_turns(
                messages,
                case_id,
                str(local_time) if local_time else None,
                pending_sla_expected=pending_sla_expected,
            )
            for idx, turn in enumerate(turns, start=1):
                step_expected = turn.get("expected") or {}
                if step_expected:
                    _assert_expected_response(
                        responses[idx - 1] if responses else "",
                        step_expected,
                        f"{case_id}/turn{idx}",
                    )
                    _collect_trace_expectations(step_expected, trace_expectations)
            if case_expected:
                response = responses[-1] if responses else ""
                _assert_expected_response(response, case_expected, case_id)
                _collect_trace_expectations(case_expected, trace_expectations)
        else:
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
            if case_expected:
                _assert_expected_response(response, case_expected, case_id)
                _collect_trace_expectations(case_expected, trace_expectations)

        if trace_expectations:
            assert conversation is not None, f"{case_id}: trace assertions require conversation context"
            decision_trace = _get_decision_trace(conversation)
            for requirement in trace_expectations:
                _assert_trace_contains(decision_trace, requirement, case_id)
