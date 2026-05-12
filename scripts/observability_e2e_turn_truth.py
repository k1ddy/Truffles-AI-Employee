#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request


DEFAULT_ENV_FILE = "/home/zhan/truffles-main/truffles-api/.env"
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TEMPO_URL = "http://localhost:3200"
DEFAULT_CLIENT_SLUG = "demo_salon"
DEFAULT_BRANCH_SLUG = "main"
DEFAULT_MESSAGE = "Какой у вас адрес?"


def load_env_file(path: Path) -> list[str]:
    loaded: list[str] = []
    if not path.exists():
        return loaded
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")
        loaded.append(key)
    return loaded


def _fetch_url(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 20.0,
) -> tuple[int, str]:
    data = None
    request_headers = {"User-Agent": "truffles-observability-e2e-turn-truth/1.0"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    req = request.Request(url, data=data, headers=request_headers, method=method)
    with request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return response.getcode(), body


def _fetch_json(url: str, **kwargs: Any) -> tuple[int, dict[str, Any]]:
    status, body = _fetch_url(url, **kwargs)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return status, {"_invalid_json": body[:500]}
    return status, payload if isinstance(payload, dict) else {"_payload": payload}


def _repo_head(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    commit = completed.stdout.strip()
    return commit or None


def _load_app(repo_root: Path) -> None:
    app_root = repo_root / "truffles-api"
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))


def resolve_target(repo_root: Path, *, client_slug: str, branch_slug: str) -> dict[str, Any]:
    _load_app(repo_root)
    from app.database import SessionLocal
    from app.models import Branch, Client, ClientSettings

    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.name == client_slug).first()
        if client is None:
            raise RuntimeError(f"client_not_found:{client_slug}")
        branch = (
            db.query(Branch)
            .filter(Branch.client_id == client.id, Branch.slug == branch_slug)
            .first()
        )
        if branch is None:
            raise RuntimeError(f"branch_not_found:{client_slug}/{branch_slug}")
        settings = db.query(ClientSettings).filter(ClientSettings.client_id == client.id).first()
        webhook_secret = getattr(branch, "webhook_secret", None) or getattr(settings, "webhook_secret", None)
        instance_id = getattr(branch, "instance_id", None)
        if not webhook_secret:
            raise RuntimeError("webhook_secret_missing")
        if not instance_id:
            raise RuntimeError("branch_instance_id_missing")
        return {
            "client_id": str(client.id),
            "client_slug": client.name,
            "branch_id": str(branch.id),
            "branch_slug": branch.slug,
            "branch_active": bool(branch.is_active),
            "branch_name": branch.name,
            "instance_id": instance_id,
            "webhook_secret": webhook_secret,
        }
    finally:
        db.close()


def build_turn_payload(target: dict[str, Any], *, message: str, message_id: str, remote_jid: str) -> dict[str, Any]:
    now_ts = int(time.time())
    return {
        "body": {
            "messageType": "text",
            "message": message,
            "metadata": {
                "remoteJid": remote_jid,
                "messageId": message_id,
                "timestamp": now_ts,
                "instanceId": target["instance_id"],
                "simulation_mode": True,
                "simulation_id": message_id,
            },
        },
        "client_slug": target["client_slug"],
        "tenant_context": {
            "client_id": target["client_id"],
            "client_slug": target["client_slug"],
            "branch_id": target["branch_id"],
            "branch_slug": target["branch_slug"],
            "instance_id": target["instance_id"],
            "source": "webhook",
            "origin_source": "observability_e2e_turn_truth",
        },
    }


def post_webhook_turn(base_url: str, target: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/webhook/{target['client_slug']}"
    status, response_payload = _fetch_json(
        url,
        method="POST",
        payload=payload,
        headers={"X-Webhook-Secret": target["webhook_secret"]},
        timeout=30.0,
    )
    return {"status_code": status, "payload": response_payload, "url": url}


def _message_summary(message: Any) -> dict[str, Any]:
    metadata = getattr(message, "message_metadata", None)
    decision_meta = metadata.get("decision_meta") if isinstance(metadata, dict) else None
    decision_trace = decision_meta.get("decision_trace") if isinstance(decision_meta, dict) else None
    runtime_trace_contract = decision_meta.get("runtime_trace_contract") if isinstance(decision_meta, dict) else None
    return {
        "id": str(message.id),
        "role": message.role,
        "created_at": message.created_at.isoformat() if message.created_at else None,
        "content_preview": (message.content or "")[:240],
        "has_decision_meta": isinstance(decision_meta, dict),
        "decision_meta": decision_meta if isinstance(decision_meta, dict) else {},
        "decision_trace": decision_trace if isinstance(decision_trace, dict) else {},
        "runtime_trace_contract": runtime_trace_contract if isinstance(runtime_trace_contract, dict) else {},
        "transport_status": metadata.get("transport_status") if isinstance(metadata, dict) else None,
        "transport_reason": metadata.get("transport_reason") if isinstance(metadata, dict) else None,
    }


def poll_turn_state(repo_root: Path, *, inbound_message_id: str, timeout_seconds: float, poll_seconds: float) -> dict[str, Any]:
    _load_app(repo_root)
    from app.database import SessionLocal
    from app.models import Message, OutboxMessage

    deadline = time.monotonic() + timeout_seconds
    polls: list[dict[str, Any]] = []
    latest: dict[str, Any] = {"outbox_found": False, "messages": []}
    while time.monotonic() <= deadline:
        db = SessionLocal()
        try:
            outbox = (
                db.query(OutboxMessage)
                .filter(OutboxMessage.inbound_message_id == inbound_message_id)
                .order_by(OutboxMessage.created_at.desc())
                .first()
            )
            if outbox is None:
                polls.append({"outbox_found": False})
                latest = {"outbox_found": False, "messages": []}
            else:
                messages = (
                    db.query(Message)
                    .filter(Message.conversation_id == outbox.conversation_id)
                    .order_by(Message.created_at.asc())
                    .all()
                )
                message_payloads = [_message_summary(message) for message in messages]
                latest = {
                    "outbox_found": True,
                    "outbox": {
                        "id": str(outbox.id),
                        "status": outbox.status,
                        "attempts": int(outbox.attempts or 0),
                        "conversation_id": str(outbox.conversation_id) if outbox.conversation_id else None,
                        "client_id": str(outbox.client_id),
                        "branch_id": str(outbox.branch_id) if outbox.branch_id else None,
                        "inbound_message_id": outbox.inbound_message_id,
                        "last_error": outbox.last_error,
                        "created_at": outbox.created_at.isoformat() if outbox.created_at else None,
                        "updated_at": outbox.updated_at.isoformat() if outbox.updated_at else None,
                        "meta": outbox.meta if isinstance(outbox.meta, dict) else {},
                    },
                    "messages": message_payloads,
                }
                polls.append(
                    {
                        "outbox_found": True,
                        "outbox_status": outbox.status,
                        "message_roles": [item["role"] for item in message_payloads],
                    }
                )
                if outbox.status in {"SENT", "FAILED"} and any(item["role"] == "assistant" for item in message_payloads):
                    latest["polls"] = polls[-10:]
                    return latest
        finally:
            db.close()
        time.sleep(poll_seconds)
    latest["polls"] = polls[-10:]
    latest["timeout"] = True
    return latest


def _latest_message(messages: list[dict[str, Any]], role: str) -> dict[str, Any] | None:
    for message in reversed(messages):
        if message.get("role") == role:
            return message
    return None


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def extract_correlation(turn_state: dict[str, Any]) -> dict[str, Any]:
    messages = turn_state.get("messages") if isinstance(turn_state.get("messages"), list) else []
    user_message = _latest_message(messages, "user")
    assistant_message = _latest_message(messages, "assistant")
    assistant_decision_meta = assistant_message.get("decision_meta") if isinstance(assistant_message, dict) else {}
    decision_trace = assistant_message.get("decision_trace") if isinstance(assistant_message, dict) else {}
    runtime_trace_contract = (
        assistant_message.get("runtime_trace_contract") if isinstance(assistant_message, dict) else {}
    )
    outbox = turn_state.get("outbox") if isinstance(turn_state.get("outbox"), dict) else {}
    outbox_meta = outbox.get("meta") if isinstance(outbox.get("meta"), dict) else {}
    outbox_correlation = outbox_meta.get("correlation") if isinstance(outbox_meta.get("correlation"), dict) else {}
    trace_id = (
        _nested(decision_trace, "trace_id")
        or _nested(runtime_trace_contract, "trace_id")
        or outbox_correlation.get("trace_id")
    )
    return {
        "conversation_id": outbox.get("conversation_id"),
        "outbox_id": outbox.get("id"),
        "inbound_message_id": outbox.get("inbound_message_id"),
        "trace_id": trace_id,
        "user_message_id": user_message.get("id") if isinstance(user_message, dict) else None,
        "assistant_message_id": assistant_message.get("id") if isinstance(assistant_message, dict) else None,
        "assistant_outcome": assistant_decision_meta.get("outcome") if isinstance(assistant_decision_meta, dict) else None,
        "assistant_action": assistant_decision_meta.get("action") if isinstance(assistant_decision_meta, dict) else None,
        "assistant_source": assistant_decision_meta.get("source") if isinstance(assistant_decision_meta, dict) else None,
        "transport_status": assistant_message.get("transport_status") if isinstance(assistant_message, dict) else None,
        "transport_reason": assistant_message.get("transport_reason") if isinstance(assistant_message, dict) else None,
        "decision_trace_trace_id": _nested(decision_trace, "trace_id"),
        "runtime_trace_contract_trace_id": _nested(runtime_trace_contract, "trace_id"),
        "outbox_meta_trace_id": outbox_correlation.get("trace_id"),
        "outbox_timing": outbox_meta.get("timing") if isinstance(outbox_meta.get("timing"), dict) else {},
    }


def evaluate_turn_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    post = snapshot.get("post") if isinstance(snapshot.get("post"), dict) else {}
    post_payload = post.get("payload") if isinstance(post.get("payload"), dict) else {}
    turn_state = snapshot.get("turn_state") if isinstance(snapshot.get("turn_state"), dict) else {}
    correlation = snapshot.get("correlation") if isinstance(snapshot.get("correlation"), dict) else {}
    outbox = turn_state.get("outbox") if isinstance(turn_state.get("outbox"), dict) else {}
    messages = turn_state.get("messages") if isinstance(turn_state.get("messages"), list) else []
    assistant_message = _latest_message(messages, "assistant")
    user_message = _latest_message(messages, "user")
    assistant_meta = assistant_message.get("decision_meta") if isinstance(assistant_message, dict) else {}
    decision_trace = assistant_message.get("decision_trace") if isinstance(assistant_message, dict) else {}
    runtime_trace_contract = (
        assistant_message.get("runtime_trace_contract") if isinstance(assistant_message, dict) else {}
    )
    outbox_meta = outbox.get("meta") if isinstance(outbox.get("meta"), dict) else {}
    outbox_timing = outbox_meta.get("timing") if isinstance(outbox_meta.get("timing"), dict) else {}
    outbox_correlation = outbox_meta.get("correlation") if isinstance(outbox_meta.get("correlation"), dict) else {}

    if post.get("status_code") != 200 or post_payload.get("success") is not True:
        errors.append("inbound webhook did not accept the turn")
    if not turn_state.get("outbox_found"):
        errors.append("outbox row was not created")
    elif outbox.get("status") != "SENT":
        errors.append(f"outbox row was not processed successfully -> status={outbox.get('status')}")
    if not isinstance(user_message, dict):
        errors.append("user message is missing")
    if not isinstance(assistant_message, dict):
        errors.append("assistant message is missing")
    if not isinstance(assistant_meta, dict) or not assistant_meta:
        errors.append("assistant decision_meta is missing")
    if not isinstance(decision_trace, dict) or not decision_trace:
        errors.append("assistant decision_trace is missing")
    if not isinstance(runtime_trace_contract, dict) or not runtime_trace_contract:
        errors.append("runtime_trace_contract is missing")
    if not correlation.get("trace_id"):
        errors.append("trace_id is missing from turn correlation")
    if not outbox_timing:
        errors.append("outbox timing metadata is missing")
    if outbox_correlation.get("inbound_message_id") != correlation.get("inbound_message_id"):
        errors.append("outbox correlation inbound_message_id mismatch")
    if outbox_correlation.get("trace_id") and correlation.get("trace_id") and outbox_correlation.get("trace_id") != correlation.get("trace_id"):
        errors.append("outbox correlation trace_id mismatch")
    if assistant_meta.get("source") != "llm_policy_core":
        errors.append(f"semantic owner source is not llm_policy_core -> {assistant_meta.get('source')}")
    if assistant_meta.get("outcome") not in {"FACT", "COLLECT", "HANDOFF"}:
        errors.append(f"product outcome is invalid -> {assistant_meta.get('outcome')}")
    if assistant_message and assistant_message.get("transport_status") != "skipped":
        warnings.append(f"controlled no-send transport was not skipped -> {assistant_message.get('transport_status')}")

    runtime = snapshot.get("runtime") if isinstance(snapshot.get("runtime"), dict) else {}
    if runtime.get("version_valid") is not True:
        errors.append("runtime fingerprint is invalid")
    metrics = snapshot.get("metrics") if isinstance(snapshot.get("metrics"), dict) else {}
    if metrics.get("valid") is not True:
        errors.append("metrics proof is invalid")
    console = snapshot.get("console") if isinstance(snapshot.get("console"), dict) else {}
    if console.get("valid") is not True:
        errors.append("Console health proof is invalid")
    logs = snapshot.get("logs") if isinstance(snapshot.get("logs"), dict) else {}
    if logs.get("valid") is not True:
        errors.append("correlated log proof is invalid")
    tempo = snapshot.get("tempo") if isinstance(snapshot.get("tempo"), dict) else {}
    if tempo.get("valid") is not True:
        errors.append("Tempo trace proof is invalid")
    provider = snapshot.get("provider") if isinstance(snapshot.get("provider"), dict) else {}
    if provider.get("valid_for_internal_turn") is not True:
        errors.append("provider readiness/blocker proof is invalid for internal turn")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": {
            "webhook_accepted": post.get("status_code") == 200 and post_payload.get("success") is True,
            "outbox_processed": outbox.get("status") == "SENT",
            "decision_trace_present": isinstance(decision_trace, dict) and bool(decision_trace),
            "runtime_trace_contract_present": isinstance(runtime_trace_contract, dict) and bool(runtime_trace_contract),
            "trace_id_present": bool(correlation.get("trace_id")),
            "outbox_timing_present": bool(outbox_timing),
            "semantic_owner_source": assistant_meta.get("source"),
            "product_outcome": assistant_meta.get("outcome"),
        },
    }


def collect_runtime_proof(repo_root: Path, base_url: str) -> dict[str, Any]:
    expected_commit = _repo_head(repo_root)
    try:
        status, payload = _fetch_json(f"{base_url.rstrip('/')}/admin/version", timeout=10.0)
    except Exception as exc:
        return {"valid": False, "version_valid": False, "error": str(exc)}
    runtime_commit = payload.get("git_commit")
    return {
        "valid": status == 200 and bool(payload),
        "version_valid": status == 200 and expected_commit is not None and runtime_commit == expected_commit,
        "expected_commit": expected_commit,
        "runtime_commit": runtime_commit,
        "build_time": payload.get("build_time"),
        "payload": payload,
    }


def collect_metrics_proof(base_url: str, *, client_slug: str) -> dict[str, Any]:
    try:
        status, body = _fetch_url(f"{base_url.rstrip('/')}/metrics", timeout=10.0)
    except Exception as exc:
        return {"valid": False, "error": str(exc)}
    worker_token = 'worker_heartbeat_status{worker="truffles-outbox"} 1.0'
    webhook_token = f'http_request_count_total{{method="POST",path="/webhook/{client_slug}",status="200"}}'
    console_token = 'http_request_count_total{method="GET",path="/console/v1/health",status="200"}'
    return {
        "valid": status == 200 and worker_token in body and webhook_token in body,
        "status_code": status,
        "worker_heartbeat_present": worker_token in body,
        "webhook_metric_present": webhook_token in body,
        "console_health_metric_present": console_token in body,
    }


def collect_console_proof(base_url: str) -> dict[str, Any]:
    try:
        status, payload = _fetch_json(f"{base_url.rstrip('/')}/console/v1/health", timeout=10.0)
    except Exception as exc:
        return {"valid": False, "error": str(exc)}
    return {
        "valid": status == 200 and payload.get("status") == "ok",
        "status_code": status,
        "payload": payload,
    }


def _flatten_tempo_spans(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    span_names: list[str] = []
    service_names: list[str] = []
    for batch in payload.get("batches") or []:
        resource = batch.get("resource") if isinstance(batch, dict) else {}
        for attr in (resource or {}).get("attributes") or []:
            if attr.get("key") == "service.name":
                value = attr.get("value") or {}
                service_name = value.get("stringValue")
                if service_name:
                    service_names.append(str(service_name))
        for scope_span in batch.get("scopeSpans") or []:
            for span in scope_span.get("spans") or []:
                name = span.get("name")
                if name:
                    span_names.append(str(name))
    return span_names, sorted(set(service_names))


def collect_tempo_proof(tempo_url: str, trace_id: str | None) -> dict[str, Any]:
    if not trace_id:
        return {"valid": False, "error": "trace_id_missing"}
    last_error = None
    for _attempt in range(6):
        try:
            status, payload = _fetch_json(f"{tempo_url.rstrip('/')}/api/traces/{trace_id}", timeout=10.0)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(2)
            continue
        span_names, service_names = _flatten_tempo_spans(payload)
        valid = status == 200 and "outbox.process" in span_names and "truffles-outbox" in service_names
        if valid:
            return {
                "valid": True,
                "status_code": status,
                "trace_id": trace_id,
                "service_names": service_names,
                "span_names_sample": span_names[:30],
                "span_count": len(span_names),
            }
        last_error = "trace_not_ready_or_missing_required_spans"
        time.sleep(2)
    return {"valid": False, "trace_id": trace_id, "error": last_error}


def collect_log_proof(*, outbox_id: str | None, trace_id: str | None, inbound_message_id: str | None) -> dict[str, Any]:
    if not outbox_id or not inbound_message_id:
        return {"valid": False, "error": "correlation_ids_missing"}
    try:
        completed = subprocess.run(
            ["docker", "logs", "truffles-outbox", "--since", "10m"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as exc:
        return {"valid": False, "error": str(exc)}
    logs = completed.stdout + completed.stderr
    outbox_hit = outbox_id in logs
    inbound_hit = inbound_message_id in logs
    trace_hit = bool(trace_id and trace_id in logs)
    return {
        "valid": completed.returncode == 0 and outbox_hit and inbound_hit and trace_hit,
        "outbox_log_hit": outbox_hit,
        "inbound_message_log_hit": inbound_hit,
        "trace_log_hit": trace_hit,
    }


def collect_provider_proof(repo_root: Path, base_url: str, env_file: Path) -> dict[str, Any]:
    script = repo_root / "scripts" / "provider_integration_truth.py"
    if not script.exists():
        return {"valid_for_internal_turn": False, "error": "provider_integration_truth_missing"}
    with tempfile.NamedTemporaryFile(prefix="truffles_provider_truth_", suffix=".json", delete=False) as handle:
        output_path = Path(handle.name)
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--repo-root",
                str(repo_root),
                "--base-url",
                base_url,
                "--env-file",
                str(env_file),
                "--output",
                str(output_path),
            ],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        payload = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}
    except Exception as exc:
        return {"valid_for_internal_turn": False, "error": str(exc)}
    finally:
        try:
            output_path.unlink()
        except OSError:
            pass
    errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
    verdict = payload.get("target_verdict") if isinstance(payload.get("target_verdict"), dict) else {}
    commercial_blocker = any("CHATFLOW_WHATSAPP_COMMERCIALLY_UNAVAILABLE" in str(item) for item in errors)
    internal_blocked = verdict.get("internal_booking_blocked_by_provider") is True
    return {
        "valid_for_internal_turn": completed.returncode in {0, 1}
        and commercial_blocker
        and internal_blocked is False,
        "provider_truth_valid": payload.get("valid"),
        "commercial_blocker_expected": commercial_blocker,
        "internal_booking_blocked_by_provider": internal_blocked,
        "returncode": completed.returncode,
        "errors": errors,
        "warnings": payload.get("warnings") if isinstance(payload.get("warnings"), list) else [],
    }


def run_truth(
    repo_root: Path,
    *,
    base_url: str,
    tempo_url: str,
    env_file: Path,
    client_slug: str,
    branch_slug: str,
    message: str,
    timeout_seconds: float,
    poll_seconds: float,
) -> dict[str, Any]:
    loaded_env_keys = load_env_file(env_file)
    target = resolve_target(repo_root, client_slug=client_slug, branch_slug=branch_slug)
    message_id = f"obs-e2e-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:10]}"
    remote_suffix = f"{uuid.uuid4().int % 10_000_000:07d}"
    remote_jid = f"770099{remote_suffix}@s.whatsapp.net"
    payload = build_turn_payload(target, message=message, message_id=message_id, remote_jid=remote_jid)
    post = post_webhook_turn(base_url, target, payload)
    turn_state = poll_turn_state(
        repo_root,
        inbound_message_id=message_id,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )
    correlation = extract_correlation(turn_state)
    runtime = collect_runtime_proof(repo_root, base_url)
    metrics = collect_metrics_proof(base_url, client_slug=client_slug)
    console = collect_console_proof(base_url)
    tempo = collect_tempo_proof(tempo_url, correlation.get("trace_id"))
    logs = collect_log_proof(
        outbox_id=correlation.get("outbox_id"),
        trace_id=correlation.get("trace_id"),
        inbound_message_id=correlation.get("inbound_message_id"),
    )
    provider = collect_provider_proof(repo_root, base_url, env_file)
    snapshot = {
        "valid": False,
        "contract_name": "observability_e2e_turn_truth",
        "version": "2026-05-01.v1",
        "repo_root": str(repo_root),
        "base_url": base_url,
        "tempo_url": tempo_url,
        "env_file": str(env_file),
        "env_file_loaded_keys": sorted(loaded_env_keys),
        "controlled_transport": {
            "mode": "no_send",
            "reason": "metadata.simulation_mode suppresses external send while preserving runtime/outbox turn proof",
        },
        "target": {
            key: value
            for key, value in target.items()
            if key not in {"webhook_secret", "instance_id"}
        },
        "input": {
            "message_id": message_id,
            "remote_jid": remote_jid,
            "message": message,
        },
        "post": post,
        "turn_state": turn_state,
        "correlation": correlation,
        "runtime": runtime,
        "metrics": metrics,
        "console": console,
        "tempo": tempo,
        "logs": logs,
        "provider": provider,
    }
    verdict = evaluate_turn_snapshot(snapshot)
    snapshot.update(verdict)
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--tempo-url", default=DEFAULT_TEMPO_URL)
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE)
    parser.add_argument("--client-slug", default=DEFAULT_CLIENT_SLUG)
    parser.add_argument("--branch-slug", default=DEFAULT_BRANCH_SLUG)
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    payload = run_truth(
        repo_root,
        base_url=args.base_url,
        tempo_url=args.tempo_url,
        env_file=Path(args.env_file),
        client_slug=args.client_slug,
        branch_slug=args.branch_slug,
        message=args.message,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
    )
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, default=str))
    return 0 if payload.get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
