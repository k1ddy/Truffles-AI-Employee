from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.branch import Branch
from app.models.client_capability import ClientCapability
from app.models.client_onboarding_contract import ClientOnboardingContract
from app.models.client_settings import ClientSettings
from app.models.reference_pack import ReferencePack
from app.models.specialist import Specialist
from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.onboarding_contract import OnboardingContractPayload
from app.services.audit_service import record_audit_event
from app.services.capabilities_service import merge_capabilities
from app.services.console_errors import ConsoleAPIError
from app.services.knowledge_registry_service import get_current_published
from app.services.knowledge_validation import get_missing_required_fields
from app.services.onboarding_contract_service import (
    find_capability_mismatches,
    merge_onboarding_contract,
)
from app.services.reference_pack_integrity import evaluate_reference_pack_integrity


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
class OnboardingContractContext:
    has_records: bool
    payload: OnboardingContractPayload
    payment_status: str
    payment_confirmed: bool
    payment_confirmed_at: Optional[datetime]
    payment_confirmed_by: Optional[UUID]


@dataclass(frozen=True)
class OnboardingInputs:
    has_capabilities: bool
    capabilities: CapabilitiesPayload
    has_onboarding_contract: bool
    onboarding_contract: OnboardingContractPayload
    payment_status: str
    payment_confirmed: bool
    payment_confirmed_at: Optional[datetime]
    payment_confirmed_by: Optional[UUID]
    has_webhook_secret: bool
    has_reference_pack: bool
    has_reference_pack_integrity: bool
    reference_pack_integrity_missing: list[str]
    reference_pack_domain_slug: Optional[str]
    capability_mismatches: list[str]
    instance_id: Optional[str]
    has_instance_id: bool
    has_phone: bool
    branch_is_active: bool
    has_team: bool
    has_telegram_chat: bool
    has_knowledge_tag: bool
    has_published_knowledge: bool
    missing_pack_fields: list[str]
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


@dataclass(frozen=True)
class OnboardingScorecardCheck:
    id: OnboardingStep
    required: bool
    passed: bool
    missing: list[str]


@dataclass(frozen=True)
class OnboardingScorecard:
    ready: bool
    checks: list[OnboardingScorecardCheck]
    missing: list[str]


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
    client_id: UUID,
    scope: str,
    branch_id: Optional[UUID],
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


def _get_latest_onboarding_contract(
    db: Session,
    *,
    client_id: UUID,
    scope: str,
    branch_id: Optional[UUID],
) -> Optional[ClientOnboardingContract]:
    query = db.query(ClientOnboardingContract).filter(
        ClientOnboardingContract.client_id == client_id,
        ClientOnboardingContract.scope == scope,
    )
    if branch_id:
        query = query.filter(ClientOnboardingContract.branch_id == branch_id)
    else:
        query = query.filter(ClientOnboardingContract.branch_id.is_(None))
    return query.order_by(
        ClientOnboardingContract.updated_at.desc(),
        ClientOnboardingContract.created_at.desc(),
    ).first()


def _load_onboarding_contract(db: Session, branch: Branch) -> OnboardingContractContext:
    client_record = _get_latest_onboarding_contract(
        db,
        client_id=branch.client_id,
        scope="client",
        branch_id=None,
    )
    branch_record = _get_latest_onboarding_contract(
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
    payload = OnboardingContractPayload.model_validate(
        merge_onboarding_contract(client_payload, branch_payload)
    )
    has_records = bool(client_payload or branch_payload)

    payment_source = None
    if branch_record and branch_record.status == "active":
        payment_source = branch_record
    elif client_record and client_record.status == "active":
        payment_source = client_record

    payment_status = payment_source.payment_status if payment_source else "pending"
    payment_confirmed = payment_status == "confirmed"
    payment_confirmed_at = payment_source.payment_confirmed_at if payment_source else None
    payment_confirmed_by = payment_source.payment_confirmed_by if payment_source else None

    return OnboardingContractContext(
        has_records=has_records,
        payload=payload,
        payment_status=payment_status,
        payment_confirmed=payment_confirmed,
        payment_confirmed_at=payment_confirmed_at,
        payment_confirmed_by=payment_confirmed_by,
    )


def _has_non_empty_dict(value: Optional[dict]) -> bool:
    if not value or not isinstance(value, dict):
        return False
    return bool(value)


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        return None


def build_onboarding_inputs(db: Session, branch: Branch) -> OnboardingInputs:
    capabilities = _load_capabilities(db, branch)
    onboarding_contract = _load_onboarding_contract(db, branch)

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

    published_version = get_current_published(db, branch_id=branch.id)
    has_published_knowledge = published_version is not None
    missing_pack_fields: list[str] = []

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

    has_webhook_secret = bool((getattr(branch, "webhook_secret", None) or "").strip())
    if not has_webhook_secret:
        settings = db.query(ClientSettings).filter(ClientSettings.client_id == branch.client_id).first()
        has_webhook_secret = bool(settings and (settings.webhook_secret or "").strip())

    reference_pack_domain_slug = (
        onboarding_contract.payload.domain_slug or capabilities.payload.domain_slug
    )
    has_reference_pack = False
    has_reference_pack_integrity = False
    reference_pack_integrity_missing: list[str] = []
    if reference_pack_domain_slug:
        reference_pack_record = (
            db.query(ReferencePack)
            .filter(
                ReferencePack.domain_slug == reference_pack_domain_slug,
                ReferencePack.status == "active",
            )
            .first()
        )
        has_reference_pack = reference_pack_record is not None
        if reference_pack_record:
            reference_pack_integrity_missing = evaluate_reference_pack_integrity(
                domain_slug=reference_pack_domain_slug,
                schema_version=reference_pack_record.schema_version,
                metadata=reference_pack_record.metadata_json,
            )
            has_reference_pack_integrity = len(reference_pack_integrity_missing) == 0

    capability_mismatches: list[str] = []
    if capabilities.has_records and onboarding_contract.has_records:
        capability_mismatches = find_capability_mismatches(
            purchased=onboarding_contract.payload.purchased,
            effective=capabilities.payload,
        )
    booking_required = capabilities.payload.features.booking_mode is not None
    if published_version and isinstance(published_version.payload_json, dict):
        missing_pack_fields = get_missing_required_fields(
            published_version.payload_json,
            domain_slug=reference_pack_domain_slug,
            require_booking=booking_required,
        )
    instance_id = (branch.instance_id or "").strip() or None

    return OnboardingInputs(
        has_capabilities=capabilities.has_records,
        capabilities=capabilities.payload,
        has_onboarding_contract=onboarding_contract.has_records,
        onboarding_contract=onboarding_contract.payload,
        payment_status=onboarding_contract.payment_status,
        payment_confirmed=onboarding_contract.payment_confirmed,
        payment_confirmed_at=onboarding_contract.payment_confirmed_at,
        payment_confirmed_by=onboarding_contract.payment_confirmed_by,
        has_webhook_secret=has_webhook_secret,
        has_reference_pack=has_reference_pack,
        has_reference_pack_integrity=has_reference_pack_integrity,
        reference_pack_integrity_missing=reference_pack_integrity_missing,
        reference_pack_domain_slug=reference_pack_domain_slug,
        capability_mismatches=capability_mismatches,
        instance_id=instance_id,
        has_instance_id=bool(instance_id),
        has_phone=bool(branch.phone),
        branch_is_active=bool(branch.is_active),
        has_team=has_team,
        has_telegram_chat=bool(branch.telegram_chat_id),
        has_knowledge_tag=bool(branch.knowledge_tag),
        has_published_knowledge=has_published_knowledge,
        missing_pack_fields=missing_pack_fields,
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
        if not inputs.has_phone:
            missing.append("phone")
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
        if inputs.has_published_knowledge and inputs.missing_pack_fields:
            missing.extend(inputs.missing_pack_fields)
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
            missing.append("capabilities")
        if not inputs.has_onboarding_contract:
            missing.append("onboarding_contract")
        if not inputs.payment_confirmed:
            missing.append("payment_confirmed")
        if not inputs.has_webhook_secret:
            missing.append("webhook_secret")
        if not inputs.reference_pack_domain_slug:
            missing.append("reference_pack_domain")
        elif not inputs.has_reference_pack:
            missing.append("reference_pack")
        elif not inputs.has_reference_pack_integrity:
            if inputs.reference_pack_integrity_missing:
                missing.extend(inputs.reference_pack_integrity_missing)
            else:
                missing.append("reference_pack_integrity")
        if inputs.capability_mismatches:
            missing.extend([f"capability_mismatch:{item}" for item in inputs.capability_mismatches])

        if inputs.has_capabilities and inputs.capabilities.channels.whatsapp is True:
            if not inputs.has_instance_id:
                missing.append("instance_id")
            if not inputs.has_phone:
                missing.append("phone")
            if not inputs.branch_is_active:
                missing.append("branch_active")
            whatsapp_binding = inputs.onboarding_contract.provider_binding.whatsapp
            if not whatsapp_binding:
                missing.append("provider_binding.whatsapp")
            else:
                if not whatsapp_binding.provider:
                    missing.append("provider_binding.whatsapp.provider")
                if not whatsapp_binding.instance_id:
                    missing.append("provider_binding.whatsapp.instance_id")
                elif inputs.instance_id and whatsapp_binding.instance_id != inputs.instance_id:
                    missing.append("provider_binding.whatsapp.instance_id_mismatch")
                if whatsapp_binding.webhook_status != "configured":
                    missing.append("provider_binding.whatsapp.webhook_status")

                paid_until = _parse_iso_date(whatsapp_binding.paid_until)
                if not paid_until:
                    missing.append("provider_binding.whatsapp.paid_until")
                elif paid_until < datetime.now(timezone.utc).date():
                    missing.append("provider_binding.whatsapp.paid_until_expired")

        if (
            inputs.has_capabilities
            and inputs.capabilities.channels.telegram is True
            and not inputs.has_telegram_chat
        ):
            missing.append("telegram_chat_id")

        if inputs.has_capabilities and inputs.capabilities.features.knowledge_upload is True:
            if not inputs.has_knowledge_tag:
                missing.append("knowledge_tag")
            if not inputs.has_published_knowledge:
                missing.append("knowledge_published")
            if inputs.has_published_knowledge and inputs.missing_pack_fields:
                missing.extend(inputs.missing_pack_fields)

        if inputs.has_capabilities and inputs.capabilities.features.booking_mode is not None:
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


def _deduplicate_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def build_onboarding_scorecard_from_inputs(inputs: OnboardingInputs) -> OnboardingScorecard:
    checks: list[OnboardingScorecardCheck] = []
    for step in ONBOARDING_STEPS:
        required = is_step_required(step, inputs)
        missing = _deduplicate_strings(missing_prerequisites(step, inputs)) if required else []
        checks.append(
            OnboardingScorecardCheck(
                id=step,
                required=required,
                passed=len(missing) == 0,
                missing=missing,
            )
        )

    go_no_go_missing = _deduplicate_strings(missing_prerequisites(OnboardingStep.GO_NO_GO, inputs))
    return OnboardingScorecard(
        ready=len(go_no_go_missing) == 0,
        checks=checks,
        missing=go_no_go_missing,
    )


def build_onboarding_scorecard(db: Session, branch: Branch) -> OnboardingScorecard:
    inputs = build_onboarding_inputs(db, branch)
    return build_onboarding_scorecard_from_inputs(inputs)


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
