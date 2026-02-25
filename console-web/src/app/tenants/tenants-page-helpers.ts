"use client";

import type { components } from "@/types/api.generated";

export const LIFECYCLE_AUDIT_STORAGE_KEY = "tenants:client-lifecycle-audit:v2";
export const MAX_LIFECYCLE_AUDIT_ENTRIES_PER_CLIENT = 20;

export const SLUG_INPUT_PATTERN = /^[a-z0-9][a-z0-9_-]*$/;
export const BRANCH_PHONE_INPUT_PATTERN = /^\+?[0-9][0-9\s()-]{5,23}$/;
const TELEGRAM_CHAT_ID_INPUT_PATTERN = /^-?[0-9]{5,20}$/;
const KNOWLEDGE_TAG_INPUT_PATTERN = /^[a-z0-9][a-z0-9_-]{0,63}$/;

const REFERENCE_SCOPE_REASON_LABELS: Record<string, string> = {
    active_live_signals: "live-сигналы активных филиалов",
    active_fallback_best_candidate: "fallback на лучший активный филиал",
    no_active_branches: "нет активных филиалов",
};

const LIFECYCLE_STATE_LABELS: Record<string, string> = {
    active: "Активный",
    archived: "Архив",
};

export type ClientLifecycleMode = "archive" | "restore";
export type ClientLifecycleAuditSource = "session" | "api";

export type ClientLifecycleAuditEntry = {
    clientId: string;
    mode: ClientLifecycleMode;
    previousLifecycleLabel: string;
    targetLifecycleLabel: string;
    reason: string;
    status: "success" | "error";
    message: string;
    traceId?: string;
    actorLabel: string;
    happenedAt: string;
    source: ClientLifecycleAuditSource;
    sourceEventId?: string;
};

export type ClientLifecycleAuditMap = Record<string, ClientLifecycleAuditEntry[]>;

type BranchEditorLike = {
    name: string;
    slug: string;
    timezone: string;
    phone: string;
    instanceId: string;
    telegramChatId: string;
    knowledgeTag: string;
    isActive: boolean;
    original: {
        name: string;
        slug: string;
        timezone: string;
        phone: string;
        instanceId: string;
        telegramChatId: string;
        knowledgeTag: string;
        isActive: boolean;
    };
};

function lifecycleStateFromStatus(status: string | undefined): string {
    const normalized = (status ?? "").trim().toLowerCase();
    if (!normalized) {
        return "—";
    }
    if (normalized === "active") {
        return LIFECYCLE_STATE_LABELS.active;
    }
    if (normalized === "archived" || normalized === "inactive") {
        return LIFECYCLE_STATE_LABELS.archived;
    }
    return normalized;
}

export function isValidTimezoneName(value: string): boolean {
    try {
        Intl.DateTimeFormat("en-US", { timeZone: value });
        return true;
    } catch {
        return false;
    }
}

export function formatStateLabel(
    value: string | null | undefined,
    map: Record<string, string>,
): string {
    if (!value) {
        return "—";
    }
    return map[value] ?? value;
}

export function formatDateTimeLabel(value: string | undefined): string {
    if (!value) {
        return "—";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return "—";
    }
    return parsed.toLocaleString("ru-RU");
}

export function formatReferenceScopeReason(value?: string | null): string {
    if (!value) {
        return "не задан";
    }
    return REFERENCE_SCOPE_REASON_LABELS[value] ?? value;
}

export function toIsoWeekKey(dateValue: string): string {
    const parsed = new Date(dateValue);
    if (Number.isNaN(parsed.getTime())) {
        return "invalid-week";
    }
    const target = new Date(Date.UTC(parsed.getUTCFullYear(), parsed.getUTCMonth(), parsed.getUTCDate()));
    const weekday = target.getUTCDay() || 7;
    target.setUTCDate(target.getUTCDate() + 4 - weekday);

    const isoYear = target.getUTCFullYear();
    const yearStart = new Date(Date.UTC(isoYear, 0, 1));
    const week = Math.ceil((((target.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
    return `${isoYear}-W${String(week).padStart(2, "0")}`;
}

export function safeParseLifecycleAuditMap(rawValue: string | null): ClientLifecycleAuditMap {
    if (!rawValue) {
        return {};
    }
    try {
        const parsed = JSON.parse(rawValue) as ClientLifecycleAuditMap;
        if (!parsed || typeof parsed !== "object") {
            return {};
        }
        const result: ClientLifecycleAuditMap = {};
        for (const [clientId, entries] of Object.entries(parsed)) {
            if (!Array.isArray(entries)) {
                continue;
            }
            const normalized: ClientLifecycleAuditEntry[] = entries
                .filter((entry) => entry && typeof entry === "object")
                .map((entry) => {
                    const raw = entry as Partial<ClientLifecycleAuditEntry>;
                    const mode: ClientLifecycleMode = raw.mode === "restore" ? "restore" : "archive";
                    const status: "success" | "error" = raw.status === "error" ? "error" : "success";
                    const source: ClientLifecycleAuditSource = raw.source === "api" ? "api" : "session";
                    return {
                        clientId: raw.clientId ?? clientId,
                        mode,
                        previousLifecycleLabel: raw.previousLifecycleLabel ?? "—",
                        targetLifecycleLabel: raw.targetLifecycleLabel ?? "—",
                        reason: raw.reason ?? "—",
                        status,
                        message: raw.message ?? "—",
                        traceId: raw.traceId,
                        actorLabel: raw.actorLabel ?? "unknown",
                        happenedAt: raw.happenedAt ?? new Date().toISOString(),
                        source,
                        sourceEventId: raw.sourceEventId,
                    };
                })
                .slice(0, MAX_LIFECYCLE_AUDIT_ENTRIES_PER_CLIENT);
            result[clientId] = normalized;
        }
        return result;
    } catch {
        return {};
    }
}

export function mergeLifecycleAuditEntries(
    sessionEntries: ClientLifecycleAuditEntry[],
    apiEntries: ClientLifecycleAuditEntry[],
): ClientLifecycleAuditEntry[] {
    const merged = [...sessionEntries, ...apiEntries];
    const deduped = new Map<string, ClientLifecycleAuditEntry>();
    for (const entry of merged) {
        const key = [
            entry.clientId,
            entry.mode,
            entry.status,
            entry.reason,
            entry.happenedAt,
            entry.source,
            entry.sourceEventId ?? "",
        ].join("|");
        if (!deduped.has(key)) {
            deduped.set(key, entry);
        }
    }
    return [...deduped.values()]
        .sort((a, b) => new Date(b.happenedAt).getTime() - new Date(a.happenedAt).getTime())
        .slice(0, MAX_LIFECYCLE_AUDIT_ENTRIES_PER_CLIENT);
}

export function pushLifecycleAuditEntry(
    previous: ClientLifecycleAuditMap,
    entry: ClientLifecycleAuditEntry,
): ClientLifecycleAuditMap {
    const existing = previous[entry.clientId] ?? [];
    const dedupKey = [
        entry.clientId,
        entry.mode,
        entry.status,
        entry.reason,
        entry.happenedAt,
        entry.source,
        entry.sourceEventId ?? "",
    ].join("|");
    if (
        existing.some((item) =>
            [
                item.clientId,
                item.mode,
                item.status,
                item.reason,
                item.happenedAt,
                item.source,
                item.sourceEventId ?? "",
            ].join("|") === dedupKey)
    ) {
        return previous;
    }
    return {
        ...previous,
        [entry.clientId]: [entry, ...existing].slice(0, MAX_LIFECYCLE_AUDIT_ENTRIES_PER_CLIENT),
    };
}

export function buildBranchChangePatch(editor: BranchEditorLike): {
    patch: components["schemas"]["ConsoleBranchChangePatch"];
    hasChanges: boolean;
    error?: string;
} {
    const name = editor.name.trim();
    const slug = editor.slug.trim();
    if (!name || !slug) {
        return {
            patch: {},
            hasChanges: false,
            error: "Заполните название и slug филиала",
        };
    }
    if (!SLUG_INPUT_PATTERN.test(slug)) {
        return {
            patch: {},
            hasChanges: false,
            error: "slug должен быть в формате snake-case: [a-z0-9_-], без пробелов",
        };
    }
    const patch: components["schemas"]["ConsoleBranchChangePatch"] = {};
    if (name !== editor.original.name) {
        patch.name = name;
    }
    if (slug !== editor.original.slug) {
        patch.slug = slug;
    }
    const timezone = editor.timezone.trim();
    if (timezone && !isValidTimezoneName(timezone)) {
        return {
            patch: {},
            hasChanges: false,
            error: "timezone должен быть в формате IANA, например Asia/Almaty",
        };
    }
    if (timezone !== editor.original.timezone) {
        patch.timezone = timezone || null;
    }
    const phone = editor.phone.trim();
    if (phone && !BRANCH_PHONE_INPUT_PATTERN.test(phone)) {
        return {
            patch: {},
            hasChanges: false,
            error: "phone: ожидается +7 700 000 00 00 (7-15 цифр, допускаются пробелы/скобки)",
        };
    }
    if (phone !== editor.original.phone) {
        patch.phone = phone || null;
    }
    const instanceId = editor.instanceId.trim();
    if (instanceId !== editor.original.instanceId) {
        patch.instance_id = instanceId || null;
    }
    const telegramChatId = editor.telegramChatId.trim();
    if (telegramChatId && !TELEGRAM_CHAT_ID_INPUT_PATTERN.test(telegramChatId)) {
        return {
            patch: {},
            hasChanges: false,
            error: "Чат Telegram: ожидается целое число (например -1001234567890)",
        };
    }
    if (telegramChatId !== editor.original.telegramChatId) {
        patch.telegram_chat_id = telegramChatId || null;
    }
    const knowledgeTag = editor.knowledgeTag.trim();
    if (knowledgeTag && !KNOWLEDGE_TAG_INPUT_PATTERN.test(knowledgeTag.toLowerCase())) {
        return {
            patch: {},
            hasChanges: false,
            error: "Тег базы знаний: [a-z0-9_-], до 64 символов",
        };
    }
    if (knowledgeTag !== editor.original.knowledgeTag) {
        patch.knowledge_tag = knowledgeTag || null;
    }
    if (editor.isActive !== editor.original.isActive) {
        patch.is_active = editor.isActive;
    }
    if (editor.isActive && !editor.instanceId.trim()) {
        return {
            patch: {},
            hasChanges: false,
            error: "Для активного филиала обязателен идентификатор WhatsApp",
        };
    }
    return { patch, hasChanges: Object.keys(patch).length > 0 };
}

export function applyBranchSnapshotToEditor<T extends BranchEditorLike>(
    editor: T,
    branch?: components["schemas"]["ConsoleBranch"] | null,
): T {
    if (!branch) {
        return editor;
    }
    const next = {
        name: branch.name ?? "",
        slug: branch.slug ?? "",
        timezone: branch.timezone ?? "",
        phone: branch.phone ?? "",
        instanceId: branch.instance_id ?? "",
        telegramChatId: branch.telegram_chat_id ?? "",
        knowledgeTag: branch.knowledge_tag ?? "",
        isActive: branch.is_active ?? false,
    };
    return {
        ...editor,
        ...next,
        changeReason: "",
        confirmReason: "",
        rollbackReason: "",
        original: next,
    };
}

export function mapAuditEventToLifecycleEntry(
    event: components["schemas"]["ConsoleAuditEvent"],
): ClientLifecycleAuditEntry | null {
    const eventType = (event.event_type ?? "").trim();
    if (!eventType) {
        return null;
    }
    if (eventType !== "client_archived" && eventType !== "client_restored" && eventType !== "client_archive_blocked") {
        return null;
    }
    const payload = event.payload && typeof event.payload === "object"
        ? (event.payload as Record<string, unknown>)
        : {};
    const clientId = typeof event.entity_id === "string" ? event.entity_id : "";
    if (!clientId) {
        return null;
    }
    const mode: ClientLifecycleMode = eventType === "client_restored" ? "restore" : "archive";
    const status: "success" | "error" = eventType === "client_archive_blocked" ? "error" : "success";
    const previousLifecycleLabel = lifecycleStateFromStatus(
        typeof payload.previous_status === "string" ? payload.previous_status : undefined,
    );
    const targetLifecycleLabel = lifecycleStateFromStatus(
        typeof payload.next_status === "string" ? payload.next_status : undefined,
    );
    const reason = typeof payload.reason === "string" ? payload.reason : "—";
    const message = eventType === "client_archived"
        ? "Архивация подтверждена API"
        : eventType === "client_restored"
            ? "Восстановление подтверждено API"
            : "Архивация заблокирована зависимостями";

    return {
        clientId,
        mode,
        previousLifecycleLabel,
        targetLifecycleLabel,
        reason,
        status,
        message,
        actorLabel: event.actor_name ?? "system",
        happenedAt: event.created_at ?? new Date().toISOString(),
        source: "api",
        sourceEventId: typeof event.id === "string" ? event.id : undefined,
        traceId: typeof payload.trace_id === "string" ? payload.trace_id : undefined,
    };
}
