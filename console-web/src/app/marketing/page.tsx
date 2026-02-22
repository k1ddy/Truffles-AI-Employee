"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";

import AccessDenied from "@/components/AccessDenied";
import {
    adminApi,
    authApi,
    canAccessConsole,
    parseApiError,
    type MarketingAudienceFunnel,
    type MarketingCampaign,
    type MarketingCampaignDiagnosticsResponse,
    type MarketingCampaignPreflightResponse,
    type MarketingCampaignRecipient,
    type MarketingSegmentCode,
    type MarketingSegmentDefinition,
    type MarketingSegmentEditableField,
} from "@/lib/api-client";
import { useConsoleContextScope } from "@/lib/use-console-context-scope";

type SegmentParams = Record<string, unknown>;
type MarketingDisplayStatus = MarketingCampaign["status"] | MarketingCampaign["status_v2"];

const FALLBACK_SEGMENTS: MarketingSegmentDefinition[] = [
    {
        code: "reactivation_30_120",
        label: "Возврат клиентов",
        short_label: "Возврат",
        description: "Клиенты с прошлым визитом без будущей записи.",
        defaults: {
            min_days_since_last_visit: 30,
            max_days_since_last_visit: 120,
            require_no_future_booking: true,
        },
        summary: "Клиенты без будущей записи, у которых последний визит был 30-120 дней назад.",
        editable_fields: [
            {
                key: "min_days_since_last_visit",
                label: "От, дней после визита",
                type: "int",
                min: 1,
                max: 3650,
                step: 1,
            },
            {
                key: "max_days_since_last_visit",
                label: "До, дней после визита",
                type: "int",
                min: 1,
                max: 3650,
                step: 1,
            },
            {
                key: "require_no_future_booking",
                label: "Только без будущей записи",
                type: "bool",
            },
        ],
    },
    {
        code: "no_show_recovery_14d",
        label: "После no-show",
        short_label: "No-show",
        description: "Клиенты с недавним no-show без будущей записи.",
        defaults: {
            no_show_window_days: 14,
            min_no_show_count: 1,
            require_no_future_booking: true,
        },
        summary: "Клиенты с no-show за последние 14 дней (минимум 1), без будущей записи.",
        editable_fields: [
            {
                key: "no_show_window_days",
                label: "Период поиска no-show, дней",
                type: "int",
                min: 1,
                max: 365,
                step: 1,
            },
            {
                key: "min_no_show_count",
                label: "Минимум no-show за период",
                type: "int",
                min: 1,
                max: 10,
                step: 1,
            },
            {
                key: "require_no_future_booking",
                label: "Только без будущей записи",
                type: "bool",
            },
        ],
    },
    {
        code: "engaged_no_booking_7d",
        label: "Интерес без записи",
        short_label: "Интерес",
        description: "Клиенты, задававшие вопросы по услугам/ценам и не записавшиеся.",
        defaults: {
            engagement_window_days: 7,
            require_no_future_booking: true,
        },
        summary: "Клиенты с интересом к услугам/ценам за последние 7 дней, без будущей записи.",
        editable_fields: [
            {
                key: "engagement_window_days",
                label: "Период интереса, дней",
                type: "int",
                min: 1,
                max: 90,
                step: 1,
            },
            {
                key: "require_no_future_booking",
                label: "Только без будущей записи",
                type: "bool",
            },
        ],
    },
];

const PREFLIGHT_REASON_HINTS: Record<string, string> = {
    runtime_health_critical: "Нестабильный runtime/outbox. Сначала устраните инциденты.",
    provider_billing_blocked: "Провайдер заблокирован по оплате. Отправка невозможна до оплаты.",
    campaign_not_approved: "Кампанию нужно подтвердить перед отправкой.",
    audience_snapshot_missing: "Сначала выполните Preview аудитории.",
    eligible_recipients_empty: "Нет получателей. Измените сегмент или параметры.",
    template_not_approved: "Template gate включен: нужен approved template.",
};

function formatDateTime(value?: string | null): string {
    if (!value) {
        return "-";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("ru-RU");
}

function parseBoundedInt(value: string, fallback: number, min: number, max: number): number {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
        return fallback;
    }
    return Math.min(max, Math.max(min, Math.trunc(parsed)));
}

function formatReason(value: string): string {
    return value.replaceAll("_", " ");
}

function preflightReasonHint(reason: string): string {
    return PREFLIGHT_REASON_HINTS[reason] ?? "Нужна ручная проверка причины блокировки.";
}

function campaignStatusLabel(status: MarketingDisplayStatus): string {
    const labels: Record<MarketingDisplayStatus, string> = {
        draft: "Черновик",
        ready: "Legacy: ready",
        executed: "Legacy: executed",
        paused: "На паузе",
        in_review: "На ревью",
        approved: "Подтверждена",
        scheduled: "Запланирована",
        running: "В отправке",
        completed: "Завершена",
        cancelled: "Отменена",
        failed: "Ошибка",
    };
    return labels[status] ?? status;
}

function campaignStatusClass(status: MarketingDisplayStatus): string {
    if (status === "completed" || status === "executed") {
        return "bg-emerald-100 text-emerald-700";
    }
    if (status === "approved" || status === "scheduled" || status === "running") {
        return "bg-sky-100 text-sky-700";
    }
    if (status === "in_review") {
        return "bg-indigo-100 text-indigo-700";
    }
    if (status === "paused") {
        return "bg-amber-100 text-amber-700";
    }
    if (status === "failed" || status === "cancelled") {
        return "bg-red-100 text-red-700";
    }
    return "bg-muted text-muted-foreground";
}

function resolveCampaignStatus(campaign: MarketingCampaign): MarketingDisplayStatus {
    return campaign.status_v2 || campaign.status;
}

function parseAudienceFunnel(value: unknown): MarketingAudienceFunnel | null {
    if (!value || typeof value !== "object") {
        return null;
    }
    const payload = value as Record<string, unknown>;
    const rawCounts = payload.suppression_reason_counts;
    const suppression_reason_counts: Record<string, number> = {};
    if (rawCounts && typeof rawCounts === "object") {
        for (const [key, raw] of Object.entries(rawCounts as Record<string, unknown>)) {
            const parsed = Number(raw ?? 0);
            suppression_reason_counts[key] = Number.isFinite(parsed) ? Math.trunc(parsed) : 0;
        }
    }
    return {
        candidate_count: Number(payload.candidate_count ?? 0) || 0,
        matched_count: Number(payload.matched_count ?? 0) || 0,
        segment_excluded_count: Number(payload.segment_excluded_count ?? 0) || 0,
        eligible_count: Number(payload.eligible_count ?? 0) || 0,
        suppressed_count: Number(payload.suppressed_count ?? 0) || 0,
        suppression_reason_counts,
    };
}

function toBool(value: unknown, fallback: boolean): boolean {
    if (typeof value === "boolean") {
        return value;
    }
    if (typeof value === "string") {
        const normalized = value.trim().toLowerCase();
        if (["1", "true", "yes", "on"].includes(normalized)) {
            return true;
        }
        if (["0", "false", "no", "off"].includes(normalized)) {
            return false;
        }
    }
    return fallback;
}

function normalizeSegmentParamsByDefinition(
    definition: MarketingSegmentDefinition,
    raw: SegmentParams | null | undefined,
): SegmentParams {
    const source = raw && typeof raw === "object" ? raw : {};
    const normalized: SegmentParams = {};

    for (const field of definition.editable_fields) {
        const fallback = definition.defaults[field.key];
        const rawValue = source[field.key];
        if (field.type === "bool") {
            normalized[field.key] = toBool(rawValue, Boolean(fallback));
            continue;
        }
        const fallbackNum = Number(fallback ?? 0);
        const parsed = Number(rawValue);
        const min = field.min ?? Number.MIN_SAFE_INTEGER;
        const max = field.max ?? Number.MAX_SAFE_INTEGER;
        const value = Number.isFinite(parsed) ? Math.trunc(parsed) : Math.trunc(fallbackNum);
        normalized[field.key] = Math.min(max, Math.max(min, value));
    }

    return normalized;
}

function sortObjectDeep(value: unknown): unknown {
    if (Array.isArray(value)) {
        return value.map((item) => sortObjectDeep(item));
    }
    if (!value || typeof value !== "object") {
        return value;
    }
    const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b));
    const sorted: Record<string, unknown> = {};
    for (const [key, nested] of entries) {
        sorted[key] = sortObjectDeep(nested);
    }
    return sorted;
}

function stableJson(value: unknown): string {
    return JSON.stringify(sortObjectDeep(value));
}

function segmentLabel(definition: MarketingSegmentDefinition | undefined, code: MarketingSegmentCode): string {
    if (definition) {
        return definition.label;
    }
    return code;
}

function renderSegmentParamField(
    field: MarketingSegmentEditableField,
    params: SegmentParams,
    onChange: (key: string, value: unknown) => void,
    disabled: boolean,
) {
    const key = field.key;
    if (field.type === "bool") {
        const checked = Boolean(params[key]);
        return (
            <label key={key} className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm">
                <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => onChange(key, event.target.checked)}
                    disabled={disabled}
                />
                <span>{field.label}</span>
            </label>
        );
    }

    const min = field.min ?? 1;
    const max = field.max ?? 3650;
    const step = field.step ?? 1;
    const value = Number(params[key] ?? min);

    return (
        <label key={key} className="text-sm">
            <div className="mb-1 text-xs text-muted-foreground">{field.label}</div>
            <input
                type="number"
                min={min}
                max={max}
                step={step}
                className="h-10 w-full rounded-lg border border-border bg-card px-3 text-sm"
                value={Number.isFinite(value) ? Math.trunc(value) : min}
                onChange={(event) => onChange(key, parseBoundedInt(event.target.value, min, min, max))}
                disabled={disabled}
            />
        </label>
    );
}

export default function MarketingPage() {
    const { data: session } = useSession();
    const [name, setName] = useState("");
    const [messageText, setMessageText] = useState("");
    const [segmentCode, setSegmentCode] = useState<MarketingSegmentCode>("reactivation_30_120");
    const [segmentParams, setSegmentParams] = useState<SegmentParams>({});

    const [editName, setEditName] = useState("");
    const [editMessageText, setEditMessageText] = useState("");
    const [editSegmentCode, setEditSegmentCode] = useState<MarketingSegmentCode>("reactivation_30_120");
    const [editSegmentParams, setEditSegmentParams] = useState<SegmentParams>({});

    const [sampleLimit, setSampleLimit] = useState(5);
    const [maxRecipients, setMaxRecipients] = useState(200);
    const [audienceLimit, setAudienceLimit] = useState(100);
    const [includeSuppressed, setIncludeSuppressed] = useState(true);
    const [lifecycleReason, setLifecycleReason] = useState("");
    const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
    const [busyAction, setBusyAction] = useState<string | null>(null);
    const [executeModalOpen, setExecuteModalOpen] = useState(false);
    const [lastPreviewFunnel, setLastPreviewFunnel] = useState<MarketingAudienceFunnel | null>(null);

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const {
        scope,
        setBranchId: setScopeBranchId,
        syncFromRuntime,
        persistScopeToStorage,
    } = useConsoleContextScope(meData);

    const role = meData?.agent?.role ?? "manager";
    const canReadMarketing = canAccessConsole(role, "marketing", "read");
    const branchOptions = useMemo(() => meData?.branches ?? [], [meData?.branches]);
    const selectedBranchId = scope.branchId || meData?.selected_branch_id || branchOptions[0]?.id || "";

    useEffect(() => {
        if (!branchOptions.length || scope.branchId || !selectedBranchId) {
            return;
        }
        setScopeBranchId(selectedBranchId);
        persistScopeToStorage({ branchId: selectedBranchId });
    }, [branchOptions, persistScopeToStorage, scope.branchId, selectedBranchId, setScopeBranchId]);

    useEffect(() => {
        syncFromRuntime();
    }, [syncFromRuntime]);

    const {
        data: segmentsData,
        isError: segmentsIsError,
        error: segmentsError,
    } = useQuery({
        queryKey: ["marketing-segment-catalog"],
        queryFn: async () => {
            const response = await adminApi.getMarketingSegmentsCatalog();
            return response.data;
        },
        enabled: !!session && canReadMarketing,
    });

    const segmentDefinitions = useMemo<MarketingSegmentDefinition[]>(() => {
        const items = segmentsData?.items ?? [];
        return items.length ? items : FALLBACK_SEGMENTS;
    }, [segmentsData?.items]);

    const segmentDefinitionByCode = useMemo(() => {
        return new Map<MarketingSegmentCode, MarketingSegmentDefinition>(
            segmentDefinitions.map((item) => [item.code, item]),
        );
    }, [segmentDefinitions]);

    const segmentDefinition = segmentDefinitionByCode.get(segmentCode) ?? FALLBACK_SEGMENTS[0];
    const editSegmentDefinition = segmentDefinitionByCode.get(editSegmentCode) ?? FALLBACK_SEGMENTS[0];

    useEffect(() => {
        if (Object.keys(segmentParams).length > 0) {
            return;
        }
        setSegmentParams(normalizeSegmentParamsByDefinition(segmentDefinition, null));
    }, [segmentDefinition, segmentParams]);

    const {
        data: campaignsData,
        isLoading: campaignsLoading,
        isError: campaignsIsError,
        error: campaignsError,
        refetch: refetchCampaigns,
    } = useQuery({
        queryKey: ["marketing-campaigns", selectedBranchId],
        queryFn: async () => {
            const response = await adminApi.listMarketingCampaigns({ branch_id: selectedBranchId || undefined });
            return response.data;
        },
        enabled: !!session && canReadMarketing && !!selectedBranchId,
    });

    const campaigns = useMemo(() => campaignsData?.items ?? [], [campaignsData?.items]);

    useEffect(() => {
        if (!campaigns.length) {
            setSelectedCampaignId(null);
            return;
        }
        if (selectedCampaignId && campaigns.some((item) => item.id === selectedCampaignId)) {
            return;
        }
        setSelectedCampaignId(campaigns[0].id);
    }, [campaigns, selectedCampaignId]);

    const selectedCampaign = useMemo(
        () => campaigns.find((item) => item.id === selectedCampaignId) ?? null,
        [campaigns, selectedCampaignId],
    );

    useEffect(() => {
        setExecuteModalOpen(false);
        setLastPreviewFunnel(null);
    }, [selectedCampaignId]);

    useEffect(() => {
        if (!selectedCampaign) {
            setEditName("");
            setEditMessageText("");
            setEditSegmentCode("reactivation_30_120");
            setEditSegmentParams(normalizeSegmentParamsByDefinition(FALLBACK_SEGMENTS[0], null));
            return;
        }
        setEditName(selectedCampaign.name);
        setEditMessageText(selectedCampaign.message_text);
        setEditSegmentCode(selectedCampaign.segment_code);
        const definition = segmentDefinitionByCode.get(selectedCampaign.segment_code) ?? FALLBACK_SEGMENTS[0];
        setEditSegmentParams(normalizeSegmentParamsByDefinition(definition, selectedCampaign.segment_params));
    }, [selectedCampaign, segmentDefinitionByCode]);

    const {
        data: diagnosticsData,
        isLoading: diagnosticsLoading,
        isError: diagnosticsIsError,
        error: diagnosticsError,
        refetch: refetchDiagnostics,
    } = useQuery({
        queryKey: ["marketing-diagnostics", selectedCampaignId, sampleLimit],
        queryFn: async () => {
            const response = await adminApi.getMarketingCampaignDiagnostics(selectedCampaignId ?? "", {
                sample_limit: sampleLimit,
            });
            return response.data;
        },
        enabled: !!session && canReadMarketing && !!selectedCampaignId,
    });

    const {
        data: preflightData,
        isLoading: preflightLoading,
        isError: preflightIsError,
        error: preflightError,
        refetch: refetchPreflight,
    } = useQuery({
        queryKey: ["marketing-preflight", selectedCampaignId],
        queryFn: async () => {
            const response = await adminApi.getMarketingCampaignPreflight(selectedCampaignId ?? "");
            return response.data;
        },
        enabled: !!session && canReadMarketing && !!selectedCampaignId,
    });

    const {
        data: audienceData,
        isLoading: audienceLoading,
        isError: audienceIsError,
        error: audienceError,
        refetch: refetchAudience,
    } = useQuery({
        queryKey: ["marketing-audience", selectedCampaignId, includeSuppressed, audienceLimit],
        queryFn: async () => {
            const response = await adminApi.getMarketingCampaignAudience(selectedCampaignId ?? "", {
                include_suppressed: includeSuppressed,
                limit: audienceLimit,
            });
            return response.data;
        },
        enabled: !!session && canReadMarketing && !!selectedCampaignId,
    });

    if (meLoading) {
        return <div className="p-6 text-sm text-muted-foreground">Загрузка...</div>;
    }

    if (!canReadMarketing) {
        return <AccessDenied message="Нужна роль owner/admin/platform_admin для управления маркетингом." />;
    }

    const selectedStatus = selectedCampaign ? resolveCampaignStatus(selectedCampaign) : null;
    const canEditCampaign = selectedStatus ? ["draft", "in_review", "ready"].includes(selectedStatus) : false;
    const canRequestApproval = selectedStatus ? ["draft", "ready"].includes(selectedStatus) : false;
    const canApprove = selectedStatus ? ["in_review", "ready"].includes(selectedStatus) : false;
    const canPause = selectedStatus ? ["approved", "scheduled", "running", "executed"].includes(selectedStatus) : false;
    const canResume = selectedStatus === "paused";
    const canExecute = selectedStatus ? ["approved", "scheduled"].includes(selectedStatus) : false;

    const diagnostics: MarketingCampaignDiagnosticsResponse | null = diagnosticsData ?? null;
    const preflight: MarketingCampaignPreflightResponse | null = preflightData ?? null;
    const audienceRows: MarketingCampaignRecipient[] = audienceData?.items ?? [];

    const campaignsErrorMessage = campaignsIsError ? parseApiError(campaignsError).message : null;
    const diagnosticsErrorMessage = diagnosticsIsError ? parseApiError(diagnosticsError).message : null;
    const preflightErrorMessage = preflightIsError ? parseApiError(preflightError).message : null;
    const audienceErrorMessage = audienceIsError ? parseApiError(audienceError).message : null;
    const segmentsErrorMessage = segmentsIsError ? parseApiError(segmentsError).message : null;

    const failureClassRows = diagnostics
        ? Object.entries(diagnostics.failure_classes ?? {}).sort((a, b) => b[1] - a[1])
        : [];

    const providerBillingBlocked = Boolean(preflight?.provider_billing_blocked);
    const canConfirmExecute = Boolean(preflight?.preflight_valid) && !providerBillingBlocked;
    const executeBlockedByPreflight = !canConfirmExecute;

    const selectedSnapshotFunnel = parseAudienceFunnel(
        preflight?.preview_stats ??
            ((selectedCampaign?.preflight_snapshot as Record<string, unknown> | null)?.preview_stats ?? null),
    );
    const audienceFunnel = lastPreviewFunnel ?? selectedSnapshotFunnel;
    const audienceFunnelReasonRows = audienceFunnel
        ? Object.entries(audienceFunnel.suppression_reason_counts ?? {}).sort((a, b) => b[1] - a[1])
        : [];

    const normalizedEditParams = normalizeSegmentParamsByDefinition(editSegmentDefinition, editSegmentParams);
    const currentCampaignParams = selectedCampaign
        ? normalizeSegmentParamsByDefinition(
              segmentDefinitionByCode.get(selectedCampaign.segment_code) ?? FALLBACK_SEGMENTS[0],
              selectedCampaign.segment_params,
          )
        : {};

    const campaignChanged = Boolean(
        selectedCampaign &&
            (
                editName.trim() !== selectedCampaign.name ||
                editMessageText.trim() !== selectedCampaign.message_text ||
                editSegmentCode !== selectedCampaign.segment_code ||
                stableJson(normalizedEditParams) !== stableJson(currentCampaignParams)
            ),
    );

    const selectedSegmentDef = selectedCampaign
        ? segmentDefinitionByCode.get(selectedCampaign.segment_code) ?? FALLBACK_SEGMENTS[0]
        : null;
    const selectedSegmentSummary =
        preflight?.segment_summary ?? selectedCampaign?.segment_summary ?? selectedSegmentDef?.summary ?? "";

    const withReasonPayload = () => {
        const normalized = lifecycleReason.trim();
        return normalized ? { reason: normalized } : {};
    };

    const createCampaign = async () => {
        if (!selectedBranchId) {
            toast.error("Сначала выберите филиал в контексте.");
            return;
        }
        if (!name.trim()) {
            toast.error("Укажите название кампании.");
            return;
        }
        if (!messageText.trim()) {
            toast.error("Укажите текст сообщения.");
            return;
        }

        setBusyAction("create");
        try {
            const normalizedParams = normalizeSegmentParamsByDefinition(segmentDefinition, segmentParams);
            await adminApi.createMarketingCampaign({
                branch_id: selectedBranchId,
                name: name.trim(),
                message_text: messageText.trim(),
                segment_code: segmentCode,
                segment_params: normalizedParams,
                audience_mode: "branch_active_conversations",
            });
            setName("");
            setMessageText("");
            setSegmentParams(normalizeSegmentParamsByDefinition(segmentDefinition, null));
            await refetchCampaigns();
            toast.success("Кампания создана.");
        } catch (error) {
            const parsed = parseApiError(error);
            toast.error(parsed.message);
        } finally {
            setBusyAction(null);
        }
    };

    const updateCampaign = async () => {
        if (!selectedCampaign) {
            return;
        }
        if (!campaignChanged) {
            toast.error("Нет изменений для сохранения.");
            return;
        }
        if (!editName.trim() || !editMessageText.trim()) {
            toast.error("Название и текст сообщения обязательны.");
            return;
        }

        setBusyAction("update");
        try {
            await adminApi.updateMarketingCampaign(selectedCampaign.id, {
                name: editName.trim(),
                message_text: editMessageText.trim(),
                segment_code: editSegmentCode,
                segment_params: normalizedEditParams,
                reason: lifecycleReason.trim() || null,
            });
            setLastPreviewFunnel(null);
            await Promise.all([refetchCampaigns(), refetchAudience(), refetchPreflight()]);
            toast.success("Кампания обновлена. Выполните Preview для пересчета аудитории.");
        } catch (error) {
            toast.error(parseApiError(error).message);
        } finally {
            setBusyAction(null);
        }
    };

    const previewCampaign = async () => {
        if (!selectedCampaign) {
            return;
        }
        setBusyAction("preview");
        try {
            const response = await adminApi.previewMarketingCampaign(selectedCampaign.id, { sample_limit: sampleLimit });
            setLastPreviewFunnel(response.data.funnel ?? null);
            await Promise.all([refetchCampaigns(), refetchAudience(), refetchPreflight()]);
            toast.success("Preview выполнен.");
        } catch (error) {
            toast.error(parseApiError(error).message);
        } finally {
            setBusyAction(null);
        }
    };

    const requestApproval = async () => {
        if (!selectedCampaign) {
            return;
        }
        setBusyAction("request-approval");
        try {
            await adminApi.requestMarketingCampaignApproval(selectedCampaign.id, withReasonPayload());
            await Promise.all([refetchCampaigns(), refetchPreflight()]);
            toast.success("Кампания отправлена на подтверждение.");
        } catch (error) {
            toast.error(parseApiError(error).message);
        } finally {
            setBusyAction(null);
        }
    };

    const approveCampaign = async () => {
        if (!selectedCampaign) {
            return;
        }
        setBusyAction("approve");
        try {
            await adminApi.approveMarketingCampaign(selectedCampaign.id, withReasonPayload());
            await Promise.all([refetchCampaigns(), refetchPreflight()]);
            toast.success("Кампания подтверждена.");
        } catch (error) {
            toast.error(parseApiError(error).message);
        } finally {
            setBusyAction(null);
        }
    };

    const pauseCampaign = async () => {
        if (!selectedCampaign) {
            return;
        }
        setBusyAction("pause");
        try {
            await adminApi.pauseMarketingCampaign(selectedCampaign.id, withReasonPayload());
            await refetchCampaigns();
            toast.success("Кампания на паузе.");
        } catch (error) {
            toast.error(parseApiError(error).message);
        } finally {
            setBusyAction(null);
        }
    };

    const resumeCampaign = async () => {
        if (!selectedCampaign) {
            return;
        }
        setBusyAction("resume");
        try {
            await adminApi.resumeMarketingCampaign(selectedCampaign.id, withReasonPayload());
            await Promise.all([refetchCampaigns(), refetchPreflight()]);
            toast.success("Кампания возобновлена.");
        } catch (error) {
            toast.error(parseApiError(error).message);
        } finally {
            setBusyAction(null);
        }
    };

    const refreshPreflight = async () => {
        if (!selectedCampaign) {
            return;
        }
        setBusyAction("preflight");
        try {
            await refetchPreflight();
            toast.success("Preflight обновлен.");
        } catch (error) {
            toast.error(parseApiError(error).message);
        } finally {
            setBusyAction(null);
        }
    };

    const executeCampaign = async () => {
        if (!selectedCampaign) {
            return;
        }
        setBusyAction("execute");
        try {
            const response = await adminApi.executeMarketingCampaign(selectedCampaign.id, {
                confirm_send: true,
                max_recipients: maxRecipients,
            });
            await Promise.all([refetchCampaigns(), refetchDiagnostics(), refetchPreflight()]);
            setExecuteModalOpen(false);
            toast.success(`Поставлено в очередь: ${response.data.queued_count}`);
        } catch (error) {
            toast.error(parseApiError(error).message);
        } finally {
            setBusyAction(null);
        }
    };

    const retryFailed = async () => {
        if (!selectedCampaign) {
            return;
        }
        const confirmed = window.confirm("Повторить failed доставки этой кампании?");
        if (!confirmed) {
            return;
        }
        setBusyAction("retry");
        try {
            const response = await adminApi.retryFailedMarketingCampaignDeliveries(selectedCampaign.id, {
                confirm_retry: true,
                limit: 100,
            });
            await refetchDiagnostics();
            toast.success(`Повторено: ${response.data.retried_count}, permanent: ${response.data.skipped_permanent}`);
        } catch (error) {
            toast.error(parseApiError(error).message);
        } finally {
            setBusyAction(null);
        }
    };

    return (
        <div className="space-y-6 p-6">
            <div>
                <h1 className="text-2xl font-semibold">Маркетинг</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Понятный поток для владельца: выберите аудиторию, проверьте расчеты, подтвердите и отправьте.
                </p>
                {segmentsIsError ? (
                    <p className="mt-2 text-xs text-amber-700">
                        Каталог сегментов не загрузился: {segmentsErrorMessage}. Используются резервные правила.
                    </p>
                ) : null}
            </div>

            <div className="rounded-xl border bg-card p-4">
                <div className="grid gap-3 md:grid-cols-[180px,1fr] md:items-center">
                    <label className="text-sm font-medium text-foreground">Филиал</label>
                    <select
                        className="h-10 rounded-lg border border-border bg-background px-3 text-sm"
                        value={selectedBranchId}
                        onChange={(event) => {
                            const value = event.target.value;
                            setScopeBranchId(value);
                            persistScopeToStorage({ branchId: value });
                        }}
                    >
                        {branchOptions.map((branch) => (
                            <option key={branch.id} value={branch.id}>
                                {branch.name ?? branch.id}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-[380px,1fr]">
                <section className="rounded-xl border bg-card p-4">
                    <h2 className="text-lg font-semibold">Новая кампания</h2>
                    <div className="mt-3 space-y-3">
                        <input
                            className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm"
                            placeholder="Название"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                        />
                        <select
                            className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm"
                            value={segmentCode}
                            onChange={(event) => {
                                const next = event.target.value as MarketingSegmentCode;
                                setSegmentCode(next);
                                const definition = segmentDefinitionByCode.get(next) ?? FALLBACK_SEGMENTS[0];
                                setSegmentParams(normalizeSegmentParamsByDefinition(definition, null));
                            }}
                        >
                            {segmentDefinitions.map((segment) => (
                                <option key={segment.code} value={segment.code}>
                                    {segment.label}
                                </option>
                            ))}
                        </select>

                        <div className="rounded-lg border bg-background p-3">
                            <div className="text-sm font-medium">Как считается</div>
                            <p className="mt-1 text-xs text-muted-foreground">{segmentDefinition.summary}</p>
                            <p className="mt-1 text-xs text-muted-foreground">{segmentDefinition.description}</p>
                        </div>

                        <div className="grid gap-2">
                            {segmentDefinition.editable_fields.map((field) =>
                                renderSegmentParamField(
                                    field,
                                    normalizeSegmentParamsByDefinition(segmentDefinition, segmentParams),
                                    (key, value) => setSegmentParams((prev) => ({ ...prev, [key]: value })),
                                    busyAction === "create",
                                ),
                            )}
                        </div>

                        <textarea
                            className="min-h-[120px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            placeholder="Текст WhatsApp сообщения"
                            value={messageText}
                            onChange={(event) => setMessageText(event.target.value)}
                        />
                        <button
                            type="button"
                            className="h-10 w-full rounded-lg bg-foreground px-3 text-sm font-medium text-background disabled:cursor-not-allowed disabled:opacity-60"
                            onClick={createCampaign}
                            disabled={busyAction === "create"}
                        >
                            {busyAction === "create" ? "Создание..." : "Создать кампанию"}
                        </button>
                    </div>

                    <div className="mt-6 border-t pt-4">
                        <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Кампании</h3>
                        {campaignsLoading ? (
                            <p className="mt-2 text-sm text-muted-foreground">Загрузка...</p>
                        ) : campaignsIsError ? (
                            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                                <p>Ошибка загрузки кампаний: {campaignsErrorMessage}</p>
                                <button
                                    type="button"
                                    className="mt-2 h-9 rounded-lg border border-red-300 px-3 text-xs font-medium"
                                    onClick={() => refetchCampaigns()}
                                >
                                    Повторить
                                </button>
                            </div>
                        ) : campaigns.length ? (
                            <ul className="mt-3 space-y-2">
                                {campaigns.map((campaign) => {
                                    const active = campaign.id === selectedCampaignId;
                                    const statusValue = resolveCampaignStatus(campaign);
                                    const definition = segmentDefinitionByCode.get(campaign.segment_code);
                                    return (
                                        <li key={campaign.id}>
                                            <button
                                                type="button"
                                                className={`w-full rounded-lg border px-3 py-2 text-left ${
                                                    active ? "border-foreground bg-accent" : "border-border bg-background"
                                                }`}
                                                onClick={() => setSelectedCampaignId(campaign.id)}
                                            >
                                                <div className="flex items-center justify-between gap-2">
                                                    <span className="truncate text-sm font-medium">{campaign.name}</span>
                                                    <span className={`rounded-full px-2 py-0.5 text-xs ${campaignStatusClass(statusValue)}`}>
                                                        {campaignStatusLabel(statusValue)}
                                                    </span>
                                                </div>
                                                <p className="mt-1 text-xs text-muted-foreground">
                                                    {segmentLabel(definition, campaign.segment_code)}
                                                </p>
                                                <p className="mt-1 text-xs text-muted-foreground">preview: {campaign.preview_total}</p>
                                            </button>
                                        </li>
                                    );
                                })}
                            </ul>
                        ) : (
                            <p className="mt-2 text-sm text-muted-foreground">Кампании не найдены.</p>
                        )}
                    </div>
                </section>

                <section className="rounded-xl border bg-card p-4">
                    {!selectedCampaign ? (
                        <div className="text-sm text-muted-foreground">Выберите кампанию слева.</div>
                    ) : (
                        <>
                            <div className="flex flex-wrap items-center justify-between gap-3">
                                <div>
                                    <h2 className="text-lg font-semibold">{selectedCampaign.name}</h2>
                                    <p className="mt-1 text-sm text-muted-foreground">{selectedCampaign.message_text}</p>
                                </div>
                                <span className={`rounded-full px-3 py-1 text-xs ${campaignStatusClass(selectedStatus ?? "draft")}`}>
                                    {campaignStatusLabel(selectedStatus ?? "draft")}
                                </span>
                            </div>

                            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                <div className="rounded-lg border bg-background p-3">
                                    <div className="text-xs text-muted-foreground">Preview</div>
                                    <div className="mt-1 text-lg font-semibold">{selectedCampaign.preview_total}</div>
                                </div>
                                <div className="rounded-lg border bg-background p-3">
                                    <div className="text-xs text-muted-foreground">Подтверждена</div>
                                    <div className="mt-1 text-sm font-medium">{formatDateTime(selectedCampaign.approved_at)}</div>
                                </div>
                                <div className="rounded-lg border bg-background p-3">
                                    <div className="text-xs text-muted-foreground">Последняя отправка</div>
                                    <div className="mt-1 text-sm font-medium">{formatDateTime(selectedCampaign.executed_at)}</div>
                                </div>
                                <div className="rounded-lg border bg-background p-3">
                                    <div className="text-xs text-muted-foreground">Создана</div>
                                    <div className="mt-1 text-sm font-medium">{formatDateTime(selectedCampaign.created_at)}</div>
                                </div>
                            </div>

                            <div className="mt-5 rounded-lg border bg-background p-3">
                                <h3 className="text-sm font-semibold">Как считается текущий фильтр</h3>
                                <p className="mt-1 text-sm text-muted-foreground">{selectedSegmentSummary || "Описание сегмента недоступно."}</p>
                                <div className="mt-2 flex flex-wrap gap-2">
                                    {Object.entries(selectedCampaign.segment_params ?? {}).map(([key, value]) => (
                                        <span key={key} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                                            {key}: {String(value)}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            <div className="mt-5 space-y-4 rounded-lg border bg-background p-3">
                                <h3 className="text-sm font-semibold">Редактирование кампании (до approve)</h3>

                                <div className="grid gap-3 lg:grid-cols-2">
                                    <label className="text-sm">
                                        <div className="mb-1 text-xs text-muted-foreground">Название</div>
                                        <input
                                            className="h-10 w-full rounded-lg border border-border bg-card px-3 text-sm"
                                            value={editName}
                                            onChange={(event) => setEditName(event.target.value)}
                                            disabled={!canEditCampaign}
                                        />
                                    </label>
                                    <label className="text-sm">
                                        <div className="mb-1 text-xs text-muted-foreground">Сегмент</div>
                                        <select
                                            className="h-10 w-full rounded-lg border border-border bg-card px-3 text-sm"
                                            value={editSegmentCode}
                                            onChange={(event) => {
                                                const next = event.target.value as MarketingSegmentCode;
                                                setEditSegmentCode(next);
                                                const definition = segmentDefinitionByCode.get(next) ?? FALLBACK_SEGMENTS[0];
                                                setEditSegmentParams(normalizeSegmentParamsByDefinition(definition, null));
                                            }}
                                            disabled={!canEditCampaign}
                                        >
                                            {segmentDefinitions.map((segment) => (
                                                <option key={segment.code} value={segment.code}>
                                                    {segment.label}
                                                </option>
                                            ))}
                                        </select>
                                    </label>
                                </div>

                                <div className="rounded-lg border bg-card p-3">
                                    <p className="text-xs text-muted-foreground">{editSegmentDefinition.summary}</p>
                                    <p className="mt-1 text-xs text-muted-foreground">{editSegmentDefinition.description}</p>
                                </div>

                                <div className="grid gap-2 lg:grid-cols-2">
                                    {editSegmentDefinition.editable_fields.map((field) =>
                                        renderSegmentParamField(
                                            field,
                                            normalizedEditParams,
                                            (key, value) => setEditSegmentParams((prev) => ({ ...prev, [key]: value })),
                                            !canEditCampaign,
                                        ),
                                    )}
                                </div>

                                <label className="text-sm">
                                    <div className="mb-1 text-xs text-muted-foreground">Текст сообщения</div>
                                    <textarea
                                        className="min-h-[90px] w-full rounded-lg border border-border bg-card px-3 py-2 text-sm"
                                        value={editMessageText}
                                        onChange={(event) => setEditMessageText(event.target.value)}
                                        disabled={!canEditCampaign}
                                    />
                                </label>

                                <label className="text-sm">
                                    <div className="mb-1 text-xs text-muted-foreground">Причина (audit, необязательно)</div>
                                    <input
                                        className="h-10 w-full rounded-lg border border-border bg-card px-3 text-sm"
                                        placeholder="например: сезонная акция"
                                        value={lifecycleReason}
                                        onChange={(event) => setLifecycleReason(event.target.value)}
                                    />
                                </label>

                                <div className="flex flex-wrap items-center gap-3">
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
                                        onClick={updateCampaign}
                                        disabled={!canEditCampaign || !campaignChanged || busyAction === "update"}
                                    >
                                        {busyAction === "update" ? "Сохранение..." : "Сохранить кампанию"}
                                    </button>
                                    {!canEditCampaign ? (
                                        <span className="text-xs text-amber-700">Редактирование доступно только в draft/in_review.</span>
                                    ) : null}
                                </div>

                                <div className="flex flex-wrap items-end gap-3 border-t pt-3">
                                    <label className="text-sm">
                                        <div className="mb-1 text-xs text-muted-foreground">sample_limit</div>
                                        <input
                                            type="number"
                                            min={1}
                                            max={20}
                                            className="h-10 w-28 rounded-lg border border-border bg-card px-3 text-sm"
                                            value={sampleLimit}
                                            onChange={(event) => setSampleLimit(parseBoundedInt(event.target.value, 5, 1, 20))}
                                        />
                                    </label>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium"
                                        onClick={previewCampaign}
                                        disabled={busyAction === "preview"}
                                    >
                                        {busyAction === "preview" ? "Preview..." : "Preview аудитории"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
                                        onClick={requestApproval}
                                        disabled={!canRequestApproval || busyAction === "request-approval"}
                                    >
                                        {busyAction === "request-approval" ? "..." : "На ревью"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
                                        onClick={approveCampaign}
                                        disabled={!canApprove || busyAction === "approve"}
                                    >
                                        {busyAction === "approve" ? "..." : "Подтвердить"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
                                        onClick={pauseCampaign}
                                        disabled={!canPause || busyAction === "pause"}
                                    >
                                        {busyAction === "pause" ? "..." : "Пауза"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
                                        onClick={resumeCampaign}
                                        disabled={!canResume || busyAction === "resume"}
                                    >
                                        {busyAction === "resume" ? "..." : "Возобновить"}
                                    </button>
                                </div>

                                <div className="flex flex-wrap items-end gap-3 border-t pt-3">
                                    <label className="text-sm">
                                        <div className="mb-1 text-xs text-muted-foreground">max_recipients</div>
                                        <input
                                            type="number"
                                            min={1}
                                            max={500}
                                            className="h-10 w-32 rounded-lg border border-border bg-card px-3 text-sm"
                                            value={maxRecipients}
                                            onChange={(event) => setMaxRecipients(parseBoundedInt(event.target.value, 200, 1, 500))}
                                        />
                                    </label>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium"
                                        onClick={refreshPreflight}
                                        disabled={busyAction === "preflight"}
                                    >
                                        {busyAction === "preflight" ? "..." : "Обновить preflight"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background disabled:cursor-not-allowed disabled:opacity-60"
                                        onClick={() => setExecuteModalOpen(true)}
                                        disabled={busyAction === "execute" || !canExecute || executeBlockedByPreflight}
                                    >
                                        {busyAction === "execute" ? "Отправка..." : "Проверить и отправить"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium"
                                        onClick={retryFailed}
                                        disabled={busyAction === "retry"}
                                    >
                                        {busyAction === "retry" ? "Повтор..." : "Повторить failed"}
                                    </button>
                                </div>
                            </div>

                            <div className="mt-6 border-t pt-4">
                                <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Preflight</h3>
                                {preflightLoading ? (
                                    <p className="mt-2 text-sm text-muted-foreground">Загрузка...</p>
                                ) : preflightIsError ? (
                                    <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                                        <p>Ошибка preflight: {preflightErrorMessage}</p>
                                        <button
                                            type="button"
                                            className="mt-2 h-9 rounded-lg border border-red-300 px-3 text-xs font-medium"
                                            onClick={() => refetchPreflight()}
                                        >
                                            Повторить
                                        </button>
                                    </div>
                                ) : preflight ? (
                                    <>
                                        {providerBillingBlocked ? (
                                            <div className="mt-3 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800">
                                                <div className="font-semibold">Провайдер заблокирован по оплате</div>
                                                <p className="mt-1 text-xs text-red-700">
                                                    Обнаружены ошибки оплаты провайдера ({preflight.provider_billing_blocked_count}).
                                                    Отправка будет разблокирована только после оплаты на стороне провайдера.
                                                </p>
                                                <a
                                                    href="/integrations"
                                                    className="mt-2 inline-flex h-8 items-center rounded border border-red-300 bg-white px-3 text-xs font-medium text-red-700"
                                                >
                                                    Открыть Integrations
                                                </a>
                                            </div>
                                        ) : null}

                                        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Статус</div>
                                                <div className={`mt-1 text-sm font-semibold ${preflight.preflight_valid ? "text-emerald-700" : "text-red-700"}`}>
                                                    {preflight.preflight_valid ? "Готово к отправке" : "Заблокировано"}
                                                </div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Outbox</div>
                                                <div className="mt-1 text-sm font-medium">{preflight.outbox_health_status}</div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Audience</div>
                                                <div className="mt-1 text-sm font-medium">{preflight.audience_total}</div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Eligible</div>
                                                <div className="mt-1 text-sm font-medium">{preflight.eligible_count}</div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Suppressed</div>
                                                <div className="mt-1 text-sm font-medium">{preflight.suppressed_count}</div>
                                            </div>
                                        </div>

                                        <div className="mt-3 rounded-lg border bg-background p-3">
                                            <div className="text-xs text-muted-foreground">Blocked reasons</div>
                                            {preflight.blocked_reasons.length ? (
                                                <ul className="mt-2 space-y-2">
                                                    {preflight.blocked_reasons.map((item) => (
                                                        <li key={item} className="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
                                                            <div className="font-medium">{formatReason(item)}</div>
                                                            <div className="mt-1 text-red-600">{preflightReasonHint(item)}</div>
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <p className="mt-2 text-xs text-emerald-700">Блокировок нет.</p>
                                            )}
                                        </div>

                                        {audienceFunnel ? (
                                            <div className="mt-3 rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Preview funnel</div>
                                                <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
                                                    <div className="rounded border bg-card p-2 text-xs">
                                                        <div className="text-muted-foreground">Candidates</div>
                                                        <div className="mt-1 font-semibold">{audienceFunnel.candidate_count}</div>
                                                    </div>
                                                    <div className="rounded border bg-card p-2 text-xs">
                                                        <div className="text-muted-foreground">Matched</div>
                                                        <div className="mt-1 font-semibold">{audienceFunnel.matched_count}</div>
                                                    </div>
                                                    <div className="rounded border bg-card p-2 text-xs">
                                                        <div className="text-muted-foreground">Excluded</div>
                                                        <div className="mt-1 font-semibold">{audienceFunnel.segment_excluded_count}</div>
                                                    </div>
                                                    <div className="rounded border bg-card p-2 text-xs">
                                                        <div className="text-muted-foreground">Suppressed</div>
                                                        <div className="mt-1 font-semibold">{audienceFunnel.suppressed_count}</div>
                                                    </div>
                                                    <div className="rounded border bg-card p-2 text-xs">
                                                        <div className="text-muted-foreground">Eligible</div>
                                                        <div className="mt-1 font-semibold">{audienceFunnel.eligible_count}</div>
                                                    </div>
                                                </div>
                                                {audienceFunnelReasonRows.length ? (
                                                    <div className="mt-2 text-xs text-muted-foreground">
                                                        suppression: {audienceFunnelReasonRows.map(([reason, count]) => `${formatReason(reason)} (${count})`).join(", ")}
                                                    </div>
                                                ) : null}
                                            </div>
                                        ) : null}
                                    </>
                                ) : (
                                    <p className="mt-2 text-sm text-muted-foreground">Preflight недоступен.</p>
                                )}
                            </div>

                            <div className="mt-6 border-t pt-4">
                                <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Audience</h3>
                                <div className="mt-3 flex flex-wrap items-end gap-3">
                                    <label className="inline-flex items-center gap-2 text-sm text-muted-foreground">
                                        <input
                                            type="checkbox"
                                            checked={includeSuppressed}
                                            onChange={(event) => setIncludeSuppressed(event.target.checked)}
                                        />
                                        Показывать suppressed
                                    </label>
                                    <label className="text-sm">
                                        <div className="mb-1 text-xs text-muted-foreground">limit</div>
                                        <input
                                            type="number"
                                            min={1}
                                            max={500}
                                            className="h-10 w-24 rounded-lg border border-border bg-background px-3 text-sm"
                                            value={audienceLimit}
                                            onChange={(event) => setAudienceLimit(parseBoundedInt(event.target.value, 100, 1, 500))}
                                        />
                                    </label>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-background px-4 text-sm font-medium"
                                        onClick={() => refetchAudience()}
                                    >
                                        Обновить аудиторию
                                    </button>
                                    <div className="text-xs text-muted-foreground">
                                        total: {audienceData?.total_count ?? 0} | eligible: {audienceData?.eligible_count ?? 0} | suppressed: {audienceData?.suppressed_count ?? 0}
                                    </div>
                                </div>

                                {audienceLoading ? (
                                    <p className="mt-2 text-sm text-muted-foreground">Загрузка...</p>
                                ) : audienceIsError ? (
                                    <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                                        <p>Ошибка audience: {audienceErrorMessage}</p>
                                        <button
                                            type="button"
                                            className="mt-2 h-9 rounded-lg border border-red-300 px-3 text-xs font-medium"
                                            onClick={() => refetchAudience()}
                                        >
                                            Повторить
                                        </button>
                                    </div>
                                ) : audienceRows.length ? (
                                    <div className="mt-3 overflow-x-auto rounded-lg border bg-background">
                                        <table className="min-w-full text-xs">
                                            <thead className="bg-muted/40 text-left text-muted-foreground">
                                                <tr>
                                                    <th className="px-3 py-2 font-medium">Клиент</th>
                                                    <th className="px-3 py-2 font-medium">Почему в аудитории</th>
                                                    <th className="px-3 py-2 font-medium">Почему исключен</th>
                                                    <th className="px-3 py-2 font-medium">Тех. коды</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {audienceRows.map((row) => (
                                                    <tr key={row.id} className="border-t border-border/60 align-top">
                                                        <td className="px-3 py-2">
                                                            <div className="font-medium text-foreground">{row.recipient_jid}</div>
                                                            <div className="mt-1 text-muted-foreground">conv: {row.conversation_id ?? "-"}</div>
                                                            <div className="text-muted-foreground">user: {row.user_id ?? "-"}</div>
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            {row.reason_hints.length ? (
                                                                <ul className="space-y-1">
                                                                    {row.reason_hints.map((hint, idx) => (
                                                                        <li key={`${row.id}-reason-${idx}`} className="text-muted-foreground">{hint}</li>
                                                                    ))}
                                                                </ul>
                                                            ) : (
                                                                <span className="text-muted-foreground">-</span>
                                                            )}
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            {row.suppressed ? (
                                                                row.suppression_hints.length ? (
                                                                    <ul className="space-y-1">
                                                                        {row.suppression_hints.map((hint, idx) => (
                                                                            <li key={`${row.id}-suppression-${idx}`} className="text-red-700">{hint}</li>
                                                                        ))}
                                                                    </ul>
                                                                ) : (
                                                                    <span className="text-red-700">suppressed</span>
                                                                )
                                                            ) : (
                                                                <span className="text-emerald-700">eligible</span>
                                                            )}
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            <div className="flex flex-wrap gap-1">
                                                                {row.reason_codes.map((reason) => (
                                                                    <span key={reason} className="rounded-full bg-sky-100 px-2 py-0.5 text-[11px] text-sky-700">
                                                                        {formatReason(reason)}
                                                                    </span>
                                                                ))}
                                                                {row.suppression_reasons.map((reason) => (
                                                                    <span key={reason} className="rounded-full bg-red-100 px-2 py-0.5 text-[11px] text-red-700">
                                                                        {formatReason(reason)}
                                                                    </span>
                                                                ))}
                                                                {!row.reason_codes.length && !row.suppression_reasons.length ? (
                                                                    <span className="text-muted-foreground">-</span>
                                                                ) : null}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                                        <p>Audience пустой.</p>
                                        {audienceFunnel ? (
                                            <p className="mt-1 text-xs text-amber-700">
                                                candidates: {audienceFunnel.candidate_count}, matched: {audienceFunnel.matched_count}, suppressed: {audienceFunnel.suppressed_count}, eligible: {audienceFunnel.eligible_count}.
                                            </p>
                                        ) : (
                                            <p className="mt-1 text-xs text-amber-700">Сначала запустите Preview аудитории.</p>
                                        )}
                                    </div>
                                )}
                            </div>

                            <div className="mt-6 border-t pt-4">
                                <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Diagnostics</h3>
                                {diagnosticsLoading ? (
                                    <p className="mt-2 text-sm text-muted-foreground">Загрузка...</p>
                                ) : diagnosticsIsError ? (
                                    <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                                        <p>Ошибка diagnostics: {diagnosticsErrorMessage}</p>
                                        <button
                                            type="button"
                                            className="mt-2 h-9 rounded-lg border border-red-300 px-3 text-xs font-medium"
                                            onClick={() => refetchDiagnostics()}
                                        >
                                            Повторить
                                        </button>
                                    </div>
                                ) : diagnostics ? (
                                    <>
                                        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Всего</div>
                                                <div className="mt-1 text-lg font-semibold">{diagnostics.total_count}</div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Queued</div>
                                                <div className="mt-1 text-lg font-semibold">{diagnostics.queued_count}</div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Sent</div>
                                                <div className="mt-1 text-lg font-semibold">{diagnostics.sent_count}</div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Failed</div>
                                                <div className="mt-1 text-lg font-semibold text-red-700">{diagnostics.failed_count}</div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Replied</div>
                                                <div className="mt-1 text-lg font-semibold">{diagnostics.replied_count}</div>
                                            </div>
                                        </div>
                                        <div className="mt-3 grid gap-3 sm:grid-cols-2">
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Retryable failed</div>
                                                <div className="mt-1 text-lg font-semibold">{diagnostics.retryable_failed_count}</div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Permanent failed</div>
                                                <div className="mt-1 text-lg font-semibold text-red-700">{diagnostics.permanent_failed_count}</div>
                                            </div>
                                        </div>

                                        <div className="mt-3 rounded-lg border bg-background p-3">
                                            <div className="text-sm font-medium">Failure classes</div>
                                            {failureClassRows.length ? (
                                                <ul className="mt-2 space-y-1 text-xs">
                                                    {failureClassRows.map(([reason, count]) => (
                                                        <li key={reason} className="flex items-center justify-between">
                                                            <span className="text-muted-foreground">{formatReason(reason)}</span>
                                                            <span className="font-semibold">{count}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <p className="mt-2 text-xs text-muted-foreground">Нет failure classes.</p>
                                            )}
                                        </div>

                                        <div className="mt-4 rounded-lg border bg-background p-3">
                                            <div className="text-sm font-medium">Примеры failed</div>
                                            {diagnostics.sample_failed.length ? (
                                                <ul className="mt-2 space-y-2">
                                                    {diagnostics.sample_failed.map((item) => (
                                                        <li key={item.delivery_id} className="rounded border border-border p-2 text-xs">
                                                            <div className="font-medium text-foreground">
                                                                {item.recipient_jid ?? item.conversation_id ?? item.delivery_id}
                                                            </div>
                                                            <div className="mt-1 text-muted-foreground">
                                                                outbox: {item.outbox_status ?? "-"} | error: {item.last_error ?? "-"}
                                                            </div>
                                                        </li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <p className="mt-2 text-xs text-muted-foreground">Нет failed записей.</p>
                                            )}
                                        </div>
                                    </>
                                ) : (
                                    <p className="mt-2 text-sm text-muted-foreground">Diagnostics недоступен.</p>
                                )}
                            </div>
                        </>
                    )}
                </section>
            </div>

            {executeModalOpen && selectedCampaign ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-2xl rounded-xl border bg-card p-5 shadow-xl">
                        <div className="flex items-center justify-between gap-2">
                            <h3 className="text-lg font-semibold">Подтверждение отправки</h3>
                            <button
                                type="button"
                                className="h-8 rounded border border-border px-2 text-xs"
                                onClick={() => setExecuteModalOpen(false)}
                            >
                                Закрыть
                            </button>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">{selectedCampaign.name}</p>
                        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                            <div className="rounded-lg border bg-background p-3">
                                <div className="text-xs text-muted-foreground">Eligible</div>
                                <div className="mt-1 text-lg font-semibold">{preflight?.eligible_count ?? 0}</div>
                            </div>
                            <div className="rounded-lg border bg-background p-3">
                                <div className="text-xs text-muted-foreground">Suppressed</div>
                                <div className="mt-1 text-lg font-semibold">{preflight?.suppressed_count ?? 0}</div>
                            </div>
                            <div className="rounded-lg border bg-background p-3">
                                <div className="text-xs text-muted-foreground">Max recipients</div>
                                <div className="mt-1 text-lg font-semibold">{maxRecipients}</div>
                            </div>
                            <div className="rounded-lg border bg-background p-3">
                                <div className="text-xs text-muted-foreground">Outbox status</div>
                                <div className="mt-1 text-sm font-semibold">{preflight?.outbox_health_status ?? "unknown"}</div>
                            </div>
                        </div>
                        <div className="mt-3 rounded-lg border bg-background p-3">
                            <div className="text-xs text-muted-foreground">Blocked reasons</div>
                            {preflight?.blocked_reasons?.length ? (
                                <ul className="mt-2 space-y-2 text-xs">
                                    {preflight.blocked_reasons.map((item) => (
                                        <li key={item} className="rounded border border-red-200 bg-red-50 p-2 text-red-700">
                                            <div className="font-medium">{formatReason(item)}</div>
                                            <div className="mt-1 text-red-600">{preflightReasonHint(item)}</div>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <p className="mt-2 text-xs text-emerald-700">Блокировок нет.</p>
                            )}
                        </div>
                        <div className="mt-4 flex justify-end gap-2">
                            <button
                                type="button"
                                className="h-10 rounded-lg border border-border px-4 text-sm"
                                onClick={() => setExecuteModalOpen(false)}
                            >
                                Отмена
                            </button>
                            <button
                                type="button"
                                className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background disabled:cursor-not-allowed disabled:opacity-60"
                                onClick={executeCampaign}
                                disabled={busyAction === "execute" || !canConfirmExecute}
                            >
                                {busyAction === "execute" ? "Отправка..." : "Подтвердить отправку"}
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
}
