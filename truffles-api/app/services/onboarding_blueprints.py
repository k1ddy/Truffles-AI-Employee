from __future__ import annotations

from dataclasses import dataclass

from app.schemas.capabilities import CapabilitiesPayload
from app.services.knowledge_validation import get_required_fields_for_domain
from app.services.reference_pack_integrity import build_required_fields_checksum


@dataclass(frozen=True)
class OnboardingBlueprintQuestionTemplate:
    code: str
    question: str
    blocking_go_live: bool


@dataclass(frozen=True)
class OnboardingBlueprintRequiredFieldsProfile:
    fields: tuple[str, ...]
    checksum: str


@dataclass(frozen=True)
class OnboardingBlueprint:
    id: str
    domain_slug: str
    label: str
    summary: str
    payload: CapabilitiesPayload
    go_live_blockers_profile: tuple[str, ...]
    question_templates: tuple[OnboardingBlueprintQuestionTemplate, ...]
    required_fields_profile: OnboardingBlueprintRequiredFieldsProfile
    readiness_weights: tuple[tuple[str, int], ...]


_BLOCKING_QUESTION_CODES = {
    "client_pack.policy.hard_law",
    "client_pack.policy.payment_info",
    "client_pack.policy.reschedule",
    "client_pack.policy.cancel",
    "client_pack.policy.medical",
    "client_pack.policy.legal",
    "client_pack.policy.complaint",
    "client_pack.policy.discounts",
    "client_pack.policy.guard_topics.refund",
    "client_pack.location.city",
    "client_pack.location.address.full",
    "client_pack.operations.hours.days",
    "client_pack.operations.hours.open",
    "client_pack.operations.hours.close",
    "client_pack.communication.languages",
    "client_pack.services_catalog.services",
    "client_pack.price_list",
    "client_pack.service_duration_estimates",
}

_BASE_QUESTION_TEMPLATES = {
    "client_pack.business.name": "Как называется бизнес/филиал для клиентов?",
    "client_pack.location.city": "В каком городе работает филиал?",
    "client_pack.location.address.full": "Какой полный адрес филиала?",
    "client_pack.operations.hours.days": "В какие дни работает филиал?",
    "client_pack.operations.hours.open": "Во сколько филиал открывается?",
    "client_pack.operations.hours.close": "Во сколько филиал закрывается?",
    "client_pack.catalog.summary": "Кратко перечислите основные услуги.",
    "client_pack.communication.languages": "Какие языки общения доступны? Обязательно ru и kk.",
    "client_pack.services_catalog.services": "Дайте список услуг с названиями и ценами.",
    "client_pack.service_duration_estimates": "Укажите длительности услуг.",
    "client_pack.booking.collect_fields": "Какие поля бот обязан собирать для записи?",
    "client_pack.booking.bot_can_confirm": "Бот может подтверждать запись автоматически?",
    "client_pack.guest_policy": "Есть ли ограничения/правила для гостей?",
    "client_pack.safety.medical_note": "Какой медицинский дисклеймер должен говорить бот?",
    "client_pack.pricing.price_from_reason": "Как бот объясняет, почему цена может быть \"от\"?",
    "client_pack.quality.expectations_photo": "Как бот предупреждает про ожидания/референс-фото?",
    "client_pack.price_list": "Нужен прайс-лист в структурированном виде.",
    "client_pack.policy.hard_law": "Укажите обязательные юридические ограничения (hard_law).",
    "client_pack.policy.payment_info": "Опишите правила оплаты.",
    "client_pack.policy.reschedule": "Опишите правила переноса записи.",
    "client_pack.policy.cancel": "Опишите правила отмены записи.",
    "client_pack.policy.medical": "Опишите медицинскую политику.",
    "client_pack.policy.legal": "Опишите юридическую политику.",
    "client_pack.policy.complaint": "Опишите процесс обработки жалоб.",
    "client_pack.policy.discounts": "Опишите политику скидок.",
    "client_pack.policy.guard_topics.refund": "Добавьте ключевые слова/правила по возврату.",
}

_DOMAIN_QUESTION_OVERRIDES = {
    "beauty": {
        "client_pack.catalog.summary": "Кратко перечислите услуги салона (по категориям).",
        "client_pack.quality.expectations_photo": "Как бот объясняет работу с референсами и ожиданиями результата?",
    },
    "clinic": {
        "client_pack.safety.medical_note": "Какой обязательный медицинский дисклеймер должен говорить бот?",
    },
    "legal": {
        "client_pack.catalog.summary": "Какие юридические услуги/направления консультаций доступны?",
        "client_pack.policy.legal": "Опишите юридические ограничения и границы консультаций.",
    },
    "ecom": {
        "client_pack.catalog.summary": "Какие категории товаров/услуг и ключевые офферы доступны?",
        "client_pack.policy.payment_info": "Опишите способы оплаты и подтверждение платежей для клиентов.",
    },
}

_GO_LIVE_BLOCKERS_CORE = (
    "capabilities",
    "onboarding_contract",
    "payment_confirmed",
    "webhook_secret",
    "reference_pack_domain",
    "reference_pack",
    "reference_pack_integrity",
    "instance_id",
    "phone",
    "branch_active",
    "telegram_chat_id",
    "knowledge_tag",
    "knowledge_published",
    "document_ingestion_invalid",
)

_GO_LIVE_BLOCKERS_BOOKING = (
    "working_hours",
    "booking_settings",
    "specialists",
)

_DEFAULT_READINESS_WEIGHTS = (
    ("go_no_go_contract", 60),
    ("delivery_health", 25),
    ("traffic_capability_alignment", 15),
)

_READINESS_WEIGHTS_BY_DOMAIN = {
    "beauty": _DEFAULT_READINESS_WEIGHTS,
    "clinic": (
        ("go_no_go_contract", 65),
        ("delivery_health", 20),
        ("traffic_capability_alignment", 15),
    ),
    "legal": (
        ("go_no_go_contract", 70),
        ("delivery_health", 20),
        ("traffic_capability_alignment", 10),
    ),
    "ecom": (
        ("go_no_go_contract", 55),
        ("delivery_health", 30),
        ("traffic_capability_alignment", 15),
    ),
}


def _normalize_domain_slug(domain_slug: str | None) -> str | None:
    if not isinstance(domain_slug, str):
        return None
    cleaned = domain_slug.strip().lower()
    return cleaned or None


def _build_question_templates(domain_slug: str) -> tuple[OnboardingBlueprintQuestionTemplate, ...]:
    templates = dict(_BASE_QUESTION_TEMPLATES)
    templates.update(_DOMAIN_QUESTION_OVERRIDES.get(domain_slug, {}))
    ordered_codes = sorted(templates)
    return tuple(
        OnboardingBlueprintQuestionTemplate(
            code=code,
            question=templates[code],
            blocking_go_live=code in _BLOCKING_QUESTION_CODES,
        )
        for code in ordered_codes
    )


def _build_required_fields_profile(domain_slug: str) -> OnboardingBlueprintRequiredFieldsProfile:
    required_fields = get_required_fields_for_domain(domain_slug=domain_slug)
    return OnboardingBlueprintRequiredFieldsProfile(
        fields=tuple(required_fields),
        checksum=build_required_fields_checksum(required_fields),
    )


def _build_readiness_weights(domain_slug: str) -> tuple[tuple[str, int], ...]:
    weights = _READINESS_WEIGHTS_BY_DOMAIN.get(domain_slug, _DEFAULT_READINESS_WEIGHTS)
    return tuple(weights)


def _build_blueprints() -> tuple[OnboardingBlueprint, ...]:
    return (
        OnboardingBlueprint(
            id="beauty",
            domain_slug="beauty",
            label="Beauty / Salon",
            summary="WhatsApp+Telegram, запись, knowledge upload",
            payload=CapabilitiesPayload.model_validate(
                {
                    "domain_slug": "beauty",
                    "channels": {
                        "whatsapp": True,
                        "telegram": True,
                        "instagram": None,
                    },
                    "providers": {
                        "availability_provider": "google_calendar",
                        "crm_provider": "amocrm",
                        "calendar_provider": "google_calendar",
                    },
                    "features": {
                        "booking_mode": "confirm_slots",
                        "knowledge_upload": True,
                        "analytics": True,
                        "auto_learn": False,
                    },
                }
            ),
            go_live_blockers_profile=_GO_LIVE_BLOCKERS_CORE + _GO_LIVE_BLOCKERS_BOOKING,
            question_templates=_build_question_templates("beauty"),
            required_fields_profile=_build_required_fields_profile("beauty"),
            readiness_weights=_build_readiness_weights("beauty"),
        ),
        OnboardingBlueprint(
            id="clinic",
            domain_slug="clinic",
            label="Clinic",
            summary="WhatsApp, запись через календарь, строгий ручной контроль",
            payload=CapabilitiesPayload.model_validate(
                {
                    "domain_slug": "clinic",
                    "channels": {
                        "whatsapp": True,
                        "telegram": False,
                        "instagram": None,
                    },
                    "providers": {
                        "availability_provider": "google_calendar",
                        "crm_provider": "custom",
                        "calendar_provider": "google_calendar",
                    },
                    "features": {
                        "booking_mode": "confirm_slots",
                        "knowledge_upload": True,
                        "analytics": True,
                        "auto_learn": False,
                    },
                }
            ),
            go_live_blockers_profile=_GO_LIVE_BLOCKERS_CORE + _GO_LIVE_BLOCKERS_BOOKING,
            question_templates=_build_question_templates("clinic"),
            required_fields_profile=_build_required_fields_profile("clinic"),
            readiness_weights=_build_readiness_weights("clinic"),
        ),
        OnboardingBlueprint(
            id="legal",
            domain_slug="legal",
            label="Legal",
            summary="Консультационный режим без слот-подтверждения",
            payload=CapabilitiesPayload.model_validate(
                {
                    "domain_slug": "legal",
                    "channels": {
                        "whatsapp": True,
                        "telegram": True,
                        "instagram": False,
                    },
                    "providers": {
                        "availability_provider": "manual",
                        "crm_provider": "none",
                        "calendar_provider": "local",
                    },
                    "features": {
                        "booking_mode": "collect_preferences",
                        "knowledge_upload": True,
                        "analytics": True,
                        "auto_learn": False,
                    },
                }
            ),
            go_live_blockers_profile=_GO_LIVE_BLOCKERS_CORE,
            question_templates=_build_question_templates("legal"),
            required_fields_profile=_build_required_fields_profile("legal"),
            readiness_weights=_build_readiness_weights("legal"),
        ),
        OnboardingBlueprint(
            id="ecom",
            domain_slug="ecom",
            label="E-commerce",
            summary="Мультиканал и аналитика, без confirm-slots по умолчанию",
            payload=CapabilitiesPayload.model_validate(
                {
                    "domain_slug": "ecom",
                    "channels": {
                        "whatsapp": True,
                        "telegram": True,
                        "instagram": True,
                    },
                    "providers": {
                        "availability_provider": "none",
                        "crm_provider": "bitrix",
                        "calendar_provider": "none",
                    },
                    "features": {
                        "booking_mode": "collect_preferences",
                        "knowledge_upload": True,
                        "analytics": True,
                        "auto_learn": True,
                    },
                }
            ),
            go_live_blockers_profile=_GO_LIVE_BLOCKERS_CORE,
            question_templates=_build_question_templates("ecom"),
            required_fields_profile=_build_required_fields_profile("ecom"),
            readiness_weights=_build_readiness_weights("ecom"),
        ),
    )


_ONBOARDING_BLUEPRINTS = _build_blueprints()


def list_onboarding_blueprints() -> list[OnboardingBlueprint]:
    return list(_ONBOARDING_BLUEPRINTS)


def get_onboarding_blueprint(domain_slug: str | None) -> OnboardingBlueprint | None:
    normalized = _normalize_domain_slug(domain_slug)
    if not normalized:
        return None
    for blueprint in _ONBOARDING_BLUEPRINTS:
        if blueprint.domain_slug == normalized:
            return blueprint
    return None


def get_onboarding_question_templates(domain_slug: str | None) -> dict[str, str]:
    blueprint = get_onboarding_blueprint(domain_slug)
    if blueprint is None:
        return dict(_BASE_QUESTION_TEMPLATES)
    return {
        item.code: item.question
        for item in blueprint.question_templates
    }
