/**
 * Shared label utility functions for Truffles Console
 * Eliminates duplication across CaseList, CaseView, OpsPage, calendar
 */

// Status labels for cases
export function getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
        pending: "Ожидает",
        active: "В работе",
        resolved: "Закрыт",
        bot_handling: "Бот отвечает",
        escalated: "Эскалация",
    };
    return labels[status] || status;
}

type CaseBusinessStatusCode =
    | "unassigned"
    | "open"
    | "in_progress"
    | "needs_reply"
    | "waiting_client"
    | "snoozed"
    | "bot_handling"
    | "resolved"
    | string;

type CaseBusinessStatusLike = {
    status?: string;
    business_status_code?: string | null;
    business_status_label?: string | null;
    assigned_to_id?: string | null;
    assigned_to_name?: string | null;
    sla_action_state?: string | null;
    snoozed_until?: string | null;
};

export interface CaseBusinessStatusBadge {
    label: string;
    className: string;
    code: string;
}

export function getCaseBusinessStatusBadge(caseItem: CaseBusinessStatusLike): CaseBusinessStatusBadge {
    const code = (
        caseItem.business_status_code
        || deriveFallbackBusinessStatus(caseItem)
    ) as CaseBusinessStatusCode;
    const label = caseItem.business_status_label || getFallbackBusinessStatusLabel(code, caseItem.status || "");

    return {
        code,
        label,
        className: getCaseBusinessStatusClassName(code),
    };
}

type CaseSlaState =
    | "reply_due"
    | "overdue"
    | "snoozed"
    | "waiting_client"
    | "delivery_issue"
    | "pending_outbox"
    | "resolved"
    | string;

type CaseSlaLike = {
    created_at?: string;
    status?: string;
    sla_status?: string | null;
    sla_action_state?: string | null;
    sla_overdue_minutes?: number | null;
    target_response_at?: string | null;
    needs_reply?: boolean | null;
    has_delivery_error?: boolean | null;
    has_pending_outbox?: boolean | null;
    human_lock_active?: boolean | null;
    last_inbound_at?: string | null;
    last_outbound_at?: string | null;
    snoozed_until?: string | null;
};

type SyncStatusLike = {
    status?: string | null;
    detail?: string | null;
    operator_message?: string | null;
};

type CaseActionSyncLike = {
    telegram?: SyncStatusLike | null;
    client_notify?: SyncStatusLike | null;
};

// SLA status labels
export function getSlaLabel(status?: string): string {
    const labels: Record<string, string> = {
        ok: "В рабочем окне",
        warning: "Нужен ответ менеджера",
        breached: "Срок ответа нарушен",
    };
    return labels[status || ""] || status || "";
}

// System status labels (for OpsPage health checks)
export function getSystemStatusLabel(status: string): string {
    const labels: Record<string, string> = {
        ok: "норма",
        connected: "подключено",
        degraded: "ухудшено",
        error: "ошибка",
        unknown: "неизвестно",
    };
    return labels[status] || status;
}

export function getChannelLabel(channel?: string | null): string {
    if (!channel) {
        return "—";
    }
    const normalized = channel.toLowerCase();
    const labels: Record<string, string> = {
        whatsapp: "WhatsApp",
        telegram: "Telegram",
        instagram: "Instagram",
        web: "Web",
        sms: "SMS",
        email: "Email",
    };
    return labels[normalized] ?? channel;
}

export function getTriggerLabel(trigger?: string | null): string {
    if (!trigger) {
        return "—";
    }
    const normalized = trigger.toLowerCase();
    const labels: Record<string, string> = {
        inbound_message: "Входящее сообщение",
        message: "Входящее сообщение",
        handover: "Передача менеджеру",
        escalation: "Эскалация",
        policy_gate: "Policy-гейт",
        reminder: "Напоминание",
        manual: "Ручной запуск",
    };
    return labels[normalized] ?? trigger;
}

type CaseOriginLike = {
    trigger_type?: string | null;
    trigger_value?: string | null;
    context_summary?: string | null;
    user_message?: string | null;
};

export interface CaseOriginSummary {
    title: string;
    detail: string | null;
}

type CaseBookingSummaryLike = {
    status?: string | null;
    start_at?: string | null;
    specialist_name?: string | null;
    service_type?: string | null;
    needs_action?: boolean | null;
    attention_reason?: string | null;
    no_show_followup_done?: boolean | null;
    no_show_followup_result?: string | null;
    operator_summary?: string | null;
};

export interface CaseBookingSemanticSummary {
    label: string;
    className: string;
    operatorSummary: string;
    meta: string | null;
    needsAttention: boolean;
}

function getSyncFallbackMessage(target: "telegram" | "client_notify"): string {
    if (target === "telegram") {
        return "Не удалось синхронизировать состояние заявки с Telegram.";
    }
    return "Не удалось отправить системное уведомление клиенту.";
}

function getSyncFollowupMessage(
    target: "telegram" | "client_notify",
    sync?: SyncStatusLike | null,
): string | null {
    if (sync?.status !== "failed") {
        return null;
    }
    return sync.operator_message || getSyncFallbackMessage(target);
}

export function collectCaseActionFollowupMessages(sync?: CaseActionSyncLike | null): string[] {
    const messages: string[] = [];
    const telegramMessage = getSyncFollowupMessage("telegram", sync?.telegram);
    if (telegramMessage) {
        messages.push(telegramMessage);
    }
    const clientNotifyMessage = getSyncFollowupMessage("client_notify", sync?.client_notify);
    if (clientNotifyMessage) {
        messages.push(clientNotifyMessage);
    }
    return messages;
}

export function getCaseOriginSummary(caseItem: CaseOriginLike): CaseOriginSummary {
    const trigger = (caseItem.trigger_type || "").toLowerCase();
    const detail = caseItem.context_summary || caseItem.trigger_value || caseItem.user_message || null;

    if (trigger === "handover" || trigger === "escalation") {
        return {
            title: "Бот передал диалог менеджеру",
            detail,
        };
    }
    if (trigger === "policy_gate") {
        return {
            title: "Бот остановился на policy-проверке",
            detail,
        };
    }
    if (trigger === "reminder") {
        return {
            title: "Система вернула заявку в работу",
            detail,
        };
    }
    if (trigger === "manual") {
        return {
            title: "Заявка создана вручную",
            detail,
        };
    }
    if (trigger === "message" || trigger === "inbound_message") {
        return {
            title: "Клиент написал, и заявка ушла менеджеру",
            detail,
        };
    }

    return {
        title: `Повод: ${getTriggerLabel(caseItem.trigger_type)}`,
        detail,
    };
}

function formatBookingMeta(summary: CaseBookingSummaryLike): string | null {
    const parts: string[] = [];
    if (summary.start_at) {
        parts.push(
            new Date(summary.start_at).toLocaleString("ru-RU", {
                day: "2-digit",
                month: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
            }),
        );
    }
    if (summary.specialist_name) {
        parts.push(summary.specialist_name);
    }
    if (summary.service_type) {
        parts.push(summary.service_type);
    }
    return parts.length > 0 ? parts.join(" · ") : null;
}

function buildBookingOperatorSummary(summary: CaseBookingSummaryLike): string {
    const normalized = (summary.status || "").toUpperCase();
    const meta = formatBookingMeta(summary);
    const slot = meta ? ` ${meta}` : "";
    if (summary.operator_summary?.trim()) {
        return summary.operator_summary.trim();
    }
    if (normalized === "PENDING_CONFIRMATION") {
        return `По заявке создан визит${slot} — нужно подтвердить запись.`;
    }
    if (normalized === "RESCHEDULE_REQUESTED") {
        return `Клиент просит перенос записи${slot}.`;
    }
    if (normalized === "HOLD") {
        return `Запись${slot} удерживается до решения менеджера.`;
    }
    if (normalized === "NO_SHOW" && summary.no_show_followup_done) {
        return summary.no_show_followup_result === "rebooked"
            ? "После неявки клиента уже перезаписали."
            : "После неявки с клиентом уже связались.";
    }
    if (normalized === "NO_SHOW") {
        return `Клиент не пришел на визит${slot} — ${summary.attention_reason || "нужен follow-up"}.`;
    }
    if (normalized === "COMPLETED") {
        return `Визит по заявке завершен${slot ? `: ${meta}` : ""}.`;
    }
    if (normalized === "CANCELLED") {
        return `Запись по заявке отменена${slot ? `: ${meta}` : ""}.`;
    }
    return `По заявке есть запись${slot}.`;
}

export function getCaseBookingSemanticSummary(
    summary?: CaseBookingSummaryLike | null,
): CaseBookingSemanticSummary | null {
    if (!summary?.status) {
        return null;
    }
    const needsAttention = Boolean(summary.needs_action);
    return {
        label: getBookingStatusLabel(summary.status),
        className: getBookingStatusColor(summary.status),
        operatorSummary: buildBookingOperatorSummary(summary),
        meta: formatBookingMeta(summary),
        needsAttention,
    };
}

// SLA indicator with color styling based on elapsed time
export interface SlaIndicator {
    label: string;
    className: string;
    minutes: number;
    state?: string;
}

export interface SlaCountdown {
    label: string;
    className: string;
}

const SLA_WARNING_MINUTES = 60;
const SLA_BREACHED_MINUTES = 120;

function formatTimeLabel(value?: string | null): string {
    if (!value) {
        return "—";
    }
    return new Date(value).toLocaleTimeString("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatMinutesLabel(totalMinutes?: number | null): string {
    if (!totalMinutes || totalMinutes <= 0) {
        return "1 мин";
    }
    if (totalMinutes < 60) {
        return `${totalMinutes} мин`;
    }
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    if (minutes === 0) {
        return `${hours} ч`;
    }
    return `${hours} ч ${minutes} мин`;
}

function deriveFallbackBusinessStatus(caseItem: CaseBusinessStatusLike): CaseBusinessStatusCode {
    const actionState = (caseItem.sla_action_state || "").toLowerCase();
    const hasOwner = Boolean(caseItem.assigned_to_id || caseItem.assigned_to_name);
    if (caseItem.status === "resolved") {
        return "resolved";
    }
    if (caseItem.status === "bot_handling") {
        return "bot_handling";
    }
    if (actionState === "snoozed" || caseItem.snoozed_until) {
        return "snoozed";
    }
    if (!hasOwner) {
        return "unassigned";
    }
    if (actionState === "reply_due" || actionState === "overdue") {
        return "needs_reply";
    }
    if (actionState === "waiting_client") {
        return "waiting_client";
    }
    if (caseItem.status === "active") {
        return "in_progress";
    }
    return "open";
}

function getFallbackBusinessStatusLabel(code: CaseBusinessStatusCode, rawStatus: string): string {
    switch (code) {
        case "unassigned":
            return "Без владельца";
        case "open":
            return "Открыта";
        case "in_progress":
            return "В работе";
        case "needs_reply":
            return "Нужен ответ";
        case "waiting_client":
            return "Ждем клиента";
        case "snoozed":
            return "Отложена";
        case "bot_handling":
            return "Бот ведет";
        case "resolved":
            return "Закрыта";
        default:
            return getStatusLabel(rawStatus);
    }
}

function getCaseBusinessStatusClassName(code: CaseBusinessStatusCode): string {
    switch (code) {
        case "unassigned":
            return "bg-amber-100 text-amber-900";
        case "open":
            return "bg-yellow-100 text-yellow-800";
        case "in_progress":
            return "bg-green-100 text-green-800";
        case "needs_reply":
            return "bg-orange-100 text-orange-900";
        case "waiting_client":
            return "bg-blue-100 text-blue-800";
        case "snoozed":
            return "bg-slate-100 text-slate-700";
        case "bot_handling":
            return "bg-teal-100 text-teal-800";
        case "resolved":
            return "bg-muted text-muted-foreground";
        default:
            return "bg-muted text-muted-foreground";
    }
}

function getCaseSlaClassName(state?: CaseSlaState | null): string {
    if (state === "delivery_issue" || state === "overdue") {
        return "bg-red-100 text-red-800";
    }
    if (state === "pending_outbox" || state === "reply_due") {
        return "bg-yellow-100 text-yellow-800";
    }
    if (state === "waiting_client") {
        return "bg-blue-100 text-blue-800";
    }
    if (state === "snoozed") {
        return "bg-slate-200 text-slate-800";
    }
    if (state === "resolved") {
        return "bg-muted text-muted-foreground";
    }
    return "bg-green-100 text-green-800";
}

export function getCaseSlaIndicator(caseItem: CaseSlaLike): SlaIndicator {
    const state = (caseItem.sla_action_state || "").toLowerCase();
    if (state === "delivery_issue") {
        return {
            label: "Проверьте отправку",
            className: getCaseSlaClassName(state),
            minutes: 0,
            state,
        };
    }
    if (state === "pending_outbox") {
        return {
            label: "Проверьте очередь",
            className: getCaseSlaClassName(state),
            minutes: 0,
            state,
        };
    }
    if (state === "overdue") {
        const overdueMinutes = Math.max(1, caseItem.sla_overdue_minutes ?? 0);
        return {
            label: `Просрочено на ${formatMinutesLabel(overdueMinutes)}`,
            className: getCaseSlaClassName(state),
            minutes: overdueMinutes,
            state,
        };
    }
    if (state === "reply_due") {
        return {
            label: `Ответить до ${formatTimeLabel(caseItem.target_response_at)}`,
            className: getCaseSlaClassName(state),
            minutes: 0,
            state,
        };
    }
    if (state === "waiting_client") {
        return {
            label: "Ожидаем клиента",
            className: getCaseSlaClassName(state),
            minutes: 0,
            state,
        };
    }
    if (state === "snoozed") {
        return {
            label: `Отложено до ${formatTimeLabel(caseItem.snoozed_until)}`,
            className: getCaseSlaClassName(state),
            minutes: 0,
            state,
        };
    }
    if (state === "resolved" || caseItem.status === "resolved") {
        return {
            label: "Заявка закрыта",
            className: getCaseSlaClassName("resolved"),
            minutes: 0,
            state: "resolved",
        };
    }

    if (caseItem.has_delivery_error) {
        return {
            label: "Проверьте отправку",
            className: getCaseSlaClassName("delivery_issue"),
            minutes: 0,
            state: "delivery_issue",
        };
    }
    if (caseItem.has_pending_outbox) {
        return {
            label: "Проверьте очередь",
            className: getCaseSlaClassName("pending_outbox"),
            minutes: 0,
            state: "pending_outbox",
        };
    }
    if (caseItem.needs_reply && caseItem.target_response_at) {
        return {
            label: `Ответить до ${formatTimeLabel(caseItem.target_response_at)}`,
            className: getCaseSlaClassName(
                caseItem.sla_status === "breached" ? "overdue" : "reply_due",
            ),
            minutes: 0,
            state: caseItem.sla_status === "breached" ? "overdue" : "reply_due",
        };
    }
    if (caseItem.human_lock_active) {
        return {
            label: "Ожидаем клиента",
            className: getCaseSlaClassName("waiting_client"),
            minutes: 0,
            state: "waiting_client",
        };
    }

    const createdAt = caseItem.created_at;
    if (createdAt) {
        return getSlaIndicator(createdAt);
    }

    return {
        label: "Диалог под контролем",
        className: "bg-green-100 text-green-800",
        minutes: 0,
        state: "ok",
    };
}

export function getSlaIndicator(createdAt: string): SlaIndicator {
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now.getTime() - created.getTime();
    const diffMinutes = Math.max(0, Math.floor(diffMs / (1000 * 60)));

    if (diffMinutes < SLA_WARNING_MINUTES) {
        return { label: "Ответ по плану", className: "bg-green-100 text-green-800", minutes: diffMinutes, state: "ok" };
    } else if (diffMinutes < SLA_BREACHED_MINUTES) {
        return { label: "Ответ в приоритете", className: "bg-yellow-100 text-yellow-800", minutes: diffMinutes, state: "warning" };
    } else {
        return { label: "Срочный ответ", className: "bg-red-100 text-red-800", minutes: diffMinutes, state: "breached" };
    }
}

export function getSlaCountdown(createdAt: string): SlaCountdown {
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now.getTime() - created.getTime();
    const diffMinutes = Math.max(0, Math.floor(diffMs / (1000 * 60)));

    if (diffMinutes < SLA_WARNING_MINUTES) {
        return {
            label: "Ответ в рабочем окне",
            className: "bg-green-100 text-green-800",
        };
    }

    if (diffMinutes < SLA_BREACHED_MINUTES) {
        return {
            label: "Нужен ответ менеджера",
            className: "bg-yellow-100 text-yellow-800",
        };
    }

    return {
        label: "Срочный ответ менеджера",
        className: "bg-red-100 text-red-800",
    };
}

// Booking status labels (for calendar)
export function getBookingStatusLabel(status: string): string {
    const normalized = status.toLowerCase();
    const labels: Record<string, string> = {
        pending: "запланировано",
        draft: "запланировано",
        hold: "запланировано",
        pending_confirmation: "запланировано",
        confirmed: "запланировано",
        checked_in: "запланировано",
        reschedule_requested: "запланировано",
        cancelled: "отменена",
        completed: "пришел",
        no_show: "не пришел",
    };
    return labels[normalized] || status;
}

// Booking status colors (for calendar badges)
export function getBookingStatusColor(status: string): string {
    const normalized = status.toLowerCase();
    const colors: Record<string, string> = {
        pending: "bg-yellow-100 text-yellow-800",
        draft: "bg-muted text-muted-foreground",
        hold: "bg-yellow-100 text-yellow-800",
        pending_confirmation: "bg-yellow-100 text-yellow-800",
        confirmed: "bg-green-100 text-green-800",
        checked_in: "bg-green-100 text-green-800",
        reschedule_requested: "bg-orange-100 text-orange-800",
        cancelled: "bg-muted text-muted-foreground",
        completed: "bg-green-100 text-green-800",
        no_show: "bg-red-100 text-red-800",
    };
    return colors[normalized] || "bg-muted text-muted-foreground";
}
