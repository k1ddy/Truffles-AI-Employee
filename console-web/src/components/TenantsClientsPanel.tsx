"use client";

import type { components } from "@/types/api.generated";

type FleetLifecycleFilter = "all" | "lead" | "contracting" | "onboarding" | "go_live_ready" | "active" | "paused" | "archived";
type FleetPaymentFilter = "all" | "pending" | "confirmed" | "rejected" | "unknown";
type FleetServiceFilter = "all" | "ok" | "degraded" | "attention";
type ClientLifecycleMode = "archive" | "restore";
type ClientLifecycleAuditFilter = "all" | "success" | "error";

type ClientEditorState = {
    id: string;
    slug: string;
    companyId: string;
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
    source: "session" | "api";
    sourceEventId?: string;
};

type ClientsSummary = {
    total_clients?: number | null;
    active_clients?: number | null;
    onboarding_clients?: number | null;
    paused_clients?: number | null;
    archived_clients?: number | null;
    degraded_clients?: number | null;
} | null;

type TenantsClientsPanelProps = {
    decommissionFocused: boolean;
    clientsLoading: boolean;
    clientsErrored: boolean;
    clients: components["schemas"]["ConsoleClient"][];
    clientsSummary: ClientsSummary;
    pageFilterCompanyId: string | null;

    clientQuery: string;
    onClientQueryChange: (value: string) => void;
    fleetLifecycleFilter: FleetLifecycleFilter;
    onFleetLifecycleFilterChange: (value: FleetLifecycleFilter) => void;
    fleetPaymentFilter: FleetPaymentFilter;
    onFleetPaymentFilterChange: (value: FleetPaymentFilter) => void;
    fleetServiceFilter: FleetServiceFilter;
    onFleetServiceFilterChange: (value: FleetServiceFilter) => void;

    isPlatformPreset: boolean;
    canWriteTenants: boolean;
    selectedClientId: string | null;
    pageFilterClientId: string | null;

    clientEditor: ClientEditorState | null;
    savingClient: boolean;
    knownCompanies: components["schemas"]["ConsoleCompany"][];

    clientLifecyclePendingId: string | null;
    clientLifecycleAuditFilterById: Record<string, ClientLifecycleAuditFilter>;
    clientLifecycleAuditById: Record<string, ClientLifecycleAuditEntry[]>;
    selectedClientApiAuditEntries: ClientLifecycleAuditEntry[];
    selectedClientAuditIsFetching: boolean;
    onRefreshSelectedClientAudit: () => void;
    onSetClientLifecycleAuditFilter: (clientId: string, filter: ClientLifecycleAuditFilter) => void;

    mergeLifecycleAuditEntries: (
        sessionEntries: ClientLifecycleAuditEntry[],
        apiEntries: ClientLifecycleAuditEntry[],
    ) => ClientLifecycleAuditEntry[];

    formatLifecycleLabel: (value?: string | null) => string;
    formatPaymentLabel: (value?: string | null) => string;
    formatServiceLabel: (value?: string | null) => string;
    formatReferenceScopeReason: (value?: string | null) => string;
    formatDateTimeLabel: (value: string | undefined) => string;
    isClientArchived: (client: components["schemas"]["ConsoleClient"]) => boolean;

    onStartClientEdit: (client: components["schemas"]["ConsoleClient"]) => void;
    onOpenClientLifecycleAction: (
        client: components["schemas"]["ConsoleClient"],
        mode: ClientLifecycleMode,
    ) => void;
    onSetClientContext: (clientId: string, companyId?: string | null) => void;

    onClientEditorSlugChange: (value: string) => void;
    onClientEditorCompanyChange: (value: string) => void;
    onSaveClientEdit: () => void;
    onCancelClientEdit: () => void;

    clientsUsingServerContract: boolean;
    clientsHasNextPage: boolean;
    clientsFetchingNextPage: boolean;
    onFetchNextClientsPage: () => void;
};

export default function TenantsClientsPanel({
    decommissionFocused,
    clientsLoading,
    clientsErrored,
    clients,
    clientsSummary,
    pageFilterCompanyId,
    clientQuery,
    onClientQueryChange,
    fleetLifecycleFilter,
    onFleetLifecycleFilterChange,
    fleetPaymentFilter,
    onFleetPaymentFilterChange,
    fleetServiceFilter,
    onFleetServiceFilterChange,
    isPlatformPreset,
    canWriteTenants,
    selectedClientId,
    pageFilterClientId,
    clientEditor,
    savingClient,
    knownCompanies,
    clientLifecyclePendingId,
    clientLifecycleAuditFilterById,
    clientLifecycleAuditById,
    selectedClientApiAuditEntries,
    selectedClientAuditIsFetching,
    onRefreshSelectedClientAudit,
    onSetClientLifecycleAuditFilter,
    mergeLifecycleAuditEntries,
    formatLifecycleLabel,
    formatPaymentLabel,
    formatServiceLabel,
    formatReferenceScopeReason,
    formatDateTimeLabel,
    isClientArchived,
    onStartClientEdit,
    onOpenClientLifecycleAction,
    onSetClientContext,
    onClientEditorSlugChange,
    onClientEditorCompanyChange,
    onSaveClientEdit,
    onCancelClientEdit,
    clientsUsingServerContract,
    clientsHasNextPage,
    clientsFetchingNextPage,
    onFetchNextClientsPage,
}: TenantsClientsPanelProps) {
    return (
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
                        onChange={(event) => onClientQueryChange(event.target.value)}
                    />
                    <select
                        className="rounded-lg border border-border bg-background px-3 py-2 text-xs"
                        value={fleetLifecycleFilter}
                        onChange={(event) => onFleetLifecycleFilterChange(event.target.value as FleetLifecycleFilter)}
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
                        onChange={(event) => onFleetPaymentFilterChange(event.target.value as FleetPaymentFilter)}
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
                        onChange={(event) => onFleetServiceFilterChange(event.target.value as FleetServiceFilter)}
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
                                        жизненный цикл: {formatLifecycleLabel(client.lifecycle_state)} · оплата: {formatPaymentLabel(client.payment_status)} · сервис: {formatServiceLabel(client.service_state)}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        владелец: {client.owner_name ?? "—"} · следующее действие: {client.next_action ?? "—"}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        филиалы: активные {client.active_branches ?? 0}/{client.total_branches ?? 0} · деградация {client.degraded_branches ?? 0} · готовы к запуску {client.go_live_ready_branches ?? 0}
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        опорные филиалы: {client.reference_branch_ids?.length ?? 0} · {formatReferenceScopeReason(client.reference_branch_reason)}
                                    </div>
                                    {lifecycleAuditHistory.length > 0 || clientIdKey === pageFilterClientId ? (
                                        <div className="mt-2 rounded-lg border border-border/60 bg-background px-3 py-2 text-xs" data-testid="tenants-client-lifecycle-audit">
                                            <div className="flex flex-wrap items-center justify-between gap-2">
                                                <div className="font-medium">
                                                    История статуса
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <button
                                                        className={lifecycleAuditFilter === "all" ? "btn-primary" : "btn-ghost"}
                                                        onClick={() => {
                                                            if (!clientIdKey) {
                                                                return;
                                                            }
                                                            onSetClientLifecycleAuditFilter(clientIdKey, "all");
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
                                                            onSetClientLifecycleAuditFilter(clientIdKey, "success");
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
                                                            onSetClientLifecycleAuditFilter(clientIdKey, "error");
                                                        }}
                                                    >
                                                        ошибка
                                                    </button>
                                                    {clientIdKey === pageFilterClientId ? (
                                                        <button
                                                            className="btn-ghost"
                                                            onClick={onRefreshSelectedClientAudit}
                                                            disabled={selectedClientAuditIsFetching}
                                                            data-testid="tenants-client-lifecycle-audit-refresh"
                                                        >
                                                            {selectedClientAuditIsFetching ? "Обновление..." : "Обновить историю"}
                                                        </button>
                                                    ) : null}
                                                </div>
                                            </div>
                                            <div className="mt-1 text-muted-foreground">
                                                источник: текущая сессия + журнал изменений
                                                {clientIdKey === pageFilterClientId ? "" : " (журнал доступен при выбранном клиенте в фильтрах страницы)"}
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
                                                                {entry.status === "success" ? "Успех" : "Ошибка"}: {entry.message}
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
                                            onClick={() => onStartClientEdit(client)}
                                            data-testid="tenants-client-edit"
                                            disabled={lifecyclePending}
                                        >
                                            Редактировать
                                        </button>
                                    ) : null}
                                    {canWriteTenants ? (
                                        <button
                                            className="btn-ghost"
                                            onClick={() => onOpenClientLifecycleAction(client, lifecycleMode)}
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
                                        onClick={() => onSetClientContext(client.id, client.company_id)}
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
                                                    onChange={(event) => onClientEditorSlugChange(event.target.value)}
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
                                                    onChange={(event) => onClientEditorCompanyChange(event.target.value)}
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
                                                    onClick={onSaveClientEdit}
                                                    disabled={!canWriteTenants || savingClient || lifecyclePending}
                                                >
                                                    {savingClient ? "Сохранение..." : "Сохранить"}
                                                </button>
                                                <button
                                                    className="btn-ghost"
                                                    onClick={onCancelClientEdit}
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
            {!clientsUsingServerContract && clientsHasNextPage ? (
                <div className="flex justify-center pt-3">
                    <button
                        className="btn-ghost"
                        onClick={onFetchNextClientsPage}
                        disabled={clientsFetchingNextPage}
                    >
                        {clientsFetchingNextPage ? "Загрузка..." : "Показать еще"}
                    </button>
                </div>
            ) : null}
        </section>
    );
}
