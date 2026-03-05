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

// SLA indicator with color styling based on elapsed time
export interface SlaIndicator {
    label: string;
    className: string;
    minutes: number;
}

export interface SlaCountdown {
    label: string;
    className: string;
}

const SLA_WARNING_MINUTES = 60;
const SLA_BREACHED_MINUTES = 120;

export function getSlaIndicator(createdAt: string): SlaIndicator {
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now.getTime() - created.getTime();
    const diffMinutes = Math.max(0, Math.floor(diffMs / (1000 * 60)));

    if (diffMinutes < SLA_WARNING_MINUTES) {
        return { label: "В рабочем окне", className: "bg-green-100 text-green-800", minutes: diffMinutes };
    } else if (diffMinutes < SLA_BREACHED_MINUTES) {
        return { label: "Ответить сейчас", className: "bg-yellow-100 text-yellow-800", minutes: diffMinutes };
    } else {
        return { label: "Срочно ответить", className: "bg-red-100 text-red-800", minutes: diffMinutes };
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
        label: "Срок ответа нарушен",
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
