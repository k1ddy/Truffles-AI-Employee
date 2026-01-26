from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.branch import Branch
from app.models.client_capability import ClientCapability
from app.models.knowledge_version import KnowledgeVersion
from app.models.specialist import Specialist
from app.schemas.capabilities import CapabilitiesPayload
from app.services.audit_service import record_audit_event
from app.services.capabilities_service import merge_capabilities
from app.services.console_errors import ConsoleAPIError


class OnboardingStep(str, Enum):
    BRANCH_DRAFT = "branch_draft"
    INTEGRATIONS = "integrations"
    TEAM = "team"
    TELEGRAM = "telegram"
    KNOWLEDGE = "knowledge"
    BOOKING = "booking"
    GO_NO_GO = "go_no_go"


ONBOARDING_STEPS = [
    OnboardingStep.BRANCH_DRAFT,
    OnboardingStep.INTEGRATIONS,
    OnboardingStep.TEAM,
    OnboardingStep.TELEGRAM,
    OnboardingStep.KNOWLEDGE,
    OnboardingStep.BOOKING,
    OnboardingStep.GO_NO_GO,
]

STEP_INDEX = {step: index for index, step in enumerate(ONBOARDING_STEPS)}


@dataclass(frozen=True)
class CapabilitiesContext:
    has_records: bool
    payload: CapabilitiesPayload


@dataclass(frozen=True)
class OnboardingInputs:
    has_capabilities: bool
    capabilities: CapabilitiesPayload
    has_instance_id: bool
    branch_is_active: bool
    has_team: bool
    has_telegram_chat: bool
    has_knowledge_tag: bool
    has_published_knowledge: bool
    has_working_hours: bool
    has_booking_settings: bool
    has_specialists: bool


@dataclass(frozen=True)
class OnboardingStepInfo:
    id: OnboardingStep
    status: str
    required: bool
    missing: list[str]


@dataclass(frozen=True)
class OnboardingStatus:
    current_step: OnboardingStep
    steps: list[OnboardingStepInfo]


def _parse_onboarding_state(value: Optional[str]) -> Optional[OnboardingStep]:
    if not value:
        return None
    try:
        return OnboardingStep(value)
    except ValueError:
        return None


def _get_latest_capability(
    db: Session,
    *,
    client_id,
    scope: str,
    branch_id: Optional,
) -> Optional[ClientCapability]:
    query = db.query(ClientCapability).filter(
        ClientCapability.client_id == client_id,
        ClientCapability.scope == scope,
    )
    if branch_id:
        query = query.filter(ClientCapability.branch_id == branch_id)
    else:
        query = query.filter(ClientCapability.branch_id.is_(None))
    return query.order_by(
        ClientCapability.updated_at.desc(),
        ClientCapability.created_at.desc(),
    ).first()


def _load_capabilities(db: Session, branch: Branch) -> CapabilitiesContext:
    client_record = _get_latest_capability(
        db,
        client_id=branch.client_id,
        scope="client",
        branch_id=None,
    )
    branch_record = _get_latest_capability(
        db,
        client_id=branch.client_id,
        scope="branch",
        branch_id=branch.id,
    )

    client_payload = (
        client_record.payload_json if client_record and client_record.status == "active" else None
    )
    branch_payload = (
        branch_record.payload_json if branch_record and branch_record.status == "active" else None
    )

    payload = CapabilitiesPayload.model_validate(merge_capabilities(client_payload, branch_payload))
    has_records = bool(client_payload or branch_payload)
    return CapabilitiesContext(has_records=has_records, payload=payload)


def _has_non_empty_dict(value: Optional[dict]) -> bool:
    if not value or not isinstance(value, dict):
        return False
    return bool(value)


def build_onboarding_inputs(db: Session, branch: Branch) -> OnboardingInputs:
    capabilities = _load_capabilities(db, branch)

    has_team = (
        db.query(Agent)
        .filter(
            Agent.client_id == branch.client_id,
            Agent.role.in_(["owner", "admin"]),
            Agent.is_active.is_(True),
        )
        .first()
        is not None
    )

    has_published_knowledge = (
        db.query(KnowledgeVersion)
        .filter(
            KnowledgeVersion.branch_id == branch.id,
            KnowledgeVersion.status == "published",
        )
        .first()
        is not None
    )

    has_specialists = (
        db.query(Specialist)
        .filter(
            Specialist.client_id == branch.client_id,
            Specialist.branch_id == branch.id,
            Specialist.is_active.is_(True),
        )
        .first()
        is not None
    )

    return OnboardingInputs(
        has_capabilities=capabilities.has_records,
        capabilities=capabilities.payload,
        has_instance_id=bool(branch.instance_id),
        branch_is_active=bool(branch.is_active),
        has_team=has_team,
        has_telegram_chat=bool(branch.telegram_chat_id),
        has_knowledge_tag=bool(branch.knowledge_tag),
        has_published_knowledge=has_published_knowledge,
        has_working_hours=_has_non_empty_dict(branch.working_hours),
        has_booking_settings=_has_non_empty_dict(branch.booking_settings),
        has_specialists=has_specialists,
    )


def is_step_required(step: OnboardingStep, inputs: OnboardingInputs) -> bool:
    if step in (OnboardingStep.BRANCH_DRAFT, OnboardingStep.TEAM, OnboardingStep.GO_NO_GO):
        return True
    if not inputs.has_capabilities:
        return True
    if step == OnboardingStep.INTEGRATIONS:
        return inputs.capabilities.channels.whatsapp is True
    if step == OnboardingStep.TELEGRAM:
        return inputs.capabilities.channels.telegram is True
    if step == OnboardingStep.KNOWLEDGE:
        return inputs.capabilities.features.knowledge_upload is True
    if step == OnboardingStep.BOOKING:
        return inputs.capabilities.features.booking_mode is not None
    return True


def missing_prerequisites(step: OnboardingStep, inputs: OnboardingInputs) -> list[str]:
    missing: list[str] = []

    if step == OnboardingStep.INTEGRATIONS:
        if not inputs.has_instance_id:
            missing.append("instance_id")
        return missing

    if step == OnboardingStep.TEAM:
        if not inputs.has_team:
            missing.append("owner_admin")
        return missing

    if step == OnboardingStep.TELEGRAM:
        if not inputs.has_telegram_chat:
            missing.append("telegram_chat_id")
        return missing

    if step == OnboardingStep.KNOWLEDGE:
        if not inputs.has_knowledge_tag:
            missing.append("knowledge_tag")
        if not inputs.has_published_knowledge:
            missing.append("knowledge_published")
        return missing

    if step == OnboardingStep.BOOKING:
        if not inputs.has_working_hours:
            missing.append("working_hours")
        if not inputs.has_booking_settings:
            missing.append("booking_settings")
        if not inputs.has_specialists:
            missing.append("specialists")
        return missing

    if step == OnboardingStep.GO_NO_GO:
        if not inputs.has_capabilities:
            return ["capabilities"]

        if inputs.capabilities.channels.whatsapp is True:
            if not inputs.has_instance_id:
                missing.append("instance_id")
            if not inputs.branch_is_active:
                missing.append("branch_active")

        if inputs.capabilities.channels.telegram is True and not inputs.has_telegram_chat:
            missing.append("telegram_chat_id")

        if inputs.capabilities.features.knowledge_upload is True:
            if not inputs.has_knowledge_tag:
                missing.append("knowledge_tag")
            if not inputs.has_published_knowledge:
                missing.append("knowledge_published")

        if inputs.capabilities.features.booking_mode is not None:
            if not inputs.has_working_hours:
                missing.append("working_hours")
            if not inputs.has_booking_settings:
                missing.append("booking_settings")
            if not inputs.has_specialists:
                missing.append("specialists")

        return missing

    return missing


def _step_is_ready(step: OnboardingStep, inputs: OnboardingInputs) -> bool:
    if not is_step_required(step, inputs):
        return True
    return len(missing_prerequisites(step, inputs)) == 0


def derive_last_completed_step(inputs: OnboardingInputs) -> OnboardingStep:
    last_completed = OnboardingStep.BRANCH_DRAFT
    for step in ONBOARDING_STEPS[1:]:
        if _step_is_ready(step, inputs):
            last_completed = step
        else:
            break
    return last_completed


def resolve_last_completed_step(branch: Branch, inputs: OnboardingInputs) -> OnboardingStep:
    stored = _parse_onboarding_state(branch.onboarding_state)
    derived = derive_last_completed_step(inputs)
    if not stored:
        return derived
    if STEP_INDEX[stored] <= STEP_INDEX[derived]:
        return stored
    return derived


def can_advance_to_step(
    current_step: OnboardingStep, target_step: OnboardingStep, inputs: OnboardingInputs
) -> bool:
    if STEP_INDEX[target_step] <= STEP_INDEX[current_step]:
        return True
    for step in ONBOARDING_STEPS[STEP_INDEX[current_step] + 1 : STEP_INDEX[target_step]]:
        if is_step_required(step, inputs):
            return False
    return True


def _first_required_step_between(
    current_step: OnboardingStep, target_step: OnboardingStep, inputs: OnboardingInputs
) -> OnboardingStep:
    for step in ONBOARDING_STEPS[STEP_INDEX[current_step] + 1 : STEP_INDEX[target_step]]:
        if is_step_required(step, inputs):
            return step
    return target_step


def ensure_onboarding_step(db: Session, branch: Branch, target_step: OnboardingStep) -> None:
    inputs = build_onboarding_inputs(db, branch)
    current_step = resolve_last_completed_step(branch, inputs)
    if not can_advance_to_step(current_step, target_step, inputs):
        required_step = _first_required_step_between(current_step, target_step, inputs)
        raise ConsoleAPIError(
            409,
            "ONBOARDING_STEP_REQUIRED",
            "Complete previous onboarding step",
            {
                "current_step": current_step.value,
                "required_step": required_step.value,
                "target_step": target_step.value,
            },
        )


def advance_onboarding_step(
    db: Session,
    branch: Branch,
    target_step: OnboardingStep,
    *,
    actor,
) -> OnboardingStatus:
    inputs = build_onboarding_inputs(db, branch)
    current_step = resolve_last_completed_step(branch, inputs)

    if STEP_INDEX[target_step] <= STEP_INDEX[current_step]:
        return build_onboarding_status(db, branch)

    if not can_advance_to_step(current_step, target_step, inputs):
        required_step = _first_required_step_between(current_step, target_step, inputs)
        raise ConsoleAPIError(
            409,
            "ONBOARDING_STEP_REQUIRED",
            "Complete previous onboarding step",
            {
                "current_step": current_step.value,
                "required_step": required_step.value,
                "target_step": target_step.value,
            },
        )

    if is_step_required(target_step, inputs):
        missing = missing_prerequisites(target_step, inputs)
        if missing:
            raise ConsoleAPIError(
                409,
                "ONBOARDING_STEP_REQUIRED",
                "Onboarding step prerequisites missing",
                {
                    "current_step": current_step.value,
                    "required_step": target_step.value,
                    "missing": missing,
                },
            )

    now = datetime.now(timezone.utc)
    branch.onboarding_state = target_step.value
    branch.onboarding_updated_at = now
    branch.updated_at = now

    record_audit_event(
        db,
        actor=actor,
        event_type="onboarding_step_advanced",
        entity_type="branch",
        entity_id=branch.id,
        payload={
            "from": current_step.value,
            "to": target_step.value,
        },
        client_id=branch.client_id,
        branch_id=branch.id,
    )

    return build_onboarding_status(db, branch)


def build_onboarding_status(db: Session, branch: Branch) -> OnboardingStatus:
    inputs = build_onboarding_inputs(db, branch)
    last_completed = resolve_last_completed_step(branch, inputs)

    steps: list[OnboardingStepInfo] = []
    current_step: Optional[OnboardingStep] = None

    for step in ONBOARDING_STEPS:
        if STEP_INDEX[step] <= STEP_INDEX[last_completed]:
            steps.append(
                OnboardingStepInfo(
                    id=step,
                    status="complete",
                    required=is_step_required(step, inputs),
                    missing=[],
                )
            )
            continue

        if current_step is None:
            required = is_step_required(step, inputs)
            if not required:
                steps.append(
                    OnboardingStepInfo(
                        id=step,
                        status="skipped",
                        required=False,
                        missing=[],
                    )
                )
                last_completed = step
                continue

            missing = missing_prerequisites(step, inputs)
            steps.append(
                OnboardingStepInfo(
                    id=step,
                    status="available",
                    required=True,
                    missing=missing,
                )
            )
            current_step = step
            continue

        steps.append(
            OnboardingStepInfo(
                id=step,
                status="locked",
                required=is_step_required(step, inputs),
                missing=[],
            )
        )

    if current_step is None:
        current_step = OnboardingStep.GO_NO_GO

    return OnboardingStatus(current_step=current_step, steps=steps)
