"use client";

import type { components } from "@/types/api.generated";

type CompanyEditorState = {
    id: string;
    name: string;
    billingInfo: string;
    originalName: string;
    originalBillingInfo: string;
};

type TenantsPortfolioCompaniesPanelProps = {
    companies: components["schemas"]["ConsoleCompany"][];
    loading: boolean;
    errored: boolean;
    query: string;
    onQueryChange: (value: string) => void;
    isPlatformPreset: boolean;
    canWriteTenants: boolean;
    selectedCompanyId: string | null;
    companyEditor: CompanyEditorState | null;
    savingCompany: boolean;
    hasNextPage: boolean;
    isFetchingNextPage: boolean;
    onFetchNextPage: () => void;
    onStartEdit: (company: components["schemas"]["ConsoleCompany"]) => void;
    onSetContext: (companyId: string) => void;
    onCancelEdit: () => void;
    onSaveEdit: () => void;
    onChangeEditorName: (value: string) => void;
    onChangeEditorBillingInfo: (value: string) => void;
};

export default function TenantsPortfolioCompaniesPanel({
    companies,
    loading,
    errored,
    query,
    onQueryChange,
    isPlatformPreset,
    canWriteTenants,
    selectedCompanyId,
    companyEditor,
    savingCompany,
    hasNextPage,
    isFetchingNextPage,
    onFetchNextPage,
    onStartEdit,
    onSetContext,
    onCancelEdit,
    onSaveEdit,
    onChangeEditorName,
    onChangeEditorBillingInfo,
}: TenantsPortfolioCompaniesPanelProps) {
    return (
        <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-portfolio-companies">
            <div className="flex items-center justify-between gap-4 mb-4">
                <div>
                    <h2 className="text-lg font-semibold">Компании</h2>
                    <p className="text-sm text-muted-foreground">
                        {loading ? "—" : `${companies.length} всего`}
                    </p>
                </div>
                <input
                    className="w-56 rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    placeholder="Поиск по компаниям"
                    value={query}
                    onChange={(event) => onQueryChange(event.target.value)}
                />
            </div>
            <div className="space-y-3">
                {loading ? (
                    <div className="text-sm text-muted-foreground">Загрузка компаний...</div>
                ) : errored ? (
                    <div className="text-sm text-muted-foreground">Не удалось загрузить компании.</div>
                ) : companies.length === 0 ? (
                    <div className="text-sm text-muted-foreground">Компании не найдены.</div>
                ) : (
                    companies.map((company) => {
                        const isEditing = companyEditor?.id === company.id;
                        return (
                            <div
                                key={company.id}
                                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
                            >
                                <div>
                                    <div className="font-medium">{company.name ?? "Без названия"}</div>
                                    {isPlatformPreset ? (
                                        <div className="text-xs text-muted-foreground">{company.id}</div>
                                    ) : null}
                                </div>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <span>{company.id === selectedCompanyId ? "Выбрана" : ""}</span>
                                    {canWriteTenants ? (
                                        <button
                                            className="btn-ghost"
                                            onClick={() => onStartEdit(company)}
                                        >
                                            Редактировать
                                        </button>
                                    ) : null}
                                    <button
                                        className="btn-ghost"
                                        onClick={() => onSetContext(company.id)}
                                        disabled={company.id === selectedCompanyId}
                                    >
                                        В контекст
                                    </button>
                                </div>
                                {isEditing && companyEditor ? (
                                    <div className="w-full mt-3 rounded-lg border border-border/60 bg-muted/30 p-3">
                                        <div className="grid gap-3">
                                            <div className="rounded-lg border border-border/60 bg-background p-3 text-[11px] text-muted-foreground">
                                                Измените название компании. Дополнительные параметры биллинга нужны только для расширенной настройки.
                                            </div>
                                            <label className="text-xs text-muted-foreground">
                                                Название
                                                <input
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={companyEditor.name}
                                                    onChange={(event) => onChangeEditorName(event.target.value)}
                                                    disabled={!canWriteTenants || savingCompany}
                                                />
                                            </label>
                                            <details className="rounded-lg border border-border/60 bg-background p-3">
                                                <summary className="cursor-pointer text-xs text-muted-foreground">
                                                    Дополнительно: параметры биллинга (JSON)
                                                </summary>
                                                <label className="mt-2 block text-xs text-muted-foreground">
                                                    billing_info (опционально)
                                                    <textarea
                                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                                                        rows={3}
                                                        value={companyEditor.billingInfo}
                                                        onChange={(event) => onChangeEditorBillingInfo(event.target.value)}
                                                        disabled={!canWriteTenants || savingCompany}
                                                    />
                                                </label>
                                            </details>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    className="btn-primary"
                                                    onClick={onSaveEdit}
                                                    disabled={!canWriteTenants || savingCompany}
                                                >
                                                    {savingCompany ? "Сохранение..." : "Сохранить"}
                                                </button>
                                                <button
                                                    className="btn-ghost"
                                                    onClick={onCancelEdit}
                                                    disabled={savingCompany}
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
            {hasNextPage ? (
                <div className="flex justify-center pt-3">
                    <button
                        className="btn-ghost"
                        onClick={onFetchNextPage}
                        disabled={isFetchingNextPage}
                    >
                        {isFetchingNextPage ? "Загрузка..." : "Показать еще"}
                    </button>
                </div>
            ) : null}
        </section>
    );
}
