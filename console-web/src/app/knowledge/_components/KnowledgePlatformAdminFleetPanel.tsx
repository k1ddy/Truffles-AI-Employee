"use client";

import type { useKnowledgeStudioState } from "../_hooks/useKnowledgeStudioState";

type KnowledgePlatformAdminFleetState = ReturnType<typeof useKnowledgeStudioState>["platformAdminFleet"];

type KnowledgePlatformAdminFleetPanelProps = {
    state: KnowledgePlatformAdminFleetState;
};

export default function KnowledgePlatformAdminFleetPanel({
    state,
}: KnowledgePlatformAdminFleetPanelProps) {
    if (!state.visible) {
        return null;
    }

    return (
        <div className="card-surface p-5" data-testid="knowledge-fleet-control">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold">Управление знаниями по сети клиентов</h2>
                    <p className="text-sm text-muted-foreground">
                        Быстрый выбор клиента и филиала для управления знаниями по всей платформе.
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={state.onToggleAttention}
                        disabled={state.isApplyingContext}
                    >
                        {state.attentionEnabled ? "Скрыть сигналы" : "Показать сигналы"}
                    </button>
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={state.onRefresh}
                        disabled={state.isBusy}
                    >
                        {state.isBusy ? "Обновление..." : "Обновить"}
                    </button>
                </div>
            </div>

            <div className="mt-4 grid gap-3 lg:grid-cols-3">
                <label className="text-xs text-muted-foreground">
                    Клиент
                    <select
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={state.clientId}
                        onChange={(event) => state.onClientChange(event.target.value)}
                    >
                        <option value="">Выберите клиента</option>
                        {state.clients.map((client) => (
                            <option key={client.id} value={client.id ?? ""}>
                                {client.name ?? client.slug ?? client.id}
                            </option>
                        ))}
                    </select>
                </label>
                <label className="text-xs text-muted-foreground">
                    Филиал
                    <select
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={state.branchId}
                        onChange={(event) => state.onBranchChange(event.target.value)}
                        disabled={!state.clientId || state.isBranchesLoading}
                    >
                        <option value="">Выберите филиал</option>
                        {state.branches.map((branch) => (
                            <option key={branch.id} value={branch.id ?? ""}>
                                {`${branch.name ?? branch.slug ?? branch.id} · ${branch.slug ?? String(branch.id).slice(0, 8)}`}
                            </option>
                        ))}
                    </select>
                </label>
                <div className="flex flex-wrap items-end gap-2">
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={state.onApplyContext}
                        disabled={!state.clientId || !state.branchId || state.isApplyingContext}
                    >
                        {state.isApplyingContext ? "Применение..." : "Применить контекст"}
                    </button>
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={state.onOpenIntegrations}
                        disabled={!state.clientId || state.isApplyingContext}
                    >
                        Интеграции
                    </button>
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={state.onOpenInbox}
                        disabled={!state.clientId || state.isApplyingContext}
                    >
                        Заявки
                    </button>
                </div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
                Контекст филиала применяется автоматически после выбора в поле `Филиал`.
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
                Переходы в `Интеграции` и `Заявки` сохраняют контекст филиала, если выбран филиал клиента.
            </div>
            {!state.attentionEnabled && (
                <div className="mt-4 text-xs text-muted-foreground">
                    Сигналы по сети клиентов отключены по умолчанию: включайте при необходимости оперативного контроля рисков и SLA.
                </div>
            )}

            {state.attentionEnabled && (
                <div className="mt-4 space-y-2">
                    {state.isAttentionLoading && (
                        <div className="rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground">
                            Загрузка сигналов по сети клиентов...
                        </div>
                    )}

                    {state.attentionError && (
                        <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700">
                            {state.attentionError}
                            <button
                                type="button"
                                className="btn-ghost ml-2"
                                onClick={state.onRefresh}
                            >
                                Повторить
                            </button>
                        </div>
                    )}

                    {!state.attentionError && state.attentionSummary && (
                        <div className="text-xs text-muted-foreground">
                            активных клиентов {state.attentionSummary.active_clients_total} · с риском {state.attentionSummary.clients_with_attention} ·
                            высокий {state.attentionSummary.high_risk_clients} · средний {state.attentionSummary.medium_risk_clients}
                        </div>
                    )}

                    {!state.attentionError && state.attentionItems.length > 0 && (
                        <div className="space-y-2">
                            {state.attentionItems.slice(0, 5).map((item) => (
                                <div
                                    key={item.client_id}
                                    className="rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground"
                                >
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <span className="font-medium text-foreground">
                                            {item.client_name ?? item.client_slug}
                                        </span>
                                        <span>уровень риска: {item.attention_level} · оценка: {item.attention_score}</span>
                                    </div>
                                    <div className="mt-1">
                                        состояние сервиса: {item.service_state} · устаревшие филиалы: {item.stale_branches} · ошибки отправки за 24ч: {item.outbox_failed_24h}
                                    </div>
                                    <div className="mt-2 flex flex-wrap items-center gap-2">
                                        <button
                                            type="button"
                                            className="btn-ghost"
                                            onClick={() => state.onAttentionSelectClient(item)}
                                            disabled={state.isBusy}
                                        >
                                            В контекст клиента
                                        </button>
                                        <button
                                            type="button"
                                            className="btn-ghost"
                                            onClick={() => state.onAttentionOpenIntegrations(item)}
                                            disabled={state.isBusy}
                                        >
                                            Интеграции
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {!state.attentionError && !state.isAttentionLoading && state.attentionItems.length === 0 && (
                        <div className="rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground">
                            Активных проблем в сигналах по сети клиентов не найдено.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
