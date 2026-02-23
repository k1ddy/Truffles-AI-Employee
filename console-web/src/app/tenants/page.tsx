"use client";

import { useEffect, useMemo, useState } from "react";
import { InfiniteData, useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";
import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";
import TenantsActionQueuePanel, { type TenantsActionQueueItem } from "@/components/TenantsActionQueuePanel";
import TenantsOperationalKpiPanel from "@/components/TenantsOperationalKpiPanel";
import TenantsQuickCreatePanel from "@/components/TenantsQuickCreatePanel";
import TenantsScopedErrorSummary from "@/components/TenantsScopedErrorSummary";
import TenantsSensitiveIdCell, { type TenantsSensitiveAction } from "@/components/TenantsSensitiveIdCell";
import TenantsTopControls, { type TenantsFilterOption } from "@/components/TenantsTopControls";
import {
    adminApi,
    auditApi,
    authApi,
    canAccessConsole,
    confirmationsApi,
    opsApi,
    type TenantsOperationalSnapshotPayload,
    type TenantsWeeklySnapshotRecord,
} from "@/lib/api-client";
import { readBrowserStorage, writeBrowserStorage } from "@/lib/browser-storage";
import {
    readConsoleContextScopeFromStorage,
    setConsoleContextScope,
} from "@/lib/console-context-storage";
import { useInlineErrorSummary } from "@/lib/use-inline-error-summary";
import { useTenantsPageFilters } from "./use-tenants-page-filters";

type CompanyEditorState = {
    id: string;
    name: string;
    billingInfo: string;
    originalName: string;
    originalBillingInfo: string;
};

type ClientEditorState = {
    id: string;
    slug: string;
    companyId: string;
    originalSlug: string;
    originalCompanyId: string;
    totalBranches: number;
};

type ClientLifecycleMode = "archive" | "restore";
type ClientLifecycleAuditFilter = "all" | "success" | "error";
type ClientLifecycleAuditSource = "session" | "api";
type ClientLifecycleDraftState = {
    clientId: string;
    clientLabel: string;
    companyLabel: string;
    mode: ClientLifecycleMode;
    currentLifecycleLabel: string;
    targetLifecycleLabel: string;
    activeBranches: number;
    totalBranches: number;
    degradedBranches: number;
    reason: string;
    confirmChecked: boolean;
    checkClientScope: boolean;
    checkImpactReview: boolean;
    checkOwnerAligned: boolean;
};

type ClientLifecycleAuditEntry = {
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

type ClientLifecycleAuditMap = Record<string, ClientLifecycleAuditEntry[]>;

type BranchEditorState = {
    id: string;
    name: string;
    slug: string;
    timezone: string;
    phone: string;
    instanceId: string;
    telegramChatId: string;
    knowledgeTag: string;
    isActive: boolean;
    changeReason: string;
    confirmReason: string;
    rollbackReason: string;
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

type QuickCreateFormState = {
    companyName: string;
    clientSlug: string;
    branchName: string;
    branchSlug: string;
    branchTimezone: string;
    branchPhone: string;
    branchInstanceId: string;
    companyId: string;
    clientId: string;
};

type BranchChangeRecord = components["schemas"]["ConsoleBranchChangeRecord"];

type TenantLifecycleMode = "active" | "archived" | "all";
type FleetLifecycleFilter = "all" | "lead" | "contracting" | "onboarding" | "go_live_ready" | "active" | "paused" | "archived";
type FleetPaymentFilter = "all" | "pending" | "confirmed" | "rejected" | "unknown";
type FleetServiceFilter = "all" | "ok" | "degraded" | "attention";
type FleetAttentionLevel = "high" | "medium" | "low";
type TenantsWorkspaceMode = "portfolio" | "onboarding" | "changes" | "decommission";
type TenantsViewPreset = "operator" | "platform";

type ActionQueueIntent =
    | "set_context"
    | "open_cases"
    | "open_integrations"
    | "workspace_portfolio"
    | "workspace_onboarding"
    | "workspace_changes"
    | "workspace_decommission"
    | "none";

type ActionQueueItem = TenantsActionQueueItem & {
    intent: ActionQueueIntent;
};
type OperationalKpiId =
    | "onboardingCoverage"
    | "goLiveReadiness"
    | "serviceStability"
    | "decommissionShare"
    | "changeFailure"
    | "rollbackShare"
    | "blockedSignals";
type OperationalKpiStatus = "ok" | "warn" | "critical";
type OperationalKpiAction = "portfolio" | "onboarding" | "changes" | "decommission";
type OperationalKpiRule = {
    id: OperationalKpiId;
    label: string;
    unit: "percent" | "count";
    direction: "higher_better" | "lower_better";
    warn: number;
    critical: number;
    action: OperationalKpiAction;
    actionLabel: string;
};
type OperationalKpiDrilldown = {
    id: OperationalKpiId;
    label: string;
    value: number;
    displayValue: string;
    status: OperationalKpiStatus;
    thresholdLabel: string;
    reason: string;
    action: OperationalKpiAction;
    actionLabel: string;
};
type TenantsOperationalSnapshot = {
    id: string;
    weekKey: string;
    createdAt: string;
    report: {
        generatedAt: string;
        sourceWindow: number;
        workspaceMode: TenantsWorkspaceMode;
        lifecycleMode: TenantLifecycleMode;
        kpi: Record<OperationalKpiId, number>;
        drilldown: Array<{
            id: OperationalKpiId;
            status: OperationalKpiStatus;
            value: number;
            reason: string;
        }>;
        attentionSummary: {
            activeClientsTotal: number;
            highRiskClients: number;
            mediumRiskClients: number;
            outboxFailed24hTotal: number;
            pendingHandoversTotal: number;
        };
    };
};

const LIFECYCLE_AUDIT_STORAGE_KEY = "tenants:client-lifecycle-audit:v2";
const MAX_LIFECYCLE_AUDIT_ENTRIES_PER_CLIENT = 20;
const MAX_WEEKLY_SNAPSHOTS = 12;

const OPERATIONAL_KPI_RULES: OperationalKpiRule[] = [
    {
        id: "onboardingCoverage",
        label: "Покрытие онбординга",
        unit: "percent",
        direction: "higher_better",
        warn: 60,
        critical: 40,
        action: "onboarding",
        actionLabel: "Открыть онбординг",
    },
    {
        id: "goLiveReadiness",
        label: "Готовность к запуску",
        unit: "percent",
        direction: "higher_better",
        warn: 70,
        critical: 50,
        action: "onboarding",
        actionLabel: "Проверить запуск",
    },
    {
        id: "serviceStability",
        label: "Стабильность сервиса",
        unit: "percent",
        direction: "higher_better",
        warn: 95,
        critical: 85,
        action: "portfolio",
        actionLabel: "Открыть риски",
    },
    {
        id: "decommissionShare",
        label: "Доля вывода из эксплуатации",
        unit: "percent",
        direction: "lower_better",
        warn: 30,
        critical: 45,
        action: "decommission",
        actionLabel: "Открыть вывод из эксплуатации",
    },
    {
        id: "changeFailure",
        label: "Доля ошибок публикации",
        unit: "percent",
        direction: "lower_better",
        warn: 10,
        critical: 20,
        action: "changes",
        actionLabel: "Открыть изменения",
    },
    {
        id: "rollbackShare",
        label: "Доля откатов",
        unit: "percent",
        direction: "lower_better",
        warn: 15,
        critical: 30,
        action: "changes",
        actionLabel: "Проверить откаты",
    },
    {
        id: "blockedSignals",
        label: "Блокирующие сигналы",
        unit: "count",
        direction: "lower_better",
        warn: 1,
        critical: 5,
        action: "portfolio",
        actionLabel: "Разобрать блокеры",
    },
];

function stringifyOptionalJson(value: unknown): string {
    if (!value || typeof value !== "object") {
        return "";
    }
    const keys = Object.keys(value as Record<string, unknown>);
    if (keys.length === 0) {
        return "";
    }
    return JSON.stringify(value, null, 2);
}

function parseOptionalJson(value: string, label: string): { value?: Record<string, unknown>; error?: string } {
    const trimmed = value.trim();
    if (!trimmed) {
        return {};
    }
    try {
        return { value: JSON.parse(trimmed) as Record<string, unknown> };
    } catch {
        return { error: `${label}: некорректный JSON` };
    }
}

function attentionLevelClass(level?: FleetAttentionLevel): string {
    if (level === "high") {
        return "bg-red-100 text-red-700";
    }
    if (level === "medium") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-blue-100 text-blue-700";
}

const FLEET_LIFECYCLE_LABELS: Record<string, string> = {
    lead: "Лид",
    contracting: "Договор",
    onboarding: "Онбординг",
    go_live_ready: "Готов к запуску",
    active: "Активный",
    paused: "Пауза",
    archived: "Архив",
};

const FLEET_PAYMENT_LABELS: Record<string, string> = {
    pending: "Ожидает",
    confirmed: "Подтверждена",
    rejected: "Отклонена",
    unknown: "Не задана",
};

const FLEET_SERVICE_LABELS: Record<string, string> = {
    ok: "Стабильно",
    degraded: "Деградация",
    attention: "Требует внимания",
};

const REFERENCE_SCOPE_REASON_LABELS: Record<string, string> = {
    active_live_signals: "live-сигналы активных филиалов",
    active_fallback_best_candidate: "fallback на лучший активный филиал",
    no_active_branches: "нет активных филиалов",
};

const BRANCH_CHANGE_STATUS_LABELS: Record<string, string> = {
    draft: "Черновик",
    validated: "Проверено",
    published: "Применено",
    publish_failed: "Ошибка применения",
    rolled_back: "Откат выполнен",
    rollback_failed: "Ошибка отката",
};

const SLUG_INPUT_PATTERN = /^[a-z0-9][a-z0-9_-]*$/;
const BRANCH_PHONE_INPUT_PATTERN = /^\+?[0-9][0-9\s()-]{5,23}$/;
const TELEGRAM_CHAT_ID_INPUT_PATTERN = /^-?[0-9]{5,20}$/;
const KNOWLEDGE_TAG_INPUT_PATTERN = /^[a-z0-9][a-z0-9_-]{0,63}$/;

function isValidTimezoneName(value: string): boolean {
    try {
        Intl.DateTimeFormat("en-US", { timeZone: value });
        return true;
    } catch {
        return false;
    }
}

function formatStateLabel(
    value: string | null | undefined,
    map: Record<string, string>,
): string {
    if (!value) {
        return "—";
    }
    return map[value] ?? value;
}

function formatDateTimeLabel(value: string | undefined): string {
    if (!value) {
        return "—";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return "—";
    }
    return parsed.toLocaleString("ru-RU");
}

function resolveErrorScopeFromWorkspace(workspaceMode: TenantsWorkspaceMode): string {
    return workspaceMode;
}

function formatReferenceScopeReason(value?: string | null): string {
    if (!value) {
        return "не задан";
    }
    return REFERENCE_SCOPE_REASON_LABELS[value] ?? value;
}

function asPercent(numerator: number, denominator: number): number {
    if (denominator <= 0) {
        return 0;
    }
    return Math.round((numerator / denominator) * 100);
}

function formatOptionalHours(value: number | null | undefined): string {
    if (typeof value !== "number" || Number.isNaN(value)) {
        return "—";
    }
    return `${Number(value.toFixed(1))}ч`;
}

function formatOptionalPercent(value: number | null | undefined): string {
    if (typeof value !== "number" || Number.isNaN(value)) {
        return "—";
    }
    return `${Number(value.toFixed(1))}%`;
}

function toIsoWeekKey(dateValue: string): string {
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

function lifecycleStateFromStatus(status: string | undefined): string {
    const normalized = (status ?? "").trim().toLowerCase();
    if (!normalized) {
        return "—";
    }
    if (normalized === "active") {
        return FLEET_LIFECYCLE_LABELS.active;
    }
    if (normalized === "archived" || normalized === "inactive") {
        return FLEET_LIFECYCLE_LABELS.archived;
    }
    return normalized;
}

function safeParseLifecycleAuditMap(rawValue: string | null): ClientLifecycleAuditMap {
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

function mapWeeklySnapshotRecordToViewModel(
    record: TenantsWeeklySnapshotRecord,
): TenantsOperationalSnapshot | null {
    if (!record?.id || !record?.created_at || !record?.week_key) {
        return null;
    }
    if (!record.snapshot || typeof record.snapshot !== "object") {
        return null;
    }
    const report = record.snapshot as Partial<TenantsOperationalSnapshot["report"]>;
    if (!report.generatedAt || !report.kpi || typeof report.kpi !== "object") {
        return null;
    }
    return {
        id: record.id,
        weekKey: record.week_key,
        createdAt: record.created_at,
        report: report as TenantsOperationalSnapshot["report"],
    };
}

function mergeLifecycleAuditEntries(
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

function computeKpiStatus(value: number, rule: OperationalKpiRule): OperationalKpiStatus {
    if (rule.direction === "higher_better") {
        if (value < rule.critical) {
            return "critical";
        }
        if (value < rule.warn) {
            return "warn";
        }
        return "ok";
    }
    if (value > rule.critical) {
        return "critical";
    }
    if (value > rule.warn) {
        return "warn";
    }
    return "ok";
}

function formatKpiValue(value: number, unit: "percent" | "count"): string {
    if (unit === "percent") {
        return `${value}%`;
    }
    return `${value}`;
}

function formatThresholdLabel(rule: OperationalKpiRule): string {
    const formatValue = (value: number) => (rule.unit === "percent" ? `${value}%` : `${value}`);
    if (rule.direction === "higher_better") {
        return `warn < ${formatValue(rule.warn)}, critical < ${formatValue(rule.critical)}`;
    }
    return `warn > ${formatValue(rule.warn)}, critical > ${formatValue(rule.critical)}`;
}

function formatKpiReason(value: number, rule: OperationalKpiRule, status: OperationalKpiStatus): string {
    const thresholdLabel = formatThresholdLabel(rule);
    if (status === "ok") {
        return `В норме (${thresholdLabel})`;
    }
    if (status === "critical") {
        return `Критично (${thresholdLabel})`;
    }
    return `Требует внимания (${thresholdLabel})`;
}

function toCsvCell(value: string | number): string {
    const raw = String(value);
    if (raw.includes(",") || raw.includes("\"") || raw.includes("\n")) {
        return `"${raw.replaceAll("\"", "\"\"")}"`;
    }
    return raw;
}

function toFilterOptions(
    values: Array<{ id: string | null | undefined; label: string | null | undefined }>,
): TenantsFilterOption[] {
    const unique = new Map<string, string>();
    values.forEach((item) => {
        if (!item.id) {
            return;
        }
        const normalizedLabel = (item.label ?? "").trim();
        if (!unique.has(item.id)) {
            unique.set(item.id, normalizedLabel || item.id);
        }
    });
    return [...unique.entries()]
        .map(([id, label]) => ({ id, label }))
        .sort((left, right) => left.label.localeCompare(right.label, "ru"));
}

function normalizeOptionalId(value: string | null | undefined): string | null {
    const normalized = (value ?? "").trim();
    return normalized.length > 0 ? normalized : null;
}

function readBranchClientId(branch: components["schemas"]["ConsoleBranch"]): string | null {
    const value = (branch as components["schemas"]["ConsoleBranch"] & { client_id?: string | null }).client_id;
    return normalizeOptionalId(value);
}

function readBranchCompanyId(branch: components["schemas"]["ConsoleBranch"]): string | null {
    const value = (branch as components["schemas"]["ConsoleBranch"] & { company_id?: string | null }).company_id;
    return normalizeOptionalId(value);
}

function pushLifecycleAuditEntry(
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

function buildBranchChangePatch(editor: BranchEditorState): {
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
            error: "telegram_chat_id: ожидается целое число (например -1001234567890)",
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
            error: "knowledge_tag: [a-z0-9_-], до 64 символов",
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
            error: "instance_id обязателен для активного филиала",
        };
    }
    return { patch, hasChanges: Object.keys(patch).length > 0 };
}

function applyBranchSnapshotToEditor(
    editor: BranchEditorState,
    branch?: components["schemas"]["ConsoleBranch"] | null,
): BranchEditorState {
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

function mapAuditEventToLifecycleEntry(
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

function buildOperationalKpiDrilldown(
    values: Record<OperationalKpiId, number>,
): OperationalKpiDrilldown[] {
    return OPERATIONAL_KPI_RULES.map((rule) => {
        const value = values[rule.id];
        const status = computeKpiStatus(value, rule);
        return {
            id: rule.id,
            label: rule.label,
            value,
            displayValue: formatKpiValue(value, rule.unit),
            status,
            thresholdLabel: formatThresholdLabel(rule),
            reason: formatKpiReason(value, rule, status),
            action: rule.action,
            actionLabel: rule.actionLabel,
        };
    });
}

export default function TenantsPage() {
    const { data: session } = useSession();
    const router = useRouter();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();
    const controlTowerEnabled = process.env.NEXT_PUBLIC_TENANTS_V3_CONTROL_TOWER !== "0";
    const { errors: inlineErrors, reportError, reportInlineError, clearErrors } = useInlineErrorSummary();
    const reportValidationError = (
        message: string,
        code = "VALIDATION_ERROR",
        scope?: string,
    ) => {
        const resolvedScope = scope ?? resolveErrorScopeFromWorkspace(controlTowerEnabled ? workspaceMode : "portfolio");
        reportInlineError({ code, message, scope: resolvedScope });
        toast.error(message);
    };
    const reportProvisioningError = (error: unknown, operation: string, endpoint: string) =>
        reportError(error, {
            includeProvisioningGuidance: true,
            operation,
            endpoint,
            scope: resolveErrorScopeFromWorkspace(controlTowerEnabled ? workspaceMode : "portfolio"),
        });
    const [clientQuery, setClientQuery] = useState("");
    const [branchQuery, setBranchQuery] = useState("");
    const [companyQuery, setCompanyQuery] = useState("");
    const [tenantLifecycle, setTenantLifecycle] = useState<TenantLifecycleMode>("active");
    const [workspaceMode, setWorkspaceMode] = useState<TenantsWorkspaceMode>("portfolio");
    const [viewPreset, setViewPreset] = useState<TenantsViewPreset>("operator");
    const [fleetLifecycleFilter, setFleetLifecycleFilter] = useState<FleetLifecycleFilter>("all");
    const [fleetPaymentFilter, setFleetPaymentFilter] = useState<FleetPaymentFilter>("all");
    const [fleetServiceFilter, setFleetServiceFilter] = useState<FleetServiceFilter>("all");
    const [companyEditor, setCompanyEditor] = useState<CompanyEditorState | null>(null);
    const [clientEditor, setClientEditor] = useState<ClientEditorState | null>(null);
    const [branchEditor, setBranchEditor] = useState<BranchEditorState | null>(null);
    const [savingCompany, setSavingCompany] = useState(false);
    const [savingClient, setSavingClient] = useState(false);
    const [savingBranch, setSavingBranch] = useState(false);
    const [publishingBranchChange, setPublishingBranchChange] = useState(false);
    const [rollingBackBranchChange, setRollingBackBranchChange] = useState(false);
    const [branchChangePreview, setBranchChangePreview] = useState<components["schemas"]["ConsoleBranchChangeResponse"] | null>(null);
    const [clientLifecyclePendingId, setClientLifecyclePendingId] = useState<string | null>(null);
    const [clientLifecycleDraft, setClientLifecycleDraft] = useState<ClientLifecycleDraftState | null>(null);
    const [clientLifecycleAuditById, setClientLifecycleAuditById] = useState<ClientLifecycleAuditMap>({});
    const [clientLifecycleAuditFilterById, setClientLifecycleAuditFilterById] = useState<Record<string, ClientLifecycleAuditFilter>>({});
    const [weeklySnapshots, setWeeklySnapshots] = useState<TenantsOperationalSnapshot[]>([]);
    const [runningMetricsSnapshotMode, setRunningMetricsSnapshotMode] = useState<"dry_run" | "execute" | null>(null);
    const [lastMetricsSnapshotJob, setLastMetricsSnapshotJob] = useState<components["schemas"]["ConsoleOpsJobRecord"] | null>(null);
    const [quickCreateForm, setQuickCreateForm] = useState<QuickCreateFormState>({
        companyName: "",
        clientSlug: "",
        branchName: "",
        branchSlug: "",
        branchTimezone: "Asia/Almaty",
        branchPhone: "",
        branchInstanceId: "",
        companyId: "",
        clientId: "",
    });
    const [quickCreateRunning, setQuickCreateRunning] = useState<"company" | "client" | "branch" | null>(null);
    const effectiveWorkspaceMode: TenantsWorkspaceMode = controlTowerEnabled ? workspaceMode : "portfolio";

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const isPlatformAdmin = role === "platform_admin";
    const canSwitchViewPreset = isPlatformAdmin;
    const isPlatformPreset = viewPreset === "platform";
    const canReadTenants = canAccessConsole(role, "tenants", "read");
    const canWriteTenants = canAccessConsole(role, "tenants", "write");

    const selectedClientId = meData?.client?.id ?? null;
    const selectedCompanyId = meData?.selected_company_id ?? meData?.client?.company_id ?? null;
    const selectedBranchId = meData?.selected_branch_id ?? null;
    const {
        pageFilterCompanyId,
        pageFilterClientId,
        pageFilterBranchId,
        hasPageFilters,
        setPageFilterCompany,
        setPageFilterClient,
        setPageFilterBranch,
        applyScopeToPageFilters,
        clearPageFilters,
    } = useTenantsPageFilters({
        searchParams,
        router,
        initialContext: {
            companyId: selectedCompanyId,
            clientId: selectedClientId,
            branchId: selectedBranchId,
        },
        canInitialize: Boolean(meData),
    });
    const knownCompanies = useMemo(
        () => meData?.companies ?? [],
        [meData?.companies],
    );
    const knownBranches = useMemo(
        () => meData?.branches ?? [],
        [meData?.branches],
    );
    const selectedCompanyNameFromContext = useMemo(() => {
        if (!selectedCompanyId) {
            return null;
        }
        return knownCompanies.find((company) => company.id === selectedCompanyId)?.name ?? null;
    }, [knownCompanies, selectedCompanyId]);
    const selectedBranchNameFromContext = useMemo(() => {
        if (!selectedBranchId) {
            return null;
        }
        return knownBranches.find((branch) => branch.id === selectedBranchId)?.name ?? null;
    }, [knownBranches, selectedBranchId]);
    const quickCreateCompanyId = quickCreateForm.companyId || selectedCompanyId || "";
    const quickCreateClientId = quickCreateForm.clientId || selectedClientId || "";

    const tenantsEnabled = Boolean(session && canReadTenants);
    const companyQueryValue = companyQuery.trim() || undefined;
    const clientQueryValue = clientQuery.trim() || undefined;
    const branchQueryValue = branchQuery.trim() || undefined;

    useEffect(() => {
        setClientLifecycleAuditById(safeParseLifecycleAuditMap(readBrowserStorage(LIFECYCLE_AUDIT_STORAGE_KEY)));
    }, []);

    useEffect(() => {
        writeBrowserStorage(
            LIFECYCLE_AUDIT_STORAGE_KEY,
            JSON.stringify(clientLifecycleAuditById),
        );
    }, [clientLifecycleAuditById]);

    const companiesQuery = useInfiniteQuery<
        components["schemas"]["ConsoleCompanyListResponse"],
        Error,
        InfiniteData<components["schemas"]["ConsoleCompanyListResponse"], string | undefined>,
        ["tenants-companies", string | undefined],
        string | undefined
    >({
        queryKey: ["tenants-companies", companyQueryValue],
        queryFn: async ({ pageParam }) => {
            const cursor = typeof pageParam === "string" ? pageParam : undefined;
            const response = await adminApi.listCompanies({
                cursor,
                limit: 20,
                q: companyQueryValue,
            });
            return response.data;
        },
        initialPageParam: undefined,
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? lastPage.cursor ?? undefined : undefined,
        enabled: tenantsEnabled,
    });
    const tenantsPortfolioQuery = useQuery({
        queryKey: [
            "tenants-portfolio",
            clientQueryValue,
            pageFilterCompanyId,
            tenantLifecycle,
            fleetLifecycleFilter,
            fleetPaymentFilter,
            fleetServiceFilter,
        ],
        queryFn: async () => {
            const response = await adminApi.getTenantsPortfolio({
                limit: 20,
                q: clientQueryValue,
                company_id: pageFilterCompanyId ?? undefined,
                lifecycle: tenantLifecycle,
                attention_limit: 12,
                stale_after_minutes: 60,
                include_low: "false",
            });
            return response.data;
        },
        enabled: tenantsEnabled,
        staleTime: 30000,
    });
    const tenantsCompanyCockpitQuery = useQuery({
        queryKey: [
            "tenants-company-cockpit",
            pageFilterCompanyId,
            pageFilterClientId,
            clientQueryValue,
            branchQueryValue,
            tenantLifecycle,
        ],
        queryFn: async () => {
            if (!pageFilterCompanyId) {
                return null;
            }
            const response = await adminApi.getTenantsCompanyCockpit({
                company_id: pageFilterCompanyId,
                client_id: pageFilterClientId ?? undefined,
                lifecycle: tenantLifecycle,
                client_limit: 20,
                branch_limit: 20,
                client_q: clientQueryValue,
                branch_q: branchQueryValue,
            });
            return response.data;
        },
        enabled: tenantsEnabled && !!pageFilterCompanyId,
        staleTime: 30000,
    });

    const clientsQuery = useInfiniteQuery<
        components["schemas"]["ConsoleClientListResponse"],
        Error,
        InfiniteData<components["schemas"]["ConsoleClientListResponse"], string | undefined>,
        [
            "tenants-clients",
            string | undefined,
            string | null,
            TenantLifecycleMode,
            FleetLifecycleFilter,
            FleetPaymentFilter,
            FleetServiceFilter,
        ],
        string | undefined
    >({
        queryKey: [
            "tenants-clients",
            clientQueryValue,
            pageFilterCompanyId,
            tenantLifecycle,
            fleetLifecycleFilter,
            fleetPaymentFilter,
            fleetServiceFilter,
        ],
        queryFn: async ({ pageParam }) => {
            const cursor = typeof pageParam === "string" ? pageParam : undefined;
            const response = await adminApi.listClients({
                cursor,
                limit: 20,
                q: clientQueryValue,
                company_id: pageFilterCompanyId ?? undefined,
                lifecycle: tenantLifecycle,
                include_fleet: "true",
                include_summary: cursor ? undefined : "true",
                fleet_lifecycle: fleetLifecycleFilter === "all" ? undefined : fleetLifecycleFilter,
                payment_status: fleetPaymentFilter === "all" ? undefined : fleetPaymentFilter,
                service_state: fleetServiceFilter === "all" ? undefined : fleetServiceFilter,
            });
            return response.data;
        },
        initialPageParam: undefined,
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? lastPage.cursor ?? undefined : undefined,
        enabled: tenantsEnabled,
    });

    const branchesQuery = useInfiniteQuery<
        components["schemas"]["ConsoleBranchListResponse"],
        Error,
        InfiniteData<components["schemas"]["ConsoleBranchListResponse"], string | undefined>,
        ["tenants-branches", string | undefined, string | null, string | null, string | null, TenantLifecycleMode],
        string | undefined
    >({
        queryKey: ["tenants-branches", branchQueryValue, pageFilterCompanyId, pageFilterClientId, pageFilterBranchId, tenantLifecycle],
        queryFn: async ({ pageParam }) => {
            const cursor = typeof pageParam === "string" ? pageParam : undefined;
            const response = await adminApi.listBranches({
                cursor,
                limit: 20,
                q: branchQueryValue,
                company_id: pageFilterCompanyId ?? undefined,
                client_id: pageFilterClientId ?? undefined,
                lifecycle: tenantLifecycle,
            });
            return response.data;
        },
        initialPageParam: undefined,
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? lastPage.cursor ?? undefined : undefined,
        enabled: tenantsEnabled,
    });
    const fleetAttentionQuery = useQuery({
        queryKey: ["tenants-fleet-attention", tenantLifecycle],
        queryFn: async () => {
            const response = await adminApi.listFleetAttention({
                limit: 12,
                stale_after_minutes: 60,
                include_low: "false",
            });
            return response.data;
        },
        enabled: tenantsEnabled && tenantLifecycle === "active" && tenantsPortfolioQuery.isError,
    });
    const branchChangesQuery = useQuery({
        queryKey: ["tenants-branch-changes", branchEditor?.id],
        queryFn: async () => {
            if (!branchEditor?.id) {
                return null;
            }
            const response = await adminApi.listBranchChanges({
                branch_id: branchEditor.id,
                limit: 10,
            });
            return response.data;
        },
        enabled: tenantsEnabled && !!branchEditor?.id,
    });
    const recentBranchChangesKpiQuery = useQuery({
        queryKey: ["tenants-branch-changes-recent-kpi", tenantLifecycle],
        queryFn: async () => {
            const response = await adminApi.listBranchChanges({
                limit: 100,
            });
            return response.data;
        },
        enabled: tenantsEnabled && tenantLifecycle === "active",
    });
    const selectedClientAuditQuery = useQuery({
        queryKey: ["tenants-client-lifecycle-audit-api", pageFilterClientId],
        queryFn: async () => {
            if (!pageFilterClientId) {
                return [];
            }
            const response = await auditApi.list({
                entity_type: "client",
                entity_id: pageFilterClientId,
                limit: 50,
            });
            return response.data.items ?? [];
        },
        enabled: tenantsEnabled && !!pageFilterClientId,
        staleTime: 30000,
    });
    const weeklySnapshotsServerQuery = useQuery({
        queryKey: ["tenants-weekly-snapshots", pageFilterClientId],
        queryFn: async () => {
            if (!pageFilterClientId) {
                return [] as TenantsOperationalSnapshot[];
            }
            const response = await adminApi.listTenantsWeeklySnapshots({
                client_id: pageFilterClientId,
                limit: MAX_WEEKLY_SNAPSHOTS,
            });
            return (response.data.items ?? [])
                .map((item) => mapWeeklySnapshotRecordToViewModel(item))
                .filter((item): item is TenantsOperationalSnapshot => item !== null);
        },
        enabled: tenantsEnabled && !!pageFilterClientId,
        staleTime: 30000,
    });
    useEffect(() => {
        if (!pageFilterClientId) {
            setWeeklySnapshots([]);
            return;
        }
        if (!weeklySnapshotsServerQuery.data) {
            return;
        }
        setWeeklySnapshots(weeklySnapshotsServerQuery.data);
    }, [pageFilterClientId, weeklySnapshotsServerQuery.data]);

    const companies = useMemo(
        () => companiesQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [],
        [companiesQuery.data],
    );
    const clients = useMemo(() => {
        const cockpitItems = tenantsCompanyCockpitQuery.data?.clients.items ?? [];
        if (pageFilterCompanyId && (cockpitItems.length > 0 || tenantsCompanyCockpitQuery.isSuccess)) {
            return cockpitItems;
        }
        const portfolioItems = tenantsPortfolioQuery.data?.clients.items ?? [];
        if (portfolioItems.length > 0 || tenantsPortfolioQuery.isSuccess) {
            return portfolioItems;
        }
        return clientsQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [];
    }, [
        clientsQuery.data,
        pageFilterCompanyId,
        tenantsCompanyCockpitQuery.data?.clients.items,
        tenantsCompanyCockpitQuery.isSuccess,
        tenantsPortfolioQuery.data?.clients.items,
        tenantsPortfolioQuery.isSuccess,
    ]);
    const clientsSummary = useMemo(
        () => tenantsPortfolioQuery.data?.clients.summary ?? clientsQuery.data?.pages[0]?.summary ?? null,
        [clientsQuery.data, tenantsPortfolioQuery.data?.clients.summary],
    );
    const onboardingThroughput = useMemo(
        () => clientsSummary?.onboarding_throughput ?? null,
        [clientsSummary],
    );
    const branches = useMemo(() => {
        const items = branchesQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [];
        if (!pageFilterBranchId) {
            return items;
        }
        return items.filter((branch) => branch.id === pageFilterBranchId);
    }, [branchesQuery.data, pageFilterBranchId]);
    const clientsUsingServerContract = pageFilterCompanyId
        ? tenantsCompanyCockpitQuery.isSuccess
        : tenantsPortfolioQuery.isSuccess;
    const clientCompanyIdById = useMemo(() => {
        const mapping = new Map<string, string>();
        clients.forEach((client) => {
            if (client.id && client.company_id) {
                mapping.set(client.id, client.company_id);
            }
        });
        (meData?.clients ?? []).forEach((client) => {
            if (client.id && client.company_id && !mapping.has(client.id)) {
                mapping.set(client.id, client.company_id);
            }
        });
        return mapping;
    }, [clients, meData?.clients]);
    const branchClientIdById = useMemo(() => {
        const mapping = new Map<string, string>();
        branches.forEach((branch) => {
            if (branch.id) {
                const clientId = readBranchClientId(branch);
                if (clientId) {
                    mapping.set(branch.id, clientId);
                }
            }
        });
        knownBranches.forEach((branch) => {
            if (branch.id && !mapping.has(branch.id)) {
                const clientId = readBranchClientId(branch);
                if (clientId) {
                    mapping.set(branch.id, clientId);
                }
            }
        });
        return mapping;
    }, [branches, knownBranches]);
    const branchCompanyIdById = useMemo(() => {
        const mapping = new Map<string, string>();
        branches.forEach((branch) => {
            if (branch.id) {
                const companyId = readBranchCompanyId(branch);
                if (companyId) {
                    mapping.set(branch.id, companyId);
                }
            }
        });
        knownBranches.forEach((branch) => {
            if (branch.id && !mapping.has(branch.id)) {
                const companyId = readBranchCompanyId(branch);
                if (companyId) {
                    mapping.set(branch.id, companyId);
                }
            }
        });
        return mapping;
    }, [branches, knownBranches]);
    const selectedCompanyName = useMemo(() => {
        if (!selectedCompanyId) {
            return null;
        }
        return (
            companies.find((company) => company.id === selectedCompanyId)?.name
            ?? selectedCompanyNameFromContext
            ?? null
        );
    }, [companies, selectedCompanyId, selectedCompanyNameFromContext]);
    const selectedClientName = useMemo(() => {
        if (!selectedClientId) {
            return null;
        }
        if (meData?.client?.id === selectedClientId && meData.client?.name) {
            return meData.client.name;
        }
        return clients.find((client) => client.id === selectedClientId)?.name ?? null;
    }, [clients, meData?.client?.id, meData?.client?.name, selectedClientId]);
    const selectedBranchName = useMemo(() => {
        if (!selectedBranchId) {
            return null;
        }
        return (
            branches.find((branch) => branch.id === selectedBranchId)?.name
            ?? selectedBranchNameFromContext
            ?? null
        );
    }, [branches, selectedBranchId, selectedBranchNameFromContext]);
    const pageFilterCompanyOptions = useMemo(
        () => toFilterOptions([
            ...knownCompanies.map((company) => ({
                id: company.id,
                label: company.name ?? company.id ?? "",
            })),
            ...companies.map((company) => ({
                id: company.id,
                label: company.name ?? company.id ?? "",
            })),
            {
                id: selectedCompanyId,
                label: selectedCompanyNameFromContext ?? selectedCompanyId ?? "",
            },
        ]),
        [knownCompanies, companies, selectedCompanyId, selectedCompanyNameFromContext],
    );
    const pageFilterClientOptions = useMemo(
        () => toFilterOptions([
            ...clients.map((client) => ({
                id: client.id,
                label: client.name ?? client.slug ?? client.id ?? "",
            })),
            {
                id: meData?.client?.id ?? null,
                label: meData?.client?.name ?? meData?.client?.id ?? "",
            },
            {
                id: selectedClientId,
                label: selectedClientName ?? selectedClientId ?? "",
            },
        ]),
        [clients, meData?.client?.id, meData?.client?.name, selectedClientId, selectedClientName],
    );
    const pageFilterBranchOptions = useMemo(() => {
        const branchItems = branches.map((branch) => ({
            id: branch.id,
            label: branch.name ?? branch.slug ?? branch.id ?? "",
        }));
        return toFilterOptions([
            ...knownBranches.map((branch) => ({
                id: branch.id,
                label: branch.name ?? branch.id ?? "",
            })),
            ...branchItems,
            {
                id: selectedBranchId,
                label: selectedBranchNameFromContext ?? selectedBranchId ?? "",
            },
        ]);
    }, [branches, knownBranches, selectedBranchId, selectedBranchNameFromContext]);
    const activeErrorScope = useMemo(
        () => resolveErrorScopeFromWorkspace(effectiveWorkspaceMode),
        [effectiveWorkspaceMode],
    );
    const visibleInlineErrors = useMemo(() => {
        return inlineErrors.filter((error) => error.scope === "global" || error.scope === activeErrorScope);
    }, [activeErrorScope, inlineErrors]);
    const activeErrorScopeLabel = activeErrorScope;
    const latestPublishedBranchChange = useMemo(() => {
        const items = branchChangesQuery.data?.items ?? [];
        return (
            (items.find((item) => item.status === "published") as BranchChangeRecord | undefined) ?? null
        );
    }, [branchChangesQuery.data]);
    const previewChange = branchChangePreview?.change as BranchChangeRecord | undefined;
    const previewDiffEntries = useMemo(() => {
        const diff = previewChange?.diff_payload;
        if (!diff || typeof diff !== "object") {
            return [] as Array<{ field: string; before: string; after: string }>;
        }
        return Object.entries(diff as Record<string, unknown>).map(([field, rawValue]) => {
            const value = rawValue && typeof rawValue === "object"
                ? (rawValue as Record<string, unknown>)
                : {};
            return {
                field,
                before: JSON.stringify(value.before ?? null),
                after: JSON.stringify(value.after ?? null),
            };
        });
    }, [previewChange]);
    const previewValidationErrors = useMemo(() => {
        const payload = previewChange?.validation_payload;
        if (!payload || typeof payload !== "object") {
            return [] as string[];
        }
        const errors = (payload as Record<string, unknown>).errors;
        if (!Array.isArray(errors)) {
            return [] as string[];
        }
        return errors
            .map((item) => (typeof item === "string" ? item : ""))
            .filter((item) => item.length > 0);
    }, [previewChange]);
    const fleetAttention = useMemo(
        () => tenantsPortfolioQuery.data?.fleet_attention ?? fleetAttentionQuery.data ?? null,
        [fleetAttentionQuery.data, tenantsPortfolioQuery.data?.fleet_attention],
    );
    const fleetAttentionLoading = tenantsPortfolioQuery.isLoading || fleetAttentionQuery.isLoading;
    const fleetAttentionErrored = !fleetAttention && (tenantsPortfolioQuery.isError || fleetAttentionQuery.isError);
    const clientsLoading = tenantsPortfolioQuery.isLoading || clientsQuery.isLoading || tenantsCompanyCockpitQuery.isLoading;
    const clientsErrored = clients.length === 0 && (
        tenantsPortfolioQuery.isError
        || clientsQuery.isError
        || tenantsCompanyCockpitQuery.isError
    );
    const branchesLoading = branchesQuery.isLoading || tenantsCompanyCockpitQuery.isLoading;
    const branchesErrored = branches.length === 0 && (branchesQuery.isError || tenantsCompanyCockpitQuery.isError);
    const recentBranchChangesForKpi = useMemo(
        () => recentBranchChangesKpiQuery.data?.items ?? [],
        [recentBranchChangesKpiQuery.data],
    );
    const selectedClientApiAuditEntries = useMemo(() => {
        const events = selectedClientAuditQuery.data ?? [];
        return events
            .map((event) => mapAuditEventToLifecycleEntry(event))
            .filter((entry): entry is ClientLifecycleAuditEntry => entry !== null);
    }, [selectedClientAuditQuery.data]);
    const operationalKpi = useMemo(() => {
        const summary = clientsSummary;
        const attentionSummary = fleetAttention?.summary;
        const totalClients = summary?.total_clients ?? 0;
        const activeClients = summary?.active_clients ?? 0;
        const onboardingClients = summary?.onboarding_clients ?? 0;
        const goLiveReadyClients = summary?.go_live_ready_clients ?? 0;
        const archivedClients = summary?.archived_clients ?? 0;
        const degradedClients = summary?.degraded_clients ?? 0;

        const totalChanges = recentBranchChangesForKpi.length;
        const publishedChanges = recentBranchChangesForKpi.filter((item) => item.status === "published").length;
        const publishFailedChanges = recentBranchChangesForKpi.filter((item) => item.status === "publish_failed").length;
        const rolledBackChanges = recentBranchChangesForKpi.filter((item) => item.status === "rolled_back").length;

        return {
            onboardingCoveragePct: asPercent(onboardingClients + goLiveReadyClients, totalClients),
            goLiveReadinessPct: asPercent(goLiveReadyClients, onboardingClients + goLiveReadyClients),
            serviceStabilityPct: asPercent(Math.max(activeClients - degradedClients, 0), activeClients),
            decommissionSharePct: asPercent(archivedClients, totalClients),
            changeFailurePct: asPercent(publishFailedChanges, totalChanges),
            rollbackSharePct: asPercent(rolledBackChanges, publishedChanges + rolledBackChanges),
            blockedSignalsCount:
                (attentionSummary?.outbox_failed_24h_total ?? 0)
                + (attentionSummary?.pending_handovers_total ?? 0)
                + publishFailedChanges,
            sourceWindow: totalChanges,
            publishedChanges,
            publishFailedChanges,
            rolledBackChanges,
        };
    }, [clientsSummary, fleetAttention, recentBranchChangesForKpi]);
    const operationalKpiValues = useMemo<Record<OperationalKpiId, number>>(() => ({
        onboardingCoverage: operationalKpi.onboardingCoveragePct,
        goLiveReadiness: operationalKpi.goLiveReadinessPct,
        serviceStability: operationalKpi.serviceStabilityPct,
        decommissionShare: operationalKpi.decommissionSharePct,
        changeFailure: operationalKpi.changeFailurePct,
        rollbackShare: operationalKpi.rollbackSharePct,
        blockedSignals: operationalKpi.blockedSignalsCount,
    }), [operationalKpi]);
    const operationalKpiDrilldown = useMemo(
        () => buildOperationalKpiDrilldown(operationalKpiValues),
        [operationalKpiValues],
    );
    const operationalKpiById = useMemo(() => {
        const map = new Map<OperationalKpiId, OperationalKpiDrilldown>();
        for (const item of operationalKpiDrilldown) {
            map.set(item.id, item);
        }
        return map;
    }, [operationalKpiDrilldown]);
    const criticalKpiCount = useMemo(
        () => operationalKpiDrilldown.filter((item) => item.status === "critical").length,
        [operationalKpiDrilldown],
    );
    const warnKpiCount = useMemo(
        () => operationalKpiDrilldown.filter((item) => item.status === "warn").length,
        [operationalKpiDrilldown],
    );
    const alertHookPayload = useMemo(() => {
        const breaches = operationalKpiDrilldown
            .filter((item) => item.status !== "ok")
            .map((item) => ({
                metric: item.id,
                label: item.label,
                status: item.status,
                value: item.value,
                reason: item.reason,
                action: item.action,
            }));
        const severity = breaches.some((item) => item.status === "critical")
            ? "critical"
            : breaches.length > 0
                ? "warning"
                : "ok";
        return {
            generated_at: new Date().toISOString(),
            severity,
            source_window: operationalKpi.sourceWindow,
            breaches,
            attention_summary: {
                active_clients_total: fleetAttention?.summary?.active_clients_total ?? 0,
                high_risk_clients: fleetAttention?.summary?.high_risk_clients ?? 0,
                medium_risk_clients: fleetAttention?.summary?.medium_risk_clients ?? 0,
                outbox_failed_24h_total: fleetAttention?.summary?.outbox_failed_24h_total ?? 0,
                pending_handovers_total: fleetAttention?.summary?.pending_handovers_total ?? 0,
            },
        };
    }, [operationalKpiDrilldown, operationalKpi.sourceWindow, fleetAttention?.summary]);
    const operationalReport = useMemo<TenantsOperationalSnapshotPayload>(() => ({
        generatedAt: new Date().toISOString(),
        sourceWindow: operationalKpi.sourceWindow,
        workspaceMode: effectiveWorkspaceMode,
        lifecycleMode: tenantLifecycle,
        kpi: operationalKpiValues,
        drilldown: operationalKpiDrilldown.map((item) => ({
            id: item.id,
            status: item.status,
            value: item.value,
            reason: item.reason,
        })),
        attentionSummary: {
            activeClientsTotal: fleetAttention?.summary?.active_clients_total ?? 0,
            highRiskClients: fleetAttention?.summary?.high_risk_clients ?? 0,
            mediumRiskClients: fleetAttention?.summary?.medium_risk_clients ?? 0,
            outboxFailed24hTotal: fleetAttention?.summary?.outbox_failed_24h_total ?? 0,
            pendingHandoversTotal: fleetAttention?.summary?.pending_handovers_total ?? 0,
        },
    }), [operationalKpi.sourceWindow, operationalKpiValues, operationalKpiDrilldown, fleetAttention?.summary, effectiveWorkspaceMode, tenantLifecycle]);

    const refreshContext = () => {
        queryClient.invalidateQueries({ queryKey: ["console-me"] });
    };

    const refreshTenants = () => {
        queryClient.invalidateQueries({ queryKey: ["tenants-companies"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-clients"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-branches"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-fleet-attention"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-branch-changes-recent-kpi"] });
        queryClient.invalidateQueries({ queryKey: ["tenants-client-lifecycle-audit-api"] });
    };
    const auditSensitiveAccess = async (input: {
        branchId: string;
        field: "instance_id";
        action: TenantsSensitiveAction;
        contextScope?: string;
    }) => {
        try {
            await adminApi.auditTenantsSensitiveAccess({
                branch_id: input.branchId,
                field: input.field,
                action: input.action,
                context: input.contextScope,
            });
        } catch (error) {
            reportError(error, { scope: "changes" });
            throw error;
        }
    };

    const completeContextScope = (scope: { companyId?: string | null; clientId?: string | null; branchId?: string | null }) => {
        const normalizedBranchId = normalizeOptionalId(scope.branchId);
        let normalizedClientId = normalizeOptionalId(scope.clientId);
        let normalizedCompanyId = normalizeOptionalId(scope.companyId);
        if (normalizedBranchId) {
            const branchClientId = branchClientIdById.get(normalizedBranchId);
            if (!normalizedClientId && branchClientId) {
                normalizedClientId = branchClientId;
            }
            if (!normalizedCompanyId) {
                const branchCompanyId = branchCompanyIdById.get(normalizedBranchId);
                if (branchCompanyId) {
                    normalizedCompanyId = branchCompanyId;
                }
            }
        }
        if (!normalizedCompanyId && normalizedClientId) {
            normalizedCompanyId = clientCompanyIdById.get(normalizedClientId) ?? null;
        }
        return {
            companyId: normalizedCompanyId,
            clientId: normalizedClientId,
            branchId: normalizedBranchId,
        };
    };

    const writeContextScope = (scope: { companyId?: string | null; clientId?: string | null; branchId?: string | null }) => {
        const normalized = completeContextScope(scope);
        setConsoleContextScope({
            companyId: normalized.companyId ?? "",
            clientId: normalized.clientId ?? "",
            branchId: normalized.branchId ?? "",
        });
        refreshContext();
        return normalized;
    };

    const setCompanyContext = (companyId?: string | null) => {
        writeContextScope({
            companyId,
            clientId: null,
            branchId: null,
        });
    };

    const setClientContext = (clientId?: string | null, companyId?: string | null) => {
        const storedScope = readConsoleContextScopeFromStorage();
        writeContextScope({
            companyId: companyId ?? storedScope.companyId,
            clientId,
            branchId: null,
        });
    };

    const setBranchContext = (branchId?: string | null) => {
        const storedScope = readConsoleContextScopeFromStorage();
        writeContextScope({
            companyId: storedScope.companyId,
            clientId: storedScope.clientId,
            branchId,
        });
    };
    const clearContextLens = () => {
        setCompanyContext(null);
    };
    const setClientContextAndPageFilters = (clientId?: string | null, companyId?: string | null) => {
        const nextScope = writeContextScope({
            companyId,
            clientId,
            branchId: null,
        });
        applyScopeToPageFilters(nextScope);
    };
    const setBranchContextAndPageFilters = (branchId?: string | null) => {
        const storedScope = readConsoleContextScopeFromStorage();
        const nextScope = writeContextScope({
            companyId: pageFilterCompanyId ?? storedScope.companyId,
            clientId: pageFilterClientId ?? storedScope.clientId,
            branchId: branchId ?? null,
        });
        applyScopeToPageFilters(nextScope);
    };
    const applyContextToPageFilters = () => {
        const storedScope = readConsoleContextScopeFromStorage();
        const nextScope = completeContextScope(storedScope);
        applyScopeToPageFilters(nextScope);
        if (
            (nextScope.companyId ?? "") !== storedScope.companyId
            || (nextScope.clientId ?? "") !== storedScope.clientId
            || (nextScope.branchId ?? "") !== storedScope.branchId
        ) {
            setConsoleContextScope({
                companyId: nextScope.companyId ?? "",
                clientId: nextScope.clientId ?? "",
                branchId: nextScope.branchId ?? "",
            });
            refreshContext();
        }
    };

    const handleQuickCreateCompany = async () => {
        const companyName = quickCreateForm.companyName.trim();
        if (!companyName) {
            reportValidationError("Укажите название компании");
            return;
        }
        setQuickCreateRunning("company");
        try {
            const response = await adminApi.createCompany({ name: companyName });
            const companyId = response.data.company?.id;
            if (!companyId) {
                reportValidationError("Компания создана, но company_id не вернулся");
                return;
            }
            setQuickCreateForm((prev) => ({
                ...prev,
                companyId,
                companyName,
            }));
            setCompanyContext(companyId);
            refreshTenants();
            toast.success("Компания создана");
        } catch (error) {
            reportProvisioningError(error, "создание компании", "POST /api/proxy/admin/companies");
        } finally {
            setQuickCreateRunning(null);
        }
    };

    const handleQuickCreateClient = async () => {
        const slug = quickCreateForm.clientSlug.trim().toLowerCase();
        const companyId = quickCreateCompanyId;
        if (!companyId) {
            reportValidationError("Сначала выберите или создайте компанию");
            return;
        }
        if (!slug) {
            reportValidationError("Укажите slug клиента");
            return;
        }
        if (!SLUG_INPUT_PATTERN.test(slug)) {
            reportValidationError("slug: [a-z0-9_-], без пробелов");
            return;
        }
        setQuickCreateRunning("client");
        try {
            const response = await adminApi.createClient({
                slug,
                company_id: companyId,
                status: null,
            });
            const clientId = response.data.client?.id;
            if (!clientId) {
                reportValidationError("Клиент создан, но client_id не вернулся");
                return;
            }
            setQuickCreateForm((prev) => ({
                ...prev,
                clientSlug: slug,
                companyId,
                clientId,
            }));
            setClientContextAndPageFilters(clientId, companyId);
            refreshTenants();
            toast.success("Клиент создан");
        } catch (error) {
            reportProvisioningError(error, "создание клиента", "POST /api/proxy/admin/clients");
        } finally {
            setQuickCreateRunning(null);
        }
    };

    const handleQuickCreateBranch = async () => {
        const clientId = quickCreateClientId;
        const branchName = quickCreateForm.branchName.trim();
        const branchSlug = quickCreateForm.branchSlug.trim().toLowerCase();
        const timezone = quickCreateForm.branchTimezone.trim();
        const phone = quickCreateForm.branchPhone.trim();
        const instanceId = quickCreateForm.branchInstanceId.trim();
        if (!clientId) {
            reportValidationError("Сначала выберите или создайте клиента");
            return;
        }
        if (!branchName || !branchSlug) {
            reportValidationError("Укажите название и slug филиала");
            return;
        }
        if (!SLUG_INPUT_PATTERN.test(branchSlug)) {
            reportValidationError("branch slug: [a-z0-9_-], без пробелов");
            return;
        }
        if (timezone && !isValidTimezoneName(timezone)) {
            reportValidationError("timezone должен быть в формате IANA, например Asia/Almaty");
            return;
        }
        if (phone && !BRANCH_PHONE_INPUT_PATTERN.test(phone)) {
            reportValidationError("phone: 7-15 цифр (допускаются +, пробелы, скобки и -)");
            return;
        }
        if (instanceId && !phone) {
            reportValidationError("Для instance_id укажите phone филиала");
            return;
        }
        setQuickCreateRunning("branch");
        try {
            const response = await adminApi.createBranch({
                client_id: clientId,
                name: branchName,
                slug: branchSlug,
                timezone: timezone || undefined,
                phone: phone || undefined,
                instance_id: instanceId || undefined,
                is_active: Boolean(phone && instanceId),
                bootstrap_accounts: [],
            });
            const branchId = response.data.branch?.id;
            if (!branchId) {
                reportValidationError("Филиал создан, но branch_id не вернулся");
                return;
            }
            setBranchContextAndPageFilters(branchId);
            refreshTenants();
            toast.success("Филиал создан и выбран в контексте");
        } catch (error) {
            reportProvisioningError(error, "создание филиала", "POST /api/proxy/admin/branches");
        } finally {
            setQuickCreateRunning(null);
        }
    };

    const openClientContextTarget = (target: "/" | "/integrations" | "/ops", clientId?: string | null, companyId?: string | null) => {
        if (!clientId) {
            return;
        }
        setClientContextAndPageFilters(clientId, companyId);
        router.push(target);
    };

    const runActionQueueIntent = (item: ActionQueueItem) => {
        if (item.intent === "set_context") {
            setClientContextAndPageFilters(item.clientId, item.companyId);
            return;
        }
        if (item.intent === "open_cases") {
            openClientContextTarget("/", item.clientId, item.companyId);
            return;
        }
        if (item.intent === "open_integrations") {
            openClientContextTarget("/integrations", item.clientId, item.companyId);
            return;
        }
        if (item.intent === "workspace_portfolio") {
            setWorkspaceMode("portfolio");
            return;
        }
        if (item.intent === "workspace_onboarding") {
            setWorkspaceMode("onboarding");
            return;
        }
        if (item.intent === "workspace_changes") {
            setWorkspaceMode("changes");
            return;
        }
        if (item.intent === "workspace_decommission") {
            setWorkspaceMode("decommission");
        }
    };

    const runKpiAction = (action: OperationalKpiAction) => {
        if (action === "onboarding") {
            setWorkspaceMode("onboarding");
            setTenantLifecycle("active");
            setTimeout(() => {
                document.querySelector('[data-testid="tenants-onboarding-section"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 120);
            return;
        }
        if (action === "changes") {
            setWorkspaceMode("changes");
            setTenantLifecycle("active");
            setTimeout(() => {
                document.querySelector('[data-testid="tenants-change-management"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 120);
            return;
        }
        if (action === "decommission") {
            setWorkspaceMode("decommission");
            setTenantLifecycle("all");
            setTimeout(() => {
                document.querySelector('[data-testid="tenants-decommission-center"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
            }, 120);
            return;
        }
        setWorkspaceMode("portfolio");
        setTenantLifecycle("active");
        setTimeout(() => {
            document.querySelector('[data-testid="tenants-fleet-attention"]')?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 120);
    };

    const exportOperationalReport = (format: "json" | "csv") => {
        const timestamp = new Date().toISOString().replaceAll(":", "-");
        if (format === "json") {
            const content = JSON.stringify(
                {
                    report: operationalReport,
                    alert_payload: alertHookPayload,
                },
                null,
                2,
            );
            const blob = new Blob([content], { type: "application/json;charset=utf-8" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `tenants-operational-report-${timestamp}.json`;
            link.click();
            URL.revokeObjectURL(url);
            toast.success("Отчёт JSON выгружен");
            return;
        }
        const rows = [
            ["metric", "value", "status", "reason"],
            ...operationalKpiDrilldown.map((item) => [
                item.id,
                item.displayValue,
                item.status,
                item.reason,
            ]),
        ];
        const csvContent = rows.map((row) => row.map((cell) => toCsvCell(cell)).join(",")).join("\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `tenants-operational-report-${timestamp}.csv`;
        link.click();
        URL.revokeObjectURL(url);
        toast.success("Отчёт CSV выгружен");
    };

    const saveWeeklySnapshot = async () => {
        if (!pageFilterClientId) {
            reportValidationError("Сначала выберите клиента в фильтрах страницы", "VALIDATION_ERROR", "portfolio");
            return;
        }
        const now = new Date().toISOString();
        const weekKey = toIsoWeekKey(now);
        const localSnapshot: TenantsOperationalSnapshot = {
            id: typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
                ? crypto.randomUUID()
                : `${Date.now()}`,
            weekKey,
            createdAt: now,
            report: operationalReport,
        };
        const applySnapshot = (snapshot: TenantsOperationalSnapshot) => {
            setWeeklySnapshots((previous) => {
                const withoutWeek = previous.filter((item) => item.weekKey !== snapshot.weekKey);
                return [snapshot, ...withoutWeek].slice(0, MAX_WEEKLY_SNAPSHOTS);
            });
        };
        try {
            const response = await adminApi.saveTenantsWeeklySnapshot({
                client_id: pageFilterClientId,
                week_key: weekKey,
                snapshot: operationalReport,
            });
            const mappedSnapshot = mapWeeklySnapshotRecordToViewModel(response.data.item);
            applySnapshot(mappedSnapshot ?? localSnapshot);
                queryClient.invalidateQueries({
                    queryKey: ["tenants-weekly-snapshots", pageFilterClientId],
                });
            toast.success(`Недельный снимок сохранён (${weekKey})`);
        } catch (error) {
            reportError(error, { scope: "portfolio" });
            toast.error(`Не удалось сохранить недельный снимок (${weekKey})`);
        }
    };

    const copyAlertHookPayload = async () => {
        const serialized = JSON.stringify(alertHookPayload, null, 2);
        try {
            await navigator.clipboard.writeText(serialized);
            toast.success("Alert payload скопирован");
        } catch {
            reportValidationError("Не удалось скопировать payload");
        }
    };

    const runMetricsSnapshotHook = async (mode: "dry_run" | "execute") => {
        if (!pageFilterClientId) {
            reportValidationError("Сначала выберите клиента в фильтрах страницы");
            return;
        }
        setRunningMetricsSnapshotMode(mode);
        try {
            const response = await opsApi.runJob({
                job_type: "metrics_snapshot",
                mode,
                params: ({ days: 7 } as unknown as Record<string, never>),
            });
            setLastMetricsSnapshotJob(response.data.job);
            toast.success(mode === "dry_run" ? "Пробный снимок метрик выполнен" : "Снимок метрик выполнен");
        } catch (error) {
            reportError(error, { scope: resolveErrorScopeFromWorkspace(effectiveWorkspaceMode) });
        } finally {
            setRunningMetricsSnapshotMode(null);
        }
    };

    const startCompanyEdit = (company: components["schemas"]["ConsoleCompany"]) => {
        if (!company.id) {
            reportValidationError("Не удалось открыть компанию без ID");
            return;
        }
        setClientLifecycleDraft(null);
        setBranchChangePreview(null);
        setClientEditor(null);
        setBranchEditor(null);
        const billingInfo = stringifyOptionalJson(company.billing_info);
        setCompanyEditor({
            id: company.id,
            name: company.name ?? "",
            billingInfo,
            originalName: company.name ?? "",
            originalBillingInfo: billingInfo,
        });
    };

    const startClientEdit = (client: components["schemas"]["ConsoleClient"]) => {
        if (!client.id) {
            reportValidationError("Не удалось открыть клиента без ID");
            return;
        }
        setClientLifecycleDraft(null);
        setBranchChangePreview(null);
        setCompanyEditor(null);
        setBranchEditor(null);
        setClientEditor({
            id: client.id,
            slug: client.slug ?? client.name ?? "",
            companyId: client.company_id ?? "",
            originalSlug: client.slug ?? client.name ?? "",
            originalCompanyId: client.company_id ?? "",
            totalBranches: client.total_branches ?? 0,
        });
    };

    const startBranchEdit = (branch: components["schemas"]["ConsoleBranch"]) => {
        if (!branch.id) {
            reportValidationError("Не удалось открыть филиал без ID");
            return;
        }
        setClientLifecycleDraft(null);
        setBranchChangePreview(null);
        setCompanyEditor(null);
        setClientEditor(null);
        setBranchEditor({
            id: branch.id,
            name: branch.name ?? "",
            slug: branch.slug ?? "",
            timezone: branch.timezone ?? "",
            phone: branch.phone ?? "",
            instanceId: branch.instance_id ?? "",
            telegramChatId: branch.telegram_chat_id ?? "",
            knowledgeTag: branch.knowledge_tag ?? "",
            isActive: branch.is_active ?? false,
            changeReason: "",
            confirmReason: "",
            rollbackReason: "",
            original: {
                name: branch.name ?? "",
                slug: branch.slug ?? "",
                timezone: branch.timezone ?? "",
                phone: branch.phone ?? "",
                instanceId: branch.instance_id ?? "",
                telegramChatId: branch.telegram_chat_id ?? "",
                knowledgeTag: branch.knowledge_tag ?? "",
                isActive: branch.is_active ?? false,
            },
        });
    };

    const handleSaveCompany = async () => {
        if (!companyEditor) {
            return;
        }
        const name = companyEditor.name.trim();
        if (!name) {
            reportValidationError("Укажите название компании");
            return;
        }
        const billing = parseOptionalJson(companyEditor.billingInfo, "billing_info");
        if (billing.error) {
            reportValidationError(billing.error);
            return;
        }
        const payload: components["schemas"]["ConsoleCompanyUpdateRequest"] = {};
        if (name !== companyEditor.originalName) {
            payload.name = name;
        }
        if (companyEditor.billingInfo.trim() !== companyEditor.originalBillingInfo.trim()) {
            payload.billing_info = (billing.value ?? {}) as Record<string, never>;
        }
        if (Object.keys(payload).length === 0) {
            toast("Нет изменений");
            return;
        }
        setSavingCompany(true);
        try {
            await adminApi.patchCompany(companyEditor.id, payload);
            toast.success("Компания обновлена");
            setCompanyEditor(null);
            refreshTenants();
            refreshContext();
        } catch (error) {
            reportProvisioningError(error, "обновление компании", "PATCH /api/proxy/admin/companies/:id");
        } finally {
            setSavingCompany(false);
        }
    };

    const handleSaveClient = async () => {
        if (!clientEditor) {
            return;
        }
        const slug = clientEditor.slug.trim();
        if (!slug) {
            reportValidationError("Укажите slug клиента");
            return;
        }
        if (!SLUG_INPUT_PATTERN.test(slug)) {
            reportValidationError("slug: [a-z0-9_-], без пробелов");
            return;
        }
        const payload: components["schemas"]["ConsoleClientUpdateRequest"] = {};
        if (slug !== clientEditor.originalSlug) {
            payload.slug = slug;
        }
        const companyId = clientEditor.companyId.trim();
        const companyLocked = clientEditor.totalBranches > 0 && !!clientEditor.originalCompanyId;
        if (companyLocked && companyId !== clientEditor.originalCompanyId) {
            reportValidationError("company_id нельзя менять после создания филиалов");
            return;
        }
        if (companyId !== clientEditor.originalCompanyId) {
            payload.company_id = companyId || null;
        }
        if (Object.keys(payload).length === 0) {
            toast("Нет изменений");
            return;
        }
        setSavingClient(true);
        try {
            await adminApi.patchClient(clientEditor.id, payload);
            toast.success("Клиент обновлён");
            setClientEditor(null);
            refreshTenants();
            refreshContext();
        } catch (error) {
            reportProvisioningError(error, "обновление клиента", "PATCH /api/proxy/admin/clients/:id");
        } finally {
            setSavingClient(false);
        }
    };

    const isClientArchived = (client: components["schemas"]["ConsoleClient"]) => {
        const lifecycleValue = (client.lifecycle_state ?? "").trim().toLowerCase();
        if (lifecycleValue) {
            return lifecycleValue === "archived";
        }
        return (client.status ?? "").trim().toLowerCase() !== "active";
    };

    const openClientLifecycleAction = (
        client: components["schemas"]["ConsoleClient"],
        mode: ClientLifecycleMode,
    ) => {
        if (!client.id) {
            reportValidationError("Не удалось выполнить действие без ID клиента");
            return;
        }
        setClientLifecycleDraft({
            clientId: client.id,
            clientLabel: client.name ?? client.slug ?? client.id,
            companyLabel: client.company_name ?? "—",
            mode,
            currentLifecycleLabel: formatStateLabel(client.lifecycle_state, FLEET_LIFECYCLE_LABELS),
            targetLifecycleLabel: mode === "archive" ? FLEET_LIFECYCLE_LABELS.archived : FLEET_LIFECYCLE_LABELS.active,
            activeBranches: client.active_branches ?? 0,
            totalBranches: client.total_branches ?? 0,
            degradedBranches: client.degraded_branches ?? 0,
            reason: "",
            confirmChecked: false,
            checkClientScope: false,
            checkImpactReview: false,
            checkOwnerAligned: false,
        });
    };

    const closeClientLifecycleDraft = () => {
        if (clientLifecyclePendingId) {
            return;
        }
        setClientLifecycleDraft(null);
    };

    const handleClientLifecycleAction = async () => {
        if (!clientLifecycleDraft) {
            reportValidationError("Сначала подготовьте действие");
            return;
        }
        const lifecycleDraft = clientLifecycleDraft;
        const clientId = lifecycleDraft.clientId;
        if (!clientId) {
            reportValidationError("Не удалось выполнить действие без ID клиента");
            return;
        }
        const reason = clientLifecycleDraft.reason.trim();
        if (!reason) {
            reportValidationError("Укажите причину");
            return;
        }
        if (!clientLifecycleDraft.confirmChecked) {
            reportValidationError("Подтвердите действие");
            return;
        }
        if (
            !clientLifecycleDraft.checkClientScope
            || !clientLifecycleDraft.checkImpactReview
            || !clientLifecycleDraft.checkOwnerAligned
        ) {
            reportValidationError("Заполните checklist перед выполнением действия");
            return;
        }
        const mode = lifecycleDraft.mode;
        setClientLifecyclePendingId(clientId);
        let lifecycleCompleted = false;
        try {
            if (mode === "archive") {
                await adminApi.archiveClient(clientId, { reason });
                toast.success("Клиент архивирован");
            } else {
                await adminApi.restoreClient(clientId, { reason });
                toast.success("Клиент восстановлен");
            }
            lifecycleCompleted = true;
            setClientLifecycleAuditById((prev) => pushLifecycleAuditEntry(prev, {
                    clientId,
                    mode,
                    previousLifecycleLabel: lifecycleDraft.currentLifecycleLabel,
                    targetLifecycleLabel: lifecycleDraft.targetLifecycleLabel,
                    reason,
                    status: "success",
                    message: mode === "archive" ? "Архивация подтверждена API" : "Восстановление подтверждено API",
                    actorLabel: meData?.agent?.name ?? role,
                    happenedAt: new Date().toISOString(),
                    source: "session",
                }));
            if (clientEditor?.id === clientId) {
                setClientEditor(null);
            }
            refreshTenants();
            refreshContext();
        } catch (error) {
            const parsed = reportProvisioningError(
                error,
                mode === "archive" ? "архивация клиента" : "восстановление клиента",
                mode === "archive"
                    ? "POST /api/proxy/admin/clients/:id/archive"
                    : "POST /api/proxy/admin/clients/:id/restore",
            ) as
                | { message?: string; trace_id?: string }
                | undefined;
            setClientLifecycleAuditById((prev) => pushLifecycleAuditEntry(prev, {
                    clientId,
                    mode,
                    previousLifecycleLabel: lifecycleDraft.currentLifecycleLabel,
                    targetLifecycleLabel: lifecycleDraft.targetLifecycleLabel,
                    reason,
                    status: "error",
                    message: parsed?.message ?? "Ошибка выполнения lifecycle-действия",
                    traceId: parsed?.trace_id,
                    actorLabel: meData?.agent?.name ?? role,
                    happenedAt: new Date().toISOString(),
                    source: "session",
                }));
        } finally {
            setClientLifecyclePendingId(null);
            if (lifecycleCompleted) {
                setClientLifecycleDraft(null);
            }
        }
    };

    const requiresBranchConfirmation = (editor: BranchEditorState) => {
        const removedInstance = editor.original.instanceId && !editor.instanceId.trim();
        const deactivated = editor.original.isActive && !editor.isActive;
        return removedInstance || deactivated;
    };

    const createBranchDeactivateConfirmation = async (branchId: string, reason: string) => {
        const confirmation = await confirmationsApi.create({
            action: "branch_deactivate",
            target_type: "branch",
            target_id: branchId,
            reason,
        });
        return confirmation.data.confirmation_id;
    };

    const handlePreviewBranchChange = async () => {
        if (!branchEditor) {
            return;
        }
        const reason = branchEditor.changeReason.trim();
        if (!reason) {
            reportValidationError("Укажите причину изменения");
            return;
        }
        const { patch, hasChanges, error } = buildBranchChangePatch(branchEditor);
        if (error) {
            reportValidationError(error);
            return;
        }
        if (!hasChanges) {
            toast("Нет изменений");
            return;
        }
        setSavingBranch(true);
        try {
            const draftResponse = await adminApi.draftBranchChange({
                branch_id: branchEditor.id,
                reason,
                patch,
            });
            const draftChangeId = draftResponse.data.change?.id;
            if (!draftChangeId) {
                reportValidationError("Не удалось создать черновик");
                return;
            }
            const validateResponse = await adminApi.validateBranchChange(draftChangeId);
            setBranchChangePreview(validateResponse.data);
            const status = validateResponse.data.change?.status;
            if (status === "validated") {
                toast.success("Черновик прошел проверку. Можно применять.");
            } else {
                reportValidationError("Черновик не прошел проверку. Исправьте ошибки.");
            }
            await branchChangesQuery.refetch();
        } catch (error) {
            reportProvisioningError(
                error,
                "черновик и валидация изменения филиала",
                "POST /api/proxy/admin/branch-changes + /validate",
            );
        } finally {
            setSavingBranch(false);
        }
    };

    const handlePublishBranchChange = async () => {
        if (!branchEditor) {
            return;
        }
        const changeId = branchChangePreview?.change?.id;
        if (!changeId) {
            reportValidationError("Сначала подготовьте и проверьте черновик");
            return;
        }
        setPublishingBranchChange(true);
        try {
            let confirmationId: string | undefined;
            if (requiresBranchConfirmation(branchEditor)) {
                const confirmationReason = branchEditor.confirmReason.trim() || branchEditor.changeReason.trim();
                if (!confirmationReason) {
                    reportValidationError("Укажите причину подтверждения");
                    return;
                }
                confirmationId = await createBranchDeactivateConfirmation(branchEditor.id, confirmationReason);
            }
            const publishResponse = await adminApi.publishBranchChange(changeId, {
                confirmation_id: confirmationId,
            });
            setBranchChangePreview(publishResponse.data);
            setBranchEditor((prev) => (prev ? applyBranchSnapshotToEditor(prev, publishResponse.data.branch) : prev));
            toast.success("Изменение опубликовано");
            await branchChangesQuery.refetch();
            refreshTenants();
            refreshContext();
        } catch (error) {
            reportProvisioningError(error, "публикация изменения филиала", "POST /api/proxy/admin/branch-changes/:id/publish");
        } finally {
            setPublishingBranchChange(false);
        }
    };

    const handleRollbackBranchChange = async () => {
        if (!branchEditor) {
            return;
        }
        const targetChange = branchChangePreview?.change?.status === "published"
            ? branchChangePreview.change
            : latestPublishedBranchChange;
        const changeId = targetChange?.id;
        if (!changeId) {
            reportValidationError("Нет примененного изменения для отката");
            return;
        }
        const reason = branchEditor.rollbackReason.trim();
        if (!reason) {
            reportValidationError("Укажите причину отката");
            return;
        }

        setRollingBackBranchChange(true);
        try {
            const runRollback = async (confirmationId?: string) =>
                adminApi.rollbackBranchChange(changeId, {
                    reason,
                    confirmation_id: confirmationId,
                });

            let rollbackResponse;
            try {
                rollbackResponse = await runRollback();
            } catch (error: unknown) {
                const apiCode = (error as { response?: { data?: { error?: { code?: string } } } })
                    ?.response?.data?.error?.code;
                if (apiCode !== "CONFIRMATION_REQUIRED") {
                    throw error;
                }
                const confirmationReason = branchEditor.confirmReason.trim() || reason;
                const confirmationId = await createBranchDeactivateConfirmation(branchEditor.id, confirmationReason);
                rollbackResponse = await runRollback(confirmationId);
            }

            setBranchChangePreview(rollbackResponse.data);
            setBranchEditor((prev) => (prev ? applyBranchSnapshotToEditor(prev, rollbackResponse.data.branch) : prev));
            toast.success("Откат выполнен");
            await branchChangesQuery.refetch();
            refreshTenants();
            refreshContext();
        } catch (error) {
            reportProvisioningError(error, "откат изменения филиала", "POST /api/proxy/admin/branch-changes/:id/rollback");
        } finally {
            setRollingBackBranchChange(false);
        }
    };

    const actionQueue = useMemo<ActionQueueItem[]>(() => {
        if (tenantLifecycle !== "active") {
            return [
                {
                    id: "lifecycle-mode-tip",
                    priority: "low",
                    title: "Фокус на архиве",
                    detail: "Для операционной очереди переключите режим списка на «Активные».",
                    intent: "workspace_portfolio",
                    actionLabel: "Открыть портфель",
                },
            ];
        }

        const items: ActionQueueItem[] = [];
        const attentionItems = fleetAttention?.items ?? [];
        const attentionTop = attentionItems.slice(0, 4);

        attentionTop.forEach((item) => {
            const defaultIntent: ActionQueueIntent = item.pending_handovers > 0 ? "open_cases" : "open_integrations";
            const defaultActionLabel = item.pending_handovers > 0 ? "Открыть заявки" : "Открыть интеграции";
            items.push({
                id: `attention-${item.client_id}`,
                priority: item.attention_level as FleetAttentionLevel,
                title: `${item.client_name ?? item.client_slug} · score ${item.attention_score}`,
                detail: `Следующее действие: ${item.next_action}. Причины: ${item.reasons?.slice(0, 2).join(", ") || "—"}`,
                intent: defaultIntent,
                actionLabel: defaultActionLabel,
                clientId: item.client_id,
                companyId: item.company_id ?? null,
            });
        });

        const pendingHandoversTotal = fleetAttention?.summary?.pending_handovers_total ?? 0;
        if (pendingHandoversTotal > 0) {
            items.push({
                id: "summary-pending-handovers",
                priority: pendingHandoversTotal > 10 ? "high" : "medium",
                title: `Ожидают передачи менеджеру: ${pendingHandoversTotal}`,
                detail: "Проверьте очередь HANDOFF и обработайте блокирующие кейсы.",
                intent: "workspace_portfolio",
                actionLabel: "Открыть риск-панель",
            });
        }

        if (operationalKpi.publishFailedChanges > 0) {
            items.push({
                id: "summary-publish-failed",
                priority: operationalKpi.publishFailedChanges >= 3 ? "high" : "medium",
                title: `Ошибки публикации изменений: ${operationalKpi.publishFailedChanges}`,
                detail: "Нужен разбор причин перед следующими publish/rollback.",
                intent: "workspace_changes",
                actionLabel: "Открыть Change Management",
            });
        }

        if ((clientsSummary?.onboarding_clients ?? 0) > 0 && operationalKpi.goLiveReadinessPct < 80) {
            items.push({
                id: "summary-go-live-readiness",
                priority: operationalKpi.goLiveReadinessPct < 60 ? "high" : "medium",
                title: `Go-Live readiness: ${operationalKpi.goLiveReadinessPct}%`,
                detail: "Есть филиалы в онбординге без закрытых обязательных критериев.",
                intent: "workspace_onboarding",
                actionLabel: "Открыть Onboarding",
            });
        }

        if ((clientsSummary?.archived_clients ?? 0) > 0 && operationalKpi.decommissionSharePct > 20) {
            items.push({
                id: "summary-decommission-share",
                priority: "low",
                title: `Доля decommission: ${operationalKpi.decommissionSharePct}%`,
                detail: "Проверьте архивные клиенты и восстановите тех, кто готов вернуться в актив.",
                intent: "workspace_decommission",
                actionLabel: "Открыть Decommission",
            });
        }

        if (items.length === 0) {
            items.push({
                id: "queue-healthy",
                priority: "low",
                title: "Операционная очередь пуста",
                detail: "Критичных/важных блокеров не найдено. Можно продолжать плановый онбординг.",
                intent: "workspace_onboarding",
                actionLabel: "Открыть Onboarding",
            });
        }

        const priorityOrder: Record<FleetAttentionLevel, number> = { high: 0, medium: 1, low: 2 };
        return items
            .sort((left, right) => priorityOrder[left.priority] - priorityOrder[right.priority])
            .slice(0, 8);
    }, [tenantLifecycle, fleetAttention, operationalKpi, clientsSummary]);

    const showPortfolio = effectiveWorkspaceMode === "portfolio";
    const showOnboarding = effectiveWorkspaceMode === "onboarding";
    const showChangeManagement = effectiveWorkspaceMode === "changes";
    const showDecommission = effectiveWorkspaceMode === "decommission";
    const showClientsSection = showPortfolio || showDecommission;
    const decommissionFocused = effectiveWorkspaceMode === "decommission";

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра вкладки «Тенанты».
            </div>
        );
    }

    if (meLoading) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Загрузка роли...
            </div>
        );
    }

    if (!canReadTenants) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к вкладке Тенанты." />
        );
    }

    return (
        <div className="max-w-5xl mx-auto p-6" data-testid="tenants-page">
            <div className="flex flex-col gap-2 mb-6">
                {!controlTowerEnabled ? (
                    <div className="rounded-lg border border-amber-300/60 bg-amber-50 p-3 text-xs text-amber-900" data-testid="tenants-control-tower-flag-banner">
                        `TENANTS_V3_CONTROL_TOWER=0`: включён базовый режим Tenants без расширенной control-tower панели.
                    </div>
                ) : null}
                <TenantsTopControls
                    isPlatformPreset={isPlatformPreset}
                    contextCompanyName={selectedCompanyName}
                    contextClientName={selectedClientName}
                    contextBranchName={selectedBranchName}
                    contextCompanyId={selectedCompanyId}
                    contextClientId={selectedClientId}
                    contextBranchId={selectedBranchId}
                    onClearBranchContext={() => setBranchContext(null)}
                    onClearClientContext={() => {
                        const scope = readConsoleContextScopeFromStorage();
                        setClientContext(null, scope.companyId || null);
                    }}
                    onClearContext={clearContextLens}
                    pageFilterCompanyId={pageFilterCompanyId}
                    pageFilterClientId={pageFilterClientId}
                    pageFilterBranchId={pageFilterBranchId}
                    pageFilterCompanyOptions={pageFilterCompanyOptions}
                    pageFilterClientOptions={pageFilterClientOptions}
                    pageFilterBranchOptions={pageFilterBranchOptions}
                    hasPageFilters={hasPageFilters}
                    onPageFilterCompanyChange={setPageFilterCompany}
                    onPageFilterClientChange={setPageFilterClient}
                    onPageFilterBranchChange={setPageFilterBranch}
                    onApplyContextToPageFilters={applyContextToPageFilters}
                    onClearPageFilters={clearPageFilters}
                    controlTowerEnabled={controlTowerEnabled}
                    workspaceMode={effectiveWorkspaceMode}
                    onWorkspaceModeChange={(value) => {
                        if (controlTowerEnabled) {
                            setWorkspaceMode(value);
                        }
                    }}
                    viewPreset={viewPreset}
                    onViewPresetChange={setViewPreset}
                    canSwitchViewPreset={canSwitchViewPreset}
                />
                <TenantsScopedErrorSummary
                    errors={visibleInlineErrors}
                    scopeLabel={activeErrorScopeLabel}
                    showScopeClear
                    onClearScope={() => clearErrors(activeErrorScope)}
                    onClearAll={() => clearErrors()}
                />
                {canWriteTenants ? (
                    <TenantsQuickCreatePanel
                        form={quickCreateForm}
                        running={quickCreateRunning}
                        companyId={quickCreateCompanyId}
                        clientId={quickCreateClientId}
                        onChange={(patch) => setQuickCreateForm((prev) => ({ ...prev, ...patch }))}
                        onCreateCompany={() => void handleQuickCreateCompany()}
                        onCreateClient={() => void handleQuickCreateClient()}
                        onCreateBranch={() => void handleQuickCreateBranch()}
                        onOpenWorkspace={() => router.push("/company-workspace")}
                    />
                ) : null}
                {controlTowerEnabled ? (
                    <TenantsActionQueuePanel
                        items={actionQueue}
                        refreshing={
                            tenantsPortfolioQuery.isFetching
                            || tenantsCompanyCockpitQuery.isFetching
                            || fleetAttentionQuery.isFetching
                            || recentBranchChangesKpiQuery.isFetching
                            || clientsQuery.isFetching
                        }
                        onRefresh={() => {
                            tenantsPortfolioQuery.refetch();
                            if (pageFilterCompanyId) {
                                tenantsCompanyCockpitQuery.refetch();
                            }
                            fleetAttentionQuery.refetch();
                            recentBranchChangesKpiQuery.refetch();
                            clientsQuery.refetch();
                        }}
                        onRunIntent={runActionQueueIntent}
                        onSetClientContext={setClientContextAndPageFilters}
                    />
                ) : null}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-xs text-muted-foreground">Режим списка:</span>
                    <button
                        className={tenantLifecycle === "active" ? "btn-primary" : "btn-ghost"}
                        onClick={() => setTenantLifecycle("active")}
                    >
                        Активные
                    </button>
                    <button
                        className={tenantLifecycle === "archived" ? "btn-primary" : "btn-ghost"}
                        onClick={() => setTenantLifecycle("archived")}
                    >
                        Архив
                    </button>
                    <button
                        className={tenantLifecycle === "all" ? "btn-primary" : "btn-ghost"}
                        onClick={() => setTenantLifecycle("all")}
                    >
                        Все
                    </button>
                </div>
            </div>

            <div className="grid gap-6">
                {controlTowerEnabled && showPortfolio && tenantLifecycle === "active" ? (
                    <TenantsOperationalKpiPanel
                        isRefreshing={
                            tenantsPortfolioQuery.isFetching
                            || tenantsCompanyCockpitQuery.isFetching
                            || fleetAttentionQuery.isFetching
                            || recentBranchChangesKpiQuery.isFetching
                        }
                        onRefresh={() => {
                            tenantsPortfolioQuery.refetch();
                            if (pageFilterCompanyId) {
                                tenantsCompanyCockpitQuery.refetch();
                            }
                            fleetAttentionQuery.refetch();
                            recentBranchChangesKpiQuery.refetch();
                            selectedClientAuditQuery.refetch();
                            if (pageFilterClientId) {
                                weeklySnapshotsServerQuery.refetch();
                            }
                        }}
                        onExportJson={() => exportOperationalReport("json")}
                        onExportCsv={() => exportOperationalReport("csv")}
                        onSaveWeeklySnapshot={saveWeeklySnapshot}
                        canSaveWeeklySnapshot={Boolean(pageFilterClientId)}
                        operationalKpi={operationalKpi}
                        criticalKpiCount={criticalKpiCount}
                        warnKpiCount={warnKpiCount}
                        kpiStatuses={{
                            onboardingCoverage: operationalKpiById.get("onboardingCoverage")?.status ?? "ok",
                            goLiveReadiness: operationalKpiById.get("goLiveReadiness")?.status ?? "ok",
                            serviceStability: operationalKpiById.get("serviceStability")?.status ?? "ok",
                            decommissionShare: operationalKpiById.get("decommissionShare")?.status ?? "ok",
                            changeFailure: operationalKpiById.get("changeFailure")?.status ?? "ok",
                            rollbackShare: operationalKpiById.get("rollbackShare")?.status ?? "ok",
                            blockedSignals: operationalKpiById.get("blockedSignals")?.status ?? "ok",
                        }}
                        kpiDrilldown={operationalKpiDrilldown}
                        onRunKpiAction={runKpiAction}
                        onboardingThroughput={onboardingThroughput}
                        formatOptionalHours={formatOptionalHours}
                        formatOptionalPercent={formatOptionalPercent}
                        alertSeverity={alertHookPayload.severity}
                        alertBreachesCount={alertHookPayload.breaches.length}
                        onCopyAlertPayload={copyAlertHookPayload}
                        onRunMetricsSnapshot={runMetricsSnapshotHook}
                        runningMetricsSnapshotMode={runningMetricsSnapshotMode}
                        lastMetricsSnapshotJob={lastMetricsSnapshotJob}
                        pageFilterClientId={pageFilterClientId}
                        weeklySnapshotsFetching={weeklySnapshotsServerQuery.isFetching}
                        weeklySnapshots={weeklySnapshots}
                        formatDateTimeLabel={formatDateTimeLabel}
                    />
                ) : null}

                {controlTowerEnabled && showPortfolio && tenantLifecycle === "active" ? (
                <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-fleet-attention">
                        <div className="flex items-start justify-between gap-4 mb-4">
                            <div>
                                <h2 className="text-lg font-semibold">Риски и внимание</h2>
                                <p className="text-sm text-muted-foreground">
                                    Операционные риски по активным клиентам (топ по score)
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    охват: reference branches (шум тестовых веток исключен)
                                </p>
                            </div>
                            <button
                                className="btn-ghost"
                                onClick={() => {
                                    tenantsPortfolioQuery.refetch();
                                    fleetAttentionQuery.refetch();
                                }}
                                disabled={tenantsPortfolioQuery.isFetching || fleetAttentionQuery.isFetching}
                            >
                                {tenantsPortfolioQuery.isFetching || fleetAttentionQuery.isFetching ? "Обновление..." : "Обновить"}
                            </button>
                        </div>

                        {fleetAttention ? (
                            <div className="mb-3 text-xs text-muted-foreground" data-testid="tenants-fleet-attention-summary">
                                активных клиентов {fleetAttention.summary.active_clients_total} · с риском {fleetAttention.summary.clients_with_attention} ·
                                высокий {fleetAttention.summary.high_risk_clients} · средний {fleetAttention.summary.medium_risk_clients} ·
                                ошибок outbox за 24ч {fleetAttention.summary.outbox_failed_24h_total} · ожидают передачи {fleetAttention.summary.pending_handovers_total}
                            </div>
                        ) : null}

                        <div className="space-y-3">
                            {fleetAttentionLoading ? (
                                <div className="text-sm text-muted-foreground">Загрузка панели рисков...</div>
                            ) : fleetAttentionErrored ? (
                                <div className="text-sm text-muted-foreground">Не удалось загрузить панель рисков.</div>
                            ) : !fleetAttention?.items?.length ? (
                                <div className="text-sm text-muted-foreground">Клиенты со средним/высоким риском не найдены.</div>
                            ) : (
                                fleetAttention.items.map((item) => (
                                    <div
                                        key={item.client_id}
                                        className="rounded-lg border border-border/60 px-4 py-3"
                                        data-testid="tenants-fleet-attention-row"
                                    >
                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                            <div className="font-medium">
                                                {item.client_name ?? item.client_slug}
                                            </div>
                                            <div className="flex items-center gap-2 text-xs">
                                                <span
                                                    className={`inline-flex rounded-full px-2 py-0.5 font-semibold ${attentionLevelClass(item.attention_level as FleetAttentionLevel)}`}
                                                >
                                                    {item.attention_level}
                                                </span>
                                                <span className="text-muted-foreground">оценка {item.attention_score}</span>
                                            </div>
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            жизненный цикл {formatStateLabel(item.lifecycle_state, FLEET_LIFECYCLE_LABELS)} · сервис {formatStateLabel(item.service_state, FLEET_SERVICE_LABELS)} · владелец {item.owner_name ?? "—"} · следующее действие {item.next_action}
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            филиалы активные {item.active_branches}/{item.total_branches} · неактуальные {item.stale_branches} · интеграционных ошибок {item.integration_error_branches} · outbox_failed_24h {item.outbox_failed_24h} · ожидают передачи {item.pending_handovers}
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            reference-охват: {item.reference_branch_ids?.length ?? 0} · {formatReferenceScopeReason(item.reference_branch_reason)}
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            причины: {item.reasons?.join(", ") || "—"}
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            действия: {item.suggested_actions?.join(", ") || "—"}
                                        </div>
                                        <div className="mt-2 flex flex-wrap items-center gap-2">
                                            <button
                                                className="btn-ghost"
                                                onClick={() => setClientContextAndPageFilters(item.client_id, item.company_id)}
                                            >
                                                В контекст
                                            </button>
                                            <button
                                                className="btn-ghost"
                                                onClick={() => openClientContextTarget("/integrations", item.client_id, item.company_id)}
                                            >
                                                Интеграции
                                            </button>
                                            <button
                                                className="btn-ghost"
                                                onClick={() => openClientContextTarget("/", item.client_id, item.company_id)}
                                            >
                                                Заявки
                                            </button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </section>
                ) : null}

                {showPortfolio ? (
                <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-portfolio-companies">
                    <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">Компании</h2>
                            <p className="text-sm text-muted-foreground">
                                {companiesQuery.isLoading ? "—" : `${companies.length} всего`}
                            </p>
                        </div>
                        <input
                            className="w-56 rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="Поиск по компаниям"
                            value={companyQuery}
                            onChange={(event) => setCompanyQuery(event.target.value)}
                        />
                    </div>
                    <div className="space-y-3">
                        {companiesQuery.isLoading ? (
                            <div className="text-sm text-muted-foreground">Загрузка компаний...</div>
                        ) : companiesQuery.isError ? (
                            <div className="text-sm text-muted-foreground">Не удалось загрузить компании.</div>
                        ) : companies.length === 0 ? (
                            <div className="text-sm text-muted-foreground">Компании не найдены.</div>
                        ) : (
                            companies.map((company) => {
                                const isEditing = companyEditor?.id === company.id;
                                return (
                                    <div
                                        key={company.id}
                                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
                                    >
                                        <div>
                                            <div className="font-medium">{company.name ?? "Без названия"}</div>
                                            {isPlatformPreset ? (
                                                <div className="text-xs text-muted-foreground">{company.id}</div>
                                            ) : null}
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                            <span>{company.id === selectedCompanyId ? "Выбрана" : ""}</span>
                                            {canWriteTenants ? (
                                                <button
                                                    className="btn-ghost"
                                                    onClick={() => startCompanyEdit(company)}
                                                >
                                                    Редактировать
                                                </button>
                                            ) : null}
                                            <button
                                                className="btn-ghost"
                                                onClick={() => setCompanyContext(company.id)}
                                                disabled={company.id === selectedCompanyId}
                                            >
                                                В контекст
                                            </button>
                                        </div>
                                        {isEditing && companyEditor ? (
                                            <div className="w-full mt-3 rounded-lg border border-border/60 bg-muted/30 p-3">
                                                <div className="grid gap-3">
                                                    <div className="rounded-lg border border-border/60 bg-background p-3 text-[11px] text-muted-foreground">
                                                        Контракт ввода: `name` обязателен. `billing_info` опционален и принимается как JSON-объект.
                                                        Основной сценарий: меняйте только название. JSON нужен только для расширенных атрибутов.
                                                    </div>
                                                    <label className="text-xs text-muted-foreground">
                                                        Название
                                                        <input
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                            value={companyEditor.name}
                                                            onChange={(event) =>
                                                                setCompanyEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, name: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingCompany}
                                                        />
                                                    </label>
                                                    <details className="rounded-lg border border-border/60 bg-background p-3">
                                                        <summary className="cursor-pointer text-xs text-muted-foreground">
                                                            Расширенные параметры (JSON, экспертный режим): billing_info
                                                        </summary>
                                                        <label className="mt-2 block text-xs text-muted-foreground">
                                                            billing_info (JSON, опционально)
                                                            <textarea
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                                                rows={3}
                                                                value={companyEditor.billingInfo}
                                                                onChange={(event) =>
                                                                    setCompanyEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, billingInfo: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingCompany}
                                                            />
                                                        </label>
                                                    </details>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            className="btn-primary"
                                                            onClick={handleSaveCompany}
                                                            disabled={!canWriteTenants || savingCompany}
                                                        >
                                                            {savingCompany ? "Сохранение..." : "Сохранить"}
                                                        </button>
                                                        <button
                                                            className="btn-ghost"
                                                            onClick={() => setCompanyEditor(null)}
                                                            disabled={savingCompany}
                                                        >
                                                            Отмена
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                );
                            })
                        )}
                    </div>
                    {companiesQuery.hasNextPage ? (
                        <div className="flex justify-center pt-3">
                            <button
                                className="btn-ghost"
                                onClick={() => companiesQuery.fetchNextPage()}
                                disabled={companiesQuery.isFetchingNextPage}
                            >
                                {companiesQuery.isFetchingNextPage ? "Загрузка..." : "Показать еще"}
                            </button>
                        </div>
                    ) : null}
                </section>
                ) : null}

                {showDecommission ? (
                <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-decommission-center">
                    <div className="flex items-center justify-between gap-4 mb-3">
                        <div>
                            <h2 className="text-lg font-semibold">Вывод из эксплуатации</h2>
                            <p className="text-sm text-muted-foreground">
                                Архивация и восстановление клиентов с прозрачным подтверждением.
                            </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <button
                                className={tenantLifecycle === "archived" ? "btn-primary" : "btn-ghost"}
                                onClick={() => setTenantLifecycle("archived")}
                            >
                                Только архив
                            </button>
                            <button
                                className={tenantLifecycle === "all" ? "btn-primary" : "btn-ghost"}
                                onClick={() => setTenantLifecycle("all")}
                            >
                                Все
                            </button>
                            <button
                                className={tenantLifecycle === "active" ? "btn-primary" : "btn-ghost"}
                                onClick={() => setTenantLifecycle("active")}
                            >
                                Активные
                            </button>
                        </div>
                    </div>
                    <div className="text-xs text-muted-foreground">
                        Для вывода из эксплуатации используйте действия `Архивировать/Восстановить` в карточке клиента ниже.
                    </div>
                </section>
                ) : null}

                {showClientsSection ? (
                <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-clients-section">
                    <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">
                                {decommissionFocused ? "Клиенты (вывод из эксплуатации)" : "Клиенты"}
                            </h2>
                            <p className="text-sm text-muted-foreground">
                                {clientsLoading ? "—" : `${clients.length} всего`}
                            </p>
                            {decommissionFocused ? (
                                <div className="mt-1 text-xs text-muted-foreground">
                                    Фокус на жизненном цикле клиента: архив/восстановление.
                                </div>
                            ) : null}
                            {clientsSummary ? (
                                <div className="mt-1 text-xs text-muted-foreground">
                                    портфель: клиентов {clientsSummary.total_clients} · активные {clientsSummary.active_clients} · онбординг {clientsSummary.onboarding_clients} · пауза {clientsSummary.paused_clients} · архив {clientsSummary.archived_clients} · деградация {clientsSummary.degraded_clients}
                                </div>
                            ) : null}
                            {pageFilterCompanyId ? (
                                <div className="mt-1 text-xs text-muted-foreground">
                                    фильтр по компании (ID): {pageFilterCompanyId}
                                </div>
                            ) : null}
                        </div>
                        <div className="flex flex-wrap items-center justify-end gap-2">
                            <input
                                className="w-56 rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                placeholder="Поиск по клиентам"
                                value={clientQuery}
                                onChange={(event) => setClientQuery(event.target.value)}
                            />
                            <select
                                className="rounded-lg border border-border bg-background px-3 py-2 text-xs"
                                value={fleetLifecycleFilter}
                                onChange={(event) => setFleetLifecycleFilter(event.target.value as FleetLifecycleFilter)}
                                aria-label="Фильтр этапа клиента"
                            >
                                <option value="all">Этап: все</option>
                                <option value="lead">лид</option>
                                <option value="contracting">договор</option>
                                <option value="onboarding">онбординг</option>
                                <option value="go_live_ready">готов к запуску</option>
                                <option value="active">активный</option>
                                <option value="paused">пауза</option>
                                <option value="archived">архив</option>
                            </select>
                            <select
                                className="rounded-lg border border-border bg-background px-3 py-2 text-xs"
                                value={fleetPaymentFilter}
                                onChange={(event) => setFleetPaymentFilter(event.target.value as FleetPaymentFilter)}
                                aria-label="Фильтр статуса оплаты"
                            >
                                <option value="all">Оплата: все</option>
                                <option value="pending">ожидает</option>
                                <option value="confirmed">подтверждена</option>
                                <option value="rejected">отклонена</option>
                                <option value="unknown">не задана</option>
                            </select>
                            <select
                                className="rounded-lg border border-border bg-background px-3 py-2 text-xs"
                                value={fleetServiceFilter}
                                onChange={(event) => setFleetServiceFilter(event.target.value as FleetServiceFilter)}
                                aria-label="Фильтр сервисного статуса"
                            >
                                <option value="all">Сервис: все</option>
                                <option value="ok">стабильно</option>
                                <option value="degraded">деградация</option>
                                <option value="attention">внимание</option>
                            </select>
                        </div>
                    </div>
                    <div className="space-y-3">
                        {clientsLoading ? (
                            <div className="text-sm text-muted-foreground">Загрузка клиентов...</div>
                        ) : clientsErrored ? (
                            <div className="text-sm text-muted-foreground">Не удалось загрузить клиентов.</div>
                        ) : clients.length === 0 ? (
                            <div className="text-sm text-muted-foreground">Клиенты не найдены.</div>
                        ) : (
                            clients.map((client) => {
                                const clientIdKey = client.id ? String(client.id) : "";
                                const isEditing = clientEditor?.id === client.id;
                                const isArchived = isClientArchived(client);
                                const lifecyclePending = clientLifecyclePendingId === client.id;
                                const lifecycleMode: ClientLifecycleMode = isArchived ? "restore" : "archive";
                                const lifecycleAuditFilter: ClientLifecycleAuditFilter = clientIdKey
                                    ? (clientLifecycleAuditFilterById[clientIdKey] ?? "all")
                                    : "all";
                                const sessionLifecycleAudit = clientIdKey
                                    ? (clientLifecycleAuditById[clientIdKey] ?? [])
                                    : [];
                                const apiLifecycleAudit = clientIdKey && clientIdKey === pageFilterClientId
                                    ? selectedClientApiAuditEntries
                                    : [];
                                const lifecycleAuditHistory = mergeLifecycleAuditEntries(
                                    sessionLifecycleAudit,
                                    apiLifecycleAudit,
                                );
                                const filteredLifecycleAuditHistory = lifecycleAuditHistory.filter((entry) => (
                                    lifecycleAuditFilter === "all" || entry.status === lifecycleAuditFilter
                                ));
                                const companyLocked = (client.total_branches ?? 0) > 0 && !!client.company_id;
                                return (
                                    <div
                                        key={client.id}
                                        data-testid="tenants-client-row"
                                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
                                    >
                                        <div>
                                            <div className="font-medium">{client.name ?? client.slug ?? "Без названия"}</div>
                                            {isPlatformPreset ? (
                                                <div className="text-xs text-muted-foreground">{client.id}</div>
                                            ) : null}
                                            {client.company_name ? (
                                                <div className="text-xs text-muted-foreground">{client.company_name}</div>
                                            ) : null}
                                            {client.status ? (
                                                <div className="text-xs text-muted-foreground">статус: {client.status}</div>
                                            ) : null}
                                            <div className="text-xs text-muted-foreground">
                                                жизненный цикл: {formatStateLabel(client.lifecycle_state, FLEET_LIFECYCLE_LABELS)} · оплата: {formatStateLabel(client.payment_status, FLEET_PAYMENT_LABELS)} · сервис: {formatStateLabel(client.service_state, FLEET_SERVICE_LABELS)}
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                владелец: {client.owner_name ?? "—"} · следующее действие: {client.next_action ?? "—"}
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                филиалы: активные {client.active_branches ?? 0}/{client.total_branches ?? 0} · деградация {client.degraded_branches ?? 0} · готовы к запуску {client.go_live_ready_branches ?? 0}
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                reference-охват: {client.reference_branch_ids?.length ?? 0} · {formatReferenceScopeReason(client.reference_branch_reason)}
                                            </div>
                                            {lifecycleAuditHistory.length > 0 || clientIdKey === pageFilterClientId ? (
                                                <div className="mt-2 rounded-lg border border-border/60 bg-background px-3 py-2 text-xs" data-testid="tenants-client-lifecycle-audit">
                                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                                        <div className="font-medium">
                                                            История статуса (сессия + API)
                                                        </div>
                                                        <div className="flex items-center gap-1">
                                                            <button
                                                                className={lifecycleAuditFilter === "all" ? "btn-primary" : "btn-ghost"}
                                                                onClick={() => {
                                                                    if (!clientIdKey) {
                                                                        return;
                                                                    }
                                                                    setClientLifecycleAuditFilterById((prev) => ({ ...prev, [clientIdKey]: "all" }));
                                                                }}
                                                            >
                                                                все
                                                            </button>
                                                            <button
                                                                className={lifecycleAuditFilter === "success" ? "btn-primary" : "btn-ghost"}
                                                                onClick={() => {
                                                                    if (!clientIdKey) {
                                                                        return;
                                                                    }
                                                                    setClientLifecycleAuditFilterById((prev) => ({ ...prev, [clientIdKey]: "success" }));
                                                                }}
                                                            >
                                                                успех
                                                            </button>
                                                            <button
                                                                className={lifecycleAuditFilter === "error" ? "btn-primary" : "btn-ghost"}
                                                                onClick={() => {
                                                                    if (!clientIdKey) {
                                                                        return;
                                                                    }
                                                                    setClientLifecycleAuditFilterById((prev) => ({ ...prev, [clientIdKey]: "error" }));
                                                                }}
                                                            >
                                                                ошибка
                                                            </button>
                                                            {clientIdKey === pageFilterClientId ? (
                                                                <button
                                                                    className="btn-ghost"
                                                                    onClick={() => selectedClientAuditQuery.refetch()}
                                                                    disabled={selectedClientAuditQuery.isFetching}
                                                                    data-testid="tenants-client-lifecycle-audit-refresh"
                                                                >
                                                                    {selectedClientAuditQuery.isFetching ? "Обновление..." : "Обновить данные API"}
                                                                </button>
                                                            ) : null}
                                                        </div>
                                                    </div>
                                                    <div className="mt-1 text-muted-foreground">
                                                        источник: кеш сессии + API-аудит{clientIdKey === pageFilterClientId ? "" : " (API-аудит доступен при текущем фильтре клиента)"}
                                                    </div>
                                                    <div className="mt-1 space-y-2" data-testid="tenants-client-lifecycle-audit-history">
                                                        {filteredLifecycleAuditHistory.length === 0 ? (
                                                            <div className="rounded border border-border/50 px-2 py-1 text-muted-foreground">
                                                                Записей по текущему фильтру нет.
                                                            </div>
                                                        ) : (
                                                            filteredLifecycleAuditHistory.map((entry, index) => (
                                                                <div key={`${entry.happenedAt}-${index}`} className="rounded border border-border/50 px-2 py-1" data-testid="tenants-client-lifecycle-audit-item">
                                                                    <div className="text-muted-foreground">
                                                                        действие: {entry.mode === "archive" ? "Архивация" : "Восстановление"} · оператор: {entry.actorLabel} · время: {formatDateTimeLabel(entry.happenedAt)}
                                                                    </div>
                                                                    <div className="text-muted-foreground">
                                                                        переход: {entry.previousLifecycleLabel}{" -> "}{entry.targetLifecycleLabel}
                                                                    </div>
                                                                    <div className="text-muted-foreground">
                                                                        причина: {entry.reason}
                                                                    </div>
                                                                    <div className="text-muted-foreground">
                                                                        источник: {entry.source}
                                                                    </div>
                                                                    <div className={entry.status === "success" ? "text-emerald-700" : "text-red-700"}>
                                                                        {entry.status === "success" ? "OK" : "ERROR"}: {entry.message}
                                                                        {isPlatformPreset && entry.traceId ? ` (trace_id: ${entry.traceId})` : ""}
                                                                    </div>
                                                                </div>
                                                            ))
                                                        )}
                                                    </div>
                                                </div>
                                            ) : null}
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                            <span>{client.id === selectedClientId ? "Выбран" : ""}</span>
                                            {canWriteTenants ? (
                                                <button
                                                    className="btn-ghost"
                                                    onClick={() => startClientEdit(client)}
                                                    data-testid="tenants-client-edit"
                                                    disabled={lifecyclePending}
                                                >
                                                    Редактировать
                                                </button>
                                            ) : null}
                                            {canWriteTenants ? (
                                                <button
                                                    className="btn-ghost"
                                                    onClick={() => openClientLifecycleAction(client, lifecycleMode)}
                                                    data-testid="tenants-client-lifecycle-open"
                                                    disabled={lifecyclePending}
                                                >
                                                    {lifecyclePending
                                                        ? "Выполняется..."
                                                        : lifecycleMode === "restore"
                                                            ? "Открыть восстановление"
                                                            : "Открыть архивирование"}
                                                </button>
                                            ) : null}
                                            <button
                                                className="btn-ghost"
                                                onClick={() => setClientContextAndPageFilters(client.id, client.company_id)}
                                                disabled={client.id === selectedClientId || lifecyclePending}
                                            >
                                                В контекст
                                            </button>
                                        </div>
                                        {isEditing && clientEditor ? (
                                            <div className="w-full mt-3 rounded-lg border border-border/60 bg-muted/30 p-3">
                                                <div className="grid gap-3">
                                                    <label className="text-xs text-muted-foreground">
                                                        Slug (идентификатор)
                                                        <input
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                            value={clientEditor.slug}
                                                            onChange={(event) =>
                                                                setClientEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, slug: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingClient}
                                                        />
                                                        <div className="mt-1 text-[11px] text-muted-foreground">
                                                            Формат: `a-z0-9_-`, без пробелов.
                                                        </div>
                                                    </label>
                                                    <label className="text-xs text-muted-foreground">
                                                        Компания
                                                        <select
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                            value={clientEditor.companyId}
                                                            onChange={(event) =>
                                                                setClientEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, companyId: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingClient || companyLocked}
                                                            aria-label="Компания клиента"
                                                        >
                                                            <option value="">Без компании</option>
                                                            {knownCompanies.map((company) => (
                                                                <option key={company.id} value={company.id}>
                                                                    {company.name ?? company.id}
                                                                </option>
                                                            ))}
                                                        </select>
                                                        {companyLocked ? (
                                                            <div className="mt-1 text-[11px] text-muted-foreground">
                                                                `company_id` зафиксирован после создания филиалов.
                                                            </div>
                                                        ) : null}
                                                    </label>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            className="btn-primary"
                                                            onClick={handleSaveClient}
                                                            disabled={!canWriteTenants || savingClient || lifecyclePending}
                                                        >
                                                            {savingClient ? "Сохранение..." : "Сохранить"}
                                                        </button>
                                                        <button
                                                            className="btn-ghost"
                                                            onClick={() => setClientEditor(null)}
                                                            disabled={savingClient || lifecyclePending}
                                                        >
                                                            Отмена
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                );
                            })
                        )}
                    </div>
                    {!clientsUsingServerContract && clientsQuery.hasNextPage ? (
                        <div className="flex justify-center pt-3">
                            <button
                                className="btn-ghost"
                                onClick={() => clientsQuery.fetchNextPage()}
                                disabled={clientsQuery.isFetchingNextPage}
                            >
                                {clientsQuery.isFetchingNextPage ? "Загрузка..." : "Показать еще"}
                            </button>
                        </div>
                    ) : null}
                </section>
                ) : null}

                {showChangeManagement ? (
                <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-change-management">
                    <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">Филиалы</h2>
                            <p className="text-sm text-muted-foreground">
                                {branchesLoading ? "—" : `${branches.length} всего`}
                            </p>
                            {pageFilterClientId ? (
                                <div className="mt-1 text-xs text-muted-foreground">
                                    выбран клиент для изменений: {selectedClientName ?? pageFilterClientId}
                                </div>
                            ) : null}
                        </div>
                        <input
                            className="w-56 rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="Поиск по филиалам"
                            value={branchQuery}
                            onChange={(event) => setBranchQuery(event.target.value)}
                        />
                    </div>
                    <div className="space-y-3">
                        {branchesLoading ? (
                            <div className="text-sm text-muted-foreground">Загрузка филиалов...</div>
                        ) : branchesErrored ? (
                            <div className="text-sm text-muted-foreground">Не удалось загрузить филиалы.</div>
                        ) : branches.length === 0 ? (
                            <div className="text-sm text-muted-foreground">Филиалы не найдены.</div>
                        ) : (
                            branches.map((branch) => {
                                const isEditing = branchEditor?.id === branch.id;
                                const confirmationNeeded = isEditing && branchEditor
                                    ? requiresBranchConfirmation(branchEditor)
                                    : false;
                                return (
                                    <div
                                        key={branch.id}
                                        data-testid="tenants-branch-row"
                                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
                                    >
                                        <div>
                                            <div className="font-medium">{branch.name ?? branch.slug ?? "Без названия"}</div>
                                            {isPlatformPreset ? (
                                                <div className="text-xs text-muted-foreground">{branch.id}</div>
                                            ) : null}
                                            <TenantsSensitiveIdCell
                                                branchId={branch.id}
                                                instanceId={branch.instance_id}
                                                contextScope={effectiveWorkspaceMode}
                                                onAudit={auditSensitiveAccess}
                                            />
                                            <div className="text-xs text-muted-foreground">
                                                {branch.onboarding_state ? `этап онбординга: ${branch.onboarding_state}` : "этап онбординга: —"}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                            <span>{branch.id === selectedBranchId ? "Выбран" : ""}</span>
                                            {canWriteTenants ? (
                                                <button
                                                    className="btn-ghost"
                                                    onClick={() => startBranchEdit(branch)}
                                                    data-testid="tenants-branch-edit"
                                                >
                                                    Редактировать
                                                </button>
                                            ) : null}
                                            <button
                                                className="btn-ghost"
                                                onClick={() => setBranchContextAndPageFilters(branch.id)}
                                                disabled={branch.id === selectedBranchId}
                                            >
                                                В контекст
                                            </button>
                                        </div>
                                        {isEditing && branchEditor ? (
                                            <div className="w-full mt-3 rounded-lg border border-border/60 bg-muted/30 p-3">
                                                <div className="grid gap-3">
                                                    <div className="rounded-lg border border-border/60 bg-background p-3 text-[11px] text-muted-foreground" data-testid="tenants-branch-input-contract">
                                                        Форматы: `slug` = `a-z0-9_-`; `timezone` = IANA (`Asia/Almaty`);
                                                        `phone` = 7-15 цифр (допускаются `+`, пробелы, `()`, `-`);
                                                        `telegram_chat_id` = целое число (`-100...`);
                                                        `knowledge_tag` = `a-z0-9_-` до 64.
                                                    </div>
                                                    <div className="grid gap-3 sm:grid-cols-2">
                                                        <label className="text-xs text-muted-foreground">
                                                            Название
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.name}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, name: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            Slug (идентификатор)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.slug}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, slug: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                                placeholder="branch-slug"
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            Timezone (опционально)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.timezone}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, timezone: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                                placeholder="Asia/Almaty"
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            Phone (опционально)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.phone}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, phone: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                                placeholder="+7 700 000 00 00"
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            instance_id (опционально)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.instanceId}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, instanceId: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                                placeholder="instance-123"
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            telegram_chat_id (опционально)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.telegramChatId}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, telegramChatId: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                                placeholder="-1001234567890"
                                                            />
                                                        </label>
                                                        <label className="text-xs text-muted-foreground">
                                                            knowledge_tag (опционально)
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.knowledgeTag}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, knowledgeTag: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch}
                                                                placeholder="demo_salon"
                                                            />
                                                        </label>
                                                    </div>
                                                    <label className="flex items-center gap-2 text-xs text-muted-foreground">
                                                        <input
                                                            type="checkbox"
                                                            className="h-4 w-4"
                                                            checked={branchEditor.isActive}
                                                            onChange={(event) =>
                                                                setBranchEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, isActive: event.target.checked }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingBranch}
                                                        />
                                                        Активен
                                                    </label>
                                                    <label className="text-xs text-muted-foreground">
                                                        Причина изменения (аудит)
                                                        <input
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                            value={branchEditor.changeReason}
                                                            onChange={(event) =>
                                                                setBranchEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, changeReason: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                        />
                                                    </label>
                                                    {confirmationNeeded ? (
                                                        <label className="text-xs text-muted-foreground">
                                                            Причина подтверждения
                                                            <input
                                                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                                value={branchEditor.confirmReason}
                                                                onChange={(event) =>
                                                                    setBranchEditor((prev) =>
                                                                        prev
                                                                            ? { ...prev, confirmReason: event.target.value }
                                                                            : prev
                                                                    )
                                                                }
                                                                disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                            />
                                                        </label>
                                                    ) : null}
                                                    <div className="rounded-lg border border-border/60 bg-background p-3 text-xs" data-testid="tenants-branch-impact-preview">
                                                        <div className="font-medium">Оценка влияния</div>
                                                        <div className="mt-1 text-muted-foreground">
                                                            branch: {branchEditor.name || branchEditor.slug || branchEditor.id}
                                                        </div>
                                                        <div className="text-muted-foreground">
                                                            activation: {branchEditor.original.isActive ? "active" : "inactive"} {"-> "} {branchEditor.isActive ? "active" : "inactive"}
                                                        </div>
                                                        {!branchEditor.original.isActive && branchEditor.isActive && !branchEditor.instanceId.trim() ? (
                                                            <div className="text-destructive">
                                                                Нельзя активировать без `instance_id`.
                                                            </div>
                                                        ) : null}
                                                        {confirmationNeeded ? (
                                                            <div className="text-amber-700">
                                                                Изменение требует подтверждения (`branch_deactivate`).
                                                            </div>
                                                        ) : (
                                                            <div className="text-muted-foreground">
                                                                Подтверждение не требуется для текущего изменения.
                                                            </div>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            className="btn-primary"
                                                            onClick={handlePreviewBranchChange}
                                                            data-testid="tenants-branch-change-preview"
                                                            disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                        >
                                                            {savingBranch ? "Подготовка..." : "Черновик + проверка"}
                                                        </button>
                                                        <button
                                                            className="btn-primary"
                                                            onClick={handlePublishBranchChange}
                                                            data-testid="tenants-branch-change-publish"
                                                            disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange || !branchChangePreview?.change?.id}
                                                        >
                                                            {publishingBranchChange ? "Применение..." : "Применить"}
                                                        </button>
                                                        <button
                                                            className="btn-ghost"
                                                            onClick={handleRollbackBranchChange}
                                                            data-testid="tenants-branch-change-rollback"
                                                            disabled={
                                                                !canWriteTenants ||
                                                                savingBranch ||
                                                                publishingBranchChange ||
                                                                rollingBackBranchChange ||
                                                                !(branchChangePreview?.change?.status === "published" || latestPublishedBranchChange)
                                                            }
                                                        >
                                                            {rollingBackBranchChange ? "Откат..." : "Откат"}
                                                        </button>
                                                        <button
                                                            className="btn-ghost"
                                                            onClick={() => {
                                                                setBranchEditor(null);
                                                                setBranchChangePreview(null);
                                                            }}
                                                            disabled={savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                        >
                                                            Отмена
                                                        </button>
                                                    </div>
                                                    <label className="text-xs text-muted-foreground">
                                                        Причина отката
                                                        <input
                                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                            value={branchEditor.rollbackReason}
                                                            onChange={(event) =>
                                                                setBranchEditor((prev) =>
                                                                    prev
                                                                        ? { ...prev, rollbackReason: event.target.value }
                                                                        : prev
                                                                )
                                                            }
                                                            disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                        />
                                                    </label>
                                                    {branchChangePreview?.change ? (
                                                        <div className="rounded-lg border border-border/60 bg-background p-3 text-xs">
                                                            <div className="font-medium mb-1">
                                                                Изменение #{branchChangePreview.change.id}
                                                            </div>
                                                            <div className="text-muted-foreground mb-2">
                                                                статус: {formatStateLabel(branchChangePreview.change.status, BRANCH_CHANGE_STATUS_LABELS)}
                                                            </div>
                                                            {previewValidationErrors.length > 0 ? (
                                                                <div className="mb-2 text-red-600">
                                                                    проверка: {previewValidationErrors.join("; ")}
                                                                </div>
                                                            ) : null}
                                                            {previewDiffEntries.length > 0 ? (
                                                                <div className="space-y-1">
                                                                    {previewDiffEntries.map((entry) => (
                                                                        <div key={entry.field} className="grid grid-cols-3 gap-2">
                                                                            <span className="font-medium">{entry.field}</span>
                                                                            <span className="truncate text-muted-foreground">{entry.before}</span>
                                                                            <span className="truncate text-foreground">{entry.after}</span>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            ) : (
                                                                <div className="text-muted-foreground">изменений нет</div>
                                                            )}
                                                        </div>
                                                    ) : null}
                                                    <div className="rounded-lg border border-border/60 bg-background p-3 text-xs">
                                                        <div className="font-medium mb-2">История изменений</div>
                                                        {branchChangesQuery.isLoading ? (
                                                            <div className="text-muted-foreground">Загрузка...</div>
                                                        ) : !branchChangesQuery.data?.items?.length ? (
                                                            <div className="text-muted-foreground">Пока нет изменений</div>
                                                        ) : (
                                                            <div className="space-y-1">
                                                                {branchChangesQuery.data.items.slice(0, 5).map((item) => (
                                                                    <div key={item.id} className="flex items-center justify-between gap-2">
                                                                        <span>{formatStateLabel(item.status, BRANCH_CHANGE_STATUS_LABELS)}</span>
                                                                        <span className="text-muted-foreground">{item.created_at ? new Date(item.created_at).toLocaleString("ru-RU") : "—"}</span>
                                                                    </div>
                                                                ))}
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                );
                            })
                        )}
                    </div>
                    {branchesQuery.hasNextPage ? (
                        <div className="flex justify-center pt-3">
                            <button
                                className="btn-ghost"
                                onClick={() => branchesQuery.fetchNextPage()}
                                disabled={branchesQuery.isFetchingNextPage}
                            >
                                {branchesQuery.isFetchingNextPage ? "Загрузка..." : "Показать еще"}
                            </button>
                        </div>
                    ) : null}
                </section>
                ) : null}
            </div>

            {clientLifecycleDraft ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" data-testid="tenants-client-lifecycle-modal-overlay">
                    <div
                        className="card-surface w-full max-w-xl space-y-4 p-6"
                        role="dialog"
                        aria-modal="true"
                        data-testid="tenants-client-lifecycle-modal"
                    >
                        <div>
                            <h3 className="text-lg font-semibold">
                                {clientLifecycleDraft.mode === "archive" ? "Архивировать клиента" : "Восстановить клиента"}
                            </h3>
                            <p className="text-sm text-muted-foreground">
                                Подтвердите lifecycle-действие перед отправкой в API. Заполнение checklist обязательно.
                            </p>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-background p-3 text-xs" data-testid="tenants-client-lifecycle-impact">
                            <div className="font-medium mb-1">Оценка влияния</div>
                            <div className="text-muted-foreground">
                                клиент: {clientLifecycleDraft.clientLabel} · компания: {clientLifecycleDraft.companyLabel}
                            </div>
                            <div className="text-muted-foreground">
                                переход: {clientLifecycleDraft.currentLifecycleLabel}{" -> "}{clientLifecycleDraft.targetLifecycleLabel}
                            </div>
                            <div className="text-muted-foreground">
                                филиалы: активные {clientLifecycleDraft.activeBranches}/{clientLifecycleDraft.totalBranches} · деградация {clientLifecycleDraft.degradedBranches}
                            </div>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-background p-3 text-xs" data-testid="tenants-client-lifecycle-checklist">
                            <div className="font-medium mb-1">Pre-submit checklist</div>
                            <label className="mb-2 flex items-start gap-2 text-muted-foreground">
                                <input
                                    type="checkbox"
                                    className="mt-0.5 h-4 w-4"
                                    checked={clientLifecycleDraft.checkClientScope}
                                    data-testid="tenants-client-lifecycle-check-context"
                                    onChange={(event) =>
                                        setClientLifecycleDraft((prev) =>
                                            prev
                                                ? { ...prev, checkClientScope: event.target.checked }
                                                : prev
                                        )
                                    }
                                    disabled={Boolean(clientLifecyclePendingId)}
                                />
                                <span>Проверил контекст клиента/компании перед действием.</span>
                            </label>
                            <label className="mb-2 flex items-start gap-2 text-muted-foreground">
                                <input
                                    type="checkbox"
                                    className="mt-0.5 h-4 w-4"
                                    checked={clientLifecycleDraft.checkImpactReview}
                                    data-testid="tenants-client-lifecycle-check-impact"
                                    onChange={(event) =>
                                        setClientLifecycleDraft((prev) =>
                                            prev
                                                ? { ...prev, checkImpactReview: event.target.checked }
                                                : prev
                                        )
                                    }
                                    disabled={Boolean(clientLifecyclePendingId)}
                                />
                                <span>
                                    Проверил impact:
                                    {clientLifecycleDraft.mode === "archive"
                                        ? " клиент уйдет из активного списка и деактивация отразится в операционном контуре."
                                        : " клиент вернется в активный список и потребует операционного контроля после восстановления."}
                                </span>
                            </label>
                            <label className="flex items-start gap-2 text-muted-foreground">
                                <input
                                    type="checkbox"
                                    className="mt-0.5 h-4 w-4"
                                    checked={clientLifecycleDraft.checkOwnerAligned}
                                    data-testid="tenants-client-lifecycle-check-owner"
                                    onChange={(event) =>
                                        setClientLifecycleDraft((prev) =>
                                            prev
                                                ? { ...prev, checkOwnerAligned: event.target.checked }
                                                : prev
                                        )
                                    }
                                    disabled={Boolean(clientLifecyclePendingId)}
                                />
                                <span>Подтвердил решение с ответственным владельцем клиента.</span>
                            </label>
                        </div>
                        <label className="text-xs text-muted-foreground">
                            Причина действия (обязательно)
                            <input
                                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={clientLifecycleDraft.reason}
                                data-testid="tenants-client-lifecycle-reason"
                                onChange={(event) =>
                                    setClientLifecycleDraft((prev) =>
                                        prev
                                            ? { ...prev, reason: event.target.value }
                                            : prev
                                    )
                                }
                                disabled={Boolean(clientLifecyclePendingId)}
                            />
                        </label>
                        <label className="flex items-center gap-2 text-xs text-muted-foreground">
                            <input
                                type="checkbox"
                                className="h-4 w-4"
                                checked={clientLifecycleDraft.confirmChecked}
                                data-testid="tenants-client-lifecycle-confirm"
                                onChange={(event) =>
                                    setClientLifecycleDraft((prev) =>
                                        prev
                                            ? { ...prev, confirmChecked: event.target.checked }
                                            : prev
                                    )
                                }
                                disabled={Boolean(clientLifecyclePendingId)}
                            />
                            Подтверждаю выполнение действия и влияние на lifecycle клиента
                        </label>
                        <div className="flex flex-wrap justify-end gap-2">
                            <button
                                className="btn-ghost"
                                onClick={closeClientLifecycleDraft}
                                data-testid="tenants-client-lifecycle-cancel"
                                disabled={Boolean(clientLifecyclePendingId)}
                            >
                                Отмена
                            </button>
                            <button
                                className="btn-primary"
                                onClick={handleClientLifecycleAction}
                                data-testid="tenants-client-lifecycle-submit"
                                disabled={
                                    Boolean(clientLifecyclePendingId)
                                    || !clientLifecycleDraft.reason.trim()
                                    || !clientLifecycleDraft.confirmChecked
                                    || !clientLifecycleDraft.checkClientScope
                                    || !clientLifecycleDraft.checkImpactReview
                                    || !clientLifecycleDraft.checkOwnerAligned
                                }
                            >
                                {clientLifecyclePendingId
                                    ? "Выполняется..."
                                    : clientLifecycleDraft.mode === "archive"
                                        ? "Подтвердить архив"
                                        : "Подтвердить восстановление"}
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}

            {showOnboarding ? (
                <div className="mt-10" data-testid="tenants-onboarding-section">
                    <div className="mb-3 rounded-lg border border-blue-300/60 bg-blue-50 p-3 text-xs text-blue-900">
                        Канонический execution-flow: выполняйте remediation и go-live в `Company Workspace`.
                        <button
                            className="btn-ghost ml-2"
                            onClick={() => router.push("/company-workspace")}
                            data-testid="tenants-open-workspace-from-onboarding"
                        >
                            Открыть Workspace
                        </button>
                    </div>
                    <ProvisioningWizard session={session} accessSection="tenants" />
                </div>
            ) : null}
        </div>
    );
}
