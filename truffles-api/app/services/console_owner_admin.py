"""Owner/Admin business helpers extracted from console router."""

from __future__ import annotations

from datetime import date as dt_date
from typing import Literal, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.console import ConsoleBusinessActionItem
from app.services.console_auth import ConsoleAuthContext
from app.services.provider_error_policy import incident_reason_from_provider_error


def _parse_positive_int(value: object) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def _first_non_empty_string(values: list[object]) -> Optional[str]:
    for value in values:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized
    return None


def resolve_subscription_contract_info(context: ConsoleAuthContext) -> tuple[
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[int],
    str,
]:
    company = next(
        (item for item in context.companies if item.id == context.client.company_id),
        None,
    )
    company_billing = company.billing_info if company and isinstance(company.billing_info, dict) else {}
    client_config = context.client.config if isinstance(context.client.config, dict) else {}
    client_billing = client_config.get("billing") if isinstance(client_config.get("billing"), dict) else {}
    sources: list[tuple[str, dict]] = [
        ("company_billing_info", company_billing),
        ("client_config", client_billing),
    ]

    plan_name = _first_non_empty_string(
        [
            company_billing.get("plan_name") if isinstance(company_billing, dict) else None,
            company_billing.get("plan") if isinstance(company_billing, dict) else None,
            client_billing.get("plan_name") if isinstance(client_billing, dict) else None,
            client_billing.get("plan") if isinstance(client_billing, dict) else None,
            company_billing.get("tariff") if isinstance(company_billing, dict) else None,
            client_billing.get("tariff") if isinstance(client_billing, dict) else None,
        ]
    )
    contract_label = _first_non_empty_string(
        [
            company_billing.get("contract") if isinstance(company_billing, dict) else None,
            company_billing.get("contract_label") if isinstance(company_billing, dict) else None,
            client_billing.get("contract") if isinstance(client_billing, dict) else None,
            client_billing.get("contract_label") if isinstance(client_billing, dict) else None,
        ]
    )
    currency = _first_non_empty_string(
        [
            company_billing.get("currency") if isinstance(company_billing, dict) else None,
            client_billing.get("currency") if isinstance(client_billing, dict) else None,
        ]
    )
    if currency:
        currency = currency.upper()

    quota_keys = ("monthly_quota", "message_quota", "included_messages", "messages_quota", "quota")
    for source_name, source_payload in sources:
        if not isinstance(source_payload, dict):
            continue
        nested_subscription = source_payload.get("subscription")
        candidate_maps = [source_payload]
        if isinstance(nested_subscription, dict):
            candidate_maps.insert(0, nested_subscription)
        for payload in candidate_maps:
            for key in quota_keys:
                parsed_quota = _parse_positive_int(payload.get(key))
                if parsed_quota is not None:
                    return plan_name, contract_label, currency, parsed_quota, source_name

    return plan_name, contract_label, currency, None, "unknown"


def resolve_subscription_alert(
    *,
    monthly_quota: Optional[int],
    usage_percent: Optional[float],
    over_quota: bool,
    projected_over_quota: bool,
) -> tuple[str, str]:
    if monthly_quota is None or monthly_quota <= 0:
        return (
            "normal",
            "Лимит не задан: контролируйте биллинговые сообщения через таблицу доказательств.",
        )
    if over_quota or (usage_percent is not None and usage_percent >= 100):
        return (
            "limit_100",
            "Лимит уже превышен: каждый следующий billable ответ увеличивает overage.",
        )
    if (usage_percent is not None and usage_percent >= 80) or projected_over_quota:
        return (
            "warning_80",
            "Риск перерасхода: проверьте нагрузку и тариф до даты следующего списания.",
        )
    return (
        "normal",
        "Лимит в безопасной зоне.",
    )


def derive_business_status(
    *,
    outbox_backlog: int,
    outbox_failed_24h: int,
    unresolved_cases: int,
) -> tuple[str, str]:
    if outbox_backlog >= 1000 or outbox_failed_24h >= 100:
        return "unhealthy", "Критичный риск: сообщения клиентов могут приходить с задержкой."
    if outbox_backlog >= 500 or outbox_failed_24h >= 30 or unresolved_cases >= 20:
        return "degraded", "Есть риск деградации: требуется контроль очереди и скорости ответа."
    return "healthy", "Система работает стабильно, критичных рисков не выявлено."


def build_owner_actions(
    *,
    outbox_backlog: int,
    outbox_failed_24h: int,
    unresolved_cases: int,
    first_response_p90_seconds: Optional[float],
) -> list[ConsoleBusinessActionItem]:
    actions: list[ConsoleBusinessActionItem] = []
    if outbox_backlog >= 500 or outbox_failed_24h >= 30:
        actions.append(
            ConsoleBusinessActionItem(
                id="review_ops_health",
                severity="critical" if outbox_backlog >= 1000 or outbox_failed_24h >= 100 else "warn",
                title="Проверьте очередь отправки",
                description="Откройте Статус и убедитесь, что failed/pending не растут.",
                href="/ops",
            )
        )
    if unresolved_cases > 0:
        actions.append(
            ConsoleBusinessActionItem(
                id="review_unresolved_cases",
                severity="warn",
                title="Проверьте неразобранные заявки",
                description="Есть диалоги без завершения. Проверьте очередь заявок и назначение менеджеров.",
                href="/",
            )
        )
    if first_response_p90_seconds is not None and first_response_p90_seconds > 900:
        actions.append(
            ConsoleBusinessActionItem(
                id="review_team_speed",
                severity="warn",
                title="Проверьте скорость ответа менеджеров",
                description="Время первого ответа превышает целевой диапазон, есть риск потери заявок.",
                href="/insights",
            )
        )
    if not actions:
        actions.append(
            ConsoleBusinessActionItem(
                id="monitor_daily",
                severity="info",
                title="Контроль в норме",
                description="Проверяйте ежедневные показатели и обновляйте базовые настройки по расписанию.",
                href="/insights",
            )
        )
    return actions


def safe_int(value: object) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_float(value: object) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_latest_analytics_row(
    *,
    db: Session,
    client_id: UUID,
    metric_date: dt_date,
    analytics_scope_limited: bool,
):
    if analytics_scope_limited:
        return None
    return db.execute(
        text(
            """
            SELECT
              metric_date,
              first_response_missing_total,
              escalation_meta_missing_total,
              intent_missing_total,
              first_response_p90_seconds,
              manager_median_response_seconds
            FROM metrics_analytics_daily
            WHERE client_id = :client_id
              AND metric_date <= :metric_date
            ORDER BY metric_date DESC
            LIMIT 1
            """
        ),
        {"client_id": client_id, "metric_date": metric_date},
    ).mappings().first()


def derive_data_trust_status(
    *,
    first_response_missing_total: Optional[int],
    escalation_meta_missing_total: Optional[int],
    intent_missing_total: Optional[int],
    knowledge_stale_hours: Optional[int],
    critical_audit_events_24h: int,
    analytics_scope_limited: bool,
) -> tuple[str, str]:
    missing_total = sum(
        value
        for value in (
            first_response_missing_total,
            escalation_meta_missing_total,
            intent_missing_total,
        )
        if value is not None and value > 0
    )
    if (
        critical_audit_events_24h >= 5
        or (knowledge_stale_hours is not None and knowledge_stale_hours >= 168)
        or missing_total >= 50
    ):
        return "unhealthy", "Высокий риск: качество данных и трассировок может быть недостоверным."
    if (
        analytics_scope_limited
        or critical_audit_events_24h >= 1
        or (knowledge_stale_hours is not None and knowledge_stale_hours >= 72)
        or missing_total >= 10
    ):
        return "degraded", "Есть риск по качеству данных: требуется проверка метрик, знаний и аудита."
    return "healthy", "Качество данных стабильное, критичных разрывов не обнаружено."


def build_data_trust_actions(
    *,
    first_response_missing_total: Optional[int],
    escalation_meta_missing_total: Optional[int],
    intent_missing_total: Optional[int],
    knowledge_stale_hours: Optional[int],
    critical_audit_events_24h: int,
    analytics_scope_limited: bool,
) -> list[ConsoleBusinessActionItem]:
    actions: list[ConsoleBusinessActionItem] = []
    missing_total = sum(
        value
        for value in (
            first_response_missing_total,
            escalation_meta_missing_total,
            intent_missing_total,
        )
        if value is not None and value > 0
    )
    if analytics_scope_limited:
        actions.append(
            ConsoleBusinessActionItem(
                id="review_scope_for_analytics",
                severity="warn",
                title="Проверьте полноту скоупа метрик",
                description="Для branch-режима часть quality-метрик недоступна. Проверьте company scope перед решением.",
                href="/business",
            )
        )
    if knowledge_stale_hours is not None and knowledge_stale_hours >= 72:
        actions.append(
            ConsoleBusinessActionItem(
                id="refresh_knowledge",
                severity="warn" if knowledge_stale_hours < 168 else "critical",
                title="Обновите базу знаний",
                description="Публикация знаний устарела, есть риск устаревших ответов клиентам.",
                href="/knowledge",
            )
        )
    if critical_audit_events_24h > 0:
        actions.append(
            ConsoleBusinessActionItem(
                id="review_audit_incidents",
                severity="critical" if critical_audit_events_24h >= 5 else "warn",
                title="Проверьте критичные события аудита",
                description="За 24 часа зафиксированы failed/blocked/rejected события.",
                href="/audit",
            )
        )
    if missing_total >= 10:
        actions.append(
            ConsoleBusinessActionItem(
                id="fix_missing_quality_metrics",
                severity="warn" if missing_total < 50 else "critical",
                title="Снизьте пробелы quality-метрик",
                description="Есть неполные записи по first-response/escalation/intent, это снижает доверие к аналитике.",
                href="/insights",
            )
        )
    if not actions:
        actions.append(
            ConsoleBusinessActionItem(
                id="monitor_data_trust",
                severity="info",
                title="Контроль качества данных в норме",
                description="Сохраняйте регулярный аудит и плановую публикацию знаний.",
                href="/audit",
            )
        )
    return actions


def derive_team_performance_status(
    *,
    unresolved_cases: int,
    unresolved_older_than_60m: int,
    manager_median_response_seconds: Optional[float],
) -> tuple[str, str]:
    if (
        unresolved_older_than_60m >= 20
        or unresolved_cases >= 40
        or (manager_median_response_seconds is not None and manager_median_response_seconds > 900)
    ):
        return "unhealthy", "Высокий риск: команда не успевает обрабатывать поток обращений."
    if (
        unresolved_older_than_60m >= 5
        or unresolved_cases >= 15
        or (manager_median_response_seconds is not None and manager_median_response_seconds > 600)
    ):
        return "degraded", "Есть перегрузка команды: контролируйте SLA и распределение заявок."
    return "healthy", "Команда держит стабильную скорость и нагрузку в целевом диапазоне."


def build_team_performance_actions(
    *,
    unresolved_older_than_60m: int,
    manager_median_response_seconds: Optional[float],
    top_manager_name: Optional[str],
    top_manager_unresolved: int,
    analytics_scope_limited: bool,
) -> list[ConsoleBusinessActionItem]:
    actions: list[ConsoleBusinessActionItem] = []
    if unresolved_older_than_60m > 0:
        actions.append(
            ConsoleBusinessActionItem(
                id="clear_stale_cases",
                severity="critical" if unresolved_older_than_60m >= 20 else "warn",
                title="Разберите просроченные заявки",
                description="Есть открытые заявки старше 60 минут. Проверьте очереди и назначение менеджеров.",
                href="/",
            )
        )
    if manager_median_response_seconds is not None and manager_median_response_seconds > 900:
        actions.append(
            ConsoleBusinessActionItem(
                id="improve_manager_speed",
                severity="warn",
                title="Ускорьте первый ответ менеджеров",
                description="Медиана ответа менеджеров превышает целевой порог, есть риск потери обращений.",
                href="/team",
            )
        )
    if top_manager_unresolved >= 8 and top_manager_name:
        actions.append(
            ConsoleBusinessActionItem(
                id="rebalance_manager_load",
                severity="warn",
                title="Перераспределите нагрузку в команде",
                description=f"У менеджера «{top_manager_name}» высокий объём открытых заявок.",
                href="/team",
            )
        )
    if analytics_scope_limited:
        actions.append(
            ConsoleBusinessActionItem(
                id="confirm_company_scope_kpi",
                severity="info",
                title="Подтвердите KPI в company scope",
                description="Часть аналитики недоступна в branch-режиме. Для финальных решений проверьте полный scope.",
                href="/business",
            )
        )
    if not actions:
        actions.append(
            ConsoleBusinessActionItem(
                id="monitor_team_daily",
                severity="info",
                title="Команда работает стабильно",
                description="Поддерживайте ежедневный контроль SLA и балансировки очереди.",
                href="/insights",
            )
        )
    return actions


def classify_outbox_incident_reason(
    *,
    last_error: Optional[str],
    integration_degraded: bool,
) -> tuple[
    Literal[
        "outbox_backlog",
        "provider_billing_blocked",
        "provider_invalid_recipient",
        "provider_unavailable",
        "provider_auth",
        "provider_rate_limited",
        "integration_degraded",
        "unknown",
    ],
    str,
]:
    if integration_degraded:
        return "integration_degraded", "Требуется восстановление интеграции"

    normalized = (last_error or "").strip().lower()
    if not normalized:
        return "outbox_backlog", "Очередь сообщений растёт"

    return incident_reason_from_provider_error(last_error)
