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
    type MarketingCampaign,
    type MarketingCampaignDiagnosticsResponse,
    type MarketingCampaignPreflightResponse,
    type MarketingCampaignRecipient,
    type MarketingSegmentCode,
} from "@/lib/api-client";
import { useConsoleContextScope } from "@/lib/use-console-context-scope";

const SEGMENT_OPTIONS: Array<{ value: MarketingSegmentCode; label: string }> = [
    { value: "reactivation_30_120", label: "Возврат 30-120 дней" },
    { value: "no_show_recovery_14d", label: "После no-show (14 дней)" },
    { value: "engaged_no_booking_7d", label: "Интерес без записи (7 дней)" },
];

type MarketingDisplayStatus = MarketingCampaign["status"] | MarketingCampaign["status_v2"];

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

function segmentLabel(segment: MarketingSegmentCode): string {
    return SEGMENT_OPTIONS.find((item) => item.value === segment)?.label ?? segment;
}

function formatReason(value: string): string {
    return value.replaceAll("_", " ");
}

function parseBoundedInt(value: string, fallback: number, min: number, max: number): number {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
        return fallback;
    }
    return Math.min(max, Math.max(min, Math.trunc(parsed)));
}

const PREFLIGHT_REASON_HINTS: Record<string, string> = {
    runtime_health_critical: "Runtime unhealthy: сначала стабилизируйте outbox/provider.",
    campaign_not_approved: "Кампанию нужно перевести в approved перед execute.",
    audience_snapshot_missing: "Сначала выполните Preview аудитории.",
    eligible_recipients_empty: "Нет eligible контактов: проверьте сегмент и suppression.",
    template_not_approved: "Template gate активен: template_state должен быть approved.",
};

function preflightReasonHint(reason: string): string {
    return PREFLIGHT_REASON_HINTS[reason] ?? "Требуется ручная проверка причины блокировки.";
}

export default function MarketingPage() {
    const { data: session } = useSession();
    const [name, setName] = useState("");
    const [messageText, setMessageText] = useState("");
    const [segmentCode, setSegmentCode] = useState<MarketingSegmentCode>("reactivation_30_120");
    const [sampleLimit, setSampleLimit] = useState(5);
    const [maxRecipients, setMaxRecipients] = useState(200);
    const [audienceLimit, setAudienceLimit] = useState(100);
    const [includeSuppressed, setIncludeSuppressed] = useState(true);
    const [lifecycleReason, setLifecycleReason] = useState("");
    const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
    const [busyAction, setBusyAction] = useState<string | null>(null);
    const [executeModalOpen, setExecuteModalOpen] = useState(false);

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
    }, [selectedCampaignId]);

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
        return <AccessDenied message="Нужна роль owner/admin/platform_admin для управления кампаниями." />;
    }

    const selectedStatus = selectedCampaign ? resolveCampaignStatus(selectedCampaign) : null;
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
    const failureClassRows = diagnostics
        ? Object.entries(diagnostics.failure_classes ?? {}).sort((a, b) => b[1] - a[1])
        : [];
    const canConfirmExecute = Boolean(preflight?.preflight_valid);

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
            await adminApi.createMarketingCampaign({
                branch_id: selectedBranchId,
                name: name.trim(),
                message_text: messageText.trim(),
                segment_code: segmentCode,
                audience_mode: "branch_active_conversations",
            });
            setName("");
            setMessageText("");
            await refetchCampaigns();
            toast.success("Кампания создана.");
        } catch (error) {
            const parsed = parseApiError(error);
            toast.error(parsed.message);
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
            await adminApi.previewMarketingCampaign(selectedCampaign.id, { sample_limit: sampleLimit });
            await Promise.all([refetchCampaigns(), refetchAudience(), refetchPreflight()]);
            toast.success("Preview и audience обновлены.");
        } catch (error) {
            const parsed = parseApiError(error);
            toast.error(parsed.message);
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
            const parsed = parseApiError(error);
            toast.error(parsed.message);
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
            const parsed = parseApiError(error);
            toast.error(parsed.message);
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
            toast.success("Кампания поставлена на паузу.");
        } catch (error) {
            const parsed = parseApiError(error);
            toast.error(parsed.message);
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
            const parsed = parseApiError(error);
            toast.error(parsed.message);
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
            toast.success("Preflight обновлён.");
        } catch (error) {
            const parsed = parseApiError(error);
            toast.error(parsed.message);
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
            const parsed = parseApiError(error);
            toast.error(parsed.message);
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
            const parsed = parseApiError(error);
            toast.error(parsed.message);
        } finally {
            setBusyAction(null);
        }
    };

    return (
        <div className="space-y-6 p-6">
            <div>
                <h1 className="text-2xl font-semibold">Маркетинг</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Полный цикл кампании: аудитория, approval, preflight, execute и retry.
                </p>
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

            <div className="grid gap-6 lg:grid-cols-[360px,1fr]">
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
                            onChange={(event) => setSegmentCode(event.target.value as MarketingSegmentCode)}
                        >
                            {SEGMENT_OPTIONS.map((option) => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
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
                        <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Список</h3>
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
                                                <p className="mt-1 text-xs text-muted-foreground">{segmentLabel(campaign.segment_code)}</p>
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
                                    <div className="text-xs text-muted-foreground">Approval</div>
                                    <div className="mt-1 text-sm font-medium">{formatDateTime(selectedCampaign.approved_at)}</div>
                                </div>
                                <div className="rounded-lg border bg-background p-3">
                                    <div className="text-xs text-muted-foreground">Последний execute</div>
                                    <div className="mt-1 text-sm font-medium">{formatDateTime(selectedCampaign.executed_at)}</div>
                                </div>
                                <div className="rounded-lg border bg-background p-3">
                                    <div className="text-xs text-muted-foreground">Создана</div>
                                    <div className="mt-1 text-sm font-medium">{formatDateTime(selectedCampaign.created_at)}</div>
                                </div>
                            </div>

                            <div className="mt-5 space-y-4 rounded-lg border bg-background p-3">
                                <label className="text-sm">
                                    <div className="mb-1 text-xs text-muted-foreground">Причина (audit)</div>
                                    <input
                                        className="h-10 w-full rounded-lg border border-border bg-card px-3 text-sm"
                                        placeholder="необязательно"
                                        value={lifecycleReason}
                                        onChange={(event) => setLifecycleReason(event.target.value)}
                                    />
                                </label>

                                <div className="flex flex-wrap items-end gap-3">
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
                                        {busyAction === "approve" ? "..." : "Approve"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
                                        onClick={pauseCampaign}
                                        disabled={!canPause || busyAction === "pause"}
                                    >
                                        {busyAction === "pause" ? "..." : "Pause"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
                                        onClick={resumeCampaign}
                                        disabled={!canResume || busyAction === "resume"}
                                    >
                                        {busyAction === "resume" ? "..." : "Resume"}
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
                                        {busyAction === "preflight" ? "..." : "Refresh preflight"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background disabled:cursor-not-allowed disabled:opacity-60"
                                        onClick={() => setExecuteModalOpen(true)}
                                        disabled={busyAction === "execute" || !canExecute}
                                    >
                                        {busyAction === "execute" ? "Execute..." : "Execute modal"}
                                    </button>
                                    <button
                                        type="button"
                                        className="h-10 rounded-lg border border-border bg-card px-4 text-sm font-medium"
                                        onClick={retryFailed}
                                        disabled={busyAction === "retry"}
                                    >
                                        {busyAction === "retry" ? "Retry..." : "Retry failed"}
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
                                        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Статус</div>
                                                <div className={`mt-1 text-sm font-semibold ${preflight.preflight_valid ? "text-emerald-700" : "text-red-700"}`}>
                                                    {preflight.preflight_valid ? "Готово к execute" : "Заблокировано"}
                                                </div>
                                            </div>
                                            <div className="rounded-lg border bg-background p-3">
                                                <div className="text-xs text-muted-foreground">Outbox status</div>
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
                                            <div className="text-xs text-muted-foreground">Template gate</div>
                                            <div className="mt-1 text-sm font-medium">
                                                {preflight.template_gate_enabled
                                                    ? (preflight.template_ok ? "OK" : `blocked (${preflight.template_state ?? "unknown"})`)
                                                    : "disabled"}
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
                                        Reload audience
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
                                                    <th className="px-3 py-2 font-medium">Recipient</th>
                                                    <th className="px-3 py-2 font-medium">Context</th>
                                                    <th className="px-3 py-2 font-medium">Reasons</th>
                                                    <th className="px-3 py-2 font-medium">Suppression</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {audienceRows.map((row) => (
                                                    <tr key={row.id} className="border-t border-border/60 align-top">
                                                        <td className="px-3 py-2">
                                                            <div className="font-medium text-foreground">{row.recipient_jid}</div>
                                                            <div className="mt-1 text-muted-foreground">{segmentLabel(row.segment_code)}</div>
                                                        </td>
                                                        <td className="px-3 py-2 text-muted-foreground">
                                                            <div>conv: {row.conversation_id ?? "-"}</div>
                                                            <div className="mt-1">user: {row.user_id ?? "-"}</div>
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            <div className="flex flex-wrap gap-1">
                                                                {row.reason_codes.length ? (
                                                                    row.reason_codes.map((reason) => (
                                                                        <span key={reason} className="rounded-full bg-sky-100 px-2 py-0.5 text-[11px] text-sky-700">
                                                                            {formatReason(reason)}
                                                                        </span>
                                                                    ))
                                                                ) : (
                                                                    <span className="text-muted-foreground">-</span>
                                                                )}
                                                            </div>
                                                        </td>
                                                        <td className="px-3 py-2">
                                                            {row.suppressed ? (
                                                                <div className="flex flex-wrap gap-1">
                                                                    {row.suppression_reasons.map((reason) => (
                                                                        <span key={reason} className="rounded-full bg-red-100 px-2 py-0.5 text-[11px] text-red-700">
                                                                            {formatReason(reason)}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                            ) : (
                                                                <span className="text-emerald-700">eligible</span>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <p className="mt-2 text-sm text-muted-foreground">Audience пустой. Сначала запустите preview.</p>
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
                            <h3 className="text-lg font-semibold">Execute Campaign</h3>
                            <button
                                type="button"
                                className="h-8 rounded border border-border px-2 text-xs"
                                onClick={() => setExecuteModalOpen(false)}
                            >
                                Закрыть
                            </button>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">
                            {selectedCampaign.name}
                        </p>
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
                                <div className="text-xs text-muted-foreground">Outbox risk</div>
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
                                {busyAction === "execute" ? "Execute..." : "Confirm Execute"}
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
}
