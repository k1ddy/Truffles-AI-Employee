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
        ok: "В норме",
        warning: "Внимание",
        breached: "Просрочено",
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

export function getSlaIndicator(createdAt: string): SlaIndicator {
    const created = new Date(createdAt);
    const now = new Date();
    const diffMs = now.getTime() - created.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffMinutes < 30) {
        return { label: `${diffMinutes}м`, className: "bg-green-100 text-green-800", minutes: diffMinutes };
    } else if (diffMinutes < 60) {
        return { label: `${diffMinutes}м`, className: "bg-yellow-100 text-yellow-800", minutes: diffMinutes };
    } else {
        const hours = Math.floor(diffMinutes / 60);
        return { label: `${hours}ч+`, className: "bg-red-100 text-red-800", minutes: diffMinutes };
    }
}

// Booking status labels (for calendar)
export function getBookingStatusLabel(status: string): string {
    const normalized = status.toLowerCase();
    const labels: Record<string, string> = {
        pending: "ожидает",
        draft: "черновик",
        hold: "бронь",
        pending_confirmation: "ожидает подтверждения",
        confirmed: "подтверждена",
        checked_in: "клиент пришел",
        reschedule_requested: "нужен перенос",
        cancelled: "отменена",
        completed: "завершена",
        no_show: "не пришёл",
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
        completed: "bg-secondary text-secondary-foreground",
        no_show: "bg-red-100 text-red-800",
    };
    return colors[normalized] || "bg-muted text-muted-foreground";
}
