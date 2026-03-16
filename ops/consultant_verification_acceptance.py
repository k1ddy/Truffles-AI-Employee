#!/usr/bin/env python3
"""Capture one tenant-level consultant-verification acceptance artifact."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
_SOURCE_MODES = ("auto", "live", "published", "draft")
_CHALLENGE_MODES = ("as_client", "stress")
_RESPONSE_ROLES = ("assistant", "consultant")

_CONTAINER_PROBE_TEMPLATE = r"""
import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import case

from app.database import SessionLocal
from app.models import Agent, Branch, Client
from app.schemas.console import ConsoleConsultantVerificationSessionCreateRequest
from app.services.console_auth import ConsoleAuthContext
from app.services.console_consultant_verification import (
    append_consultant_verification_message,
    build_consultant_verification_overview,
    create_consultant_verification_session,
)
from app.services.console_errors import ConsoleAPIError


def _to_json(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


payload = json.loads(__PAYLOAD_LITERAL__)
response_roles = {str(item).strip().lower() for item in __RESPONSE_ROLES_LITERAL__}
db = SessionLocal()
now = datetime.now(timezone.utc)
raw = {
    "generated_at": now.isoformat(),
    "context": {
        "client_slug": payload["client_slug"],
        "branch_slug": payload["branch_slug"],
        "error_code": None,
        "error_message": None,
    },
    "overview": {},
    "session_probe": {
        "attempted": False,
        "status": "skipped",
        "failure_code": None,
        "failure_message": None,
        "requested_source_mode": payload.get("source_mode") or "auto",
        "effective_source_mode": None,
        "challenge_mode": payload.get("challenge_mode") or "as_client",
        "session_id": None,
        "assistant_turn_id": None,
        "assistant_outcome": None,
        "assistant_business_verdict": None,
        "assistant_content_preview": None,
        "summary": {},
    },
}

try:
    client = db.query(Client).filter(Client.name == payload["client_slug"]).first()
    if client is None:
        raw["context"]["error_code"] = "client_not_found"
        raw["context"]["error_message"] = "Client slug not found."
        print(json.dumps(raw, ensure_ascii=False))
        raise SystemExit(0)

    branch = (
        db.query(Branch)
        .filter(Branch.client_id == client.id, Branch.slug == payload["branch_slug"])
        .first()
    )
    if branch is None:
        raw["context"]["error_code"] = "branch_not_found"
        raw["context"]["error_message"] = "Branch slug not found for the client."
        print(json.dumps(raw, ensure_ascii=False))
        raise SystemExit(0)

    role_rank = case((Agent.role == "owner", 0), else_=1)
    agent = (
        db.query(Agent)
        .filter(
            Agent.client_id == client.id,
            Agent.is_active.is_(True),
            Agent.role.in_(("owner", "admin")),
        )
        .order_by(role_rank.asc(), Agent.created_at.asc())
        .first()
    )
    if agent is None:
        raw["context"]["error_code"] = "owner_or_admin_missing"
        raw["context"]["error_message"] = "No active owner/admin agent found for the client."
        print(json.dumps(raw, ensure_ascii=False))
        raise SystemExit(0)

    branches = (
        db.query(Branch)
        .filter(Branch.client_id == client.id, Branch.is_active.is_(True))
        .order_by(Branch.created_at.asc(), Branch.name.asc())
        .all()
    )
    if all(candidate.id != branch.id for candidate in branches):
        branches.append(branch)
    allowed_branch_ids = {candidate.id for candidate in branches}

    context = ConsoleAuthContext(
        agent=agent,
        client=client,
        branches=branches,
        accessible_clients=[client],
        companies=[client.company] if getattr(client, "company", None) is not None else [],
        company_selection_required=False,
        selected_company_id=client.company_id,
        selection_required=False,
        role=str(agent.role),
        allowed_branch_ids=allowed_branch_ids,
        branch_restricted=False,
        effective_branch_id=branch.id,
        branch_selection_required=False,
        selected_branch_id=branch.id,
        subject=f"ops-consultant-verification-acceptance:{agent.id}",
        token_payload={"source": "ops_consultant_verification_acceptance"},
    )

    raw["context"].update(
        {
            "client_id": str(client.id),
            "branch_id": str(branch.id),
            "agent_id": str(agent.id),
            "agent_role": str(agent.role),
        }
    )

    overview = build_consultant_verification_overview(
        db=db,
        context=context,
        now=now,
        allowed_branch_ids=[branch.id],
    )
    raw["overview"] = _to_json(overview)

    requested_source_mode = raw["session_probe"]["requested_source_mode"]
    effective_source_mode = (
        overview.default_source_mode if requested_source_mode == "auto" else requested_source_mode
    )
    raw["session_probe"]["effective_source_mode"] = effective_source_mode

    if payload.get("overview_only"):
        raw["session_probe"]["failure_code"] = "overview_only"
        print(json.dumps(raw, ensure_ascii=False))
        raise SystemExit(0)

    if overview.can_verify_now is not True:
        raw["session_probe"]["failure_code"] = "overview_blocked"
        print(json.dumps(raw, ensure_ascii=False))
        raise SystemExit(0)

    if not effective_source_mode:
        raw["session_probe"]["failure_code"] = "source_mode_missing"
        print(json.dumps(raw, ensure_ascii=False))
        raise SystemExit(0)

    session_request = ConsoleConsultantVerificationSessionCreateRequest(
        source_mode=effective_source_mode,
        challenge_mode=payload.get("challenge_mode") or "as_client",
        title=payload.get("session_title") or "Tenant acceptance diagnostic",
    )
    session_response = create_consultant_verification_session(
        db=db,
        context=context,
        request=session_request,
        allowed_branch_ids=[branch.id],
        now=now,
    )

    raw["session_probe"].update(
        {
            "attempted": True,
            "status": "created",
            "session_id": str(session_response.session.id),
        }
    )

    message_text = str(payload.get("message") or "").strip()
    if not message_text:
        raw["session_probe"]["status"] = "failed"
        raw["session_probe"]["failure_code"] = "message_missing"
        raw["session_probe"]["failure_message"] = "Message probe text is required for acceptance."
        print(json.dumps(raw, ensure_ascii=False))
        raise SystemExit(0)

    session_response = asyncio.run(
        append_consultant_verification_message(
            db=db,
            context=context,
            session_id=session_response.session.id,
            content=message_text,
            allowed_branch_ids=[branch.id],
            now=now,
        )
    )

    assistant_turn = next(
        (
            turn
            for turn in reversed(session_response.turns)
            if str(getattr(turn, "role", "") or "").strip().lower() in response_roles
        ),
        None,
    )
    if assistant_turn is None:
        raw["session_probe"]["status"] = "failed"
        raw["session_probe"]["failure_code"] = "no_assistant_reply"
        raw["session_probe"]["failure_message"] = "Assistant turn is missing after message probe."
    else:
        assistant_content = str(getattr(assistant_turn, "content", "") or "")
        raw["session_probe"].update(
            {
                "status": "go",
                "assistant_turn_id": str(assistant_turn.id),
                "assistant_outcome": getattr(assistant_turn, "outcome", None),
                "assistant_business_verdict": getattr(assistant_turn, "business_verdict", None),
                "assistant_content_preview": assistant_content[:280],
                "summary": _to_json(session_response.summary),
            }
        )
except ConsoleAPIError as exc:
    if raw["overview"]:
        raw["session_probe"]["attempted"] = True
        raw["session_probe"]["status"] = "failed"
        raw["session_probe"]["failure_code"] = str(exc.code)
        raw["session_probe"]["failure_message"] = str(exc.message)
    else:
        raw["context"]["error_code"] = str(exc.code)
        raw["context"]["error_message"] = str(exc.message)
finally:
    db.close()

print(json.dumps(raw, ensure_ascii=False))
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture tenant-level consultant verification acceptance")
    parser.add_argument("--client-slug", required=True, help="Target client slug (`clients.name`)")
    parser.add_argument("--branch-slug", required=True, help="Target branch slug")
    parser.add_argument("--api-container", default="truffles-api", help="API container name")
    parser.add_argument("--source-mode", choices=_SOURCE_MODES, default="auto", help="Session source mode")
    parser.add_argument("--challenge-mode", choices=_CHALLENGE_MODES, default="as_client", help="Challenge mode")
    parser.add_argument(
        "--message",
        default="Подскажите стоимость маникюра и ближайшее время.",
        help="Probe message sent through the consultant verification session",
    )
    parser.add_argument("--session-title", default="Tenant acceptance diagnostic", help="Session title")
    parser.add_argument("--overview-only", action="store_true", help="Skip session/message probe and capture overview only")
    parser.add_argument("--output", help="Write JSON output to file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--timeout", type=float, default=90.0, help="Container probe timeout in seconds")
    parser.add_argument("--fail-on-no-go", action="store_true", help="Exit non-zero when decision is `no_go`")
    return parser.parse_args()


def _iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _load_json_output(raw_stdout: str, *, command_name: str) -> dict[str, Any]:
    text = (raw_stdout or "").strip()
    if not text:
        raise RuntimeError(f"{command_name}: empty response")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            parsed = json.loads(line)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError(f"{command_name}: non-json response ({text[:200]})")


def resolve_effective_source_mode(overview: dict[str, Any], *, requested_source_mode: str) -> str | None:
    requested = str(requested_source_mode or "auto").strip().lower() or "auto"
    if requested == "auto":
        candidate = overview.get("default_source_mode")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().lower()
        return None
    return requested


def build_acceptance_snapshot(
    *,
    raw_snapshot: dict[str, Any],
    client_slug: str,
    branch_slug: str,
) -> dict[str, Any]:
    context = raw_snapshot.get("context") if isinstance(raw_snapshot.get("context"), dict) else {}
    overview = raw_snapshot.get("overview") if isinstance(raw_snapshot.get("overview"), dict) else {}
    session_probe = raw_snapshot.get("session_probe") if isinstance(raw_snapshot.get("session_probe"), dict) else {}

    reasons: list[str] = []
    context_error_code = context.get("error_code")
    if isinstance(context_error_code, str) and context_error_code.strip():
        reasons.append(f"context:{context_error_code.strip()}")

    probe_error_code = raw_snapshot.get("probe_error_code")
    if isinstance(probe_error_code, str) and probe_error_code.strip():
        reasons.append(f"probe:{probe_error_code.strip()}")

    blocker_codes = [
        str(code).strip()
        for code in (overview.get("blocker_codes") or [])
        if isinstance(code, str) and code.strip()
    ]
    for code in blocker_codes:
        reasons.append(f"overview:{code}")

    workspace_enabled = overview.get("workspace_enabled") is True
    branch_required = overview.get("branch_selection_required") is True
    available_source_modes = overview.get("available_source_modes") or []
    can_verify_now = overview.get("can_verify_now") is True
    team_tools_enabled = overview.get("team_tools_enabled") is True

    if overview and not workspace_enabled and "overview:workspace_disabled" not in reasons:
        reasons.append("overview:workspace_disabled")
    if overview and branch_required and "overview:branch_required" not in reasons:
        reasons.append("overview:branch_required")
    if (
        overview
        and not branch_required
        and not list(available_source_modes)
        and "overview:preview_source_missing" not in reasons
    ):
        reasons.append("overview:preview_source_missing")
    if overview and not can_verify_now and not blocker_codes and not context_error_code:
        reasons.append("overview:verification_not_ready")

    session_status = str(session_probe.get("status") or "").strip().lower()
    if session_status == "failed":
        failure_code = str(session_probe.get("failure_code") or "probe_failed").strip()
        reasons.append(f"session:{failure_code}")
    elif session_status == "skipped":
        failure_code = str(session_probe.get("failure_code") or "").strip()
        if can_verify_now and failure_code and failure_code != "overview_blocked":
            reasons.append(f"session:{failure_code}")
    elif session_status == "go" and not session_probe.get("assistant_turn_id"):
        reasons.append("session:no_assistant_reply")

    reasons = _dedupe_strings(reasons)
    session_probe_passed = session_status == "go" and bool(session_probe.get("assistant_turn_id"))

    return {
        "generated_at": _iso_now(),
        "decision": "go" if not reasons else "no_go",
        "reasons": reasons,
        "client_slug": client_slug,
        "branch_slug": branch_slug,
        "context": context,
        "overview": overview,
        "session_probe": session_probe,
        "invariants": {
            "workspace_enabled": workspace_enabled,
            "team_tools_enabled": team_tools_enabled,
            "can_verify_now": can_verify_now,
            "preview_source_available": bool(list(available_source_modes)),
            "team_tools_not_required_for_preview": can_verify_now if not team_tools_enabled else True,
            "session_probe_passed": session_probe_passed,
        },
    }


def run_container_probe(
    *,
    payload: dict[str, Any],
    api_container: str,
    timeout: float,
) -> dict[str, Any]:
    payload_json = json.dumps(payload, ensure_ascii=False)
    script = (
        _CONTAINER_PROBE_TEMPLATE
        .replace("__PAYLOAD_LITERAL__", json.dumps(payload_json))
        .replace("__RESPONSE_ROLES_LITERAL__", json.dumps(list(_RESPONSE_ROLES), ensure_ascii=False))
    )
    completed = subprocess.run(
        ["docker", "exec", "-i", api_container, "python", "-"],
        cwd=REPO_ROOT,
        input=script,
        check=False,
        capture_output=True,
        text=True,
        timeout=max(timeout, 1.0),
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        detail = stderr or stdout or f"exit={completed.returncode}"
        raise RuntimeError(detail)
    return _load_json_output(completed.stdout, command_name="consultant_verification_acceptance")


def emit_snapshot(snapshot: dict[str, Any], *, output_path: str | None, pretty: bool) -> None:
    text = (
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)
        if pretty
        else json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    )
    if output_path:
        Path(output_path).write_text(text + "\n", encoding="utf-8")
    print(text)


def main() -> int:
    args = parse_args()
    payload = {
        "client_slug": args.client_slug,
        "branch_slug": args.branch_slug,
        "source_mode": args.source_mode,
        "challenge_mode": args.challenge_mode,
        "message": args.message,
        "session_title": args.session_title,
        "overview_only": bool(args.overview_only),
    }
    try:
        raw_snapshot = run_container_probe(
            payload=payload,
            api_container=args.api_container,
            timeout=args.timeout,
        )
    except Exception as exc:
        raw_snapshot = {
            "generated_at": _iso_now(),
            "probe_error_code": "runtime_probe_failed",
            "probe_error_message": str(exc),
            "context": {
                "client_slug": args.client_slug,
                "branch_slug": args.branch_slug,
                "error_code": None,
                "error_message": None,
            },
            "overview": {},
            "session_probe": {
                "attempted": False,
                "status": "failed",
                "failure_code": "runtime_probe_failed",
                "failure_message": str(exc),
            },
        }

    snapshot = build_acceptance_snapshot(
        raw_snapshot=raw_snapshot,
        client_slug=args.client_slug,
        branch_slug=args.branch_slug,
    )
    emit_snapshot(snapshot, output_path=args.output, pretty=args.pretty)
    if args.fail_on_no_go and snapshot["decision"] != "go":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
