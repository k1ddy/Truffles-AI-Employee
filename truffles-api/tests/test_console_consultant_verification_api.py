from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI

from app.models.console_consultant_verification_finding import ConsoleConsultantVerificationFinding
from app.models.knowledge_version import KnowledgeVersion
from app.models.reference_pack import ReferencePack
from app.routers import console as console_router
from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.console import (
    ConsoleConsultantVerificationCompareRequest,
    ConsoleConsultantVerificationCompareResponse,
    ConsoleConsultantVerificationFindingCreateRequest,
    ConsoleConsultantVerificationFindingRecord,
    ConsoleConsultantVerificationFindingUpdateRequest,
    ConsoleConsultantVerificationMessageCreateRequest,
    ConsoleConsultantVerificationReadinessResponse,
    ConsoleConsultantVerificationSessionCreateRequest,
    ConsoleConsultantVerificationSessionListResponse,
    ConsoleConsultantVerificationSessionRecord,
    ConsoleConsultantVerificationSessionResponse,
    ConsoleConsultantVerificationTurnRecord,
)
from app.schemas.webhook import WebhookTenantContext
from app.services import console_consultant_verification as verification_service
from app.services.console_errors import ConsoleAPIError


def _build_context(
    role: str = "owner",
    *,
    branch_id=None,
    branch_restricted: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(id=uuid4(), name="Owner"),
        client=SimpleNamespace(id=uuid4(), slug="demo-salon", config={"consultant_verification_enabled": True}),
        selected_branch_id=branch_id,
        effective_branch_id=branch_id,
        branch_restricted=branch_restricted,
        branches=[
            SimpleNamespace(
                id=branch_id,
                name="Almaty Downtown",
                knowledge_safe_mode=False,
                knowledge_safe_mode_reason=None,
            )
        ] if branch_id else [],
    )


def _build_session_record() -> ConsoleConsultantVerificationSessionRecord:
    now = datetime.now(timezone.utc).isoformat()
    return ConsoleConsultantVerificationSessionRecord(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=None,
        actor_agent_id=uuid4(),
        actor_role="owner",
        source_mode="live",
        challenge_mode="as_client",
        status="active",
        title="Smoke",
        turns_total=2,
        latest_outcome="fact",
        latest_business_verdict="answered",
        latest_preview={"simulation_mode": True, "simulation_id": "sim-1"},
        created_at=now,
        updated_at=now,
        last_message_at=now,
    )


def _build_session_response() -> ConsoleConsultantVerificationSessionResponse:
    record = _build_session_record()
    return ConsoleConsultantVerificationSessionResponse(
        session=record,
        turns=[
            ConsoleConsultantVerificationTurnRecord(
                id=uuid4(),
                turn_index=1,
                role="owner",
                content="Сколько стоит?",
                created_at=record.created_at,
                preview={"simulation_mode": True},
            ),
            ConsoleConsultantVerificationTurnRecord(
                id=uuid4(),
                turn_index=2,
                role="consultant",
                content="Стоимость зависит от услуги.",
                created_at=record.updated_at,
                outcome="fact",
                business_verdict="answered",
                source_refs=["services"],
                decision_meta={"action": "reply"},
                decision_trace=[{"stage": "truth_gate", "decision": "matched"}],
                preview={"simulation_mode": True, "would_handoff": False},
                would_handoff=False,
                would_book=False,
                gap_detected=False,
            ),
        ],
    )


def _build_finding_record() -> ConsoleConsultantVerificationFindingRecord:
    now = datetime.now(timezone.utc).isoformat()
    return ConsoleConsultantVerificationFindingRecord(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=None,
        actor_agent_id=uuid4(),
        actor_role="owner",
        session_id=uuid4(),
        owner_turn_id=uuid4(),
        assistant_turn_id=uuid4(),
        source_mode="live",
        challenge_mode="stress",
        family_key="family-1",
        family_kind="knowledge_gap",
        family_label="Не хватает данных или фактов",
        status="new",
        status_label="Новый",
        owner_prompt="Сколько стоит?",
        assistant_excerpt="Не могу ответить точно.",
        owner_note="Ответ слабый",
        resolution_note=None,
        outcome="fact",
        business_verdict="gap_detected",
        decision_reason_code="owner_flag_gap",
        source_refs=["services"],
        latest_preview={"simulation_mode": True},
        linked_knowledge_backlog_id=uuid4(),
        linked_learning_candidate_id=None,
        repeat_count=1,
        first_captured_at=now,
        last_captured_at=now,
        created_at=now,
        updated_at=now,
    )


def test_consultant_verification_routes_registered_in_openapi() -> None:
    app = FastAPI()
    app.include_router(console_router.router)
    paths = app.openapi()["paths"]

    assert "/console/v1/business/consultant-verification/overview" in paths
    assert "/console/v1/business/consultant-verification/sessions" in paths
    assert "/console/v1/business/consultant-verification/sessions/{session_id}" in paths
    assert "/console/v1/business/consultant-verification/sessions/{session_id}/messages" in paths
    assert "/console/v1/business/consultant-verification/findings" in paths
    assert "/console/v1/business/consultant-verification/findings/{finding_id}" in paths
    assert "/console/v1/business/consultant-verification/readiness" in paths
    assert "/console/v1/business/consultant-verification/compare" in paths
    assert "/console/v1/knowledge/versions/{version_id}/retry-sync" in paths


@pytest.mark.asyncio
async def test_create_consultant_verification_session_endpoint_delegates(monkeypatch) -> None:
    context = _build_context(role="owner")
    expected = _build_session_response()
    captured = {}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)

    def _fake_create(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(console_router, "_create_consultant_verification_session", _fake_create)
    monkeypatch.setattr(console_router, "_resolve_branch_scope", lambda _context: None)

    response = await console_router.create_business_consultant_verification_session(
        body=ConsoleConsultantVerificationSessionCreateRequest(
            source_mode="live",
            challenge_mode="stress",
            title="Break it",
        ),
        request=SimpleNamespace(),
        db=Mock(),
    )

    assert response == expected
    assert captured["context"] is context
    assert captured["request"].challenge_mode == "stress"


@pytest.mark.asyncio
async def test_append_consultant_verification_message_endpoint_delegates(monkeypatch) -> None:
    context = _build_context(role="admin")
    expected = _build_session_response()
    captured = {}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_resolve_branch_scope", lambda _context: None)

    async def _fake_append(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(console_router, "_append_consultant_verification_message", _fake_append)

    session_id = uuid4()
    response = await console_router.append_business_consultant_verification_message(
        session_id=session_id,
        body=ConsoleConsultantVerificationMessageCreateRequest(content="А если клиент придет ночью?"),
        request=SimpleNamespace(),
        db=Mock(),
    )

    assert response == expected
    assert captured["session_id"] == session_id
    assert captured["content"] == "А если клиент придет ночью?"


@pytest.mark.asyncio
async def test_create_consultant_verification_finding_endpoint_delegates(monkeypatch) -> None:
    context = _build_context(role="owner")
    expected = _build_finding_record()
    captured = {}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_resolve_branch_scope", lambda _context: None)

    def _fake_create(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(console_router, "_create_consultant_verification_finding", _fake_create)

    response = await console_router.create_business_consultant_verification_finding(
        body=ConsoleConsultantVerificationFindingCreateRequest(
            assistant_turn_id=uuid4(),
            owner_note="Это выглядит ненадежно",
        ),
        request=SimpleNamespace(),
        db=Mock(),
    )

    assert response == expected
    assert captured["request"].owner_note == "Это выглядит ненадежно"


@pytest.mark.asyncio
async def test_update_consultant_verification_finding_endpoint_delegates(monkeypatch) -> None:
    context = _build_context(role="admin")
    expected = _build_finding_record()
    captured = {}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_resolve_branch_scope", lambda _context: None)

    def _fake_update(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(console_router, "_update_consultant_verification_finding", _fake_update)
    finding_id = uuid4()

    response = await console_router.update_business_consultant_verification_finding(
        finding_id=finding_id,
        body=ConsoleConsultantVerificationFindingUpdateRequest(
            status="fixed",
            resolution_note="Исправили knowledge",
        ),
        request=SimpleNamespace(),
        db=Mock(),
    )

    assert response == expected
    assert captured["finding_id"] == finding_id
    assert captured["request"].status == "fixed"


@pytest.mark.asyncio
async def test_consultant_verification_endpoint_rejects_manager(monkeypatch) -> None:
    context = _build_context(role="manager")
    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_business_consultant_verification_sessions(
            request=SimpleNamespace(),
            db=Mock(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_run_consultant_verification_simulation_rolls_back_runtime_session(monkeypatch) -> None:
    session_row = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=None,
        remote_jid="console-verification@test",
        source_mode="live",
        challenge_mode="as_client",
        runtime_snapshot={},
        created_at=datetime.now(timezone.utc),
    )
    runtime_db = SimpleNamespace(rollback=Mock(), close=Mock())

    monkeypatch.setattr(
        verification_service,
        "sessionmaker",
        lambda **_kwargs: (lambda: runtime_db),
    )
    monkeypatch.setattr(
        verification_service,
        "_ensure_runtime_user",
        lambda *args, **kwargs: SimpleNamespace(id=uuid4()),
    )
    monkeypatch.setattr(
        verification_service,
        "_ensure_runtime_conversation",
        lambda *args, **kwargs: SimpleNamespace(id=uuid4()),
    )
    monkeypatch.setattr(verification_service, "_seed_runtime_messages", lambda *args, **kwargs: None)
    monkeypatch.setattr(verification_service, "_seed_runtime_handovers", lambda *args, **kwargs: None)
    monkeypatch.setattr(verification_service, "_seed_runtime_appointments", lambda *args, **kwargs: None)
    monkeypatch.setattr(verification_service, "get_instance_id", lambda *_args, **_kwargs: "instance-1")
    monkeypatch.setattr(
        verification_service,
        "_build_runtime_payload",
        lambda **_kwargs: SimpleNamespace(),
    )

    async def _fake_handle(_payload, _db, **_kwargs):
        return SimpleNamespace(conversation_id=uuid4(), bot_response="ok", message="ok")

    monkeypatch.setattr(verification_service.reasoning_core, "handle_webhook_payload", _fake_handle)
    monkeypatch.setattr(
        verification_service,
        "_capture_runtime_result",
        lambda *args, **kwargs: {
            "owner": {"content": "test", "message_metadata": {}, "created_at": datetime.now(timezone.utc)},
            "assistant": {
                "role": "consultant",
                "content": "ok",
                "message_metadata": {},
                "decision_meta": {},
                "decision_trace": [],
                "source_refs": [],
                "preview": {},
                "outcome": "fact",
                "business_verdict": "answered",
                "created_at": datetime.now(timezone.utc),
            },
            "runtime_snapshot": {},
        },
    )

    result = await verification_service._run_consultant_verification_simulation(
        db=Mock(get_bind=Mock(return_value=object())),
        session_row=session_row,
        client=SimpleNamespace(slug="demo-salon"),
        previous_turns=[],
        content="test",
        now=datetime.now(timezone.utc),
    )

    assert result["assistant"]["business_verdict"] == "answered"
    runtime_db.rollback.assert_called_once()
    runtime_db.close.assert_called_once()


def test_build_consultant_verification_scenario_catalog_uses_domain_and_capabilities() -> None:
    reference_pack = ReferencePack(
        domain_slug="beauty",
        title="Beauty reference pack",
        status="active",
    )
    scenarios = verification_service._build_scenario_catalog(
        domain_slug="beauty",
        capabilities=CapabilitiesPayload.model_validate(
            {
                "domain_slug": "beauty",
                "providers": {
                    "availability_provider": "google_calendar",
                    "calendar_provider": "google_calendar",
                },
                "features": {
                    "booking_mode": "confirm_slots",
                },
                "handoff_policy": "allow",
            }
        ),
        reference_pack=reference_pack,
    )

    scenario_ids = {item.id for item in scenarios}
    assert "booking-flow" in scenario_ids
    assert "mixed-pressure" in scenario_ids
    assert "beauty-expectations" in scenario_ids
    assert any(item.source == "reference_pack" for item in scenarios)
    assert any(item.recommended_challenge_mode == "stress" for item in scenarios)


def test_build_runtime_payload_uses_system_source_and_origin_source() -> None:
    session_row = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=None,
        remote_jid="console-verification@test",
    )
    client = SimpleNamespace(name="demo-salon")

    payload = verification_service._build_runtime_payload(
        session_row=session_row,
        client=client,
        content="Сколько стоит стрижка?",
        now=datetime.now(timezone.utc),
        instance_id="instance-1",
    )

    assert isinstance(payload.tenant_context, WebhookTenantContext)
    assert payload.body.metadata.instanceId == "instance-1"
    assert payload.tenant_context.instance_id == "instance-1"
    assert payload.tenant_context.source == "system"
    assert payload.tenant_context.origin_source == "console_consultant_verification"


def test_build_session_summary_counts_categories_and_weak_turns() -> None:
    turns = [
        ConsoleConsultantVerificationTurnRecord(
            id=uuid4(),
            turn_index=1,
            role="owner",
            content="Сколько стоит?",
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
        ConsoleConsultantVerificationTurnRecord(
            id=uuid4(),
            turn_index=2,
            role="consultant",
            content="Цена зависит от услуги.",
            created_at=datetime.now(timezone.utc).isoformat(),
            outcome="fact",
            business_verdict="answered",
        ),
        ConsoleConsultantVerificationTurnRecord(
            id=uuid4(),
            turn_index=3,
            role="owner",
            content="А если я передумаю в последний момент?",
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
        ConsoleConsultantVerificationTurnRecord(
            id=uuid4(),
            turn_index=4,
            role="consultant",
            content="Тут нужно уточнение у менеджера.",
            created_at=datetime.now(timezone.utc).isoformat(),
            outcome="handoff",
            business_verdict="gap_detected",
        ),
    ]

    summary = verification_service._build_session_summary(turns)

    assert summary.assistant_turns_total == 2
    assert summary.answered_total == 1
    assert summary.gap_detected_total == 1
    assert summary.replay_prompt_total == 2
    assert summary.latest_verdict == "gap_detected"
    assert len(summary.weak_turns) == 1
    assert summary.weak_turns[0].owner_prompt == "А если я передумаю в последний момент?"


def test_build_finding_family_key_normalizes_prompt_surface() -> None:
    client_id = uuid4()

    left = verification_service._build_finding_family_key(
        client_id=client_id,
        branch_id=None,
        family_kind="knowledge_gap",
        owner_prompt="  Сколько   стоит? ",
        decision_reason_code="owner_flag_gap",
    )
    right = verification_service._build_finding_family_key(
        client_id=client_id,
        branch_id=None,
        family_kind="knowledge_gap",
        owner_prompt="сколько стоит?",
        decision_reason_code="owner_flag_gap",
    )

    assert left == right


def test_create_consultant_verification_finding_reopens_existing_cluster(monkeypatch) -> None:
    context = _build_context(role="owner")
    assistant_turn_id = uuid4()
    owner_turn_id = uuid4()
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    existing = ConsoleConsultantVerificationFinding(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=None,
        actor_agent_id=context.agent.id,
        actor_role="owner",
        session_id=uuid4(),
        owner_turn_id=uuid4(),
        assistant_turn_id=uuid4(),
        source_mode="live",
        challenge_mode="stress",
        family_key="family-1",
        family_kind="knowledge_gap",
        family_label="Не хватает данных или фактов",
        status="fixed",
        owner_prompt="Сколько стоит?",
        assistant_excerpt="Не могу ответить.",
        repeat_count=1,
        source_refs=[],
        latest_preview={},
        first_captured_at=now,
        last_captured_at=now,
        created_at=now,
        updated_at=now,
    )
    db = Mock()
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = existing

    monkeypatch.setattr(
        verification_service,
        "_resolve_turn_pair_for_finding",
        lambda **_kwargs: (
            SimpleNamespace(id=session_id, branch_id=None, source_mode="live", challenge_mode="stress"),
            ConsoleConsultantVerificationTurnRecord(
                id=assistant_turn_id,
                turn_index=2,
                role="consultant",
                content="Не могу ответить.",
                created_at=now.isoformat(),
                outcome="fact",
                business_verdict="gap_detected",
                source_refs=["services"],
                decision_meta={"turn_outcome": {"contract_status": "degraded"}},
                decision_trace=[],
                preview={"simulation_mode": True},
            ),
            ConsoleConsultantVerificationTurnRecord(
                id=owner_turn_id,
                turn_index=1,
                role="owner",
                content="Сколько стоит?",
                created_at=now.isoformat(),
            ),
        ),
    )
    monkeypatch.setattr(
        verification_service,
        "_find_learning_candidate_id_for_prompt",
        lambda *_args, **_kwargs: uuid4(),
    )
    monkeypatch.setattr(
        verification_service,
        "_upsert_knowledge_backlog_for_finding",
        lambda *_args, **_kwargs: uuid4(),
    )

    record = verification_service.create_consultant_verification_finding(
        db=db,
        context=context,
        request=ConsoleConsultantVerificationFindingCreateRequest(
            assistant_turn_id=assistant_turn_id,
            owner_note="Провалился на цене",
        ),
        allowed_branch_ids=None,
        now=now,
    )

    assert record.status == "in_review"
    assert record.repeat_count == 2
    assert existing.assistant_turn_id == assistant_turn_id
    assert existing.owner_note == "Провалился на цене"
    db.commit.assert_called_once()


def test_update_consultant_verification_finding_rejects_invalid_transition() -> None:
    context = _build_context(role="owner")
    now = datetime.now(timezone.utc)
    finding = ConsoleConsultantVerificationFinding(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=None,
        actor_agent_id=context.agent.id,
        actor_role="owner",
        session_id=uuid4(),
        assistant_turn_id=uuid4(),
        source_mode="live",
        challenge_mode="as_client",
        family_key="family-1",
        family_kind="answer_quality",
        family_label="Ответ выглядит слабым",
        status="new",
        owner_prompt="Подскажите цену",
        assistant_excerpt="Не уверен",
        repeat_count=1,
        source_refs=[],
        latest_preview={},
        first_captured_at=now,
        last_captured_at=now,
        created_at=now,
        updated_at=now,
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        verification_service,
        "_get_finding_for_context",
        lambda **_kwargs: finding,
    )

    try:
        with pytest.raises(ConsoleAPIError) as exc_info:
            verification_service.update_consultant_verification_finding(
                db=Mock(),
                context=context,
                finding_id=finding.id,
                request=ConsoleConsultantVerificationFindingUpdateRequest(status="retested"),
                allowed_branch_ids=None,
                now=now,
            )
    finally:
        monkeypatch.undo()

    assert exc_info.value.code == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_get_consultant_verification_readiness_endpoint_delegates(monkeypatch) -> None:
    context = _build_context(role="owner")
    expected = ConsoleConsultantVerificationReadinessResponse(
        readiness={
            "status": "ready",
            "status_label": "Готово к публикации",
            "summary": "Draft не показал регрессий.",
            "draft_hash": "hash-1",
            "compared_at": datetime.now(timezone.utc).isoformat(),
            "total_cases": 1,
            "improved_total": 1,
            "unchanged_total": 0,
            "regressed_total": 0,
            "manual_review_total": 0,
            "retested_total": 0,
            "compare_required": True,
        }
    )
    captured = {}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_resolve_branch_scope", lambda _context: None)

    def _fake_get(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(console_router, "_get_consultant_verification_readiness", _fake_get)

    response = await console_router.get_business_consultant_verification_readiness(
        request=SimpleNamespace(),
        db=Mock(),
    )

    assert response == expected
    assert captured["context"] is context


@pytest.mark.asyncio
async def test_run_consultant_verification_compare_endpoint_delegates(monkeypatch) -> None:
    context = _build_context(role="admin")
    expected = ConsoleConsultantVerificationCompareResponse(
        readiness={
            "status": "ready",
            "status_label": "Готово к публикации",
            "summary": "Без регрессий",
            "draft_hash": "hash-1",
            "compared_at": datetime.now(timezone.utc).isoformat(),
            "total_cases": 1,
            "improved_total": 1,
            "unchanged_total": 0,
            "regressed_total": 0,
            "manual_review_total": 0,
            "retested_total": 1,
            "compare_required": True,
        },
        cases=[],
    )
    captured = {}

    monkeypatch.setattr(console_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(console_router, "_resolve_branch_scope", lambda _context: None)

    async def _fake_compare(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(console_router, "_run_consultant_verification_compare", _fake_compare)

    response = await console_router.run_business_consultant_verification_compare(
        body=ConsoleConsultantVerificationCompareRequest(
            prompt="Сколько стоит?",
        ),
        request=SimpleNamespace(),
        db=Mock(),
    )

    assert response == expected
    assert captured["request"].prompt == "Сколько стоит?"


@pytest.mark.asyncio
async def test_run_consultant_verification_compare_marks_finding_retested(monkeypatch) -> None:
    context = _build_context(role="owner")
    branch_id = uuid4()
    context.selected_branch_id = branch_id
    now = datetime.now(timezone.utc)
    finding = ConsoleConsultantVerificationFinding(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch_id,
        actor_agent_id=context.agent.id,
        actor_role="owner",
        session_id=uuid4(),
        assistant_turn_id=uuid4(),
        source_mode="live",
        challenge_mode="stress",
        family_key="family-1",
        family_kind="knowledge_gap",
        family_label="Не хватает данных или фактов",
        status="in_review",
        owner_prompt="Сколько стоит?",
        assistant_excerpt="Не могу ответить.",
        repeat_count=1,
        source_refs=[],
        latest_preview={},
        first_captured_at=now,
        last_captured_at=now,
        created_at=now,
        updated_at=now,
    )
    db = Mock()
    audit_calls = []

    monkeypatch.setattr(
        verification_service,
        "_resolve_compare_branch_id",
        lambda **_kwargs: branch_id,
    )
    monkeypatch.setattr(
        verification_service,
        "_get_finding_for_context",
        lambda **_kwargs: finding,
    )
    monkeypatch.setattr(
        verification_service,
        "build_runtime_truth",
        lambda *_args, **_kwargs: verification_service.RuntimeTruth(
            truth={"facts": True},
            client_slug=context.client.slug,
            branch_id=branch_id,
            source="knowledge_versions",
        ),
    )
    monkeypatch.setattr(
        verification_service,
        "_resolve_compare_draft_truth",
        lambda **_kwargs: (
            verification_service.RuntimeTruth(
                truth={"facts": True},
                client_slug=context.client.slug,
                branch_id=branch_id,
                source="knowledge_draft",
            ),
            "draft-hash-1",
        ),
    )

    async def _fake_run(**kwargs):
        source_mode = kwargs["session_row"].source_mode
        verdict = "gap_detected" if source_mode == "live" else "answered"
        content = "Не могу ответить." if source_mode == "live" else "Стоимость от 10 000 тг."
        return {
            "assistant": {
                "role": "consultant",
                "content": content,
                "created_at": now,
                "outcome": "fact",
                "business_verdict": verdict,
                "source_refs": ["price_list"],
                "decision_meta": {"reason_code": "owner_flag_gap"},
                "decision_trace": [],
                "preview": {"simulation_mode": True, "gap_detected": verdict == "gap_detected"},
            }
        }

    monkeypatch.setattr(
        verification_service,
        "_run_consultant_verification_simulation",
        _fake_run,
    )
    monkeypatch.setattr(
        verification_service,
        "record_audit_event",
        lambda *args, **kwargs: audit_calls.append(kwargs),
    )

    response = await verification_service.run_consultant_verification_compare(
        db=db,
        context=context,
        request=ConsoleConsultantVerificationCompareRequest(
            finding_id=finding.id,
            mark_finding_retested=True,
        ),
        allowed_branch_ids=[branch_id],
        now=now,
    )

    assert response.readiness.status == "ready"
    assert response.cases[0].delta == "improved"
    assert response.cases[0].retested_finding is True
    assert finding.status == "retested"
    assert audit_calls
    db.commit.assert_called_once()


def test_create_consultant_verification_session_requires_branch_selection() -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        verification_service.create_consultant_verification_session(
            db=Mock(),
            context=_build_context(role="owner"),
            request=ConsoleConsultantVerificationSessionCreateRequest(),
            allowed_branch_ids=None,
            now=datetime.now(timezone.utc),
        )

    assert exc_info.value.code == "BRANCH_SELECTION_REQUIRED"


@pytest.mark.asyncio
async def test_append_consultant_verification_message_uses_bound_draft_truth(monkeypatch) -> None:
    branch_id = uuid4()
    context = _build_context(role="owner", branch_id=branch_id)
    now = datetime.now(timezone.utc)
    session_row = SimpleNamespace(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch_id,
        actor_agent_id=context.agent.id,
        actor_role=context.role,
        source_mode="draft",
        challenge_mode="as_client",
        status="active",
        title="Draft session",
        remote_jid="console-verification@test",
        runtime_snapshot={},
        latest_preview={},
        turns_total=0,
        latest_outcome=None,
        latest_business_verdict=None,
        created_at=now,
        updated_at=now,
        last_message_at=None,
    )
    db = Mock()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        verification_service,
        "_get_session_for_context",
        lambda **_kwargs: session_row,
    )
    monkeypatch.setattr(
        verification_service,
        "_load_session_turns",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        verification_service,
        "_resolve_verification_session_runtime_truth",
        lambda **_kwargs: (
            verification_service.RuntimeTruth(
                truth={"draft": True},
                client_slug=context.client.slug,
                branch_id=branch_id,
                source="knowledge_draft",
                version_id="draft-version-1",
                compiled_hash="compiled-1",
            ),
            {
                "truth_source": "knowledge_draft",
                "truth_version_id": "draft-version-1",
                "truth_compiled_hash": "compiled-1",
                "draft_hash": "draft-hash-1",
                "branch_id": str(branch_id),
            },
        ),
    )

    async def _fake_run(**kwargs):
        captured.update(kwargs)
        return {
            "owner": {
                "content": kwargs["content"],
                "message_metadata": {},
                "created_at": now,
            },
            "assistant": {
                "role": "consultant",
                "content": "Ответ из draft.",
                "message_metadata": {},
                "decision_meta": {},
                "decision_trace": [],
                "source_refs": ["draft"],
                "preview": {"simulation_mode": True},
                "outcome": "fact",
                "business_verdict": "answered",
                "created_at": now,
            },
            "runtime_snapshot": {"simulation_mode": True},
        }

    monkeypatch.setattr(
        verification_service,
        "_run_consultant_verification_simulation",
        _fake_run,
    )
    monkeypatch.setattr(
        verification_service,
        "_load_session_turns",
        lambda *_args, **_kwargs: [],
    )

    response = await verification_service.append_consultant_verification_message(
        db=db,
        context=context,
        session_id=session_row.id,
        content="Проверим draft",
        allowed_branch_ids=[branch_id],
        now=now,
    )

    runtime_truth = captured["runtime_truth_override"]
    assert isinstance(runtime_truth, verification_service.RuntimeTruth)
    assert runtime_truth.source == "knowledge_draft"
    assert session_row.runtime_snapshot["truth_source"] == "knowledge_draft"
    assert session_row.runtime_snapshot["draft_hash"] == "draft-hash-1"
    assert response.session.source_mode == "draft"
    db.commit.assert_called_once()


def test_get_consultant_verification_readiness_marks_first_publish_as_ready(monkeypatch) -> None:
    branch_id = uuid4()
    context = _build_context(role="owner", branch_id=branch_id)
    draft_version = KnowledgeVersion(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch_id,
        status="draft",
        payload_json={"client_pack": {"salon": {"name": "Demo"}}},
    )

    monkeypatch.setattr(
        verification_service,
        "_load_latest_draft_version",
        lambda **_kwargs: draft_version,
    )
    monkeypatch.setattr(
        verification_service,
        "_load_published_knowledge_for_branch",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        verification_service,
        "resolve_consultant_verification_enabled",
        lambda _context: True,
    )

    response = verification_service.get_consultant_verification_readiness(
        db=Mock(),
        context=context,
        allowed_branch_ids=[branch_id],
    )

    assert response.readiness.status == "ready"
    assert response.readiness.compare_required is False
    assert "Первый publish" in response.readiness.status_label


def test_get_consultant_verification_readiness_skips_compare_when_rollout_disabled(monkeypatch) -> None:
    branch_id = uuid4()
    context = _build_context(role="owner", branch_id=branch_id)
    draft_version = KnowledgeVersion(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch_id,
        status="draft",
        payload_json={"client_pack": {"salon": {"name": "Demo"}}},
    )
    live_version = KnowledgeVersion(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch_id,
        status="published",
        payload_json={"client_pack": {"salon": {"name": "Demo"}}},
    )

    monkeypatch.setattr(
        verification_service,
        "_load_latest_draft_version",
        lambda **_kwargs: draft_version,
    )
    monkeypatch.setattr(
        verification_service,
        "_load_published_knowledge_for_branch",
        lambda **_kwargs: live_version,
    )
    monkeypatch.setattr(
        verification_service,
        "resolve_consultant_verification_enabled",
        lambda _context: False,
    )

    response = verification_service.get_consultant_verification_readiness(
        db=Mock(),
        context=context,
        allowed_branch_ids=[branch_id],
    )

    assert response.readiness.status == "ready"
    assert response.readiness.compare_required is False
    assert "не требуется" in response.readiness.status_label.lower()


def test_build_consultant_verification_overview_uses_selected_branch_knowledge(monkeypatch) -> None:
    branch_id = uuid4()
    context = _build_context(role="owner", branch_id=branch_id)
    captured: dict[str, object] = {}
    version = KnowledgeVersion(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch_id,
        status="published",
        payload_json={"client_pack": {"salon": {"name": "Demo"}}},
        published_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        sync_status="ready",
    )

    monkeypatch.setattr(
        verification_service,
        "_load_effective_capabilities",
        lambda *_args, **_kwargs: CapabilitiesPayload(),
    )
    monkeypatch.setattr(
        verification_service,
        "_load_reference_pack",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        verification_service,
        "_build_scenario_catalog",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        verification_service,
        "_load_published_knowledge_for_branch",
        lambda **kwargs: captured.update(kwargs) or version,
    )

    response = verification_service.build_consultant_verification_overview(
        db=Mock(),
        context=context,
        now=datetime.now(timezone.utc),
        allowed_branch_ids=[branch_id],
    )

    assert captured["branch_id"] == branch_id
    assert response.status == "ready"
    assert response.branch_selection_required is False
    assert response.selected_branch_id == branch_id
    assert response.selected_branch_name == "Almaty Downtown"
    assert response.knowledge_sync_status == "ready"


def test_build_consultant_verification_overview_blocks_pending_knowledge_sync(monkeypatch) -> None:
    branch_id = uuid4()
    context = _build_context(role="owner", branch_id=branch_id)
    version = KnowledgeVersion(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch_id,
        status="published",
        payload_json={"client_pack": {"salon": {"name": "Demo"}}},
        published_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        sync_status="pending",
    )

    monkeypatch.setattr(
        verification_service,
        "_load_effective_capabilities",
        lambda *_args, **_kwargs: CapabilitiesPayload(),
    )
    monkeypatch.setattr(
        verification_service,
        "_load_reference_pack",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        verification_service,
        "_build_scenario_catalog",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        verification_service,
        "_load_published_knowledge_for_branch",
        lambda **_kwargs: version,
    )

    response = verification_service.build_consultant_verification_overview(
        db=Mock(),
        context=context,
        now=datetime.now(timezone.utc),
        allowed_branch_ids=[branch_id],
    )

    assert response.status == "needs_attention"
    assert response.knowledge_sync_status == "pending"
    assert "синхронизац" in response.summary.lower()


def test_build_consultant_verification_overview_flags_failed_knowledge_sync(monkeypatch) -> None:
    branch_id = uuid4()
    context = _build_context(role="owner", branch_id=branch_id)
    context.branches[0].knowledge_safe_mode = True
    context.branches[0].knowledge_safe_mode_reason = "timed out"
    version = KnowledgeVersion(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch_id,
        status="published",
        payload_json={"client_pack": {"salon": {"name": "Demo"}}},
        published_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        sync_status="failed",
        sync_error="timed out",
    )

    monkeypatch.setattr(
        verification_service,
        "_load_effective_capabilities",
        lambda *_args, **_kwargs: CapabilitiesPayload(),
    )
    monkeypatch.setattr(
        verification_service,
        "_load_reference_pack",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        verification_service,
        "_build_scenario_catalog",
        lambda **_kwargs: [],
    )
    monkeypatch.setattr(
        verification_service,
        "_load_published_knowledge_for_branch",
        lambda **_kwargs: version,
    )

    response = verification_service.build_consultant_verification_overview(
        db=Mock(),
        context=context,
        now=datetime.now(timezone.utc),
        allowed_branch_ids=[branch_id],
    )

    assert response.status == "needs_attention"
    assert response.knowledge_sync_status == "failed"
    assert response.knowledge_sync_error == "timed out"
    assert response.knowledge_safe_mode is True
    assert "синхронизац" in response.summary.lower()
