"""Provider delivery errors policy (rules-as-data).

Single source of truth for:
- error text/code classification,
- retryability,
- incident reason mapping for Console.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

ProviderErrorKind = Literal[
    "billing_blocked",
    "transport_guard",
    "invalid_recipient",
    "auth",
    "rate_limited",
    "unavailable",
    "unknown",
]
ProviderIncidentReasonCode = Literal[
    "provider_billing_blocked",
    "provider_transport_guard",
    "provider_invalid_recipient",
    "provider_auth",
    "provider_rate_limited",
    "provider_unavailable",
    "unknown",
]


@dataclass(frozen=True)
class ProviderErrorRule:
    kind: ProviderErrorKind
    incident_reason_code: ProviderIncidentReasonCode
    incident_reason_label: str
    retryable: bool
    markers: tuple[str, ...] = ()
    error_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProviderErrorClassification:
    kind: ProviderErrorKind
    incident_reason_code: ProviderIncidentReasonCode
    incident_reason_label: str
    retryable: bool
    error_code: Optional[str] = None


_ERROR_CODE_PATTERN = re.compile(r"\[([A-Z0-9_]+)\]")

_PROVIDER_ERROR_RULES: tuple[ProviderErrorRule, ...] = (
    ProviderErrorRule(
        kind="billing_blocked",
        incident_reason_code="provider_billing_blocked",
        incident_reason_label="Подписка провайдера заблокирована",
        retryable=False,
        error_codes=("CHATFLOW_BILLING_BLOCKED",),
        markers=(
            "billing_blocked",
            "plan has been expired",
            "subscription expired",
            "please renew",
            "plan renewal required",
            "not paid",
            "payment required",
            "invoice overdue",
        ),
    ),
    ProviderErrorRule(
        kind="transport_guard",
        incident_reason_code="provider_transport_guard",
        incident_reason_label="Исходящая отправка заблокирована runtime transport guard",
        retryable=False,
        markers=(
            "transport mode guard",
            "transport_allowlist_guard",
            "outbound blocked by transport",
            "blocked by transport mode",
        ),
    ),
    ProviderErrorRule(
        kind="invalid_recipient",
        incident_reason_code="provider_invalid_recipient",
        incident_reason_label="Некорректный номер WhatsApp получателя",
        retryable=False,
        error_codes=("CHATFLOW_INVALID_RECIPIENT",),
        markers=(
            "invalid recipient",
            "invalid jid",
            "jid not found",
            "recipient not found",
            "number does not exist",
            "not a whatsapp user",
            "phone number shared via url is invalid",
        ),
    ),
    ProviderErrorRule(
        kind="auth",
        incident_reason_code="provider_auth",
        incident_reason_label="Ошибка авторизации у провайдера",
        retryable=True,
        markers=(
            "unauthorized",
            "forbidden",
            "invalid token",
            "expired token",
            "401",
            "403",
        ),
    ),
    ProviderErrorRule(
        kind="rate_limited",
        incident_reason_code="provider_rate_limited",
        incident_reason_label="Провайдер ограничил частоту отправки",
        retryable=True,
        markers=(
            "rate limit",
            "too many requests",
            "throttle",
            "429",
        ),
    ),
    ProviderErrorRule(
        kind="unavailable",
        incident_reason_code="provider_unavailable",
        incident_reason_label="Провайдер временно недоступен",
        retryable=True,
        markers=(
            "timeout",
            "timed out",
            "connection",
            "unreachable",
            "bad gateway",
            "service unavailable",
            "gateway timeout",
            "502",
            "503",
            "gateway",
        ),
    ),
)
_RULE_BY_KIND = {rule.kind: rule for rule in _PROVIDER_ERROR_RULES}


def extract_provider_error_code(error_text: Optional[str]) -> Optional[str]:
    if not error_text:
        return None
    match = _ERROR_CODE_PATTERN.search(error_text)
    if not match:
        return None
    return match.group(1)


def classify_provider_error(
    error_text: Optional[str],
    *,
    explicit_error_code: Optional[str] = None,
) -> ProviderErrorClassification:
    normalized_text = (error_text or "").strip().lower()
    normalized_code = (explicit_error_code or "").strip().upper() or extract_provider_error_code(error_text)

    if normalized_code:
        for rule in _PROVIDER_ERROR_RULES:
            if normalized_code in rule.error_codes:
                return ProviderErrorClassification(
                    kind=rule.kind,
                    incident_reason_code=rule.incident_reason_code,
                    incident_reason_label=rule.incident_reason_label,
                    retryable=rule.retryable,
                    error_code=normalized_code,
                )

    if normalized_text:
        for rule in _PROVIDER_ERROR_RULES:
            if any(marker in normalized_text for marker in rule.markers):
                return ProviderErrorClassification(
                    kind=rule.kind,
                    incident_reason_code=rule.incident_reason_code,
                    incident_reason_label=rule.incident_reason_label,
                    retryable=rule.retryable,
                    error_code=normalized_code,
                )

    return ProviderErrorClassification(
        kind="unknown",
        incident_reason_code="unknown",
        incident_reason_label="Требуется ручная диагностика причины",
        retryable=True,
        error_code=normalized_code,
    )


def incident_reason_from_provider_error(
    error_text: Optional[str],
    *,
    explicit_error_code: Optional[str] = None,
) -> tuple[ProviderIncidentReasonCode, str]:
    classification = classify_provider_error(error_text, explicit_error_code=explicit_error_code)
    return classification.incident_reason_code, classification.incident_reason_label


def provider_error_retryable(kind: str) -> bool:
    rule = _RULE_BY_KIND.get(kind)
    if rule is None:
        return True
    return rule.retryable


def is_permanent_provider_error(
    error_text: Optional[str],
    *,
    explicit_error_code: Optional[str] = None,
) -> bool:
    classification = classify_provider_error(error_text, explicit_error_code=explicit_error_code)
    return classification.kind != "unknown" and not classification.retryable
