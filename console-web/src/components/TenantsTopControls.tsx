type TenantsWorkspaceMode = "portfolio" | "onboarding" | "changes" | "decommission";
type TenantsViewPreset = "operator" | "platform";

export type TenantsFilterOption = {
    id: string;
    label: string;
};

type TenantsTopControlsProps = {
    isPlatformPreset: boolean;
    contextCompanyName: string | null;
    contextClientName: string | null;
    contextBranchName: string | null;
    contextCompanyId: string | null;
    contextClientId: string | null;
    contextBranchId: string | null;
    onClearBranchContext: () => void;
    onClearClientContext: () => void;
    onClearContext: () => void;
    pageFilterCompanyId: string | null;
    pageFilterClientId: string | null;
    pageFilterBranchId: string | null;
    pageFilterCompanyOptions: TenantsFilterOption[];
    pageFilterClientOptions: TenantsFilterOption[];
    pageFilterBranchOptions: TenantsFilterOption[];
    hasPageFilters: boolean;
    onPageFilterCompanyChange: (value: string | null) => void;
    onPageFilterClientChange: (value: string | null) => void;
    onPageFilterBranchChange: (value: string | null) => void;
    onApplyContextToPageFilters: () => void;
    onClearPageFilters: () => void;
    workspaceMode: TenantsWorkspaceMode;
    onWorkspaceModeChange: (value: TenantsWorkspaceMode) => void;
    viewPreset: TenantsViewPreset;
    onViewPresetChange: (value: TenantsViewPreset) => void;
    canSwitchViewPreset: boolean;
};

function renderOptionLabel(label: string, id: string) {
    const normalized = label.trim();
    if (!normalized) {
        return id;
    }
    if (normalized === id) {
        return id;
    }
    return `${normalized} (${id})`;
}

export default function TenantsTopControls({
    isPlatformPreset,
    contextCompanyName,
    contextClientName,
    contextBranchName,
    contextCompanyId,
    contextClientId,
    contextBranchId,
    onClearBranchContext,
    onClearClientContext,
    onClearContext,
    pageFilterCompanyId,
    pageFilterClientId,
    pageFilterBranchId,
    pageFilterCompanyOptions,
    pageFilterClientOptions,
    pageFilterBranchOptions,
    hasPageFilters,
    onPageFilterCompanyChange,
    onPageFilterClientChange,
    onPageFilterBranchChange,
    onApplyContextToPageFilters,
    onClearPageFilters,
    workspaceMode,
    onWorkspaceModeChange,
    viewPreset,
    onViewPresetChange,
    canSwitchViewPreset,
}: TenantsTopControlsProps) {
    return (
        <div className="flex flex-col gap-2 mb-6">
            <h1 className="text-2xl font-bold" data-testid="tenants-title">Тенанты</h1>
            <div className="text-xs text-muted-foreground">
                Рабочий контур: {contextCompanyName ?? "—"} / {contextClientName ?? "—"} / {contextBranchName ?? "—"}
                {isPlatformPreset ? (
                    <span>
                        {" · ID (для диагностики): "}
                        {contextCompanyId ?? "—"} / {contextClientId ?? "—"} / {contextBranchId ?? "—"}
                    </span>
                ) : null}
            </div>
            <div className="rounded-lg border border-primary/30 bg-primary/[0.04] p-3" data-testid="tenants-page-filters">
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-foreground/80">
                    Шаг 1. Фильтры страницы
                </div>
                <div className="grid gap-2 md:grid-cols-3">
                    <label className="text-xs text-foreground/80">
                        Компания
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={pageFilterCompanyId ?? ""}
                            onChange={(event) => onPageFilterCompanyChange(event.target.value || null)}
                            data-testid="tenants-page-filter-company"
                        >
                            <option value="">Все компании</option>
                            {pageFilterCompanyOptions.map((option) => (
                                <option key={option.id} value={option.id}>
                                    {renderOptionLabel(option.label, option.id)}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="text-xs text-foreground/80">
                        Клиент
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={pageFilterClientId ?? ""}
                            onChange={(event) => onPageFilterClientChange(event.target.value || null)}
                            data-testid="tenants-page-filter-client"
                        >
                            <option value="">Все клиенты</option>
                            {pageFilterClientOptions.map((option) => (
                                <option key={option.id} value={option.id}>
                                    {renderOptionLabel(option.label, option.id)}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="text-xs text-foreground/80">
                        Филиал
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={pageFilterBranchId ?? ""}
                            onChange={(event) => onPageFilterBranchChange(event.target.value || null)}
                            data-testid="tenants-page-filter-branch"
                        >
                            <option value="">Все филиалы</option>
                            {pageFilterBranchOptions.map((option) => (
                                <option key={option.id} value={option.id}>
                                    {renderOptionLabel(option.label, option.id)}
                                </option>
                            ))}
                        </select>
                    </label>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                    <button
                        className="btn-ghost"
                        onClick={onApplyContextToPageFilters}
                        data-testid="tenants-page-filter-apply-context"
                    >
                        Взять из рабочего контура
                    </button>
                    <button
                        className="btn-ghost"
                        onClick={onClearPageFilters}
                        disabled={!hasPageFilters}
                        data-testid="tenants-page-filter-clear-all"
                    >
                        Сбросить фильтры
                    </button>
                </div>
                <div className="mt-2 text-xs text-foreground/70">
                    Эти фильтры применяются только к этой странице и сохраняются в URL.
                </div>
            </div>
            <div className="rounded-lg border border-border/60 bg-muted/20 p-3" data-testid="tenants-context-lens">
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-foreground/80">
                    Шаг 2. Рабочий контур
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full border border-border/60 px-2 py-1">
                        компания: {contextCompanyName ?? "все"}
                    </span>
                    <span className="rounded-full border border-border/60 px-2 py-1">
                        клиент: {contextClientName ?? "все"}
                    </span>
                    <span className="rounded-full border border-border/60 px-2 py-1">
                        филиал: {contextBranchName ?? "все"}
                    </span>
                    <button
                        className="btn-ghost"
                        onClick={onClearContext}
                        data-testid="tenants-context-clear-all"
                    >
                        Сбросить контур
                    </button>
                    <details className="rounded-md border border-border/60 bg-background px-2 py-1" data-testid="tenants-context-clear-advanced">
                        <summary className="cursor-pointer text-foreground/80" data-testid="tenants-context-clear-advanced-toggle">
                            Точечная очистка
                        </summary>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                            <button
                                className="btn-ghost"
                                onClick={onClearBranchContext}
                                data-testid="tenants-context-clear-branch"
                            >
                                Очистить филиал
                            </button>
                            <button
                                className="btn-ghost"
                                onClick={onClearClientContext}
                                data-testid="tenants-context-clear-client"
                            >
                                Очистить клиента
                            </button>
                        </div>
                    </details>
                </div>
                <div className="mt-2 text-xs text-foreground/70">
                    Контур используется при переходах между разделами. Для списка на этой странице используйте кнопку «Взять из рабочего контура».
                </div>
            </div>
            <div className="rounded-lg border border-border/60 bg-card p-3" data-testid="tenants-workspace-modes">
                <div className="text-xs text-muted-foreground mb-2">Рабочая зона:</div>
                <div className="flex flex-wrap items-center gap-2">
                    <button
                        className={workspaceMode === "portfolio" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onWorkspaceModeChange("portfolio")}
                        data-testid="tenants-mode-portfolio"
                    >
                        Портфель
                    </button>
                    <button
                        className={workspaceMode === "onboarding" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onWorkspaceModeChange("onboarding")}
                        data-testid="tenants-mode-onboarding"
                    >
                        Онбординг
                    </button>
                    <button
                        className={workspaceMode === "changes" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onWorkspaceModeChange("changes")}
                        data-testid="tenants-mode-changes"
                    >
                        Изменения
                    </button>
                    <button
                        className={workspaceMode === "decommission" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onWorkspaceModeChange("decommission")}
                        data-testid="tenants-mode-decommission"
                    >
                        Вывод из эксплуатации
                    </button>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2" data-testid="tenants-view-preset">
                    <span className="text-xs text-muted-foreground">Профиль интерфейса:</span>
                    <button
                        className={viewPreset === "operator" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onViewPresetChange("operator")}
                        data-testid="tenants-view-preset-operator"
                    >
                        Оператор
                    </button>
                    <button
                        className={viewPreset === "platform" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onViewPresetChange("platform")}
                        disabled={!canSwitchViewPreset}
                        data-testid="tenants-view-preset-platform"
                    >
                        Платформа
                    </button>
                </div>
            </div>
            <div className="rounded-lg border border-border/60 bg-muted/20 p-3" data-testid="tenants-workspace-guide">
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-foreground/80">
                    Операционный ориентир
                </div>
                <div className="text-xs text-foreground/80">
                    Портфель: риски и состав клиентов. Онбординг: запуск нового филиала.
                    Изменения: согласованное изменение и публикация. Вывод из эксплуатации: архив и восстановление.
                </div>
                <div className="mt-2 text-xs text-foreground/80">
                    Перед запуском проверьте: карточку филиала, канал связи, часы работы,
                    статус оплаты и актуальность базы знаний.
                </div>
                <div className="mt-2 text-xs text-foreground/80">
                    Порядок работы: фильтры страницы, затем рабочий контур, затем профильная зона,
                    после чего проверка результата по журналу действий.
                </div>
            </div>
        </div>
    );
}
