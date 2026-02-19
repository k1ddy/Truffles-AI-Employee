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
} from "@/lib/api-client";
import { useConsoleContextScope } from "@/lib/use-console-context-scope";

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

function campaignStatusLabel(status: MarketingCampaign["status"]): string {
    if (status === "draft") {
        return "Черновик";
    }
    if (status === "ready") {
        return "Готова";
    }
    if (status === "executed") {
        return "Отправлена";
    }
    return "Пауза";
}

function campaignStatusClass(status: MarketingCampaign["status"]): string {
    if (status === "executed") {
        return "bg-emerald-100 text-emerald-700";
    }
    if (status === "ready") {
        return "bg-sky-100 text-sky-700";
    }
    if (status === "paused") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-muted text-muted-foreground";
}

export default function MarketingPage() {
    const { data: session } = useSession();
    const [name, setName] = useState("");
    const [messageText, setMessageText] = useState("");
    const [sampleLimit, setSampleLimit] = useState(5);
    const [maxRecipients, setMaxRecipients] = useState(200);
    const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
    const [busyAction, setBusyAction] = useState<string | null>(null);

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
        if (!branchOptions.length) {
            return;
        }
        if (scope.branchId) {
            return;
        }
        if (!selectedBranchId) {
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

    const {
        data: diagnosticsData,
        isLoading: diagnosticsLoading,
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

    if (meLoading) {
        return <div className="p-6 text-sm text-muted-foreground">Загрузка...</div>;
    }

    if (!canReadMarketing) {
        return (
            <AccessDenied
                message="Нужна роль owner/admin/platform_admin для управления кампаниями."
            />
        );
    }

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
            await Promise.all([refetchCampaigns(), refetchDiagnostics()]);
            toast.success("Preview обновлён.");
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
        const confirmed = window.confirm("Запустить отправку этой кампании?");
        if (!confirmed) {
            return;
        }
        setBusyAction("execute");
        try {
            const response = await adminApi.executeMarketingCampaign(selectedCampaign.id, {
                confirm_send: true,
                max_recipients: maxRecipients,
            });
            await Promise.all([refetchCampaigns(), refetchDiagnostics()]);
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
            toast.success(`Повторено: ${response.data.retried_count}`);
        } catch (error) {
            const parsed = parseApiError(error);
            toast.error(parsed.message);
        } finally {
            setBusyAction(null);
        }
    };

    const diagnostics: MarketingCampaignDiagnosticsResponse | null = diagnosticsData ?? null;

    return (
        <div className="space-y-6 p-6">
            <div>
                <h1 className="text-2xl font-semibold">Маркетинг</h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Кампании branch-scope: preview, confirm execute, diagnostics и retry failed.
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

            <div className="grid gap-6 lg:grid-cols-[340px,1fr]">
                <section className="rounded-xl border bg-card p-4">
                    <h2 className="text-lg font-semibold">Новая кампания</h2>
                    <div className="mt-3 space-y-3">
                        <input
                            className="h-10 w-full rounded-lg border border-border bg-background px-3 text-sm"
                            placeholder="Название"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                        />
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
                        ) : campaigns.length ? (
                            <ul className="mt-3 space-y-2">
                                {campaigns.map((campaign) => {
                                    const active = campaign.id === selectedCampaignId;
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
                                                    <span className={`rounded-full px-2 py-0.5 text-xs ${campaignStatusClass(campaign.status)}`}>
                                                        {campaignStatusLabel(campaign.status)}
                                                    </span>
                                                </div>
                                                <p className="mt-1 text-xs text-muted-foreground">
                                                    preview: {campaign.preview_total}
                                                </p>
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
                                    <p className="mt-1 text-sm text-muted-foreground">
                                        {selectedCampaign.message_text}
                                    </p>
                                </div>
                                <span className={`rounded-full px-3 py-1 text-xs ${campaignStatusClass(selectedCampaign.status)}`}>
                                    {campaignStatusLabel(selectedCampaign.status)}
                                </span>
                            </div>

                            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                                <div className="rounded-lg border bg-background p-3">
                                    <div className="text-xs text-muted-foreground">Preview</div>
                                    <div className="mt-1 text-lg font-semibold">{selectedCampaign.preview_total}</div>
                                </div>
                                <div className="rounded-lg border bg-background p-3">
                                    <div className="text-xs text-muted-foreground">Последний preview</div>
                                    <div className="mt-1 text-sm font-medium">{formatDateTime(selectedCampaign.last_preview_at)}</div>
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

                            <div className="mt-5 flex flex-wrap items-end gap-3">
                                <label className="text-sm">
                                    <div className="mb-1 text-xs text-muted-foreground">sample_limit</div>
                                    <input
                                        type="number"
                                        min={1}
                                        max={20}
                                        className="h-10 w-28 rounded-lg border border-border bg-background px-3 text-sm"
                                        value={sampleLimit}
                                        onChange={(event) => setSampleLimit(Number(event.target.value || 5))}
                                    />
                                </label>
                                <label className="text-sm">
                                    <div className="mb-1 text-xs text-muted-foreground">max_recipients</div>
                                    <input
                                        type="number"
                                        min={1}
                                        max={500}
                                        className="h-10 w-32 rounded-lg border border-border bg-background px-3 text-sm"
                                        value={maxRecipients}
                                        onChange={(event) => setMaxRecipients(Number(event.target.value || 200))}
                                    />
                                </label>
                                <button
                                    type="button"
                                    className="h-10 rounded-lg border border-border bg-background px-4 text-sm font-medium"
                                    onClick={previewCampaign}
                                    disabled={busyAction === "preview"}
                                >
                                    {busyAction === "preview" ? "Preview..." : "Preview"}
                                </button>
                                <button
                                    type="button"
                                    className="h-10 rounded-lg bg-foreground px-4 text-sm font-medium text-background disabled:cursor-not-allowed disabled:opacity-60"
                                    onClick={executeCampaign}
                                    disabled={busyAction === "execute"}
                                >
                                    {busyAction === "execute" ? "Execute..." : "Confirm & Execute"}
                                </button>
                                <button
                                    type="button"
                                    className="h-10 rounded-lg border border-border bg-background px-4 text-sm font-medium"
                                    onClick={retryFailed}
                                    disabled={busyAction === "retry"}
                                >
                                    {busyAction === "retry" ? "Retry..." : "Retry Failed"}
                                </button>
                            </div>

                            <div className="mt-6 border-t pt-4">
                                <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-muted-foreground">Diagnostics</h3>
                                {diagnosticsLoading ? (
                                    <p className="mt-2 text-sm text-muted-foreground">Загрузка...</p>
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
        </div>
    );
}
