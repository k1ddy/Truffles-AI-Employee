"use client";

import type { components } from "@/types/api.generated";

type FleetAttentionLevel = "high" | "medium" | "low";

type TenantsFleetAttentionPanelProps = {
    fleetAttention: components["schemas"]["ConsoleFleetAttentionResponse"] | null;
    loading: boolean;
    errored: boolean;
    refreshing: boolean;
    onRefresh: () => void;
    attentionLevelClass: (level: FleetAttentionLevel) => string;
    formatLifecycleLabel: (value?: string | null) => string;
    formatServiceLabel: (value?: string | null) => string;
    formatReferenceScopeReason: (value?: string | null) => string;
    onSetClientContext: (clientId: string, companyId?: string | null) => void;
    onOpenIntegrations: (clientId: string, companyId?: string | null) => void;
    onOpenCases: (clientId: string, companyId?: string | null) => void;
};

export default function TenantsFleetAttentionPanel({
    fleetAttention,
    loading,
    errored,
    refreshing,
    onRefresh,
    attentionLevelClass,
    formatLifecycleLabel,
    formatServiceLabel,
    formatReferenceScopeReason,
    onSetClientContext,
    onOpenIntegrations,
    onOpenCases,
}: TenantsFleetAttentionPanelProps) {
    return (
        <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-fleet-attention">
            <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                    <h2 className="text-lg font-semibold">Риски и внимание</h2>
                    <p className="text-sm text-muted-foreground">
                        Приоритетные риски по активным клиентам.
                    </p>
                    <p className="text-xs text-muted-foreground">
                        Оценка строится по рабочим филиалам и текущим операционным сигналам.
                    </p>
                </div>
                <button
                    className="btn-ghost"
                    onClick={onRefresh}
                    disabled={refreshing}
                >
                    {refreshing ? "Обновление..." : "Обновить"}
                </button>
            </div>

            {fleetAttention ? (
                <div className="mb-3 text-xs text-muted-foreground" data-testid="tenants-fleet-attention-summary">
                    активных клиентов {fleetAttention.summary.active_clients_total} · с риском {fleetAttention.summary.clients_with_attention} ·
                    высокий {fleetAttention.summary.high_risk_clients} · средний {fleetAttention.summary.medium_risk_clients} ·
                    ошибок отправки за 24ч {fleetAttention.summary.outbox_failed_24h_total} · ожидают передачи {fleetAttention.summary.pending_handovers_total}
                </div>
            ) : null}

            <div className="space-y-3">
                {loading ? (
                    <div className="text-sm text-muted-foreground">Загрузка панели рисков...</div>
                ) : errored ? (
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
                                жизненный цикл {formatLifecycleLabel(item.lifecycle_state)} · сервис {formatServiceLabel(item.service_state)} · владелец {item.owner_name ?? "—"} · следующее действие {item.next_action}
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">
                                филиалы активные {item.active_branches}/{item.total_branches} · неактуальные {item.stale_branches} · интеграционных ошибок {item.integration_error_branches} · ошибок отправки за 24ч {item.outbox_failed_24h} · ожидают передачи {item.pending_handovers}
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">
                                опорные филиалы: {item.reference_branch_ids?.length ?? 0} · {formatReferenceScopeReason(item.reference_branch_reason)}
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
                                    onClick={() => onSetClientContext(item.client_id, item.company_id)}
                                >
                                    В контекст
                                </button>
                                <button
                                    className="btn-ghost"
                                    onClick={() => onOpenIntegrations(item.client_id, item.company_id)}
                                >
                                    Интеграции
                                </button>
                                <button
                                    className="btn-ghost"
                                    onClick={() => onOpenCases(item.client_id, item.company_id)}
                                >
                                    Заявки
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </section>
    );
}
