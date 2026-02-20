"use client";

import { useEffect, useMemo, useState } from "react";
import { InfiniteData, useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";
import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";
import TenantsActionQueuePanel, { type TenantsActionQueueItem } from "@/components/TenantsActionQueuePanel";
import { adminApi, auditApi, authApi, canAccessConsole, confirmationsApi, opsApi } from "@/lib/api-client";
import { readBrowserStorage, writeBrowserStorage } from "@/lib/browser-storage";
import {
    setConsoleBranchContext,
    setConsoleClientContext,
    setConsoleCompanyContext,
} from "@/lib/console-context-storage";
import { useInlineErrorSummary } from "@/lib/use-inline-error-summary";

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

type BranchChangeRecord = components["schemas"]["BranchChangeRecord"];

type TenantLifecycleMode = "active" | "archived" | "all";
type FleetLifecycleFilter = "all" | "lead" | "contracting" | "onboarding" | "go_live_ready" | "active" | "paused" | "archived";
type FleetPaymentFilter = "all" | "pending" | "confirmed" | "rejected" | "unknown";
type FleetServiceFilter = "all" | "ok" | "degraded" | "attention";
type FleetAttentionLevel = "high" | "medium" | "low";
type TenantsWorkspaceMode = "all" | "portfolio" | "onboarding" | "changes" | "decommission";
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
const WEEKLY_SNAPSHOT_STORAGE_KEY = "tenants:operational-weekly-snapshots:v1";
const MAX_LIFECYCLE_AUDIT_ENTRIES_PER_CLIENT = 20;
const MAX_WEEKLY_SNAPSHOTS = 12;

const OPERATIONAL_KPI_RULES: OperationalKpiRule[] = [
    {
        id: "onboardingCoverage",
        label: "Onboarding coverage",
        unit: "percent",
        direction: "higher_better",
        warn: 60,
        critical: 40,
        action: "onboarding",
        actionLabel: "Открыть Onboarding",
    },
    {
        id: "goLiveReadiness",
        label: "Go-live readiness",
        unit: "percent",
        direction: "higher_better",
        warn: 70,
        critical: 50,
        action: "onboarding",
        actionLabel: "Проверить Go-live",
    },
    {
        id: "serviceStability",
        label: "Service stability",
        unit: "percent",
        direction: "higher_better",
        warn: 95,
        critical: 85,
        action: "portfolio",
        actionLabel: "Открыть риски",
    },
    {
        id: "decommissionShare",
        label: "Decommission share",
        unit: "percent",
        direction: "lower_better",
        warn: 30,
        critical: 45,
        action: "decommission",
        actionLabel: "Открыть Decommission",
    },
    {
        id: "changeFailure",
        label: "Publish failure rate",
        unit: "percent",
        direction: "lower_better",
        warn: 10,
        critical: 20,
        action: "changes",
        actionLabel: "Открыть Change Mgmt",
    },
    {
        id: "rollbackShare",
        label: "Rollback share",
        unit: "percent",
        direction: "lower_better",
        warn: 15,
        critical: 30,
        action: "changes",
        actionLabel: "Проверить rollback",
    },
    {
        id: "blockedSignals",
        label: "Blocked signals",
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

function toWeekKey(dateValue: string): string {
    const parsed = new Date(dateValue);
    if (Number.isNaN(parsed.getTime())) {
        return "invalid-week";
    }
    const yearStart = new Date(Date.UTC(parsed.getUTCFullYear(), 0, 1));
    const current = new Date(Date.UTC(parsed.getUTCFullYear(), parsed.getUTCMonth(), parsed.getUTCDate()));
    const dayOfYear = Math.floor((current.getTime() - yearStart.getTime()) / 86400000) + 1;
    const week = Math.ceil(dayOfYear / 7);
    return `${parsed.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
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

function safeParseWeeklySnapshots(rawValue: string | null): TenantsOperationalSnapshot[] {
    if (!rawValue) {
        return [];
    }
    try {
        const parsed = JSON.parse(rawValue) as TenantsOperationalSnapshot[];
        if (!Array.isArray(parsed)) {
            return [];
        }
        return parsed.filter((item) => item && typeof item === "object").slice(0, MAX_WEEKLY_SNAPSHOTS);
    } catch {
        return [];
    }
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

function kpiStatusBadgeClass(status: OperationalKpiStatus): string {
    if (status === "critical") {
        return "bg-red-100 text-red-700";
    }
    if (status === "warn") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-emerald-100 text-emerald-700";
}

function kpiCardClass(status: OperationalKpiStatus): string {
    if (status === "critical") {
        return "rounded-lg border border-red-300/80 bg-red-50/30 px-3 py-2";
    }
    if (status === "warn") {
        return "rounded-lg border border-amber-300/80 bg-amber-50/30 px-3 py-2";
    }
    return "rounded-lg border border-border/60 px-3 py-2";
}

function toCsvCell(value: string | number): string {
    const raw = String(value);
    if (raw.includes(",") || raw.includes("\"") || raw.includes("\n")) {
        return `"${raw.replaceAll("\"", "\"\"")}"`;
    }
    return raw;
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
    patch: components["schemas"]["BranchChangePatch"];
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
    const patch: components["schemas"]["BranchChangePatch"] = {};
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
    branch?: components["schemas"]["Branch"] | null,
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
    event: components["schemas"]["AuditEvent"],
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
    const queryClient = useQueryClient();
    const { errors: inlineErrors, reportError, reportInlineError, clearErrors } = useInlineErrorSummary();
    const reportValidationError = (message: string, code = "VALIDATION_ERROR") => {
        reportInlineError({ code, message });
        toast.error(message);
    };
    const [clientQuery, setClientQuery] = useState("");
    const [branchQuery, setBranchQuery] = useState("");
    const [companyQuery, setCompanyQuery] = useState("");
    const [tenantLifecycle, setTenantLifecycle] = useState<TenantLifecycleMode>("active");
    const [workspaceMode, setWorkspaceMode] = useState<TenantsWorkspaceMode>("all");
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
    const [branchChangePreview, setBranchChangePreview] = useState<components["schemas"]["BranchChangeResponse"] | null>(null);
    const [clientLifecyclePendingId, setClientLifecyclePendingId] = useState<string | null>(null);
    const [clientLifecycleDraft, setClientLifecycleDraft] = useState<ClientLifecycleDraftState | null>(null);
    const [clientLifecycleAuditById, setClientLifecycleAuditById] = useState<ClientLifecycleAuditMap>({});
    const [clientLifecycleAuditFilterById, setClientLifecycleAuditFilterById] = useState<Record<string, ClientLifecycleAuditFilter>>({});
    const [weeklySnapshots, setWeeklySnapshots] = useState<TenantsOperationalSnapshot[]>([]);
    const [runningMetricsSnapshotMode, setRunningMetricsSnapshotMode] = useState<"dry_run" | "execute" | null>(null);
    const [lastMetricsSnapshotJob, setLastMetricsSnapshotJob] = useState<components["schemas"]["OpsJobRecord"] | null>(null);
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
    const knownCompanies = useMemo(
        () => meData?.companies ?? [],
        [meData?.companies],
    );
    const knownBranches = useMemo(
        () => meData?.branches ?? [],
        [meData?.branches],
    );
    const selectedCompanyName = useMemo(() => {
        if (!selectedCompanyId) {
            return null;
        }
        return knownCompanies.find((company) => company.id === selectedCompanyId)?.name ?? null;
    }, [knownCompanies, selectedCompanyId]);
    const selectedBranchName = useMemo(() => {
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
        setWeeklySnapshots(safeParseWeeklySnapshots(readBrowserStorage(WEEKLY_SNAPSHOT_STORAGE_KEY)));
    }, []);

    useEffect(() => {
        writeBrowserStorage(
            LIFECYCLE_AUDIT_STORAGE_KEY,
            JSON.stringify(clientLifecycleAuditById),
        );
    }, [clientLifecycleAuditById]);

    useEffect(() => {
        writeBrowserStorage(
            WEEKLY_SNAPSHOT_STORAGE_KEY,
            JSON.stringify(weeklySnapshots.slice(0, MAX_WEEKLY_SNAPSHOTS)),
        );
    }, [weeklySnapshots]);

    const companiesQuery = useInfiniteQuery<
        components["schemas"]["CompanyListResponse"],
        Error,
        InfiniteData<components["schemas"]["CompanyListResponse"], string | undefined>,
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

    const clientsQuery = useInfiniteQuery<
        components["schemas"]["ClientListResponse"],
        Error,
        InfiniteData<components["schemas"]["ClientListResponse"], string | undefined>,
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
            selectedCompanyId,
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
                company_id: selectedCompanyId ?? undefined,
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
        components["schemas"]["BranchListResponse"],
        Error,
        InfiniteData<components["schemas"]["BranchListResponse"], string | undefined>,
        ["tenants-branches", string | undefined, string | null, TenantLifecycleMode],
        string | undefined
    >({
        queryKey: ["tenants-branches", branchQueryValue, selectedClientId, tenantLifecycle],
        queryFn: async ({ pageParam }) => {
            const cursor = typeof pageParam === "string" ? pageParam : undefined;
            const response = await adminApi.listBranches({
                cursor,
                limit: 20,
                q: branchQueryValue,
                client_id: selectedClientId ?? undefined,
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
        enabled: tenantsEnabled && tenantLifecycle === "active",
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
        queryKey: ["tenants-client-lifecycle-audit-api", selectedClientId],
        queryFn: async () => {
            if (!selectedClientId) {
                return [];
            }
            const response = await auditApi.list({
                entity_type: "client",
                entity_id: selectedClientId,
                limit: 50,
            });
            return response.data.items ?? [];
        },
        enabled: tenantsEnabled && !!selectedClientId,
        staleTime: 30000,
    });

    const companies = useMemo(
        () => companiesQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [],
        [companiesQuery.data],
    );
    const clients = useMemo(
        () => clientsQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [],
        [clientsQuery.data],
    );
    const clientsSummary = useMemo(
        () => clientsQuery.data?.pages[0]?.summary ?? null,
        [clientsQuery.data],
    );
    const branches = useMemo(
        () => branchesQuery.data?.pages.flatMap((page) => page.items ?? []) ?? [],
        [branchesQuery.data],
    );
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
        () => fleetAttentionQuery.data ?? null,
        [fleetAttentionQuery.data],
    );
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
    const operationalReport = useMemo(() => ({
        generatedAt: new Date().toISOString(),
        sourceWindow: operationalKpi.sourceWindow,
        workspaceMode,
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
    }), [operationalKpi.sourceWindow, operationalKpiValues, operationalKpiDrilldown, fleetAttention?.summary, workspaceMode, tenantLifecycle]);

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

    const setCompanyContext = (companyId?: string | null) => {
        setConsoleCompanyContext(companyId);
        refreshContext();
    };

    const setClientContext = (clientId?: string | null, companyId?: string | null) => {
        setConsoleClientContext(clientId, companyId);
        refreshContext();
    };

    const setBranchContext = (branchId?: string | null) => {
        setConsoleBranchContext(branchId);
        refreshContext();
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
            reportError(error);
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
            setClientContext(clientId, companyId);
            refreshTenants();
            toast.success("Клиент создан");
        } catch (error) {
            reportError(error);
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
            });
            const branchId = response.data.branch?.id;
            if (!branchId) {
                reportValidationError("Филиал создан, но branch_id не вернулся");
                return;
            }
            setBranchContext(branchId);
            refreshTenants();
            toast.success("Филиал создан и выбран в контексте");
        } catch (error) {
            reportError(error);
        } finally {
            setQuickCreateRunning(null);
        }
    };

    const openClientContextTarget = (target: "/" | "/integrations" | "/ops", clientId?: string | null, companyId?: string | null) => {
        if (!clientId) {
            return;
        }
        setClientContext(clientId, companyId);
        router.push(target);
    };

    const runActionQueueIntent = (item: ActionQueueItem) => {
        if (item.intent === "set_context") {
            setClientContext(item.clientId, item.companyId);
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

    const saveWeeklySnapshot = () => {
        const now = new Date().toISOString();
        const weekKey = toWeekKey(now);
        setWeeklySnapshots((previous) => {
            const next: TenantsOperationalSnapshot = {
                id: typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
                    ? crypto.randomUUID()
                    : `${Date.now()}`,
                weekKey,
                createdAt: now,
                report: operationalReport,
            };
            const withoutWeek = previous.filter((item) => item.weekKey !== weekKey);
            return [next, ...withoutWeek].slice(0, MAX_WEEKLY_SNAPSHOTS);
        });
        toast.success(`Weekly snapshot сохранён (${weekKey})`);
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
        if (!selectedClientId) {
            reportValidationError("Сначала выберите клиента в контексте");
            return;
        }
        setRunningMetricsSnapshotMode(mode);
        try {
            const response = await opsApi.runJob({
                job_type: "metrics_snapshot",
                mode,
                params: { days: 7 },
            });
            setLastMetricsSnapshotJob(response.data.job);
            toast.success(mode === "dry_run" ? "Snapshot dry-run выполнен" : "Snapshot execute выполнен");
        } catch (error) {
            reportError(error);
        } finally {
            setRunningMetricsSnapshotMode(null);
        }
    };

    const startCompanyEdit = (company: components["schemas"]["Company"]) => {
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

    const startClientEdit = (client: components["schemas"]["Client"]) => {
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

    const startBranchEdit = (branch: components["schemas"]["Branch"]) => {
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
        const payload: components["schemas"]["CompanyUpdateRequest"] = {};
        if (name !== companyEditor.originalName) {
            payload.name = name;
        }
        if (companyEditor.billingInfo.trim() !== companyEditor.originalBillingInfo.trim()) {
            payload.billing_info = billing.value ?? {};
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
            reportError(error);
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
        const payload: components["schemas"]["ClientUpdateRequest"] = {};
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
            reportError(error);
        } finally {
            setSavingClient(false);
        }
    };

    const isClientArchived = (client: components["schemas"]["Client"]) => {
        const lifecycleValue = (client.lifecycle_state ?? "").trim().toLowerCase();
        if (lifecycleValue) {
            return lifecycleValue === "archived";
        }
        return (client.status ?? "").trim().toLowerCase() !== "active";
    };

    const openClientLifecycleAction = (
        client: components["schemas"]["Client"],
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
            const parsed = reportError(error) as
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
            reportError(error);
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
            reportError(error);
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
            reportError(error);
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

    const showPortfolio = workspaceMode === "all" || workspaceMode === "portfolio";
    const showOnboarding = workspaceMode === "all" || workspaceMode === "onboarding";
    const showChangeManagement = workspaceMode === "all" || workspaceMode === "changes";
    const showDecommission = workspaceMode === "all" || workspaceMode === "decommission";
    const showClientsSection = showPortfolio || showDecommission;
    const decommissionFocused = workspaceMode === "decommission";

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
                <h1 className="text-2xl font-bold" data-testid="tenants-title">Тенанты</h1>
                <div className="text-xs text-muted-foreground">
                    Контекст: {selectedCompanyName ?? "—"} / {meData?.client?.name ?? "—"} / {selectedBranchName ?? "—"}
                    {isPlatformPreset ? (
                        <span>
                            {" · IDs: "}
                            {selectedCompanyId ?? "—"} / {selectedClientId ?? "—"} / {selectedBranchId ?? "—"}
                        </span>
                    ) : null}
                </div>
                {inlineErrors.length > 0 ? (
                    <section className="rounded-lg border border-red-300/60 bg-red-50 p-3" data-testid="tenants-error-summary">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="text-sm font-semibold text-red-900">Ошибки последних операций</div>
                            <button className="btn-ghost" onClick={clearErrors}>Очистить</button>
                        </div>
                        <div className="mt-1 text-xs text-red-900/80">
                            Исправьте отмеченные поля и повторите действие. Для API ошибок используйте `trace` из записи ниже.
                        </div>
                        <div className="mt-2 space-y-2">
                            {inlineErrors.map((error) => (
                                <div key={error.id} className="rounded-md border border-red-200/80 bg-background/90 p-2 text-xs">
                                    <div className="font-mono text-red-900">{error.code}</div>
                                    <div className="mt-1 text-foreground">{error.message}</div>
                                    <div className="mt-1 text-muted-foreground">
                                        {new Date(error.capturedAt).toLocaleString("ru-RU")}
                                        {error.traceId ? ` · trace: ${error.traceId}` : ""}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>
                ) : null}
                <div className="rounded-lg border border-border/60 bg-card p-3" data-testid="tenants-workspace-modes">
                    <div className="text-xs text-muted-foreground mb-2">Рабочая зона Tenants:</div>
                    <div className="flex flex-wrap items-center gap-2">
                        <button
                            className={workspaceMode === "all" ? "btn-primary" : "btn-ghost"}
                            onClick={() => setWorkspaceMode("all")}
                            data-testid="tenants-mode-all"
                        >
                            Все зоны
                        </button>
                        <button
                            className={workspaceMode === "portfolio" ? "btn-primary" : "btn-ghost"}
                            onClick={() => setWorkspaceMode("portfolio")}
                            data-testid="tenants-mode-portfolio"
                        >
                            Портфель
                        </button>
                        <button
                            className={workspaceMode === "onboarding" ? "btn-primary" : "btn-ghost"}
                            onClick={() => setWorkspaceMode("onboarding")}
                            data-testid="tenants-mode-onboarding"
                        >
                            Онбординг
                        </button>
                        <button
                            className={workspaceMode === "changes" ? "btn-primary" : "btn-ghost"}
                            onClick={() => setWorkspaceMode("changes")}
                            data-testid="tenants-mode-changes"
                        >
                            Изменения
                        </button>
                        <button
                            className={workspaceMode === "decommission" ? "btn-primary" : "btn-ghost"}
                            onClick={() => setWorkspaceMode("decommission")}
                            data-testid="tenants-mode-decommission"
                        >
                            Decommission
                        </button>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2" data-testid="tenants-view-preset">
                        <span className="text-xs text-muted-foreground">Профиль интерфейса:</span>
                        <button
                            className={viewPreset === "operator" ? "btn-primary" : "btn-ghost"}
                            onClick={() => setViewPreset("operator")}
                            data-testid="tenants-view-preset-operator"
                        >
                            Operator
                        </button>
                        <button
                            className={viewPreset === "platform" ? "btn-primary" : "btn-ghost"}
                            onClick={() => setViewPreset("platform")}
                            disabled={!canSwitchViewPreset}
                            data-testid="tenants-view-preset-platform"
                        >
                            Platform
                        </button>
                    </div>
                </div>
                <div className="rounded-lg border border-border/60 bg-muted/20 p-3" data-testid="tenants-workspace-guide">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-2">
                        Операционный guide
                    </div>
                    <div className="text-xs text-muted-foreground">
                        Портфель: риск-панель и состав клиентов. Онбординг: запуск нового филиала. Изменения:
                        controlled change + draft/validate/publish. Decommission: архив/восстановление с подтверждением.
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                        Перед Go-Live проверьте: `instance_id`, `phone`, `timezone`, `telegram_chat_id`, `knowledge_tag`,
                        `payment_status`, активный reference pack.
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                        Порядок работы: `Action Queue`, затем контекст клиента, затем профильная зона, затем подтверждение результата через trace/audit.
                    </div>
                </div>
                {canWriteTenants ? (
                    <section className="rounded-lg border border-border/60 bg-card p-4" data-testid="tenants-quick-create">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                                <h2 className="text-sm font-semibold">Quick Create Wizard</h2>
                                <p className="text-xs text-muted-foreground">
                                    Быстрый поток: {"company -> client -> branch"} с автоматическим установлением контекста.
                                </p>
                            </div>
                            <button
                                className="btn-ghost"
                                onClick={() => router.push("/company-workspace")}
                            >
                                Company Workspace
                            </button>
                        </div>
                        <div className="mt-3 grid gap-3 md:grid-cols-3">
                            <div className="rounded-lg border border-border/60 bg-background p-3">
                                <div className="text-xs font-semibold">1. Компания</div>
                                <label className="mt-2 block text-xs text-muted-foreground">
                                    name
                                    <input
                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={quickCreateForm.companyName}
                                        onChange={(event) =>
                                            setQuickCreateForm((prev) => ({ ...prev, companyName: event.target.value }))
                                        }
                                        placeholder="Beauty Group"
                                    />
                                </label>
                                <button
                                    className="btn-primary mt-3"
                                    onClick={() => void handleQuickCreateCompany()}
                                    disabled={quickCreateRunning !== null}
                                >
                                    {quickCreateRunning === "company" ? "Создание..." : "Создать компанию"}
                                </button>
                                <div className="mt-2 text-[11px] text-muted-foreground">
                                    company_id: <span className="font-mono">{quickCreateCompanyId || "—"}</span>
                                </div>
                            </div>

                            <div className="rounded-lg border border-border/60 bg-background p-3">
                                <div className="text-xs font-semibold">2. Клиент</div>
                                <label className="mt-2 block text-xs text-muted-foreground">
                                    slug
                                    <input
                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={quickCreateForm.clientSlug}
                                        onChange={(event) =>
                                            setQuickCreateForm((prev) => ({ ...prev, clientSlug: event.target.value.toLowerCase() }))
                                        }
                                        placeholder="beauty_group_almaty"
                                    />
                                </label>
                                <button
                                    className="btn-primary mt-3"
                                    onClick={() => void handleQuickCreateClient()}
                                    disabled={quickCreateRunning !== null}
                                >
                                    {quickCreateRunning === "client" ? "Создание..." : "Создать клиента"}
                                </button>
                                <div className="mt-2 text-[11px] text-muted-foreground">
                                    client_id: <span className="font-mono">{quickCreateClientId || "—"}</span>
                                </div>
                            </div>

                            <div className="rounded-lg border border-border/60 bg-background p-3">
                                <div className="text-xs font-semibold">3. Филиал</div>
                                <div className="mt-2 grid gap-2">
                                    <input
                                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={quickCreateForm.branchName}
                                        onChange={(event) =>
                                            setQuickCreateForm((prev) => ({ ...prev, branchName: event.target.value }))
                                        }
                                        placeholder="Branch name"
                                    />
                                    <input
                                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={quickCreateForm.branchSlug}
                                        onChange={(event) =>
                                            setQuickCreateForm((prev) => ({ ...prev, branchSlug: event.target.value.toLowerCase() }))
                                        }
                                        placeholder="branch_slug"
                                    />
                                    <input
                                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={quickCreateForm.branchTimezone}
                                        onChange={(event) =>
                                            setQuickCreateForm((prev) => ({ ...prev, branchTimezone: event.target.value }))
                                        }
                                        placeholder="Asia/Almaty"
                                    />
                                    <input
                                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={quickCreateForm.branchPhone}
                                        onChange={(event) =>
                                            setQuickCreateForm((prev) => ({ ...prev, branchPhone: event.target.value }))
                                        }
                                        placeholder="+77000000000"
                                    />
                                    <input
                                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={quickCreateForm.branchInstanceId}
                                        onChange={(event) =>
                                            setQuickCreateForm((prev) => ({ ...prev, branchInstanceId: event.target.value }))
                                        }
                                        placeholder="instance-xxxxxxxx"
                                    />
                                </div>
                                <button
                                    className="btn-primary mt-3"
                                    onClick={() => void handleQuickCreateBranch()}
                                    disabled={quickCreateRunning !== null}
                                >
                                    {quickCreateRunning === "branch" ? "Создание..." : "Создать филиал"}
                                </button>
                            </div>
                        </div>
                    </section>
                ) : null}
                <TenantsActionQueuePanel
                    items={actionQueue}
                    refreshing={fleetAttentionQuery.isFetching || recentBranchChangesKpiQuery.isFetching || clientsQuery.isFetching}
                    onRefresh={() => {
                        fleetAttentionQuery.refetch();
                        recentBranchChangesKpiQuery.refetch();
                        clientsQuery.refetch();
                    }}
                    onRunIntent={runActionQueueIntent}
                    onSetClientContext={setClientContext}
                />
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
                {showPortfolio && tenantLifecycle === "active" ? (
                    <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-operational-kpi">
                        <div className="flex items-start justify-between gap-4 mb-4">
                            <div>
                                <h2 className="text-lg font-semibold">Операционные KPI</h2>
                                <p className="text-sm text-muted-foreground">
                                    Прокси-метрики: портфель + attention + branch changes (последние 100 изменений)
                                </p>
                            </div>
                            <div className="flex flex-wrap items-center gap-2" data-testid="tenants-kpi-export-controls">
                                <button
                                    className="btn-ghost"
                                    onClick={() => {
                                        fleetAttentionQuery.refetch();
                                        recentBranchChangesKpiQuery.refetch();
                                        selectedClientAuditQuery.refetch();
                                    }}
                                    disabled={fleetAttentionQuery.isFetching || recentBranchChangesKpiQuery.isFetching}
                                >
                                    {fleetAttentionQuery.isFetching || recentBranchChangesKpiQuery.isFetching ? "Обновление..." : "Обновить KPI"}
                                </button>
                                <button
                                    className="btn-ghost"
                                    onClick={() => exportOperationalReport("json")}
                                    data-testid="tenants-kpi-export-json"
                                >
                                    Экспорт JSON
                                </button>
                                <button
                                    className="btn-ghost"
                                    onClick={() => exportOperationalReport("csv")}
                                    data-testid="tenants-kpi-export-csv"
                                >
                                    Экспорт CSV
                                </button>
                                <button
                                    className="btn-ghost"
                                    onClick={saveWeeklySnapshot}
                                    data-testid="tenants-kpi-save-weekly-snapshot"
                                >
                                    Weekly snapshot
                                </button>
                            </div>
                        </div>
                        <div className="mb-3 text-xs text-muted-foreground">
                            окно расчета branch-change: {operationalKpi.sourceWindow} · published: {operationalKpi.publishedChanges} · publish_failed: {operationalKpi.publishFailedChanges} · rolled_back: {operationalKpi.rolledBackChanges} · critical KPI: {criticalKpiCount} · warn KPI: {warnKpiCount}
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                            <div className={kpiCardClass(operationalKpiById.get("onboardingCoverage")?.status ?? "ok")} data-testid="tenants-kpi-onboarding-coverage">
                                <div className="text-xs text-muted-foreground">Onboarding coverage (proxy)</div>
                                <div className="text-xl font-semibold">{operationalKpi.onboardingCoveragePct}%</div>
                                <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(operationalKpiById.get("onboardingCoverage")?.status ?? "ok")}`}>
                                    {operationalKpiById.get("onboardingCoverage")?.status ?? "ok"}
                                </div>
                            </div>
                            <div className={kpiCardClass(operationalKpiById.get("goLiveReadiness")?.status ?? "ok")} data-testid="tenants-kpi-go-live-readiness">
                                <div className="text-xs text-muted-foreground">Go-live readiness (proxy)</div>
                                <div className="text-xl font-semibold">{operationalKpi.goLiveReadinessPct}%</div>
                                <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(operationalKpiById.get("goLiveReadiness")?.status ?? "ok")}`}>
                                    {operationalKpiById.get("goLiveReadiness")?.status ?? "ok"}
                                </div>
                            </div>
                            <div className={kpiCardClass(operationalKpiById.get("serviceStability")?.status ?? "ok")} data-testid="tenants-kpi-service-stability">
                                <div className="text-xs text-muted-foreground">Service stability</div>
                                <div className="text-xl font-semibold">{operationalKpi.serviceStabilityPct}%</div>
                                <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(operationalKpiById.get("serviceStability")?.status ?? "ok")}`}>
                                    {operationalKpiById.get("serviceStability")?.status ?? "ok"}
                                </div>
                            </div>
                            <div className={kpiCardClass(operationalKpiById.get("decommissionShare")?.status ?? "ok")} data-testid="tenants-kpi-decommission-share">
                                <div className="text-xs text-muted-foreground">Decommission share</div>
                                <div className="text-xl font-semibold">{operationalKpi.decommissionSharePct}%</div>
                                <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(operationalKpiById.get("decommissionShare")?.status ?? "ok")}`}>
                                    {operationalKpiById.get("decommissionShare")?.status ?? "ok"}
                                </div>
                            </div>
                            <div className={kpiCardClass(operationalKpiById.get("changeFailure")?.status ?? "ok")} data-testid="tenants-kpi-change-failure">
                                <div className="text-xs text-muted-foreground">Publish failure rate (proxy)</div>
                                <div className="text-xl font-semibold">{operationalKpi.changeFailurePct}%</div>
                                <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(operationalKpiById.get("changeFailure")?.status ?? "ok")}`}>
                                    {operationalKpiById.get("changeFailure")?.status ?? "ok"}
                                </div>
                            </div>
                            <div className={kpiCardClass(operationalKpiById.get("rollbackShare")?.status ?? "ok")} data-testid="tenants-kpi-rollback-share">
                                <div className="text-xs text-muted-foreground">Rollback share (proxy)</div>
                                <div className="text-xl font-semibold">{operationalKpi.rollbackSharePct}%</div>
                                <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(operationalKpiById.get("rollbackShare")?.status ?? "ok")}`}>
                                    {operationalKpiById.get("rollbackShare")?.status ?? "ok"}
                                </div>
                            </div>
                            <div className={kpiCardClass(operationalKpiById.get("blockedSignals")?.status ?? "ok")} data-testid="tenants-kpi-blocked-signals">
                                <div className="text-xs text-muted-foreground">Blocked signals</div>
                                <div className="text-xl font-semibold">{operationalKpi.blockedSignalsCount}</div>
                                <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(operationalKpiById.get("blockedSignals")?.status ?? "ok")}`}>
                                    {operationalKpiById.get("blockedSignals")?.status ?? "ok"}
                                </div>
                            </div>
                        </div>

                        <div className="mt-4 rounded-lg border border-border/60 bg-background p-3" data-testid="tenants-kpi-drilldown">
                            <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                Threshold drill-down
                            </div>
                            <div className="space-y-2">
                                {operationalKpiDrilldown.map((item) => (
                                    <div
                                        key={item.id}
                                        className="rounded-lg border border-border/60 p-2"
                                        data-testid="tenants-kpi-drilldown-row"
                                    >
                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                            <div className="font-medium text-sm">{item.label}</div>
                                            <div className="flex items-center gap-2 text-xs">
                                                <span className={`inline-flex rounded-full px-2 py-0.5 font-semibold ${kpiStatusBadgeClass(item.status)}`}>
                                                    {item.status}
                                                </span>
                                                <span className="font-medium">{item.displayValue}</span>
                                            </div>
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            {item.reason}
                                        </div>
                                        <div className="mt-1 text-xs text-muted-foreground">
                                            threshold: {item.thresholdLabel}
                                        </div>
                                        <div className="mt-2">
                                            <button
                                                className="btn-ghost"
                                                onClick={() => runKpiAction(item.action)}
                                                data-testid={`tenants-kpi-action-${item.id}`}
                                            >
                                                {item.actionLabel}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="mt-4 grid gap-3 lg:grid-cols-2">
                            <div className="rounded-lg border border-border/60 bg-background p-3" data-testid="tenants-kpi-alert-hooks">
                                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                    Alert hooks
                                </div>
                                <div className="text-xs text-muted-foreground">
                                    <span data-testid="tenants-kpi-alert-severity">severity: {alertHookPayload.severity}</span> · breaches: {alertHookPayload.breaches.length}
                                </div>
                                <div className="mt-2 flex flex-wrap items-center gap-2">
                                    <button
                                        className="btn-ghost"
                                        onClick={copyAlertHookPayload}
                                        data-testid="tenants-kpi-alert-copy"
                                    >
                                        Скопировать payload
                                    </button>
                                    <button
                                        className="btn-ghost"
                                        onClick={() => runMetricsSnapshotHook("dry_run")}
                                        disabled={runningMetricsSnapshotMode !== null}
                                        data-testid="tenants-kpi-alert-dryrun"
                                    >
                                        {runningMetricsSnapshotMode === "dry_run" ? "Dry-run..." : "Snapshot dry-run"}
                                    </button>
                                    <button
                                        className="btn-ghost"
                                        onClick={() => runMetricsSnapshotHook("execute")}
                                        disabled={runningMetricsSnapshotMode !== null}
                                        data-testid="tenants-kpi-alert-execute"
                                    >
                                        {runningMetricsSnapshotMode === "execute" ? "Execute..." : "Snapshot execute"}
                                    </button>
                                </div>
                                {lastMetricsSnapshotJob ? (
                                    <div className="mt-2 text-xs text-muted-foreground" data-testid="tenants-kpi-alert-last-job">
                                        job: {lastMetricsSnapshotJob.job_type} · mode: {lastMetricsSnapshotJob.mode} · status: {lastMetricsSnapshotJob.status}
                                    </div>
                                ) : null}
                            </div>

                            <div className="rounded-lg border border-border/60 bg-background p-3" data-testid="tenants-kpi-weekly-snapshots">
                                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                    Weekly snapshots
                                </div>
                                {weeklySnapshots.length === 0 ? (
                                    <div className="text-xs text-muted-foreground">
                                        Снимков пока нет. Сохраните первый weekly snapshot.
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {weeklySnapshots.slice(0, 4).map((item, index) => {
                                            const previous = weeklySnapshots[index + 1];
                                            const delta = previous
                                                ? item.report.kpi.changeFailure - previous.report.kpi.changeFailure
                                                : 0;
                                            return (
                                                <div key={item.id} className="rounded border border-border/50 px-2 py-1 text-xs">
                                                    <div className="font-medium">
                                                        {item.weekKey} · {formatDateTimeLabel(item.createdAt)}
                                                    </div>
                                                    <div className="text-muted-foreground">
                                                        change_failure: {item.report.kpi.changeFailure}% {previous ? `(Δ ${delta >= 0 ? "+" : ""}${delta}%)` : ""}
                                                    </div>
                                                    <div className="text-muted-foreground">
                                                        blocked_signals: {item.report.kpi.blockedSignals} · service_stability: {item.report.kpi.serviceStability}%
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        </div>
                    </section>
                ) : null}

                {showPortfolio && tenantLifecycle === "active" ? (
                    <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-fleet-attention">
                        <div className="flex items-start justify-between gap-4 mb-4">
                            <div>
                                <h2 className="text-lg font-semibold">Риски и внимание</h2>
                                <p className="text-sm text-muted-foreground">
                                    Операционные риски по активным клиентам (топ по score)
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    scope: reference branches (шум тестовых веток исключен)
                                </p>
                            </div>
                            <button
                                className="btn-ghost"
                                onClick={() => fleetAttentionQuery.refetch()}
                                disabled={fleetAttentionQuery.isFetching}
                            >
                                {fleetAttentionQuery.isFetching ? "Обновление..." : "Обновить"}
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
                            {fleetAttentionQuery.isLoading ? (
                                <div className="text-sm text-muted-foreground">Загрузка панели рисков...</div>
                            ) : fleetAttentionQuery.isError ? (
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
                                            reference scope: {item.reference_branch_ids?.length ?? 0} · {formatReferenceScopeReason(item.reference_branch_reason)}
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
                                                onClick={() => setClientContext(item.client_id, item.company_id)}
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
                                                            Advanced JSON (expert): billing_info
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
                            <h2 className="text-lg font-semibold">Decommission</h2>
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
                        Для decommission используйте действия `Архивировать/Восстановить` в карточке клиента ниже.
                    </div>
                </section>
                ) : null}

                {showClientsSection ? (
                <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-clients-section">
                    <div className="flex items-center justify-between gap-4 mb-4">
                        <div>
                            <h2 className="text-lg font-semibold">
                                {decommissionFocused ? "Клиенты (Decommission)" : "Клиенты"}
                            </h2>
                            <p className="text-sm text-muted-foreground">
                                {clientsQuery.isLoading ? "—" : `${clients.length} всего`}
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
                            {selectedCompanyId ? (
                                <div className="mt-1 text-xs text-muted-foreground">
                                    фильтр по компании из контекста: {selectedCompanyId}
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
                            >
                                <option value="all">Сервис: все</option>
                                <option value="ok">стабильно</option>
                                <option value="degraded">деградация</option>
                                <option value="attention">внимание</option>
                            </select>
                        </div>
                    </div>
                    <div className="space-y-3">
                        {clientsQuery.isLoading ? (
                            <div className="text-sm text-muted-foreground">Загрузка клиентов...</div>
                        ) : clientsQuery.isError ? (
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
                                const apiLifecycleAudit = clientIdKey && clientIdKey === selectedClientId
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
                                                lifecycle: {formatStateLabel(client.lifecycle_state, FLEET_LIFECYCLE_LABELS)} · payment: {formatStateLabel(client.payment_status, FLEET_PAYMENT_LABELS)} · service: {formatStateLabel(client.service_state, FLEET_SERVICE_LABELS)}
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                owner: {client.owner_name ?? "—"} · next: {client.next_action ?? "—"}
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                филиалы: активные {client.active_branches ?? 0}/{client.total_branches ?? 0} · деградация {client.degraded_branches ?? 0} · готовы к запуску {client.go_live_ready_branches ?? 0}
                                            </div>
                                            <div className="text-xs text-muted-foreground">
                                                reference scope: {client.reference_branch_ids?.length ?? 0} · {formatReferenceScopeReason(client.reference_branch_reason)}
                                            </div>
                                            {lifecycleAuditHistory.length > 0 || clientIdKey === selectedClientId ? (
                                                <div className="mt-2 rounded-lg border border-border/60 bg-background px-3 py-2 text-xs" data-testid="tenants-client-lifecycle-audit">
                                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                                        <div className="font-medium">
                                                            Lifecycle timeline (session + API)
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
                                                                all
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
                                                                success
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
                                                                error
                                                            </button>
                                                            {clientIdKey === selectedClientId ? (
                                                                <button
                                                                    className="btn-ghost"
                                                                    onClick={() => selectedClientAuditQuery.refetch()}
                                                                    disabled={selectedClientAuditQuery.isFetching}
                                                                    data-testid="tenants-client-lifecycle-audit-refresh"
                                                                >
                                                                    {selectedClientAuditQuery.isFetching ? "Обновление..." : "Обновить API"}
                                                                </button>
                                                            ) : null}
                                                        </div>
                                                    </div>
                                                    <div className="mt-1 text-muted-foreground">
                                                        источник: session cache + API audit{clientIdKey === selectedClientId ? "" : " (API audit доступен в текущем client context)"}
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
                                                onClick={() => setClientContext(client.id, client.company_id)}
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
                    {clientsQuery.hasNextPage ? (
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
                                {branchesQuery.isLoading ? "—" : `${branches.length} всего`}
                            </p>
                            {selectedClientId ? (
                                <div className="mt-1 text-xs text-muted-foreground">
                                    фильтр по клиенту из контекста: {selectedClientId}
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
                        {branchesQuery.isLoading ? (
                            <div className="text-sm text-muted-foreground">Загрузка филиалов...</div>
                        ) : branchesQuery.isError ? (
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
                                            <div className="text-xs text-muted-foreground">
                                                {branch.instance_id ? `instance_id: ${branch.instance_id}` : "instance_id: —"}
                                            </div>
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
                                                onClick={() => setBranchContext(branch.id)}
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
                                                        <div className="font-medium">Impact preview</div>
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
                            <div className="font-medium mb-1">Impact preview</div>
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
                    <ProvisioningWizard session={session} accessSection="tenants" />
                </div>
            ) : null}
        </div>
    );
}
