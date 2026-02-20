"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import {
    adminApi,
    authApi,
    canAccessConsole,
    opsApi,
    telegramApi,
    type IncidentAction,
    type IncidentItem,
    type OpsJobRunRequest,
} from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import { useSession } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import AccessDenied from "@/components/AccessDenied";
import { ConsolePageSkeleton } from "@/components/PageStates";
import { getProviderErrorContract } from "@/lib/provider-error-contract";
import { QUERY_PROFILE_CONTEXT, QUERY_PROFILE_DASHBOARD, keepPreviousData } from "@/lib/query-profiles";

interface HealthData {
    status: string;
    version: string;
    database: string;
    redis: string;
    outbox_backlog: number;
}

interface MetricsData {
    date: string;
    total_cases: number;
    pending_cases: number;
    active_cases: number;
    resolved_cases: number;
    avg_resolution_hours: number | null;
}

// TG-03: Telegram Health
interface TelegramHealthData {
    status: string;  // ok, degraded, error
    webhook_alive: boolean;
    last_success_at: string | null;
    last_error_at: string | null;
    last_error_message: string | null;
    error_rate_24h: number;
    pending_messages: number;
}

type OutboxStatusFilter = "failed" | "pending" | "processing" | "all";
type ReminderStatusFilter = "failed" | "pending" | "sent" | "all";

interface OutboxCounts {
    pending: number;
    processing: number;
    failed: number;
}

interface OutboxItem {
    id: string;
    status: string;
    attempts: number;
    next_attempt_at: string | null;
    last_error: string | null;
    created_at: string;
    updated_at: string;
    conversation_id: string | null;
    branch_id: string | null;
    inbound_message_id: string;
    channel: string | null;
    message_type: string | null;
    message_preview: string | null;
    remote_jid: string | null;
    instance_id: string | null;
    forwarded_to_telegram: boolean | null;
}

interface OutboxListResponse {
    items: OutboxItem[];
    cursor: string | null;
    has_more: boolean;
    counts: OutboxCounts;
}

interface OutboxRetryResponse {
    success: boolean;
    retried: number;
    skipped: number;
}

interface ReminderCounts {
    pending: number;
    sent: number;
    failed: number;
    due_now: number;
    overdue_15m: number;
}

interface ReminderErrorBucket {
    reason: string;
    count: number;
}

interface ReminderItem {
    id: string;
    appointment_id: string;
    branch_id: string;
    channel: string;
    template: string;
    run_at: string;
    status: "pending" | "sent" | "failed" | string;
    attempt: number;
    max_attempts: number;
    next_attempt_at: string | null;
    last_error: string | null;
    dedupe_key: string;
    created_at: string;
    updated_at: string;
    outbox_id: string | null;
    outbox_status: string | null;
    outbox_attempts: number | null;
    outbox_last_error: string | null;
    outbox_updated_at: string | null;
}

interface ReminderListResponse {
    items: ReminderItem[];
    cursor: string | null;
    has_more: boolean;
    counts: ReminderCounts;
    error_buckets: ReminderErrorBucket[];
}

interface ReminderRetryResponse {
    success: boolean;
    retried: number;
    skipped: number;
    matched: number;
}

type OpsJobType = OpsJobRunRequest["job_type"];
type OpsJobMode = OpsJobRunRequest["mode"];

interface OpsJobDefinition {
    job_type: OpsJobType;
    label: string;
    description: string;
    supports_dry_run: boolean;
}

interface OpsJobCatalogResponse {
    items: OpsJobDefinition[];
}

interface OpsJobRecord {
    id: string;
    job_type: OpsJobType;
    mode: OpsJobMode;
    status: "success" | "failed";
    created_at: string;
    finished_at: string | null;
    error_message: string | null;
    request_payload: Record<string, unknown> | null;
    result_payload: Record<string, unknown> | null;
}

interface OpsJobListResponse {
    items: OpsJobRecord[];
    cursor: string | null;
    has_more: boolean;
}

interface OpsJobRunResponse {
    job: OpsJobRecord;
}

type IncidentPostCheckSnapshot = {
    outbox_backlog: number;
    outbox_failed_24h: number;
    integration_degraded_branches: number;
    pending_handovers: number;
    captured_at: string;
};

type IncidentResolutionDraft = {
    check_action_completed: boolean;
    check_postcheck_recorded: boolean;
    check_owner_ack: boolean;
    note: string;
};

function _incidentMetricNumber(item: IncidentItem, key: string): number {
    const raw = item.metrics?.[key];
    if (typeof raw === "number" && Number.isFinite(raw)) {
        return raw;
    }
    if (typeof raw === "string") {
        const parsed = Number(raw);
        if (Number.isFinite(parsed)) {
            return parsed;
        }
    }
    return 0;
}

function buildIncidentPostCheckSnapshot(item: IncidentItem): IncidentPostCheckSnapshot {
    return {
        outbox_backlog: _incidentMetricNumber(item, "outbox_backlog"),
        outbox_failed_24h: _incidentMetricNumber(item, "outbox_failed_24h"),
        integration_degraded_branches: _incidentMetricNumber(item, "integration_degraded_branches"),
        pending_handovers: _incidentMetricNumber(item, "pending_handovers"),
        captured_at: new Date().toISOString(),
    };
}

function formatSignedDelta(value: number): string {
    if (value > 0) {
        return `+${value}`;
    }
    return `${value}`;
}

function resolutionChecklistReady(draft: IncidentResolutionDraft): boolean {
    return Boolean(
        draft.check_action_completed
        && draft.check_postcheck_recorded
        && draft.check_owner_ack
        && draft.note.trim().length >= 12,
    );
}

async function fetchHealth(): Promise<HealthData> {
    const response = await api.get("/health");
    return response.data;
}

async function fetchMetrics(): Promise<MetricsData> {
    const response = await api.get("/metrics/daily");
    return response.data;
}

async function fetchTelegramHealth(): Promise<TelegramHealthData> {
    const response = await api.get("/telegram/health");
    return response.data;
}

async function fetchOutbox(status: OutboxStatusFilter): Promise<OutboxListResponse> {
    const response = await api.get("/ops/outbox", {
        params: {
            status,
            limit: 50,
        },
    });
    return response.data;
}

async function fetchReminders(status: ReminderStatusFilter, template?: string): Promise<ReminderListResponse> {
    const response = await api.get("/ops/reminders", {
        params: {
            status,
            template: template && template.trim() ? template.trim() : undefined,
            limit: 50,
        },
    });
    return response.data;
}

import { getSystemStatusLabel } from "@/utils/labels";

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, string> = {
        ok: "bg-green-100 text-green-800",
        connected: "bg-green-100 text-green-800",
        degraded: "bg-yellow-100 text-yellow-800",
        error: "bg-red-100 text-red-800",
        unhealthy: "bg-red-100 text-red-800",
    };
    return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${styles[status] || "bg-muted text-muted-foreground"}`}>
            {getSystemStatusLabel(status)}
        </span>
    );
}

function MetricCard({ label, value, subtext }: { label: string; value: string | number; subtext?: string }) {
    return (
        <div className="bg-muted rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-foreground">{value}</div>
            <div className="text-sm text-muted-foreground">{label}</div>
            {subtext && <div className="text-xs text-muted-foreground mt-1">{subtext}</div>}
        </div>
    );
}

function incidentChipClass(severity: "critical" | "warn" | "info"): string {
    if (severity === "critical") {
        return "bg-red-100 text-red-800";
    }
    if (severity === "warn") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-slate-100 text-slate-700";
}

function incidentSeverityLabel(severity: "critical" | "warn" | "info"): string {
    if (severity === "critical") {
        return "critical";
    }
    if (severity === "warn") {
        return "warn";
    }
    return "info";
}

function incidentStateChipClass(state: IncidentItem["incident_state"]): string {
    if (state === "resolved") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (state === "in_progress") {
        return "bg-blue-100 text-blue-800";
    }
    return "bg-slate-100 text-slate-700";
}

function incidentStateLabel(state: IncidentItem["incident_state"]): string {
    if (state === "resolved") {
        return "закрыт";
    }
    if (state === "in_progress") {
        return "в работе";
    }
    return "открыт";
}

function formatJsonPreview(payload: Record<string, unknown> | null, limit = 160): string {
    if (!payload) {
        return "—";
    }
    const raw = JSON.stringify(payload);
    if (!raw) {
        return "—";
    }
    if (raw.length <= limit) {
        return raw;
    }
    return `${raw.slice(0, limit - 3)}...`;
}

function incidentFastSteps(item: IncidentItem): string[] {
    if (item.reason_code === "integration_degraded") {
        return [
            "Проверьте branch из инцидента и запустите dry-run integration_reconcile.",
            "Если dry-run подтверждает проблему, выполните execute для целевого филиала.",
            "Перепроверьте failed_24h и последний error через 3-5 минут.",
        ];
    }
    if (item.reason_code === "outbox_backlog") {
        return [
            "Проверьте pending/processing/failed и тренд за последние минуты.",
            "Запустите dry-run outbox_process, затем execute при безопасном результате.",
            "Подтвердите, что backlog снижается, а новые failed не растут.",
        ];
    }
    if (item.reason_code === "provider_auth" || item.reason_code === "provider_unavailable" || item.reason_code === "provider_rate_limited" || item.reason_code === "provider_billing_blocked") {
        return [
            "Сверьте provider состояние и reason_label по филиалу.",
            "Перейдите в Workspace/Integrations и выполните dry-run remediation.",
            "После execute проверьте стабилизацию delivery без роста failed_24h.",
        ];
    }
    if (item.reason_code === "handover_backlog") {
        return [
            "Проверьте нагрузку по handoff и oldest unresolved.",
            "Приоритизируйте входящие handoff и снимите узкие места по SLA.",
            "Подтвердите снижение pending handoff в следующем цикле обновления.",
        ];
    }
    return [
        "Проверьте summary + reason_label и выберите безопасное dry-run действие.",
        "Если dry-run подтверждает проблему, выполните целевое execute с причиной.",
        "После выполнения перепроверьте метрики и закройте инцидент evidence-данными.",
    ];
}

function incidentFallbackWhereToLook(item: IncidentItem): string {
    if (item.reason_code === "integration_degraded") {
        return "Если после действий деградация осталась: откройте Workspace -> Панель WhatsApp/ChatFlow -> перепроверьте webhook/instance_id и provider lifecycle.";
    }
    if (item.reason_code === "outbox_backlog") {
        return "Если backlog не падает: проверьте Ops Jobs результат outbox_process и ошибки в outbox last_error.";
    }
    if (item.reason_code === "provider_billing_blocked") {
        return "Если проблема остается: проверьте Subscription + paid_until/renewal в Workspace и зафиксируйте действие в журнале.";
    }
    if (item.reason_code === "provider_auth" || item.reason_code === "provider_unavailable" || item.reason_code === "provider_rate_limited") {
        return "Если ошибка повторяется: проверьте Integrations registry и webhook-contract, затем выполните integration_reconcile.";
    }
    return "Если причина не снимается: поднимите инцидент в журнале и приложите trace/job evidence.";
}

export default function OpsPage() {
    const { data: session } = useSession();
    const searchParams = useSearchParams();
    const { handleError } = useErrorHandler();
    const [telegramAction, setTelegramAction] = useState<"verify" | "test" | null>(null);
    const [outboxStatus, setOutboxStatus] = useState<OutboxStatusFilter>("failed");
    const [reminderStatus, setReminderStatus] = useState<ReminderStatusFilter>("failed");
    const [reminderTemplate, setReminderTemplate] = useState<string>("");
    const [jobType, setJobType] = useState<OpsJobType>("outbox_process");
    const [outboxProcessLimit, setOutboxProcessLimit] = useState<number>(10);
    const [integrationReconcileLimit, setIntegrationReconcileLimit] = useState<number>(25);
    const [integrationReconcileBranchIds, setIntegrationReconcileBranchIds] = useState<string>("");
    const [metricsSnapshotDays, setMetricsSnapshotDays] = useState<number>(1);
    const [metricsSnapshotDate, setMetricsSnapshotDate] = useState<string>("");
    const [incidentActionRunningId, setIncidentActionRunningId] = useState<string | null>(null);
    const [incidentBaselines, setIncidentBaselines] = useState<Record<string, IncidentPostCheckSnapshot>>({});
    const [incidentResolutionDrafts, setIncidentResolutionDrafts] = useState<Record<string, IncidentResolutionDraft>>({});
    const focusedIncidentId = (searchParams?.get("incident_id") ?? "").trim();
    const focusedReasonCode = (searchParams?.get("reason") ?? "").trim();

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
        ...QUERY_PROFILE_CONTEXT,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadOps = canAccessConsole(role, "ops", "read");
    const canWriteOps = canAccessConsole(role, "ops", "write");
    const canWriteSettings = canAccessConsole(role, "settings", "write");
    const isFullOps = role === "platform_admin";

    const { data: health, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
        queryKey: ["health"],
        queryFn: fetchHealth,
        enabled: !!session && canReadOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const { data: metrics, isLoading: metricsLoading, error: metricsError } = useQuery({
        queryKey: ["metrics-daily"],
        queryFn: fetchMetrics,
        enabled: !!session && canReadOps && isFullOps,
        refetchInterval: 60000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    // TG-03: Telegram Health
    const { data: telegramHealth, isLoading: telegramLoading } = useQuery({
        queryKey: ["telegram-health"],
        queryFn: fetchTelegramHealth,
        enabled: !!session && canReadOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const { data: outboxData, isLoading: outboxLoading, error: outboxError, refetch: refetchOutbox } = useQuery({
        queryKey: ["ops-outbox", outboxStatus],
        queryFn: () => fetchOutbox(outboxStatus),
        enabled: !!session && canReadOps && isFullOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const {
        data: remindersData,
        isLoading: remindersLoading,
        error: remindersError,
        refetch: refetchReminders,
    } = useQuery({
        queryKey: ["ops-reminders", reminderStatus, reminderTemplate],
        queryFn: () => fetchReminders(reminderStatus, reminderTemplate),
        enabled: !!session && canReadOps && isFullOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const { data: opsJobsCatalog } = useQuery({
        queryKey: ["ops-jobs-catalog"],
        queryFn: async () => {
            const response = await opsApi.getJobsCatalog();
            return response.data as OpsJobCatalogResponse;
        },
        enabled: !!session && canReadOps && isFullOps,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const { data: opsJobs, isLoading: opsJobsLoading, error: opsJobsError, refetch: refetchOpsJobs } = useQuery({
        queryKey: ["ops-jobs"],
        queryFn: async () => {
            const response = await opsApi.listJobs({ limit: 20 });
            return response.data as OpsJobListResponse;
        },
        enabled: !!session && canReadOps && isFullOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const {
        data: incidentsData,
        isLoading: incidentsLoading,
        error: incidentsError,
        refetch: refetchIncidents,
    } = useQuery({
        queryKey: ["admin-incidents"],
        queryFn: async () => {
            const response = await adminApi.listIncidents({ limit: 20 });
            return response.data;
        },
        enabled: !!session && canReadOps && isFullOps,
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    useEffect(() => {
        if (outboxError) {
            handleError(outboxError);
        }
    }, [outboxError, handleError]);

    useEffect(() => {
        if (remindersError) {
            handleError(remindersError);
        }
    }, [remindersError, handleError]);

    useEffect(() => {
        if (opsJobsError) {
            handleError(opsJobsError);
        }
    }, [opsJobsError, handleError]);

    useEffect(() => {
        if (incidentsError) {
            handleError(incidentsError);
        }
    }, [incidentsError, handleError]);

    const incidentItems = useMemo(() => {
        const items = incidentsData?.items ?? [];
        if (items.length === 0) {
            return [];
        }
        const match = (item: IncidentItem) => (
            (focusedIncidentId && item.id === focusedIncidentId)
            || (focusedReasonCode && item.reason_code === focusedReasonCode)
        );
        return [...items].sort((left, right) => {
            const leftFocused = match(left) ? 1 : 0;
            const rightFocused = match(right) ? 1 : 0;
            if (leftFocused !== rightFocused) {
                return rightFocused - leftFocused;
            }
            return new Date(right.detected_at).getTime() - new Date(left.detected_at).getTime();
        });
    }, [focusedIncidentId, focusedReasonCode, incidentsData?.items]);

    useEffect(() => {
        if (!incidentItems.length) {
            return;
        }
        setIncidentBaselines((prev) => {
            let changed = false;
            const next = { ...prev };
            for (const item of incidentItems) {
                if (!next[item.id]) {
                    next[item.id] = buildIncidentPostCheckSnapshot(item);
                    changed = true;
                }
            }
            return changed ? next : prev;
        });
        setIncidentResolutionDrafts((prev) => {
            let changed = false;
            const next = { ...prev };
            for (const item of incidentItems) {
                if (!next[item.id]) {
                    next[item.id] = {
                        check_action_completed: false,
                        check_postcheck_recorded: false,
                        check_owner_ack: false,
                        note: "",
                    };
                    changed = true;
                }
            }
            return changed ? next : prev;
        });
    }, [incidentItems]);

    const telegramVerify = useMutation({
        mutationFn: async () => {
            const { data } = await telegramApi.verify({ scope: "client" });
            return data;
        },
        onMutate: () => {
            setTelegramAction("verify");
        },
        onSuccess: (data) => {
            if (data.success) {
                toast.success(`Код верификации: ${data.verification_code}`);
            } else {
                toast.error(data.error_message || "Не удалось отправить код");
            }
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setTelegramAction(null);
        },
    });

    const telegramTest = useMutation({
        mutationFn: async () => {
            const { data } = await telegramApi.test({ scope: "client" });
            return data;
        },
        onMutate: () => {
            setTelegramAction("test");
        },
        onSuccess: (data) => {
            if (data.success) {
                toast.success("Тестовое сообщение отправлено");
            } else {
                toast.error(data.error_message || "Не удалось отправить тест");
            }
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setTelegramAction(null);
        },
    });

    const outboxRetry = useMutation({
        mutationFn: async (ids?: string[]) => {
            const { data } = await api.post<OutboxRetryResponse>("/ops/outbox/retry", {
                ids: ids && ids.length > 0 ? ids : undefined,
                limit: 100,
            });
            return data;
        },
        onSuccess: (data) => {
            if (data.success) {
                toast.success(`Ретрай: ${data.retried} сообщений`);
            } else {
                toast.error("Не удалось ретраить сообщения");
            }
            refetchOutbox();
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const reminderRetry = useMutation({
        mutationFn: async (payload: { ids?: string[]; confirm: boolean }) => {
            const { data } = await api.post<ReminderRetryResponse>("/ops/reminders/retry", {
                ids: payload.ids && payload.ids.length > 0 ? payload.ids : undefined,
                limit: 100,
                status: reminderStatus === "sent" ? "failed" : reminderStatus,
                confirm: payload.confirm,
            });
            return data;
        },
        onSuccess: (data) => {
            if (data.success) {
                toast.success(`Retry reminders: ${data.retried}`);
            } else {
                toast.error("Не удалось выполнить retry reminders");
            }
            refetchReminders();
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const runOpsJob = useMutation({
        mutationFn: async (payload: OpsJobRunRequest) => {
            const response = await opsApi.runJob(payload);
            return response.data as OpsJobRunResponse;
        },
        onSuccess: (data) => {
            if (data.job.status === "success") {
                toast.success(`Job ${data.job.job_type} выполнен`);
            } else {
                toast.error(data.job.error_message || `Job ${data.job.job_type} завершился с ошибкой`);
            }
            refetchOpsJobs();
        },
        onError: (error) => {
            handleError(error);
        },
    });

    const outboxCounts = useMemo(() => {
        const pending = outboxData?.counts?.pending ?? 0;
        const processing = outboxData?.counts?.processing ?? 0;
        const failed = outboxData?.counts?.failed ?? 0;
        return {
            pending,
            processing,
            failed,
            total: pending + processing + failed,
        };
    }, [outboxData]);

    const reminderCounts = useMemo(() => {
        return {
            pending: remindersData?.counts?.pending ?? 0,
            sent: remindersData?.counts?.sent ?? 0,
            failed: remindersData?.counts?.failed ?? 0,
            dueNow: remindersData?.counts?.due_now ?? 0,
            overdue: remindersData?.counts?.overdue_15m ?? 0,
        };
    }, [remindersData]);

    const opsCatalogItems = useMemo(
        () => (opsJobsCatalog?.items ?? []).filter((item) => item.job_type !== "incident_state"),
        [opsJobsCatalog],
    );

    const selectedJob = useMemo(
        () => opsCatalogItems.find((item) => item.job_type === jobType) ?? null,
        [opsCatalogItems, jobType],
    );

    useEffect(() => {
        if (!opsCatalogItems.length) {
            return;
        }
        if (opsCatalogItems.some((item) => item.job_type === jobType)) {
            return;
        }
        setJobType(opsCatalogItems[0].job_type);
    }, [jobType, opsCatalogItems]);

    const buildRunJobPayload = (mode: OpsJobMode): OpsJobRunRequest => {
        const params: Record<string, unknown> = {};
        if (jobType === "outbox_process") {
            params.limit = Math.max(1, outboxProcessLimit);
        }
        if (jobType === "integration_reconcile") {
            params.limit = Math.max(1, integrationReconcileLimit);
            const branchIds = integrationReconcileBranchIds
                .split(/[\s,]+/)
                .map((item) => item.trim())
                .filter((item) => item.length > 0);
            if (branchIds.length > 0) {
                params.branch_ids = branchIds;
            }
        }
        if (jobType === "metrics_snapshot") {
            params.days = Math.max(1, metricsSnapshotDays);
            if (metricsSnapshotDate) {
                params.metric_date = metricsSnapshotDate;
            }
        }
        return {
            job_type: jobType,
            mode,
            params,
        };
    };

    const runIncidentAction = async (incident: IncidentItem, action: IncidentAction) => {
        if (!action.job_type || !action.mode) {
            return;
        }
        if (action.mode === "execute") {
            const confirmed = window.confirm(`Выполнить ${action.job_type} в execute для incident ${incident.id}?`);
            if (!confirmed) {
                return;
            }
        }
        setIncidentActionRunningId(action.id);
        try {
            const payload: OpsJobRunRequest = {
                job_type: action.job_type,
                mode: action.mode,
                params: (action.params ?? undefined) as Record<string, unknown> | undefined,
            };
            const response = await opsApi.runJob(payload);
            const job = response.data.job;
            if (job.status === "success") {
                toast.success(`${action.title}: job ${job.id} выполнен`);
            } else {
                toast.error(job.error_message || `${action.title}: job завершился с ошибкой`);
            }
            void refetchOpsJobs();
            void refetchOutbox();
            void refetchIncidents();
        } catch (error) {
            handleError(error);
        } finally {
            setIncidentActionRunningId(null);
        }
    };

    const runIncidentStateTransition = async (
        incident: IncidentItem,
        targetState: IncidentItem["incident_state"],
    ) => {
        const baseline = incidentBaselines[incident.id] ?? buildIncidentPostCheckSnapshot(incident);
        const current = buildIncidentPostCheckSnapshot(incident);
        const draft = incidentResolutionDrafts[incident.id] ?? {
            check_action_completed: false,
            check_postcheck_recorded: false,
            check_owner_ack: false,
            note: "",
        };
        const checklistDone = resolutionChecklistReady(draft);
        const evidenceSummary = [
            `baseline(backlog=${baseline.outbox_backlog},failed_24h=${baseline.outbox_failed_24h},degraded=${baseline.integration_degraded_branches},handover=${baseline.pending_handovers})`,
            `current(backlog=${current.outbox_backlog},failed_24h=${current.outbox_failed_24h},degraded=${current.integration_degraded_branches},handover=${current.pending_handovers})`,
            `delta(backlog=${formatSignedDelta(current.outbox_backlog - baseline.outbox_backlog)},failed_24h=${formatSignedDelta(current.outbox_failed_24h - baseline.outbox_failed_24h)},degraded=${formatSignedDelta(current.integration_degraded_branches - baseline.integration_degraded_branches)},handover=${formatSignedDelta(current.pending_handovers - baseline.pending_handovers)})`,
            `checks(action=${draft.check_action_completed ? "yes" : "no"},postcheck=${draft.check_postcheck_recorded ? "yes" : "no"},owner=${draft.check_owner_ack ? "yes" : "no"})`,
            `note=${draft.note.trim() || "-"}`,
        ].join(" | ");

        if (targetState === "resolved" && !checklistDone) {
            toast.error("Для закрытия инцидента заполните evidence checklist и note (мин. 12 символов).");
            return;
        }

        const actionId = `state:${incident.id}:${targetState}`;
        setIncidentActionRunningId(actionId);
        try {
            const payload: OpsJobRunRequest = {
                job_type: "incident_state",
                mode: "execute",
                params: {
                    incident_id: incident.id,
                    incident_state: targetState,
                    reason_code: incident.reason_code,
                    branch_id: incident.branch_id ?? undefined,
                    owner: meData?.agent?.name || undefined,
                    note: targetState === "resolved" ? draft.note.trim() : undefined,
                    evidence_confirmed: targetState === "resolved" ? checklistDone : undefined,
                    evidence_summary: targetState === "resolved" ? evidenceSummary : undefined,
                },
            };
            const response = await opsApi.runJob(payload);
            const job = response.data.job;
            if (job.status === "success") {
                toast.success(`Инцидент переведен в "${incidentStateLabel(targetState)}"`);
                if (targetState === "resolved") {
                    setIncidentResolutionDrafts((prev) => ({
                        ...prev,
                        [incident.id]: {
                            check_action_completed: false,
                            check_postcheck_recorded: false,
                            check_owner_ack: false,
                            note: "",
                        },
                    }));
                }
            } else {
                toast.error(job.error_message || "Не удалось обновить состояние инцидента");
            }
            void refetchIncidents();
            void refetchOpsJobs();
        } catch (error) {
            handleError(error);
        } finally {
            setIncidentActionRunningId(null);
        }
    };

    const isLoading = healthLoading || (isFullOps && metricsLoading) || (!isFullOps && telegramLoading);

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Войдите в систему для просмотра статуса.
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

    if (!canReadOps) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к Ops." />
        );
    }

    if (isLoading) {
        return (
            <ConsolePageSkeleton
                pageTestId="ops-page"
                title="Статус системы"
                titleTestId="ops-title"
                columns={1}
                cardCount={2}
                cardHeightClass="h-32"
                maxWidthClass="max-w-4xl"
            />
        );
    }

    return (
        <div className="max-w-4xl mx-auto p-6" data-testid="ops-page">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold" data-testid="ops-title">Статус системы</h1>
                <div className="flex items-center gap-4">
                    <span className="text-sm text-muted-foreground">Авто-обновление: 30с</span>
                    <button
                        onClick={() => {
                            void refetchHealth();
                            if (isFullOps) {
                                void refetchIncidents();
                                void refetchOutbox();
                                void refetchReminders();
                                void refetchOpsJobs();
                            }
                        }}
                        className="text-sm text-primary hover:text-primary/80"
                    >
                        Обновить
                    </button>
                </div>
            </div>

            {isFullOps && (
                <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-incidents-card">
                    <div className="mb-4 flex items-center justify-between">
                        <div>
                            <h2 className="text-lg font-semibold">Критичные инциденты</h2>
                            <p className="text-xs text-muted-foreground">
                                Только факт-основанные причины и безопасные шаги (`dry-run` сначала).
                            </p>
                        </div>
                        <span className="text-xs text-muted-foreground">
                            {incidentsData?.summary.total ?? 0} шт.
                        </span>
                    </div>
                    <div className="mb-4 grid grid-cols-3 gap-3">
                        <MetricCard label="Critical" value={incidentsData?.summary.critical ?? 0} />
                        <MetricCard label="Warn" value={incidentsData?.summary.warn ?? 0} />
                        <MetricCard label="Info" value={incidentsData?.summary.info ?? 0} />
                    </div>
                    {incidentsLoading ? (
                        <p className="text-sm text-muted-foreground">Загрузка инцидентов...</p>
                    ) : !incidentItems.length ? (
                        <p className="text-sm text-muted-foreground">Критичных инцидентов не обнаружено.</p>
                    ) : (
                        <div className="space-y-3">
                            {incidentItems.map((item) => {
                                const providerContract = getProviderErrorContract(item.reason_code);
                                const fastSteps = incidentFastSteps(item);
                                const fallbackGuide = incidentFallbackWhereToLook(item);
                                const isFocused = Boolean(
                                    (focusedIncidentId && item.id === focusedIncidentId)
                                    || (focusedReasonCode && item.reason_code === focusedReasonCode),
                                );
                                const baseline = incidentBaselines[item.id] ?? buildIncidentPostCheckSnapshot(item);
                                const current = buildIncidentPostCheckSnapshot(item);
                                const deltaBacklog = current.outbox_backlog - baseline.outbox_backlog;
                                const deltaFailed24h = current.outbox_failed_24h - baseline.outbox_failed_24h;
                                const deltaDegraded = current.integration_degraded_branches - baseline.integration_degraded_branches;
                                const deltaPendingHandovers = current.pending_handovers - baseline.pending_handovers;
                                const draft = incidentResolutionDrafts[item.id] ?? {
                                    check_action_completed: false,
                                    check_postcheck_recorded: false,
                                    check_owner_ack: false,
                                    note: "",
                                };
                                const checklistDone = resolutionChecklistReady(draft);
                                return (
                                    <article
                                        key={item.id}
                                        className={`rounded-lg border p-3 ${isFocused ? "border-amber-400/90 bg-amber-50/40" : "border-border/60 bg-muted/20"}`}
                                        data-testid={`ops-incident-${item.id}`}
                                    >
                                        {providerContract && (
                                            <div className="mb-2 rounded-md border border-border/60 bg-background px-2 py-1 text-[11px] text-muted-foreground">
                                                <p className="font-semibold text-foreground">{providerContract.shortLabel}</p>
                                                <p className="mt-0.5">{providerContract.operatorMeaning}</p>
                                            </div>
                                        )}
                                        <div className="flex flex-wrap items-center justify-between gap-2">
                                            <p className="text-sm font-semibold">{item.title}</p>
                                            <div className="flex items-center gap-1">
                                                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${incidentChipClass(item.severity)}`}>
                                                    {incidentSeverityLabel(item.severity)}
                                                </span>
                                                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${incidentStateChipClass(item.incident_state)}`}>
                                                    {incidentStateLabel(item.incident_state)}
                                                </span>
                                            </div>
                                        </div>
                                        <p className="mt-1 text-xs text-muted-foreground">{item.reason_label}</p>
                                        <p className="mt-1 text-xs text-muted-foreground">{item.summary}</p>
                                        <p className="mt-1 text-[11px] text-muted-foreground">
                                            client: {item.client_slug || "n/a"} · detected: {new Date(item.detected_at).toLocaleString("ru-RU")}
                                        </p>
                                        {(item.incident_state_updated_at || item.incident_state_owner || item.incident_state_due_at || item.incident_state_note) && (
                                            <p className="mt-1 text-[11px] text-muted-foreground">
                                                updated: {item.incident_state_updated_at ? new Date(item.incident_state_updated_at).toLocaleString("ru-RU") : "—"}
                                                {item.incident_state_owner ? ` · owner: ${item.incident_state_owner}` : ""}
                                                {item.incident_state_due_at ? ` · due: ${new Date(item.incident_state_due_at).toLocaleString("ru-RU")}` : ""}
                                                {item.incident_state_note ? ` · note: ${item.incident_state_note}` : ""}
                                            </p>
                                        )}
                                        <div className="mt-2 rounded-md border border-border/60 bg-background px-3 py-2 text-[11px]" data-testid={`ops-incident-postcheck-${item.id}`}>
                                            <p className="font-semibold text-foreground">Post-check evidence</p>
                                            <div className="mt-1 text-muted-foreground">
                                                baseline: backlog={baseline.outbox_backlog}, failed_24h={baseline.outbox_failed_24h}, degraded={baseline.integration_degraded_branches}, handover={baseline.pending_handovers}
                                            </div>
                                            <div className="text-muted-foreground">
                                                current: backlog={current.outbox_backlog}, failed_24h={current.outbox_failed_24h}, degraded={current.integration_degraded_branches}, handover={current.pending_handovers}
                                            </div>
                                            <div className="text-muted-foreground">
                                                delta: backlog={formatSignedDelta(deltaBacklog)}, failed_24h={formatSignedDelta(deltaFailed24h)}, degraded={formatSignedDelta(deltaDegraded)}, handover={formatSignedDelta(deltaPendingHandovers)}
                                            </div>
                                            <div className="mt-1 text-muted-foreground">
                                                baseline captured: {new Date(baseline.captured_at).toLocaleString("ru-RU")}
                                            </div>
                                            <div className="mt-2 flex flex-wrap gap-2">
                                                <button
                                                    type="button"
                                                    className="btn-ghost text-xs"
                                                    onClick={() => {
                                                        setIncidentBaselines((prev) => ({
                                                            ...prev,
                                                            [item.id]: buildIncidentPostCheckSnapshot(item),
                                                        }));
                                                        toast.success("Baseline обновлен");
                                                    }}
                                                >
                                                    Обновить baseline
                                                </button>
                                            </div>
                                            <div className="mt-2 grid gap-1 text-muted-foreground">
                                                <label className="inline-flex items-center gap-2">
                                                    <input
                                                        type="checkbox"
                                                        className="h-4 w-4"
                                                        checked={draft.check_action_completed}
                                                        onChange={(event) => {
                                                            const checked = event.target.checked;
                                                            setIncidentResolutionDrafts((prev) => ({
                                                                ...prev,
                                                                [item.id]: { ...draft, check_action_completed: checked },
                                                            }));
                                                        }}
                                                    />
                                                    remediation action выполнено
                                                </label>
                                                <label className="inline-flex items-center gap-2">
                                                    <input
                                                        type="checkbox"
                                                        className="h-4 w-4"
                                                        checked={draft.check_postcheck_recorded}
                                                        onChange={(event) => {
                                                            const checked = event.target.checked;
                                                            setIncidentResolutionDrafts((prev) => ({
                                                                ...prev,
                                                                [item.id]: { ...draft, check_postcheck_recorded: checked },
                                                            }));
                                                        }}
                                                    />
                                                    post-check зафиксирован (delta проверен)
                                                </label>
                                                <label className="inline-flex items-center gap-2">
                                                    <input
                                                        type="checkbox"
                                                        className="h-4 w-4"
                                                        checked={draft.check_owner_ack}
                                                        onChange={(event) => {
                                                            const checked = event.target.checked;
                                                            setIncidentResolutionDrafts((prev) => ({
                                                                ...prev,
                                                                [item.id]: { ...draft, check_owner_ack: checked },
                                                            }));
                                                        }}
                                                    />
                                                    подтверждено ответственным оператором
                                                </label>
                                            </div>
                                            <textarea
                                                className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 text-xs"
                                                rows={2}
                                                placeholder="Коротко: что сделали и что изменилось по метрикам (минимум 12 символов)"
                                                value={draft.note}
                                                onChange={(event) => {
                                                    const value = event.target.value;
                                                    setIncidentResolutionDrafts((prev) => ({
                                                        ...prev,
                                                        [item.id]: { ...draft, note: value },
                                                    }));
                                                }}
                                            />
                                            <div className="mt-1 text-muted-foreground">
                                                checklist: {checklistDone ? "готов к закрытию" : "неполный"}
                                            </div>
                                        </div>
                                        <div className="mt-2 flex flex-wrap gap-2">
                                            {item.incident_state !== "in_progress" && (
                                                <button
                                                    type="button"
                                                    className="btn-ghost text-xs"
                                                    disabled={!canWriteOps || incidentActionRunningId === `state:${item.id}:in_progress`}
                                                    onClick={() => {
                                                        void runIncidentStateTransition(item, "in_progress");
                                                    }}
                                                    data-testid={`ops-incident-state-${item.id}-in-progress`}
                                                >
                                                    {incidentActionRunningId === `state:${item.id}:in_progress` ? "Выполняю..." : "В работу"}
                                                </button>
                                            )}
                                            {item.incident_state !== "resolved" && (
                                                <button
                                                    type="button"
                                                    className="btn-ghost text-xs"
                                                    disabled={!canWriteOps || incidentActionRunningId === `state:${item.id}:resolved` || !checklistDone}
                                                    onClick={() => {
                                                        void runIncidentStateTransition(item, "resolved");
                                                    }}
                                                    data-testid={`ops-incident-state-${item.id}-resolved`}
                                                    title={checklistDone ? undefined : "Заполните post-check checklist и note"}
                                                >
                                                    {incidentActionRunningId === `state:${item.id}:resolved` ? "Выполняю..." : "Закрыть"}
                                                </button>
                                            )}
                                            {item.incident_state === "resolved" && (
                                                <button
                                                    type="button"
                                                    className="btn-ghost text-xs"
                                                    disabled={!canWriteOps || incidentActionRunningId === `state:${item.id}:open`}
                                                    onClick={() => {
                                                        void runIncidentStateTransition(item, "open");
                                                    }}
                                                    data-testid={`ops-incident-state-${item.id}-open`}
                                                >
                                                    {incidentActionRunningId === `state:${item.id}:open` ? "Выполняю..." : "Открыть снова"}
                                                </button>
                                            )}
                                        </div>
                                        <div className="mt-2 rounded-md border border-border/60 bg-background px-3 py-2 text-[11px]">
                                            <p className="font-semibold text-foreground">Что сделать сейчас (5 минут)</p>
                                            <ol className="mt-1 list-decimal space-y-1 pl-4 text-muted-foreground" data-testid={`ops-incident-fast-steps-${item.id}`}>
                                                {fastSteps.map((step) => (
                                                    <li key={step}>{step}</li>
                                                ))}
                                            </ol>
                                            <p className="mt-2 text-muted-foreground">{fallbackGuide}</p>
                                        </div>
                                        {providerContract && (
                                            <ol className="mt-2 list-decimal space-y-0.5 pl-4 text-[11px] text-muted-foreground" data-testid={`ops-provider-runbook-${item.id}`}>
                                                {providerContract.runbook.map((step) => (
                                                    <li key={step}>{step}</li>
                                                ))}
                                            </ol>
                                        )}
                                        <div className="mt-2 flex flex-wrap gap-2">
                                            {item.actions.map((action) => (
                                                action.href ? (
                                                    <Link
                                                        key={action.id}
                                                        href={`${action.href}${action.href.includes("?") ? "&" : "?"}incident_id=${encodeURIComponent(item.id)}&reason=${encodeURIComponent(item.reason_code)}&severity=${encodeURIComponent(item.severity)}`}
                                                        className="btn-ghost text-xs"
                                                    >
                                                        {action.title}
                                                    </Link>
                                                ) : (
                                                    action.job_type && action.mode ? (
                                                        <button
                                                            key={action.id}
                                                            type="button"
                                                            className="btn-ghost text-xs"
                                                            disabled={!canWriteOps || incidentActionRunningId === action.id}
                                                            onClick={() => {
                                                                void runIncidentAction(item, action);
                                                            }}
                                                            data-testid={`ops-incident-action-${item.id}-${action.id}`}
                                                        >
                                                            {incidentActionRunningId === action.id
                                                                ? "Выполняю..."
                                                                : `${action.title} (${action.job_type}:${action.mode})`}
                                                        </button>
                                                    ) : (
                                                        <span key={action.id} className="rounded-full border border-border/60 px-2 py-1 text-[11px] text-muted-foreground">
                                                            {action.title}
                                                        </span>
                                                    )
                                                )
                                            ))}
                                        </div>
                                    </article>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}

            {!isFullOps && (
                <div className="mb-6 rounded-lg border border-border/60 bg-muted/40 p-4 text-sm text-muted-foreground" data-testid="ops-short-note">
                    Краткий статус. Полный Ops доступен только platform admin.
                    {health?.status && health.status !== "ok" ? " Есть деградации — обратитесь к platform admin." : ""}
                </div>
            )}

            {/* Overall Health */}
            <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-health-card">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold">Общее состояние</h2>
                    <StatusBadge status={health?.status || "unknown"} />
                </div>
                <p className="text-sm text-muted-foreground">
                    Версия: <span className="font-mono">{health?.version || "неизвестно"}</span>
                </p>
            </div>

            {isFullOps && (
                <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-metrics-card">
                    <h2 className="text-lg font-semibold mb-4">
                        Метрики за сегодня
                        <span className="text-sm font-normal text-muted-foreground ml-2">
                            ({metrics?.date || "сегодня"})
                        </span>
                    </h2>
                    {metricsError ? (
                        <div className="text-sm text-muted-foreground text-center py-4">
                            Не удалось загрузить метрики
                        </div>
                    ) : (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <MetricCard label="Всего заявок" value={metrics?.total_cases ?? 0} />
                            <MetricCard label="Ожидает" value={metrics?.pending_cases ?? 0} />
                            <MetricCard label="В работе" value={metrics?.active_cases ?? 0} />
                            <MetricCard
                                label="Закрыто"
                                value={metrics?.resolved_cases ?? 0}
                                subtext={metrics?.avg_resolution_hours ? `Средн: ${metrics.avg_resolution_hours}ч` : undefined}
                            />
                        </div>
                    )}
                </div>
            )}

            {/* Components */}
            <div className="bg-card border border-border/60 rounded-lg p-6 mb-6">
                <h2 className="text-lg font-semibold mb-4">Компоненты</h2>
                <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center justify-between p-3 bg-muted rounded">
                        <span className="text-sm font-medium">База данных</span>
                        <StatusBadge status={health?.database || "unknown"} />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-muted rounded">
                        <span className="text-sm font-medium">Redis</span>
                        <StatusBadge status={health?.redis || "unknown"} />
                    </div>
                </div>
            </div>

            {/* TG-03: Telegram Health */}
            <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-telegram-card">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                        📨 Telegram
                    </h2>
                    <StatusBadge status={telegramHealth?.status || "unknown"} />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-muted rounded-lg p-3 text-center">
                        <div className={`text-lg font-bold ${telegramHealth?.webhook_alive ? "text-green-600" : "text-red-600"}`}>
                            {telegramHealth?.webhook_alive ? "✓" : "✗"}
                        </div>
                        <div className="text-xs text-muted-foreground">Webhook</div>
                    </div>
                    <div className="bg-muted rounded-lg p-3 text-center">
                        <div className={`text-lg font-bold ${(telegramHealth?.error_rate_24h || 0) > 0.1 ? "text-red-600" : "text-green-600"}`}>
                            {((telegramHealth?.error_rate_24h || 0) * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-muted-foreground">Ошибки 24ч</div>
                    </div>
                    <div className="bg-muted rounded-lg p-3 text-center">
                        <div className={`text-lg font-bold ${(telegramHealth?.pending_messages || 0) > 5 ? "text-yellow-600" : "text-foreground"}`}>
                            {telegramHealth?.pending_messages ?? 0}
                        </div>
                        <div className="text-xs text-muted-foreground">В ожидании</div>
                    </div>
                    <div className="bg-muted rounded-lg p-3 text-center">
                        <div className="text-xs text-foreground">
                            {telegramHealth?.last_success_at
                                ? new Date(telegramHealth.last_success_at).toLocaleTimeString("ru-RU")
                                : "—"}
                        </div>
                        <div className="text-xs text-muted-foreground">Посл. успех</div>
                    </div>
                </div>
                {telegramHealth?.last_error_message && (
                    <div className="mt-3 p-2 bg-destructive/10 rounded text-xs text-destructive">
                        ⚠️ {telegramHealth.last_error_message}
                    </div>
                )}
                <div className="mt-4 flex items-center gap-2">
                    <button
                        type="button"
                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => telegramVerify.mutate()}
                        disabled={telegramAction !== null || !canWriteSettings}
                        data-testid="ops-telegram-verify"
                    >
                        {telegramAction === "verify" ? "Отправка..." : "Verify"}
                    </button>
                    <button
                        type="button"
                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                        onClick={() => telegramTest.mutate()}
                        disabled={telegramAction !== null || !canWriteSettings}
                        data-testid="ops-telegram-test"
                    >
                        {telegramAction === "test" ? "Отправка..." : "Send test"}
                    </button>
                    {!canWriteSettings && (
                        <span className="text-xs text-muted-foreground">Только owner/admin/platform admin</span>
                    )}
                </div>
            </div>

            {isFullOps && (
                <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-queue-card">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold">Очередь сообщений</h2>
                        <span
                            className={`text-2xl font-bold ${(health?.outbox_backlog || 0) > 100
                            ? "text-red-600"
                            : (health?.outbox_backlog || 0) > 10
                                ? "text-yellow-600"
                                : "text-green-600"
                            }`}
                            data-testid="ops-queue-count"
                        >
                            {health?.outbox_backlog ?? 0}
                        </span>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-4">
                        {([
                            { value: "failed", label: "Failed", count: outboxCounts.failed },
                            { value: "pending", label: "Pending", count: outboxCounts.pending },
                            { value: "processing", label: "Processing", count: outboxCounts.processing },
                            { value: "all", label: "All", count: outboxCounts.total },
                        ] as const).map((item) => (
                            <button
                                key={item.value}
                                type="button"
                                onClick={() => setOutboxStatus(item.value)}
                                className={`rounded-full border px-3 py-1 text-xs font-medium ${
                                    outboxStatus === item.value
                                        ? "border-primary text-primary"
                                        : "border-border/60 text-muted-foreground hover:text-foreground"
                                }`}
                            >
                                {item.label} · {item.count}
                            </button>
                        ))}
                        {outboxStatus === "failed" && (
                            <button
                                type="button"
                                className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                onClick={() => outboxRetry.mutate(undefined)}
                                disabled={outboxRetry.isPending || !canWriteOps}
                            >
                                {outboxRetry.isPending ? "Ретрай..." : "Retry failed"}
                            </button>
                        )}
                        {!canWriteOps && (
                            <span className="text-xs text-muted-foreground">Ретрай доступен только owner/admin/platform admin</span>
                        )}
                    </div>
                    {outboxLoading ? (
                        <div className="text-sm text-muted-foreground">Загрузка...</div>
                    ) : outboxError ? (
                        <div className="text-sm text-muted-foreground">Не удалось загрузить очередь</div>
                    ) : outboxData?.items?.length ? (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="text-xs text-muted-foreground">
                                    <tr className="text-left border-b border-border/60">
                                        <th className="py-2 pr-3">Статус</th>
                                        <th className="py-2 pr-3">Попытки</th>
                                        <th className="py-2 pr-3">Канал</th>
                                        <th className="py-2 pr-3">Сообщение</th>
                                        <th className="py-2 pr-3">Ошибка</th>
                                        <th className="py-2 pr-3">Обновлено</th>
                                        <th className="py-2 pr-3 text-right">Действия</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {outboxData.items.map((item) => (
                                        <tr key={item.id} className="border-b border-border/40">
                                            <td className="py-2 pr-3">
                                                <span
                                                    className={`px-2 py-1 rounded text-xs font-medium ${
                                                        item.status === "failed"
                                                            ? "bg-red-100 text-red-800"
                                                            : item.status === "pending"
                                                                ? "bg-yellow-100 text-yellow-800"
                                                                : "bg-blue-100 text-blue-800"
                                                    }`}
                                                >
                                                    {item.status}
                                                </span>
                                            </td>
                                            <td className="py-2 pr-3">{item.attempts}</td>
                                            <td className="py-2 pr-3">{item.channel || "—"}</td>
                                            <td className="py-2 pr-3">
                                                <div className="text-xs text-foreground">{item.message_preview || "—"}</div>
                                                {item.remote_jid && (
                                                    <div className="text-xs text-muted-foreground">{item.remote_jid}</div>
                                                )}
                                            </td>
                                            <td className="py-2 pr-3">
                                                <span className="text-xs text-destructive">{item.last_error || "—"}</span>
                                            </td>
                                            <td className="py-2 pr-3">
                                                {item.updated_at ? new Date(item.updated_at).toLocaleString("ru-RU") : "—"}
                                            </td>
                                            <td className="py-2 pr-3 text-right">
                                                {item.status === "failed" && (
                                                    <button
                                                        type="button"
                                                        className="text-xs text-primary hover:text-primary/80 disabled:opacity-50"
                                                        onClick={() => outboxRetry.mutate([item.id])}
                                                        disabled={outboxRetry.isPending || !canWriteOps}
                                                    >
                                                        Retry
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="text-sm text-muted-foreground">Очередь пуста</div>
                    )}
                </div>
            )}

            {isFullOps && (
                <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-reminders-card">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold">Reminder Queue</h2>
                        <button
                            type="button"
                            className="text-xs text-primary hover:text-primary/80"
                            onClick={() => refetchReminders()}
                        >
                            Обновить reminders
                        </button>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
                        <MetricCard label="Pending" value={reminderCounts.pending} />
                        <MetricCard label="Sent" value={reminderCounts.sent} />
                        <MetricCard label="Failed" value={reminderCounts.failed} />
                        <MetricCard label="Due now" value={reminderCounts.dueNow} />
                        <MetricCard label="Overdue 15m+" value={reminderCounts.overdue} />
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                        {([
                            { value: "failed", label: "Failed", count: reminderCounts.failed },
                            { value: "pending", label: "Pending", count: reminderCounts.pending },
                            { value: "sent", label: "Sent", count: reminderCounts.sent },
                            { value: "all", label: "All", count: reminderCounts.pending + reminderCounts.sent + reminderCounts.failed },
                        ] as const).map((item) => (
                            <button
                                key={item.value}
                                type="button"
                                onClick={() => setReminderStatus(item.value)}
                                className={`rounded-full border px-3 py-1 text-xs font-medium ${
                                    reminderStatus === item.value
                                        ? "border-primary text-primary"
                                        : "border-border/60 text-muted-foreground hover:text-foreground"
                                }`}
                            >
                                {item.label} · {item.count}
                            </button>
                        ))}
                        {reminderStatus !== "sent" && (
                            <button
                                type="button"
                                className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                disabled={reminderRetry.isPending || !canWriteOps}
                                onClick={() => {
                                    if (!window.confirm("Retry reminders for current filter?")) {
                                        return;
                                    }
                                    reminderRetry.mutate({ confirm: true });
                                }}
                            >
                                {reminderRetry.isPending ? "Retry..." : "Retry filtered"}
                            </button>
                        )}
                    </div>
                    <div className="mb-3 flex items-center gap-2">
                        <label className="text-xs text-muted-foreground">Template:</label>
                        <input
                            type="text"
                            className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                            placeholder="appointment_reminder"
                            value={reminderTemplate}
                            onChange={(event) => setReminderTemplate(event.target.value)}
                        />
                    </div>
                    {remindersData?.error_buckets?.length ? (
                        <div className="mb-3 flex flex-wrap gap-2">
                            {remindersData.error_buckets.map((bucket) => (
                                <span
                                    key={bucket.reason}
                                    className="rounded-full border border-border/60 px-2 py-1 text-[11px] text-muted-foreground"
                                >
                                    {bucket.reason}: {bucket.count}
                                </span>
                            ))}
                        </div>
                    ) : null}
                    {remindersLoading ? (
                        <div className="text-sm text-muted-foreground">Загрузка reminders...</div>
                    ) : remindersData?.items?.length ? (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="text-xs text-muted-foreground">
                                    <tr className="text-left border-b border-border/60">
                                        <th className="py-2 pr-3">Template</th>
                                        <th className="py-2 pr-3">Run at</th>
                                        <th className="py-2 pr-3">Status</th>
                                        <th className="py-2 pr-3">Attempts</th>
                                        <th className="py-2 pr-3">Error</th>
                                        <th className="py-2 pr-3">Outbox</th>
                                        <th className="py-2 pr-3 text-right">Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {remindersData.items.map((item) => (
                                        <tr key={item.id} className="border-b border-border/40">
                                            <td className="py-2 pr-3">
                                                <div className="text-xs text-foreground">{item.template}</div>
                                                <div className="text-[11px] text-muted-foreground">{item.channel}</div>
                                            </td>
                                            <td className="py-2 pr-3 text-xs">
                                                {item.run_at ? new Date(item.run_at).toLocaleString("ru-RU") : "—"}
                                            </td>
                                            <td className="py-2 pr-3">
                                                <span
                                                    className={`px-2 py-1 rounded text-xs font-medium ${
                                                        item.status === "failed"
                                                            ? "bg-red-100 text-red-800"
                                                            : item.status === "pending"
                                                                ? "bg-yellow-100 text-yellow-800"
                                                                : "bg-green-100 text-green-800"
                                                    }`}
                                                >
                                                    {item.status}
                                                </span>
                                            </td>
                                            <td className="py-2 pr-3 text-xs">
                                                {item.attempt}/{item.max_attempts}
                                            </td>
                                            <td className="py-2 pr-3 text-xs text-destructive">
                                                {item.last_error || "—"}
                                            </td>
                                            <td className="py-2 pr-3 text-xs">
                                                {item.outbox_status ? (
                                                    <span
                                                        className={`px-2 py-1 rounded text-[11px] font-medium ${
                                                            item.outbox_status === "failed"
                                                                ? "bg-red-100 text-red-800"
                                                                : item.outbox_status === "pending"
                                                                    ? "bg-yellow-100 text-yellow-800"
                                                                    : "bg-blue-100 text-blue-800"
                                                        }`}
                                                    >
                                                        {item.outbox_status}
                                                    </span>
                                                ) : (
                                                    <span className="text-muted-foreground">no outbox</span>
                                                )}
                                            </td>
                                            <td className="py-2 pr-3 text-right">
                                                {(item.status === "failed" || item.status === "pending") && (
                                                    <button
                                                        type="button"
                                                        className="text-xs text-primary hover:text-primary/80 disabled:opacity-50"
                                                        onClick={() => reminderRetry.mutate({ ids: [item.id], confirm: false })}
                                                        disabled={reminderRetry.isPending || !canWriteOps}
                                                    >
                                                        Retry
                                                    </button>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="text-sm text-muted-foreground">Reminder jobs не найдены</div>
                    )}
                </div>
            )}

            {isFullOps && (
                <div className="bg-card border border-border/60 rounded-lg p-6 mb-6" data-testid="ops-jobs-card">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold">Console Jobs</h2>
                        <button
                            type="button"
                            className="text-xs text-primary hover:text-primary/80"
                            onClick={() => refetchOpsJobs()}
                        >
                            Обновить историю
                        </button>
                    </div>

                    <div className="grid gap-3 md:grid-cols-2 mb-4">
                        <div>
                            <label className="block text-xs text-muted-foreground mb-1">Job type</label>
                            <select
                                className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                value={jobType}
                                onChange={(event) => setJobType(event.target.value as OpsJobType)}
                            >
                                {opsCatalogItems.map((item) => (
                                    <option key={item.job_type} value={item.job_type}>
                                        {item.label}
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-muted-foreground mt-1">
                                {selectedJob?.description || "Каталог jobs загружается..."}
                            </p>
                        </div>

                        <div>
                            {jobType === "outbox_process" && (
                                <>
                                    <label className="block text-xs text-muted-foreground mb-1">Limit</label>
                                    <input
                                        type="number"
                                        min={1}
                                        max={200}
                                        className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                        value={outboxProcessLimit}
                                        onChange={(event) => setOutboxProcessLimit(Number(event.target.value))}
                                    />
                                </>
                            )}
                            {jobType === "integration_reconcile" && (
                                <div className="grid gap-2">
                                    <div>
                                        <label className="block text-xs text-muted-foreground mb-1">Limit</label>
                                        <input
                                            type="number"
                                            min={1}
                                            max={200}
                                            className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                            value={integrationReconcileLimit}
                                            onChange={(event) => setIntegrationReconcileLimit(Number(event.target.value))}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs text-muted-foreground mb-1">
                                            Branch IDs (optional, comma or newline separated)
                                        </label>
                                        <textarea
                                            className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-xs font-mono"
                                            rows={3}
                                            value={integrationReconcileBranchIds}
                                            onChange={(event) => setIntegrationReconcileBranchIds(event.target.value)}
                                            placeholder="uuid-1, uuid-2"
                                        />
                                    </div>
                                </div>
                            )}
                            {jobType === "metrics_snapshot" && (
                                <div className="grid gap-2">
                                    <div>
                                        <label className="block text-xs text-muted-foreground mb-1">Days</label>
                                        <input
                                            type="number"
                                            min={1}
                                            max={60}
                                            className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                            value={metricsSnapshotDays}
                                            onChange={(event) => setMetricsSnapshotDays(Number(event.target.value))}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs text-muted-foreground mb-1">Metric date (optional)</label>
                                        <input
                                            type="date"
                                            className="w-full rounded-md border border-border/60 bg-background px-3 py-2 text-sm"
                                            value={metricsSnapshotDate}
                                            onChange={(event) => setMetricsSnapshotDate(event.target.value)}
                                        />
                                    </div>
                                </div>
                            )}
                            {jobType === "heal" && (
                                <p className="text-xs text-muted-foreground mt-6">
                                    Для `heal` в этом срезе доступен только dry-run.
                                </p>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center gap-2 mb-4">
                        <button
                            type="button"
                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() => runOpsJob.mutate(buildRunJobPayload("dry_run"))}
                            disabled={runOpsJob.isPending || !canWriteOps}
                        >
                            {runOpsJob.isPending ? "Запуск..." : "Dry-run"}
                        </button>
                        <button
                            type="button"
                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() => runOpsJob.mutate(buildRunJobPayload("execute"))}
                            disabled={runOpsJob.isPending || !canWriteOps || jobType === "heal"}
                        >
                            Execute
                        </button>
                    </div>

                    {opsJobsLoading ? (
                        <div className="text-sm text-muted-foreground">Загрузка истории jobs...</div>
                    ) : !opsJobs?.items?.length ? (
                        <div className="text-sm text-muted-foreground">История jobs пока пуста</div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead className="text-xs text-muted-foreground">
                                    <tr className="text-left border-b border-border/60">
                                        <th className="py-2 pr-3">Тип</th>
                                        <th className="py-2 pr-3">Режим</th>
                                        <th className="py-2 pr-3">Статус</th>
                                        <th className="py-2 pr-3">Запуск</th>
                                        <th className="py-2 pr-3">Результат</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {opsJobs.items.map((job) => (
                                        <tr key={job.id} className="border-b border-border/40">
                                            <td className="py-2 pr-3">{job.job_type}</td>
                                            <td className="py-2 pr-3">{job.mode}</td>
                                            <td className="py-2 pr-3">
                                                <span
                                                    className={`px-2 py-1 rounded text-xs font-medium ${
                                                        job.status === "success"
                                                            ? "bg-green-100 text-green-800"
                                                            : "bg-red-100 text-red-800"
                                                    }`}
                                                >
                                                    {job.status}
                                                </span>
                                            </td>
                                            <td className="py-2 pr-3">
                                                {job.created_at ? new Date(job.created_at).toLocaleString("ru-RU") : "—"}
                                            </td>
                                            <td className="py-2 pr-3">
                                                <span className="text-xs text-muted-foreground">
                                                    {job.error_message || formatJsonPreview(job.result_payload)}
                                                </span>
                                                {(() => {
                                                    const artifactRaw = job.result_payload && typeof job.result_payload === "object"
                                                        ? job.result_payload["artifact"]
                                                        : undefined;
                                                    if (!artifactRaw || typeof artifactRaw !== "object") {
                                                        return null;
                                                    }
                                                    const artifact = artifactRaw as Record<string, unknown>;
                                                    return (
                                                        <div className="mt-1 text-[11px] text-muted-foreground">
                                                            artifact: {String(artifact.artifact_id || "—")}
                                                        </div>
                                                    );
                                                })()}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* Navigation */}
            <div className="text-center">
                <Link href="/" className="text-primary hover:text-primary/80">
                    ← Назад к заявкам
                </Link>
            </div>
        </div>
    );
}
