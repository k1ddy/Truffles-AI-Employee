"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";

import AccessDenied from "@/components/AccessDenied";
import {
    adminApi,
    authApi,
    canAccessConsole,
    confirmationsApi,
    type BranchIntegrationStatus,
} from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";

function statusBadgeClass(status: string): string {
    if (status === "error") {
        return "bg-red-100 text-red-800";
    }
    if (status === "warn") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-green-100 text-green-800";
}

function statusLabel(status: string): string {
    const labels: Record<string, string> = {
        ok: "OK",
        warn: "Warning",
        error: "Error",
        inactive: "Inactive",
        missing_instance_id: "Missing instance_id",
        instance_id_mismatch: "Instance mismatch",
        invalid_webhook_url: "Invalid webhook URL",
        invalid_webhook_secret: "Invalid webhook secret",
        webhook_secret_drift: "Webhook secret drift",
        no_recent_inbound: "No recent inbound",
        inbound_without_outbound: "Inbound without outbound",
        missing_bot_token: "Missing bot token",
        missing_chat_id: "Missing chat id",
    };
    return labels[status] ?? status;
}

function paymentStatusLabel(status?: string | null): string {
    if (status === "confirmed") {
        return "Confirmed";
    }
    if (status === "rejected") {
        return "Rejected";
    }
    if (status === "pending") {
        return "Pending";
    }
    return "Unknown";
}

function providerBindingExpiryLabel(status?: string | null): string {
    if (status === "ok") {
        return "OK";
    }
    if (status === "expiring_soon") {
        return "Expiring soon";
    }
    if (status === "expired") {
        return "Expired";
    }
    return "Unknown";
}

function providerBindingExpiryBadgeClass(status?: string | null): string {
    if (status === "expired") {
        return "bg-red-100 text-red-800";
    }
    if (status === "expiring_soon") {
        return "bg-amber-100 text-amber-800";
    }
    if (status === "ok") {
        return "bg-green-100 text-green-800";
    }
    return "bg-muted text-muted-foreground";
}

function formatTimestamp(value?: string | null): string {
    if (!value) {
        return "—";
    }
    return new Date(value).toLocaleString("ru-RU");
}

function DriftIssues({ item }: { item: BranchIntegrationStatus }) {
    if (!item.drift_issues || item.drift_issues.length === 0) {
        return <span className="text-muted-foreground">—</span>;
    }
    return (
        <div className="flex flex-wrap gap-1">
            {item.drift_issues.map((issue) => (
                <span
                    key={`${item.branch_id}-${issue}`}
                    className="rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-800"
                >
                    {statusLabel(issue)}
                </span>
            ))}
        </div>
    );
}

export default function IntegrationsPage() {
    const { data: session } = useSession();
    const { handleError } = useErrorHandler();
    const [staleAfterMinutes, setStaleAfterMinutes] = useState(60);
    const [runningAction, setRunningAction] = useState<{ branchId: string; mode: "dry_run" | "execute" } | null>(null);
    const [actionSummaryByBranch, setActionSummaryByBranch] = useState<Record<string, string>>({});

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadIntegrations = canAccessConsole(role, "integrations", "read");

    const {
        data,
        isLoading,
        error,
        refetch,
    } = useQuery({
        queryKey: ["integrations-registry", staleAfterMinutes],
        queryFn: async () => {
            const response = await adminApi.listIntegrations({
                stale_after_minutes: staleAfterMinutes,
            });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
        refetchInterval: 60000,
    });

    useEffect(() => {
        if (error) {
            handleError(error);
        }
    }, [error, handleError]);

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Войдите в систему для просмотра интеграций.
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

    if (!canReadIntegrations) {
        return <AccessDenied message="Эта роль не имеет доступа к интеграциям." />;
    }

    if (isLoading) {
        return (
            <div className="max-w-6xl mx-auto p-6" data-testid="integrations-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="integrations-title">Интеграции</h1>
                <div className="animate-pulse space-y-3">
                    {[...Array(8)].map((_, index) => (
                        <div key={index} className="h-12 bg-muted/70 rounded" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="max-w-6xl mx-auto p-6" data-testid="integrations-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="integrations-title">Интеграции</h1>
                <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center" data-testid="integrations-error">
                    <p className="text-destructive mb-4">Не удалось загрузить интеграции</p>
                    <button
                        onClick={() => refetch()}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="integrations-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    const items = data?.items ?? [];

    const createReconcileConfirmation = async (branchId: string, reason: string): Promise<string> => {
        const confirmation = await confirmationsApi.create({
            action: "integration_reconcile",
            target_type: "branch",
            target_id: branchId,
            reason,
        });
        return confirmation.data.confirmation_id;
    };

    const runBranchReconcile = async (branchId: string, mode: "dry_run" | "execute") => {
        setRunningAction({ branchId, mode });
        try {
            const runAction = async (confirmationId?: string) =>
                adminApi.reconcileIntegrationBranch(branchId, {
                    mode,
                    confirmation_id: confirmationId,
                });

            let response;
            try {
                response = await runAction();
            } catch (error: unknown) {
                const apiCode = (error as { response?: { data?: { error?: { code?: string } } } })
                    ?.response?.data?.error?.code;
                if (mode !== "execute" || apiCode !== "CONFIRMATION_REQUIRED") {
                    throw error;
                }
                const reason = window.prompt(
                    "Укажите причину execute integration_reconcile",
                    "manual integration reconcile from platform admin cockpit",
                );
                if (!reason || !reason.trim()) {
                    toast.error("Укажите причину для execute");
                    return;
                }
                const confirmationId = await createReconcileConfirmation(branchId, reason.trim());
                response = await runAction(confirmationId);
            }

            const result = response.data.result || {};
            const summary = `checked ${result.checked ?? 0} · degraded ${result.degraded ?? 0} · recovered ${result.recovered ?? 0} · remediated ${result.remediated ?? 0}`;
            setActionSummaryByBranch((prev) => ({ ...prev, [branchId]: summary }));
            toast.success(mode === "dry_run" ? "Dry-run выполнен" : "Execute выполнен");
            await refetch();
        } catch (error) {
            handleError(error);
        } finally {
            setRunningAction(null);
        }
    };

    return (
        <div className="max-w-6xl mx-auto p-6" data-testid="integrations-page">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
                <div>
                    <h1 className="text-2xl font-bold" data-testid="integrations-title">Интеграции</h1>
                    <p className="text-sm text-muted-foreground mt-1">
                        WhatsApp/Telegram статус, provider binding lifecycle и drift-сигналы по филиалам.
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <label className="text-sm text-muted-foreground" htmlFor="stale-after-select">
                        Stale threshold
                    </label>
                    <select
                        id="stale-after-select"
                        className="rounded border border-border/70 bg-background px-3 py-2 text-sm"
                        value={staleAfterMinutes}
                        onChange={(event) => setStaleAfterMinutes(Number(event.target.value))}
                        data-testid="integrations-stale-select"
                    >
                        <option value={15}>15 min</option>
                        <option value={30}>30 min</option>
                        <option value={60}>60 min</option>
                        <option value={180}>180 min</option>
                    </select>
                    <Link href="/" className="text-primary hover:text-primary/80">
                        ← Назад к заявкам
                    </Link>
                </div>
            </div>

            <div className="mb-3 text-xs text-muted-foreground" data-testid="integrations-threshold-info">
                stale_after_minutes: {data?.stale_after_minutes ?? staleAfterMinutes}
            </div>

            <div className="bg-card border border-border/60 rounded-lg overflow-hidden" data-testid="integrations-table">
                <table className="w-full text-left">
                    <thead className="bg-muted">
                        <tr>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Клиент</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Филиал</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">WhatsApp</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Telegram</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Provider binding</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Оплата/срок</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Последний inbound</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Drift issues</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Итог</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.map((item) => (
                            <tr
                                key={item.branch_id}
                                className="border-t border-border/60 hover:bg-muted/50"
                                data-testid="integrations-row"
                            >
                                <td className="p-4">
                                    <div className="font-medium">{item.client_slug}</div>
                                    <div className="text-xs text-muted-foreground">{item.client_id}</div>
                                </td>
                                <td className="p-4">
                                    <div className="font-medium">{item.branch_name}</div>
                                    <div className="text-xs text-muted-foreground">{item.branch_slug}</div>
                                    {!item.is_active && (
                                        <div className="text-xs text-muted-foreground">archived</div>
                                    )}
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{statusLabel(item.whatsapp_status)}</div>
                                    <div className="text-xs text-muted-foreground">
                                        instance: {item.instance_id ?? "—"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{statusLabel(item.telegram_status)}</div>
                                    <div className="text-xs text-muted-foreground">
                                        chat: {item.telegram_chat_id ?? "—"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{item.provider_binding_provider ?? "—"}</div>
                                    <div className="text-xs text-muted-foreground">
                                        binding instance: {item.provider_binding_instance_id ?? "—"}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        webhook: {item.provider_binding_webhook_status ?? "—"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{paymentStatusLabel(item.provider_binding_payment_status)}</div>
                                    <div className="text-xs text-muted-foreground">
                                        paid_until: {item.provider_binding_paid_until ?? "—"}
                                    </div>
                                    <div className="mt-1">
                                        <span
                                            className={`rounded px-2 py-0.5 text-[11px] font-medium ${providerBindingExpiryBadgeClass(item.provider_binding_expiry_status)}`}
                                        >
                                            {providerBindingExpiryLabel(item.provider_binding_expiry_status)}
                                        </span>
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">
                                        days left: {item.provider_binding_days_until_expiry ?? "—"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <div>{formatTimestamp(item.last_inbound_at)}</div>
                                    <div className="text-xs text-muted-foreground">
                                        instance: {item.last_inbound_instance_id ?? "—"}
                                    </div>
                                </td>
                                <td className="p-4 text-sm">
                                    <DriftIssues item={item} />
                                </td>
                                <td className="p-4">
                                    <span className={`rounded px-2 py-1 text-xs font-medium ${statusBadgeClass(item.status)}`}>
                                        {statusLabel(item.status)}
                                    </span>
                                </td>
                                <td className="p-4 text-sm">
                                    <div className="flex flex-wrap gap-2">
                                        <button
                                            type="button"
                                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                            onClick={() => runBranchReconcile(String(item.branch_id), "dry_run")}
                                            disabled={!item.is_active || !!runningAction}
                                        >
                                            {runningAction?.branchId === String(item.branch_id) && runningAction?.mode === "dry_run" ? "Dry-run..." : "Dry-run"}
                                        </button>
                                        <button
                                            type="button"
                                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                            onClick={() => runBranchReconcile(String(item.branch_id), "execute")}
                                            disabled={!item.is_active || !!runningAction}
                                        >
                                            {runningAction?.branchId === String(item.branch_id) && runningAction?.mode === "execute" ? "Execute..." : "Execute"}
                                        </button>
                                    </div>
                                    <div className="mt-1 text-xs text-muted-foreground">
                                        {actionSummaryByBranch[String(item.branch_id)] ?? "—"}
                                    </div>
                                </td>
                            </tr>
                        ))}
                        {items.length === 0 && (
                            <tr>
                                <td colSpan={10} className="p-8 text-center text-muted-foreground" data-testid="integrations-empty">
                                    Филиалы в доступном fleet не найдены.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
