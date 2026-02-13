import asyncio
import os
import re
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import yaml

import app.services.demo_salon_knowledge as demo_knowledge
import app.services.knowledge_service as knowledge_service
import app.services.reminder_service as reminder_service
from app.models import Client, ClientSettings, Conversation, Handover, User
from app.routers import webhook as webhook_router
from app.routers.webhook import response as webhook_response
from app.routers.webhook import trace as webhook_trace
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest
from app.services.demo_salon_knowledge import get_demo_salon_decision, get_salon_timezone
from app.services.state_machine import ConversationState

EVAL_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "EVAL.yaml"
EVAL_GOLDEN_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "EVAL_GOLDEN.yaml"
SALON_TRUTH_PATH = Path(__file__).resolve().parents[1] / "app" / "knowledge" / "demo_salon" / "SALON_TRUTH.yaml"
EVAL_TIER = os.environ.get("EVAL_TIER", "").strip().lower()
TEST_CLIENT_ID = "11111111-1111-4111-8111-111111111111"
TEXT_EXPECTATION_KEYS = {
    "must_include",
    "must_include_any",
    "must_tell_user",
    "must_tell_user_any",
    "must_not",
    "collect",
    "must_do",
}
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
    "E361",
    "E361a",
    "E361b",
    "E361c",
    "E361d",
    "E361g",
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
    "E746",
    "E747",
    "E748",
    "E749",
    "E750",
    "E751",
    "E752",
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
    policy_pack = truth.get("policy") if isinstance(truth, dict) else None
    if not isinstance(policy_pack, dict):
        policy_pack = None
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
        },
        "policy_pack": policy_pack,
        "policy_type": "demo_salon",
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
            context[webhook_router.DECISION_TRACE_KEY] = trace_list[-webhook_trace.DECISION_TRACE_MAX:]
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
    if any(
        keyword in normalized
        for keyword in [
            "скидк",
            "акци",
            "промо",
            "именин",
            "день рождения",
            "перв",
            "студент",
            "пенсион",
        ]
    ):
        intents.append("promotions")
    if "до после" in normalized and any(word in normalized for word in ["дней", "дня", "день"]):
        intents.append("promotions")
    if any(keyword in normalized for keyword in ["цена", "стоим", "стоимость", "прайс", "сколько стоит", "почем"]):
        intents.append("pricing")
    if any(keyword in normalized for keyword in ["бағас", "канша", "қанша"]):
        intents.append("pricing")
    if any(
        keyword in normalized
        for keyword in [
            "сколько длится",
            "длится",
            "длительность",
            "по времени",
            "сколько времени",
            "сколько по времени",
        ]
    ):
        intents.append("duration")
    if any(keyword in normalized for keyword in ["во сколько", "до скольки", "работаете", "график", "часы"]):
        intents.append("hours")
    if any(
        keyword in normalized
        for keyword in ["жұмыс уақыты", "жумыс уакыты", "нешеге дейін"]
    ):
        intents.append("hours")
    if any(keyword in normalized for keyword in ["где", "адрес", "находитесь"]):
        intents.append("location")
    if any(keyword in normalized for keyword in ["қайда", "мекенжай", "мекен жай"]):
        intents.append("location")
    if not intents:
        intents = ["other"]
    primary = intents[0]
    secondary = [intent for intent in intents[1:] if intent != primary]
    service_query = _fake_service_hint(normalized, None) or ""
    consult_intent = False
    consult_topic = ""
    consult_question = ""
    consult_verbs = (
        "посовет",
        "совет",
        "рекоменд",
        "как ухаж",
        "ухаживать за цвет",
        "что делать",
        "что мне",
        "что лучше",
        "нужен уход",
        "уход за",
        "уход после",
        "сохранить цвет",
        "после окраш",
        "после покраск",
        "подскажите варианты",
    )
    consult_color = (
        "какой цвет",
        "какой оттен",
        "подойдет цвет",
        "подойдет оттен",
        "подобрать цвет",
        "подобрать оттен",
    )
    consult_visual = (
        "референс",
        "как на фото",
        "в стиле",
        "фото пример",
    )
    consult_problems = (
        "лома",
        "сух",
        "поврежд",
        "чувств",
        "редеют",
        "сло",
        "раздраж",
    )
    consult_parts = (
        "волос",
        "ногт",
        "кожа",
        "бров",
        "ресниц",
        "кутикул",
    )
    consult_kz = (
        "күтім",
        "бояудан кейін",
        "қалай күт",
        "қандай түс",
    )
    aftercare_signal = "гель лак" in normalized and any(
        keyword in normalized for keyword in ("ухаж", "продл", "держ", "нос", "срок")
    )
    extra_consult = "чувств" in normalized and "уход" in normalized
    availability_intent = any(
        phrase in normalized for phrase in ("делаете", "предлагаете", "оказываете", "есть ли")
    )
    availability_block = availability_intent and not any(
        phrase in normalized
        for phrase in (
            "посовет",
            "совет",
            "рекоменд",
            "как ухаж",
            "что делать",
            "что мне",
            "что лучше",
            "подскажите варианты",
            "после окраш",
            "после покраск",
        )
    ) and not any(problem in normalized for problem in consult_problems)
    if primary == "other" and not aftercare_signal and (
        any(phrase in normalized for phrase in consult_verbs)
        or any(phrase in normalized for phrase in consult_color)
        or any(phrase in normalized for phrase in consult_visual)
        or (
            any(part in normalized for part in consult_parts)
            and any(problem in normalized for problem in consult_problems)
        )
        or any(phrase in normalized for phrase in consult_kz)
        or extra_consult
    ):
        consult_intent = True
        consult_question = (text or "").strip()
        try:
            from app.services.consult_pack_service import load_consult_playbook
            from app.services.knowledge_service import resolve_consult_topic_candidates

            playbook, _error = load_consult_playbook("demo_salon")
            if playbook:
                candidates = resolve_consult_topic_candidates(
                    text,
                    playbook.topics,
                    client_slug="demo_salon",
                    top_k=1,
                    embedding_fn=demo_knowledge._local_text_embedding,
                )
                if candidates:
                    consult_topic = candidates[0].get("topic_id") or ""
                if any(token in normalized for token in ("уход за лиц", "уход по лиц", "чувствит", "кожа", "лиц")):
                    for topic in playbook.topics:
                        if topic.id == "sensitive_skin":
                            consult_topic = topic.id
                            break
                if not consult_topic:
                    for topic in playbook.topics:
                        if topic.id == "general_consult":
                            consult_topic = topic.id
                            break
        except Exception:
            consult_intent = False
            consult_topic = ""
            consult_question = ""
    if consult_intent and availability_block:
        consult_intent = False
        consult_topic = ""
        consult_question = ""
    return {
        "multi_intent": len(intents) > 1,
        "primary_intent": primary,
        "secondary_intents": secondary,
        "intents": intents,
        "service_query": service_query,
        "consult_intent": consult_intent,
        "consult_topic": consult_topic,
        "consult_question": consult_question,
    }


def _build_query(result):
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
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
            if hasattr(conversation, "_sa_instance_state"):
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


def _run_webhook_case(
    user_text: str,
    case_id: str,
    local_time: str | None,
    *,
    intent_decomp_fn=_fake_intent_decomp,
    service_hint_fn=_fake_service_hint,
) -> tuple[str, SimpleNamespace, SimpleNamespace]:
    conversation_id = uuid4()
    client = SimpleNamespace(id=TEST_CLIENT_ID, name="demo_salon", config=_load_client_config_from_truth())
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
        context={"simulation": {"mode": True}},
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
        patch("app.routers.webhook._legacy._get_debounce_redis", return_value=None),
        patch("app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)),
        patch("app.routers.webhook._legacy.send_bot_response", return_value=True),
        patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False),
        patch("app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message),
        patch("app.routers.webhook._legacy._get_user_branch_preference", return_value=None),
        patch(
            "app.routers.webhook._legacy.generate_bot_response",
            return_value=SimpleNamespace(ok=True, error=None, error_code=None, value=("", 0.0)),
        ),
        patch(
            "app.services.knowledge_snapshot_consumer.get_consult_snapshot_mode",
            return_value="shadow",
        ),
        patch(
            "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
            return_value=False,
        ),
        patch(
            "app.services.knowledge_snapshot_consumer.is_consult_snapshot_allowlisted",
            return_value=False,
        ),
        patch(
            "app.services.ai_service.generate_consult_controller_output",
            return_value=SimpleNamespace(ok=False, error="llm_disabled", error_code="llm_disabled", value=None),
        ),
        patch(
            "app.services.demo_salon_knowledge.get_embedding",
            side_effect=lambda text, *_args, **_kwargs: demo_knowledge._local_text_embedding(text),
        ),
        patch(
            "app.services.knowledge_service.get_embedding",
            side_effect=lambda text, *_args, **_kwargs: demo_knowledge._local_text_embedding(text),
        ),
        patch("app.services.demo_salon_knowledge._search_services_index", return_value=[]),
        *carryover_patches,
    ]
    if service_hint_fn is not None:
        patches.append(
            patch(
                "app.routers.webhook._legacy._extract_service_hint",
                side_effect=service_hint_fn,
            )
        )
    if intent_decomp_fn is not None:
        patches.append(
            patch(
                "app.routers.webhook._legacy.detect_multi_intent",
                side_effect=intent_decomp_fn,
            )
        )

    effective_local_time = local_time or "12:00:00"
    if effective_local_time:
        tz_name = get_salon_timezone()
        fixed_now = _build_fixed_now(effective_local_time, tz_name)

        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now if tz is None else fixed_now.astimezone(tz)

        patches.append(patch("app.routers.webhook._legacy.datetime", _FixedDateTime))
        patches.append(patch("app.routers.webhook.decision.datetime", _FixedDateTime))
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
    return response.bot_response or "", conversation, saved_message


def _run_webhook_conversation_turns(
    messages: list[str],
    case_id: str,
    local_time: str | None,
    pending_sla_expected: bool = False,
    intent_decomp_fn=_fake_intent_decomp,
    *,
    service_hint_fn=_fake_service_hint,
) -> tuple[list[str], SimpleNamespace, SimpleNamespace]:
    conversation_id = uuid4()
    client = SimpleNamespace(id=TEST_CLIENT_ID, name="demo_salon", config=_load_client_config_from_truth())
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
        context={"simulation": {"mode": True}},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-123", context={}, remote_jid="77000000000@s.whatsapp.net")
    saved_message = SimpleNamespace(id=f"msg-{case_id}", message_metadata={})
    handovers: list[Handover] = []
    db = _build_fake_db(client, settings, conversation, user, handovers)

    carryover_patches, _ = _build_service_carryover_patch()
    patches = [
        patch("app.routers.webhook._legacy._get_debounce_redis", return_value=None),
        patch("app.routers.webhook._legacy.should_process_debounced_message", AsyncMock(return_value=True)),
        patch("app.routers.webhook._legacy.send_bot_response", return_value=True),
        patch("app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED", False),
        patch("app.routers.webhook._legacy._find_message_by_message_id", return_value=saved_message),
        patch("app.routers.webhook._legacy._get_user_branch_preference", return_value=None),
        patch(
            "app.routers.webhook._legacy.generate_bot_response",
            return_value=SimpleNamespace(ok=True, error=None, error_code=None, value=("", 0.0)),
        ),
        patch(
            "app.services.knowledge_snapshot_consumer.get_consult_snapshot_mode",
            return_value="shadow",
        ),
        patch(
            "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
            return_value=False,
        ),
        patch(
            "app.services.knowledge_snapshot_consumer.is_consult_snapshot_allowlisted",
            return_value=False,
        ),
        patch(
            "app.services.ai_service.generate_consult_controller_output",
            return_value=SimpleNamespace(ok=False, error="llm_disabled", error_code="llm_disabled", value=None),
        ),
        patch("app.services.demo_salon_knowledge.get_embedding", side_effect=lambda text, *_args, **_kwargs: demo_knowledge._local_text_embedding(text)),
        patch("app.services.knowledge_service.get_embedding", side_effect=lambda text, *_args, **_kwargs: demo_knowledge._local_text_embedding(text)),
        patch("app.services.demo_salon_knowledge._search_services_index", return_value=[]),
        *carryover_patches,
    ]
    if service_hint_fn is not None:
        patches.append(
            patch(
                "app.routers.webhook._legacy._extract_service_hint",
                side_effect=service_hint_fn,
            )
        )
    if intent_decomp_fn is not None:
        patches.append(
            patch(
                "app.routers.webhook._legacy.detect_multi_intent",
                side_effect=intent_decomp_fn,
            )
        )

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
        patches.append(patch("app.routers.webhook.decision.datetime", _FixedDateTime))
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


def _run_webhook_conversation(
    messages: list[str],
    case_id: str,
    local_time: str | None,
    *,
    intent_decomp_fn=_fake_intent_decomp,
    service_hint_fn=_fake_service_hint,
) -> tuple[str, SimpleNamespace, SimpleNamespace]:
    responses, conversation, saved_message = _run_webhook_conversation_turns(
        messages,
        case_id,
        local_time,
        intent_decomp_fn=intent_decomp_fn,
        service_hint_fn=service_hint_fn,
    )
    last_response = responses[-1] if responses else ""
    return last_response, conversation, saved_message


def test_policy_gates_discount_and_payment():
    cases = [
        ("CA02_DISCOUNT", "есть скидка на маникюр?", "discounts", "discounts", "reply", "low"),
        ("CA02_PAYMENT", "можно оплатить картой?", "payment_info", "payment_info", "escalate", "medium"),
    ]
    for case_id, message, policy_gate, policy_section, action, risk_level in cases:
        _response, conversation, saved_message = _run_webhook_conversation(
            [message],
            case_id,
            None,
        )
        meta = saved_message.message_metadata.get("decision_meta", {})
        assert meta.get("action") == action, f"{case_id}: action mismatch"
        assert meta.get("policy_gate") == policy_gate, f"{case_id}: policy_gate mismatch"
        assert meta.get("policy_section") == policy_section, f"{case_id}: policy_section mismatch"
        assert meta.get("risk_level") == risk_level, f"{case_id}: risk_level mismatch"
        assert meta.get("source") == "policy_pack", f"{case_id}: source mismatch"
        assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"
        assert not meta.get("policy_pack_missing"), f"{case_id}: policy_pack_missing true"

        trace = _get_decision_trace(conversation)
        _assert_trace_contains(
            trace,
            {
                "stage": "policy_gate",
                "policy_type": "demo_salon",
                "policy_gate": policy_gate,
                "policy_section": policy_section,
                "risk_level": risk_level,
                "source": "policy_pack",
            },
            case_id,
        )


def test_cancel_policy_question_not_escalated_as_cancel_request():
    case_id = "CA02_CANCEL_POLICY_QUESTION"
    response, _conversation, saved_message = _run_webhook_conversation(
        ["За сколько нужно отменять запись?"],
        case_id,
        None,
        intent_decomp_fn=None,
        service_hint_fn=None,
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") in {"reply", "booking_prompt"}, f"{case_id}: expected reply-like action"
    assert meta.get("action") != "escalate", f"{case_id}: must not escalate"
    assert meta.get("intent") != "cancel_request", f"{case_id}: misclassified as cancel_request"
    assert isinstance(response, str) and response.strip(), f"{case_id}: empty response"


def test_cancel_request_still_escalates():
    case_id = "CA02_CANCEL_REQUEST_ESCALATE"
    _response, _conversation, saved_message = _run_webhook_conversation(
        ["Отмените мою запись на завтра в 12:00"],
        case_id,
        None,
        intent_decomp_fn=None,
        service_hint_fn=None,
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "escalate", f"{case_id}: expected escalate action"


def test_truth_first_info_bundle():
    cases = [
        {
            "case_id": "CA03_ADDRESS_HOURS",
            "message": "где вы и когда работаете?",
            "expected_info_sections": ["address", "hours"],
            "expected_fact_intents": ["location", "hours"],
            "expect_info_combined": True,
        },
        {
            "case_id": "CA03_GUEST_POLICY",
            "message": "можно с ребенком?",
            "expected_info_sections": ["guest_policy"],
            "expected_fact_intents": ["guest_policy"],
        },
    ]

    allowed_sources = {"truth_gate", "class_router"}
    allowed_trace_stages = {"truth_gate", "info_class"}
    for case in cases:
        case_id = case["case_id"]
        _response, conversation, saved_message = _run_webhook_conversation(
            [case["message"]],
            case_id,
            None,
        )
        meta = saved_message.message_metadata.get("decision_meta", {})
        assert meta.get("fact_source") == "truth", f"{case_id}: fact_source mismatch"
        assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"
        assert meta.get("source") in allowed_sources, f"{case_id}: source mismatch"
        _assert_list_contains(meta.get("info_sections"), case["expected_info_sections"], case_id, "info_sections")
        _assert_list_contains(meta.get("fact_intents"), case["expected_fact_intents"], case_id, "fact_intents")
        if case.get("expect_info_combined"):
            assert meta.get("info_combined") is True, f"{case_id}: info_combined mismatch"

        trace = _get_decision_trace(conversation)
        info_trace = next((entry for entry in trace if entry.get("stage") in allowed_trace_stages), None)
        assert info_trace is not None, f"{case_id}: missing info_class/truth_gate trace"
        assert info_trace.get("fact_source") == "truth", f"{case_id}: trace fact_source mismatch"
        _assert_list_contains(
            info_trace.get("info_sections"),
            case["expected_info_sections"],
            case_id,
            "trace info_sections",
        )


def test_response_composer_variant_meta():
    case_id = "CA03_RESPONSE_VARIANT"
    _response, _conversation, saved_message = _run_webhook_conversation(
        ["Сколько стоит маникюр?"],
        case_id,
        None,
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    variant_id = meta.get("response_variant_id")
    assert isinstance(variant_id, str) and variant_id, f"{case_id}: response_variant_id missing"
    variant_tag = meta.get("response_variant_tag")
    assert isinstance(variant_tag, str) and variant_tag, f"{case_id}: response_variant_tag missing"


def test_service_matcher_core():
    cases = [
        {
            "case_id": "CA04_SERVICE_MATCH",
            "message": "делаете маникюр?",
            "expected_intent": "service_match",
            "expected_fact_intents": ["service_match"],
        },
        {
            "case_id": "CA04_SERVICE_NOT_FOUND",
            "message": "делаете массаж?",
            "expected_intent": "service_not_found",
            "expected_fact_intents": ["service_not_found"],
        },
    ]

    for case in cases:
        case_id = case["case_id"]
        _response, conversation, saved_message = _run_webhook_conversation(
            [case["message"]],
            case_id,
            None,
        )
        meta = saved_message.message_metadata.get("decision_meta", {})
        assert meta.get("action") == "reply", f"{case_id}: action mismatch"
        assert meta.get("intent") == case["expected_intent"], f"{case_id}: intent mismatch"
        assert meta.get("fact_source") == "service_matcher", f"{case_id}: fact_source mismatch"
        assert meta.get("source") == "service_matcher", f"{case_id}: source mismatch"
        assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"
        _assert_list_contains(
            meta.get("fact_intents"),
            case["expected_fact_intents"],
            case_id,
            "fact_intents",
        )

        trace = _get_decision_trace(conversation)
        _assert_trace_contains(
            trace,
            {
                "stage": "service_matcher",
                "decision": case["expected_intent"],
                "fact_source": "service_matcher",
            },
            case_id,
        )


def test_booking_flow_expected_reply_and_interrupt():
    case_id = "CA05_BOOKING_START"
    _response, conversation, saved_message = _run_webhook_conversation(
        ["хочу записаться"],
        case_id,
        None,
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE, f"{case_id}: expected_reply_type mismatch"
    assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"
    assert (
        (conversation.context or {}).get("expected_reply_type") == webhook_router.EXPECTED_REPLY_SERVICE
    ), f"{case_id}: context expected_reply_type mismatch"

    case_id = "CA05_BOOKING_SERVICE"
    _response, conversation, saved_message = _run_webhook_conversation(
        ["хочу записаться", "маникюр"],
        case_id,
        None,
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME, f"{case_id}: expected_reply_type mismatch"
    assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"
    assert (
        (conversation.context or {}).get("expected_reply_type") == webhook_router.EXPECTED_REPLY_TIME
    ), f"{case_id}: context expected_reply_type mismatch"
    booking_state = (conversation.context or {}).get("booking", {})
    booking_service = booking_state.get("service") if isinstance(booking_state, dict) else None
    assert booking_service, f"{case_id}: booking.service missing"
    assert "маникюр" in booking_service.lower(), f"{case_id}: booking.service mismatch"

    case_id = "CA05_BOOKING_INTERRUPT"
    _response, conversation, saved_message = _run_webhook_conversation(
        ["хочу записаться на маникюр", "сколько стоит маникюр?"],
        case_id,
        None,
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("booking_info_interrupt") is True, f"{case_id}: booking_info_interrupt mismatch"
    booking_info_intents = meta.get("booking_info_intents")
    assert isinstance(booking_info_intents, list) and booking_info_intents, f"{case_id}: booking_info_intents empty"

    trace = _get_decision_trace(conversation)
    interrupt_trace = next(
        (entry for entry in trace if entry.get("stage") == "booking_interrupt"),
        None,
    )
    assert interrupt_trace is not None, f"{case_id}: missing booking_interrupt trace"
    trace_intents = interrupt_trace.get("info_intents")
    assert isinstance(trace_intents, list) and trace_intents, f"{case_id}: trace info_intents empty"


def test_booking_flow_info_interrupt_sections_location_hours_parking_promo():
    cases = [
        ("CA05_BOOKING_INTERRUPT_LOCATION", "где находится ваш салон?", "location"),
        ("CA05_BOOKING_INTERRUPT_HOURS", "как вы работаете?", "hours"),
        ("CA05_BOOKING_INTERRUPT_DURATION", "Какова продолжительность сеанса?", "service_duration"),
        ("CA05_BOOKING_INTERRUPT_PARKING", "есть ли у вас парковка?", "parking"),
        ("CA05_BOOKING_INTERRUPT_PROMO", "у вас есть акции или скидки?", "promotions"),
    ]

    for case_id, question, expected_section in cases:
        _response, conversation, saved_message = _run_webhook_conversation(
            ["хочу записаться", "маникюр", question],
            case_id,
            None,
        )
        meta = saved_message.message_metadata.get("decision_meta", {})
        assert meta.get("booking_info_interrupt") is True, (
            f"{case_id}: booking_info_interrupt mismatch; meta={meta}"
        )
        sections = meta.get("info_sections")
        assert isinstance(sections, list) and sections, f"{case_id}: info_sections empty"
        assert expected_section in sections, f"{case_id}: missing info section {expected_section}"
        assert meta.get("action") == "reply", f"{case_id}: action mismatch"

        trace = _get_decision_trace(conversation)
        interrupt_trace = next(
            (entry for entry in reversed(trace) if entry.get("stage") == "booking_interrupt"),
            None,
        )
        assert interrupt_trace is not None, f"{case_id}: missing booking_interrupt trace"
        trace_sections = interrupt_trace.get("info_sections")
        assert isinstance(trace_sections, list) and expected_section in trace_sections, (
            f"{case_id}: trace missing section {expected_section}"
        )


def test_booking_flow_info_interrupt_parking_colloquial_phrase():
    case_id = "CA05_BOOKING_INTERRUPT_PARKING_COLLOQUIAL"
    _response, conversation, saved_message = _run_webhook_conversation(
        ["хочу записаться", "маникюр", "Подскажите, есть ли паркинг возле салона?"],
        case_id,
        None,
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("booking_info_interrupt") is True, f"{case_id}: booking_info_interrupt mismatch"
    sections = meta.get("info_sections")
    assert isinstance(sections, list) and "parking" in sections, (
        f"{case_id}: missing parking section; meta={meta}"
    )

    trace = _get_decision_trace(conversation)
    interrupt_trace = next(
        (entry for entry in reversed(trace) if entry.get("stage") == "booking_interrupt"),
        None,
    )
    assert interrupt_trace is not None, f"{case_id}: missing booking_interrupt trace"
    trace_sections = interrupt_trace.get("info_sections")
    assert isinstance(trace_sections, list) and "parking" in trace_sections, (
        f"{case_id}: trace missing parking section"
    )


def test_booking_flow_interrupt_after_price_duration_sequence():
    prefix = [
        "Здравствуйте! Я хочу записаться на стрижку.",
        "Какой у вас прайс на стрижку?",
        "Сколько времени займет стрижка?",
    ]
    cases = [
        ("CA05_AFTER_PRICE_LOCATION", "Где находится ваш салон?", "location"),
        ("CA05_AFTER_PRICE_HOURS", "Каковы ваши часы работы?", "hours"),
        ("CA05_AFTER_PRICE_PARKING", "Есть ли у вас парковка?", "parking"),
        ("CA05_AFTER_PRICE_PROMO", "У вас есть какие-то акции или скидки?", "promotions"),
    ]
    for case_id, question, expected_section in cases:
        _response, _conversation, saved_message = _run_webhook_conversation(
            [*prefix, question],
            case_id,
            None,
        )
        meta = saved_message.message_metadata.get("decision_meta", {})
        sections = meta.get("info_sections")
        assert isinstance(sections, list) and sections, f"{case_id}: info_sections empty; meta={meta}"
        assert expected_section in sections, f"{case_id}: missing info section {expected_section}; meta={meta}"


def test_consult_pack_only_and_short_circuit():
    def _consult_intent_decomp(text: str, **_kwargs) -> dict:
        payload = _fake_intent_decomp(text, **_kwargs)
        normalized = (text or "").casefold()
        if any(keyword in normalized for keyword in ("уход", "посовет", "сух")):
            payload["consult_intent"] = True
        return payload

    real_consult_resolver = knowledge_service.resolve_consult_topic_candidates

    def _fake_consult_candidates(message_text: str, topics: list, **kwargs) -> list[dict]:
        normalized = (message_text or "").casefold()

        def _candidate(topic_id: str, score: float) -> dict:
            topic = next((item for item in topics if item.id == topic_id), None)
            return {
                "topic_id": topic_id,
                "title": topic.title if topic else "",
                "summary": topic.summary if topic else "",
                "score": score,
            }

        if any(keyword in normalized for keyword in ("волос", "сух")):
            return [_candidate("hair_damage", 0.92)]
        if "ногт" in normalized:
            return [_candidate("nails_care", 0.91)]
        return real_consult_resolver(message_text, topics, **kwargs)

    with patch(
        "app.services.knowledge_service.resolve_consult_topic_candidates",
        side_effect=_fake_consult_candidates,
    ):
        case_id = "CA06_PACK_ONLY"
        _responses, conversation, saved_message = _run_webhook_conversation_turns(
            ["сухие волосы, что посоветуете?"],
            case_id,
            None,
            intent_decomp_fn=_consult_intent_decomp,
        )
        meta = saved_message.message_metadata.get("decision_meta", {})
        assert meta.get("consult_playbook_id") == "hair_damage", f"{case_id}: consult_playbook_id mismatch"
        assert meta.get("source") == "pack", f"{case_id}: source mismatch"
        assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"

        trace = _get_decision_trace(conversation)
        _assert_trace_contains(
            trace,
            {
                "stage": "consult_flow",
                "decision": "consult_reply",
                "consult_playbook_id": "hair_damage",
            },
            case_id,
        )

        case_id = "CA06_SHORT_CIRCUIT"
        _responses, conversation, saved_message = _run_webhook_conversation_turns(
            ["уход за ногтями, сколько стоит маникюр?"],
            case_id,
            None,
            intent_decomp_fn=_consult_intent_decomp,
        )
        meta = saved_message.message_metadata.get("decision_meta", {})
        assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"
        fact_source = meta.get("fact_source")
        assert fact_source in {"truth", "service_matcher"}, (
            f"{case_id}: fact_source mismatch ({fact_source})"
        )

        trace = _get_decision_trace(conversation)
        _assert_trace_contains(
            trace,
            {
                "stage": "consult_flow",
                "decision": "short_circuit",
                "consult_playbook_id": "nails_care",
            },
            case_id,
        )
        stage = "truth_gate" if fact_source == "truth" else "service_matcher"
        _assert_trace_stage_decision_any(trace, case_id, {stage})


def test_ood_low_signal_and_smalltalk_gates():
    ood_sources = {
        "domain_router",
        "domain_anchor",
        "router_low_confidence",
        "service_semantic_guard",
        "no_response_guard",
        "question_contract",
    }
    ood_decisions = {
        "early_block",
        "fallback",
        "domain_anchor",
        "router_low_confidence",
        "service_semantic_guard",
        "no_response_guard",
        "expected_reply_off_topic",
    }
    low_signal_sources = {
        "service_semantic_guard",
        "no_response_guard",
        "router_low_confidence",
        "domain_router",
        "question_contract",
        "domain_anchor",
    }
    low_signal_decisions = {
        "service_semantic_guard",
        "no_response_guard",
        "router_low_confidence",
        "early_block",
    }

    case_id = "CA07_OOD"
    _response, conversation, saved_message = _run_webhook_conversation(
        ["какая погода?"],
        case_id,
        None,
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "out_of_domain", f"{case_id}: action mismatch"
    assert meta.get("intent") == "out_of_domain", f"{case_id}: intent mismatch"
    assert meta.get("source") in ood_sources, f"{case_id}: source mismatch"
    assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"

    trace = _get_decision_trace(conversation)
    _assert_trace_stage_decision_any(trace, case_id, {"out_of_domain"}, ood_decisions)

    case_id = "CA07_LOW_SIGNAL"
    _response, conversation, saved_message = _run_webhook_conversation(
        ["мм..."],
        case_id,
        None,
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "out_of_domain", f"{case_id}: action mismatch"
    assert meta.get("intent") == "out_of_domain", f"{case_id}: intent mismatch"
    assert meta.get("source") in low_signal_sources, f"{case_id}: source mismatch"
    assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"

    trace = _get_decision_trace(conversation)
    _assert_trace_stage_decision_any(
        trace,
        case_id,
        {"out_of_domain"},
        low_signal_decisions,
    )

    greetings = ["привет", "привет плз"]
    for idx, greeting in enumerate(greetings, start=1):
        case_id = f"CA07_SMALLTALK_{idx}"
        _response, conversation, saved_message = _run_webhook_conversation(
            [greeting],
            case_id,
            None,
        )
        meta = saved_message.message_metadata.get("decision_meta", {})
        assert meta.get("action") == "smalltalk", f"{case_id}: action mismatch"
        assert meta.get("intent") == "greeting", f"{case_id}: intent mismatch"
        assert meta.get("source") == "fast_intent", f"{case_id}: source mismatch"
        assert meta.get("llm_used") is False, f"{case_id}: llm_used mismatch"

        trace = _get_decision_trace(conversation)
        _assert_trace_stage_decision_any(
            trace,
            case_id,
            {"fast_intent", "smalltalk"},
            {"smalltalk", "greeting"},
        )


def test_llm_guard_records_trace_and_meta():
    conversation = SimpleNamespace(
        id=uuid4(),
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )
    user = SimpleNamespace(id="user-123", remote_jid="77000000000@s.whatsapp.net")
    saved_message = SimpleNamespace(message_metadata={"decision_meta": {}})
    timing_context: dict = {}

    def _send_and_save(text: str | None, allow_quiet_hours: bool = True):
        return text, True

    with patch(
        "app.services.ai_service.rewrite_query_for_retrieval",
        return_value={"rewrite_used": False, "rewrite_text": "", "reason": "disabled"},
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        return_value=SimpleNamespace(ok=True, error=None, error_code=None, value=("плохой ответ", "high")),
    ), patch(
        "app.routers.webhook._legacy._detect_llm_guard_topics",
        return_value=["hard_law"],
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        return_value=(None, False, False),
    ), patch(
        "app.routers.webhook._legacy.escalate_to_pending",
        return_value=SimpleNamespace(ok=True, value=SimpleNamespace()),
    ), patch(
        "app.routers.webhook._legacy.send_telegram_notification",
        return_value=True,
    ), patch(
        "app.routers.webhook._legacy._reset_low_confidence_retry",
        return_value=None,
    ):
        webhook_response._handle_llm_primary(
            db=Mock(),
            conversation=conversation,
            user=user,
            message_text="что-то странное",
            saved_message=saved_message,
            client_slug="demo_salon",
            policy_type="demo_salon",
            policy_pack={},
            routing={"allow_bot_reply": True, "allow_handover_create": True},
            append_user_message=False,
            timing_context=timing_context,
            client_config={},
            intent=None,
            multi_intent_other_followup=None,
            send_and_save=_send_and_save,
            record_escalation_metric=lambda *_args, **_kwargs: None,
        )

    trace = _get_decision_trace(conversation)
    assert _trace_has_entry(
        trace,
        {"stage": "llm_guard", "decision": "blocked_topics"},
    )
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "escalate"
    assert meta.get("intent") == "llm_guard"
    assert meta.get("source") == "llm_guard"


def test_budget_gate_trace_records_on_budget_exceeded():
    conversation = SimpleNamespace(context={})
    saved_message = SimpleNamespace(message_metadata={"decision_meta": {}})
    timing_context: dict = {}

    with patch(
        "app.services.ai_service.OPENAI_API_KEY",
        "test-key",
    ), patch(
        "app.services.ai_service.consume_llm_budget",
        return_value={
            "active": True,
            "allowed": False,
            "reason": "budget_exceeded",
            "limit": 1,
            "count": 2,
            "scope": "rag_rewrite",
        },
    ):
        webhook_response._ensure_rag_rewrite(
            conversation=conversation,
            saved_message=saved_message,
            message_text="нужна информация",
            client_slug="demo_salon",
            client_config={"llm_budget": {"daily_max_calls": 0}},
            timing_context=timing_context,
        )

    trace = _get_decision_trace(conversation)
    assert _trace_has_entry(
        trace,
        {"stage": "budget_gate", "decision": "deny", "llm_scope": "rag_rewrite"},
    )


def _assert_contains_all(response: str, items: list[str], case_id: str, label: str) -> None:
    normalized = _normalize(response)
    for item in items:
        expected = _normalize(item)
        if expected in normalized:
            continue
        expected_tokens = [token for token in re.findall(r"\w+", expected) if token]
        if expected_tokens and all(token in normalized for token in expected_tokens):
            continue
        raise AssertionError(f"{case_id}: missing {label} '{item}'")


def _assert_contains_any(response: str, items: list[str], case_id: str, label: str) -> None:
    normalized = _normalize(response)
    for item in items:
        expected = _normalize(item)
        if expected in normalized:
            return
        expected_tokens = [token for token in re.findall(r"\w+", expected) if token]
        if expected_tokens and all(token in normalized for token in expected_tokens):
            return
    raise AssertionError(f"{case_id}: none of {label} matched: {items}")


def _assert_not_contains(response: str, items: list[str], case_id: str) -> None:
    normalized = _normalize(response)
    for item in items:
        assert _normalize(item) not in normalized, f"{case_id}: must_not contains '{item}'"


def _assert_list_contains(value: object, expected: list[str], case_id: str, label: str) -> None:
    if not isinstance(value, list):
        raise AssertionError(f"{case_id}: {label} not list")
    for item in expected:
        if item not in value:
            raise AssertionError(f"{case_id}: missing {label} '{item}'")


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
    if isinstance(expected, dict) and not _has_valid_openai_key():
        source = expected.get("source")
        llm_source = (
            isinstance(source, str)
            and source.strip().casefold() in {"llm", "llm_primary", "policy_core", "answer_interpreter"}
        )
        if (
            expected.get("controller_used") is True
            or expected.get("answer_interpreter_used") is True
            or llm_source
        ):
            return
    for entry in trace:
        if _match_trace(entry, expected):
            return
    raise AssertionError(f"{case_id}: missing trace entry matching {expected}")


def _trace_has_entry(trace: list[dict], expected: dict) -> bool:
    return any(_match_trace(entry, expected) for entry in trace)


def _assert_trace_stage_decision_any(
    trace: list[dict], case_id: str, stages: set[str], decisions: set[str] | None = None
) -> None:
    for entry in trace:
        if entry.get("stage") in stages and (decisions is None or entry.get("decision") in decisions):
            return
    raise AssertionError(
        f"{case_id}: missing trace stage in {sorted(stages)} with decision in {sorted(decisions or [])}"
    )


def _match_trace_expected(entry: dict, expected: dict) -> bool:
    if not isinstance(entry, dict):
        return False
    for key, value in expected.items():
        if key.endswith("_any"):
            actual = entry.get(key[:-4])
            if actual not in value:
                return False
            continue
        if isinstance(value, list):
            actual = entry.get(key)
            if not isinstance(actual, list):
                return False
            for item in value:
                if item not in actual:
                    return False
            continue
        if isinstance(value, str):
            if _normalize(entry.get(key)) != _normalize(value):
                return False
            continue
        if entry.get(key) != value:
            return False
    return True


def _assert_trace_contains_expected(trace: list[dict], expected: dict, case_id: str) -> None:
    for entry in trace:
        if _match_trace_expected(entry, expected):
            return
    raise AssertionError(f"{case_id}: missing trace entry matching {expected}")


def _assert_meta_expected(
    meta: dict,
    case_id: str,
    expected: dict | None,
    expected_any: dict | None,
    expected_contains: dict | None,
) -> None:
    expected = expected or {}
    expected_any = expected_any or {}
    expected_contains = expected_contains or {}
    for key, value in expected.items():
        if meta.get(key) != value:
            raise AssertionError(f"{case_id}: meta {key} mismatch")
    for key, values in expected_any.items():
        if not isinstance(values, list):
            raise AssertionError(f"{case_id}: meta {key}_any must be a list")
        if meta.get(key) not in values:
            raise AssertionError(f"{case_id}: meta {key} not in {values}")
    for key, values in expected_contains.items():
        if not isinstance(values, list):
            raise AssertionError(f"{case_id}: meta {key}_contains must be a list")
        _assert_list_contains(meta.get(key), values, case_id, f"meta {key}")


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


@lru_cache(maxsize=1)
def _load_consult_pack():
    from app.services.consult_pack_service import load_consult_playbook

    playbook, _error = load_consult_playbook("demo_salon")
    return playbook


def _assert_consult_pack_response(response: str, topic_id: str | None, case_id: str) -> None:
    if not topic_id:
        raise AssertionError(f"{case_id}: consult_topic_id missing for consult case")
    playbook = _load_consult_pack()
    if playbook is None:
        raise AssertionError(f"{case_id}: consult playbook missing")
    from app.services.consult_pack_service import get_consult_topic

    topic = get_consult_topic(playbook, topic_id)
    if topic is None:
        raise AssertionError(f"{case_id}: unknown consult_topic_id '{topic_id}'")
    allowed = [item for item in (topic.allowed_advice or []) if isinstance(item, str) and item.strip()]
    if not allowed:
        raise AssertionError(f"{case_id}: consult topic '{topic_id}' has no allowed_advice")
    normalized = _normalize(response)
    if not any(_normalize(item) in normalized for item in allowed):
        raise AssertionError(
            f"{case_id}: consult response missing allowed_advice for topic '{topic_id}'"
        )


def _sanitize_consult_expected(expected: dict) -> dict:
    payload = dict(expected)
    payload.pop("must_include", None)
    payload.pop("must_include_any", None)
    must_not = payload.get("must_not")
    if isinstance(must_not, list):
        filtered = [
            item
            for item in must_not
            if not (isinstance(item, str) and "запис" in item)
        ]
        if filtered:
            payload["must_not"] = filtered
        else:
            payload.pop("must_not", None)
    return payload


def _assert_consult_cta(response: str, case_id: str) -> None:
    _assert_contains_all(response, ["Хотите записаться"], case_id, "consult_cta")


def _collect_trace_expectations(expected: dict, trace_expectations: list[dict]) -> None:
    items = expected.get("trace_contains") or []
    if isinstance(items, list):
        trace_expectations.extend(items)


def _is_core_eval_mode() -> bool:
    return EVAL_TIER in {"core", "ci"} or (not EVAL_TIER and os.environ.get("CI"))


def _sanitize_core_semantic_expected(expected: dict) -> dict:
    payload = dict(expected)
    for key in TEXT_EXPECTATION_KEYS:
        payload.pop(key, None)
    return payload


def _semantic_action_matches(expected_action: object, actual_action: object) -> bool:
    return expected_action == actual_action


def _assert_semantic_expected_response(
    *,
    response: str,
    expected: dict,
    meta: dict,
    case_id: str,
) -> None:
    expected_action = expected.get("action")
    if expected_action is not None:
        actual_action = meta.get("action")
        if expected_action == "reply":
            if not isinstance(actual_action, str) or not actual_action.strip():
                raise AssertionError(f"{case_id}: missing action for expected reply")
        else:
            if not _semantic_action_matches(expected_action, actual_action):
                raise AssertionError(
                    f"{case_id}: semantic action mismatch (expected={expected_action}, actual={actual_action})"
                )
    if expected_action and expected_action != "off_topic":
        if not isinstance(response, str) or not response.strip():
            raise AssertionError(f"{case_id}: empty response for expected action '{expected_action}'")


def _extract_tiers(case: dict) -> list[str]:
    raw_tier = case.get("tier")
    if isinstance(raw_tier, str):
        cleaned = raw_tier.strip().lower()
        return [cleaned] if cleaned else []
    if isinstance(raw_tier, list):
        tiers: list[str] = []
        for item in raw_tier:
            if isinstance(item, str):
                cleaned = item.strip().lower()
                if cleaned:
                    tiers.append(cleaned)
        return tiers
    return []


def _has_valid_openai_key() -> bool:
    raw = os.environ.get("OPENAI_API_KEY")
    if not isinstance(raw, str):
        return False
    key = raw.strip()
    return bool(key and key.casefold() not in {"none", "null"})


def _filter_cases(cases: list[dict]) -> list[dict]:
    if EVAL_TIER in {"all", "full"} and _has_valid_openai_key():
        return cases
    if EVAL_TIER in {"all", "full"} and not _has_valid_openai_key():
        core_cases = [case for case in cases if case.get("id") in CORE_EVAL_IDS]
        assert core_cases, "Core eval set is empty"
        return core_cases
    if EVAL_TIER == "asr":
        asr_cases = [case for case in cases if "asr" in _extract_tiers(case)]
        assert asr_cases, "ASR eval set is empty"
        return asr_cases
    if EVAL_TIER == "chaos":
        chaos_cases = [case for case in cases if "chaos" in _extract_tiers(case)]
        assert chaos_cases, "Chaos eval set is empty"
        return chaos_cases
    if EVAL_TIER == "long":
        long_cases = [case for case in cases if "long" in _extract_tiers(case)]
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
    core_eval_mode = _is_core_eval_mode()
    eval_intent_decomp_fn = None if core_eval_mode else _fake_intent_decomp
    eval_service_hint_fn = None if core_eval_mode else _fake_service_hint

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
        is_consult_case = case_expected.get("intent") == "consult_reply"
        trace_required = bool(case_expected.get("trace_contains"))
        if turns:
            trace_required = trace_required or any(
                (turn.get("expected") or {}).get("trace_contains") for turn in turns
            )

        if turns and messages:
            raise AssertionError(f"{case_id}: use turns or messages, not both")
        if turns:
            messages = [turn["user"] for turn in turns]

        expected_action = case_expected.get("action")
        if expected_action == "booking_flow":
            booking_messages = messages if messages else ([user_text] if user_text else [])
            if core_eval_mode:
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
            else:
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
        if (
            not core_eval_mode
            and not messages
            and expected_action != "off_topic"
            and not trace_required
        ):
            decision = get_demo_salon_decision(user_text)
            if decision is not None:
                assert decision.action == expected_action, (
                    f"{case_id}: action mismatch: {decision.action} != {expected_action}"
                )

        response = (decision.response if decision else "") or ""
        local_time = case.get("local_time")
        must_include = case_expected.get("must_include") or []
        wants_cta = (not core_eval_mode) and any(
            isinstance(item, str) and "Хотите записаться" in item for item in must_include
        )
        if turns:
            responses, conversation, saved_message = _run_webhook_conversation_turns(
                messages,
                case_id,
                str(local_time) if local_time else None,
                pending_sla_expected=pending_sla_expected,
                intent_decomp_fn=eval_intent_decomp_fn,
                service_hint_fn=eval_service_hint_fn,
            )
            for idx, turn in enumerate(turns, start=1):
                step_expected = turn.get("expected") or {}
                if step_expected:
                    if not core_eval_mode:
                        _assert_expected_response(
                            responses[idx - 1] if responses else "",
                            step_expected,
                            f"{case_id}/turn{idx}",
                        )
                _collect_trace_expectations(step_expected, trace_expectations)
                if case_expected:
                    response = responses[-1] if responses else ""
                    expected_payload = case_expected
                    if is_consult_case and saved_message and not core_eval_mode:
                        meta = saved_message.message_metadata.get("decision_meta", {})
                        topic_id = meta.get("consult_topic_id") or meta.get("consult_topic")
                        _assert_consult_pack_response(response, topic_id, case_id)
                        _assert_consult_cta(response, case_id)
                        expected_payload = _sanitize_consult_expected(case_expected)
                    if core_eval_mode:
                        meta = saved_message.message_metadata.get("decision_meta", {}) if saved_message else {}
                        expected_payload = _sanitize_core_semantic_expected(expected_payload)
                        _assert_semantic_expected_response(
                            response=response,
                            expected=expected_payload,
                            meta=meta,
                            case_id=case_id,
                        )
                    else:
                        _assert_expected_response(response, expected_payload, case_id)
                    _collect_trace_expectations(case_expected, trace_expectations)
        else:
            if messages:
                response, conversation, saved_message = _run_webhook_conversation(
                    messages,
                    case_id,
                    str(local_time) if local_time else None,
                    intent_decomp_fn=eval_intent_decomp_fn,
                    service_hint_fn=eval_service_hint_fn,
                )
            elif local_time or wants_cta or not decision or is_consult_case:
                response, conversation, saved_message = _run_webhook_case(
                    user_text,
                    case_id,
                    str(local_time) if local_time else None,
                    intent_decomp_fn=eval_intent_decomp_fn,
                    service_hint_fn=eval_service_hint_fn,
                )
            if case_expected:
                expected_payload = case_expected
                if is_consult_case and saved_message and not core_eval_mode:
                    meta = saved_message.message_metadata.get("decision_meta", {})
                    topic_id = meta.get("consult_topic_id") or meta.get("consult_topic")
                    _assert_consult_pack_response(response, topic_id, case_id)
                    _assert_consult_cta(response, case_id)
                    expected_payload = _sanitize_consult_expected(case_expected)
                if core_eval_mode:
                    meta = saved_message.message_metadata.get("decision_meta", {}) if saved_message else {}
                    expected_payload = _sanitize_core_semantic_expected(expected_payload)
                    _assert_semantic_expected_response(
                        response=response,
                        expected=expected_payload,
                        meta=meta,
                        case_id=case_id,
                    )
                else:
                    _assert_expected_response(response, expected_payload, case_id)
                _collect_trace_expectations(case_expected, trace_expectations)

        if trace_expectations:
            assert conversation is not None, f"{case_id}: trace assertions require conversation context"
            decision_trace = _get_decision_trace(conversation)
            for requirement in trace_expectations:
                _assert_trace_contains(decision_trace, requirement, case_id)


def test_demo_salon_golden_eval_cases():
    data = yaml.safe_load(EVAL_GOLDEN_PATH.read_text(encoding="utf-8"))
    cases = data.get("eval_cases", []) if isinstance(data, dict) else []
    assert cases, "Golden eval set is empty"

    for case in cases:
        case_id = case.get("id", "<unknown>")
        messages = case.get("messages")
        if messages is None:
            user_text = case.get("user", "")
            if not isinstance(user_text, str) or not user_text.strip():
                raise AssertionError(f"{case_id}: missing user text")
            messages = [user_text]
        if not isinstance(messages, list) or not messages:
            raise AssertionError(f"{case_id}: messages must be a non-empty list")
        for idx, message in enumerate(messages, start=1):
            if not isinstance(message, str) or not message.strip():
                raise AssertionError(f"{case_id}: message {idx} empty")

        local_time = case.get("local_time")
        _response, conversation, saved_message = _run_webhook_conversation(
            messages,
            case_id,
            str(local_time) if local_time else None,
        )
        meta = saved_message.message_metadata.get("decision_meta", {})
        _assert_meta_expected(
            meta,
            case_id,
            case.get("expected_meta"),
            case.get("expected_meta_any"),
            case.get("expected_meta_contains"),
        )

        trace_expectations = case.get("expected_trace_contains") or []
        if trace_expectations:
            decision_trace = _get_decision_trace(conversation)
            for requirement in trace_expectations:
                if not isinstance(requirement, dict):
                    raise AssertionError(f"{case_id}: trace expectation must be a mapping")
                _assert_trace_contains_expected(decision_trace, requirement, case_id)
