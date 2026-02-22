"use client";

export type TenantsActionQueuePriority = "high" | "medium" | "low";

export type TenantsActionQueueItem = {
    id: string;
    priority: TenantsActionQueuePriority;
    title: string;
    detail: string;
    actionLabel: string;
    clientId?: string;
    companyId?: string | null;
};

type TenantsActionQueuePanelProps<T extends TenantsActionQueueItem> = {
    items: T[];
    refreshing: boolean;
    onRefresh: () => void;
    onRunIntent: (item: T) => void;
    onSetClientContext: (clientId: string, companyId?: string | null) => void;
};

function priorityBadgeClass(priority: TenantsActionQueuePriority): string {
    if (priority === "high") {
        return "bg-red-100 text-red-800";
    }
    if (priority === "medium") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-emerald-100 text-emerald-800";
}

function priorityLabel(priority: TenantsActionQueuePriority): string {
    if (priority === "high") {
        return "Высокий";
    }
    if (priority === "medium") {
        return "Средний";
    }
    return "Низкий";
}

export default function TenantsActionQueuePanel<T extends TenantsActionQueueItem>({
    items,
    refreshing,
    onRefresh,
    onRunIntent,
    onSetClientContext,
}: TenantsActionQueuePanelProps<T>) {
    return (
        <section className="rounded-lg border border-border/60 bg-card p-3" data-testid="tenants-action-queue">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <h2 className="text-sm font-semibold">Очередь действий</h2>
                    <p className="text-xs text-muted-foreground">
                        Приоритетные действия для текущего среза активных тенантов.
                    </p>
                </div>
                <button className="btn-ghost" onClick={onRefresh} disabled={refreshing}>
                    Обновить
                </button>
            </div>
            <div className="mt-3 grid gap-2">
                {items.map((item) => (
                    <div
                        key={item.id}
                        className="rounded-lg border border-border/60 bg-background px-3 py-2"
                        data-testid="tenants-action-queue-item"
                    >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="text-xs font-medium">{item.title}</div>
                            <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${priorityBadgeClass(item.priority)}`}>
                                {priorityLabel(item.priority)}
                            </span>
                        </div>
                        <div className="mt-1 text-xs text-muted-foreground">{item.detail}</div>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                            <button
                                className="btn-ghost"
                                onClick={() => onRunIntent(item)}
                                data-testid="tenants-action-queue-run"
                            >
                                {item.actionLabel}
                            </button>
                            {item.clientId ? (
                                <button
                                    className="btn-ghost"
                                    onClick={() => {
                                        if (item.clientId) {
                                            onSetClientContext(item.clientId, item.companyId);
                                        }
                                    }}
                                    data-testid="tenants-action-queue-context"
                                >
                                    В контекст клиента
                                </button>
                            ) : null}
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}
