#!/usr/bin/env python3
"""Capture one tenant-level knowledge activation closeout artifact."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
_GUARD_SCRIPT = REPO_ROOT / "truffles-api" / "scripts" / "knowledge_activation_release_guard.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture tenant-level knowledge activation closeout")
    parser.add_argument("--client-slug", required=True, help="Target client slug")
    parser.add_argument("--branch-slug", required=True, help="Target branch slug")
    parser.add_argument("--output", help="Write closeout JSON to file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--guard-json", help="Reuse an existing P5 guard artifact instead of calling endpoints")
    parser.add_argument("--timeout", type=float, default=20.0, help="Shell command timeout in seconds")
    parser.add_argument("--postgres-container", default="truffles_postgres_1", help="Postgres container name")
    parser.add_argument("--postgres-db", default="chatbot", help="Postgres database name")
    parser.add_argument("--db-user", default=None, help="Postgres user override")
    parser.add_argument(
        "--service-health-url",
        default="http://127.0.0.1:8015/health",
        help="Knowledge activation service /health URL",
    )
    parser.add_argument(
        "--process-url",
        default="http://127.0.0.1:8015/knowledge-activation/process",
        help="Knowledge activation process URL",
    )
    parser.add_argument(
        "--admin-health-url",
        default="http://127.0.0.1:8000/admin/health/check",
        help="Admin health URL",
    )
    parser.add_argument(
        "--metrics-url",
        default="http://127.0.0.1:8000/metrics",
        help="Metrics URL",
    )
    parser.add_argument("--service-token", default=None, help="Knowledge activation service token override")
    parser.add_argument(
        "--max-activation-status",
        choices=("healthy", "warning", "critical"),
        default="warning",
        help="Maximum allowed activation status for the reused P5 guard",
    )
    return parser.parse_args()


def run_shell(command: str, *, timeout: float) -> str:
    completed = subprocess.run(
        ["/bin/bash", "-lc", command],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or f"exit={completed.returncode}"
        raise RuntimeError(detail)
    return completed.stdout.strip()


def resolve_db_user(args: argparse.Namespace) -> str:
    if args.db_user:
        return args.db_user
    shell = (
        "DB_USER=$(docker exec -i "
        f"{shlex.quote(args.postgres_container)} /bin/sh -lc 'printf %s \"${{POSTGRES_USER:-postgres}}\"')\n"
        "printf '%s' \"$DB_USER\""
    )
    try:
        resolved = run_shell(shell, timeout=args.timeout).strip()
        if resolved:
            return resolved
    except Exception:
        pass
    return "postgres"


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def load_tenant_snapshot(
    *,
    client_slug: str,
    branch_slug: str,
    postgres_container: str,
    postgres_db: str,
    db_user: str,
    timeout: float,
) -> dict[str, Any]:
    client_slug_sql = _sql_literal(client_slug)
    branch_slug_sql = _sql_literal(branch_slug)
    sql = f"""
WITH target_client AS (
  SELECT id, name, config
  FROM clients
  WHERE name = '{client_slug_sql}'
  LIMIT 1
),
target_branch AS (
  SELECT b.id, b.slug, b.name, b.client_id, b.active_knowledge_version_id, b.knowledge_safe_mode, b.knowledge_safe_mode_reason
  FROM branches b
  JOIN target_client c ON c.id = b.client_id
  WHERE b.slug = '{branch_slug_sql}'
  LIMIT 1
),
active_version AS (
  SELECT kv.id, kv.status, kv.published_at, kv.sync_status, kv.sync_error
  FROM knowledge_versions kv
  JOIN target_branch b ON b.active_knowledge_version_id = kv.id
),
latest_published AS (
  SELECT kv.id, kv.status, kv.published_at, kv.sync_status, kv.sync_error, kv.created_at
  FROM knowledge_versions kv
  JOIN target_branch b ON b.id = kv.branch_id
  WHERE kv.status = 'published'
  ORDER BY kv.published_at DESC NULLS LAST, kv.created_at DESC NULLS LAST
  LIMIT 1
),
latest_draft AS (
  SELECT kv.id, kv.status, kv.created_at
  FROM knowledge_versions kv
  JOIN target_branch b ON b.id = kv.branch_id
  WHERE kv.status = 'draft'
  ORDER BY kv.created_at DESC NULLS LAST
  LIMIT 1
),
latest_job AS (
  SELECT kaj.id, kaj.version_id, kaj.state, kaj.current_stage, kaj.attempt_count, kaj.queued_at, kaj.started_at, kaj.heartbeat_at, kaj.finished_at, kaj.error_code, kaj.last_error
  FROM knowledge_activation_jobs kaj
  JOIN latest_published lp ON lp.id = kaj.version_id
  JOIN target_branch b ON b.id = kaj.branch_id
  ORDER BY kaj.created_at DESC NULLS LAST, kaj.queued_at DESC NULLS LAST
  LIMIT 1
),
job_stats AS (
  SELECT
    COUNT(*) FILTER (WHERE kaj.state = 'queued') AS queued_24h,
    COUNT(*) FILTER (WHERE kaj.state = 'running') AS running_24h,
    COUNT(*) FILTER (WHERE kaj.state = 'ready') AS ready_24h,
    COUNT(*) FILTER (WHERE kaj.state = 'failed') AS failed_24h,
    COUNT(*) FILTER (WHERE kaj.state = 'stuck') AS stuck_24h
  FROM knowledge_activation_jobs kaj
  JOIN target_branch b ON b.id = kaj.branch_id
  WHERE kaj.created_at >= NOW() - INTERVAL '24 hours'
)
SELECT json_build_object(
  'client_id', (SELECT id::text FROM target_client),
  'client_slug', (SELECT name FROM target_client),
  'client_config', COALESCE((SELECT config FROM target_client), '{{}}'::jsonb),
  'branch_id', (SELECT id::text FROM target_branch),
  'branch_slug', (SELECT slug FROM target_branch),
  'branch_name', (SELECT name FROM target_branch),
  'knowledge_safe_mode', COALESCE((SELECT knowledge_safe_mode FROM target_branch), false),
  'knowledge_safe_mode_reason', (SELECT knowledge_safe_mode_reason FROM target_branch),
  'active_version', (
    SELECT json_build_object(
      'id', av.id::text,
      'status', av.status,
      'published_at', av.published_at::text,
      'sync_status', av.sync_status,
      'sync_error', av.sync_error
    )
    FROM active_version av
  ),
  'latest_published', (
    SELECT json_build_object(
      'id', lp.id::text,
      'status', lp.status,
      'published_at', lp.published_at::text,
      'created_at', lp.created_at::text,
      'sync_status', lp.sync_status,
      'sync_error', lp.sync_error
    )
    FROM latest_published lp
  ),
  'latest_draft', (
    SELECT json_build_object(
      'id', ld.id::text,
      'status', ld.status,
      'created_at', ld.created_at::text
    )
    FROM latest_draft ld
  ),
  'latest_job', (
    SELECT json_build_object(
      'id', lj.id::text,
      'version_id', lj.version_id::text,
      'state', lj.state,
      'current_stage', lj.current_stage,
      'attempt_count', lj.attempt_count,
      'queued_at', lj.queued_at::text,
      'started_at', lj.started_at::text,
      'heartbeat_at', lj.heartbeat_at::text,
      'finished_at', lj.finished_at::text,
      'error_code', lj.error_code,
      'last_error', lj.last_error
    )
    FROM latest_job lj
  ),
  'job_stats_24h', (
    SELECT json_build_object(
      'queued', COALESCE(js.queued_24h, 0),
      'running', COALESCE(js.running_24h, 0),
      'ready', COALESCE(js.ready_24h, 0),
      'failed', COALESCE(js.failed_24h, 0),
      'stuck', COALESCE(js.stuck_24h, 0)
    )
    FROM job_stats js
  )
)::text;
"""
    shell = (
        f"docker exec -i {shlex.quote(postgres_container)} "
        f"psql -U {shlex.quote(db_user)} -d {shlex.quote(postgres_db)} -Atc {shlex.quote(sql)}"
    )
    raw = run_shell(shell, timeout=timeout)
    line = ""
    for candidate in reversed(raw.splitlines()):
        if candidate.strip():
            line = candidate.strip()
            break
    if not line:
        raise RuntimeError("empty SQL output")
    payload = json.loads(line)
    if not isinstance(payload, dict):
        raise RuntimeError("invalid SQL payload")
    return payload


def _parse_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def resolve_feature_enabled(client_config: Any) -> bool:
    config = client_config if isinstance(client_config, dict) else {}
    candidates: list[Any] = []

    console_features = config.get("console_features")
    if isinstance(console_features, dict):
        consultant_verification = console_features.get("consultant_verification")
        if isinstance(consultant_verification, dict):
            candidates.append(consultant_verification.get("enabled"))

    owner_surface = config.get("owner_consultant_verification")
    if isinstance(owner_surface, dict):
        candidates.append(owner_surface.get("enabled"))

    candidates.append(config.get("consultant_verification_enabled"))

    for candidate in candidates:
        parsed = _parse_optional_bool(candidate)
        if parsed is not None:
            return parsed
    return False


def _load_guard_module():
    spec = importlib.util.spec_from_file_location("knowledge_activation_release_guard", _GUARD_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load guard module: {_GUARD_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_guard_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    if args.guard_json:
        payload = json.loads(Path(args.guard_json).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("invalid guard JSON object")
        return payload

    guard_module = _load_guard_module()
    return guard_module.build_release_guard_snapshot(
        service_health_url=args.service_health_url,
        process_url=args.process_url,
        admin_health_url=args.admin_health_url,
        metrics_url=args.metrics_url,
        service_token=args.service_token,
        timeout_seconds=max(float(args.timeout), 0.1),
        max_activation_status=args.max_activation_status,
    )


def derive_live_activation_status(
    *,
    active_version: dict[str, Any] | None,
    latest_published: dict[str, Any] | None,
    latest_job: dict[str, Any] | None,
) -> str:
    if not latest_published and not active_version:
        return "not_ready"
    if latest_published and active_version and latest_published.get("id") == active_version.get("id"):
        job_state = str((latest_job or {}).get("state") or "").strip().lower()
        if job_state in {"queued", "running"}:
            return "pending"
        if job_state in {"failed", "stuck"}:
            return "failed"
        return "ready"
    if latest_published and (not active_version or latest_published.get("id") != active_version.get("id")):
        if latest_job is None:
            return "unknown"
        job_state = str(latest_job.get("state") or "").strip().lower()
        if job_state in {"queued", "running"}:
            return "pending"
        if job_state in {"failed", "stuck"}:
            return "failed"
        if job_state == "ready":
            return "ready"
        return job_state or "unknown"
    return "ready"


def build_closeout_snapshot(
    *,
    guard_snapshot: dict[str, Any],
    tenant_snapshot: dict[str, Any],
    client_slug: str,
    branch_slug: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    active_version = tenant_snapshot.get("active_version") if isinstance(tenant_snapshot.get("active_version"), dict) else None
    latest_published = tenant_snapshot.get("latest_published") if isinstance(tenant_snapshot.get("latest_published"), dict) else None
    latest_draft = tenant_snapshot.get("latest_draft") if isinstance(tenant_snapshot.get("latest_draft"), dict) else None
    latest_job = tenant_snapshot.get("latest_job") if isinstance(tenant_snapshot.get("latest_job"), dict) else None

    feature_enabled = resolve_feature_enabled(tenant_snapshot.get("client_config"))
    has_live_knowledge = active_version is not None
    has_published_knowledge = latest_published is not None
    has_draft_knowledge = latest_draft is not None
    has_published_candidate = bool(
        has_published_knowledge
        and (active_version is None or latest_published.get("id") != active_version.get("id"))
    )

    available_source_modes: list[str] = []
    if has_live_knowledge:
        available_source_modes.append("live")
    if has_published_candidate:
        available_source_modes.append("published")
    if has_draft_knowledge:
        available_source_modes.append("draft")

    default_source_mode = (
        "draft"
        if has_draft_knowledge
        else ("published" if has_published_candidate else ("live" if has_live_knowledge else None))
    )
    preview_available = bool(available_source_modes)
    branch_present = bool(tenant_snapshot.get("branch_id"))
    can_verify_now = feature_enabled and branch_present and preview_available

    live_activation_status = derive_live_activation_status(
        active_version=active_version,
        latest_published=latest_published,
        latest_job=latest_job,
    )

    release_guard_go = str(guard_snapshot.get("decision") or "").strip().lower() == "go"
    if not release_guard_go:
        release_guard_reasons = guard_snapshot.get("reasons") if isinstance(guard_snapshot.get("reasons"), list) else []
        if release_guard_reasons:
            reasons.extend([f"release_guard:{reason}" for reason in release_guard_reasons])
        else:
            reasons.append("release_guard:no_go")

    if not tenant_snapshot.get("client_id"):
        reasons.append("tenant:client_not_found")
    if not branch_present:
        reasons.append("tenant:branch_not_found")
    if not feature_enabled:
        reasons.append("tenant:consultant_verification_disabled")
    if not preview_available:
        reasons.append("tenant:preview_unavailable")
    if has_published_candidate and latest_job is None:
        reasons.append("tenant:candidate_missing_activation_job")
    if (
        has_published_candidate
        and active_version is not None
        and latest_published is not None
        and latest_published.get("id") == active_version.get("id")
        and str((latest_job or {}).get("state") or "").strip().lower() in {"queued", "running", "failed", "stuck"}
    ):
        reasons.append("tenant:live_pointer_switched_early")
    if (
        latest_published is not None
        and latest_job is not None
        and str(latest_job.get("state") or "").strip().lower() == "ready"
        and active_version is not None
        and latest_published.get("id") != active_version.get("id")
    ):
        reasons.append("tenant:ready_candidate_not_active")
    if live_activation_status in {"pending", "failed", "unknown", "not_ready"} and not can_verify_now and feature_enabled:
        reasons.append("tenant:preview_blocked_by_activation")
    if live_activation_status == "pending":
        reasons.append("tenant:activation_pending")
    elif live_activation_status == "failed":
        reasons.append("tenant:activation_failed")
    elif live_activation_status == "unknown":
        reasons.append("tenant:activation_unknown")
    elif live_activation_status == "not_ready":
        reasons.append("tenant:activation_not_ready")

    invariants = {
        "release_guard_go": release_guard_go,
        "feature_enabled": feature_enabled,
        "preview_available": preview_available,
        "can_verify_now": can_verify_now,
        "preview_not_blocked_by_activation": not (
            feature_enabled and live_activation_status in {"pending", "failed", "unknown", "not_ready"} and not can_verify_now
        ),
        "candidate_has_activation_job": (not has_published_candidate) or (latest_job is not None),
        "live_pointer_separated_from_pending_candidate": not (
            has_published_candidate and active_version is not None and latest_published is not None and latest_published.get("id") == active_version.get("id")
        ),
        "ready_candidate_is_active": not (
            latest_published is not None
            and latest_job is not None
            and str(latest_job.get("state") or "").strip().lower() == "ready"
            and active_version is not None
            and latest_published.get("id") != active_version.get("id")
        ),
        "tenant_activation_ready": live_activation_status == "ready",
    }

    decision = "go" if not reasons else "no_go"
    return {
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "decision": decision,
        "reasons": reasons,
        "target": {
            "client_slug": client_slug,
            "branch_slug": branch_slug,
        },
        "guard": guard_snapshot,
        "tenant": {
            **tenant_snapshot,
            "feature_enabled": feature_enabled,
            "available_source_modes": available_source_modes,
            "default_source_mode": default_source_mode,
            "preview_available": preview_available,
            "can_verify_now": can_verify_now,
            "live_activation_status": live_activation_status,
        },
        "invariants": invariants,
    }


def main() -> int:
    args = parse_args()
    db_user = resolve_db_user(args)
    guard_snapshot = load_guard_snapshot(args)
    tenant_snapshot = load_tenant_snapshot(
        client_slug=args.client_slug,
        branch_slug=args.branch_slug,
        postgres_container=args.postgres_container,
        postgres_db=args.postgres_db,
        db_user=db_user,
        timeout=args.timeout,
    )
    snapshot = build_closeout_snapshot(
        guard_snapshot=guard_snapshot,
        tenant_snapshot=tenant_snapshot,
        client_slug=args.client_slug,
        branch_slug=args.branch_slug,
    )
    payload = json.dumps(snapshot, ensure_ascii=False, indent=2 if args.pretty else None)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + ("\n" if not payload.endswith("\n") else ""), encoding="utf-8")
    print(payload)
    return 0 if snapshot.get("decision") == "go" else 1


if __name__ == "__main__":
    raise SystemExit(main())
