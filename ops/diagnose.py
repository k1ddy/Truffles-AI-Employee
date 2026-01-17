#!/usr/bin/env python3
"""
БЫСТРАЯ ДИАГНОСТИКА
Запуск: python3 ~/truffles-main/ops/diagnose.py

Показывает:
- Состояние conversations
- Состояние handovers
"""
import argparse
import json
import os
import random
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
SAFE_ALLOWLIST_JID = "77015705555@s.whatsapp.net"

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
    parser.add_argument("--jid-mode", choices=["unique", "allowlist"], default="unique")
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

def _resolve_env_from_container(container_name, var_name):
    if not container_name:
        return ""
    result = run_docker_exec(container_name, f'printf "%s" "${{{var_name}:-}}"')
    if result.returncode != 0:
        return ""
    return result.stdout.strip()

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
    test_mode_enabled = _resolve_test_mode(container_name)
    allowlist_jids = _resolve_allowlist_jids(args.allowlist_jids, container_name)
    if SAFE_ALLOWLIST_JID not in allowlist_jids or len(allowlist_jids) != 1:
        raise SystemExit(
            f"livecheck-auto: allowlist must contain only {SAFE_ALLOWLIST_JID} (got {allowlist_jids})"
        )
    if not test_mode_enabled:
        raise SystemExit("livecheck-auto: TEST_MODE disabled; refusing to run")

    webhook_secret = (
        args.webhook_secret
        or os.environ.get("WEBHOOK_SECRET")
        or os.environ.get("TRUFFLES_WEBHOOK_SECRET")
    )
    if not webhook_secret:
        raise SystemExit("livecheck-auto: missing webhook secret")

    admin_token = args.admin_token or os.environ.get("ALERTS_ADMIN_TOKEN")
    if not admin_token and container_name:
        admin_token = _resolve_env_from_container(container_name, "ALERTS_ADMIN_TOKEN")
    if not admin_token and not args.dry_run:
        raise SystemExit("livecheck-auto: missing admin token")

    instance_id = (
        args.instance_id
        or os.environ.get("CHATFLOW_INSTANCE_ID")
        or os.environ.get("INSTANCE_ID")
    )

    selected_cases, requested_case_ids = _select_cases(suite_cases, args.case_ids)
    if selected_cases is None:
        selected_cases = suite_cases
        requested_case_ids = [case["case_id"] for case in suite_cases]

    if args.jid_mode == "allowlist":
        remote_jid = args.remote_jid or allowlist_jids[0]
        if remote_jid not in allowlist_jids:
            raise SystemExit(
                f"livecheck-auto: remote-jid {remote_jid} not in allowlist; refusing to send"
            )
    else:
        remote_jid = None

    db_user = _resolve_db_user_simple()
    results = []

    for idx, case in enumerate(selected_cases, start=1):
        base_text = rng.choice(case["messages"])
        text = _apply_noise(base_text, rng, args.noise)
        marker = f"LC:AUTO:{args.suite}:{case['case_id']}:{timestamp}:{idx:02d}"
        message = f"{text} [{marker}]"
        message_id = f"LC-AUTO-{timestamp}-{idx:02d}-{uuid.uuid4().hex[:8]}"
        sent_at = datetime.now(timezone.utc).isoformat()
        if args.jid_mode == "unique":
            remote_jid = _logic_jid_for_index(idx)
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
            "expected_policy_section": case["expected_policy_section"],
            "status": status,
            "http_status": response_status,
        }
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
            ack_payload = {
                "body": {
                    "messageType": "text",
                    "message": f"{args.ack_text} [{ack_marker}]",
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
            ack_status, ack_body, ack_error = _send_webhook_payload(
                webhook_url, ack_payload, webhook_secret, args.timeout
            )
            if ack_error:
                raise SystemExit(f"livecheck-auto: ACK failed ({ack_error})")
            _post_admin_outbox(outbox_url, admin_token, args.timeout)

            results.append(
                {
                    "case_id": case["case_id"],
                    "message_id": message_id,
                    "conversation_id": conv_id,
                    "remote_jid": remote_jid,
                    "action": (meta or {}).get("action"),
                    "policy_gate": (meta or {}).get("policy_gate"),
                    "policy_section": (meta or {}).get("policy_section"),
                    "llm_used": (meta or {}).get("llm_used"),
                    "ack_message_id": ack_message_id,
                    "ack_status": ack_status,
                }
            )

        if idx < len(selected_cases):
            time.sleep(rng.uniform(min_wait, max_wait))

    summary = {
        "suite": args.suite,
        "case_ids": requested_case_ids,
        "jid_mode": args.jid_mode,
        "allowlist_jids": allowlist_jids,
        "test_mode": test_mode_enabled,
        "results": results,
    }
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
