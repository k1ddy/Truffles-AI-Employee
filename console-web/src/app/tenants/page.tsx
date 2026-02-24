"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import type { components } from "@/types/api.generated";
import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";
import TenantsActionQueuePanel, { type TenantsActionQueueItem } from "@/components/TenantsActionQueuePanel";
import TenantsBranchChangeManagementPanel from "@/components/TenantsBranchChangeManagementPanel";
import TenantsClientLifecycleModal from "@/components/TenantsClientLifecycleModal";
import TenantsClientsPanel from "@/components/TenantsClientsPanel";
import TenantsDecommissionPanel from "@/components/TenantsDecommissionPanel";
import TenantsFleetAttentionPanel from "@/components/TenantsFleetAttentionPanel";
import TenantsOperationalKpiPanel from "@/components/TenantsOperationalKpiPanel";
import TenantsPortfolioCompaniesPanel from "@/components/TenantsPortfolioCompaniesPanel";
import TenantsQuickCreatePanel from "@/components/TenantsQuickCreatePanel";
import TenantsScopedErrorSummary from "@/components/TenantsScopedErrorSummary";
import type { TenantsSensitiveAction } from "@/components/TenantsSensitiveIdCell";
import TenantsTopControls, { type TenantsFilterOption } from "@/components/TenantsTopControls";
import {
    adminApi,
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
} from "@/lib/console-context-storage";
import { useInlineErrorSummary } from "@/lib/use-inline-error-summary";
import {
    asPercent,
    buildOperationalKpiDrilldown,
    formatOptionalHours,
    formatOptionalPercent,
    type OperationalKpiDrilldown,
    type OperationalKpiId,
    type OperationalKpiStatus,
} from "./operational-kpi";
import { useTenantsDataQueries } from "./use-tenants-data-queries";
import { useTenantsActions } from "./use-tenants-actions";
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

    const {
        companiesQuery,
        tenantsPortfolioQuery,
        tenantsCompanyCockpitQuery,
        clientsQuery,
        branchesQuery,
        fleetAttentionQuery,
        branchChangesQuery,
        recentBranchChangesKpiQuery,
        selectedClientAuditQuery,
        weeklySnapshotsServerQuery,
    } = useTenantsDataQueries<TenantsOperationalSnapshot>({
        tenantsEnabled,
        companyQueryValue,
        clientQueryValue,
        branchQueryValue,
        pageFilterCompanyId,
        pageFilterClientId,
        pageFilterBranchId,
        tenantLifecycle,
        fleetLifecycleFilter,
        fleetPaymentFilter,
        fleetServiceFilter,
        branchEditorId: branchEditor?.id,
        maxWeeklySnapshots: MAX_WEEKLY_SNAPSHOTS,
        mapWeeklySnapshotRecordToViewModel,
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

    const {
        setCompanyContext,
        setClientContext,
        setBranchContext,
        clearContextLens,
        setClientContextAndPageFilters,
        setBranchContextAndPageFilters,
        applyContextToPageFilters,
        openClientContextTarget,
        runActionQueueIntent,
        runKpiAction,
        handleQuickCreateCompany,
        handleQuickCreateClient,
        handleQuickCreateBranch,
    } = useTenantsActions({
        clientCompanyIdById,
        branchClientIdById,
        branchCompanyIdById,
        pageFilterCompanyId,
        pageFilterClientId,
        applyScopeToPageFilters,
        refreshContext,
        reportValidationError,
        setWorkspaceMode,
        setTenantLifecycle,
        navigateTo: (target) => router.push(target),
        quickCreateForm,
        quickCreateCompanyId,
        quickCreateClientId,
        setQuickCreateForm,
        setQuickCreateRunning,
        refreshTenants,
        reportProvisioningError,
        slugInputPattern: SLUG_INPUT_PATTERN,
        branchPhoneInputPattern: BRANCH_PHONE_INPUT_PATTERN,
        isValidTimezoneName,
    });

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
            toast.success("Данные уведомления скопированы");
        } catch {
            reportValidationError("Не удалось скопировать данные уведомления");
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
                    <TenantsFleetAttentionPanel
                        fleetAttention={fleetAttention}
                        loading={fleetAttentionLoading}
                        errored={fleetAttentionErrored}
                        refreshing={tenantsPortfolioQuery.isFetching || fleetAttentionQuery.isFetching}
                        onRefresh={() => {
                            tenantsPortfolioQuery.refetch();
                            fleetAttentionQuery.refetch();
                        }}
                        attentionLevelClass={attentionLevelClass}
                        formatLifecycleLabel={(value) => formatStateLabel(value, FLEET_LIFECYCLE_LABELS)}
                        formatServiceLabel={(value) => formatStateLabel(value, FLEET_SERVICE_LABELS)}
                        formatReferenceScopeReason={formatReferenceScopeReason}
                        onSetClientContext={setClientContextAndPageFilters}
                        onOpenIntegrations={(clientId, companyId) => openClientContextTarget("/integrations", clientId, companyId)}
                        onOpenCases={(clientId, companyId) => openClientContextTarget("/", clientId, companyId)}
                    />
                ) : null}

                {showPortfolio ? (
                    <TenantsPortfolioCompaniesPanel
                        companies={companies}
                        loading={companiesQuery.isLoading}
                        errored={companiesQuery.isError}
                        query={companyQuery}
                        onQueryChange={setCompanyQuery}
                        isPlatformPreset={isPlatformPreset}
                        canWriteTenants={canWriteTenants}
                        selectedCompanyId={selectedCompanyId}
                        companyEditor={companyEditor}
                        savingCompany={savingCompany}
                        hasNextPage={Boolean(companiesQuery.hasNextPage)}
                        isFetchingNextPage={companiesQuery.isFetchingNextPage}
                        onFetchNextPage={() => companiesQuery.fetchNextPage()}
                        onStartEdit={startCompanyEdit}
                        onSetContext={setCompanyContext}
                        onCancelEdit={() => setCompanyEditor(null)}
                        onSaveEdit={handleSaveCompany}
                        onChangeEditorName={(value) => {
                            setCompanyEditor((prev) => (prev ? { ...prev, name: value } : prev));
                        }}
                        onChangeEditorBillingInfo={(value) => {
                            setCompanyEditor((prev) => (prev ? { ...prev, billingInfo: value } : prev));
                        }}
                    />
                ) : null}

                {showDecommission ? (
                    <TenantsDecommissionPanel
                        tenantLifecycle={tenantLifecycle}
                        onTenantLifecycleChange={setTenantLifecycle}
                    />
                ) : null}

                {showClientsSection ? (
                    <TenantsClientsPanel
                        decommissionFocused={decommissionFocused}
                        clientsLoading={clientsLoading}
                        clientsErrored={clientsErrored}
                        clients={clients}
                        clientsSummary={clientsSummary}
                        pageFilterCompanyId={pageFilterCompanyId}
                        clientQuery={clientQuery}
                        onClientQueryChange={setClientQuery}
                        fleetLifecycleFilter={fleetLifecycleFilter}
                        onFleetLifecycleFilterChange={setFleetLifecycleFilter}
                        fleetPaymentFilter={fleetPaymentFilter}
                        onFleetPaymentFilterChange={setFleetPaymentFilter}
                        fleetServiceFilter={fleetServiceFilter}
                        onFleetServiceFilterChange={setFleetServiceFilter}
                        isPlatformPreset={isPlatformPreset}
                        canWriteTenants={canWriteTenants}
                        selectedClientId={selectedClientId}
                        pageFilterClientId={pageFilterClientId}
                        clientEditor={clientEditor}
                        savingClient={savingClient}
                        knownCompanies={knownCompanies}
                        clientLifecyclePendingId={clientLifecyclePendingId}
                        clientLifecycleAuditFilterById={clientLifecycleAuditFilterById}
                        clientLifecycleAuditById={clientLifecycleAuditById}
                        selectedClientApiAuditEntries={selectedClientApiAuditEntries}
                        selectedClientAuditIsFetching={selectedClientAuditQuery.isFetching}
                        onRefreshSelectedClientAudit={() => selectedClientAuditQuery.refetch()}
                        onSetClientLifecycleAuditFilter={(clientId, filter) => {
                            setClientLifecycleAuditFilterById((prev) => ({ ...prev, [clientId]: filter }));
                        }}
                        mergeLifecycleAuditEntries={mergeLifecycleAuditEntries}
                        formatLifecycleLabel={(value) => formatStateLabel(value, FLEET_LIFECYCLE_LABELS)}
                        formatPaymentLabel={(value) => formatStateLabel(value, FLEET_PAYMENT_LABELS)}
                        formatServiceLabel={(value) => formatStateLabel(value, FLEET_SERVICE_LABELS)}
                        formatReferenceScopeReason={formatReferenceScopeReason}
                        formatDateTimeLabel={formatDateTimeLabel}
                        isClientArchived={isClientArchived}
                        onStartClientEdit={startClientEdit}
                        onOpenClientLifecycleAction={openClientLifecycleAction}
                        onSetClientContext={setClientContextAndPageFilters}
                        onClientEditorSlugChange={(value) => {
                            setClientEditor((prev) => (prev ? { ...prev, slug: value } : prev));
                        }}
                        onClientEditorCompanyChange={(value) => {
                            setClientEditor((prev) => (prev ? { ...prev, companyId: value } : prev));
                        }}
                        onSaveClientEdit={handleSaveClient}
                        onCancelClientEdit={() => setClientEditor(null)}
                        clientsUsingServerContract={clientsUsingServerContract}
                        clientsHasNextPage={Boolean(clientsQuery.hasNextPage)}
                        clientsFetchingNextPage={clientsQuery.isFetchingNextPage}
                        onFetchNextClientsPage={() => clientsQuery.fetchNextPage()}
                    />
                ) : null}

                {showChangeManagement ? (
                    <TenantsBranchChangeManagementPanel
                        branchesLoading={branchesLoading}
                        branchesErrored={branchesErrored}
                        branches={branches}
                        pageFilterClientId={pageFilterClientId}
                        selectedClientName={selectedClientName}
                        branchQuery={branchQuery}
                        onBranchQueryChange={setBranchQuery}
                        isPlatformPreset={isPlatformPreset}
                        canWriteTenants={canWriteTenants}
                        selectedBranchId={selectedBranchId}
                        contextScope={effectiveWorkspaceMode}
                        onAuditSensitiveAccess={auditSensitiveAccess}
                        onStartBranchEdit={startBranchEdit}
                        onSetBranchContext={(branch) =>
                            setBranchContextAndPageFilters({
                                branchId: branch.id,
                                clientId: readBranchClientId(branch),
                                companyId: readBranchCompanyId(branch),
                            })
                        }
                        branchEditor={branchEditor}
                        onPatchBranchEditor={(patch) => {
                            setBranchEditor((prev) => (prev ? { ...prev, ...patch } : prev));
                        }}
                        requiresBranchConfirmation={requiresBranchConfirmation}
                        savingBranch={savingBranch}
                        publishingBranchChange={publishingBranchChange}
                        rollingBackBranchChange={rollingBackBranchChange}
                        onPreviewBranchChange={handlePreviewBranchChange}
                        onPublishBranchChange={handlePublishBranchChange}
                        onRollbackBranchChange={handleRollbackBranchChange}
                        onCancelBranchEdit={() => {
                            setBranchEditor(null);
                            setBranchChangePreview(null);
                        }}
                        branchChangePreview={branchChangePreview}
                        previewValidationErrors={previewValidationErrors}
                        previewDiffEntries={previewDiffEntries}
                        hasPublishedBranchChange={Boolean(latestPublishedBranchChange)}
                        branchChangesLoading={branchChangesQuery.isLoading}
                        branchChangesItems={branchChangesQuery.data?.items ?? []}
                        formatBranchChangeStatus={(value) => formatStateLabel(value, BRANCH_CHANGE_STATUS_LABELS)}
                        branchesHasNextPage={Boolean(branchesQuery.hasNextPage)}
                        branchesFetchingNextPage={branchesQuery.isFetchingNextPage}
                        onFetchNextBranchesPage={() => branchesQuery.fetchNextPage()}
                    />
                ) : null}
            </div>

            <TenantsClientLifecycleModal
                draft={clientLifecycleDraft}
                pending={Boolean(clientLifecyclePendingId)}
                onClose={closeClientLifecycleDraft}
                onSubmit={handleClientLifecycleAction}
                onPatchDraft={(patch) => {
                    setClientLifecycleDraft((prev) => (prev ? { ...prev, ...patch } : prev));
                }}
            />

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
