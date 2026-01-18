#!/usr/bin/env python3
"""
БЫСТРАЯ ДИАГНОСТИКА
Запуск: python3 ~/truffles-main/ops/diagnose.py

Показывает:
- Состояние conversations
- Состояние handovers
"""
import argparse
import base64
import glob
import json
import os
import random
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone

LIVECHECK_SUITES = {
    "ca01-core": [
        {
            "case_id": "CA01_REFUND",
            "expected_policy_section": "refund",
            "messages": [
                "хочу вернуть деньги за услугу",
                "верните оплату пожалуйста",
                "нужен возврат денег",
            ],
        },
        {
            "case_id": "CA01_PAYMENT",
            "expected_policy_section": "payment_info",
            "messages": [
                "можно оплатить картой?",
                "есть оплата каспи?",
                "можно оплатить переводом?",
            ],
        },
        {
            "case_id": "CA01_RESCHEDULE",
            "expected_policy_section": "reschedule",
            "messages": [
                "перенесите запись на завтра",
                "поменять дату записи",
                "переписать на другой день",
            ],
        },
        {
            "case_id": "CA01_MEDICAL",
            "expected_policy_section": "medical",
            "messages": [
                "у меня аллергия на гель-лак",
                "жжет после окрашивания",
                "можно беременным на процедуру?",
            ],
        },
    ],
    "ca01-extended": [
        {
            "case_id": "CA01_CANCEL",
            "expected_policy_section": "cancel",
            "messages": [
                "отмените запись пожалуйста",
                "я не приду, отмените",
            ],
        },
        {
            "case_id": "CA01_LEGAL",
            "expected_policy_section": "legal",
            "messages": [
                "хочу договор и оферту",
                "у меня юридическая претензия",
            ],
        },
        {
            "case_id": "CA01_COMPLAINT",
            "expected_policy_section": "complaint",
            "messages": [
                "жалоба: плохо сделали",
                "недоволен качеством услуги",
            ],
        },
    ],
    "ca02-policy": [
        {
            "case_id": "CA02_DISCOUNT",
            "expected_policy_section": "discounts",
            "messages": [
                "есть скидка на услуги?",
                "можно скидку?",
                "какие акции сейчас есть?",
            ],
        },
        {
            "case_id": "CA02_PAYMENT",
            "expected_policy_section": "payment_info",
            "messages": [
                "можно оплатить картой?",
                "есть оплата каспи?",
                "можно оплатить переводом?",
            ],
        },
    ],
    "ca03-info": [
        {
            "case_id": "CA03_ADDRESS_HOURS",
            "expected_info_sections": ["address", "hours"],
            "expected_fact_intents": ["location", "hours"],
            "expected_info_combined": True,
            "messages": [
                "где вы и когда работаете?",
                "где находитесь и во сколько открыты?",
            ],
        },
        {
            "case_id": "CA03_GUEST_POLICY",
            "expected_info_sections": ["guest_policy"],
            "expected_fact_intents": ["guest_policy"],
            "messages": [
                "можно с ребенком?",
                "детям можно приходить?",
            ],
        },
    ],
    "ca04-service": [
        {
            "case_id": "CA04_SERVICE_MATCH",
            "expected_intent": "service_match",
            "expected_fact_intents": ["service_match"],
            "messages": [
                "делаете маникюр?",
                "маникюр делаете?",
            ],
        },
        {
            "case_id": "CA04_SERVICE_NOT_FOUND",
            "expected_intent": "service_not_found",
            "expected_fact_intents": ["service_not_found"],
            "messages": [
                "делаете массаж?",
                "делаете стрижку?",
            ],
        },
    ],
    "ca05-booking": [
        {
            "case_id": "CA05_BOOKING_FLOW",
            "expected_policy_section": None,
            "messages": [
                "хочу записаться",
                "маникюр",
                "сколько стоит маникюр?",
            ],
            "steps": [
                {
                    "message": "хочу записаться",
                    "expect_expected_reply_type": "service_choice",
                    "expect_llm_used": False,
                },
                {
                    "message": "маникюр",
                    "expect_expected_reply_type": "time",
                    "expect_booking_service": "маникюр",
                    "expect_llm_used": False,
                },
                {
                    "message": "сколько стоит маникюр?",
                    "expect_booking_interrupt": True,
                },
            ],
        }
    ],
    "ca06-consult": [
        {
            "case_id": "CA06_PACK_ONLY",
            "expected_consult_playbook_id": "hair_damage",
            "expected_meta_consult_playbook_id": "hair_damage",
            "expected_consult_decision": "consult_reply",
            "expected_source": "pack",
            "expected_llm_used": False,
            "messages": [
                "сухие волосы, что посоветуете?",
            ],
        },
        {
            "case_id": "CA06_SHORT_CIRCUIT",
            "expected_consult_playbook_id": "nails_care",
            "expected_consult_decision": "short_circuit",
            "expected_fact_source_any": ["truth", "service_matcher"],
            "expected_llm_used": False,
            "messages": [
                "уход за ногтями, сколько стоит маникюр?",
            ],
        },
    ],
    "ca07-ood": [
        {
            "case_id": "CA07_OOD",
            "expected_action": "out_of_domain",
            "expected_intent": "out_of_domain",
            "expected_source_any": [
                "domain_router",
                "domain_anchor",
                "router_low_confidence",
                "service_semantic_guard",
                "no_response_guard",
                "question_contract",
            ],
            "expected_trace_stage_any": ["out_of_domain"],
            "expected_trace_decision_any": [
                "early_block",
                "domain_anchor",
                "router_low_confidence",
                "service_semantic_guard",
                "no_response_guard",
                "expected_reply_off_topic",
            ],
            "expected_llm_used": False,
            "messages": [
                "какая погода?",
            ],
        },
        {
            "case_id": "CA07_LOW_SIGNAL",
            "expected_action": "out_of_domain",
            "expected_intent": "out_of_domain",
            "expected_source_any": ["service_semantic_guard", "no_response_guard", "router_low_confidence"],
            "expected_trace_stage_any": ["out_of_domain"],
            "expected_trace_decision_any": ["service_semantic_guard", "no_response_guard", "router_low_confidence"],
            "expected_llm_used": False,
            "messages": [
                "мм...",
            ],
        },
        {
            "case_id": "CA07_SMALLTALK",
            "expected_action": "smalltalk",
            "expected_intent": "greeting",
            "expected_source_any": ["fast_intent"],
            "expected_trace_stage_any": ["fast_intent", "smalltalk"],
            "expected_trace_decision_any": ["smalltalk", "greeting"],
            "expected_llm_used": False,
            "messages": [
                "привет",
            ],
        },
    ],
    "ca08-state": [
        {
            "case_id": "CA08_PENDING",
            "expected_policy_section": "refund",
            "messages": [
                "верните оплату пожалуйста",
                "хочу вернуть деньги",
            ],
        }
    ],
    "ca09-manager": [
        {
            "case_id": "CA09_MANAGER",
            "expected_policy_section": "payment_info",
            "messages": [
                "можно оплатить картой?",
                "есть оплата каспи?",
            ],
        }
    ],
    "ca10-outbox": [
        {
            "case_id": "CA10_DEDUP",
            "expected_policy_section": "reschedule",
            "messages": [
                "перенесите запись на завтра",
                "поменять дату записи",
            ],
        }
    ],
}

WEBHOOK_FUZZ_CASES = [
    {
        "case_id": "LAW_REFUND",
        "expected_policy_section": "refund",
        "messages": [
            "хочу вернуть деньги за услугу",
            "нужен возврат денег",
        ],
    },
    {
        "case_id": "LAW_PAYMENT",
        "expected_policy_section": "payment_info",
        "messages": [
            "можно оплатить картой?",
            "есть оплата каспи?",
        ],
    },
    {
        "case_id": "LAW_RESCHEDULE",
        "expected_policy_section": "reschedule",
        "messages": [
            "перенесите запись на завтра",
            "поменять дату записи",
        ],
    },
    {
        "case_id": "LAW_MEDICAL",
        "expected_policy_section": "medical",
        "messages": [
            "у меня аллергия на гель-лак",
            "жжет после окрашивания",
        ],
    },
    {
        "case_id": "LAW_LEGAL",
        "expected_policy_section": "legal",
        "messages": [
            "хочу договор и оферту",
            "у меня юридическая претензия",
        ],
    },
    {
        "case_id": "LAW_COMPLAINT",
        "expected_policy_section": "complaint",
        "messages": [
            "жалоба: плохо сделали",
            "недоволен качеством услуги",
        ],
    },
    {
        "case_id": "INFO_HOURS",
        "expected_policy_section": None,
        "messages": [
            "до скольки работаете?",
            "какой график работы?",
        ],
    },
    {
        "case_id": "INFO_LOCATION",
        "expected_policy_section": None,
        "messages": [
            "где вы находитесь?",
            "как до вас добраться?",
        ],
    },
    {
        "case_id": "INFO_PRICE",
        "expected_policy_section": None,
        "messages": [
            "сколько стоит маникюр?",
            "какая цена на стрижку?",
        ],
    },
    {
        "case_id": "BOOK_TIME",
        "expected_policy_section": None,
        "messages": [
            "хочу записаться на завтра вечером",
            "запишите на понедельник",
        ],
    },
    {
        "case_id": "CONSULT_AFTERCOLOR",
        "expected_policy_section": None,
        "messages": [
            "посоветуйте уход после окрашивания",
            "как ухаживать после окраски?",
        ],
    },
]

NOISE_SUFFIXES = ["плз", "срочно", "спс"]
PENDING_ACK_PHRASES = ["ок", "да", "жду", "ага", "можно"]
SAFE_ALLOWLIST_JID = "77015705555@s.whatsapp.net"
SAFE_ALLOWLIST_CLIENT_SLUG = "demo_salon"

def _parse_livecheck_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py livecheck",
        description="Run live-check runner via ChatFlow send-text.",
    )
    parser.add_argument("--suite", default="ca01-core", choices=sorted(LIVECHECK_SUITES.keys()))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--min-wait", type=float, default=5.0)
    parser.add_argument("--max-wait", type=float, default=15.0)
    parser.add_argument("--noise", choices=["none", "low"], default="low")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)

def _parse_livecheck_auto_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py livecheck-auto",
        description="Run webhook live-check with auto-ACK and DB polling.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TRUFFLES_API_BASE_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--client-slug",
        default=os.environ.get("TRUFFLES_CLIENT_SLUG", "demo_salon"),
    )
    parser.add_argument("--suite", default="ca01-core", choices=sorted(LIVECHECK_SUITES.keys()))
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--min-wait", type=float, default=1.0)
    parser.add_argument("--max-wait", type=float, default=3.0)
    parser.add_argument("--noise", choices=["none", "low"], default="low")
    parser.add_argument("--case-ids", default=None)
    parser.add_argument("--jid-mode", choices=["unique", "allowlist"], default="allowlist")
    parser.add_argument("--remote-jid", default=None)
    parser.add_argument("--allowlist-jids", default=None)
    parser.add_argument("--webhook-secret", default=None)
    parser.add_argument("--admin-token", default=None)
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--ack-text", default="ок")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--poll-timeout", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)

def _apply_noise(text, rng, level):
    if level == "none":
        return text
    suffix = rng.choice(NOISE_SUFFIXES)
    return f"{text} {suffix}"

def _send_chatflow_message(api_url, token, instance_id, jid, message, timeout):
    params = {
        "token": token,
        "instance_id": instance_id,
        "jid": jid,
        "msg": message,
    }
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"{api_url}?{query}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body

def _parse_webhook_fuzz_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py webhook-fuzz",
        description="Send webhook fuzz batch directly to /webhook/{client_slug}.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("TRUFFLES_API_BASE_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--client-slug",
        default=os.environ.get("TRUFFLES_CLIENT_SLUG", "demo_salon"),
    )
    parser.add_argument("--mode", choices=["logic", "state"], default="logic")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--min-wait", type=float, default=0.5)
    parser.add_argument("--max-wait", type=float, default=2.0)
    parser.add_argument("--noise", choices=["none", "low"], default="low")
    parser.add_argument("--case-ids", default=None)
    parser.add_argument("--allowlist-jids", default=None)
    parser.add_argument("--remote-jid", default=None)
    parser.add_argument("--instance-id", default=None)
    parser.add_argument("--webhook-secret", default=None)
    parser.add_argument("--admin-token", default=None)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--skip-outbox", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)

def _pick_fuzz_cases(cases, count, rng):
    if count <= 0:
        return []
    shuffled = list(cases)
    rng.shuffle(shuffled)
    if count <= len(shuffled):
        return shuffled[:count]
    selected = list(shuffled)
    while len(selected) < count:
        selected.append(rng.choice(cases))
    return selected

def _parse_csv_values(value):
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]

def _resolve_allowlist_jids(explicit, container_name):
    for value in (
        explicit,
        os.environ.get("FUZZ_ALLOWLIST_JIDS"),
        os.environ.get("OUTBOUND_ALLOWLIST_JIDS"),
        os.environ.get("CHATFLOW_JID"),
    ):
        jids = _parse_csv_values(value)
        if jids:
            return jids
    if container_name:
        for env_name in ("OUTBOUND_ALLOWLIST_JIDS", "CHATFLOW_JID"):
            jids = _parse_csv_values(_resolve_env_from_container(container_name, env_name))
            if jids:
                return jids
    return []

def _select_allowlist_jid(allowlist_jids, suite_name, seed):
    if not allowlist_jids:
        return None
    if len(allowlist_jids) == 1:
        return allowlist_jids[0]
    seed_value = f"{suite_name}:{seed or 0}"
    digest = uuid.uuid5(uuid.NAMESPACE_DNS, seed_value).int
    idx = digest % len(allowlist_jids)
    return allowlist_jids[idx]

def _select_cases(cases, case_ids):
    if not case_ids:
        return None, []
    requested = _parse_csv_values(case_ids)
    case_map = {case["case_id"]: case for case in cases}
    missing = [case_id for case_id in requested if case_id not in case_map]
    if missing:
        raise SystemExit(f"webhook-fuzz: unknown case_ids: {', '.join(missing)}")
    return [case_map[case_id] for case_id in requested], requested

def _resolve_test_mode(container_name):
    value = os.environ.get("TEST_MODE")
    if (value is None or value == "") and container_name:
        value = _resolve_env_from_container(container_name, "TEST_MODE")
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

def _resolve_db_user_simple():
    env_user = os.environ.get("DB_USER")
    if env_user:
        return env_user
    result = run_command(
        ["docker", "exec", "-i", "truffles_postgres_1", "/bin/sh", "-lc", "printf '%s' \"${POSTGRES_USER:-}\""]
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return "postgres"

def _escape_sql_literal(value):
    return str(value).replace("'", "''")

def _resolve_webhook_secret(client_slug, explicit):
    if explicit:
        return explicit
    for env_name in ("WEBHOOK_SECRET", "TRUFFLES_WEBHOOK_SECRET"):
        env_value = os.environ.get(env_name)
        if env_value:
            return env_value
    if not client_slug:
        return None
    db_user = _resolve_db_user_simple()
    safe_slug = _escape_sql_literal(client_slug)
    query = (
        "SELECT cs.webhook_secret "
        "FROM client_settings cs "
        "JOIN clients c ON c.id = cs.client_id "
        f"WHERE c.name = '{safe_slug}' LIMIT 1;"
    )
    result = run_command(
        [
            "docker",
            "exec",
            "-i",
            "truffles_postgres_1",
            "psql",
            "-U",
            db_user,
            "-d",
            "chatbot",
            "-t",
            "-A",
            "-c",
            query,
        ]
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None

def _run_psql_query(db_user, query):
    result = run_command(
        [
            "docker",
            "exec",
            "-i",
            "truffles_postgres_1",
            "psql",
            "-U",
            db_user,
            "-d",
            "chatbot",
            "-t",
            "-A",
            "-F",
            "\t",
            "-c",
            query,
        ]
    )
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout.strip(), None

def _fetch_client_meta(db_user, client_slug):
    safe_slug = _escape_sql_literal(client_slug)
    query = (
        "SELECT c.id, c.config->>'instance_id', b.id, b.instance_id, "
        "cs.telegram_chat_id, cs.owner_telegram_id "
        "FROM clients c "
        "LEFT JOIN branches b ON b.client_id = c.id AND b.is_active = TRUE "
        "LEFT JOIN client_settings cs ON cs.client_id = c.id "
        f"WHERE c.name = '{safe_slug}' "
        "ORDER BY b.created_at DESC NULLS LAST "
        "LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    parts = row.split("\t")
    return {
        "client_id": parts[0] if len(parts) > 0 else None,
        "client_instance_id": parts[1] if len(parts) > 1 and parts[1] else None,
        "branch_id": parts[2] if len(parts) > 2 else None,
        "branch_instance_id": parts[3] if len(parts) > 3 and parts[3] else None,
        "telegram_chat_id": parts[4] if len(parts) > 4 and parts[4] else None,
        "owner_telegram_id": parts[5] if len(parts) > 5 and parts[5] else None,
    }, None

def _fetch_conversation_meta(db_user, conversation_id):
    safe_id = _escape_sql_literal(conversation_id)
    query = (
        "SELECT state, telegram_topic_id, context::text "
        f"FROM conversations WHERE id = '{safe_id}' LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    parts = row.split("\t", 2)
    state = parts[0] if len(parts) > 0 else None
    topic_raw = parts[1] if len(parts) > 1 else None
    context_raw = parts[2] if len(parts) > 2 else None
    topic_id = None
    if topic_raw:
        try:
            topic_id = int(topic_raw)
        except ValueError:
            topic_id = None
    context = None
    if context_raw:
        try:
            context = json.loads(context_raw)
        except Exception:
            context = None
    return {
        "state": state,
        "telegram_topic_id": topic_id,
        "context": context,
    }, None

def _fetch_latest_conversation_state(db_user, client_id, remote_jid):
    if not client_id or not remote_jid:
        return None, None, "missing client_id or remote_jid"
    safe_client = _escape_sql_literal(client_id)
    safe_jid = _escape_sql_literal(remote_jid)
    query = (
        "SELECT c.id, c.state "
        "FROM conversations c "
        "JOIN users u ON u.id = c.user_id "
        f"WHERE c.client_id = '{safe_client}' AND u.remote_jid = '{safe_jid}' "
        "ORDER BY c.last_message_at DESC NULLS LAST, c.started_at DESC "
        "LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, None, error
    if not row:
        return None, None, None
    parts = row.split("\t", 1)
    return parts[0] if parts else None, parts[1] if len(parts) > 1 else None, None

def _fetch_handover_meta(db_user, conversation_id):
    safe_id = _escape_sql_literal(conversation_id)
    query = (
        "SELECT id, status, assigned_to, assigned_to_name, first_response_at, "
        "manager_response, resolved_at, added_to_knowledge, knowledge_doc_id "
        f"FROM handovers WHERE conversation_id = '{safe_id}' "
        "ORDER BY created_at DESC LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    parts = row.split("\t", 8)
    return {
        "handover_id": parts[0] if len(parts) > 0 else None,
        "status": parts[1] if len(parts) > 1 else None,
        "assigned_to": parts[2] if len(parts) > 2 and parts[2] else None,
        "assigned_to_name": parts[3] if len(parts) > 3 and parts[3] else None,
        "first_response_at": parts[4] if len(parts) > 4 and parts[4] else None,
        "manager_response": parts[5] if len(parts) > 5 and parts[5] else None,
        "resolved_at": parts[6] if len(parts) > 6 and parts[6] else None,
        "added_to_knowledge": parts[7] if len(parts) > 7 and parts[7] else None,
        "knowledge_doc_id": parts[8] if len(parts) > 8 and parts[8] else None,
    }, None

def _fetch_message_count(db_user, message_id):
    safe_id = _escape_sql_literal(message_id)
    query = f"SELECT COUNT(*) FROM messages WHERE metadata->>'messageId' = '{safe_id}';"
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return 0, None
    try:
        return int(row.strip()), None
    except ValueError:
        return None, None

def _fetch_message_dedup_count(db_user, client_id, message_id):
    safe_client = _escape_sql_literal(client_id)
    safe_id = _escape_sql_literal(message_id)
    query = (
        "SELECT COUNT(*) FROM message_dedup "
        f"WHERE client_id = '{safe_client}' AND message_id = '{safe_id}';"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return 0, None
    try:
        return int(row.strip()), None
    except ValueError:
        return None, None

def _fetch_outbox_summary(db_user, client_id, inbound_message_id):
    safe_client = _escape_sql_literal(client_id)
    safe_id = _escape_sql_literal(inbound_message_id)
    query = (
        "SELECT COUNT(*), MAX(status) "
        "FROM outbox_messages "
        f"WHERE client_id = '{safe_client}' AND inbound_message_id = '{safe_id}';"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return {"count": 0, "status": None}, None
    parts = row.split("\t", 1)
    count = None
    try:
        count = int(parts[0]) if parts and parts[0] else 0
    except ValueError:
        count = None
    status = parts[1] if len(parts) > 1 and parts[1] else None
    return {"count": count, "status": status}, None

def _fetch_latest_outbox_for_conversation(db_user, conversation_id):
    safe_id = _escape_sql_literal(conversation_id)
    query = (
        "SELECT inbound_message_id, status, payload_json::text "
        f"FROM outbox_messages WHERE conversation_id = '{safe_id}' "
        "ORDER BY created_at DESC LIMIT 1;"
    )
    row, error = _run_psql_query(db_user, query)
    if error:
        return None, error
    if not row:
        return None, None
    parts = row.split("\t", 2)
    payload = None
    if len(parts) > 2 and parts[2]:
        try:
            payload = json.loads(parts[2])
        except Exception:
            payload = None
    return {
        "inbound_message_id": parts[0] if len(parts) > 0 else None,
        "status": parts[1] if len(parts) > 1 else None,
        "payload_json": payload,
    }, None

def _parse_owner_identity(raw_value):
    if not raw_value:
        return None, None
    tokens = [token for token in re.split(r"[\\s,]+", raw_value.strip()) if token]
    for token in tokens:
        cleaned = token.strip().lstrip("@")
        if not cleaned:
            continue
        if cleaned.lstrip("-").isdigit():
            try:
                return int(cleaned), None
            except ValueError:
                continue
        return None, cleaned
    return None, None

def _resolve_learning_env(container_name):
    learning_mode = os.environ.get("LEARNING_MODE") or ""
    qdrant_collection = os.environ.get("QDRANT_COLLECTION") or ""
    if container_name:
        learning_mode = _resolve_env_from_container(container_name, "LEARNING_MODE") or learning_mode
        qdrant_collection = _resolve_env_from_container(container_name, "QDRANT_COLLECTION") or qdrant_collection
    return {
        "learning_mode": learning_mode.strip().lower(),
        "qdrant_collection": qdrant_collection.strip(),
    }

def _resolve_qdrant_env(container_name):
    host = os.environ.get("QDRANT_HOST", "") or ""
    api_key = os.environ.get("QDRANT_API_KEY", "") or ""
    if container_name:
        host = _resolve_env_from_container(container_name, "QDRANT_HOST") or host
        api_key = _resolve_env_from_container(container_name, "QDRANT_API_KEY") or api_key
    host = host.strip() or "http://qdrant:6333"
    return {"host": host, "api_key": api_key.strip()}

def _qdrant_find_handover(
    *,
    container_name,
    host,
    api_key,
    collection,
    handover_id,
    client_slug,
    timeout,
):
    if not container_name:
        return None, "qdrant: container not found"
    if not collection:
        return None, "qdrant: collection missing"
    payload = {
        "filter": {
            "must": [
                {"key": "metadata.handover_id", "match": {"value": handover_id}},
                {"key": "metadata.client_slug", "match": {"value": client_slug}},
            ]
        },
        "limit": 1,
        "with_payload": True,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    url = f"{host.rstrip('/')}/collections/{collection}/points/scroll"
    max_time = int(max(timeout, 1))
    curl_check = run_docker_exec(container_name, "command -v curl >/dev/null 2>&1 && echo curl_ok")
    use_curl = curl_check.returncode == 0 and "curl_ok" in (curl_check.stdout or "")
    if use_curl:
        headers = "-H 'Content-Type: application/json'"
        if api_key:
            headers += f" -H 'api-key: {api_key}'"
        cmd = (
            f"printf %s {shlex.quote(payload_json)} | "
            f"curl -sS -X POST {headers} --data-binary @- --max-time {max_time} {shlex.quote(url)}"
        )
        result = run_docker_exec(container_name, cmd)
        if result.returncode != 0:
            return None, (result.stderr.strip() or "qdrant: curl failed")
    else:
        payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")
        env_parts = [
            f"PAYLOAD_B64={shlex.quote(payload_b64)}",
            f"QDRANT_URL={shlex.quote(url)}",
        ]
        if api_key:
            env_parts.append(f"QDRANT_API_KEY={shlex.quote(api_key)}")
        env_prefix = " ".join(env_parts)
        python_script = (
            "import base64, json, os, sys, urllib.request\n"
            "payload = json.loads(base64.b64decode(os.environ['PAYLOAD_B64']).decode('utf-8'))\n"
            "url = os.environ.get('QDRANT_URL')\n"
            "api_key = os.environ.get('QDRANT_API_KEY')\n"
            "req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), method='POST')\n"
            "req.add_header('Content-Type', 'application/json')\n"
            "if api_key:\n"
            "    req.add_header('api-key', api_key)\n"
            "try:\n"
            f"    with urllib.request.urlopen(req, timeout={max_time}) as resp:\n"
            "        body = resp.read().decode('utf-8', 'replace')\n"
            "        print(body)\n"
            "except Exception as exc:\n"
            "    print('ERROR:' + str(exc))\n"
            "    sys.exit(1)\n"
        )
        cmd = f"{env_prefix} python3 - <<'PY'\n{python_script}PY"
        result = run_docker_exec(container_name, cmd)
        if result.returncode != 0:
            return None, (result.stderr.strip() or "qdrant: python request failed")
    try:
        data = json.loads(result.stdout or "")
    except Exception:
        return None, "qdrant: invalid json response"
    points = (data.get("result") or {}).get("points") or []
    return bool(points), None

def _trace_has_entry(trace_list, stage, decision=None):
    if not isinstance(trace_list, list):
        return False
    for entry in trace_list:
        if not isinstance(entry, dict):
            continue
        if entry.get("stage") != stage:
            continue
        if decision is not None and entry.get("decision") != decision:
            continue
        return True
    return False


def _trace_as_list(trace_list):
    if isinstance(trace_list, dict):
        return [trace_list]
    if isinstance(trace_list, list):
        return [entry for entry in trace_list if isinstance(entry, dict)]
    return []


def _find_trace_entry(trace_list, *, stage, policy_gate=None, policy_section=None):
    for entry in _trace_as_list(trace_list):
        if entry.get("stage") != stage:
            continue
        if policy_gate and entry.get("policy_gate") != policy_gate:
            continue
        if policy_section and entry.get("policy_section") != policy_section:
            continue
        return entry
    return None

def _send_json_payload(url, payload, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return exc.code, body, str(exc)
    except urllib.error.URLError as exc:
        return None, "", str(exc)

def _build_livecheck_message(rng, case, marker_prefix, timestamp, idx, noise):
    base_text = rng.choice(case["messages"])
    text = _apply_noise(base_text, rng, noise)
    marker = f"{marker_prefix}:{case['case_id']}:{timestamp}:{idx:02d}"
    message = f"{text} [{marker}]"
    return text, marker, message

def _fetch_message_meta(db_user, message_id):
    query = (
        "SELECT conversation_id, metadata->'decision_meta' AS decision_meta "
        "FROM messages WHERE role='user' "
        f"AND metadata->>'messageId' = '{message_id}' "
        "ORDER BY created_at DESC LIMIT 1;"
    )
    result = run_command(
        [
            "docker",
            "exec",
            "-i",
            "truffles_postgres_1",
            "psql",
            "-U",
            db_user,
            "-d",
            "chatbot",
            "-t",
            "-A",
            "-F",
            "\t",
            "-c",
            query,
        ]
    )
    if result.returncode != 0:
        return None, None, result.stderr.strip()
    row = result.stdout.strip()
    if not row:
        return None, None, None
    parts = row.split("\t", 1)
    conversation_id = parts[0] if parts else None
    meta_raw = parts[1] if len(parts) > 1 else None
    if meta_raw:
        try:
            meta = json.loads(meta_raw)
        except Exception:
            meta = None
    else:
        meta = None
    return conversation_id, meta, None

def _poll_decision_meta(db_user, message_id, timeout, interval):
    deadline = time.time() + max(timeout, 0)
    last_meta = None
    last_conv_id = None
    last_error = None
    while time.time() <= deadline:
        conversation_id, meta, error = _fetch_message_meta(db_user, message_id)
        if error:
            last_error = error
        if conversation_id:
            last_conv_id = conversation_id
        if meta:
            last_meta = meta
            action = meta.get("action") or meta.get("pending_action")
            policy_gate = meta.get("policy_gate")
            if action or policy_gate:
                return last_conv_id, last_meta, None
        time.sleep(max(interval, 0.2))
    return last_conv_id, last_meta, last_error or "timeout"

def _poll_decision_trace(db_user, conversation_id, timeout, interval):
    if not conversation_id:
        return None, [], "missing conversation_id"
    deadline = time.time() + max(timeout, 0)
    last_meta = None
    last_error = None
    last_trace = []
    while time.time() <= deadline:
        conv_meta, conv_error = _fetch_conversation_meta(db_user, conversation_id)
        if conv_error:
            last_error = conv_error
        elif conv_meta:
            last_meta = conv_meta
            context = conv_meta.get("context") if isinstance(conv_meta, dict) else None
            trace_list = context.get("decision_trace") if isinstance(context, dict) else None
            trace_entries = _trace_as_list(trace_list)
            if trace_entries:
                return conv_meta, trace_entries, None
            last_trace = trace_entries
        time.sleep(max(interval, 0.2))
    return last_meta, last_trace, last_error or "trace timeout"

def _resolve_env_from_container(container_name, var_name):
    if not container_name:
        return ""
    result = run_docker_exec(container_name, f'printf "%s" "${{{var_name}:-}}"')
    if result.returncode != 0:
        return ""
    return result.stdout.strip()

def _resolve_outbox_coalesce_seconds(container_name):
    value = os.environ.get("OUTBOX_COALESCE_SECONDS") or ""
    if container_name:
        container_value = _resolve_env_from_container(container_name, "OUTBOX_COALESCE_SECONDS")
        if container_value:
            value = container_value
    if not value:
        return 8.0
    try:
        return max(0.0, float(value))
    except ValueError:
        return 8.0

def _resolve_outbox_wait_seconds(container_name, extra_seconds=1.0):
    return max(0.0, _resolve_outbox_coalesce_seconds(container_name) + extra_seconds)

def _resolve_remote_jid(explicit, rng, container_name=None):
    if explicit:
        return explicit
    env_value = (
        os.environ.get("FUZZ_REMOTE_JID")
        or os.environ.get("CHATFLOW_JID")
        or os.environ.get("OUTBOUND_ALLOWLIST_JIDS")
    )
    if not env_value and container_name:
        env_value = _resolve_env_from_container(container_name, "OUTBOUND_ALLOWLIST_JIDS")
    if not env_value and container_name:
        env_value = _resolve_env_from_container(container_name, "CHATFLOW_JID")
    jids = [jid.strip() for jid in (env_value or "").split(",") if jid.strip()]
    if jids:
        return rng.choice(jids) if len(jids) > 1 else jids[0]
    return "77015705555@s.whatsapp.net"

def _logic_jid_for_index(idx):
    base = int(os.environ.get("FUZZ_LOGIC_JID_BASE", "99900000000"))
    return f"{base + idx}@s.whatsapp.net"

def _send_webhook_payload(url, payload, secret, timeout):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Webhook-Secret"] = secret
    req = urllib.request.Request(url, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return exc.code, body, str(exc)
    except urllib.error.URLError as exc:
        return None, "", str(exc)

def _post_admin_outbox(url, admin_token, timeout):
    headers = {"X-Admin-Token": admin_token} if admin_token else {}
    req = urllib.request.Request(url, data=b"", method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        return exc.code, body, str(exc)
    except urllib.error.URLError as exc:
        return None, "", str(exc)

def _ensure_bot_active_before_suite(args, context):
    if args.dry_run:
        return
    remote_jid = context.get("remote_jid")
    client_meta = context.get("client_meta") or {}
    client_id = client_meta.get("client_id")
    db_user = context.get("db_user")
    webhook_url = context.get("webhook_url")
    webhook_secret = context.get("webhook_secret")
    admin_token = context.get("admin_token")
    instance_id = context.get("instance_id")
    timestamp = context.get("timestamp")
    if not remote_jid or not client_id or not db_user:
        return
    conv_id, state, error = _fetch_latest_conversation_state(db_user, client_id, remote_jid)
    if error:
        print(json.dumps({"stage": "preflight_state", "error": error}, ensure_ascii=False))
        return
    state_before = state
    if state not in ("pending", "manager_active"):
        return
    if state == "manager_active":
        handover_meta, _ = _fetch_handover_meta(db_user, conv_id)
        handover_id = (handover_meta or {}).get("handover_id")
        conv_meta, _ = _fetch_conversation_meta(db_user, conv_id)
        topic_id = (conv_meta or {}).get("telegram_topic_id")
        chat_id_raw = client_meta.get("telegram_chat_id")
        if not handover_id or not chat_id_raw:
            raise SystemExit("livecheck-auto: preflight missing handover or telegram_chat_id")
        try:
            chat_id = int(chat_id_raw)
        except ValueError:
            raise SystemExit(f"livecheck-auto: invalid telegram_chat_id {chat_id_raw}")
        owner_id, owner_username = _parse_owner_identity(client_meta.get("owner_telegram_id"))
        manager_id = owner_id if owner_id is not None else 10001
        manager_username = owner_username or "ci_manager"
        preflight_action = "resolve_manager"
        preflight_message_id = f"LC-PREFLIGHT-{timestamp}-{uuid.uuid4().hex[:8]}"
        callback_message = {
            "message_id": int(time.time() * 1000) % 1000000,
            "date": int(time.time()),
            "chat": {"id": chat_id, "type": "supergroup", "title": "CI"},
        }
        if topic_id:
            callback_message["message_thread_id"] = topic_id
        callback_payload = {
            "update_id": int(time.time()),
            "callback_query": {
                "id": preflight_message_id,
                "from": {
                    "id": manager_id,
                    "is_bot": False,
                    "first_name": "CI",
                    "last_name": "Runner",
                    "username": manager_username,
                },
                "message": callback_message,
                "data": f"resolve_{handover_id}",
            },
        }
        preflight_status, preflight_body, preflight_error = _send_json_payload(
            f"{context.get('base_url')}/telegram-webhook", callback_payload, args.timeout
        )
    else:
        preflight_text = args.ack_text or "ок"
        preflight_action = "ack_pending"
        preflight_message_id = f"LC-PREFLIGHT-{timestamp}-{uuid.uuid4().hex[:8]}"
        preflight_payload = {
            "body": {
                "messageType": "text",
                "message": preflight_text,
                "metadata": {
                    "sender": "LivecheckAuto",
                    "timestamp": int(time.time()),
                    "messageId": preflight_message_id,
                    "remoteJid": remote_jid,
                },
            }
        }
        if instance_id:
            preflight_payload["body"]["metadata"]["instanceId"] = instance_id
        preflight_status, preflight_body, preflight_error = _send_webhook_payload(
            webhook_url, preflight_payload, webhook_secret, args.timeout
        )
        _post_admin_outbox(f"{context.get('base_url')}/admin/outbox/process", admin_token, args.timeout)
    if preflight_error:
        raise SystemExit(f"livecheck-auto: preflight message failed ({preflight_error})")
    cleared = False
    clear_wait_seconds = 30
    for _ in range(clear_wait_seconds):
        time.sleep(1.0)
        conv_id, state, _ = _fetch_latest_conversation_state(db_user, client_id, remote_jid)
        if state == "bot_active":
            cleared = True
            break
    print(
        json.dumps(
            {
                "stage": "preflight_clear_pending",
                "state_before": state_before,
                "action": preflight_action,
                "conversation_id": conv_id,
                "message_id": preflight_message_id,
                "status": preflight_status,
                "response": (preflight_body or "")[:200] if preflight_body else None,
                "state_after": state,
                "cleared": cleared,
            },
            ensure_ascii=False,
        )
    )
    if not cleared:
        raise SystemExit(
            f"livecheck-auto: pending state not cleared before {args.suite} (state_after={state})"
        )

def _run_webhook_fuzz(args):
    if args.count < 1:
        raise SystemExit("webhook-fuzz: --count must be >= 1")
    rng = random.Random(args.seed or int(time.time()))
    min_wait = min(args.min_wait, args.max_wait)
    max_wait = max(args.min_wait, args.max_wait)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_url = args.base_url.rstrip("/")
    client_slug = args.client_slug
    webhook_url = f"{base_url}/webhook/{client_slug}"
    mode = args.mode
    skip_outbox = args.skip_outbox or mode == "logic"

    container_name, _ = resolve_container_name()

    webhook_secret = (
        args.webhook_secret
        or os.environ.get("WEBHOOK_SECRET")
        or os.environ.get("TRUFFLES_WEBHOOK_SECRET")
    )
    admin_token = args.admin_token or os.environ.get("ALERTS_ADMIN_TOKEN")
    if not admin_token and container_name:
        admin_token = _resolve_env_from_container(container_name, "ALERTS_ADMIN_TOKEN")

    instance_id = (
        args.instance_id
        or os.environ.get("CHATFLOW_INSTANCE_ID")
        or os.environ.get("INSTANCE_ID")
    )
    test_mode_enabled = _resolve_test_mode(container_name)
    allowlist_jids = _resolve_allowlist_jids(args.allowlist_jids, container_name)
    selected_cases, requested_case_ids = _select_cases(WEBHOOK_FUZZ_CASES, args.case_ids)
    if selected_cases is None:
        selected_cases = _pick_fuzz_cases(WEBHOOK_FUZZ_CASES, args.count, rng)
        requested_case_ids = []

    if mode == "logic" and not test_mode_enabled:
        raise SystemExit("webhook-fuzz: TEST_MODE disabled; logic mode is blocked for safety")

    remote_jid = None
    if mode == "state":
        if not allowlist_jids:
            raise SystemExit("webhook-fuzz: allowlist-jids required for state mode")
        remote_jid = args.remote_jid or allowlist_jids[0]
        if remote_jid not in allowlist_jids:
            raise SystemExit(
                f"webhook-fuzz: remote-jid {remote_jid} not in allowlist; refusing to send"
            )

    markers = []
    message_ids = []
    remote_jids = []

    for idx, case in enumerate(selected_cases, start=1):
        base_text = rng.choice(case["messages"])
        text = _apply_noise(base_text, rng, args.noise)
        marker = f"FZ:{case['case_id']}:{timestamp}:{idx:02d}"
        message = f"{text} [{marker}]"
        message_id = f"FZ-{timestamp}-{idx:02d}-{uuid.uuid4().hex[:8]}"
        sent_at = datetime.now(timezone.utc).isoformat()
        if mode == "logic":
            remote_jid = _logic_jid_for_index(idx)
            if not skip_outbox and allowlist_jids and remote_jid not in allowlist_jids:
                raise SystemExit(
                    f"webhook-fuzz: remote-jid {remote_jid} not in allowlist; refusing to send"
                )
        remote_jids.append(remote_jid)
        metadata = {
            "sender": "FuzzRunner",
            "timestamp": int(time.time()),
            "messageId": message_id,
            "remoteJid": remote_jid,
        }
        if instance_id:
            metadata["instanceId"] = instance_id
        payload = {
            "body": {
                "messageType": "text",
                "message": message,
                "metadata": metadata,
            }
        }

        status = "dry_run"
        response_status = None
        response_body = None
        response_error = None
        if not args.dry_run:
            response_status, response_body, response_error = _send_webhook_payload(
                webhook_url, payload, webhook_secret, args.timeout
            )
            if response_status and 200 <= response_status < 300:
                status = "sent"
            else:
                status = "error"

        log = {
            "case_id": case["case_id"],
            "marker": marker,
            "message_id": message_id,
            "remote_jid": remote_jid,
            "text": message,
            "sent_at": sent_at,
            "expected_policy_section": case["expected_policy_section"],
            "status": status,
            "http_status": response_status,
        }
        if response_error:
            log["error"] = response_error
        if response_body:
            log["response"] = response_body[:200]
        print(json.dumps(log, ensure_ascii=False))

        markers.append(marker)
        message_ids.append(message_id)

        if idx < len(selected_cases):
            time.sleep(rng.uniform(min_wait, max_wait))

    outbox_status = None
    outbox_error = None
    outbox_body = None
    if not skip_outbox:
        if not allowlist_jids:
            raise SystemExit("webhook-fuzz: allowlist-jids required when outbox enabled")
        unique_jids = sorted(set(remote_jids))
        not_allowed = [jid for jid in unique_jids if jid not in allowlist_jids]
        if not_allowed:
            raise SystemExit(
                "webhook-fuzz: outbox enabled for non-allowlist JID(s): "
                + ", ".join(not_allowed)
            )
        if not admin_token and not args.dry_run:
            raise SystemExit("webhook-fuzz: missing admin token for outbox/process")
        if not args.dry_run:
            outbox_url = f"{base_url}/admin/outbox/process"
            outbox_status, outbox_body, outbox_error = _post_admin_outbox(
                outbox_url, admin_token, args.timeout
            )
            outbox_log = {
                "outbox_url": outbox_url,
                "status": outbox_status,
                "error": outbox_error,
            }
            if outbox_body:
                outbox_log["response"] = outbox_body[:200]
            print(json.dumps(outbox_log, ensure_ascii=False))
            if outbox_status and outbox_status >= 400:
                raise SystemExit(f"webhook-fuzz: outbox/process failed (status {outbox_status})")

    summary = {
        "count": len(selected_cases),
        "base_url": base_url,
        "client_slug": client_slug,
        "seed": args.seed,
        "mode": mode,
        "skip_outbox": skip_outbox,
        "allowlist_jids": allowlist_jids,
        "case_ids": requested_case_ids,
        "remote_jid": remote_jid,
        "remote_jids": remote_jids,
        "instance_id": instance_id,
        "test_mode": test_mode_enabled,
        "markers": markers,
        "message_ids": message_ids,
        "outbox_status": outbox_status,
    }
    print(json.dumps({"summary": summary}, ensure_ascii=False))

def _run_livecheck_ca05_booking(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    steps = case.get("steps") or []
    if not steps:
        raise SystemExit("livecheck-auto: CA05 missing steps")
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    db_user = context["db_user"]
    allowlist_jids = context["allowlist_jids"]
    outbox_url = f"{base_url}/admin/outbox/process"
    min_wait = min(args.min_wait, args.max_wait)
    max_wait = max(args.min_wait, args.max_wait)

    if not remote_jid or remote_jid not in allowlist_jids:
        raise SystemExit("livecheck-auto: CA05 remote_jid not in allowlist")

    results = []
    conv_id = None
    reset_summary = None

    if not args.dry_run:
        reset_text = "начнем сначала"
        reset_marker = f"LC:AUTO:CA05:RESET:{timestamp}"
        reset_message_id = f"LC-AUTO-{timestamp}-CA05-RESET-{uuid.uuid4().hex[:8]}"
        reset_payload = {
            "body": {
                "messageType": "text",
                "message": f"{reset_text} [{reset_marker}]",
                "metadata": {
                    "sender": "LivecheckAuto",
                    "timestamp": int(time.time()),
                    "messageId": reset_message_id,
                    "remoteJid": remote_jid,
                },
            }
        }
        if instance_id:
            reset_payload["body"]["metadata"]["instanceId"] = instance_id
        reset_status, reset_body, reset_error = _send_webhook_payload(
            webhook_url, reset_payload, webhook_secret, args.timeout
        )
        print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "step": "reset",
                    "marker": reset_marker,
                    "message_id": reset_message_id,
                    "remote_jid": remote_jid,
                    "text": reset_payload["body"]["message"],
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "status": "sent" if reset_status and 200 <= reset_status < 300 else "error",
                    "http_status": reset_status,
                    "error": reset_error,
                    "response": (reset_body or "")[:200] if reset_body else None,
                },
                ensure_ascii=False,
            )
        )
        _post_admin_outbox(outbox_url, admin_token, args.timeout)
        conv_id, reset_meta, reset_meta_error = _poll_decision_meta(
            db_user, reset_message_id, args.poll_timeout, args.poll_interval
        )
        if reset_meta_error:
            raise SystemExit(f"livecheck-auto: CA05 reset poll failed ({reset_meta_error})")
        reset_conv_meta, reset_conv_error = _fetch_conversation_meta(db_user, conv_id)
        reset_context = reset_conv_meta.get("context") if isinstance(reset_conv_meta, dict) else None
        reset_expected = (
            reset_context.get("expected_reply_type") if isinstance(reset_context, dict) else None
        )
        reset_booking = reset_context.get("booking") if isinstance(reset_context, dict) else None
        booking_active = False
        booking_service = None
        if isinstance(reset_booking, dict):
            booking_active = bool(reset_booking.get("active"))
            booking_service = reset_booking.get("service")
        if reset_expected:
            raise SystemExit("livecheck-auto: CA05 reset did not clear expected_reply_type")
        if booking_active:
            raise SystemExit("livecheck-auto: CA05 reset did not clear booking active")
        reset_summary = {
            "reset_message_id": reset_message_id,
            "reset_action": (reset_meta or {}).get("action"),
            "reset_intent": (reset_meta or {}).get("intent"),
            "reset_expected_reply_type": reset_expected,
            "reset_booking_active": booking_active,
            "reset_booking_service": booking_service,
            "reset_error": reset_conv_error,
        }

    for idx, step in enumerate(steps, start=1):
        base_text = step.get("message") or ""
        if not base_text:
            raise SystemExit("livecheck-auto: CA05 empty step message")
        text = _apply_noise(base_text, rng, args.noise)
        marker = f"LC:AUTO:CA05:{case['case_id']}:{timestamp}:{idx:02d}"
        message = f"{text} [{marker}]"
        message_id = f"LC-AUTO-{timestamp}-CA05-{idx:02d}-{uuid.uuid4().hex[:8]}"
        sent_at = datetime.now(timezone.utc).isoformat()

        metadata = {
            "sender": "LivecheckAuto",
            "timestamp": int(time.time()),
            "messageId": message_id,
            "remoteJid": remote_jid,
        }
        if instance_id:
            metadata["instanceId"] = instance_id
        payload = {"body": {"messageType": "text", "message": message, "metadata": metadata}}

        status = "dry_run"
        response_status = None
        response_body = None
        response_error = None
        if not args.dry_run:
            response_status, response_body, response_error = _send_webhook_payload(
                webhook_url, payload, webhook_secret, args.timeout
            )
            status = "sent" if response_status and 200 <= response_status < 300 else "error"
        print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "step": idx,
                    "marker": marker,
                    "message_id": message_id,
                    "remote_jid": remote_jid,
                    "text": message,
                    "sent_at": sent_at,
                    "status": status,
                    "http_status": response_status,
                    "error": response_error,
                    "response": (response_body or "")[:200] if response_body else None,
                },
                ensure_ascii=False,
            )
        )

        meta = None
        conv_meta = None
        conv_error = None
        if not args.dry_run:
            _post_admin_outbox(outbox_url, admin_token, args.timeout)
            conv_id, meta, error = _poll_decision_meta(
                db_user, message_id, args.poll_timeout, args.poll_interval
            )
            if error:
                raise SystemExit(f"livecheck-auto: CA05 decision_meta poll failed ({error})")
            conv_meta, conv_error = _fetch_conversation_meta(db_user, conv_id)

        conv_context = conv_meta.get("context") if isinstance(conv_meta, dict) else None
        expected_reply_type = conv_context.get("expected_reply_type") if isinstance(conv_context, dict) else None
        booking_state = conv_context.get("booking") if isinstance(conv_context, dict) else None
        trace_list = conv_context.get("decision_trace") if isinstance(conv_context, dict) else None
        interrupt_trace = None
        for entry in reversed(_trace_as_list(trace_list)):
            if entry.get("stage") == "booking_interrupt":
                interrupt_trace = entry
                break

        if not args.dry_run:
            expected_reply = step.get("expect_expected_reply_type")
            if expected_reply and expected_reply_type != expected_reply:
                raise SystemExit(
                    f"livecheck-auto: CA05 expected_reply_type mismatch ({expected_reply_type})"
                )
            expected_llm = step.get("expect_llm_used")
            if expected_llm is not None and (meta or {}).get("llm_used") is not expected_llm:
                raise SystemExit("livecheck-auto: CA05 llm_used mismatch")
            expected_service = step.get("expect_booking_service")
            if expected_service:
                service = None
                if isinstance(booking_state, dict):
                    service = booking_state.get("service")
                if not service or expected_service not in str(service).lower():
                    raise SystemExit("livecheck-auto: CA05 booking.service mismatch")
            if step.get("expect_booking_interrupt"):
                if (meta or {}).get("booking_info_interrupt") is not True:
                    raise SystemExit("livecheck-auto: CA05 booking_info_interrupt mismatch")
                info_intents = (meta or {}).get("booking_info_intents")
                if not isinstance(info_intents, list) or not info_intents:
                    raise SystemExit("livecheck-auto: CA05 booking_info_intents empty")
                if not interrupt_trace:
                    raise SystemExit("livecheck-auto: CA05 missing booking_interrupt trace")
                trace_intents = interrupt_trace.get("info_intents")
                if not isinstance(trace_intents, list) or not trace_intents:
                    raise SystemExit("livecheck-auto: CA05 trace info_intents empty")

        results.append(
            {
                "step": idx,
                "message_id": message_id,
                "conversation_id": conv_id,
                "expected_reply_type": expected_reply_type,
                "booking_service": booking_state.get("service") if isinstance(booking_state, dict) else None,
                "booking_info_interrupt": (meta or {}).get("booking_info_interrupt"),
                "booking_info_intents": (meta or {}).get("booking_info_intents"),
                "trace_booking_interrupt": bool(interrupt_trace),
                "trace_info_intents": interrupt_trace.get("info_intents") if interrupt_trace else None,
                "llm_used": (meta or {}).get("llm_used"),
                "error": conv_error,
            }
        )

        if idx < len(steps):
            time.sleep(rng.uniform(min_wait, max_wait))

    summary = {
        "suite": "ca05-booking",
        "case_id": case["case_id"],
        "conversation_id": conv_id,
        "results": results,
        "reset": reset_summary,
    }
    return summary

def _run_livecheck_ca06_reset(args, context):
    if args.dry_run:
        return None
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    db_user = context["db_user"]
    allowlist_jids = context["allowlist_jids"]
    outbox_url = f"{base_url}/admin/outbox/process"

    if not remote_jid or remote_jid not in allowlist_jids:
        raise SystemExit("livecheck-auto: CA06 remote_jid not in allowlist")

    reset_text = "начнем сначала"
    reset_marker = f"LC:AUTO:CA06:RESET:{timestamp}"
    reset_message_id = f"LC-AUTO-{timestamp}-CA06-RESET-{uuid.uuid4().hex[:8]}"
    reset_payload = {
        "body": {
            "messageType": "text",
            "message": f"{reset_text} [{reset_marker}]",
            "metadata": {
                "sender": "LivecheckAuto",
                "timestamp": int(time.time()),
                "messageId": reset_message_id,
                "remoteJid": remote_jid,
            },
        }
    }
    if instance_id:
        reset_payload["body"]["metadata"]["instanceId"] = instance_id
    reset_status, reset_body, reset_error = _send_webhook_payload(
        webhook_url, reset_payload, webhook_secret, args.timeout
    )
    print(
        json.dumps(
            {
                "case_id": "CA06_RESET",
                "step": "reset",
                "marker": reset_marker,
                "message_id": reset_message_id,
                "remote_jid": remote_jid,
                "text": reset_payload["body"]["message"],
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "status": "sent" if reset_status and 200 <= reset_status < 300 else "error",
                "http_status": reset_status,
                "error": reset_error,
                "response": (reset_body or "")[:200] if reset_body else None,
            },
            ensure_ascii=False,
        )
    )
    _post_admin_outbox(outbox_url, admin_token, args.timeout)
    conv_id, reset_meta, reset_meta_error = _poll_decision_meta(
        db_user, reset_message_id, args.poll_timeout, args.poll_interval
    )
    if reset_meta_error:
        raise SystemExit(f"livecheck-auto: CA06 reset meta poll failed ({reset_meta_error})")
    reset_conv_meta, reset_trace, reset_trace_error = _poll_decision_trace(
        db_user, conv_id, args.poll_timeout, args.poll_interval
    )
    if reset_trace_error:
        raise SystemExit(f"livecheck-auto: CA06 reset trace poll failed ({reset_trace_error})")
    last_trace = reset_trace[-1] if reset_trace else None
    reset_state = reset_conv_meta.get("state") if isinstance(reset_conv_meta, dict) else None
    return {
        "reset_message_id": reset_message_id,
        "reset_action": (reset_meta or {}).get("action"),
        "reset_intent": (reset_meta or {}).get("intent"),
        "reset_state": reset_state,
        "reset_trace_stage": (last_trace or {}).get("stage"),
        "reset_trace_decision": (last_trace or {}).get("decision"),
    }

def _run_livecheck_ca08_state(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    db_user = context["db_user"]
    outbox_url = f"{base_url}/admin/outbox/process"
    allowlist_jids = context["allowlist_jids"]

    if not remote_jid or remote_jid not in allowlist_jids:
        raise SystemExit("livecheck-auto: CA08 remote_jid not in allowlist")

    text, marker, message = _build_livecheck_message(
        rng, case, "LC:AUTO:CA08", timestamp, 1, args.noise
    )
    message_id = f"LC-AUTO-{timestamp}-CA08-{uuid.uuid4().hex[:8]}"
    sent_at = datetime.now(timezone.utc).isoformat()

    metadata = {
        "sender": "LivecheckAuto",
        "timestamp": int(time.time()),
        "messageId": message_id,
        "remoteJid": remote_jid,
    }
    if instance_id:
        metadata["instanceId"] = instance_id
    payload = {"body": {"messageType": "text", "message": message, "metadata": metadata}}

    status = "dry_run"
    response_status = None
    response_body = None
    response_error = None
    if not args.dry_run:
        response_status, response_body, response_error = _send_webhook_payload(
            webhook_url, payload, webhook_secret, args.timeout
        )
        status = "sent" if response_status and 200 <= response_status < 300 else "error"
    print(
        json.dumps(
            {
                "case_id": case["case_id"],
                "marker": marker,
                "message_id": message_id,
                "remote_jid": remote_jid,
                "text": message,
                "sent_at": sent_at,
                "expected_policy_section": case["expected_policy_section"],
                "status": status,
                "http_status": response_status,
                "error": response_error,
                "response": (response_body or "")[:200] if response_body else None,
            },
            ensure_ascii=False,
        )
    )

    conv_id = None
    meta = None
    outbox_status = None
    outbox_body = None
    outbox_error = None
    if not args.dry_run:
        outbox_status, outbox_body, outbox_error = _post_admin_outbox(
            outbox_url, admin_token, args.timeout
        )
        conv_id, meta, error = _poll_decision_meta(
            db_user, message_id, args.poll_timeout, args.poll_interval
        )
        if error:
            raise SystemExit(f"livecheck-auto: CA08 decision_meta poll failed ({error})")

    conv_before, conv_before_error = _fetch_conversation_meta(db_user, conv_id) if conv_id else (None, None)
    handover_before, handover_before_error = _fetch_handover_meta(db_user, conv_id) if conv_id else (None, None)

    ack_text = args.ack_text or "ок"
    ack_marker = f"LC:ACK:CA08:{timestamp}:01"
    ack_message_id = f"LC-ACK-{timestamp}-CA08-{uuid.uuid4().hex[:8]}"
    ack_payload = {
        "body": {
            "messageType": "text",
            "message": ack_text,
            "metadata": {
                "sender": "LivecheckAuto",
                "timestamp": int(time.time()),
                "messageId": ack_message_id,
                "remoteJid": remote_jid,
            },
        }
    }
    if instance_id:
        ack_payload["body"]["metadata"]["instanceId"] = instance_id

    ack_status = None
    ack_body = None
    ack_error = None
    ack_meta = None
    ack_outbox_status = None
    ack_outbox_body = None
    ack_outbox_error = None
    if not args.dry_run:
        ack_status, ack_body, ack_error = _send_webhook_payload(
            webhook_url, ack_payload, webhook_secret, args.timeout
        )
        ack_outbox_status, ack_outbox_body, ack_outbox_error = _post_admin_outbox(
            outbox_url, admin_token, args.timeout
        )
        _, ack_meta, ack_meta_error = _poll_decision_meta(
            db_user, ack_message_id, args.poll_timeout, args.poll_interval
        )
        if ack_meta_error:
            raise SystemExit(f"livecheck-auto: CA08 ACK poll failed ({ack_meta_error})")

    conv_after, conv_after_error = _fetch_conversation_meta(db_user, conv_id) if conv_id else (None, None)
    handover_after, handover_after_error = _fetch_handover_meta(db_user, conv_id) if conv_id else (None, None)

    trace_list = None
    if conv_after and isinstance(conv_after.get("context"), dict):
        trace_list = conv_after.get("context", {}).get("decision_trace")

    summary = {
        "suite": "ca08-state",
        "message_id": message_id,
        "ack_message_id": ack_message_id,
        "ack_marker": ack_marker,
        "conversation_id": conv_id,
        "policy_gate": (meta or {}).get("policy_gate"),
        "action": (meta or {}).get("action"),
        "pending_action": (ack_meta or {}).get("pending_action"),
        "ack_text": ack_text,
        "conversation_state_before": (conv_before or {}).get("state"),
        "conversation_state_after": (conv_after or {}).get("state"),
        "handover_status_before": (handover_before or {}).get("status"),
        "handover_status_after": (handover_after or {}).get("status"),
        "handover_added_to_knowledge": (handover_after or {}).get("added_to_knowledge"),
        "pending_sla_trace": _trace_has_entry(trace_list, "pending_sla", "pending_ack"),
        "pending_resume_trace": _trace_has_entry(trace_list, "pending_resume"),
        "errors": {
            "conversation_before": conv_before_error,
            "handover_before": handover_before_error,
            "conversation_after": conv_after_error,
            "handover_after": handover_after_error,
            "ack_error": ack_error,
            "outbox_error": outbox_error,
            "ack_outbox_error": ack_outbox_error,
        },
        "ack_http_status": ack_status,
        "ack_http_response": (ack_body or "")[:200] if ack_body else None,
        "outbox_status": outbox_status,
        "outbox_response": (outbox_body or "")[:200] if outbox_body else None,
        "ack_outbox_status": ack_outbox_status,
        "ack_outbox_response": (ack_outbox_body or "")[:200] if ack_outbox_body else None,
    }
    return summary

def _run_livecheck_ca09_manager(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    db_user = context["db_user"]
    client_slug = context["client_slug"]
    client_meta = context["client_meta"]
    learning_env = context["learning_env"]
    outbox_url = f"{base_url}/admin/outbox/process"
    allowlist_jids = context["allowlist_jids"]
    qdrant_env = context["qdrant_env"]

    if not remote_jid or remote_jid not in allowlist_jids:
        raise SystemExit("livecheck-auto: CA09 remote_jid not in allowlist")

    text, marker, message = _build_livecheck_message(
        rng, case, "LC:AUTO:CA09", timestamp, 1, args.noise
    )
    message_id = f"LC-AUTO-{timestamp}-CA09-{uuid.uuid4().hex[:8]}"
    metadata = {
        "sender": "LivecheckAuto",
        "timestamp": int(time.time()),
        "messageId": message_id,
        "remoteJid": remote_jid,
    }
    if instance_id:
        metadata["instanceId"] = instance_id
    payload = {"body": {"messageType": "text", "message": message, "metadata": metadata}}

    status = "dry_run"
    response_status = None
    response_body = None
    response_error = None
    if not args.dry_run:
        response_status, response_body, response_error = _send_webhook_payload(
            webhook_url, payload, webhook_secret, args.timeout
        )
        status = "sent" if response_status and 200 <= response_status < 300 else "error"
    print(
        json.dumps(
            {
                "case_id": case["case_id"],
                "marker": marker,
                "message_id": message_id,
                "remote_jid": remote_jid,
                "text": message,
                "expected_policy_section": case["expected_policy_section"],
                "status": status,
                "http_status": response_status,
                "error": response_error,
                "response": (response_body or "")[:200] if response_body else None,
            },
            ensure_ascii=False,
        )
    )

    conv_id = None
    meta = None
    if not args.dry_run:
        _post_admin_outbox(outbox_url, admin_token, args.timeout)
        conv_id, meta, error = _poll_decision_meta(
            db_user, message_id, args.poll_timeout, args.poll_interval
        )
        if error:
            raise SystemExit(f"livecheck-auto: CA09 decision_meta poll failed ({error})")

    conv_before, conv_before_error = _fetch_conversation_meta(db_user, conv_id) if conv_id else (None, None)
    handover_before, handover_before_error = _fetch_handover_meta(db_user, conv_id) if conv_id else (None, None)

    chat_id_raw = client_meta.get("telegram_chat_id") if client_meta else None
    topic_id = (conv_before or {}).get("telegram_topic_id")
    if not chat_id_raw:
        raise SystemExit("livecheck-auto: CA09 missing telegram_chat_id for client")
    if not topic_id:
        raise SystemExit("livecheck-auto: CA09 missing telegram_topic_id for conversation")
    try:
        chat_id = int(chat_id_raw)
    except ValueError:
        raise SystemExit(f"livecheck-auto: CA09 invalid telegram_chat_id {chat_id_raw}")

    owner_id, owner_username = _parse_owner_identity(client_meta.get("owner_telegram_id"))
    manager_id = owner_id if owner_id is not None else 10001
    manager_username = owner_username or "ci_manager"

    qdrant_collection = learning_env.get("qdrant_collection_effective") or ""
    if not qdrant_collection.endswith("_ci"):
        raise SystemExit("livecheck-auto: CA09 requires _ci Qdrant collection")

    manager_text = "Менеджер: уточнили детали, вернемся с ответом."
    telegram_payload = {
        "update_id": int(time.time()),
        "message": {
            "message_id": int(time.time() * 1000) % 1000000,
            "date": int(time.time()),
            "chat": {"id": chat_id, "type": "supergroup", "title": "CI"},
            "from": {
                "id": manager_id,
                "is_bot": False,
                "first_name": "CI",
                "last_name": "Runner",
                "username": manager_username,
            },
            "text": manager_text,
            "message_thread_id": topic_id,
        },
    }

    manager_status = None
    manager_body = None
    manager_error = None
    if not args.dry_run:
        manager_status, manager_body, manager_error = _send_json_payload(
            f"{base_url}/telegram-webhook", telegram_payload, args.timeout
        )
        _post_admin_outbox(outbox_url, admin_token, args.timeout)

    conv_after, conv_after_error = _fetch_conversation_meta(db_user, conv_id) if conv_id else (None, None)
    handover_after, handover_after_error = _fetch_handover_meta(db_user, conv_id) if conv_id else (None, None)
    outbox_latest, outbox_error = _fetch_latest_outbox_for_conversation(db_user, conv_id) if conv_id else (None, None)
    outbox_remote_jid = None
    if outbox_latest and isinstance(outbox_latest.get("payload_json"), dict):
        payload_meta = outbox_latest["payload_json"].get("body", {}).get("metadata", {})
        outbox_remote_jid = payload_meta.get("remoteJid")

    qdrant_found = None
    qdrant_error = None
    if not args.dry_run:
        handover_id = (handover_after or {}).get("handover_id")
        if not handover_id:
            qdrant_error = "qdrant: handover_id missing"
        else:
            qdrant_found, qdrant_error = _qdrant_find_handover(
                container_name=context.get("container_name"),
                host=qdrant_env.get("host"),
                api_key=qdrant_env.get("api_key"),
                collection=qdrant_collection,
                handover_id=handover_id,
                client_slug=client_slug,
                timeout=args.timeout,
            )

    summary = {
        "suite": "ca09-manager",
        "message_id": message_id,
        "conversation_id": conv_id,
        "policy_gate": (meta or {}).get("policy_gate"),
        "action": (meta or {}).get("action"),
        "manager_message": manager_text,
        "manager_identity": {
            "manager_id": manager_id,
            "manager_username": manager_username,
            "owner_used": owner_id is not None or owner_username is not None,
        },
        "telegram_chat_id": chat_id,
        "telegram_topic_id": topic_id,
        "conversation_state_before": (conv_before or {}).get("state"),
        "conversation_state_after": (conv_after or {}).get("state"),
        "handover_status_before": (handover_before or {}).get("status"),
        "handover_status_after": (handover_after or {}).get("status"),
        "assigned_to": (handover_after or {}).get("assigned_to"),
        "first_response_at": (handover_after or {}).get("first_response_at"),
        "manager_response": (handover_after or {}).get("manager_response"),
        "learning_mode": learning_env.get("learning_mode"),
        "qdrant_collection": qdrant_collection,
        "added_to_knowledge": (handover_after or {}).get("added_to_knowledge"),
        "knowledge_doc_id": (handover_after or {}).get("knowledge_doc_id"),
        "qdrant_found": qdrant_found,
        "qdrant_error": qdrant_error,
        "outbox_status": (outbox_latest or {}).get("status"),
        "outbox_remote_jid": outbox_remote_jid,
        "telegram_status": manager_status,
        "errors": {
            "conversation_before": conv_before_error,
            "handover_before": handover_before_error,
            "conversation_after": conv_after_error,
            "handover_after": handover_after_error,
            "outbox": outbox_error,
            "telegram": manager_error,
        },
        "telegram_response": (manager_body or "")[:200] if manager_body else None,
    }
    return summary

def _run_livecheck_ca10_outbox(args, context):
    rng = context["rng"]
    case = context["cases"][0]
    timestamp = context["timestamp"]
    webhook_url = context["webhook_url"]
    base_url = context["base_url"]
    webhook_secret = context["webhook_secret"]
    admin_token = context["admin_token"]
    instance_id = context["instance_id"]
    remote_jid = context["remote_jid"]
    outbox_wait_seconds = context.get("outbox_wait_seconds") or 0.0
    db_user = context["db_user"]
    client_id = context["client_meta"].get("client_id") if context.get("client_meta") else None
    allowlist_jids = context["allowlist_jids"]

    if not client_id:
        raise SystemExit("livecheck-auto: CA10 missing client_id")
    if not remote_jid or remote_jid not in allowlist_jids:
        raise SystemExit("livecheck-auto: CA10 remote_jid not in allowlist")

    text, marker, message = _build_livecheck_message(
        rng, case, "LC:AUTO:CA10", timestamp, 1, args.noise
    )
    message_id = f"LC-DEDUP-{timestamp}-{uuid.uuid4().hex[:8]}"
    outbox_url = f"{base_url}/admin/outbox/process"

    def _send_once(seq):
        sent_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "body": {
                "messageType": "text",
                "message": f"{message} [SEQ:{seq:02d}]",
                "metadata": {
                    "sender": "LivecheckAuto",
                    "timestamp": int(time.time()),
                    "messageId": message_id,
                    "remoteJid": remote_jid,
                },
            }
        }
        if instance_id:
            payload["body"]["metadata"]["instanceId"] = instance_id
        response_status, response_body, response_error = _send_webhook_payload(
            webhook_url, payload, webhook_secret, args.timeout
        )
        status = "sent" if response_status and 200 <= response_status < 300 else "error"
        print(
            json.dumps(
                {
                    "case_id": case["case_id"],
                    "marker": marker,
                    "message_id": message_id,
                    "remote_jid": remote_jid,
                    "text": payload["body"]["message"],
                    "sent_at": sent_at,
                    "status": status,
                    "http_status": response_status,
                    "error": response_error,
                    "response": (response_body or "")[:200] if response_body else None,
                },
                ensure_ascii=False,
            )
        )

    if not args.dry_run:
        _send_once(1)
        _send_once(2)
        if outbox_wait_seconds > 0:
            time.sleep(outbox_wait_seconds)
        _post_admin_outbox(outbox_url, admin_token, args.timeout)

    message_count, message_error = _fetch_message_count(db_user, message_id)
    dedup_count, dedup_error = _fetch_message_dedup_count(db_user, client_id, message_id)
    outbox_summary, outbox_error = _fetch_outbox_summary(db_user, client_id, message_id)
    if (
        not args.dry_run
        and outbox_summary
        and outbox_summary.get("status") == "PENDING"
    ):
        time.sleep(2.0)
        _post_admin_outbox(outbox_url, admin_token, args.timeout)
        outbox_summary, outbox_error = _fetch_outbox_summary(db_user, client_id, message_id)

    summary = {
        "suite": "ca10-outbox",
        "message_id": message_id,
        "message_count": message_count,
        "message_dedup_count": dedup_count,
        "outbox_count": (outbox_summary or {}).get("count"),
        "outbox_status": (outbox_summary or {}).get("status"),
        "errors": {
            "message_count": message_error,
            "dedup_count": dedup_error,
            "outbox": outbox_error,
        },
    }
    return summary

def _run_livecheck_auto(args):
    suite_cases = LIVECHECK_SUITES.get(args.suite)
    if not suite_cases:
        raise SystemExit(f"Unknown suite: {args.suite}")
    rng = random.Random(args.seed or int(time.time()))
    min_wait = min(args.min_wait, args.max_wait)
    max_wait = max(args.min_wait, args.max_wait)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    base_url = args.base_url.rstrip("/")
    client_slug = args.client_slug
    webhook_url = f"{base_url}/webhook/{client_slug}"

    container_name, _ = resolve_container_name()
    if client_slug != SAFE_ALLOWLIST_CLIENT_SLUG:
        raise SystemExit(
            f"livecheck-auto: client_slug {client_slug} not allowed; expected {SAFE_ALLOWLIST_CLIENT_SLUG}"
        )
    test_mode_enabled = _resolve_test_mode(container_name)
    allowlist_jids = _resolve_allowlist_jids(args.allowlist_jids, container_name)
    if not allowlist_jids:
        raise SystemExit("livecheck-auto: allowlist-jids is empty")
    if not test_mode_enabled:
        raise SystemExit("livecheck-auto: TEST_MODE disabled; refusing to run")

    webhook_secret = _resolve_webhook_secret(client_slug, args.webhook_secret)
    if not webhook_secret:
        raise SystemExit("livecheck-auto: missing webhook secret")

    admin_token = args.admin_token or os.environ.get("ALERTS_ADMIN_TOKEN")
    if not admin_token and container_name:
        admin_token = _resolve_env_from_container(container_name, "ALERTS_ADMIN_TOKEN")
    if not admin_token and not args.dry_run:
        raise SystemExit("livecheck-auto: missing admin token")

    db_user = _resolve_db_user_simple()
    client_meta, client_error = _fetch_client_meta(db_user, client_slug)
    if client_error:
        raise SystemExit(f"livecheck-auto: client meta lookup failed ({client_error})")
    if not client_meta or not client_meta.get("client_id"):
        raise SystemExit(f"livecheck-auto: client {client_slug} not found in DB")

    branch_instance_id = client_meta.get("branch_instance_id")
    if not branch_instance_id:
        raise SystemExit("livecheck-auto: branch.instance_id missing for client")

    instance_id = (
        args.instance_id
        or os.environ.get("CHATFLOW_INSTANCE_ID")
        or os.environ.get("INSTANCE_ID")
        or branch_instance_id
    )
    if instance_id != branch_instance_id:
        raise SystemExit(
            f"livecheck-auto: instance_id mismatch (payload {instance_id} vs branch {branch_instance_id})"
        )
    instance_drift = bool(
        client_meta.get("client_instance_id")
        and client_meta.get("client_instance_id") != branch_instance_id
    )

    learning_env = _resolve_learning_env(container_name)
    qdrant_collection = learning_env.get("qdrant_collection") or ""
    if not qdrant_collection and test_mode_enabled:
        qdrant_collection = "truffles_knowledge_ci"
    learning_env["qdrant_collection_effective"] = qdrant_collection
    qdrant_env = _resolve_qdrant_env(container_name)

    selected_cases, requested_case_ids = _select_cases(suite_cases, args.case_ids)
    if selected_cases is None:
        selected_cases = suite_cases
        requested_case_ids = [case["case_id"] for case in suite_cases]

    if args.jid_mode == "allowlist":
        remote_jid = args.remote_jid or _select_allowlist_jid(
            allowlist_jids, args.suite, args.seed
        )
        if remote_jid not in allowlist_jids:
            raise SystemExit(
                f"livecheck-auto: remote-jid {remote_jid} not in allowlist; refusing to send"
            )
    else:
        remote_jid = None

    common = {
        "suite": args.suite,
        "case_ids": requested_case_ids,
        "client_slug": client_slug,
        "instance_id": instance_id,
        "branch_instance_id": branch_instance_id,
        "client_instance_id": client_meta.get("client_instance_id"),
        "instance_drift": instance_drift,
        "jid_mode": args.jid_mode,
        "remote_jid": remote_jid,
        "allowlist_jids": allowlist_jids,
        "test_mode": test_mode_enabled,
        "learning_mode": learning_env.get("learning_mode"),
        "qdrant_collection": learning_env.get("qdrant_collection_effective"),
    }

    context = {
        "rng": rng,
        "cases": selected_cases,
        "timestamp": timestamp,
        "base_url": base_url,
        "webhook_url": webhook_url,
        "webhook_secret": webhook_secret,
        "admin_token": admin_token,
        "instance_id": instance_id,
        "allowlist_jids": allowlist_jids,
        "remote_jid": remote_jid,
        "db_user": db_user,
        "client_slug": client_slug,
        "client_meta": client_meta,
        "learning_env": learning_env,
        "qdrant_env": qdrant_env,
        "container_name": container_name,
        "outbox_wait_seconds": _resolve_outbox_wait_seconds(container_name),
    }

    if args.suite in {
        "ca01-core",
        "ca02-policy",
        "ca03-info",
        "ca04-service",
        "ca05-booking",
        "ca06-consult",
        "ca07-ood",
    }:
        _ensure_bot_active_before_suite(args, context)

    reset_summary = None
    if args.suite == "ca06-consult":
        reset_summary = _run_livecheck_ca06_reset(args, context)

    if args.suite == "ca08-state":
        summary = _run_livecheck_ca08_state(args, context)
        summary.update(common)
        print(json.dumps({"summary": summary}, ensure_ascii=False))
        return
    if args.suite == "ca05-booking":
        summary = _run_livecheck_ca05_booking(args, context)
        summary.update(common)
        print(json.dumps({"summary": summary}, ensure_ascii=False))
        return
    if args.suite == "ca09-manager":
        summary = _run_livecheck_ca09_manager(args, context)
        summary.update(common)
        print(json.dumps({"summary": summary}, ensure_ascii=False))
        if not args.dry_run and summary.get("qdrant_found") is not True:
            error_note = summary.get("qdrant_error") or "qdrant evidence missing"
            raise SystemExit(f"livecheck-auto: CA09 {error_note}")
        return
    if args.suite == "ca10-outbox":
        summary = _run_livecheck_ca10_outbox(args, context)
        summary.update(common)
        print(json.dumps({"summary": summary}, ensure_ascii=False))
        return

    results = []

    for idx, case in enumerate(selected_cases, start=1):
        text, marker, message = _build_livecheck_message(
            rng, case, f"LC:AUTO:{args.suite}", timestamp, idx, args.noise
        )
        message_id = f"LC-AUTO-{timestamp}-{idx:02d}-{uuid.uuid4().hex[:8]}"
        sent_at = datetime.now(timezone.utc).isoformat()
        if args.jid_mode == "unique":
            remote_jid = _logic_jid_for_index(idx)
        if remote_jid not in allowlist_jids:
            raise SystemExit(
                f"livecheck-auto: remote-jid {remote_jid} not in allowlist; refusing to send"
            )
        metadata = {
            "sender": "LivecheckAuto",
            "timestamp": int(time.time()),
            "messageId": message_id,
            "remoteJid": remote_jid,
        }
        if instance_id:
            metadata["instanceId"] = instance_id
        payload = {
            "body": {
                "messageType": "text",
                "message": message,
                "metadata": metadata,
            }
        }
        status = "dry_run"
        response_status = None
        response_body = None
        response_error = None
        if not args.dry_run:
            response_status, response_body, response_error = _send_webhook_payload(
                webhook_url, payload, webhook_secret, args.timeout
            )
            status = "sent" if response_status and 200 <= response_status < 300 else "error"
        log = {
            "case_id": case["case_id"],
            "marker": marker,
            "message_id": message_id,
            "remote_jid": remote_jid,
            "text": message,
            "sent_at": sent_at,
            "expected_policy_section": case.get("expected_policy_section"),
            "status": status,
            "http_status": response_status,
        }
        if case.get("expected_info_sections"):
            log["expected_info_sections"] = case.get("expected_info_sections")
        if case.get("expected_fact_intents"):
            log["expected_fact_intents"] = case.get("expected_fact_intents")
        if case.get("expected_info_combined") is not None:
            log["expected_info_combined"] = case.get("expected_info_combined")
        if case.get("expected_action"):
            log["expected_action"] = case.get("expected_action")
        if case.get("expected_intent"):
            log["expected_intent"] = case.get("expected_intent")
        if case.get("expected_source_any"):
            log["expected_source_any"] = case.get("expected_source_any")
        if case.get("expected_trace_stage_any"):
            log["expected_trace_stage_any"] = case.get("expected_trace_stage_any")
        if case.get("expected_trace_decision_any"):
            log["expected_trace_decision_any"] = case.get("expected_trace_decision_any")
        if case.get("expected_llm_used") is not None:
            log["expected_llm_used"] = case.get("expected_llm_used")
        if response_error:
            log["error"] = response_error
        if response_body:
            log["response"] = response_body[:200]
        print(json.dumps(log, ensure_ascii=False))

        if not args.dry_run:
            outbox_url = f"{base_url}/admin/outbox/process"
            _post_admin_outbox(outbox_url, admin_token, args.timeout)
            conv_id, meta, error = _poll_decision_meta(
                db_user, message_id, args.poll_timeout, args.poll_interval
            )
            if error:
                raise SystemExit(f"livecheck-auto: decision_meta poll failed ({error})")

            ack_marker = f"LC:ACK:{case['case_id']}:{timestamp}:{idx:02d}"
            ack_message_id = f"LC-ACK-{timestamp}-{idx:02d}-{uuid.uuid4().hex[:8]}"
            ack_text = args.ack_text or "ок"
            ack_payload = {
                "body": {
                    "messageType": "text",
                    "message": ack_text,
                    "metadata": {
                        "sender": "LivecheckAuto",
                        "timestamp": int(time.time()),
                        "messageId": ack_message_id,
                        "remoteJid": remote_jid,
                    },
                }
            }
            if instance_id:
                ack_payload["body"]["metadata"]["instanceId"] = instance_id
            ack_status, _, ack_error = _send_webhook_payload(
                webhook_url, ack_payload, webhook_secret, args.timeout
            )
            if ack_error:
                raise SystemExit(f"livecheck-auto: ACK failed ({ack_error})")
            _post_admin_outbox(outbox_url, admin_token, args.timeout)

            policy_pack_missing = (meta or {}).get("policy_pack_missing")
            if policy_pack_missing:
                raise SystemExit("livecheck-auto: policy_pack_missing=true")

            expected_sections = case.get("expected_info_sections") or []
            expected_fact_intents = case.get("expected_fact_intents") or []
            expected_info_combined = case.get("expected_info_combined")
            if args.suite == "ca03-info":
                fact_source = (meta or {}).get("fact_source")
                if fact_source != "truth":
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} fact_source mismatch ({fact_source})"
                    )
                if (meta or {}).get("llm_used") is not False:
                    raise SystemExit(f"livecheck-auto: CA03 {case['case_id']} llm_used not false")
                if (meta or {}).get("source") not in {"truth_gate", "class_router"}:
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} source mismatch"
                    )
                info_sections = (meta or {}).get("info_sections")
                if expected_sections:
                    if not isinstance(info_sections, list) or any(
                        item not in info_sections for item in expected_sections
                    ):
                        raise SystemExit(
                            f"livecheck-auto: CA03 {case['case_id']} info_sections mismatch"
                        )
                fact_intents = (meta or {}).get("fact_intents")
                if expected_fact_intents:
                    if not isinstance(fact_intents, list) or any(
                        item not in fact_intents for item in expected_fact_intents
                    ):
                        raise SystemExit(
                            f"livecheck-auto: CA03 {case['case_id']} fact_intents mismatch"
                        )
                if expected_info_combined is True and (meta or {}).get("info_combined") is not True:
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} info_combined mismatch"
                    )

            if args.suite == "ca04-service":
                expected_intent = case.get("expected_intent")
                if (meta or {}).get("action") != "reply":
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} action mismatch")
                if (meta or {}).get("intent") != expected_intent:
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} intent mismatch")
                if (meta or {}).get("fact_source") != "service_matcher":
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} fact_source mismatch")
                if (meta or {}).get("source") != "service_matcher":
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} source mismatch")
                if (meta or {}).get("llm_used") is not False:
                    raise SystemExit(f"livecheck-auto: CA04 {case['case_id']} llm_used not false")
                fact_intents = (meta or {}).get("fact_intents")
                if expected_fact_intents:
                    if not isinstance(fact_intents, list) or any(
                        item not in fact_intents for item in expected_fact_intents
                    ):
                        raise SystemExit(
                            f"livecheck-auto: CA04 {case['case_id']} fact_intents mismatch"
                        )

            if args.suite == "ca06-consult":
                expected_source = case.get("expected_source")
                if expected_source and (meta or {}).get("source") != expected_source:
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} source mismatch"
                    )
                expected_meta_playbook = case.get("expected_meta_consult_playbook_id")
                if expected_meta_playbook and (
                    (meta or {}).get("consult_playbook_id") != expected_meta_playbook
                ):
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} consult_playbook_id mismatch"
                    )
                expected_fact_sources = case.get("expected_fact_source_any") or []
                if expected_fact_sources:
                    fact_source = (meta or {}).get("fact_source")
                    if fact_source not in expected_fact_sources:
                        raise SystemExit(
                            f"livecheck-auto: CA06 {case['case_id']} fact_source mismatch"
                        )
                expected_llm = case.get("expected_llm_used")
                if expected_llm is not None and (meta or {}).get("llm_used") is not expected_llm:
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} llm_used mismatch"
                    )

            if args.suite == "ca07-ood":
                expected_action = case.get("expected_action")
                if expected_action and (meta or {}).get("action") != expected_action:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} action mismatch"
                    )
                expected_intent = case.get("expected_intent")
                if expected_intent and (meta or {}).get("intent") != expected_intent:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} intent mismatch"
                    )
                expected_sources = case.get("expected_source_any") or []
                if expected_sources and (meta or {}).get("source") not in expected_sources:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} source mismatch"
                    )
                expected_llm = case.get("expected_llm_used")
                if expected_llm is not None and (meta or {}).get("llm_used") is not expected_llm:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} llm_used mismatch"
                    )

            conv_meta = None
            conv_error = None
            trace_entry = None
            info_trace = None
            consult_trace = None
            trace_source = None
            if conv_id:
                conv_meta, conv_error = _fetch_conversation_meta(db_user, conv_id)
                trace_list = None
                if conv_meta and isinstance(conv_meta.get("context"), dict):
                    trace_list = conv_meta.get("context", {}).get("decision_trace")
                if (meta or {}).get("policy_gate") or case.get("expected_policy_section"):
                    trace_entry = _find_trace_entry(
                        trace_list,
                        stage="policy_gate",
                        policy_gate=(meta or {}).get("policy_gate"),
                        policy_section=(meta or {}).get("policy_section")
                        or case.get("expected_policy_section"),
                    )
                if args.suite == "ca03-info":
                    for entry in reversed(_trace_as_list(trace_list)):
                        if entry.get("stage") in {"truth_gate", "info_class"}:
                            info_trace = entry
                            break
                if args.suite == "ca04-service":
                    for entry in reversed(_trace_as_list(trace_list)):
                        if entry.get("stage") == "service_matcher":
                            info_trace = entry
                            break
                if args.suite == "ca06-consult":
                    for entry in reversed(_trace_as_list(trace_list)):
                        if entry.get("stage") == "consult_flow":
                            consult_trace = entry
                            break
                if args.suite == "ca07-ood":
                    for entry in reversed(_trace_as_list(trace_list)):
                        if entry.get("stage") in {"out_of_domain", "fast_intent", "smalltalk"}:
                            info_trace = entry
                            break

            if args.suite == "ca03-info":
                if not info_trace:
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} missing truth_gate/info_class trace"
                    )
                if info_trace.get("stage") == "truth_gate":
                    trace_source = "truth_gate"
                else:
                    trace_source = "class_router"
                if trace_source not in {"truth_gate", "class_router"}:
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} trace_source mismatch"
                    )
                if info_trace.get("fact_source") != "truth":
                    raise SystemExit(
                        f"livecheck-auto: CA03 {case['case_id']} trace fact_source mismatch"
                    )

            if args.suite == "ca04-service":
                if not info_trace:
                    raise SystemExit(
                        f"livecheck-auto: CA04 {case['case_id']} missing service_matcher trace"
                    )
                if info_trace.get("decision") != case.get("expected_intent"):
                    raise SystemExit(
                        f"livecheck-auto: CA04 {case['case_id']} trace decision mismatch"
                    )
                if info_trace.get("fact_source") != "service_matcher":
                    raise SystemExit(
                        f"livecheck-auto: CA04 {case['case_id']} trace fact_source mismatch"
                    )

            if args.suite == "ca06-consult":
                if not consult_trace:
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} missing consult_flow trace"
                    )
                expected_decision = case.get("expected_consult_decision")
                if expected_decision and consult_trace.get("decision") != expected_decision:
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} consult_flow decision mismatch"
                    )
                expected_trace_playbook = case.get("expected_consult_playbook_id")
                if expected_trace_playbook and (
                    consult_trace.get("consult_playbook_id") != expected_trace_playbook
                ):
                    raise SystemExit(
                        f"livecheck-auto: CA06 {case['case_id']} consult_flow playbook mismatch"
                    )

            if args.suite == "ca07-ood":
                if not info_trace:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} missing guard trace"
                    )
                expected_stages = case.get("expected_trace_stage_any") or []
                if expected_stages and info_trace.get("stage") not in expected_stages:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} trace stage mismatch"
                    )
                expected_decisions = case.get("expected_trace_decision_any") or []
                if expected_decisions and info_trace.get("decision") not in expected_decisions:
                    raise SystemExit(
                        f"livecheck-auto: CA07 {case['case_id']} trace decision mismatch"
                    )

            results.append(
                {
                    "case_id": case["case_id"],
                    "message_id": message_id,
                    "conversation_id": conv_id,
                    "remote_jid": remote_jid,
                    "action": (meta or {}).get("action"),
                    "intent": (meta or {}).get("intent"),
                    "policy_gate": (meta or {}).get("policy_gate"),
                    "policy_section": (meta or {}).get("policy_section"),
                    "policy_source": (meta or {}).get("source"),
                    "risk_level": (meta or {}).get("risk_level"),
                    "policy_pack_missing": policy_pack_missing,
                    "llm_used": (meta or {}).get("llm_used"),
                    "fact_source": (meta or {}).get("fact_source"),
                    "info_sections": (meta or {}).get("info_sections"),
                    "info_combined": (meta or {}).get("info_combined"),
                    "fact_intents": (meta or {}).get("fact_intents"),
                    "service_query": (meta or {}).get("service_query"),
                    "consult_playbook_id": (meta or {}).get("consult_playbook_id"),
                    "consult_topic": (meta or {}).get("consult_topic"),
                    "consult_variant_id": (meta or {}).get("consult_variant_id"),
                    "source": (meta or {}).get("source"),
                    "ack_message_id": ack_message_id,
                    "ack_marker": ack_marker,
                    "ack_text": ack_text,
                    "ack_status": ack_status,
                    "trace_policy_type": (trace_entry or {}).get("policy_type") if trace_entry else None,
                    "trace_source": (trace_entry or {}).get("source") if trace_entry else None,
                    "trace_policy_gate": (trace_entry or {}).get("policy_gate") if trace_entry else None,
                    "trace_policy_section": (trace_entry or {}).get("policy_section") if trace_entry else None,
                    "trace_risk_level": (trace_entry or {}).get("risk_level") if trace_entry else None,
                    "trace_stage": (info_trace or {}).get("stage") if info_trace else None,
                    "trace_decision": (info_trace or {}).get("decision") if info_trace else None,
                    "trace_source": trace_source,
                    "trace_fact_source": (info_trace or {}).get("fact_source") if info_trace else None,
                    "trace_info_sections": (info_trace or {}).get("info_sections") if info_trace else None,
                    "trace_intents": (info_trace or {}).get("intents") if info_trace else None,
                    "trace_consult_decision": (consult_trace or {}).get("decision") if consult_trace else None,
                    "trace_consult_playbook_id": (consult_trace or {}).get("consult_playbook_id")
                    if consult_trace
                    else None,
                    "trace_error": conv_error,
                }
            )

        if idx < len(selected_cases):
            time.sleep(rng.uniform(min_wait, max_wait))

    summary = dict(common)
    summary["results"] = results
    if reset_summary:
        summary["reset"] = reset_summary
    print(json.dumps({"summary": summary}, ensure_ascii=False))

def _run_livecheck(args):
    suite = LIVECHECK_SUITES.get(args.suite)
    if not suite:
        raise SystemExit(f"Unknown suite: {args.suite}")
    token = os.environ.get("CHATFLOW_TOKEN")
    instance_id = os.environ.get("CHATFLOW_INSTANCE_ID")
    jid = os.environ.get("CHATFLOW_JID")
    api_url = os.environ.get("CHATFLOW_API_URL", "https://app.chatflow.kz/api/v1/send-text")
    timeout = float(os.environ.get("CHATFLOW_TIMEOUT_SECONDS", "30"))
    if not token or not instance_id or not jid:
        raise SystemExit("Missing CHATFLOW_TOKEN/CHATFLOW_INSTANCE_ID/CHATFLOW_JID in env.")

    rng = random.Random(args.seed or int(time.time()))
    min_wait = min(args.min_wait, args.max_wait)
    max_wait = max(args.min_wait, args.max_wait)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    for idx, case in enumerate(suite, start=1):
        base_text = rng.choice(case["messages"])
        text = _apply_noise(base_text, rng, args.noise)
        marker = f"LC:{args.suite}:{case['case_id']}:{timestamp}:{idx:02d}"
        message = f"{text} [{marker}]"
        sent_at = datetime.now(timezone.utc).isoformat()
        status = "dry_run"
        response_body = None
        response_status = None
        if not args.dry_run:
            response_status, response_body = _send_chatflow_message(
                api_url, token, instance_id, jid, message, timeout
            )
            status = "sent" if response_status == 200 else "error"
        log = {
            "case_id": case["case_id"],
            "marker": marker,
            "text": message,
            "sent_at": sent_at,
            "expected_policy_section": case["expected_policy_section"],
            "status": status,
            "http_status": response_status,
        }
        if response_body:
            log["response"] = response_body[:200]
        print(json.dumps(log, ensure_ascii=False))
        if idx < len(suite):
            time.sleep(rng.uniform(min_wait, max_wait))


def _parse_deploy_verify_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py deploy-verify",
        description="Verify deployed build via /admin/version.",
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--expected-commit", default=None)
    parser.add_argument("--expected-version", default=None)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--retries", type=int, default=10)
    parser.add_argument("--sleep", type=float, default=1.0)
    return parser.parse_args(argv)


def _fetch_json(url, timeout):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)


def _run_deploy_verify(args):
    url = args.base_url.rstrip("/") + "/admin/version"
    last_error = None
    payload = None
    for _ in range(max(args.retries, 1)):
        try:
            payload = _fetch_json(url, args.timeout)
            break
        except Exception as exc:
            last_error = str(exc)
            time.sleep(max(args.sleep, 0))

    if not isinstance(payload, dict):
        raise SystemExit(f"deploy-verify failed: no response from {url}. last_error={last_error}")

    version = payload.get("version") or ""
    git_commit = payload.get("git_commit") or ""

    if not version or version == "unknown":
        raise SystemExit("deploy-verify failed: version unknown")
    if args.expected_commit and git_commit != args.expected_commit:
        raise SystemExit(
            f"deploy-verify failed: git_commit mismatch (expected {args.expected_commit}, got {git_commit})"
        )
    if args.expected_version and version != args.expected_version:
        raise SystemExit(
            f"deploy-verify failed: version mismatch (expected {args.expected_version}, got {version})"
        )

    print(
        json.dumps(
            {"ok": True, "version": version, "git_commit": git_commit, "url": url},
            ensure_ascii=False,
        )
    )

def _parse_emit_evidence_args(argv):
    parser = argparse.ArgumentParser(
        prog="ops/diagnose.py emit-evidence",
        description="Generate markdown evidence from livecheck jsonl artifacts.",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Path/glob to livecheck jsonl file (repeatable).",
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Directory containing livecheck-*.jsonl artifacts.",
    )
    parser.add_argument("--gate", default=None, help="Path to livecheck-gate.txt.")
    parser.add_argument(
        "--output",
        default="livecheck-evidence.md",
        help="Markdown output path (use '-' for stdout).",
    )
    parser.add_argument("--title", default="Livecheck Evidence")
    parser.add_argument(
        "--suite-order",
        default=None,
        help="Comma-separated suite order (default: alphabetical).",
    )
    return parser.parse_args(argv)

def _resolve_emit_inputs(inputs, input_dir):
    paths = []
    if input_dir:
        paths.extend(sorted(glob.glob(os.path.join(input_dir, "livecheck-*.jsonl"))))
    for raw in inputs or []:
        if not raw:
            continue
        if os.path.isdir(raw):
            paths.extend(sorted(glob.glob(os.path.join(raw, "livecheck-*.jsonl"))))
            continue
        expanded = glob.glob(raw)
        if expanded:
            paths.extend(sorted(expanded))
        else:
            paths.append(raw)
    seen = set()
    resolved = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        resolved.append(path)
    if not resolved:
        raise SystemExit("emit-evidence: no jsonl inputs found")
    return resolved

def _resolve_gate_path(gate_path, input_dir):
    if gate_path:
        return gate_path
    if input_dir:
        direct = os.path.join(input_dir, "livecheck-gate.txt")
        if os.path.isfile(direct):
            return direct
        matches = sorted(glob.glob(os.path.join(input_dir, "livecheck-gate-*.txt")))
        if matches:
            return matches[0]
    return None

def _read_gate_file(path):
    if not path or not os.path.isfile(path):
        return None
    values = {}
    flags = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value
            else:
                flags.append(line)
    return {"path": path, "values": values, "flags": flags}

def _load_jsonl_entries(path):
    entries = []
    errors = []
    with open(path, "r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except Exception as exc:
                errors.append({"line": idx, "error": str(exc), "raw": raw[:200]})
    return entries, errors

def _extract_summary(entries):
    summary = None
    for entry in entries:
        if isinstance(entry, dict) and "summary" in entry:
            summary = entry.get("summary")
    return summary

def _extract_case_logs(entries):
    logs = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if "summary" in entry:
            continue
        if entry.get("case_id"):
            logs.append(entry)
    return logs

def _suite_name_from_path(path, summary):
    if isinstance(summary, dict):
        suite = summary.get("suite")
        if suite:
            return suite
    base = os.path.basename(path)
    if base.startswith("livecheck-") and base.endswith(".jsonl"):
        return base[len("livecheck-") : -len(".jsonl")]
    return os.path.splitext(base)[0]

def _format_cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)

def _escape_table(value):
    return _format_cell(value).replace("|", "\\|").replace("\n", " ").strip()

def _render_table(columns, rows):
    lines = []
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    lines.append(header)
    lines.append(sep)
    for row in rows:
        values = []
        for _, key in columns:
            values.append(_escape_table(row.get(key)))
        lines.append("| " + " | ".join(values) + " |")
    return lines

def _compact_errors(errors):
    if not isinstance(errors, dict):
        return None
    present = {key: value for key, value in errors.items() if value}
    if not present:
        return None
    return json.dumps(present, ensure_ascii=False)

def _render_suite_summary(lines, summary):
    if not isinstance(summary, dict):
        lines.append("- summary: missing")
        return
    case_ids = summary.get("case_ids")
    if case_ids:
        lines.append(f"- case_ids: {', '.join(case_ids)}")
    for key in (
        "client_slug",
        "instance_id",
        "branch_instance_id",
        "client_instance_id",
        "instance_drift",
        "jid_mode",
        "remote_jid",
        "test_mode",
        "learning_mode",
        "qdrant_collection",
    ):
        value = summary.get(key)
        if value is None or value == "":
            continue
        lines.append(f"- {key}: `{_format_cell(value)}`")
    error_note = _compact_errors(summary.get("errors"))
    if error_note:
        lines.append(f"- errors: `{error_note}`")

def _render_suite_lines(suite):
    lines = [f"## Suite {suite['name']}", f"- input: `{suite['input']}`"]
    summary = suite.get("summary")
    _render_suite_summary(lines, summary)
    if not isinstance(summary, dict):
        if suite.get("case_logs"):
            lines.append("")
            columns = [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("marker", "marker"),
                ("status", "status"),
                ("http_status", "http_status"),
            ]
            lines.extend(_render_table(columns, suite["case_logs"]))
        return lines

    suite_name = suite["name"]
    results = summary.get("results")
    if suite_name == "ca05-booking" and isinstance(results, list):
        reset = summary.get("reset") or {}
        if reset:
            reset_parts = []
            for key in (
                "reset_message_id",
                "reset_action",
                "reset_intent",
                "reset_expected_reply_type",
                "reset_booking_active",
                "reset_booking_service",
            ):
                if key in reset and reset.get(key) is not None:
                    reset_parts.append(f"{key}={_format_cell(reset.get(key))}")
            if reset_parts:
                lines.append(f"- reset: {'; '.join(reset_parts)}")
        lines.append("")
        columns = [
            ("step", "step"),
            ("message_id", "message_id"),
            ("conversation_id", "conversation_id"),
            ("expected_reply_type", "expected_reply_type"),
            ("booking_service", "booking_service"),
            ("booking_info_interrupt", "booking_info_interrupt"),
            ("booking_info_intents", "booking_info_intents"),
            ("trace_booking_interrupt", "trace_booking_interrupt"),
            ("llm_used", "llm_used"),
        ]
        lines.extend(_render_table(columns, results))
        return lines

    if suite_name == "ca08-state":
        for key in ("message_id", "ack_message_id", "conversation_id"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        lines.append(
            f"- conversation_state: `{summary.get('conversation_state_before')}` → `{summary.get('conversation_state_after')}`"
        )
        lines.append(
            f"- handover_status: `{summary.get('handover_status_before')}` → `{summary.get('handover_status_after')}`"
        )
        for key in ("policy_gate", "action", "pending_action"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        lines.append(f"- pending_sla_trace: `{_format_cell(summary.get('pending_sla_trace'))}`")
        lines.append(f"- pending_resume_trace: `{_format_cell(summary.get('pending_resume_trace'))}`")
        return lines

    if suite_name == "ca09-manager":
        for key in ("message_id", "conversation_id"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        lines.append(
            f"- conversation_state: `{summary.get('conversation_state_before')}` → `{summary.get('conversation_state_after')}`"
        )
        lines.append(
            f"- handover_status: `{summary.get('handover_status_before')}` → `{summary.get('handover_status_after')}`"
        )
        for key in ("assigned_to", "first_response_at"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        lines.append(f"- qdrant_found: `{_format_cell(summary.get('qdrant_found'))}`")
        for key in ("outbox_status", "telegram_status"):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        return lines

    if suite_name == "ca10-outbox":
        for key in (
            "message_id",
            "message_count",
            "message_dedup_count",
            "outbox_count",
            "outbox_status",
        ):
            value = _format_cell(summary.get(key))
            if value:
                lines.append(f"- {key}: `{value}`")
        return lines

    if isinstance(results, list):
        suite_columns = {
            "ca01-core": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("policy_gate", "policy_gate"),
                ("policy_section", "policy_section"),
                ("risk_level", "risk_level"),
                ("llm_used", "llm_used"),
                ("trace_policy_gate", "trace_policy_gate"),
                ("trace_policy_section", "trace_policy_section"),
            ],
            "ca02-policy": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("policy_gate", "policy_gate"),
                ("policy_section", "policy_section"),
                ("risk_level", "risk_level"),
                ("llm_used", "llm_used"),
                ("trace_policy_type", "trace_policy_type"),
                ("trace_policy_gate", "trace_policy_gate"),
                ("trace_policy_section", "trace_policy_section"),
            ],
            "ca03-info": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("fact_source", "fact_source"),
                ("info_sections", "info_sections"),
                ("fact_intents", "fact_intents"),
                ("info_combined", "info_combined"),
                ("llm_used", "llm_used"),
                ("source", "source"),
                ("trace_stage", "trace_stage"),
                ("trace_fact_source", "trace_fact_source"),
                ("trace_info_sections", "trace_info_sections"),
            ],
            "ca04-service": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("fact_source", "fact_source"),
                ("fact_intents", "fact_intents"),
                ("service_query", "service_query"),
                ("llm_used", "llm_used"),
                ("trace_stage", "trace_stage"),
                ("trace_decision", "trace_decision"),
                ("trace_fact_source", "trace_fact_source"),
            ],
            "ca06-consult": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("consult_playbook_id", "consult_playbook_id"),
                ("source", "source"),
                ("fact_source", "fact_source"),
                ("llm_used", "llm_used"),
                ("trace_consult_decision", "trace_consult_decision"),
                ("trace_consult_playbook_id", "trace_consult_playbook_id"),
            ],
            "ca07-ood": [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
                ("action", "action"),
                ("intent", "intent"),
                ("source", "source"),
                ("llm_used", "llm_used"),
                ("trace_stage", "trace_stage"),
                ("trace_decision", "trace_decision"),
            ],
        }
        columns = suite_columns.get(
            suite_name,
            [
                ("case_id", "case_id"),
                ("message_id", "message_id"),
                ("conversation_id", "conversation_id"),
            ],
        )
        lines.append("")
        lines.extend(_render_table(columns, results))
    return lines

def _run_emit_evidence(args):
    inputs = _resolve_emit_inputs(args.input, args.input_dir)
    gate_path = _resolve_gate_path(args.gate, args.input_dir)
    gate = _read_gate_file(gate_path)

    suites = []
    for path in inputs:
        entries, parse_errors = _load_jsonl_entries(path)
        summary = _extract_summary(entries)
        suite_name = _suite_name_from_path(path, summary)
        suites.append(
            {
                "name": suite_name,
                "input": os.path.basename(path),
                "summary": summary,
                "case_logs": _extract_case_logs(entries),
                "parse_errors": parse_errors,
            }
        )

    if args.suite_order:
        ordered = []
        suite_map = {suite["name"]: suite for suite in suites}
        for name in _parse_csv_values(args.suite_order):
            suite = suite_map.pop(name, None)
            if suite:
                ordered.append(suite)
        for name in sorted(suite_map.keys()):
            ordered.append(suite_map[name])
        suites = ordered
    else:
        suites = sorted(suites, key=lambda item: item["name"])

    lines = [f"# {args.title}"]
    generated_at = datetime.now(timezone.utc).isoformat()
    lines.append(f"- generated_at: `{generated_at}`")
    lines.append(
        "- inputs: " + ", ".join(f"`{os.path.basename(path)}`" for path in inputs)
    )
    if gate:
        lines.append("")
        lines.append("## Gate")
        for key in sorted(gate.get("values", {}).keys()):
            value = gate["values"].get(key, "")
            lines.append(f"- {key}={value}")
        if gate.get("flags"):
            lines.append(f"- flags: {', '.join(gate['flags'])}")
        lines.append(f"- gate_file: `{os.path.basename(gate['path'])}`")
    else:
        lines.append("")
        lines.append("## Gate")
        lines.append("- gate_file: missing")

    for suite in suites:
        lines.append("")
        lines.extend(_render_suite_lines(suite))
        if suite.get("parse_errors"):
            lines.append(f"- parse_errors: `{json.dumps(suite['parse_errors'], ensure_ascii=False)}`")

    output = "\n".join(lines).rstrip() + "\n"
    if args.output == "-":
        print(output)
        return
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(output)
    print(json.dumps({"output": args.output, "suites": [s['name'] for s in suites]}, ensure_ascii=False))

def run_command(command):
    return subprocess.run(command, capture_output=True, text=True)

API_CONTAINER_HINT = "truffles-api"

def resolve_container_name():
    result = run_command(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"name={API_CONTAINER_HINT}",
            "--format",
            "{{.Names}}",
        ]
    )
    if result.returncode != 0:
        return None, result.stderr.strip()
    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not names:
        return None, ""
    if API_CONTAINER_HINT in names:
        return API_CONTAINER_HINT, ""
    return names[0], ""

def run_docker_exec(container_name, command):
    return run_command(["docker", "exec", "-i", container_name, "/bin/sh", "-lc", command])

def run_curl(url, headers=None):
    cmd = ["curl", "-s"]
    if headers:
        for key, value in headers.items():
            cmd.extend(["-H", f"{key}: {value}"])
    cmd.append(url)
    return run_command(cmd)

if len(sys.argv) > 1 and sys.argv[1] == "webhook-fuzz":
    _run_webhook_fuzz(_parse_webhook_fuzz_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "emit-evidence":
    _run_emit_evidence(_parse_emit_evidence_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "livecheck-auto":
    _run_livecheck_auto(_parse_livecheck_auto_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "livecheck":
    _run_livecheck(_parse_livecheck_args(sys.argv[2:]))
    raise SystemExit(0)
if len(sys.argv) > 1 and sys.argv[1] == "deploy-verify":
    _run_deploy_verify(_parse_deploy_verify_args(sys.argv[2:]))
    raise SystemExit(0)

print("=" * 60)
print("ДИАГНОСТИКА TRUFFLES")
print("=" * 60)

print("\n🔎 PRE-FLIGHT:")
print("-" * 40)
container_name, docker_error = resolve_container_name()
status = ""
if docker_error:
    print(f"docker error: {docker_error}")
    print("Skipping docker checks (no access).")
else:
    if container_name:
        print(f"truffles-api container: {container_name}")
        status_result = run_command(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name]
        )
        status = status_result.stdout.strip() if status_result.returncode == 0 else ""
        if status:
            print(f"truffles-api status: {status}")
        else:
            print("truffles-api status: UNKNOWN")
    else:
        print("truffles-api container: NOT FOUND (container missing?)")

if container_name:
    image_result = run_command(
        ["docker", "inspect", "--format", "{{.Config.Image}}", container_name]
    )
    if image_result.returncode == 0 and image_result.stdout.strip():
        print(f"truffles-api image: {image_result.stdout.strip()}")
    else:
        print("truffles-api image: UNKNOWN")
else:
    print("truffles-api image: UNKNOWN")

if status == "running":
    env_checks = [
        ("TEST_MODE", True),
        ("OUTBOUND_ALLOWLIST_JIDS", True),
        ("OUTBOX_WORKER_ENABLED", True),
        ("PUBLIC_BASE_URL", True),
        ("MEDIA_SIGNING_SECRET", False),
        ("MEDIA_URL_TTL_SECONDS", True),
        ("MEDIA_CLEANUP_TTL_DAYS", True),
        ("CHATFLOW_MEDIA_TIMEOUT_SECONDS", True),
        ("ALERTS_ADMIN_TOKEN", False),
    ]
    for name, show_value in env_checks:
        if show_value:
            cmd = (
                f'if [ -n "${name}" ]; then echo "{name}=${{{name}}}"; '
                f'else echo "{name}=MISSING"; fi'
            )
        else:
            cmd = (
                f'if [ -n "${name}" ]; then echo "{name}=SET"; '
                f'else echo "{name}=MISSING"; fi'
            )
        result = run_docker_exec(container_name, cmd)
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print(f"{name}=UNKNOWN (env check failed)")
else:
    print("Skipping env checks (truffles-api not running).")

# 1. Database state
print("\n📁 БАЗА ДАННЫХ:")
print("-" * 40)

# Conversations
def resolve_db_user():
    env_user = os.environ.get("DB_USER")
    if env_user:
        return env_user
    result = run_command(
        ["docker", "exec", "-i", "truffles_postgres_1", "/bin/sh", "-lc", "printf '%s' \"${POSTGRES_USER:-}\""]
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return "postgres"

db_user = resolve_db_user()
print(f"DB_USER={db_user}")

result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', db_user, '-d', 'chatbot', '-t', '-c',
     "SELECT COUNT(*) as total, COUNT(CASE WHEN bot_status='muted' THEN 1 END) as muted, COUNT(telegram_topic_id) as with_topic FROM conversations;"],
    capture_output=True, text=True
)
if result.returncode == 0:
    parts = result.stdout.strip().split('|')
    if len(parts) >= 3:
        print(f"Conversations: {parts[0].strip()} total, {parts[1].strip()} muted, {parts[2].strip()} with topic")

# Handovers
result = subprocess.run(
    ['docker', 'exec', '-i', 'truffles_postgres_1', 'psql', '-U', db_user, '-d', 'chatbot', '-t', '-c',
     "SELECT COUNT(*) as total, COUNT(CASE WHEN status='pending' THEN 1 END) as pending, COUNT(CASE WHEN status='active' THEN 1 END) as active FROM handovers;"],
    capture_output=True, text=True
)
if result.returncode == 0:
    parts = result.stdout.strip().split('|')
    if len(parts) >= 3:
        print(f"Handovers: {parts[0].strip()} total, {parts[1].strip()} pending, {parts[2].strip()} active")

print("\n📮 OUTBOX STATUS:")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT status, COUNT(*) FROM outbox_messages GROUP BY status;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🧩 DECISION_META (last 3):")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT metadata->'decision_meta' FROM messages ORDER BY created_at DESC LIMIT 3;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🧾 ПОСЛЕДНИЕ HANDOVERS:")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT created_at, status, conversation_id, channel_ref, telegram_message_id "
        "FROM handovers ORDER BY created_at DESC LIMIT 10;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🟡 PENDING/MANAGER_ACTIVE CONVERSATIONS:")
print("-" * 40)
result = subprocess.run(
    [
        'docker',
        'exec',
        '-i',
        'truffles_postgres_1',
        'psql',
        '-U',
        db_user,
        '-d',
        'chatbot',
        '-t',
        '-c',
        "SELECT id, state, telegram_topic_id, last_message_at "
        "FROM conversations WHERE state IN ('pending','manager_active') "
        "ORDER BY last_message_at DESC LIMIT 10;",
    ],
    capture_output=True,
    text=True,
)
if result.returncode == 0:
    print(result.stdout.strip())

print("\n🌐 ADMIN ENDPOINTS:")
print("-" * 40)
version_result = run_curl("http://localhost:8000/admin/version")
if version_result.returncode == 0 and version_result.stdout.strip():
    print(f"/admin/version: {version_result.stdout.strip()}")
else:
    print("/admin/version: FAILED")

health_result = run_curl("http://localhost:8000/admin/health")
if health_result.returncode == 0 and health_result.stdout.strip():
    print(f"/admin/health: {health_result.stdout.strip()}")
else:
    print("/admin/health: FAILED")

admin_token = ""
if container_name:
    token_result = run_docker_exec(
        container_name, 'printf "%s" "${ALERTS_ADMIN_TOKEN:-}"'
    )
    if token_result.returncode == 0:
        admin_token = token_result.stdout.strip()

if admin_token:
    metric_date = datetime.now(timezone.utc).date().isoformat()
    metrics_result = run_curl(
        f"http://localhost:8000/admin/metrics?client_slug=demo_salon&metric_date={metric_date}",
        headers={"X-Admin-Token": admin_token},
    )
    if metrics_result.returncode == 0 and metrics_result.stdout.strip():
        print(f"/admin/metrics: {metrics_result.stdout.strip()}")
    else:
        print("/admin/metrics: FAILED")
else:
    print("/admin/metrics: SKIPPED (ALERTS_ADMIN_TOKEN missing)")

print("\n" + "=" * 60)
