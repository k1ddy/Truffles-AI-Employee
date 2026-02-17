from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.branch import Branch
from app.models.client_capability import ClientCapability
from app.models.client_onboarding_contract import ClientOnboardingContract
from app.models.client_settings import ClientSettings
from app.models.conversation import Conversation
from app.models.handover import Handover
from app.models.knowledge_version import KnowledgeVersion
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

_DOCUMENT_INGESTION_CRITICAL_FIELDS = {
    "client_pack.booking.collect_fields",
    "client_pack.booking.bot_can_confirm",
    "client_pack.policy.hard_law",
    "client_pack.policy.payment_info",
    "client_pack.policy.reschedule",
    "client_pack.policy.cancel",
    "client_pack.policy.medical",
    "client_pack.policy.legal",
    "client_pack.policy.complaint",
    "client_pack.policy.discounts",
    "client_pack.policy.guard_topics.refund",
}

_DEFAULT_REMINDER_1_MINUTES = 10
_DEFAULT_REMINDER_2_MINUTES = 45
_DEFAULT_ESCALATION_TIMEOUT_MINUTES = 120
_SLA_ACTIVE_HANDOVER_STATUSES = ("pending", "active")


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
    document_ingestion_valid: bool
    document_ingestion_source: str
    document_ingestion_missing_fields: list[str]
    document_ingestion_critical_missing_fields: list[str]
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
class OnboardingDocumentIngestion:
    status: str
    valid: bool
    source: str
    missing_fields: list[str]
    critical_missing_fields: list[str]


@dataclass(frozen=True)
class OnboardingSlaControlLoop:
    status: str
    reminder_1_minutes: int
    reminder_2_minutes: int
    escalation_timeout_minutes: int
    pending_total: int
    warning_total: int
    breached_total: int
    provider_status: str
    provider_paid_until: Optional[str]
    provider_days_to_renewal: Optional[int]
    provider_alert_state: str
    active_incidents: list[str]
    recommended_actions: list[str]


@dataclass(frozen=True)
class OnboardingOperationalStage:
    id: str
    label: str
    owner_lane: str
    required: bool
    status: str
    blockers: list[str]
    next_action: Optional[str]


@dataclass(frozen=True)
class OnboardingOperationalPipeline:
    status: str
    blocked: bool
    current_stage_id: Optional[str]
    blockers: list[str]
    next_actions: list[str]
    stages: list[OnboardingOperationalStage]


@dataclass(frozen=True)
class OnboardingScorecard:
    ready: bool
    checks: list[OnboardingScorecardCheck]
    missing: list[str]
    document_ingestion: Optional[OnboardingDocumentIngestion] = None
    sla_control_loop: Optional[OnboardingSlaControlLoop] = None
    operational_pipeline: Optional[OnboardingOperationalPipeline] = None


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


def _normalize_timeout_minutes(value: Optional[int], *, fallback: int, minimum: int) -> int:
    if value is None:
        return fallback
    if value < minimum:
        return minimum
    return value


def _resolve_sla_thresholds(db: Session, branch: Branch) -> tuple[int, int, int]:
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == branch.client_id).first()
    reminder_1 = _normalize_timeout_minutes(
        settings.reminder_timeout_1 if settings else None,
        fallback=_DEFAULT_REMINDER_1_MINUTES,
        minimum=1,
    )
    reminder_2 = _normalize_timeout_minutes(
        settings.reminder_timeout_2 if settings else None,
        fallback=_DEFAULT_REMINDER_2_MINUTES,
        minimum=reminder_1 + 1,
    )
    escalation = _normalize_timeout_minutes(
        settings.auto_close_timeout if settings else None,
        fallback=_DEFAULT_ESCALATION_TIMEOUT_MINUTES,
        minimum=reminder_2 + 1,
    )
    return reminder_1, reminder_2, escalation


def _build_sla_control_loop(
    db: Session,
    branch: Branch,
    *,
    inputs: OnboardingInputs,
) -> OnboardingSlaControlLoop:
    reminder_1, reminder_2, escalation_timeout = _resolve_sla_thresholds(db, branch)
    now = datetime.now(timezone.utc)

    unresolved_query = (
        db.query(Handover)
        .join(Conversation, Handover.conversation_id == Conversation.id)
        .filter(
            Handover.client_id == branch.client_id,
            Conversation.branch_id == branch.id,
            Handover.status.in_(_SLA_ACTIVE_HANDOVER_STATUSES),
        )
    )
    pending_total = unresolved_query.count()
    warning_cutoff = now - timedelta(minutes=reminder_2)
    breach_cutoff = now - timedelta(minutes=escalation_timeout)
    warning_total = unresolved_query.filter(
        Handover.created_at <= warning_cutoff,
        Handover.created_at > breach_cutoff,
    ).count()
    breached_total = unresolved_query.filter(Handover.created_at <= breach_cutoff).count()

    provider_status = "not_required"
    provider_paid_until: Optional[str] = None
    provider_days_to_renewal: Optional[int] = None
    provider_alert_state = "unknown"

    whatsapp_required = (
        inputs.has_capabilities
        and inputs.capabilities.channels.whatsapp is True
    )
    whatsapp_binding = inputs.onboarding_contract.provider_binding.whatsapp
    if whatsapp_required:
        if not whatsapp_binding:
            provider_status = "missing"
        else:
            provider_alert_state = (whatsapp_binding.alert_state or "unknown").strip() or "unknown"
            provider_paid_until = whatsapp_binding.paid_until or whatsapp_binding.next_renewal_at
            renewal_anchor = whatsapp_binding.next_renewal_at or whatsapp_binding.paid_until
            renewal_until = _parse_iso_date(renewal_anchor)
            if renewal_until is not None:
                provider_days_to_renewal = (renewal_until - now.date()).days

            if whatsapp_binding.rebind_required is True or whatsapp_binding.webhook_status == "rebind_required":
                provider_status = "rebind_required"
            elif whatsapp_binding.webhook_status != "configured":
                provider_status = "webhook_not_configured"
            elif provider_days_to_renewal is not None and provider_days_to_renewal < 0:
                provider_status = "billing_expired"
            elif provider_days_to_renewal is not None and provider_days_to_renewal <= 3:
                provider_status = "renewal_due"
            else:
                provider_status = "configured"

    incidents: list[str] = []
    if breached_total > 0:
        incidents.append("handover_sla_breached")
    if warning_total > 0:
        incidents.append("handover_sla_warning")
    if provider_status == "missing":
        incidents.append("provider_binding_missing")
    elif provider_status == "webhook_not_configured":
        incidents.append("provider_webhook_not_configured")
    elif provider_status == "rebind_required":
        incidents.append("provider_rebind_required")
    elif provider_status == "billing_expired":
        incidents.append("provider_billing_expired")
    elif provider_status == "renewal_due":
        incidents.append("provider_renewal_due")
    if provider_alert_state == "critical":
        incidents.append("provider_capability_alert_critical")
    elif provider_alert_state == "warn":
        incidents.append("provider_capability_alert_warn")

    recommended_actions: list[str] = []
    if breached_total > 0:
        recommended_actions.append("resolve_breached_handovers")
    elif warning_total > 0:
        recommended_actions.append("review_pending_handovers")
    if provider_status in {"missing", "webhook_not_configured", "rebind_required"}:
        recommended_actions.append("fix_provider_binding")
    if provider_status == "billing_expired":
        recommended_actions.append("renew_provider_subscription_urgent")
    elif provider_status == "renewal_due":
        recommended_actions.append("renew_provider_subscription")
    if provider_alert_state == "critical":
        recommended_actions.append("run_provider_capability_check")
    if not recommended_actions:
        recommended_actions.append("monitor_sla_loop")

    if (
        breached_total > 0
        or provider_status in {"missing", "webhook_not_configured", "rebind_required", "billing_expired"}
        or provider_alert_state == "critical"
    ):
        status = "fail"
    elif warning_total > 0 or provider_status in {"renewal_due", "unknown"} or provider_alert_state == "warn":
        status = "warn"
    else:
        status = "pass"

    return OnboardingSlaControlLoop(
        status=status,
        reminder_1_minutes=reminder_1,
        reminder_2_minutes=reminder_2,
        escalation_timeout_minutes=escalation_timeout,
        pending_total=pending_total,
        warning_total=warning_total,
        breached_total=breached_total,
        provider_status=provider_status,
        provider_paid_until=provider_paid_until,
        provider_days_to_renewal=provider_days_to_renewal,
        provider_alert_state=provider_alert_state,
        active_incidents=_deduplicate_strings(incidents),
        recommended_actions=_deduplicate_strings(recommended_actions),
    )


def _get_latest_draft(db: Session, branch: Branch) -> Optional[KnowledgeVersion]:
    return (
        db.query(KnowledgeVersion)
        .filter(
            KnowledgeVersion.branch_id == branch.id,
            KnowledgeVersion.status == "draft",
        )
        .order_by(KnowledgeVersion.created_at.desc())
        .first()
    )


def _critical_document_missing_fields(missing_fields: list[str]) -> list[str]:
    return [field for field in missing_fields if field in _DOCUMENT_INGESTION_CRITICAL_FIELDS]


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
    draft_version = _get_latest_draft(db, branch)

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
    document_ingestion_source = "none"
    document_ingestion_missing_fields: list[str] = []
    document_ingestion_critical_missing_fields: list[str] = []
    if published_version and isinstance(published_version.payload_json, dict):
        document_ingestion_source = "published"
        document_ingestion_missing_fields = list(missing_pack_fields)
    elif draft_version and isinstance(draft_version.payload_json, dict):
        document_ingestion_source = "draft"
        document_ingestion_missing_fields = get_missing_required_fields(
            draft_version.payload_json,
            domain_slug=reference_pack_domain_slug,
            require_booking=booking_required,
        )
    document_ingestion_critical_missing_fields = _critical_document_missing_fields(
        document_ingestion_missing_fields
    )
    document_ingestion_valid = (
        document_ingestion_source != "none"
        and len(document_ingestion_missing_fields) == 0
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
        document_ingestion_valid=document_ingestion_valid,
        document_ingestion_source=document_ingestion_source,
        document_ingestion_missing_fields=document_ingestion_missing_fields,
        document_ingestion_critical_missing_fields=document_ingestion_critical_missing_fields,
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
                if not whatsapp_binding.owner:
                    missing.append("provider_binding.whatsapp.owner")
                if whatsapp_binding.webhook_status != "configured":
                    missing.append("provider_binding.whatsapp.webhook_status")
                if whatsapp_binding.rebind_required is True or whatsapp_binding.webhook_status == "rebind_required":
                    missing.append("provider_binding.whatsapp.rebind_required")
                if not whatsapp_binding.alert_state:
                    missing.append("provider_binding.whatsapp.alert_state")
                elif whatsapp_binding.alert_state == "critical":
                    missing.append("provider_binding.whatsapp.capability_check_failed")

                renewal_anchor = whatsapp_binding.next_renewal_at or whatsapp_binding.paid_until
                renewal_until = _parse_iso_date(renewal_anchor)
                if not renewal_until:
                    missing.append("provider_binding.whatsapp.next_renewal_at")
                elif renewal_until < datetime.now(timezone.utc).date():
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
            if not inputs.document_ingestion_valid:
                missing.append("document_ingestion_invalid")
                if inputs.document_ingestion_critical_missing_fields:
                    missing.extend(inputs.document_ingestion_critical_missing_fields)

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


def _collect_stage_blockers(
    missing_codes: list[str],
    *,
    exact: set[str],
    prefixes: tuple[str, ...] = (),
) -> list[str]:
    blockers: list[str] = []
    for code in missing_codes:
        if code in exact or any(code.startswith(prefix) for prefix in prefixes):
            blockers.append(code)
    return _deduplicate_strings(blockers)


def _build_pipeline_stage(
    *,
    stage_id: str,
    label: str,
    owner_lane: str,
    required: bool,
    blockers: list[str],
    next_action: Optional[str],
    forced_status: Optional[str] = None,
) -> OnboardingOperationalStage:
    if forced_status is not None:
        status = forced_status
    elif not required:
        status = "skip"
    elif blockers:
        status = "fail"
    else:
        status = "pass"
    return OnboardingOperationalStage(
        id=stage_id,
        label=label,
        owner_lane=owner_lane,
        required=required,
        status=status,
        blockers=_deduplicate_strings(blockers),
        next_action=next_action,
    )


def _build_operational_pipeline(
    *,
    inputs: OnboardingInputs,
    go_no_go_missing: list[str],
    sla_control_loop: Optional[OnboardingSlaControlLoop],
) -> OnboardingOperationalPipeline:
    contract_blockers = _collect_stage_blockers(
        go_no_go_missing,
        exact={
            "capabilities",
            "onboarding_contract",
            "payment_confirmed",
            "reference_pack_domain",
            "reference_pack",
            "reference_pack_integrity",
        },
        prefixes=("reference_pack_", "capability_mismatch:"),
    )
    channel_blockers = _collect_stage_blockers(
        go_no_go_missing,
        exact={
            "instance_id",
            "phone",
            "branch_active",
            "telegram_chat_id",
            "webhook_secret",
        },
        prefixes=("provider_binding.whatsapp",),
    )
    knowledge_blockers = _collect_stage_blockers(
        go_no_go_missing,
        exact={
            "knowledge_tag",
            "knowledge_published",
            "document_ingestion_invalid",
        },
        prefixes=("client_pack.",),
    )
    booking_blockers = _collect_stage_blockers(
        go_no_go_missing,
        exact={"working_hours", "booking_settings", "specialists"},
    )
    go_live_blockers = _deduplicate_strings(go_no_go_missing)

    channels_required = (
        inputs.has_capabilities
        and (
            inputs.capabilities.channels.whatsapp is True
            or inputs.capabilities.channels.telegram is True
        )
    )
    knowledge_required = (
        inputs.has_capabilities
        and inputs.capabilities.features.knowledge_upload is True
    )
    booking_required = (
        inputs.has_capabilities
        and inputs.capabilities.features.booking_mode is not None
    )

    stages: list[OnboardingOperationalStage] = [
        _build_pipeline_stage(
            stage_id="contract_alignment",
            label="Contract alignment",
            owner_lane="owner_admin",
            required=True,
            blockers=contract_blockers,
            next_action="complete_contract_and_payment" if contract_blockers else None,
        ),
        _build_pipeline_stage(
            stage_id="channel_readiness",
            label="Channel readiness",
            owner_lane="ops",
            required=channels_required,
            blockers=channel_blockers,
            next_action="fix_channel_bindings" if channel_blockers else None,
        ),
        _build_pipeline_stage(
            stage_id="knowledge_readiness",
            label="Knowledge readiness",
            owner_lane="knowledge",
            required=knowledge_required,
            blockers=knowledge_blockers,
            next_action="publish_knowledge_pack" if knowledge_blockers else None,
        ),
        _build_pipeline_stage(
            stage_id="booking_readiness",
            label="Booking readiness",
            owner_lane="operations",
            required=booking_required,
            blockers=booking_blockers,
            next_action="configure_booking_runtime" if booking_blockers else None,
        ),
    ]

    sla_required = sla_control_loop is not None
    sla_blockers = (
        list(sla_control_loop.active_incidents)
        if sla_control_loop and sla_control_loop.status in {"warn", "fail"}
        else []
    )
    sla_next_action = (
        (sla_control_loop.recommended_actions[0] if sla_control_loop.recommended_actions else None)
        if sla_control_loop and sla_control_loop.status in {"warn", "fail"}
        else None
    )
    stages.append(
        _build_pipeline_stage(
            stage_id="sla_escalation_loop",
            label="SLA/escalation loop",
            owner_lane="support",
            required=sla_required,
            blockers=sla_blockers,
            next_action=sla_next_action,
            forced_status=sla_control_loop.status if sla_control_loop else None,
        )
    )
    stages.append(
        _build_pipeline_stage(
            stage_id="go_live_control",
            label="Go-live control",
            owner_lane="owner_admin",
            required=True,
            blockers=go_live_blockers,
            next_action="resolve_go_live_blockers" if go_live_blockers else None,
        )
    )

    required_stages = [stage for stage in stages if stage.required]
    blocked = any(stage.status == "fail" for stage in required_stages)
    has_warning = any(stage.status == "warn" for stage in required_stages)
    if blocked:
        pipeline_status = "fail"
    elif has_warning:
        pipeline_status = "warn"
    else:
        pipeline_status = "pass"

    current_stage = next(
        (stage.id for stage in required_stages if stage.status in {"fail", "warn"}),
        (required_stages[-1].id if required_stages else None),
    )
    blocker_list = _deduplicate_strings(
        [code for stage in required_stages if stage.status == "fail" for code in stage.blockers]
    )
    next_actions = _deduplicate_strings(
        [
            stage.next_action
            for stage in required_stages
            if stage.status in {"fail", "warn"} and stage.next_action
        ]
    )
    if not next_actions:
        next_actions = ["monitor_go_live_readiness"]

    return OnboardingOperationalPipeline(
        status=pipeline_status,
        blocked=blocked,
        current_stage_id=current_stage,
        blockers=blocker_list,
        next_actions=next_actions,
        stages=stages,
    )


def build_onboarding_scorecard_from_inputs(
    inputs: OnboardingInputs,
    *,
    sla_control_loop: Optional[OnboardingSlaControlLoop] = None,
) -> OnboardingScorecard:
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
    knowledge_required = (
        inputs.has_capabilities
        and inputs.capabilities.features.knowledge_upload is True
    )
    document_ingestion_status = OnboardingDocumentIngestion(
        status=(
            "skipped"
            if not knowledge_required
            else ("pass" if inputs.document_ingestion_valid else "fail")
        ),
        valid=(inputs.document_ingestion_valid if knowledge_required else True),
        source=inputs.document_ingestion_source,
        missing_fields=(
            _deduplicate_strings(inputs.document_ingestion_missing_fields)
            if knowledge_required
            else []
        ),
        critical_missing_fields=(
            _deduplicate_strings(inputs.document_ingestion_critical_missing_fields)
            if knowledge_required
            else []
        ),
    )
    operational_pipeline = _build_operational_pipeline(
        inputs=inputs,
        go_no_go_missing=go_no_go_missing,
        sla_control_loop=sla_control_loop,
    )
    return OnboardingScorecard(
        ready=len(go_no_go_missing) == 0,
        checks=checks,
        missing=go_no_go_missing,
        document_ingestion=document_ingestion_status,
        sla_control_loop=sla_control_loop,
        operational_pipeline=operational_pipeline,
    )


def build_onboarding_scorecard(db: Session, branch: Branch) -> OnboardingScorecard:
    inputs = build_onboarding_inputs(db, branch)
    sla_control_loop = _build_sla_control_loop(
        db,
        branch,
        inputs=inputs,
    )
    return build_onboarding_scorecard_from_inputs(
        inputs,
        sla_control_loop=sla_control_loop,
    )


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
