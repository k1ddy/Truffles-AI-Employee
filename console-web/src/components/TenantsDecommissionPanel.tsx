"use client";

type TenantLifecycleMode = "active" | "archived" | "all";

type TenantsDecommissionPanelProps = {
    tenantLifecycle: TenantLifecycleMode;
    onTenantLifecycleChange: (mode: TenantLifecycleMode) => void;
};

export default function TenantsDecommissionPanel({
    tenantLifecycle,
    onTenantLifecycleChange,
}: TenantsDecommissionPanelProps) {
    return (
        <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-decommission-center">
            <div className="flex items-center justify-between gap-4 mb-3">
                <div>
                    <h2 className="text-lg font-semibold">Вывод из эксплуатации</h2>
                    <p className="text-sm text-muted-foreground">
                        Архивация и восстановление клиентов с прозрачным подтверждением.
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <button
                        className={tenantLifecycle === "archived" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onTenantLifecycleChange("archived")}
                    >
                        Только архив
                    </button>
                    <button
                        className={tenantLifecycle === "all" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onTenantLifecycleChange("all")}
                    >
                        Все
                    </button>
                    <button
                        className={tenantLifecycle === "active" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onTenantLifecycleChange("active")}
                    >
                        Активные
                    </button>
                </div>
            </div>
            <div className="text-xs text-muted-foreground">
                Для вывода из эксплуатации используйте действия `Архивировать/Восстановить` в карточке клиента ниже.
            </div>
        </section>
    );
}
