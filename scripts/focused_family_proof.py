#!/usr/bin/env python3
"""Canonical cheap focused live proof runner for exact-family dialogs."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

DEFAULT_BASE_URL = "http://127.0.0.1:18189"
DEFAULT_CLIENT_SLUG = "demo_salon"
DEFAULT_DB_CONTAINER = "truffles_postgres_1"
DEFAULT_DB_NAME = "chatbot"
DEFAULT_SENDER = "focused_family_proof"
DEFAULT_ORIGIN_SOURCE = "focused_family_proof"


@dataclass(frozen=True)
class RuntimeFingerprint:
    endpoint: str
    expected_commit: str | None
    runtime_commit: str | None
    runtime_version: str | None
    runtime_build_time: str | None
    valid: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeClientContext:
    client_id: str
    client_slug: str
    branch_id: str | None
    branch_slug: str | None
    instance_id: str | None
    webhook_secret: str | None
    webhook_secret_source: str | None


def runtime_fingerprint_payload(fingerprint: RuntimeFingerprint) -> dict[str, Any]:
    return {
        "endpoint": fingerprint.endpoint,
        "expected_commit": fingerprint.expected_commit,
        "runtime_commit": fingerprint.runtime_commit,
        "runtime_version": fingerprint.runtime_version,
        "runtime_build_time": fingerprint.runtime_build_time,
        "valid": fingerprint.valid,
        "reasons": list(fingerprint.reasons),
    }


def format_runtime_fingerprint_failure(fingerprint: RuntimeFingerprint) -> str:
    return (
        "focused-family-proof: runtime fingerprint failed "
        f"(endpoint={fingerprint.endpoint}, "
        f"expected_commit={fingerprint.expected_commit or 'unknown'}, "
        f"runtime_commit={fingerprint.runtime_commit or 'unknown'}, "
        f"reasons={','.join(fingerprint.reasons) or 'unknown'})"
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _clean_git_commit(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().strip('"').strip("'")
    if not cleaned:
        return None
    if cleaned.casefold() in {"unknown", "none", "null", "n/a", "na"}:
        return None
    return cleaned.lower()


def _resolve_expected_commit(explicit: str | None = None) -> str | None:
    explicit_clean = _clean_git_commit(explicit)
    if explicit_clean:
        return explicit_clean
    result = subprocess.run(
        ["git", "-C", str(_repo_root()), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=5.0,
        check=False,
    )
    if result.returncode != 0:
        return None
    return _clean_git_commit(result.stdout)


def _fingerprint_secret(secret: str | None) -> str | None:
    if not secret:
        return None
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:10]}"


def _fetch_json(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=max(1.0, float(timeout))) as response:
        body = response.read().decode("utf-8", errors="replace")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object from {url}")
    return payload


def validate_runtime_fingerprint(
    *,
    base_url: str,
    expected_commit: str | None,
    timeout: float,
) -> RuntimeFingerprint:
    endpoint = f"{base_url.rstrip('/')}/admin/version"
    reasons: list[str] = []
    payload: dict[str, Any] | None = None
    runtime_error = None
    try:
        payload = _fetch_json(endpoint, timeout)
    except Exception as exc:  # pragma: no cover - exercised in live path
        runtime_error = f"{exc.__class__.__name__}:{exc}"
    runtime_commit = _clean_git_commit(payload.get("git_commit") if isinstance(payload, dict) else None)
    runtime_version = payload.get("version") if isinstance(payload, dict) else None
    runtime_build_time = payload.get("build_time") if isinstance(payload, dict) else None
    expected_value = _clean_git_commit(expected_commit)
    if runtime_error:
        reasons.append("admin_version_unreachable")
    if not expected_value:
        reasons.append("expected_commit_missing")
    if not runtime_commit and not runtime_error:
        reasons.append("runtime_commit_missing")
    if expected_value and runtime_commit and expected_value != runtime_commit:
        reasons.append("git_commit_mismatch")
    return RuntimeFingerprint(
        endpoint=endpoint,
        expected_commit=expected_value,
        runtime_commit=runtime_commit,
        runtime_version=str(runtime_version).strip() if isinstance(runtime_version, str) and runtime_version.strip() else None,
        runtime_build_time=(
            str(runtime_build_time).strip()
            if isinstance(runtime_build_time, str) and runtime_build_time.strip()
            else None
        ),
        valid=not reasons,
        reasons=tuple(reasons if runtime_error is None else [*reasons, runtime_error]),
    )


def _escape_sql_literal(value: Any) -> str:
    return str(value).replace("'", "''")


def _run_command(args: Sequence[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        timeout=max(1.0, float(timeout)),
        check=False,
    )


def _resolve_db_user(*, explicit: str | None, db_container: str, timeout: float) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    env_user = os.environ.get("DB_USER")
    if env_user and env_user.strip():
        return env_user.strip()
    result = _run_command(
        [
            "docker",
            "exec",
            "-i",
            db_container,
            "/bin/sh",
            "-lc",
            "printf '%s' \"${POSTGRES_USER:-}\"",
        ],
        timeout=timeout,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return "postgres"


def _run_psql_json_query(
    *,
    db_container: str,
    db_name: str,
    db_user: str,
    query: str,
    timeout: float,
) -> dict[str, Any] | None:
    result = _run_command(
        [
            "docker",
            "exec",
            "-i",
            db_container,
            "psql",
            "-U",
            db_user,
            "-d",
            db_name,
            "-t",
            "-A",
            "-c",
            query,
        ],
        timeout=timeout,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "psql query failed"
        raise RuntimeError(stderr)
    text = result.stdout.strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"psql JSON parse failed: {exc}") from exc
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise RuntimeError("psql query returned non-object JSON")
    return payload


def _build_client_query(
    *,
    client_slug: str,
    branch_slug: str | None,
    branch_id: str | None,
    instance_id: str | None,
) -> str:
    where_clauses = ["c.name = '{client_slug}'".format(client_slug=_escape_sql_literal(client_slug))]
    branch_filters: list[str] = ["b.client_id = c.id", "b.is_active = TRUE"]
    if branch_slug:
        branch_filters.append("b.slug = '{slug}'".format(slug=_escape_sql_literal(branch_slug)))
    if branch_id:
        branch_filters.append("b.id = '{branch_id}'".format(branch_id=_escape_sql_literal(branch_id)))
    if instance_id:
        branch_filters.append(
            "COALESCE(b.instance_id, '') = '{instance_id}'".format(
                instance_id=_escape_sql_literal(instance_id)
            )
        )
    branch_where = " AND ".join(branch_filters)
    return (
        "SELECT json_build_object("
        "'client_id', c.id, "
        "'client_slug', c.name, "
        "'branch_id', branch_row.id, "
        "'branch_slug', branch_row.slug, "
        "'instance_id', COALESCE(branch_row.instance_id, c.config->>'instance_id'), "
        "'branch_webhook_secret', branch_row.webhook_secret, "
        "'client_webhook_secret', cs.webhook_secret"
        ") "
        "FROM clients c "
        "LEFT JOIN client_settings cs ON cs.client_id = c.id "
        "LEFT JOIN LATERAL ("
        "  SELECT b.id, b.slug, b.instance_id, b.webhook_secret "
        "  FROM branches b "
        f" WHERE {branch_where} "
        "  ORDER BY "
        "    CASE WHEN b.instance_id IS NULL OR b.instance_id = '' THEN 1 ELSE 0 END ASC, "
        "    b.updated_at DESC NULLS LAST, "
        "    b.created_at DESC NULLS LAST, "
        "    b.id ASC "
        "  LIMIT 1"
        ") AS branch_row ON TRUE "
        f"WHERE {' AND '.join(where_clauses)} "
        "LIMIT 1;"
    )


def resolve_runtime_client_context(
    *,
    client_slug: str,
    db_container: str,
    db_name: str,
    db_user: str,
    timeout: float,
    branch_slug: str | None,
    branch_id: str | None,
    instance_id: str | None,
) -> RuntimeClientContext:
    query = _build_client_query(
        client_slug=client_slug,
        branch_slug=branch_slug,
        branch_id=branch_id,
        instance_id=instance_id,
    )
    payload = _run_psql_json_query(
        db_container=db_container,
        db_name=db_name,
        db_user=db_user,
        query=query,
        timeout=timeout,
    )
    if not isinstance(payload, dict) or not payload.get("client_id"):
        raise SystemExit(f"focused-family-proof: client context not found for {client_slug}")
    branch_secret = str(payload.get("branch_webhook_secret") or "").strip() or None
    client_secret = str(payload.get("client_webhook_secret") or "").strip() or None
    return RuntimeClientContext(
        client_id=str(payload["client_id"]),
        client_slug=str(payload.get("client_slug") or client_slug),
        branch_id=str(payload["branch_id"]) if payload.get("branch_id") else None,
        branch_slug=str(payload["branch_slug"]) if payload.get("branch_slug") else None,
        instance_id=str(payload["instance_id"]) if payload.get("instance_id") else None,
        webhook_secret=branch_secret or client_secret,
        webhook_secret_source="branch" if branch_secret else ("client" if client_secret else None),
    )


def build_turn_payload(
    *,
    message: str,
    context: RuntimeClientContext,
    remote_jid: str,
    message_id: str,
    sender: str,
    timestamp: int,
    origin_source: str = DEFAULT_ORIGIN_SOURCE,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "sender": sender,
        "timestamp": timestamp,
        "messageId": message_id,
        "remoteJid": remote_jid,
    }
    if context.instance_id:
        metadata["instanceId"] = context.instance_id
    tenant_context: dict[str, Any] = {
        "client_id": context.client_id,
        "client_slug": context.client_slug,
        "source": "webhook",
        "origin_source": origin_source,
    }
    if context.branch_id:
        tenant_context["branch_id"] = context.branch_id
    if context.branch_slug:
        tenant_context["branch_slug"] = context.branch_slug
    if context.instance_id:
        tenant_context["instance_id"] = context.instance_id
    return {
        "client_slug": context.client_slug,
        "body": {
            "messageType": "text",
            "message": message,
            "metadata": metadata,
        },
        "tenant_context": tenant_context,
    }


def _send_webhook_payload(
    *,
    base_url: str,
    client_slug: str,
    payload: dict[str, Any],
    webhook_secret: str | None,
    timeout: float,
) -> tuple[int | None, dict[str, Any] | None, str | None]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/webhook/{client_slug}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    if webhook_secret:
        request.add_header("X-Webhook-Secret", webhook_secret)
    try:
        with urllib.request.urlopen(request, timeout=max(1.0, float(timeout))) as response:
            body = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(body) if body.strip() else {}
            if parsed and not isinstance(parsed, dict):
                raise ValueError("webhook response is not a JSON object")
            return response.status, parsed if isinstance(parsed, dict) else {}, None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        try:
            parsed = json.loads(body) if body.strip() else {}
        except Exception:
            parsed = {"raw_body": body}
        return exc.code, parsed if isinstance(parsed, dict) else {"raw_body": body}, str(exc)
    except urllib.error.URLError as exc:
        return None, None, f"{exc.__class__.__name__}:{exc}"
    except (TimeoutError, socket.timeout, http.client.RemoteDisconnected) as exc:
        return None, None, f"{exc.__class__.__name__}:{exc}"


def _error_allows_db_fallback(error: str | None) -> bool:
    if not error:
        return False
    lowered = error.casefold()
    return any(marker in lowered for marker in ("timed out", "timeouterror", "remotedisconnected"))


def _fetch_conversation_bundle(
    *,
    conversation_id: str,
    db_container: str,
    db_name: str,
    db_user: str,
    timeout: float,
) -> dict[str, Any] | None:
    query = (
        "SELECT json_build_object("
        "'conversation_id', c.id, "
        "'state', c.state, "
        "'context', c.context, "
        "'messages', COALESCE(("
        "  SELECT json_agg(json_build_object("
        "    'id', m.id, "
        "    'role', m.role, "
        "    'content', m.content, "
        "    'created_at', m.created_at, "
        "    'message_id', m.metadata->>'messageId', "
        "    'decision_meta', m.metadata->'decision_meta', "
        "    'metadata', m.metadata"
        "  ) ORDER BY m.created_at ASC, m.id ASC) "
        "  FROM messages m "
        "  WHERE m.conversation_id = c.id"
        "), '[]'::json)"
        ") "
        "FROM conversations c "
        "WHERE c.id = '{conversation_id}' "
        "LIMIT 1;"
    ).format(conversation_id=_escape_sql_literal(conversation_id))
    return _run_psql_json_query(
        db_container=db_container,
        db_name=db_name,
        db_user=db_user,
        query=query,
        timeout=timeout,
    )


def _poll_conversation_id(
    *,
    client_id: str,
    remote_jid: str,
    db_container: str,
    db_name: str,
    db_user: str,
    timeout: float,
    interval: float,
) -> str | None:
    deadline = time.time() + max(timeout, 1.0)
    while time.time() <= deadline:
        conversation_id = _fetch_latest_conversation_id(
            client_id=client_id,
            remote_jid=remote_jid,
            db_container=db_container,
            db_name=db_name,
            db_user=db_user,
            timeout=timeout,
        )
        if conversation_id:
            return conversation_id
        time.sleep(max(interval, 0.2))
    return None


def _fetch_latest_conversation_id(
    *,
    client_id: str,
    remote_jid: str,
    db_container: str,
    db_name: str,
    db_user: str,
    timeout: float,
) -> str | None:
    query = (
        "SELECT json_build_object('conversation_id', c.id) "
        "FROM conversations c "
        "JOIN users u ON u.id = c.user_id "
        "WHERE c.client_id = '{client_id}' AND u.remote_jid = '{remote_jid}' "
        "ORDER BY c.last_message_at DESC NULLS LAST, c.started_at DESC "
        "LIMIT 1;"
    ).format(
        client_id=_escape_sql_literal(client_id),
        remote_jid=_escape_sql_literal(remote_jid),
    )
    payload = _run_psql_json_query(
        db_container=db_container,
        db_name=db_name,
        db_user=db_user,
        query=query,
        timeout=timeout,
    )
    if not isinstance(payload, dict) or not payload.get("conversation_id"):
        return None
    return str(payload["conversation_id"])


def _decision_meta_ready(meta: dict[str, Any] | None) -> bool:
    if not isinstance(meta, dict):
        return False
    if meta.get("action") or meta.get("pending_action") or meta.get("policy_gate"):
        return True
    timing = meta.get("timing")
    if isinstance(timing, dict) and timing.get("pipeline_finished_at"):
        return True
    if meta.get("source") and meta.get("intent"):
        return True
    return False


def _canonical_meta_subset(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(meta, dict):
        return {}
    keys = (
        "action",
        "tool_action",
        "source",
        "expected_reply_type",
        "expected_reply_reason",
        "pending_question_target",
        "active_question_relation",
    )
    return {key: meta[key] for key in keys if key in meta}


def _runtime_trace_contract_subset(contract: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(contract, dict):
        return {}
    owner = contract.get("owner_transition") if isinstance(contract.get("owner_transition"), dict) else {}
    action = contract.get("action_transition") if isinstance(contract.get("action_transition"), dict) else {}
    return {
        key: value
        for key, value in {
            "owner_requested_outcome": owner.get("requested_outcome"),
            "contract_action": action.get("contract_action"),
            "execution_tool_action": action.get("execution_tool_action"),
            "reply_kind": action.get("reply_kind"),
        }.items()
        if value is not None
    }


def extract_turn_snapshot(
    *,
    bundle: dict[str, Any],
    message_id: str,
    previous_trace_count: int,
) -> dict[str, Any] | None:
    messages = bundle.get("messages")
    if not isinstance(messages, list):
        return None
    inbound_index = None
    inbound_message = None
    for index, item in enumerate(messages):
        if not isinstance(item, dict):
            continue
        if item.get("role") == "user" and item.get("message_id") == message_id:
            inbound_index = index
            inbound_message = item
    if inbound_index is None or not isinstance(inbound_message, dict):
        return None
    meta = inbound_message.get("decision_meta") if isinstance(inbound_message.get("decision_meta"), dict) else {}
    if not _decision_meta_ready(meta):
        return None
    assistant_message = None
    for item in messages[inbound_index + 1 :]:
        if isinstance(item, dict) and item.get("role") in {"assistant", "system"} and str(item.get("content") or "").strip():
            assistant_message = item
            break
    if not isinstance(assistant_message, dict):
        return None
    context = bundle.get("context") if isinstance(bundle.get("context"), dict) else {}
    trace_entries = context.get("decision_trace") if isinstance(context.get("decision_trace"), list) else []
    trace_delta = trace_entries[previous_trace_count:] if len(trace_entries) >= previous_trace_count else trace_entries
    runtime_trace_contract = (
        meta.get("runtime_trace_contract")
        if isinstance(meta.get("runtime_trace_contract"), dict)
        else None
    )
    return {
        "message_id": message_id,
        "conversation_id": bundle.get("conversation_id"),
        "conversation_state": bundle.get("state"),
        "user_content": inbound_message.get("content"),
        "assistant_content": assistant_message.get("content"),
        "decision_meta": meta,
        "decision_meta_subset": _canonical_meta_subset(meta),
        "decision_trace": [entry for entry in trace_delta if isinstance(entry, dict)],
        "runtime_trace_contract": runtime_trace_contract or {},
        "runtime_trace_contract_subset": _runtime_trace_contract_subset(runtime_trace_contract),
        "trace_count": len(trace_entries),
    }


def _build_timeline(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            continue
        timeline.append({"role": role, "content": content})
    return timeline


def _read_turns(args: argparse.Namespace) -> list[str]:
    turns: list[str] = []
    for item in args.turn or []:
        if item and item.strip():
            turns.append(item.strip())
    if args.turns_file:
        payload = json.loads(Path(args.turns_file).read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
            raise SystemExit("focused-family-proof: turns file must be a JSON string array")
        turns.extend(item.strip() for item in payload if item.strip())
    if not turns:
        raise SystemExit("focused-family-proof: provide at least one --turn or --turns-file")
    return turns


def _default_remote_jid() -> str:
    suffix = uuid4().int % 10_000_000_000
    return f"7999{suffix:010d}@s.whatsapp.net"


def _poll_turn_snapshot(
    *,
    conversation_id: str,
    message_id: str,
    previous_trace_count: int,
    db_container: str,
    db_name: str,
    db_user: str,
    timeout: float,
    interval: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    deadline = time.time() + max(timeout, 1.0)
    last_bundle: dict[str, Any] | None = None
    while time.time() <= deadline:
        bundle = _fetch_conversation_bundle(
            conversation_id=conversation_id,
            db_container=db_container,
            db_name=db_name,
            db_user=db_user,
            timeout=timeout,
        )
        if isinstance(bundle, dict):
            last_bundle = bundle
            snapshot = extract_turn_snapshot(
                bundle=bundle,
                message_id=message_id,
                previous_trace_count=previous_trace_count,
            )
            if snapshot:
                return snapshot, bundle
        time.sleep(max(interval, 0.2))
    raise SystemExit(
        f"focused-family-proof: timed out waiting for decision evidence "
        f"(conversation_id={conversation_id}, message_id={message_id})"
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--client-slug", default=DEFAULT_CLIENT_SLUG)
    parser.add_argument("--turn", action="append", help="User turn text; repeat for multi-turn dialog.")
    parser.add_argument("--turns-file", help="Path to JSON string array with dialog turns.")
    parser.add_argument("--output", required=True, help="Artifact output path.")
    parser.add_argument("--poll-timeout", type=float, default=20.0)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--request-timeout", type=float, default=45.0)
    parser.add_argument("--expected-commit", default=None)
    parser.add_argument("--remote-jid", default=None)
    parser.add_argument("--sender", default=DEFAULT_SENDER)
    parser.add_argument("--origin-source", default=DEFAULT_ORIGIN_SOURCE)
    parser.add_argument("--db-container", default=DEFAULT_DB_CONTAINER)
    parser.add_argument("--db-name", default=DEFAULT_DB_NAME)
    parser.add_argument("--db-user", default=None)
    parser.add_argument("--branch-slug", default=None)
    parser.add_argument("--branch-id", default=None)
    parser.add_argument("--instance-id", default=None)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    turns = _read_turns(args)
    expected_commit = _resolve_expected_commit(args.expected_commit)
    fingerprint = validate_runtime_fingerprint(
        base_url=args.base_url,
        expected_commit=expected_commit,
        timeout=args.request_timeout,
    )
    if not fingerprint.valid:
        raise SystemExit(format_runtime_fingerprint_failure(fingerprint))

    db_user = _resolve_db_user(
        explicit=args.db_user,
        db_container=args.db_container,
        timeout=args.request_timeout,
    )
    context = resolve_runtime_client_context(
        client_slug=args.client_slug,
        db_container=args.db_container,
        db_name=args.db_name,
        db_user=db_user,
        timeout=args.request_timeout,
        branch_slug=args.branch_slug,
        branch_id=args.branch_id,
        instance_id=args.instance_id,
    )
    remote_jid = args.remote_jid or _default_remote_jid()

    webhook_secret_preflight = {
        "valid": bool(context.webhook_secret),
        "expected_source": context.webhook_secret_source,
        "expected_fingerprint": _fingerprint_secret(context.webhook_secret),
    }
    if not webhook_secret_preflight["valid"]:
        raise SystemExit("focused-family-proof: runtime webhook secret missing")

    turns_report: list[dict[str, Any]] = []
    conversation_id: str | None = None
    current_bundle: dict[str, Any] | None = None
    previous_trace_count = 0

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for index, turn in enumerate(turns, start=1):
        message_id = f"focused-family-proof-{run_id}-{index:02d}-{uuid4().hex[:8]}"
        payload = build_turn_payload(
            message=turn,
            context=context,
            remote_jid=remote_jid,
            message_id=message_id,
            sender=args.sender,
            timestamp=int(time.time()),
            origin_source=args.origin_source,
        )
        status, response_payload, error = _send_webhook_payload(
            base_url=args.base_url,
            client_slug=context.client_slug,
            payload=payload,
            webhook_secret=context.webhook_secret,
            timeout=args.request_timeout,
        )
        if error and _error_allows_db_fallback(error):
            response_payload = {
                "fallback_after_http_timeout": True,
                "transport_error": error,
            }
        elif error or status is None or status >= 400:
            raise SystemExit(
                "focused-family-proof: webhook request failed "
                f"(status={status}, error={error}, response={json.dumps(response_payload or {}, ensure_ascii=False)})"
            )
        response_payload = response_payload or {}
        response_conversation_id = response_payload.get("conversation_id")
        if response_conversation_id:
            conversation_id = str(response_conversation_id)
        if not conversation_id:
            conversation_id = _poll_conversation_id(
                client_id=context.client_id,
                remote_jid=remote_jid,
                db_container=args.db_container,
                db_name=args.db_name,
                db_user=db_user,
                timeout=args.poll_timeout,
                interval=args.poll_interval,
            )
        if not conversation_id:
            raise SystemExit("focused-family-proof: runtime did not yield conversation_id")
        snapshot, current_bundle = _poll_turn_snapshot(
            conversation_id=conversation_id,
            message_id=message_id,
            previous_trace_count=previous_trace_count,
            db_container=args.db_container,
            db_name=args.db_name,
            db_user=db_user,
            timeout=args.poll_timeout,
            interval=args.poll_interval,
        )
        previous_trace_count = int(snapshot.get("trace_count") or previous_trace_count)
        turns_report.append(
            {
                "turn_index": index,
                "message_id": message_id,
                "request_payload": payload,
                "webhook_response": response_payload,
                **snapshot,
            }
        )

    final_bundle = current_bundle or (
        _fetch_conversation_bundle(
            conversation_id=conversation_id or "",
            db_container=args.db_container,
            db_name=args.db_name,
            db_user=db_user,
            timeout=args.request_timeout,
        )
        if conversation_id
        else {}
    )
    messages = final_bundle.get("messages") if isinstance(final_bundle, dict) and isinstance(final_bundle.get("messages"), list) else []
    last_turn = turns_report[-1] if turns_report else {}
    artifact = {
        "run_id": run_id,
        "base_url": args.base_url,
        "client_slug": context.client_slug,
        "conversation_id": conversation_id,
        "remote_jid": remote_jid,
        "runtime_fingerprint": runtime_fingerprint_payload(fingerprint),
        "tenant_context": {
            "client_id": context.client_id,
            "client_slug": context.client_slug,
            "branch_id": context.branch_id,
            "branch_slug": context.branch_slug,
            "instance_id": context.instance_id,
        },
        "webhook_secret_preflight": webhook_secret_preflight,
        "assistant_content": last_turn.get("assistant_content"),
        "decision_meta_subset": last_turn.get("decision_meta_subset", {}),
        "runtime_trace_contract_subset": last_turn.get("runtime_trace_contract_subset", {}),
        "timeline": _build_timeline([item for item in messages if isinstance(item, dict)]),
        "turns": turns_report,
    }
    output_path = Path(args.output).resolve()
    _write_json(output_path, artifact)
    print(json.dumps({"status": "ok", "output": str(output_path), "conversation_id": conversation_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
