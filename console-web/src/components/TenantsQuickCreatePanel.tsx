type QuickCreateRunning = "company" | "client" | "branch" | null;

export type TenantsQuickCreateForm = {
    companyName: string;
    clientSlug: string;
    branchName: string;
    branchSlug: string;
    branchTimezone: string;
    branchPhone: string;
    branchInstanceId: string;
    companyId: string;
    clientId: string;
};

type TenantsQuickCreatePanelProps = {
    form: TenantsQuickCreateForm;
    running: QuickCreateRunning;
    companyId: string;
    clientId: string;
    onChange: (patch: Partial<TenantsQuickCreateForm>) => void;
    onCreateCompany: () => void;
    onCreateClient: () => void;
    onCreateBranch: () => void;
    onOpenWorkspace: () => void;
};

export default function TenantsQuickCreatePanel({
    form,
    running,
    companyId,
    clientId,
    onChange,
    onCreateCompany,
    onCreateClient,
    onCreateBranch,
    onOpenWorkspace,
}: TenantsQuickCreatePanelProps) {
    return (
        <section className="rounded-lg border border-border/60 bg-card p-4" data-testid="tenants-quick-create">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                    <h2 className="text-sm font-semibold">Быстрое создание</h2>
                    <p className="text-xs text-muted-foreground">
                        Поток: компания -&gt; клиент -&gt; филиал. Рабочий контур обновляется автоматически.
                    </p>
                </div>
                <button className="btn-ghost" onClick={onOpenWorkspace}>
                    Открыть рабочее место компании
                </button>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
                <div className="rounded-lg border border-border/60 bg-background p-3">
                    <div className="text-xs font-semibold">1. Компания</div>
                    <label htmlFor="quick-create-company-name" className="mt-2 block text-xs text-muted-foreground">
                        Название компании
                    </label>
                    <input
                        id="quick-create-company-name"
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={form.companyName}
                        onChange={(event) => onChange({ companyName: event.target.value })}
                        placeholder="Beauty Group"
                        data-testid="tenants-quick-create-company-name"
                    />
                    <button
                        className="btn-primary mt-3"
                        onClick={onCreateCompany}
                        disabled={running !== null}
                    >
                        {running === "company" ? "Создание..." : "Создать компанию"}
                    </button>
                    <div className="mt-2 text-[11px] text-muted-foreground">
                        ID компании: <span className="font-mono">{companyId || "—"}</span>
                    </div>
                </div>

                <div className="rounded-lg border border-border/60 bg-background p-3">
                    <div className="text-xs font-semibold">2. Клиент</div>
                    <label htmlFor="quick-create-client-slug" className="mt-2 block text-xs text-muted-foreground">
                        Slug клиента
                    </label>
                    <input
                        id="quick-create-client-slug"
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={form.clientSlug}
                        onChange={(event) => onChange({ clientSlug: event.target.value.toLowerCase() })}
                        placeholder="beauty_group_almaty"
                        data-testid="tenants-quick-create-client-slug"
                    />
                    <button
                        className="btn-primary mt-3"
                        onClick={onCreateClient}
                        disabled={running !== null}
                    >
                        {running === "client" ? "Создание..." : "Создать клиента"}
                    </button>
                    <div className="mt-2 text-[11px] text-muted-foreground">
                        ID клиента: <span className="font-mono">{clientId || "—"}</span>
                    </div>
                </div>

                <div className="rounded-lg border border-border/60 bg-background p-3">
                    <div className="text-xs font-semibold">3. Филиал</div>
                    <div className="mt-2 grid gap-2">
                        <label htmlFor="quick-create-branch-name" className="text-xs text-muted-foreground">
                            Название филиала
                        </label>
                        <input
                            id="quick-create-branch-name"
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={form.branchName}
                            onChange={(event) => onChange({ branchName: event.target.value })}
                            placeholder="Almaty Downtown"
                            data-testid="tenants-quick-create-branch-name"
                        />
                        <label htmlFor="quick-create-branch-slug" className="text-xs text-muted-foreground">
                            Slug филиала
                        </label>
                        <input
                            id="quick-create-branch-slug"
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={form.branchSlug}
                            onChange={(event) => onChange({ branchSlug: event.target.value.toLowerCase() })}
                            placeholder="almaty_downtown"
                            data-testid="tenants-quick-create-branch-slug"
                        />
                        <label htmlFor="quick-create-branch-timezone" className="text-xs text-muted-foreground">
                            Часовой пояс
                        </label>
                        <input
                            id="quick-create-branch-timezone"
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={form.branchTimezone}
                            onChange={(event) => onChange({ branchTimezone: event.target.value })}
                            placeholder="Asia/Almaty"
                            data-testid="tenants-quick-create-branch-timezone"
                        />
                        <label htmlFor="quick-create-branch-phone" className="text-xs text-muted-foreground">
                            Телефон WhatsApp
                        </label>
                        <input
                            id="quick-create-branch-phone"
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={form.branchPhone}
                            onChange={(event) => onChange({ branchPhone: event.target.value })}
                            placeholder="+77000000000"
                            data-testid="tenants-quick-create-branch-phone"
                        />
                        <label htmlFor="quick-create-branch-instance-id" className="text-xs text-muted-foreground">
                            Идентификатор WhatsApp (если есть)
                        </label>
                        <input
                            id="quick-create-branch-instance-id"
                            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={form.branchInstanceId}
                            onChange={(event) => onChange({ branchInstanceId: event.target.value })}
                            placeholder="instance-xxxxxxxx"
                            data-testid="tenants-quick-create-branch-instance-id"
                        />
                    </div>
                    <button
                        className="btn-primary mt-3"
                        onClick={onCreateBranch}
                        disabled={running !== null}
                    >
                        {running === "branch" ? "Создание..." : "Создать филиал"}
                    </button>
                </div>
            </div>
        </section>
    );
}
