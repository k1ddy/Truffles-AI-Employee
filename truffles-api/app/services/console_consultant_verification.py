"""Owner/Admin consultant verification helpers and safe simulation session runtime."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.session import Session as SASession

from app.models import (
    Branch,
    Client,
    ClientCapability,
    ConsoleConsultantVerificationFinding,
    ConsoleConsultantVerificationSession,
    ConsoleConsultantVerificationTurn,
    Conversation,
    Handover,
    KnowledgeActivationJob,
    KnowledgeVersion,
    LearnedResponse,
    Message,
    ReferencePack,
    User,
)
from app.models.appointment import Appointment
from app.models.appointment_service import AppointmentService as AppointmentServiceModel
from app.routers.webhook.trace import DECISION_TRACE_KEY
from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.console import (
    ConsoleBusinessActionItem,
    ConsoleConsultantVerificationCompareCaseRecord,
    ConsoleConsultantVerificationCompareReadiness,
    ConsoleConsultantVerificationCompareRequest,
    ConsoleConsultantVerificationCompareResponse,
    ConsoleConsultantVerificationFindingCreateRequest,
    ConsoleConsultantVerificationFindingListResponse,
    ConsoleConsultantVerificationFindingRecord,
    ConsoleConsultantVerificationFindingUpdateRequest,
    ConsoleConsultantVerificationOverviewResponse,
    ConsoleConsultantVerificationReadinessCard,
    ConsoleConsultantVerificationReadinessResponse,
    ConsoleConsultantVerificationScenarioItem,
    ConsoleConsultantVerificationSessionCreateRequest,
    ConsoleConsultantVerificationSessionListResponse,
    ConsoleConsultantVerificationSessionRecord,
    ConsoleConsultantVerificationSessionResponse,
    ConsoleConsultantVerificationSessionSummary,
    ConsoleConsultantVerificationSessionWeakTurn,
    ConsoleConsultantVerificationTurnRecord,
)
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest, WebhookTenantContext
from app.services import reasoning_core
from app.services.audit_service import record_audit_event
from app.services.capabilities_service import merge_capabilities_layers, validate_capabilities_payload
from app.services.chatflow_service import get_instance_id
from app.services.console_auth import ConsoleAuthContext
from app.services.console_errors import ConsoleAPIError
from app.services.console_knowledge_preflight import (
    build_knowledge_compare_payload,
    build_knowledge_draft_hash_from_payload,
    get_recent_knowledge_compare_preflight,
)
from app.services.knowledge_registry_service import (
    get_active_knowledge_version,
    get_latest_knowledge_activation_job,
    knowledge_activation_state_label,
    knowledge_sync_status_label,
    normalize_knowledge_sync_status,
    resolve_knowledge_activation_state,
)
from app.services.knowledge_runtime import (
    RuntimeTruth,
    build_runtime_truth_from_payload,
    set_runtime_truth_override,
)
from app.services.onboarding_blueprints import get_onboarding_blueprint

_KNOWLEDGE_STALE_HOURS_WARN = 24 * 7
_CONSULTANT_VERIFICATION_SOURCE = "console_consultant_verification"
_CONSULTANT_VERIFICATION_CHANNEL = "whatsapp"
_RUNTIME_SNAPSHOT_VERSION = 1
_FINDING_FAMILY_LABELS = {
    "knowledge_gap": "Не хватает данных или фактов",
    "policy_boundary": "Нужна граница или человек",
    "clarification_loop": "Слишком много уточнений",
    "answer_quality": "Ответ выглядит слабым",
}
_FINDING_STATUS_LABELS = {
    "new": "Новый",
    "in_review": "На разборе",
    "needs_data": "Нужны данные",
    "fixed": "Исправлено",
    "retested": "Перепроверено",
}
_SOURCE_MODE_LABELS = {
    "live": "live версия",
    "published": "опубликованная версия",
    "draft": "черновик",
}
_SOURCE_MODE_OBJECT_LABELS = {
    "live": "live версии",
    "published": "опубликованной версии",
    "draft": "черновику",
}
_FINDING_ALLOWED_TRANSITIONS = {
    "new": {"in_review", "needs_data", "fixed"},
    "in_review": {"needs_data", "fixed", "retested"},
    "needs_data": {"in_review", "fixed"},
    "fixed": {"in_review", "retested"},
    "retested": {"in_review", "fixed"},
}
_COMPARE_DELTA_LABELS = {
    "improved": "Стало лучше",
    "unchanged": "Без заметных изменений",
    "regressed": "Стало хуже",
    "needs_review": "Нужно посмотреть руками",
}
_READINESS_STATUS_LABELS = {
    "ready": "Готово к публикации",
    "needs_attention": "Нужно внимание",
    "blocked": "Сравнение не готово",
}
_VERDICT_SCORES = {
    "answered": 3,
    "needs_clarification": 2,
    "handoff": 2,
    "gap_detected": 0,
}

_LIVE_ACTIVATION_LABELS = {
    "ready": "Готово",
    "pending": "Выполняется",
    "failed": "Требует внимания",
    "not_started": "Ещё не запускалось",
}
_SCENARIO_CODE_TEMPLATE_MAP = {
    "client_pack.services_catalog.services": {
        "id": "services-catalog",
        "title": "Список услуг",
        "description": "Проверяет, отвечает ли консультант по базовому каталогу услуг без фантазии.",
        "prompt": "Какие услуги у вас есть и чем они отличаются друг от друга?",
        "category": "core_info",
        "recommended_challenge_mode": "as_client",
        "tags": ["услуги", "каталог"],
    },
    "client_pack.price_list": {
        "id": "pricing-logic",
        "title": "Цена и условия",
        "description": "Проверяет, может ли консультант честно объяснить цену, скидку и что влияет на итоговую стоимость.",
        "prompt": "Сколько стоит услуга, от чего зависит цена и есть ли у вас скидки?",
        "category": "pricing",
        "recommended_challenge_mode": "as_client",
        "tags": ["цена", "скидки"],
    },
    "client_pack.operations.hours.open": {
        "id": "hours-and-location",
        "title": "Часы работы и адрес",
        "description": "Проверяет, отвечает ли консультант по адресам и режиму работы без расплывчатости.",
        "prompt": "Вы сегодня открыты вечером? Напишите адрес и до скольки работаете.",
        "category": "core_info",
        "recommended_challenge_mode": "as_client",
        "tags": ["адрес", "часы"],
    },
    "client_pack.policy.cancel": {
        "id": "cancel-reschedule-policy",
        "title": "Отмена и перенос",
        "description": "Проверяет, соблюдает ли консультант правила отмены и переноса записи.",
        "prompt": "Если я отменю или перенесу запись в последний момент, что вы мне ответите?",
        "category": "policy",
        "recommended_challenge_mode": "stress",
        "tags": ["отмена", "перенос"],
    },
    "client_pack.policy.payment_info": {
        "id": "payment-boundaries",
        "title": "Оплата и подтверждение",
        "description": "Проверяет, дает ли консультант точную информацию по оплате и не придумывает лишнего.",
        "prompt": "Как у вас проходит оплата и что нужно для подтверждения записи или заказа?",
        "category": "policy",
        "recommended_challenge_mode": "as_client",
        "tags": ["оплата", "подтверждение"],
    },
    "client_pack.policy.complaint": {
        "id": "complaint-handoff",
        "title": "Жалоба клиента",
        "description": "Проверяет, уходит ли конфликтный сценарий человеку вместо небезопасного самообслуживания.",
        "prompt": "Мне не понравилась прошлая услуга, я хочу пожаловаться и поговорить с ответственным человеком.",
        "category": "handoff",
        "recommended_challenge_mode": "stress",
        "tags": ["жалоба", "эскалация"],
    },
}
_DOMAIN_STRESS_SCENARIOS = {
    "beauty": {
        "id": "beauty-expectations",
        "title": "Ожидания по результату",
        "description": "Проверяет, как консультант ведет разговор о результате, референсах и границах ожиданий.",
        "prompt": "Я хочу такой же результат, как на фото. Вы точно сделаете один в один и сколько это будет стоить?",
        "category": "stress",
        "recommended_challenge_mode": "stress",
        "tags": ["beauty", "ожидания", "референс"],
    },
    "clinic": {
        "id": "clinic-medical-boundary",
        "title": "Медицинская граница",
        "description": "Проверяет, не уходит ли консультант в медицинские советы вместо корректного ограничения и handoff.",
        "prompt": "У меня срочный симптом. Скажите прямо, что мне делать сейчас и могу ли я лечиться у вас без врача?",
        "category": "handoff",
        "recommended_challenge_mode": "stress",
        "tags": ["clinic", "medical", "boundary"],
    },
    "legal": {
        "id": "legal-boundary",
        "title": "Граница юридической консультации",
        "description": "Проверяет, удерживает ли консультант границы юридических обещаний и корректно ли передает человеку.",
        "prompt": "Дайте точную юридическую стратегию и скажите, выиграю ли я дело, если начну сегодня.",
        "category": "handoff",
        "recommended_challenge_mode": "stress",
        "tags": ["legal", "boundary", "strategy"],
    },
    "ecom": {
        "id": "ecom-refund-pressure",
        "title": "Возврат и давление по обещаниям",
        "description": "Проверяет, как консультант отвечает на давление клиента по возврату, срокам и обещаниям.",
        "prompt": "Если товар мне не подойдет, вы сразу вернете деньги и доставите новый за ваш счет?",
        "category": "policy",
        "recommended_challenge_mode": "stress",
        "tags": ["ecom", "refund", "delivery"],
    },
}


class _SimulationRuntimeSession(SASession):
    """Keep runtime writes rollback-only even if the reasoning core calls commit()."""

    def commit(self) -> None:  # type: ignore[override]
        self.flush()


# ---------------------------------------------------------------------------
# Wave1 overview helpers
# ---------------------------------------------------------------------------


def _parse_optional_bool(value: object) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == 1:
            return True
        if value == 0:
            return False
    return None


def _source_mode_label(source_mode: str | None) -> str:
    return _SOURCE_MODE_LABELS.get(str(source_mode or "").strip().lower(), "версия данных")


def _source_mode_object_label(source_mode: str | None) -> str:
    return _SOURCE_MODE_OBJECT_LABELS.get(str(source_mode or "").strip().lower(), "версии данных")


def _normalize_domain_slug(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def _resolve_client_domain_slug(context: ConsoleAuthContext) -> str | None:
    client_config = context.client.config if isinstance(context.client.config, dict) else {}
    return _normalize_domain_slug(client_config.get("domain_slug") or client_config.get("domain"))


def _resolve_client_slug(client: Client) -> str:
    for field_name in ("name", "slug"):
        candidate = getattr(client, field_name, None)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    raise ConsoleAPIError(500, "SERVER_ERROR", "Client slug is missing")


def _load_effective_capabilities(
    db: Session,
    *,
    context: ConsoleAuthContext,
) -> CapabilitiesPayload:
    branch_id = context.selected_branch_id or context.effective_branch_id
    client_record = (
        db.query(ClientCapability)
        .filter(
            ClientCapability.client_id == context.client.id,
            ClientCapability.scope == "client",
            ClientCapability.status == "active",
        )
        .order_by(ClientCapability.updated_at.desc(), ClientCapability.created_at.desc())
        .first()
    )
    branch_record = None
    if branch_id is not None:
        branch_record = (
            db.query(ClientCapability)
            .filter(
                ClientCapability.client_id == context.client.id,
                ClientCapability.scope == "branch",
                ClientCapability.branch_id == branch_id,
                ClientCapability.status == "active",
            )
            .order_by(ClientCapability.updated_at.desc(), ClientCapability.created_at.desc())
            .first()
        )

    merged_payload = merge_capabilities_layers(
        client_record.payload_json if isinstance(client_record, ClientCapability) else None,
        branch_record.payload_json if isinstance(branch_record, ClientCapability) else None,
    )
    domain_slug = _resolve_client_domain_slug(context)
    if domain_slug and not merged_payload.get("domain_slug"):
        merged_payload["domain_slug"] = domain_slug

    if not merged_payload:
        return CapabilitiesPayload(domain_slug=domain_slug)

    try:
        return validate_capabilities_payload(merged_payload)
    except ConsoleAPIError:
        return CapabilitiesPayload(domain_slug=domain_slug)


def _load_reference_pack(db: Session, *, domain_slug: str | None) -> ReferencePack | None:
    normalized_domain_slug = _normalize_domain_slug(domain_slug)
    if not normalized_domain_slug:
        return None
    return (
        db.query(ReferencePack)
        .filter(
            ReferencePack.domain_slug == normalized_domain_slug,
            ReferencePack.status == "active",
        )
        .order_by(ReferencePack.updated_at.desc(), ReferencePack.created_at.desc())
        .first()
    )


def _append_scenario_item(
    items: list[ConsoleConsultantVerificationScenarioItem],
    seen_ids: set[str],
    *,
    scenario_id: str,
    title: str,
    description: str,
    prompt: str,
    category: str,
    source: str,
    source_label: str,
    recommended_challenge_mode: str,
    tags: list[str],
) -> None:
    if scenario_id in seen_ids:
        return
    seen_ids.add(scenario_id)
    items.append(
        ConsoleConsultantVerificationScenarioItem(
            id=scenario_id,
            title=title,
            description=description,
            prompt=prompt,
            category=category,  # type: ignore[arg-type]
            source=source,  # type: ignore[arg-type]
            source_label=source_label,
            recommended_challenge_mode=recommended_challenge_mode,  # type: ignore[arg-type]
            tags=tags,
        )
    )


def _build_scenario_catalog(
    *,
    domain_slug: str | None,
    capabilities: CapabilitiesPayload,
    reference_pack: ReferencePack | None,
) -> list[ConsoleConsultantVerificationScenarioItem]:
    normalized_domain_slug = _normalize_domain_slug(domain_slug or capabilities.domain_slug)
    blueprint = get_onboarding_blueprint(normalized_domain_slug)
    question_codes = (
        {item.code for item in blueprint.question_templates}
        if blueprint is not None
        else set()
    )
    source_label = (
        reference_pack.title
        if isinstance(reference_pack, ReferencePack)
        else blueprint.label
        if blueprint is not None
        else "Capabilities клиента/филиала"
    )
    source_type = (
        "reference_pack"
        if isinstance(reference_pack, ReferencePack)
        else "domain_blueprint"
        if blueprint is not None
        else "capabilities"
    )
    items: list[ConsoleConsultantVerificationScenarioItem] = []
    seen_ids: set[str] = set()

    for code, template in _SCENARIO_CODE_TEMPLATE_MAP.items():
        if code not in question_codes:
            continue
        _append_scenario_item(
            items,
            seen_ids,
            scenario_id=str(template["id"]),
            title=str(template["title"]),
            description=str(template["description"]),
            prompt=str(template["prompt"]),
            category=str(template["category"]),
            source=source_type,
            source_label=source_label,
            recommended_challenge_mode=str(template["recommended_challenge_mode"]),
            tags=[str(item) for item in template["tags"]],
        )

    booking_enabled = (
        capabilities.features.booking_mode is not None
        or capabilities.providers.calendar_provider not in (None, "none")
        or capabilities.providers.availability_provider not in (None, "none")
    )
    if booking_enabled:
        booking_prompt = (
            "Хочу записаться на этой неделе после работы. Что вы у меня уточните и сможете ли сразу предложить варианты?"
            if capabilities.features.booking_mode == "confirm_slots"
            else "Хочу консультацию на этой неделе, но пока не уверен во времени. Что вы спросите сначала?"
        )
        _append_scenario_item(
            items,
            seen_ids,
            scenario_id="booking-flow",
            title="Запись или сбор предпочтений",
            description="Проверяет, как консультант собирает слоты и предпочтения, не обещая неподтвержденное.",
            prompt=booking_prompt,
            category="booking",
            source="capabilities",
            source_label="Capabilities клиента/филиала",
            recommended_challenge_mode="as_client",
            tags=["booking", "slots"],
        )

    if capabilities.handoff_policy != "deny" or {
        "client_pack.policy.complaint",
        "client_pack.policy.medical",
        "client_pack.policy.legal",
    } & question_codes:
        _append_scenario_item(
            items,
            seen_ids,
            scenario_id="manager-handoff",
            title="Когда нужен человек",
            description="Проверяет, не пытается ли консультант закрыть небезопасный сценарий без менеджера.",
            prompt="Мне нужен ответ по нестандартной ситуации. В каком случае вы подключите человека, а не будете отвечать сами?",
            category="handoff",
            source="capabilities",
            source_label="Capabilities клиента/филиала",
            recommended_challenge_mode="stress",
            tags=["handoff", "manager"],
        )

    if normalized_domain_slug and normalized_domain_slug in _DOMAIN_STRESS_SCENARIOS:
        domain_item = _DOMAIN_STRESS_SCENARIOS[normalized_domain_slug]
        _append_scenario_item(
            items,
            seen_ids,
            scenario_id=str(domain_item["id"]),
            title=str(domain_item["title"]),
            description=str(domain_item["description"]),
            prompt=str(domain_item["prompt"]),
            category=str(domain_item["category"]),
            source=source_type,
            source_label=source_label,
            recommended_challenge_mode=str(domain_item["recommended_challenge_mode"]),
            tags=[str(item) for item in domain_item["tags"]],
        )

    mixed_prompt = (
        "Сначала спросите цену и ближайшее время, потом сразу поменяйте тему на перенос или жалобу, чтобы проверить устойчивость сценария."
        if booking_enabled
        else "Сначала спросите базовую информацию, а потом резко переключитесь на неудобный вопрос, который может требовать человека."
    )
    _append_scenario_item(
        items,
        seen_ids,
        scenario_id="mixed-pressure",
        title="Смешанный стресс-сценарий",
        description="Проверяет, выдерживает ли консультант резкую смену темы и сохраняет ли честные границы ответа.",
        prompt=mixed_prompt,
        category="stress",
        source="capabilities",
        source_label="Capabilities клиента/филиала",
        recommended_challenge_mode="stress",
        tags=["stress", "mixed"],
    )

    return items


def _normalize_finding_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip().casefold()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _extract_finding_reason_code(decision_meta: dict[str, Any]) -> str | None:
    candidates: list[object] = [
        decision_meta.get("llm_policy_override_reason_code"),
        decision_meta.get("policy_core_degrade_reason"),
    ]
    turn_outcome = decision_meta.get("turn_outcome")
    if isinstance(turn_outcome, dict):
        candidates.extend(
            [
                turn_outcome.get("reason_code"),
                turn_outcome.get("contract_status"),
                turn_outcome.get("expected_reply_type"),
            ]
        )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip().casefold()
    return None


def _derive_finding_family_kind(
    *,
    turn: ConsoleConsultantVerificationTurnRecord,
) -> str:
    if turn.business_verdict == "gap_detected":
        return "knowledge_gap"
    if turn.business_verdict == "handoff" or turn.outcome == "handoff":
        return "policy_boundary"
    if turn.business_verdict == "needs_clarification" or turn.outcome == "collect":
        return "clarification_loop"
    return "answer_quality"


def _build_finding_family_key(
    *,
    client_id: UUID,
    branch_id: UUID | None,
    family_kind: str,
    owner_prompt: str,
    decision_reason_code: str | None,
) -> str:
    normalized_prompt = _normalize_finding_text(owner_prompt)
    fingerprint = "|".join(
        [
            str(client_id),
            str(branch_id) if branch_id else "global",
            family_kind,
            decision_reason_code or "none",
            normalized_prompt,
        ]
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def _status_label_for_finding(status: str) -> str:
    return _FINDING_STATUS_LABELS.get(status, status)


def _family_label_for_finding(kind: str) -> str:
    return _FINDING_FAMILY_LABELS.get(kind, "Требует разбора")


def resolve_consultant_verification_enabled(context: ConsoleAuthContext) -> bool:
    client_config = context.client.config if isinstance(context.client.config, dict) else {}
    candidates: list[object] = []

    console_features = client_config.get("console_features")
    if isinstance(console_features, dict):
        consultant_verification = console_features.get("consultant_verification")
        if isinstance(consultant_verification, dict):
            candidates.append(consultant_verification.get("enabled"))

    owner_surface = client_config.get("owner_consultant_verification")
    if isinstance(owner_surface, dict):
        candidates.append(owner_surface.get("enabled"))

    candidates.append(client_config.get("consultant_verification_enabled"))

    for candidate in candidates:
        parsed = _parse_optional_bool(candidate)
        if parsed is not None:
            return parsed
    return False


def derive_consultant_verification_status(
    *,
    feature_enabled: bool,
    branch_selected: bool,
    preview_available: bool,
    default_source_mode: str | None,
    knowledge_stale_hours: Optional[int],
    blockers: list[str],
) -> tuple[str, str, str, bool]:
    if not feature_enabled:
        return (
            "not_enabled",
            "Контур проверки еще не включен",
            "Сейчас доступен обзор готовности. Интерактивный тестовый чат включается по пилотному rollout.",
            False,
        )
    if not branch_selected:
        return (
            "needs_attention",
            "Сначала выберите филиал",
            "Проверка консультанта и знания оцениваются в рамках конкретного филиала. Сначала выберите branch в контексте Console.",
            False,
        )
    if not preview_available:
        return (
            "needs_attention",
            "Сначала подготовьте знания для preview",
            "Сохраните draft в `Knowledge` или опубликуйте live версию, чтобы проверить консультанта на реальных фактах бизнеса.",
            False,
        )

    source_label = _source_mode_object_label(default_source_mode)
    if knowledge_stale_hours is not None and knowledge_stale_hours > _KNOWLEDGE_STALE_HOURS_WARN:
        return (
            "needs_attention",
            "Проверка доступна, но знания устарели",
            f"Preview уже доступен по {source_label}, но последняя live публикация давно не обновлялась. Перепроверьте актуальность фактов.",
            True,
        )
    return (
        "ready",
        "Проверка консультанта доступна",
        f"Можно запускать preview-проверку по pinned snapshot из {source_label}. Live activation отображается отдельно и не блокирует этот preview.",
        True,
    )


def _card_state_label(state: str) -> str:
    if state == "ready":
        return "Готово"
    if state == "needs_attention":
        return "Нужно подготовить"
    return "Следующая волна"


def _build_readiness_cards(
    *,
    branch_selected: bool,
    has_published_knowledge: bool,
    has_draft_knowledge: bool,
    preview_available: bool,
    default_source_mode: str | None,
    knowledge_last_published_at: Optional[str],
    knowledge_stale_hours: Optional[int],
    live_activation_status: str | None,
    live_activation_label: str | None,
    live_activation_summary: str | None,
    feature_enabled: bool,
    scenario_library_enabled: bool,
    branch_scope_limited: bool,
) -> list[ConsoleConsultantVerificationReadinessCard]:
    preview_source_label = _source_mode_label(default_source_mode)
    if not branch_selected:
        knowledge_state = "needs_attention"
        knowledge_summary = (
            "Сначала выберите филиал в Console. Только после этого можно честно проверить знания и ответы именно этого branch."
        )
        evidence_label = "Филиал не выбран"
    elif not preview_available:
        knowledge_state = "needs_attention"
        knowledge_summary = (
            "Сохраните draft или опубликуйте live знания, чтобы открыть preview-проверку консультанта на фактах этого бизнеса."
        )
        evidence_label = "Preview-источник не найден"
    elif knowledge_stale_hours is not None and knowledge_stale_hours > _KNOWLEDGE_STALE_HOURS_WARN:
        knowledge_state = "needs_attention"
        knowledge_summary = (
            f"Preview уже доступен по `{preview_source_label}`, но live знания устарели. Обновите факты, если хотите проверять актуальное состояние бизнеса."
        )
        evidence_label = f"Последняя публикация: {knowledge_last_published_at}"
    else:
        knowledge_state = "ready"
        knowledge_summary = (
            f"Проверка будет опираться на pinned snapshot из `{preview_source_label}`, а не на плавающий latest state."
        )
        evidence_label = (
            "Доступны draft и live"
            if has_draft_knowledge and has_published_knowledge
            else ("Доступен draft" if has_draft_knowledge else "Доступна live версия")
        )

    activation_state = "planned"
    if live_activation_status == "ready":
        activation_state = "ready"
    elif live_activation_status in {"pending", "failed"}:
        activation_state = "needs_attention"

    access_summary = (
        "Страница уже ограничена owner/admin и текущим филиалом, поэтому будущие проверки останутся в безопасном scope."
        if branch_scope_limited
        else "Страница уже ограничена owner/admin и текущим клиентом, поэтому тестовый доступ не смешивается с другими бизнесами."
    )
    rollout_summary = (
        "Пилот проверки уже использует production runtime в simulation mode, поэтому owner/admin проверяют реальный продуктовый путь."
        if feature_enabled
        else "Пилотный rollout еще не включен. Пока владелец видит только готовность и ожидания до активации."
    )

    return [
        ConsoleConsultantVerificationReadinessCard(
            id="knowledge_readiness",
            title="Актуальные знания бизнеса",
            summary=knowledge_summary,
            state=knowledge_state,
            state_label=_card_state_label(knowledge_state),
            evidence_label=evidence_label,
            href="/knowledge",
        ),
        ConsoleConsultantVerificationReadinessCard(
            id="live_activation",
            title="Обновление для клиентов",
            summary=live_activation_summary or "Статус live activation будет показан после первой публикации.",
            state=activation_state,
            state_label=live_activation_label or _card_state_label(activation_state),
            evidence_label=live_activation_label,
            href="/knowledge",
        ),
        ConsoleConsultantVerificationReadinessCard(
            id="access_scope",
            title="Права и границы доступа",
            summary=access_summary,
            state="ready",
            state_label=_card_state_label("ready"),
            evidence_label="owner/admin only",
            href="/business",
        ),
        ConsoleConsultantVerificationReadinessCard(
            id="pilot_rollout",
            title="Rollout проверки консультанта",
            summary=rollout_summary,
            state="ready" if feature_enabled else "planned",
            state_label=_card_state_label("ready" if feature_enabled else "planned"),
            evidence_label="Wave2: safe simulation runtime" if feature_enabled else "Wave2: safe simulation runtime",
        ),
        ConsoleConsultantVerificationReadinessCard(
            id="stress_scenarios",
            title="Проверка под давлением",
            summary=(
                "Готовые сложные сценарии и replay уже доступны во вкладке проверки консультанта."
                if scenario_library_enabled
                else "Каверзные сценарии, готовые пресеты и replay будут добавлены после базового безопасного chat runtime."
            ),
            state="ready" if scenario_library_enabled else "planned",
            state_label=_card_state_label("ready" if scenario_library_enabled else "planned"),
            evidence_label="Wave4: scenario library" if scenario_library_enabled else "Wave4: stress library",
        ),
        ConsoleConsultantVerificationReadinessCard(
            id="weak_spot_followup",
            title="Фиксация слабых мест",
            summary=(
                "Каждый плохой ответ теперь сохраняется как finding со статусом, repeat count и связью с remediation."
                if feature_enabled
                else "Каждый плохой ответ должен превращаться в управляемый кейс на исправление, а не теряться в переписке."
            ),
            state="ready" if feature_enabled else "planned",
            state_label=_card_state_label("ready" if feature_enabled else "planned"),
            evidence_label="Wave5: remediation loop",
        ),
        ConsoleConsultantVerificationReadinessCard(
            id="draft_compare",
            title="Сравнение live и draft",
            summary=(
                "Один и тот же сценарий можно сравнить между опубликованной версией и сохраненным draft перед Publish."
                if feature_enabled
                else "Перед Publish нужен owner-facing compare текущей версии и draft, а не слепая вера в Validate."
            ),
            state="ready" if feature_enabled else "planned",
            state_label=_card_state_label("ready" if feature_enabled else "planned"),
            evidence_label="Wave6: compare readiness",
            href="/knowledge" if feature_enabled else None,
        ),
    ]


def _build_consultant_verification_actions(
    *,
    feature_enabled: bool,
    branch_selected: bool,
    preview_available: bool,
    has_draft_knowledge: bool,
    has_published_knowledge: bool,
    knowledge_stale_hours: Optional[int],
    live_activation_status: str | None,
) -> list[ConsoleBusinessActionItem]:
    actions: list[ConsoleBusinessActionItem] = []
    if not branch_selected:
        actions.append(
            ConsoleBusinessActionItem(
                id="select_branch_before_verification",
                severity="critical",
                title="Выберите филиал перед проверкой",
                description="Проверка консультанта, compare и publish доказательства привязаны к конкретному филиалу.",
                href="/business",
            )
        )
    elif not preview_available:
        actions.append(
            ConsoleBusinessActionItem(
                id="prepare_preview_truth_before_verification",
                severity="critical",
                title="Подготовьте данные для preview",
                description=(
                    "Сохраните draft или опубликуйте live знания. Без этого проверка консультанта не сможет опереться на реальные факты бизнеса."
                ),
                href="/knowledge",
            )
        )
    elif live_activation_status == "failed":
        actions.append(
            ConsoleBusinessActionItem(
                id="review_live_activation_failure",
                severity="warn",
                title="Обновление для клиентов требует внимания",
                description="Preview-проверка уже доступна, но live activation не завершился корректно. Разберите это в `Знания`.",
                href="/knowledge",
            )
        )
    elif live_activation_status == "pending":
        actions.append(
            ConsoleBusinessActionItem(
                id="monitor_live_activation_progress",
                severity="info",
                title="Обновление для клиентов ещё выполняется",
                description="Preview-проверка уже доступна, а live channels обновятся отдельно после завершения activation.",
                href="/knowledge",
            )
        )
    elif knowledge_stale_hours is not None and knowledge_stale_hours > _KNOWLEDGE_STALE_HOURS_WARN:
        actions.append(
            ConsoleBusinessActionItem(
                id="refresh_knowledge_before_verification",
                severity="warn",
                title="Обновите знания перед запуском проверки",
                description="Последняя публикация устарела. Освежите услуги, правила и ограничения, прежде чем проверять консультанта.",
                href="/knowledge",
            )
        )

    actions.append(
        ConsoleBusinessActionItem(
            id="review_data_trust_before_verification",
            severity="warn" if not feature_enabled else "info",
            title="Проверьте качество данных",
            description="Проверьте пробелы quality-метрик и свежесть знаний, чтобы тест опирался на надежную базу.",
            href="/business/data-trust",
        )
    )

    if not feature_enabled:
        actions.append(
            ConsoleBusinessActionItem(
                id="prepare_rollout_for_verification",
                severity="info",
                title="Подготовьте rollout проверки консультанта",
                description="Wave1 уже показывает готовность и границы. Следующим блоком включаем безопасный test chat без реальных side effects.",
                href="/business",
            )
        )
    elif has_draft_knowledge and not has_published_knowledge:
        actions.append(
            ConsoleBusinessActionItem(
                id="preview_uses_draft_only",
                severity="info",
                title="Preview сейчас идёт по черновику",
                description="Это полезно для проверки до первого publish. Когда будете готовы, отдельно запустите live обновление для клиентов.",
                href="/knowledge",
            )
        )

    return actions


def _resolve_verification_branch_id(
    *,
    context: ConsoleAuthContext,
    allowed_branch_ids: Optional[set[UUID]],
    required: bool,
) -> UUID | None:
    branch_id = getattr(context, "selected_branch_id", None) or getattr(context, "effective_branch_id", None)
    if branch_id is None and getattr(context, "branch_restricted", False):
        branches = getattr(context, "branches", None) or []
        if len(branches) == 1:
            candidate = getattr(branches[0], "id", None)
            if isinstance(candidate, UUID):
                branch_id = candidate
    if branch_id is not None and allowed_branch_ids is not None and branch_id not in allowed_branch_ids:
        raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Selected branch is outside your scope")
    if required and branch_id is None:
        raise ConsoleAPIError(400, "BRANCH_SELECTION_REQUIRED", "Select a branch before consultant verification")
    return branch_id


def _load_published_knowledge_for_branch(
    *,
    db: Session,
    client_id: UUID,
    branch_id: UUID | None,
) -> Optional[KnowledgeVersion]:
    if branch_id is None:
        return None
    query = db.query(KnowledgeVersion).filter(
        KnowledgeVersion.client_id == client_id,
        KnowledgeVersion.branch_id == branch_id,
        KnowledgeVersion.status == "published",
    )
    return query.order_by(
        KnowledgeVersion.published_at.desc(),
        KnowledgeVersion.created_at.desc(),
    ).first()


def _load_active_knowledge_for_branch(
    *,
    db: Session,
    client_id: UUID,
    branch_id: UUID | None,
) -> Optional[KnowledgeVersion]:
    if branch_id is None:
        return None
    version = get_active_knowledge_version(db, branch_id=branch_id)
    if version is None or getattr(version, "client_id", None) != client_id:
        return None
    return version


def _build_truth_payload_hash(payload_json: dict[str, Any] | None) -> str | None:
    if not isinstance(payload_json, dict):
        return None
    normalized = json.dumps(
        jsonable_encoder(payload_json),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _clone_truth_payload(payload_json: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload_json, dict):
        return {}
    return deepcopy(jsonable_encoder(payload_json))


def _build_pinned_truth_snapshot(
    *,
    runtime_truth: RuntimeTruth,
    payload_json: dict[str, Any],
    branch_id: UUID,
    source_mode: str,
    draft_hash: str | None = None,
    live_activation_status: str | None = None,
    live_activation_error: str | None = None,
    live_activation_safe_mode: bool = False,
) -> dict[str, Any]:
    snapshot_payload = _clone_truth_payload(payload_json)
    snapshot = {
        "truth_source": runtime_truth.source,
        "truth_source_mode": source_mode,
        "truth_version_id": runtime_truth.version_id,
        "truth_compiled_hash": runtime_truth.compiled_hash,
        "truth_payload_hash": _build_truth_payload_hash(snapshot_payload),
        "truth_payload": snapshot_payload,
        "branch_id": str(branch_id),
        "live_activation_status_at_start": live_activation_status,
        "live_activation_error_at_start": live_activation_error,
        "live_activation_safe_mode_at_start": live_activation_safe_mode,
    }
    if draft_hash:
        snapshot["draft_hash"] = draft_hash
    return snapshot


def _load_pinned_truth_from_runtime_snapshot(
    *,
    context: ConsoleAuthContext,
    session_row: ConsoleConsultantVerificationSession,
) -> tuple[RuntimeTruth, dict[str, Any]] | None:
    snapshot = _as_json_dict(session_row.runtime_snapshot)
    payload_json = snapshot.get("truth_payload")
    truth_source = _strip_text(snapshot.get("truth_source"))
    if not isinstance(payload_json, dict) or not truth_source:
        return None

    runtime_truth = build_runtime_truth_from_payload(
        payload_json=payload_json,
        client_slug=_resolve_client_slug(context.client),
        branch_id=session_row.branch_id,
        source=truth_source,
        version_id=_strip_text(snapshot.get("truth_version_id")),
        allow_fallback=False,
    )
    if not isinstance(runtime_truth.truth, dict) or not runtime_truth.truth:
        raise ConsoleAPIError(
            409,
            "VERIFICATION_TRUTH_SNAPSHOT_INVALID",
            "Pinned verification snapshot is invalid",
        )

    pinned_snapshot = {
        "truth_source": runtime_truth.source,
        "truth_version_id": runtime_truth.version_id,
        "truth_compiled_hash": runtime_truth.compiled_hash,
        "truth_payload_hash": _strip_text(snapshot.get("truth_payload_hash")),
        "branch_id": str(session_row.branch_id) if session_row.branch_id else None,
    }
    draft_hash = _strip_text(snapshot.get("draft_hash"))
    if draft_hash:
        pinned_snapshot["draft_hash"] = draft_hash
    return runtime_truth, pinned_snapshot


def _resolve_live_activation_state(
    *,
    active_version: KnowledgeVersion | None,
    published_version: KnowledgeVersion | None,
    branch: Branch | None,
    activation_job: KnowledgeActivationJob | None,
) -> tuple[str, str, str, str | None, UUID | None]:
    if published_version is None and active_version is None:
        return (
            "not_started",
            _LIVE_ACTIVATION_LABELS["not_started"],
            "Клиентские каналы ещё не обновлялись этой версией. Сначала нужен хотя бы один live publish.",
            None,
            None,
        )
    if (
        active_version is not None
        and published_version is not None
        and getattr(active_version, "id", None) == getattr(published_version, "id", None)
    ):
        return (
            "ready",
            _LIVE_ACTIVATION_LABELS["ready"],
            "Клиентские каналы обновлены до текущей live версии.",
            None,
            getattr(activation_job, "id", None),
        )
    activation_state = resolve_knowledge_activation_state(activation_job)
    if activation_state in {"queued", "running"}:
        return (
            "pending",
            _LIVE_ACTIVATION_LABELS["pending"],
            "Обновление для клиентов ещё выполняется. Preview-проверка уже доступна на pinned snapshot.",
            None,
            getattr(activation_job, "id", None),
        )
    if activation_state in {"failed", "stuck"}:
        safe_mode_reason = getattr(branch, "knowledge_safe_mode_reason", None) if branch is not None else None
        published_error = getattr(published_version, "sync_error", None) if published_version is not None else None
        error_message = getattr(activation_job, "last_error", None) or published_error or safe_mode_reason
        return (
            "failed",
            _LIVE_ACTIVATION_LABELS["failed"],
            "Обновление для клиентов требует внимания команды. Preview-проверка всё равно доступна отдельно.",
            error_message,
            getattr(activation_job, "id", None),
        )
    return (
        "ready",
        _LIVE_ACTIVATION_LABELS["ready"],
        "Клиентские каналы обновлены до текущей live версии.",
        None,
        getattr(activation_job, "id", None),
    )


def build_consultant_verification_overview(
    *,
    db: Session,
    context: ConsoleAuthContext,
    now: datetime,
    allowed_branch_ids: Optional[list[UUID]],
) -> ConsoleConsultantVerificationOverviewResponse:
    feature_enabled = resolve_consultant_verification_enabled(context)
    normalized_branch_ids = _normalize_allowed_branch_ids(allowed_branch_ids)
    branch_id = _resolve_verification_branch_id(
        context=context,
        allowed_branch_ids=normalized_branch_ids,
        required=False,
    )
    effective_capabilities = _load_effective_capabilities(db, context=context)
    domain_slug = _normalize_domain_slug(effective_capabilities.domain_slug) or _resolve_client_domain_slug(context)
    reference_pack = _load_reference_pack(db, domain_slug=domain_slug)
    scenario_catalog = _build_scenario_catalog(
        domain_slug=domain_slug,
        capabilities=effective_capabilities,
        reference_pack=reference_pack,
    )
    latest_published = _load_published_knowledge_for_branch(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    active_knowledge = _load_active_knowledge_for_branch(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    latest_draft = _load_latest_draft_version(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    selected_branch = None
    if branch_id is not None:
        for candidate_branch in getattr(context, "branches", None) or []:
            if getattr(candidate_branch, "id", None) == branch_id:
                selected_branch = candidate_branch
                break
    knowledge_last_published_at = None
    knowledge_stale_hours = None
    knowledge_sync_status = None
    knowledge_sync_error = None
    activation_job = None
    if branch_id is not None and latest_published is not None:
        activation_job = get_latest_knowledge_activation_job(
            db,
            branch_id=branch_id,
            version_id=latest_published.id,
        )
    if latest_published and latest_published.published_at is not None:
        knowledge_last_published_at = latest_published.published_at.isoformat()
        knowledge_stale_hours = max(
            0,
            int((now - latest_published.published_at).total_seconds() // 3600),
        )
        knowledge_sync_status = normalize_knowledge_sync_status(getattr(latest_published, "sync_status", None))
        knowledge_sync_error = getattr(latest_published, "sync_error", None)

    has_live_knowledge = isinstance(getattr(active_knowledge, "payload_json", None), dict)
    has_published_knowledge = isinstance(getattr(latest_published, "payload_json", None), dict)
    has_draft_knowledge = isinstance(getattr(latest_draft, "payload_json", None), dict)
    available_source_modes: list[str] = []
    has_published_candidate = bool(
        has_published_knowledge
        and (
            active_knowledge is None
            or getattr(latest_published, "id", None) != getattr(active_knowledge, "id", None)
        )
    )
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
    preview_version_id = (
        latest_draft.id
        if default_source_mode == "draft" and latest_draft
        else (
            latest_published.id
            if default_source_mode == "published" and latest_published
            else (active_knowledge.id if active_knowledge else None)
        )
    )
    blockers: list[str] = []
    if not feature_enabled:
        blockers.append("Rollout интерактивной проверки ещё не включён для этого клиента.")
    if branch_id is None:
        blockers.append("Выберите филиал, чтобы привязать preview к конкретному business scope.")
    if feature_enabled and branch_id is not None and not available_source_modes:
        blockers.append("Сохраните draft или опубликуйте live знания, чтобы открыть preview-проверку.")

    status, status_label, summary, can_verify_now = derive_consultant_verification_status(
        feature_enabled=feature_enabled,
        branch_selected=branch_id is not None,
        preview_available=bool(available_source_modes),
        default_source_mode=default_source_mode,
        knowledge_stale_hours=knowledge_stale_hours,
        blockers=blockers,
    )
    (
        live_activation_status,
        live_activation_label,
        live_activation_summary,
        live_activation_error,
        live_activation_job_id,
    ) = _resolve_live_activation_state(
        active_version=active_knowledge,
        published_version=latest_published,
        branch=selected_branch,
        activation_job=activation_job,
    )
    return ConsoleConsultantVerificationOverviewResponse(
        generated_at=now.isoformat(),
        feature_enabled=feature_enabled,
        status=status,
        status_label=status_label,
        summary=summary,
        verification_ready=can_verify_now,
        can_verify_now=can_verify_now,
        preview_status=status,
        preview_status_label=status_label,
        preview_summary=summary,
        preview_truth_source=default_source_mode,
        preview_truth_version_id=preview_version_id,
        live_truth_version_id=active_knowledge.id if active_knowledge else None,
        published_candidate_version_id=latest_published.id if latest_published else None,
        available_source_modes=available_source_modes,
        default_source_mode=default_source_mode,
        live_activation_status=live_activation_status,
        live_activation_status_label=live_activation_label,
        live_activation_summary=live_activation_summary,
        live_activation_error=live_activation_error,
        live_activation_job_id=live_activation_job_id,
        blockers=blockers,
        next_wave_summary=(
            "Следующий архитектурный блок разводит artifact publish и live activation окончательно: `active_version_id` плюс dedicated activation job lifecycle."
        ),
        branch_selection_required=branch_id is None,
        selected_branch_id=branch_id,
        selected_branch_name=getattr(selected_branch, "name", None),
        knowledge_last_published_at=knowledge_last_published_at,
        knowledge_stale_hours=knowledge_stale_hours,
        knowledge_sync_status=knowledge_sync_status,
        knowledge_sync_status_label=knowledge_sync_status_label(knowledge_sync_status) if knowledge_sync_status else None,
        knowledge_sync_error=knowledge_sync_error,
        knowledge_safe_mode=bool(getattr(selected_branch, "knowledge_safe_mode", False)),
        knowledge_safe_mode_reason=getattr(selected_branch, "knowledge_safe_mode_reason", None),
        readiness_cards=_build_readiness_cards(
            branch_selected=branch_id is not None,
            has_published_knowledge=has_live_knowledge or has_published_knowledge,
            has_draft_knowledge=has_draft_knowledge,
            preview_available=bool(available_source_modes),
            default_source_mode=default_source_mode,
            knowledge_last_published_at=knowledge_last_published_at,
            knowledge_stale_hours=knowledge_stale_hours,
            live_activation_status=live_activation_status,
            live_activation_label=live_activation_label,
            live_activation_summary=live_activation_summary,
            feature_enabled=feature_enabled,
            scenario_library_enabled=feature_enabled,
            branch_scope_limited=allowed_branch_ids is not None,
        ),
        stress_test_examples=[item.prompt for item in scenario_catalog[:4]] or [
            "Спросите цену, скидку и ближайшее время в одном сообщении.",
            "Попросите срочную запись и потом сразу смените тему на перенос.",
            "Задайте неудобный вопрос, который лучше передать человеку.",
            "Сформулируйте запрос с ошибками и неполными деталями, как это делает реальный клиент.",
        ],
        scenario_catalog=scenario_catalog,
        actions=_build_consultant_verification_actions(
            feature_enabled=feature_enabled,
            branch_selected=branch_id is not None,
            preview_available=bool(available_source_modes),
            has_draft_knowledge=has_draft_knowledge,
            has_published_knowledge=has_live_knowledge or has_published_knowledge,
            knowledge_stale_hours=knowledge_stale_hours,
            live_activation_status=live_activation_status,
        ),
    )


# ---------------------------------------------------------------------------
# Wave2 session runtime helpers
# ---------------------------------------------------------------------------


def _normalize_allowed_branch_ids(allowed_branch_ids: Optional[list[UUID]]) -> Optional[set[UUID]]:
    if allowed_branch_ids is None:
        return None
    return {branch_id for branch_id in allowed_branch_ids}


def _require_verification_rollout(context: ConsoleAuthContext) -> None:
    if not resolve_consultant_verification_enabled(context):
        raise ConsoleAPIError(
            409,
            "ACCESS_DENIED",
            "Consultant verification pilot is not enabled for this client",
        )


def _ensure_session_scope(
    session_row: ConsoleConsultantVerificationSession,
    *,
    context: ConsoleAuthContext,
    allowed_branch_ids: Optional[set[UUID]],
    current_branch_id: UUID | None = None,
) -> None:
    if session_row.client_id != context.client.id:
        raise ConsoleAPIError(404, "NOT_FOUND", "Consultant verification session not found")
    if allowed_branch_ids is not None:
        if session_row.branch_id is None or session_row.branch_id not in allowed_branch_ids:
            raise ConsoleAPIError(404, "NOT_FOUND", "Consultant verification session not found")
    if current_branch_id is not None and session_row.branch_id != current_branch_id:
        raise ConsoleAPIError(404, "NOT_FOUND", "Consultant verification session not found")


def _build_runtime_remote_jid(session_id: UUID) -> str:
    return f"console-verification-{session_id}@simulation.truffles"


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str) and value.strip():
        raw = value.strip()
        if raw.endswith("Z"):
            raw = f"{raw[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _strip_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _as_json_dict(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return jsonable_encoder(value)
    return {}


def _as_json_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in jsonable_encoder(value) if isinstance(item, dict)]


def _extract_turn_source_refs(decision_meta: dict[str, Any]) -> list[str]:
    collected: list[str] = []

    def _append_many(value: object) -> None:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    collected.append(item.strip())

    _append_many(decision_meta.get("fact_evidence_refs"))
    _append_many(decision_meta.get("pack_refs"))
    _append_many(decision_meta.get("info_sections"))
    llm_policy_core = decision_meta.get("llm_policy_core")
    if isinstance(llm_policy_core, dict):
        _append_many(llm_policy_core.get("pack_refs"))
    seen: set[str] = set()
    deduped: list[str] = []
    for item in collected:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _resolve_turn_outcome(decision_meta: dict[str, Any], *, would_book: bool) -> str:
    turn_outcome = decision_meta.get("turn_outcome") if isinstance(decision_meta.get("turn_outcome"), dict) else {}
    llm_audit = (
        decision_meta.get("llm_policy_plan_audit")
        if isinstance(decision_meta.get("llm_policy_plan_audit"), dict)
        else {}
    )
    llm_core = decision_meta.get("llm_policy_core") if isinstance(decision_meta.get("llm_policy_core"), dict) else {}

    action_tokens = [
        decision_meta.get("action"),
        turn_outcome.get("tool_action"),
        llm_audit.get("final_action"),
        llm_core.get("final_action"),
    ]
    normalized = {
        str(item).strip().casefold()
        for item in action_tokens
        if isinstance(item, str) and item.strip()
    }

    if normalized & {"handoff", "escalate", "pending_escalation"}:
        return "handoff"
    if normalized & {
        "collect",
        "booking",
        "calendar.list_slots",
        "calendar.book_slot",
        "calendar.reschedule",
        "calendar.cancel",
    }:
        return "collect"
    if isinstance(turn_outcome.get("expected_reply_type"), str) and turn_outcome.get("expected_reply_type"):
        return "collect"
    if would_book:
        return "collect"
    return "fact"


def _resolve_gap_detected(decision_meta: dict[str, Any], *, assistant_content: str | None) -> bool:
    turn_outcome = decision_meta.get("turn_outcome") if isinstance(decision_meta.get("turn_outcome"), dict) else {}
    if turn_outcome.get("contract_status") == "degraded":
        return True
    if decision_meta.get("llm_policy_override_reason_missing_detected"):
        return True
    minimum_data = decision_meta.get("minimum_data_contract")
    if isinstance(minimum_data, dict) and minimum_data.get("ready") is False:
        return True
    return not bool(_strip_text(assistant_content))


def _resolve_business_verdict(
    *,
    outcome: str,
    would_book: bool,
    would_handoff: bool,
    gap_detected: bool,
) -> str:
    if gap_detected:
        return "gap_detected"
    if would_handoff or outcome == "handoff":
        return "handoff"
    if outcome == "collect" and not would_book:
        return "needs_clarification"
    return "answered"


def _serialize_user_snapshot(user: User, *, remote_jid: str) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "remote_jid": remote_jid,
        "name": user.name,
        "phone": user.phone,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
        "telegram_topic_id": user.telegram_topic_id,
        "metadata": jsonable_encoder(user.user_metadata or {}),
    }


def _serialize_conversation_snapshot(conversation: Conversation) -> dict[str, Any]:
    return {
        "id": str(conversation.id),
        "state": conversation.state,
        "status": conversation.status,
        "context": jsonable_encoder(conversation.context or {}),
        "started_at": conversation.started_at.isoformat() if conversation.started_at else None,
        "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
        "telegram_topic_id": conversation.telegram_topic_id,
    }


def _serialize_handover_snapshot(handover: Handover) -> dict[str, Any]:
    return {
        "id": str(handover.id),
        "status": handover.status,
        "trigger_type": handover.trigger_type,
        "trigger_value": handover.trigger_value,
        "user_message": handover.user_message,
        "context_summary": handover.context_summary,
        "messages": jsonable_encoder(handover.messages or []),
        "meta": jsonable_encoder(handover.meta or {}),
        "adapter_type": handover.adapter_type,
        "channel": handover.channel,
        "channel_ref": handover.channel_ref,
        "trigger_message_id": str(handover.trigger_message_id) if handover.trigger_message_id else None,
        "created_at": handover.created_at.isoformat() if handover.created_at else None,
        "notified_at": handover.notified_at.isoformat() if handover.notified_at else None,
        "telegram_message_id": handover.telegram_message_id,
    }


def _serialize_appointment_snapshot(runtime_db: Session, appointment: Appointment) -> dict[str, Any]:
    services = (
        runtime_db.query(AppointmentServiceModel)
        .filter(AppointmentServiceModel.appointment_id == appointment.id)
        .all()
    )
    return {
        "id": str(appointment.id),
        "branch_id": str(appointment.branch_id),
        "specialist_id": str(appointment.specialist_id) if appointment.specialist_id else None,
        "user_id": str(appointment.user_id) if appointment.user_id else None,
        "conversation_id": str(appointment.conversation_id) if appointment.conversation_id else None,
        "case_id": str(appointment.case_id) if appointment.case_id else None,
        "status": appointment.status,
        "source": appointment.source,
        "confirmation_policy": appointment.confirmation_policy,
        "start_at": appointment.start_at.isoformat() if appointment.start_at else None,
        "end_at": appointment.end_at.isoformat() if appointment.end_at else None,
        "hold_expires_at": appointment.hold_expires_at.isoformat() if appointment.hold_expires_at else None,
        "customer_name": appointment.customer_name,
        "customer_phone": appointment.customer_phone,
        "notes": appointment.notes,
        "version": appointment.version,
        "services": [
            {
                "service_name": item.service_name,
                "duration_min": item.duration_min,
                "price": item.price,
                "buffer_before_min": item.buffer_before_min,
                "buffer_after_min": item.buffer_after_min,
            }
            for item in services
        ],
    }


def _build_runtime_snapshot(
    *,
    session_row: ConsoleConsultantVerificationSession,
    user: User,
    conversation: Conversation,
    handovers: list[Handover],
    appointments: list[Appointment],
    runtime_db: Session,
) -> dict[str, Any]:
    return {
        "schema_version": _RUNTIME_SNAPSHOT_VERSION,
        "session_id": str(session_row.id),
        "source_mode": session_row.source_mode,
        "challenge_mode": session_row.challenge_mode,
        "user": _serialize_user_snapshot(user, remote_jid=session_row.remote_jid),
        "conversation": _serialize_conversation_snapshot(conversation),
        "handovers": [_serialize_handover_snapshot(item) for item in handovers],
        "appointments": [_serialize_appointment_snapshot(runtime_db, item) for item in appointments],
    }


def _ensure_runtime_user(
    runtime_db: Session,
    *,
    session_row: ConsoleConsultantVerificationSession,
    snapshot: dict[str, Any],
    now: datetime,
) -> User:
    user_snapshot = snapshot.get("user") if isinstance(snapshot.get("user"), dict) else {}
    user = User(
        id=uuid4(),
        client_id=session_row.client_id,
        remote_jid=session_row.remote_jid,
        name=_strip_text(user_snapshot.get("name")),
        phone=_strip_text(user_snapshot.get("phone")),
        user_metadata=_as_json_dict(user_snapshot.get("metadata")),
        created_at=_parse_datetime(user_snapshot.get("created_at")) or session_row.created_at or now,
        last_active_at=_parse_datetime(user_snapshot.get("last_active_at")) or now,
        telegram_topic_id=user_snapshot.get("telegram_topic_id"),
    )
    runtime_db.add(user)
    runtime_db.flush()
    return user


def _ensure_runtime_conversation(
    runtime_db: Session,
    *,
    session_row: ConsoleConsultantVerificationSession,
    user: User,
    snapshot: dict[str, Any],
    now: datetime,
) -> Conversation:
    conversation_snapshot = (
        snapshot.get("conversation") if isinstance(snapshot.get("conversation"), dict) else {}
    )
    conversation = Conversation(
        id=uuid4(),
        client_id=session_row.client_id,
        branch_id=session_row.branch_id,
        user_id=user.id,
        channel=_CONSULTANT_VERIFICATION_CHANNEL,
        status=str(conversation_snapshot.get("status") or "active"),
        started_at=_parse_datetime(conversation_snapshot.get("started_at")) or session_row.created_at or now,
        last_message_at=_parse_datetime(conversation_snapshot.get("last_message_at")),
        telegram_topic_id=conversation_snapshot.get("telegram_topic_id"),
        state=str(conversation_snapshot.get("state") or "bot_active"),
        context=_as_json_dict(conversation_snapshot.get("context")),
    )
    runtime_db.add(conversation)
    runtime_db.flush()
    return conversation


def _seed_runtime_messages(
    runtime_db: Session,
    *,
    session_row: ConsoleConsultantVerificationSession,
    conversation: Conversation,
    turns: list[ConsoleConsultantVerificationTurn],
) -> None:
    for turn in turns:
        role = "assistant" if turn.role == "consultant" else ("system" if turn.role == "system" else "user")
        created_at = turn.created_at or datetime.now(timezone.utc)
        message = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            client_id=session_row.client_id,
            role=role,
            content=turn.content,
            intent=None,
            confidence=None,
            message_metadata=_as_json_dict(turn.message_metadata),
            created_at=created_at,
            processed_at=created_at if role in {"assistant", "system"} else None,
        )
        runtime_db.add(message)
    runtime_db.flush()


def _seed_runtime_handovers(
    runtime_db: Session,
    *,
    session_row: ConsoleConsultantVerificationSession,
    conversation: Conversation,
    snapshot: dict[str, Any],
) -> None:
    for payload in _as_json_list(snapshot.get("handovers")):
        handover = Handover(
            id=uuid4(),
            conversation_id=conversation.id,
            client_id=session_row.client_id,
            trigger_type=str(payload.get("trigger_type") or "simulation"),
            trigger_value=_strip_text(payload.get("trigger_value")),
            status=str(payload.get("status") or "pending"),
            user_message=_strip_text(payload.get("user_message")),
            created_at=_parse_datetime(payload.get("created_at")) or datetime.now(timezone.utc),
            context_summary=_strip_text(payload.get("context_summary")),
            messages=_as_json_list(payload.get("messages")),
            adapter_type=_strip_text(payload.get("adapter_type")) or "telegram",
            channel=_strip_text(payload.get("channel")) or "telegram",
            channel_ref=_strip_text(payload.get("channel_ref")) or session_row.remote_jid,
            meta=_as_json_dict(payload.get("meta")),
            notified_at=_parse_datetime(payload.get("notified_at")),
            telegram_message_id=payload.get("telegram_message_id"),
        )
        runtime_db.add(handover)
    runtime_db.flush()


def _seed_runtime_appointments(
    runtime_db: Session,
    *,
    session_row: ConsoleConsultantVerificationSession,
    conversation: Conversation,
    user: User,
    snapshot: dict[str, Any],
) -> None:
    for payload in _as_json_list(snapshot.get("appointments")):
        appointment = Appointment(
            id=uuid4(),
            client_id=session_row.client_id,
            branch_id=session_row.branch_id or UUID(str(payload.get("branch_id"))),
            specialist_id=UUID(str(payload["specialist_id"])) if payload.get("specialist_id") else None,
            user_id=user.id,
            conversation_id=conversation.id,
            case_id=None,
            status=str(payload.get("status") or "REQUESTED"),
            source=str(payload.get("source") or _CONSULTANT_VERIFICATION_SOURCE),
            confirmation_policy=str(payload.get("confirmation_policy") or "manager"),
            start_at=_parse_datetime(payload.get("start_at")) or datetime.now(timezone.utc),
            end_at=_parse_datetime(payload.get("end_at")) or datetime.now(timezone.utc),
            hold_expires_at=_parse_datetime(payload.get("hold_expires_at")),
            customer_name=_strip_text(payload.get("customer_name")),
            customer_phone=_strip_text(payload.get("customer_phone")),
            notes=_strip_text(payload.get("notes")),
            version=int(payload.get("version") or 1),
        )
        runtime_db.add(appointment)
        runtime_db.flush()
        services = payload.get("services") if isinstance(payload.get("services"), list) else []
        for item in services:
            if not isinstance(item, dict):
                continue
            runtime_db.add(
                AppointmentServiceModel(
                    id=uuid4(),
                    appointment_id=appointment.id,
                    service_id=None,
                    service_name=str(item.get("service_name") or "услуга"),
                    duration_min=int(item.get("duration_min") or 0),
                    price=item.get("price"),
                    buffer_before_min=int(item.get("buffer_before_min") or 0),
                    buffer_after_min=int(item.get("buffer_after_min") or 0),
                    created_at=datetime.now(timezone.utc),
                )
            )
    runtime_db.flush()


def _build_runtime_payload(
    *,
    session_row: ConsoleConsultantVerificationSession,
    client: Client,
    content: str,
    now: datetime,
    instance_id: str | None,
) -> WebhookRequest:
    client_slug = _resolve_client_slug(client)
    metadata = WebhookMetadata(
        sender="console_owner",
        timestamp=int(now.timestamp()),
        messageId=f"console-consultant-verification-{uuid4()}",
        remoteJid=session_row.remote_jid,
        instanceId=instance_id,
        simulation_mode=True,
        simulation_id=str(session_row.id),
        simulation_llm=True,
    )
    tenant_context = WebhookTenantContext(
        client_id=session_row.client_id,
        branch_id=session_row.branch_id,
        client_slug=client_slug,
        branch_slug=None,
        instance_id=instance_id,
        source="system",
        origin_source=_CONSULTANT_VERIFICATION_SOURCE,
    )
    return WebhookRequest(
        client_slug=client_slug,
        body=WebhookBody(
            messageType="text",
            message=content,
            metadata=metadata,
        ),
        tenant_context=tenant_context,
    )


def _extract_new_trace_entries(
    previous_snapshot: dict[str, Any],
    conversation: Conversation,
) -> list[dict[str, Any]]:
    current_context = conversation.context if isinstance(conversation.context, dict) else {}
    current_trace = current_context.get(DECISION_TRACE_KEY) if isinstance(current_context.get(DECISION_TRACE_KEY), list) else []
    previous_context = (
        previous_snapshot.get("conversation", {}).get("context")
        if isinstance(previous_snapshot.get("conversation"), dict)
        else {}
    )
    previous_trace = previous_context.get(DECISION_TRACE_KEY) if isinstance(previous_context, dict) and isinstance(previous_context.get(DECISION_TRACE_KEY), list) else []
    if len(current_trace) >= len(previous_trace):
        trimmed = current_trace[len(previous_trace):]
        if trimmed:
            return [item for item in trimmed if isinstance(item, dict)]
    return [item for item in current_trace if isinstance(item, dict)]


def _capture_runtime_result(
    runtime_db: Session,
    *,
    session_row: ConsoleConsultantVerificationSession,
    previous_snapshot: dict[str, Any],
    response: Any,
) -> dict[str, Any]:
    conversation = runtime_db.query(Conversation).filter(Conversation.id == response.conversation_id).first()
    if not isinstance(conversation, Conversation):
        raise ConsoleAPIError(500, "SERVER_ERROR", "Simulation conversation was not produced")

    user = runtime_db.query(User).filter(User.id == conversation.user_id).first()
    if not isinstance(user, User):
        raise ConsoleAPIError(500, "SERVER_ERROR", "Simulation user was not produced")

    messages = (
        runtime_db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    latest_user_message = next((item for item in reversed(messages) if item.role == "user"), None)
    latest_assistant_message = next(
        (item for item in reversed(messages) if item.role in {"assistant", "system"}),
        None,
    )
    if latest_user_message is None:
        raise ConsoleAPIError(500, "SERVER_ERROR", "Simulation did not persist the owner message")

    handovers = (
        runtime_db.query(Handover)
        .filter(Handover.conversation_id == conversation.id)
        .order_by(Handover.created_at.asc())
        .all()
    )
    appointments = (
        runtime_db.query(Appointment)
        .filter(Appointment.conversation_id == conversation.id)
        .order_by(Appointment.created_at.asc())
        .all()
    )

    assistant_content = None
    assistant_role = "consultant"
    if isinstance(latest_assistant_message, Message):
        assistant_content = latest_assistant_message.content
        if latest_assistant_message.role == "system":
            assistant_role = "system"
    if not assistant_content:
        assistant_content = response.bot_response or response.message
        assistant_role = "system"

    decision_meta = {}
    if isinstance(latest_user_message.message_metadata, dict):
        raw_decision_meta = latest_user_message.message_metadata.get("decision_meta")
        if isinstance(raw_decision_meta, dict):
            decision_meta = jsonable_encoder(raw_decision_meta)

    preview = {
        "simulation_mode": True,
        "simulation_id": str(session_row.id),
        "would_handoff": bool(handovers),
        "would_book": bool(appointments),
        "handover_ids": [str(item.id) for item in handovers],
        "appointment_ids": [str(item.id) for item in appointments],
        "transport_status": (
            (decision_meta.get("turn_outcome") or {}).get("observability", {}).get("transport_status")
            if isinstance((decision_meta.get("turn_outcome") or {}).get("observability"), dict)
            else None
        ),
        "outbox_suppressed": bool(decision_meta.get("outbox_simulated")) or bool(response.bot_response),
    }
    source_refs = _extract_turn_source_refs(decision_meta)
    outcome = _resolve_turn_outcome(decision_meta, would_book=bool(preview["would_book"]))
    gap_detected = _resolve_gap_detected(decision_meta, assistant_content=assistant_content)
    business_verdict = _resolve_business_verdict(
        outcome=outcome,
        would_book=bool(preview["would_book"]),
        would_handoff=bool(preview["would_handoff"]),
        gap_detected=gap_detected,
    )
    preview["gap_detected"] = gap_detected

    runtime_snapshot = _build_runtime_snapshot(
        session_row=session_row,
        user=user,
        conversation=conversation,
        handovers=handovers,
        appointments=appointments,
        runtime_db=runtime_db,
    )
    decision_trace = _extract_new_trace_entries(previous_snapshot, conversation)

    owner_message_metadata = jsonable_encoder(latest_user_message.message_metadata or {})
    assistant_message_metadata = (
        jsonable_encoder(latest_assistant_message.message_metadata or {})
        if isinstance(latest_assistant_message, Message) and isinstance(latest_assistant_message.message_metadata, dict)
        else {}
    )

    return {
        "owner": {
            "content": latest_user_message.content,
            "message_metadata": owner_message_metadata,
            "created_at": latest_user_message.created_at,
        },
        "assistant": {
            "role": assistant_role,
            "content": assistant_content,
            "message_metadata": assistant_message_metadata,
            "decision_meta": decision_meta,
            "decision_trace": decision_trace,
            "source_refs": source_refs,
            "preview": preview,
            "outcome": outcome,
            "business_verdict": business_verdict,
            "created_at": (
                latest_assistant_message.created_at
                if isinstance(latest_assistant_message, Message)
                else datetime.now(timezone.utc)
            ),
        },
        "runtime_snapshot": runtime_snapshot,
    }


async def _run_consultant_verification_simulation(
    *,
    db: Session,
    session_row: ConsoleConsultantVerificationSession,
    client: Client,
    previous_turns: list[ConsoleConsultantVerificationTurn],
    content: str,
    now: datetime,
    runtime_truth_override: RuntimeTruth | None = None,
) -> dict[str, Any]:
    session_factory = sessionmaker(
        bind=db.get_bind(),
        class_=_SimulationRuntimeSession,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    runtime_db = session_factory()
    previous_snapshot = _as_json_dict(session_row.runtime_snapshot)
    try:
        user = _ensure_runtime_user(
            runtime_db,
            session_row=session_row,
            snapshot=previous_snapshot,
            now=now,
        )
        conversation = _ensure_runtime_conversation(
            runtime_db,
            session_row=session_row,
            user=user,
            snapshot=previous_snapshot,
            now=now,
        )
        _seed_runtime_messages(
            runtime_db,
            session_row=session_row,
            conversation=conversation,
            turns=previous_turns,
        )
        _seed_runtime_handovers(
            runtime_db,
            session_row=session_row,
            conversation=conversation,
            snapshot=previous_snapshot,
        )
        _seed_runtime_appointments(
            runtime_db,
            session_row=session_row,
            conversation=conversation,
            user=user,
            snapshot=previous_snapshot,
        )
        instance_id = get_instance_id(
            runtime_db,
            session_row.client_id,
            branch_id=session_row.branch_id,
            remote_jid=session_row.remote_jid,
        )
        payload = _build_runtime_payload(
            session_row=session_row,
            client=client,
            content=content,
            now=now,
            instance_id=instance_id,
        )
        set_runtime_truth_override(runtime_truth_override)
        response = await reasoning_core.handle_webhook_payload(
            payload,
            runtime_db,
            provided_secret=None,
            enforce_secret=False,
        )
        return _capture_runtime_result(
            runtime_db,
            session_row=session_row,
            previous_snapshot=previous_snapshot,
            response=response,
        )
    finally:
        set_runtime_truth_override(None)
        runtime_db.rollback()
        runtime_db.close()


def _build_turn_record(turn: ConsoleConsultantVerificationTurn) -> ConsoleConsultantVerificationTurnRecord:
    preview = _as_json_dict(turn.preview)
    return ConsoleConsultantVerificationTurnRecord(
        id=turn.id,
        turn_index=turn.turn_index,
        role=str(turn.role),
        content=turn.content,
        created_at=turn.created_at.isoformat() if turn.created_at else datetime.now(timezone.utc).isoformat(),
        outcome=turn.outcome,
        business_verdict=turn.business_verdict,
        source_refs=[item for item in (turn.source_refs or []) if isinstance(item, str)],
        decision_meta=_as_json_dict(turn.decision_meta),
        decision_trace=[item for item in (turn.decision_trace or []) if isinstance(item, dict)],
        preview=preview,
        would_handoff=bool(preview.get("would_handoff")),
        would_book=bool(preview.get("would_book")),
        gap_detected=bool(preview.get("gap_detected")),
    )


def _build_session_summary(
    turns: list[ConsoleConsultantVerificationTurnRecord],
) -> ConsoleConsultantVerificationSessionSummary:
    latest_verdict = None
    weak_turns: list[ConsoleConsultantVerificationSessionWeakTurn] = []
    owner_prompt_total = 0
    latest_owner_prompt = ""
    answered_total = 0
    needs_clarification_total = 0
    handoff_total = 0
    gap_detected_total = 0
    assistant_turns_total = 0

    for turn in turns:
        if turn.role == "owner":
            owner_prompt_total += 1
            latest_owner_prompt = turn.content
            continue

        assistant_turns_total += 1
        latest_verdict = turn.business_verdict
        if turn.business_verdict == "answered":
            answered_total += 1
        elif turn.business_verdict == "needs_clarification":
            needs_clarification_total += 1
        elif turn.business_verdict == "handoff":
            handoff_total += 1
        elif turn.business_verdict == "gap_detected":
            gap_detected_total += 1
            if len(weak_turns) < 3:
                weak_turns.append(
                    ConsoleConsultantVerificationSessionWeakTurn(
                        assistant_turn_id=turn.id,
                        assistant_turn_index=turn.turn_index,
                        owner_prompt=latest_owner_prompt,
                        assistant_excerpt=turn.content[:240],
                        business_verdict=turn.business_verdict,
                    )
                )

    return ConsoleConsultantVerificationSessionSummary(
        assistant_turns_total=assistant_turns_total,
        answered_total=answered_total,
        needs_clarification_total=needs_clarification_total,
        handoff_total=handoff_total,
        gap_detected_total=gap_detected_total,
        replay_prompt_total=owner_prompt_total,
        latest_verdict=latest_verdict,
        weak_turns=weak_turns,
    )


def _build_session_record(session_row: ConsoleConsultantVerificationSession) -> ConsoleConsultantVerificationSessionRecord:
    preview = _as_json_dict(session_row.latest_preview)
    return ConsoleConsultantVerificationSessionRecord(
        id=session_row.id,
        client_id=session_row.client_id,
        branch_id=session_row.branch_id,
        actor_agent_id=session_row.actor_agent_id,
        actor_role=session_row.actor_role,
        source_mode=session_row.source_mode,
        challenge_mode=session_row.challenge_mode,
        status=session_row.status,
        title=session_row.title,
        turns_total=int(session_row.turns_total or 0),
        latest_outcome=session_row.latest_outcome,
        latest_business_verdict=session_row.latest_business_verdict,
        latest_preview=preview,
        created_at=session_row.created_at.isoformat() if session_row.created_at else datetime.now(timezone.utc).isoformat(),
        updated_at=session_row.updated_at.isoformat() if session_row.updated_at else datetime.now(timezone.utc).isoformat(),
        last_message_at=session_row.last_message_at.isoformat() if session_row.last_message_at else None,
    )


def _build_session_response(
    session_row: ConsoleConsultantVerificationSession,
    turns: list[ConsoleConsultantVerificationTurn],
) -> ConsoleConsultantVerificationSessionResponse:
    turn_records = [_build_turn_record(turn) for turn in turns]
    return ConsoleConsultantVerificationSessionResponse(
        session=_build_session_record(session_row),
        turns=turn_records,
        summary=_build_session_summary(turn_records),
    )


def _load_session_turns(db: Session, session_id: UUID) -> list[ConsoleConsultantVerificationTurn]:
    return (
        db.query(ConsoleConsultantVerificationTurn)
        .filter(ConsoleConsultantVerificationTurn.session_id == session_id)
        .order_by(ConsoleConsultantVerificationTurn.turn_index.asc())
        .all()
    )


def _resolve_compare_case_label(
    *,
    prompt: str,
    finding: ConsoleConsultantVerificationFinding | None,
) -> str:
    if isinstance(finding, ConsoleConsultantVerificationFinding):
        return finding.family_label
    normalized_prompt = _strip_text(prompt) or "Сценарий сравнения"
    return normalized_prompt[:96]


def _build_compare_session_row(
    *,
    context: ConsoleAuthContext,
    branch_id: UUID | None,
    source_mode: str,
    challenge_mode: str,
    now: datetime,
    title: str,
) -> ConsoleConsultantVerificationSession:
    session_id = uuid4()
    return ConsoleConsultantVerificationSession(
        id=session_id,
        client_id=context.client.id,
        branch_id=branch_id,
        actor_agent_id=context.agent.id,
        actor_role=context.role,
        source_mode=source_mode,
        challenge_mode=challenge_mode,
        status="active",
        title=title,
        remote_jid=_build_runtime_remote_jid(session_id),
        runtime_snapshot={
            "schema_version": _RUNTIME_SNAPSHOT_VERSION,
            "source_mode": source_mode,
            "challenge_mode": challenge_mode,
        },
        latest_preview={"simulation_mode": True, "simulation_id": str(session_id)},
        turns_total=0,
        created_at=now,
        updated_at=now,
    )


def _build_turn_record_from_simulation_payload(
    *,
    assistant_payload: dict[str, Any],
) -> ConsoleConsultantVerificationTurnRecord:
    preview = _as_json_dict(assistant_payload.get("preview"))
    created_at = assistant_payload.get("created_at")
    created_at_value = created_at.isoformat() if isinstance(created_at, datetime) else datetime.now(timezone.utc).isoformat()
    raw_source_refs = assistant_payload.get("source_refs")
    source_refs = [item.strip() for item in raw_source_refs if isinstance(item, str) and item.strip()] if isinstance(raw_source_refs, list) else []
    decision_trace = [item for item in _as_json_list(assistant_payload.get("decision_trace")) if isinstance(item, dict)]
    return ConsoleConsultantVerificationTurnRecord(
        id=uuid4(),
        turn_index=2,
        role=str(assistant_payload.get("role") or "consultant"),
        content=str(assistant_payload.get("content") or ""),
        created_at=created_at_value,
        outcome=assistant_payload.get("outcome"),
        business_verdict=assistant_payload.get("business_verdict"),
        source_refs=source_refs,
        decision_meta=_as_json_dict(assistant_payload.get("decision_meta")),
        decision_trace=decision_trace,
        preview=preview,
        would_handoff=bool(preview.get("would_handoff")),
        would_book=bool(preview.get("would_book")),
        gap_detected=bool(preview.get("gap_detected")),
    )


def _compare_delta_label(delta: str) -> str:
    return _COMPARE_DELTA_LABELS.get(delta, "Нужно проверить")


def _readiness_status_label(status: str) -> str:
    return _READINESS_STATUS_LABELS.get(status, "Нужно проверить")


def _resolve_compare_delta(
    *,
    live_turn: ConsoleConsultantVerificationTurnRecord,
    draft_turn: ConsoleConsultantVerificationTurnRecord,
) -> tuple[str, str]:
    live_score = _VERDICT_SCORES.get(live_turn.business_verdict or "", 1)
    draft_score = _VERDICT_SCORES.get(draft_turn.business_verdict or "", 1)
    live_label = live_turn.business_verdict or "unknown"
    draft_label = draft_turn.business_verdict or "unknown"
    if draft_score > live_score:
        return (
            "improved",
            f"Draft улучшил исход: было `{live_label}`, стало `{draft_label}`.",
        )
    if draft_score < live_score:
        return (
            "regressed",
            f"Draft ухудшил исход: было `{live_label}`, стало `{draft_label}`.",
        )
    same_contract = (
        live_turn.business_verdict == draft_turn.business_verdict
        and live_turn.outcome == draft_turn.outcome
    )
    same_text = _strip_text(live_turn.content) == _strip_text(draft_turn.content)
    if same_contract and same_text:
        return ("unchanged", "Поведение по сути не изменилось между live и draft.")
    return (
        "needs_review",
        "Категория ответа не стала хуже, но поведение или формулировка изменились. Проверьте вручную.",
    )


def _resolve_compare_branch_id(
    *,
    context: ConsoleAuthContext,
    allowed_branch_ids: Optional[set[UUID]],
) -> UUID:
    return _resolve_verification_branch_id(
        context=context,
        allowed_branch_ids=allowed_branch_ids,
        required=True,
    )


def _load_latest_draft_version(
    *,
    db: Session,
    client_id: UUID,
    branch_id: UUID,
) -> KnowledgeVersion | None:
    return (
        db.query(KnowledgeVersion)
        .filter(
            KnowledgeVersion.client_id == client_id,
            KnowledgeVersion.branch_id == branch_id,
            KnowledgeVersion.status == "draft",
        )
        .order_by(KnowledgeVersion.created_at.desc())
        .first()
    )


def _resolve_draft_runtime_truth_data(
    *,
    db: Session,
    context: ConsoleAuthContext,
    branch_id: UUID,
) -> tuple[KnowledgeVersion, RuntimeTruth, str]:
    draft_version = _load_latest_draft_version(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    if not isinstance(draft_version, KnowledgeVersion) or not isinstance(draft_version.payload_json, dict):
        raise ConsoleAPIError(
            409,
            "DRAFT_REQUIRED",
            "Validate and save a draft in Knowledge before comparing live vs draft",
        )
    draft_hash = build_knowledge_draft_hash_from_payload(draft_version.payload_json)
    runtime_truth = build_runtime_truth_from_payload(
        payload_json=draft_version.payload_json,
        client_slug=_resolve_client_slug(context.client),
        branch_id=branch_id,
        source="knowledge_draft",
        version_id=str(draft_version.id),
        allow_fallback=False,
    )
    if not isinstance(runtime_truth.truth, dict) or not runtime_truth.truth:
        raise ConsoleAPIError(
            409,
            "DRAFT_KNOWLEDGE_INVALID",
            "Draft knowledge cannot be used for consultant verification preview",
        )
    return draft_version, runtime_truth, draft_hash


def _resolve_compare_draft_truth(
    *,
    db: Session,
    context: ConsoleAuthContext,
    branch_id: UUID,
) -> tuple[RuntimeTruth, str]:
    _draft_version, runtime_truth, draft_hash = _resolve_draft_runtime_truth_data(
        db=db,
        context=context,
        branch_id=branch_id,
    )
    return runtime_truth, draft_hash


def _resolve_live_runtime_truth_data(
    *,
    db: Session,
    context: ConsoleAuthContext,
    branch_id: UUID,
) -> tuple[KnowledgeVersion, RuntimeTruth]:
    live_version = _load_active_knowledge_for_branch(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    if not isinstance(live_version, KnowledgeVersion) or not isinstance(live_version.payload_json, dict):
        raise ConsoleAPIError(
            409,
            "LIVE_KNOWLEDGE_REQUIRED",
            "Publish at least one live knowledge version before compare",
        )
    runtime_truth = build_runtime_truth_from_payload(
        payload_json=live_version.payload_json,
        client_slug=_resolve_client_slug(context.client),
        branch_id=branch_id,
        source="knowledge_active_version",
        version_id=str(live_version.id),
        allow_fallback=False,
    )
    if not isinstance(runtime_truth.truth, dict) or not runtime_truth.truth:
        raise ConsoleAPIError(
            409,
            "LIVE_KNOWLEDGE_REQUIRED",
            "Publish at least one live knowledge version before compare",
        )
    return live_version, runtime_truth


def _resolve_published_runtime_truth_data(
    *,
    db: Session,
    context: ConsoleAuthContext,
    branch_id: UUID,
) -> tuple[KnowledgeVersion, RuntimeTruth]:
    published_version = _load_published_knowledge_for_branch(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    if not isinstance(published_version, KnowledgeVersion) or not isinstance(published_version.payload_json, dict):
        raise ConsoleAPIError(
            409,
            "PUBLISHED_KNOWLEDGE_REQUIRED",
            "Publish at least one knowledge version before previewing the published candidate",
        )
    runtime_truth = build_runtime_truth_from_payload(
        payload_json=published_version.payload_json,
        client_slug=_resolve_client_slug(context.client),
        branch_id=branch_id,
        source="knowledge_published_candidate",
        version_id=str(published_version.id),
        allow_fallback=False,
    )
    if not isinstance(runtime_truth.truth, dict) or not runtime_truth.truth:
        raise ConsoleAPIError(
            409,
            "PUBLISHED_KNOWLEDGE_REQUIRED",
            "Published knowledge cannot be used for consultant verification preview",
        )
    return published_version, runtime_truth


def _resolve_live_runtime_truth(
    *,
    db: Session,
    context: ConsoleAuthContext,
    branch_id: UUID,
) -> RuntimeTruth:
    _live_version, live_truth = _resolve_live_runtime_truth_data(
        db=db,
        context=context,
        branch_id=branch_id,
    )
    return live_truth


def _resolve_preview_truth_snapshot(
    *,
    db: Session,
    context: ConsoleAuthContext,
    branch_id: UUID,
    source_mode: str,
    branch: Branch | None,
    live_version: KnowledgeVersion | None,
    published_version: KnowledgeVersion | None,
) -> tuple[RuntimeTruth, dict[str, Any]]:
    activation_job = (
        get_latest_knowledge_activation_job(
            db,
            branch_id=branch_id,
            version_id=published_version.id,
        )
        if published_version is not None
        else None
    )
    live_activation_status, _, _, live_activation_error, _live_activation_job_id = (
        _resolve_live_activation_state(
            active_version=live_version,
            published_version=published_version,
            branch=branch,
            activation_job=activation_job,
        )
    )
    live_activation_safe_mode = bool(getattr(branch, "knowledge_safe_mode", False))
    if source_mode == "draft":
        draft_version, runtime_truth, draft_hash = _resolve_draft_runtime_truth_data(
            db=db,
            context=context,
            branch_id=branch_id,
        )
        return runtime_truth, _build_pinned_truth_snapshot(
            runtime_truth=runtime_truth,
            payload_json=draft_version.payload_json,
            branch_id=branch_id,
            source_mode=source_mode,
            draft_hash=draft_hash,
            live_activation_status=live_activation_status,
            live_activation_error=live_activation_error,
            live_activation_safe_mode=live_activation_safe_mode,
        )
    if source_mode == "published":
        resolved_published_version, runtime_truth = _resolve_published_runtime_truth_data(
            db=db,
            context=context,
            branch_id=branch_id,
        )
        return runtime_truth, _build_pinned_truth_snapshot(
            runtime_truth=runtime_truth,
            payload_json=resolved_published_version.payload_json,
            branch_id=branch_id,
            source_mode=source_mode,
            live_activation_status=live_activation_status,
            live_activation_error=live_activation_error,
            live_activation_safe_mode=live_activation_safe_mode,
        )

    resolved_live_version, runtime_truth = _resolve_live_runtime_truth_data(
        db=db,
        context=context,
        branch_id=branch_id,
    )
    return runtime_truth, _build_pinned_truth_snapshot(
        runtime_truth=runtime_truth,
        payload_json=resolved_live_version.payload_json,
        branch_id=branch_id,
        source_mode=source_mode,
        live_activation_status=live_activation_status,
        live_activation_error=live_activation_error,
        live_activation_safe_mode=live_activation_safe_mode,
    )


def _resolve_verification_session_runtime_truth(
    *,
    db: Session,
    context: ConsoleAuthContext,
    session_row: ConsoleConsultantVerificationSession,
) -> tuple[RuntimeTruth, dict[str, Any]]:
    branch_id = session_row.branch_id
    if branch_id is None:
        raise ConsoleAPIError(400, "BRANCH_SELECTION_REQUIRED", "Select a branch before consultant verification")
    pinned_truth = _load_pinned_truth_from_runtime_snapshot(
        context=context,
        session_row=session_row,
    )
    if pinned_truth is not None:
        return pinned_truth

    branch = None
    for candidate_branch in getattr(context, "branches", None) or []:
        if getattr(candidate_branch, "id", None) == branch_id:
            branch = candidate_branch
            break
    live_version = _load_active_knowledge_for_branch(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    published_version = _load_published_knowledge_for_branch(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    return _resolve_preview_truth_snapshot(
        db=db,
        context=context,
        branch_id=branch_id,
        source_mode=session_row.source_mode,
        branch=branch,
        live_version=live_version,
        published_version=published_version,
    )


def _resolve_compare_readiness(
    *,
    cases: list[ConsoleConsultantVerificationCompareCaseRecord],
    draft_hash: str | None,
    compared_at: datetime | None,
    compare_required: bool,
) -> ConsoleConsultantVerificationCompareReadiness:
    if not cases:
        return ConsoleConsultantVerificationCompareReadiness(
            status="blocked",
            status_label=_readiness_status_label("blocked"),
            summary="Нет сценариев для сравнения. Сначала выберите prompt или finding.",
            draft_hash=draft_hash,
            compared_at=compared_at.isoformat() if isinstance(compared_at, datetime) else None,
            compare_required=compare_required,
        )
    improved_total = sum(1 for item in cases if item.delta == "improved")
    unchanged_total = sum(1 for item in cases if item.delta == "unchanged")
    regressed_total = sum(1 for item in cases if item.delta == "regressed")
    manual_review_total = sum(1 for item in cases if item.delta == "needs_review")
    retested_total = sum(1 for item in cases if item.retested_finding)
    if regressed_total > 0:
        status = "needs_attention"
        summary = "Draft показал регрессии. Публиковать изменения без разбора нельзя."
    elif manual_review_total > 0:
        status = "needs_attention"
        summary = "Draft не просел по контракту, но часть ответов изменилась. Нужна ручная проверка."
    else:
        status = "ready"
        summary = "Draft не показал регрессий по выбранным сценариям. Можно использовать это как publish proof."
    return ConsoleConsultantVerificationCompareReadiness(
        status=status,
        status_label=_readiness_status_label(status),
        summary=summary,
        draft_hash=draft_hash,
        compared_at=compared_at.isoformat() if isinstance(compared_at, datetime) else None,
        total_cases=len(cases),
        improved_total=improved_total,
        unchanged_total=unchanged_total,
        regressed_total=regressed_total,
        manual_review_total=manual_review_total,
        retested_total=retested_total,
        compare_required=compare_required,
    )


def _build_compare_case_record(
    *,
    label: str,
    prompt: str,
    finding: ConsoleConsultantVerificationFinding | None,
    live_turn: ConsoleConsultantVerificationTurnRecord,
    draft_turn: ConsoleConsultantVerificationTurnRecord,
    retested_finding: bool,
) -> ConsoleConsultantVerificationCompareCaseRecord:
    delta, summary = _resolve_compare_delta(live_turn=live_turn, draft_turn=draft_turn)
    return ConsoleConsultantVerificationCompareCaseRecord(
        case_id=hashlib.sha1(f"{label}:{prompt}".encode("utf-8")).hexdigest()[:12],
        label=label,
        source="finding" if isinstance(finding, ConsoleConsultantVerificationFinding) else "prompt",
        finding_id=finding.id if isinstance(finding, ConsoleConsultantVerificationFinding) else None,
        live_turn=live_turn,
        draft_turn=draft_turn,
        delta=delta,
        delta_label=_compare_delta_label(delta),
        summary=summary,
        retested_finding=retested_finding,
    )


def _build_readiness_from_compare_payload(
    payload: dict[str, Any] | None,
    *,
    compare_required: bool,
) -> ConsoleConsultantVerificationCompareReadiness:
    if not isinstance(payload, dict):
        return ConsoleConsultantVerificationCompareReadiness(
            status="blocked",
            status_label=_readiness_status_label("blocked"),
            summary="Для текущего сохраненного draft еще нет compare-доказательства.",
            compare_required=compare_required,
        )
    status = str(payload.get("status") or "needs_attention")
    total_cases = int(payload.get("total_cases") or 0)
    improved_total = int(payload.get("improved_total") or 0)
    unchanged_total = int(payload.get("unchanged_total") or 0)
    regressed_total = int(payload.get("regressed_total") or 0)
    manual_review_total = int(payload.get("manual_review_total") or 0)
    return ConsoleConsultantVerificationCompareReadiness(
        status=status,
        status_label=_readiness_status_label(status),
        summary=(
            "Для этого draft нет регрессий по последнему compare."
            if status == "ready"
            else "Последний compare показал регрессии или требует ручной проверки."
        ),
        draft_hash=_strip_text(payload.get("draft_hash")),
        compared_at=_strip_text(payload.get("compared_at")),
        total_cases=total_cases,
        improved_total=improved_total,
        unchanged_total=unchanged_total,
        regressed_total=regressed_total,
        manual_review_total=manual_review_total,
        retested_total=int(payload.get("retested_total") or 0),
        compare_required=compare_required,
    )


def _resolve_finding_language(turn: ConsoleConsultantVerificationTurn | None) -> str:
    if not isinstance(turn, ConsoleConsultantVerificationTurn):
        return "unknown"
    metadata = turn.message_metadata if isinstance(turn.message_metadata, dict) else {}
    for key in ("language", "lang", "locale"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    media_meta = metadata.get("media")
    if isinstance(media_meta, dict):
        transcript_language = media_meta.get("transcript_language")
        if isinstance(transcript_language, str) and transcript_language.strip():
            return transcript_language.strip().lower()
    return "unknown"


def _resolve_finding_miss_type(
    *,
    family_kind: str,
    decision_reason_code: str | None,
) -> str | None:
    if family_kind == "knowledge_gap":
        return decision_reason_code or "owner_flag_gap"
    if family_kind == "clarification_loop":
        return decision_reason_code or "owner_flag_clarification"
    return None


def _upsert_knowledge_backlog_for_finding(
    db: Session,
    *,
    client_id: UUID,
    owner_prompt: str,
    language: str,
    miss_type: str | None,
) -> UUID | None:
    text_value = _strip_text(owner_prompt)
    miss_value = _strip_text(miss_type)
    if not text_value or not miss_value:
        return None
    row = (
        db.execute(
            text(
                """
                INSERT INTO knowledge_backlog (
                  id,
                  client_id,
                  conversation_id,
                  message_id,
                  user_text,
                  language,
                  miss_type,
                  repeat_count,
                  first_seen_at,
                  last_seen_at
                )
                VALUES (
                  gen_random_uuid(),
                  :client_id,
                  NULL,
                  NULL,
                  :user_text,
                  :language,
                  :miss_type,
                  1,
                  NOW(),
                  NOW()
                )
                ON CONFLICT (client_id, language, miss_type, user_text)
                DO UPDATE SET
                  repeat_count = knowledge_backlog.repeat_count + 1,
                  last_seen_at = EXCLUDED.last_seen_at
                RETURNING id
                """
            ),
            {
                "client_id": client_id,
                "user_text": text_value,
                "language": language or "unknown",
                "miss_type": miss_value,
            },
        )
        .mappings()
        .first()
    )
    raw_id = row.get("id") if isinstance(row, dict) else None
    if isinstance(raw_id, UUID):
        return raw_id
    if isinstance(raw_id, str):
        return UUID(raw_id)
    return None


def _find_learning_candidate_id_for_prompt(
    db: Session,
    *,
    client_id: UUID,
    branch_id: UUID | None,
    owner_prompt: str,
) -> UUID | None:
    normalized_prompt = _normalize_finding_text(owner_prompt)
    if not normalized_prompt:
        return None
    query = db.query(LearnedResponse).filter(
        LearnedResponse.client_id == client_id,
        LearnedResponse.question_normalized == normalized_prompt,
        LearnedResponse.status.in_(["pending", "approved"]),
    )
    if branch_id is not None:
        query = query.filter(LearnedResponse.branch_id == branch_id)
    learned_response = (
        query.order_by(LearnedResponse.updated_at.desc(), LearnedResponse.created_at.desc())
        .first()
    )
    if not isinstance(learned_response, LearnedResponse):
        return None
    return learned_response.id


def _build_finding_record(
    finding: ConsoleConsultantVerificationFinding,
) -> ConsoleConsultantVerificationFindingRecord:
    return ConsoleConsultantVerificationFindingRecord(
        id=finding.id,
        client_id=finding.client_id,
        branch_id=finding.branch_id,
        actor_agent_id=finding.actor_agent_id,
        actor_role=finding.actor_role,
        session_id=finding.session_id,
        owner_turn_id=finding.owner_turn_id,
        assistant_turn_id=finding.assistant_turn_id,
        source_mode=finding.source_mode,
        challenge_mode=finding.challenge_mode,
        family_key=finding.family_key,
        family_kind=finding.family_kind,  # type: ignore[arg-type]
        family_label=finding.family_label,
        status=finding.status,  # type: ignore[arg-type]
        status_label=_status_label_for_finding(finding.status),
        owner_prompt=finding.owner_prompt,
        assistant_excerpt=finding.assistant_excerpt,
        owner_note=finding.owner_note,
        resolution_note=finding.resolution_note,
        outcome=finding.outcome,
        business_verdict=finding.business_verdict,
        decision_reason_code=finding.decision_reason_code,
        source_refs=[item for item in (finding.source_refs or []) if isinstance(item, str)],
        latest_preview=_as_json_dict(finding.latest_preview),
        linked_knowledge_backlog_id=finding.linked_knowledge_backlog_id,
        linked_learning_candidate_id=finding.linked_learning_candidate_id,
        repeat_count=int(finding.repeat_count or 1),
        first_captured_at=(
            finding.first_captured_at.isoformat()
            if finding.first_captured_at
            else datetime.now(timezone.utc).isoformat()
        ),
        last_captured_at=(
            finding.last_captured_at.isoformat()
            if finding.last_captured_at
            else datetime.now(timezone.utc).isoformat()
        ),
        created_at=(
            finding.created_at.isoformat()
            if finding.created_at
            else datetime.now(timezone.utc).isoformat()
        ),
        updated_at=(
            finding.updated_at.isoformat()
            if finding.updated_at
            else datetime.now(timezone.utc).isoformat()
        ),
    )


def _get_finding_for_context(
    *,
    db: Session,
    finding_id: UUID,
    context: ConsoleAuthContext,
    allowed_branch_ids: Optional[set[UUID]],
) -> ConsoleConsultantVerificationFinding:
    current_branch_id = _resolve_verification_branch_id(
        context=context,
        allowed_branch_ids=allowed_branch_ids,
        required=False,
    )
    finding = (
        db.query(ConsoleConsultantVerificationFinding)
        .filter(ConsoleConsultantVerificationFinding.id == finding_id)
        .first()
    )
    if not isinstance(finding, ConsoleConsultantVerificationFinding):
        raise ConsoleAPIError(404, "NOT_FOUND", "Consultant verification finding not found")
    if finding.client_id != context.client.id:
        raise ConsoleAPIError(404, "NOT_FOUND", "Consultant verification finding not found")
    if allowed_branch_ids is not None:
        if not finding.branch_id or finding.branch_id not in allowed_branch_ids:
            raise ConsoleAPIError(403, "BRANCH_ACCESS_DENIED", "Access to this branch denied")
    if current_branch_id is not None and finding.branch_id != current_branch_id:
        raise ConsoleAPIError(404, "NOT_FOUND", "Consultant verification finding not found")
    return finding


def _resolve_turn_pair_for_finding(
    *,
    db: Session,
    context: ConsoleAuthContext,
    assistant_turn_id: UUID,
    allowed_branch_ids: Optional[set[UUID]],
) -> tuple[
    ConsoleConsultantVerificationSession,
    ConsoleConsultantVerificationTurnRecord,
    ConsoleConsultantVerificationTurnRecord | None,
]:
    assistant_turn_row = (
        db.query(ConsoleConsultantVerificationTurn)
        .filter(ConsoleConsultantVerificationTurn.id == assistant_turn_id)
        .first()
    )
    if not isinstance(assistant_turn_row, ConsoleConsultantVerificationTurn):
        raise ConsoleAPIError(404, "NOT_FOUND", "Consultant verification turn not found")
    if assistant_turn_row.role == "owner":
        raise ConsoleAPIError(400, "VALIDATION_ERROR", "Only consultant turns can be flagged")
    session_row = _get_session_for_context(
        db=db,
        session_id=assistant_turn_row.session_id,
        context=context,
        allowed_branch_ids=allowed_branch_ids,
    )
    turns = _load_session_turns(db, session_id=session_row.id)
    assistant_index = next(
        (index for index, item in enumerate(turns) if item.id == assistant_turn_row.id),
        None,
    )
    if assistant_index is None:
        raise ConsoleAPIError(404, "NOT_FOUND", "Consultant verification turn not found")
    owner_turn_row = next(
        (item for item in reversed(turns[:assistant_index]) if item.role == "owner"),
        None,
    )
    return (
        session_row,
        _build_turn_record(assistant_turn_row),
        _build_turn_record(owner_turn_row) if isinstance(owner_turn_row, ConsoleConsultantVerificationTurn) else None,
    )


def _get_session_for_context(
    *,
    db: Session,
    session_id: UUID,
    context: ConsoleAuthContext,
    allowed_branch_ids: Optional[set[UUID]],
) -> ConsoleConsultantVerificationSession:
    current_branch_id = _resolve_verification_branch_id(
        context=context,
        allowed_branch_ids=allowed_branch_ids,
        required=False,
    )
    session_row = (
        db.query(ConsoleConsultantVerificationSession)
        .filter(ConsoleConsultantVerificationSession.id == session_id)
        .first()
    )
    if not isinstance(session_row, ConsoleConsultantVerificationSession):
        raise ConsoleAPIError(404, "NOT_FOUND", "Consultant verification session not found")
    _ensure_session_scope(
        session_row,
        context=context,
        allowed_branch_ids=allowed_branch_ids,
        current_branch_id=current_branch_id,
    )
    return session_row


def create_consultant_verification_session(
    *,
    db: Session,
    context: ConsoleAuthContext,
    request: ConsoleConsultantVerificationSessionCreateRequest,
    allowed_branch_ids: Optional[list[UUID]],
    now: datetime,
) -> ConsoleConsultantVerificationSessionResponse:
    _require_verification_rollout(context)
    normalized_branch_ids = _normalize_allowed_branch_ids(allowed_branch_ids)
    branch_id = _resolve_verification_branch_id(
        context=context,
        allowed_branch_ids=normalized_branch_ids,
        required=True,
    )
    selected_branch = None
    for candidate_branch in getattr(context, "branches", None) or []:
        if getattr(candidate_branch, "id", None) == branch_id:
            selected_branch = candidate_branch
            break
    live_version = _load_active_knowledge_for_branch(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    published_version = _load_published_knowledge_for_branch(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    _, source_snapshot = _resolve_preview_truth_snapshot(
        db=db,
        context=context,
        branch_id=branch_id,
        source_mode=request.source_mode,
        branch=selected_branch,
        live_version=live_version,
        published_version=published_version,
    )
    session_id = uuid4()
    session_row = ConsoleConsultantVerificationSession(
        id=session_id,
        client_id=context.client.id,
        branch_id=branch_id,
        actor_agent_id=context.agent.id,
        actor_role=context.role,
        source_mode=request.source_mode,
        challenge_mode=request.challenge_mode,
        status="active",
        title=_strip_text(request.title),
        remote_jid=_build_runtime_remote_jid(session_id),
        runtime_snapshot={
            "schema_version": _RUNTIME_SNAPSHOT_VERSION,
            "source_mode": request.source_mode,
            "challenge_mode": request.challenge_mode,
            "branch_id": str(branch_id),
            **source_snapshot,
        },
        latest_preview={"simulation_mode": True, "simulation_id": str(session_id)},
        turns_total=0,
        created_at=now,
        updated_at=now,
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)
    return _build_session_response(session_row, [])


def list_consultant_verification_sessions(
    *,
    db: Session,
    context: ConsoleAuthContext,
    allowed_branch_ids: Optional[list[UUID]],
    limit: int = 20,
) -> ConsoleConsultantVerificationSessionListResponse:
    _require_verification_rollout(context)
    normalized_branch_ids = _normalize_allowed_branch_ids(allowed_branch_ids)
    branch_id = _resolve_verification_branch_id(
        context=context,
        allowed_branch_ids=normalized_branch_ids,
        required=False,
    )
    query = db.query(ConsoleConsultantVerificationSession).filter(
        ConsoleConsultantVerificationSession.client_id == context.client.id,
    )
    if branch_id is not None:
        query = query.filter(ConsoleConsultantVerificationSession.branch_id == branch_id)
    elif not getattr(context, "branch_restricted", False):
        return ConsoleConsultantVerificationSessionListResponse(items=[])
    elif normalized_branch_ids is not None:
        if not normalized_branch_ids:
            return ConsoleConsultantVerificationSessionListResponse(items=[])
        query = query.filter(ConsoleConsultantVerificationSession.branch_id.in_(normalized_branch_ids))
    items = query.order_by(ConsoleConsultantVerificationSession.updated_at.desc()).limit(max(1, min(limit, 50))).all()
    return ConsoleConsultantVerificationSessionListResponse(
        items=[_build_session_record(item) for item in items],
    )


def get_consultant_verification_session(
    *,
    db: Session,
    context: ConsoleAuthContext,
    session_id: UUID,
    allowed_branch_ids: Optional[list[UUID]],
) -> ConsoleConsultantVerificationSessionResponse:
    _require_verification_rollout(context)
    session_row = _get_session_for_context(
        db=db,
        session_id=session_id,
        context=context,
        allowed_branch_ids=_normalize_allowed_branch_ids(allowed_branch_ids),
    )
    turns = _load_session_turns(db, session_id=session_row.id)
    return _build_session_response(session_row, turns)


def list_consultant_verification_findings(
    *,
    db: Session,
    context: ConsoleAuthContext,
    allowed_branch_ids: Optional[list[UUID]],
    status: str | None = None,
    limit: int = 20,
) -> ConsoleConsultantVerificationFindingListResponse:
    _require_verification_rollout(context)
    normalized_branch_ids = _normalize_allowed_branch_ids(allowed_branch_ids)
    branch_id = _resolve_verification_branch_id(
        context=context,
        allowed_branch_ids=normalized_branch_ids,
        required=False,
    )
    query = db.query(ConsoleConsultantVerificationFinding).filter(
        ConsoleConsultantVerificationFinding.client_id == context.client.id,
    )
    if branch_id is not None:
        query = query.filter(ConsoleConsultantVerificationFinding.branch_id == branch_id)
    elif not getattr(context, "branch_restricted", False):
        return ConsoleConsultantVerificationFindingListResponse(items=[])
    elif normalized_branch_ids is not None:
        if not normalized_branch_ids:
            return ConsoleConsultantVerificationFindingListResponse(items=[])
        query = query.filter(ConsoleConsultantVerificationFinding.branch_id.in_(normalized_branch_ids))
    normalized_status = _strip_text(status)
    if normalized_status:
        cleaned_status = normalized_status.casefold()
        if cleaned_status not in _FINDING_STATUS_LABELS:
            raise ConsoleAPIError(400, "INVALID_PARAM", "Invalid finding status")
        query = query.filter(ConsoleConsultantVerificationFinding.status == cleaned_status)
    items = (
        query.order_by(
            ConsoleConsultantVerificationFinding.last_captured_at.desc(),
            ConsoleConsultantVerificationFinding.updated_at.desc(),
        )
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return ConsoleConsultantVerificationFindingListResponse(
        items=[_build_finding_record(item) for item in items],
    )


def create_consultant_verification_finding(
    *,
    db: Session,
    context: ConsoleAuthContext,
    request: ConsoleConsultantVerificationFindingCreateRequest,
    allowed_branch_ids: Optional[list[UUID]],
    now: datetime,
) -> ConsoleConsultantVerificationFindingRecord:
    _require_verification_rollout(context)
    normalized_branch_ids = _normalize_allowed_branch_ids(allowed_branch_ids)
    session_row, assistant_turn, owner_turn = _resolve_turn_pair_for_finding(
        db=db,
        context=context,
        assistant_turn_id=request.assistant_turn_id,
        allowed_branch_ids=normalized_branch_ids,
    )
    owner_prompt = _strip_text(owner_turn.content if owner_turn else None) or "Исходный вопрос недоступен"
    owner_note = _strip_text(request.owner_note)
    family_kind = _derive_finding_family_kind(turn=assistant_turn)
    decision_reason_code = _extract_finding_reason_code(assistant_turn.decision_meta)
    family_key = _build_finding_family_key(
        client_id=context.client.id,
        branch_id=session_row.branch_id,
        family_kind=family_kind,
        owner_prompt=owner_prompt,
        decision_reason_code=decision_reason_code,
    )
    existing = (
        db.query(ConsoleConsultantVerificationFinding)
        .filter(
            ConsoleConsultantVerificationFinding.client_id == context.client.id,
            ConsoleConsultantVerificationFinding.family_key == family_key,
        )
        .order_by(
            ConsoleConsultantVerificationFinding.last_captured_at.desc(),
            ConsoleConsultantVerificationFinding.updated_at.desc(),
        )
        .first()
    )
    linked_learning_candidate_id = _find_learning_candidate_id_for_prompt(
        db,
        client_id=context.client.id,
        branch_id=session_row.branch_id,
        owner_prompt=owner_prompt,
    )
    knowledge_backlog_id = _upsert_knowledge_backlog_for_finding(
        db,
        client_id=context.client.id,
        owner_prompt=owner_prompt,
        language=_resolve_finding_language(None),
        miss_type=_resolve_finding_miss_type(
            family_kind=family_kind,
            decision_reason_code=decision_reason_code,
        ),
    )

    if isinstance(existing, ConsoleConsultantVerificationFinding):
        same_capture = (
            existing.session_id == session_row.id
            and existing.assistant_turn_id == assistant_turn.id
        )
        if not same_capture:
            existing.repeat_count = int(existing.repeat_count or 1) + 1
            existing.last_captured_at = now
            if existing.status in {"fixed", "retested"}:
                existing.status = "in_review"
        existing.session_id = session_row.id
        existing.owner_turn_id = owner_turn.id if owner_turn else None
        existing.assistant_turn_id = assistant_turn.id
        existing.source_mode = session_row.source_mode
        existing.challenge_mode = session_row.challenge_mode
        existing.family_label = _family_label_for_finding(family_kind)
        existing.owner_prompt = owner_prompt
        existing.assistant_excerpt = assistant_turn.content[:280]
        if owner_note:
            existing.owner_note = owner_note
        existing.outcome = assistant_turn.outcome
        existing.business_verdict = assistant_turn.business_verdict
        existing.decision_reason_code = decision_reason_code
        existing.source_refs = assistant_turn.source_refs
        existing.latest_preview = assistant_turn.preview
        if knowledge_backlog_id:
            existing.linked_knowledge_backlog_id = knowledge_backlog_id
        if linked_learning_candidate_id:
            existing.linked_learning_candidate_id = linked_learning_candidate_id
        existing.updated_at = now
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return _build_finding_record(existing)

    finding = ConsoleConsultantVerificationFinding(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=session_row.branch_id,
        actor_agent_id=context.agent.id,
        actor_role=context.role,
        session_id=session_row.id,
        owner_turn_id=owner_turn.id if owner_turn else None,
        assistant_turn_id=assistant_turn.id,
        source_mode=session_row.source_mode,
        challenge_mode=session_row.challenge_mode,
        family_key=family_key,
        family_kind=family_kind,
        family_label=_family_label_for_finding(family_kind),
        status="new",
        owner_prompt=owner_prompt,
        assistant_excerpt=assistant_turn.content[:280],
        owner_note=owner_note,
        resolution_note=None,
        outcome=assistant_turn.outcome,
        business_verdict=assistant_turn.business_verdict,
        decision_reason_code=decision_reason_code,
        source_refs=assistant_turn.source_refs,
        latest_preview=assistant_turn.preview,
        linked_knowledge_backlog_id=knowledge_backlog_id,
        linked_learning_candidate_id=linked_learning_candidate_id,
        repeat_count=1,
        first_captured_at=now,
        last_captured_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return _build_finding_record(finding)


def update_consultant_verification_finding(
    *,
    db: Session,
    context: ConsoleAuthContext,
    finding_id: UUID,
    request: ConsoleConsultantVerificationFindingUpdateRequest,
    allowed_branch_ids: Optional[list[UUID]],
    now: datetime,
) -> ConsoleConsultantVerificationFindingRecord:
    _require_verification_rollout(context)
    normalized_branch_ids = _normalize_allowed_branch_ids(allowed_branch_ids)
    finding = _get_finding_for_context(
        db=db,
        finding_id=finding_id,
        context=context,
        allowed_branch_ids=normalized_branch_ids,
    )
    next_status = request.status
    if next_status != finding.status:
        allowed = _FINDING_ALLOWED_TRANSITIONS.get(finding.status, set())
        if next_status not in allowed:
            raise ConsoleAPIError(400, "VALIDATION_ERROR", "Invalid finding status transition")
        finding.status = next_status
    resolution_note = _strip_text(request.resolution_note)
    if resolution_note is not None:
        finding.resolution_note = resolution_note
    if not finding.linked_learning_candidate_id:
        finding.linked_learning_candidate_id = _find_learning_candidate_id_for_prompt(
            db,
            client_id=finding.client_id,
            branch_id=finding.branch_id,
            owner_prompt=finding.owner_prompt,
        )
    finding.updated_at = now
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return _build_finding_record(finding)


def get_consultant_verification_readiness(
    *,
    db: Session,
    context: ConsoleAuthContext,
    allowed_branch_ids: Optional[list[UUID]],
) -> ConsoleConsultantVerificationReadinessResponse:
    normalized_branch_ids = _normalize_allowed_branch_ids(allowed_branch_ids)
    branch_id = _resolve_verification_branch_id(
        context=context,
        allowed_branch_ids=normalized_branch_ids,
        required=False,
    )
    if not branch_id:
        return ConsoleConsultantVerificationReadinessResponse(
            readiness=ConsoleConsultantVerificationCompareReadiness(
                status="blocked",
                status_label=_readiness_status_label("blocked"),
                summary="Сначала выберите филиал. Draft и live сравниваются только в рамках одного branch.",
                compare_required=False,
            )
        )
    feature_enabled = resolve_consultant_verification_enabled(context)

    draft_version = _load_latest_draft_version(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    if not isinstance(draft_version, KnowledgeVersion) or not isinstance(draft_version.payload_json, dict):
        return ConsoleConsultantVerificationReadinessResponse(
            readiness=ConsoleConsultantVerificationCompareReadiness(
                status="blocked",
                status_label=_readiness_status_label("blocked"),
                summary="В Knowledge еще нет сохраненного draft. Сначала выполните Validate, затем вернитесь к compare.",
                compare_required=False,
            )
        )

    draft_hash = build_knowledge_draft_hash_from_payload(draft_version.payload_json)
    live_version = _load_active_knowledge_for_branch(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
    )
    if not feature_enabled:
        return ConsoleConsultantVerificationReadinessResponse(
            readiness=ConsoleConsultantVerificationCompareReadiness(
                status="ready",
                status_label="Сравнение пока не требуется",
                summary="Для этого клиента pilot compare еще не включен. Publish опирается на Validate и сохраненный draft.",
                draft_hash=draft_hash,
                compare_required=False,
            )
        )
    if not isinstance(live_version, KnowledgeVersion):
        return ConsoleConsultantVerificationReadinessResponse(
            readiness=ConsoleConsultantVerificationCompareReadiness(
                status="ready",
                status_label="Первый publish — compare не требуется",
                summary="Для этого филиала еще нет опубликованной live версии. Сначала можно сделать первый publish после успешного Validate.",
                draft_hash=draft_hash,
                compare_required=False,
            )
        )
    payload = get_recent_knowledge_compare_preflight(
        db=db,
        client_id=context.client.id,
        branch_id=branch_id,
        draft_hash=draft_hash,
    )
    readiness = _build_readiness_from_compare_payload(payload, compare_required=True)
    if readiness.draft_hash is None:
        readiness.draft_hash = draft_hash
    return ConsoleConsultantVerificationReadinessResponse(readiness=readiness)


async def run_consultant_verification_compare(
    *,
    db: Session,
    context: ConsoleAuthContext,
    request: ConsoleConsultantVerificationCompareRequest,
    allowed_branch_ids: Optional[list[UUID]],
    now: datetime,
) -> ConsoleConsultantVerificationCompareResponse:
    _require_verification_rollout(context)
    normalized_branch_ids = _normalize_allowed_branch_ids(allowed_branch_ids)
    branch_id = _resolve_compare_branch_id(
        context=context,
        allowed_branch_ids=normalized_branch_ids,
    )
    prompt = _strip_text(request.prompt)
    finding: ConsoleConsultantVerificationFinding | None = None
    challenge_mode = "as_client"
    if request.finding_id:
        finding = _get_finding_for_context(
            db=db,
            finding_id=request.finding_id,
            context=context,
            allowed_branch_ids=normalized_branch_ids,
        )
        prompt = finding.owner_prompt
        challenge_mode = finding.challenge_mode
    if not prompt:
        raise ConsoleAPIError(400, "VALIDATION_ERROR", "Compare requires a prompt or finding_id")

    live_truth = _resolve_live_runtime_truth(
        db=db,
        context=context,
        branch_id=branch_id,
    )

    draft_truth, draft_hash = _resolve_compare_draft_truth(
        db=db,
        context=context,
        branch_id=branch_id,
    )
    compare_label = _resolve_compare_case_label(prompt=prompt, finding=finding)

    live_session = _build_compare_session_row(
        context=context,
        branch_id=branch_id,
        source_mode="live",
        challenge_mode=challenge_mode,
        now=now,
        title=f"Compare live: {compare_label}",
    )
    draft_session = _build_compare_session_row(
        context=context,
        branch_id=branch_id,
        source_mode="draft",
        challenge_mode=challenge_mode,
        now=now,
        title=f"Compare draft: {compare_label}",
    )

    live_result = await _run_consultant_verification_simulation(
        db=db,
        session_row=live_session,
        client=context.client,
        previous_turns=[],
        content=prompt,
        now=now,
        runtime_truth_override=live_truth,
    )
    draft_result = await _run_consultant_verification_simulation(
        db=db,
        session_row=draft_session,
        client=context.client,
        previous_turns=[],
        content=prompt,
        now=now,
        runtime_truth_override=draft_truth,
    )

    live_turn = _build_turn_record_from_simulation_payload(
        assistant_payload=_as_json_dict(live_result.get("assistant")),
    )
    draft_turn = _build_turn_record_from_simulation_payload(
        assistant_payload=_as_json_dict(draft_result.get("assistant")),
    )

    retested_finding = False
    preview_case = _build_compare_case_record(
        label=compare_label,
        prompt=prompt,
        finding=finding,
        live_turn=live_turn,
        draft_turn=draft_turn,
        retested_finding=False,
    )

    if isinstance(finding, ConsoleConsultantVerificationFinding) and request.mark_finding_retested:
        if preview_case.delta != "regressed" and draft_turn.business_verdict != "gap_detected":
            finding.status = "retested"
            finding.resolution_note = (
                f"Retested against draft at {now.isoformat()}: {preview_case.summary}"
            )[:500]
            finding.updated_at = now
            db.add(finding)
            retested_finding = True

    case_record = _build_compare_case_record(
        label=compare_label,
        prompt=prompt,
        finding=finding,
        live_turn=live_turn,
        draft_turn=draft_turn,
        retested_finding=retested_finding,
    )
    readiness = _resolve_compare_readiness(
        cases=[case_record],
        draft_hash=draft_hash,
        compared_at=now,
        compare_required=True,
    )

    audit_payload = build_knowledge_compare_payload(
        draft_hash=draft_hash,
        readiness_status=readiness.status,
        improved_total=readiness.improved_total,
        unchanged_total=readiness.unchanged_total,
        regressed_total=readiness.regressed_total,
        manual_review_total=readiness.manual_review_total,
        total_cases=readiness.total_cases,
    )
    audit_payload.update(
        {
            "compared_at": now.isoformat(),
            "prompt": prompt,
            "finding_id": str(finding.id) if isinstance(finding, ConsoleConsultantVerificationFinding) else None,
            "retested_total": readiness.retested_total,
        }
    )
    record_audit_event(
        db,
        actor=context.agent,
        event_type="knowledge_compare_readiness",
        entity_type="branch",
        entity_id=branch_id,
        payload=audit_payload,
        client_id=context.client.id,
        branch_id=branch_id,
        actor_id=context.agent.id,
        actor_name=_strip_text(getattr(context.agent, "name", None)),
    )
    db.commit()

    return ConsoleConsultantVerificationCompareResponse(
        readiness=readiness,
        cases=[case_record],
    )


async def append_consultant_verification_message(
    *,
    db: Session,
    context: ConsoleAuthContext,
    session_id: UUID,
    content: str,
    allowed_branch_ids: Optional[list[UUID]],
    now: datetime,
) -> ConsoleConsultantVerificationSessionResponse:
    _require_verification_rollout(context)
    normalized_content = _strip_text(content)
    if not normalized_content:
        raise ConsoleAPIError(400, "VALIDATION_ERROR", "Message content is required")

    normalized_branch_ids = _normalize_allowed_branch_ids(allowed_branch_ids)
    session_row = _get_session_for_context(
        db=db,
        session_id=session_id,
        context=context,
        allowed_branch_ids=normalized_branch_ids,
    )
    previous_turns = _load_session_turns(db, session_id=session_row.id)
    runtime_truth, source_snapshot = _resolve_verification_session_runtime_truth(
        db=db,
        context=context,
        session_row=session_row,
    )
    simulation_result = await _run_consultant_verification_simulation(
        db=db,
        session_row=session_row,
        client=context.client,
        previous_turns=previous_turns,
        content=normalized_content,
        now=now,
        runtime_truth_override=runtime_truth,
    )

    next_index = int(session_row.turns_total or 0) + 1
    owner_payload = simulation_result["owner"]
    assistant_payload = simulation_result["assistant"]

    owner_turn = ConsoleConsultantVerificationTurn(
        id=uuid4(),
        session_id=session_row.id,
        turn_index=next_index,
        role="owner",
        content=str(owner_payload["content"]),
        message_metadata=_as_json_dict(owner_payload.get("message_metadata")),
        decision_meta={},
        decision_trace=[],
        source_refs=[],
        preview={"simulation_mode": True, "simulation_id": str(session_row.id)},
        outcome=None,
        business_verdict=None,
        created_at=owner_payload.get("created_at") or now,
    )
    assistant_turn = ConsoleConsultantVerificationTurn(
        id=uuid4(),
        session_id=session_row.id,
        turn_index=next_index + 1,
        role=str(assistant_payload["role"]),
        content=str(assistant_payload["content"]),
        message_metadata=_as_json_dict(assistant_payload.get("message_metadata")),
        decision_meta=_as_json_dict(assistant_payload.get("decision_meta")),
        decision_trace=[item for item in assistant_payload.get("decision_trace", []) if isinstance(item, dict)],
        source_refs=[item for item in assistant_payload.get("source_refs", []) if isinstance(item, str)],
        preview=_as_json_dict(assistant_payload.get("preview")),
        outcome=str(assistant_payload.get("outcome") or "fact"),
        business_verdict=str(assistant_payload.get("business_verdict") or "answered"),
        created_at=assistant_payload.get("created_at") or now,
    )

    next_runtime_snapshot = _as_json_dict(simulation_result.get("runtime_snapshot"))
    next_runtime_snapshot.update(source_snapshot)
    next_runtime_snapshot["source_mode"] = session_row.source_mode
    next_runtime_snapshot["challenge_mode"] = session_row.challenge_mode
    session_row.runtime_snapshot = next_runtime_snapshot
    session_row.latest_preview = _as_json_dict(assistant_turn.preview)
    session_row.latest_outcome = assistant_turn.outcome
    session_row.latest_business_verdict = assistant_turn.business_verdict
    session_row.turns_total = next_index + 1
    session_row.updated_at = now
    session_row.last_message_at = assistant_turn.created_at or now

    db.add(owner_turn)
    db.add(assistant_turn)
    db.add(session_row)
    db.commit()
    db.refresh(session_row)
    turns = _load_session_turns(db, session_id=session_row.id)
    return _build_session_response(session_row, turns)
