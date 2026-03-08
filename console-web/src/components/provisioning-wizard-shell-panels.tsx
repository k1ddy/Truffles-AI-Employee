type ProvisioningInlineError = {
    id: string;
    code: string;
    message: string;
    capturedAt: string;
    traceId?: string | null;
};

type ProvisioningOnboardingMode = "autopilot" | "manual";

type ProvisioningWorkspaceScope = {
    companyId: string;
    clientId: string;
    branchId: string;
};

type ProvisioningWizardErrorSummaryProps = {
    errors: ProvisioningInlineError[];
    onClear: () => void;
};

type ProvisioningWizardModePanelProps = {
    mode: ProvisioningOnboardingMode;
    onChange: (next: ProvisioningOnboardingMode) => void;
};

type ProvisioningWizardExecutionHubProps = {
    scope: ProvisioningWorkspaceScope;
    scopeReady: boolean;
    onOpen: () => void;
};

export function ProvisioningWizardErrorSummary({
    errors,
    onClear,
}: ProvisioningWizardErrorSummaryProps) {
    if (errors.length === 0) {
        return null;
    }

    return (
        <section className="mt-6 rounded-xl border border-red-300/60 bg-red-50 p-4" data-testid="provisioning-error-summary">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-red-900">Ошибки последних операций</h3>
                <button type="button" className="btn-ghost" onClick={onClear}>
                    Очистить
                </button>
            </div>
            <div className="mt-2 space-y-2">
                {errors.map((error) => (
                    <div key={error.id} className="rounded-lg border border-red-200/80 bg-background/90 p-3 text-xs">
                        <div className="font-mono text-red-900">{error.code}</div>
                        <div className="mt-1 text-foreground">{error.message}</div>
                        <div className="mt-1 text-muted-foreground">
                            {new Date(error.capturedAt).toLocaleString("ru-RU")}
                            {error.traceId ? ` · trace: ${error.traceId}` : ""}
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}

export function ProvisioningWizardModePanel({
    mode,
    onChange,
}: ProvisioningWizardModePanelProps) {
    return (
        <div className="mt-6 rounded-xl border border-border/60 bg-card p-4">
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Режим онбординга</div>
            <div className="mt-3 flex flex-wrap gap-2">
                <button
                    type="button"
                    className={`rounded-lg border px-3 py-2 text-sm ${
                        mode === "autopilot"
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border/60 bg-background"
                    }`}
                    onClick={() => onChange("autopilot")}
                >
                    Автопроцесс (Recommended)
                </button>
                <button
                    type="button"
                    className={`rounded-lg border px-3 py-2 text-sm ${
                        mode === "manual"
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-border/60 bg-background"
                    }`}
                    onClick={() => onChange("manual")}
                >
                    Ручной по шагам
                </button>
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
                Автопроцесс: минимальные входы и авто-связка сущностей. Ручной режим: детальная настройка шага за шагом.
            </p>
        </div>
    );
}

export function ProvisioningWizardExecutionHub({
    scope,
    scopeReady,
    onOpen,
}: ProvisioningWizardExecutionHubProps) {
    return (
        <div className="mt-4 rounded-xl border border-blue-300/60 bg-blue-50 p-4" data-testid="onboarding-execution-hub">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-900">
                        Execution Hub
                    </div>
                    <div className="mt-1 text-sm text-blue-900">
                        Рабочий поток выполнения: используйте Company Workspace для remediation/go-live.
                    </div>
                    <div className="mt-1 text-xs text-blue-900/80">
                        scope: company={scope.companyId || "—"} · client={scope.clientId || "—"} · branch={scope.branchId || "—"}
                    </div>
                    {!scopeReady && (
                        <div className="mt-1 text-xs text-blue-900/80">
                            Для полного контекста заполните company/client/branch.
                        </div>
                    )}
                </div>
                <button
                    type="button"
                    className="btn-primary"
                    onClick={onOpen}
                    data-testid="onboarding-open-workspace"
                >
                    Продолжить в Workspace
                </button>
            </div>
        </div>
    );
}
