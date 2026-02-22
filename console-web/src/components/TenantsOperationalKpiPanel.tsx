"use client";

type OperationalKpiStatus = "ok" | "warn" | "critical";
type OperationalKpiAction = "portfolio" | "onboarding" | "changes" | "decommission";
type OperationalKpiId =
    | "onboardingCoverage"
    | "goLiveReadiness"
    | "serviceStability"
    | "decommissionShare"
    | "changeFailure"
    | "rollbackShare"
    | "blockedSignals";

type OperationalKpiDrilldownItem = {
    id: OperationalKpiId;
    label: string;
    displayValue: string;
    status: OperationalKpiStatus;
    thresholdLabel: string;
    reason: string;
    action: OperationalKpiAction;
    actionLabel: string;
};

type OnboardingThroughput = {
    window_hours?: number | null;
    approved_branches_total?: number | null;
    first_pass_approved_branches?: number | null;
    time_to_go_live_median_hours?: number | null;
    blocker_age_p95_hours?: number | null;
    first_pass_go_live_rate_pct?: number | null;
    incident_reopen_rate_24h_pct?: number | null;
};

type MetricsSnapshotMode = "dry_run" | "execute";

type MetricsSnapshotJob = {
    job_type?: string | null;
    mode?: string | null;
    status?: string | null;
};

type WeeklySnapshot = {
    id: string;
    weekKey: string;
    createdAt: string;
    report: {
        kpi: {
            changeFailure: number | null | undefined;
            blockedSignals: number | null | undefined;
            serviceStability: number | null | undefined;
        };
    };
};

type TenantsOperationalKpiPanelProps = {
    isRefreshing: boolean;
    onRefresh: () => void;
    onExportJson: () => void;
    onExportCsv: () => void;
    onSaveWeeklySnapshot: () => void;
    canSaveWeeklySnapshot: boolean;
    operationalKpi: {
        sourceWindow: number;
        publishedChanges: number;
        publishFailedChanges: number;
        rolledBackChanges: number;
        onboardingCoveragePct: number;
        goLiveReadinessPct: number;
        serviceStabilityPct: number;
        decommissionSharePct: number;
        changeFailurePct: number;
        rollbackSharePct: number;
        blockedSignalsCount: number;
    };
    criticalKpiCount: number;
    warnKpiCount: number;
    kpiStatuses: Record<OperationalKpiId, OperationalKpiStatus>;
    kpiDrilldown: OperationalKpiDrilldownItem[];
    onRunKpiAction: (action: OperationalKpiAction) => void;
    onboardingThroughput: OnboardingThroughput | null;
    formatOptionalHours: (value: number | null | undefined) => string;
    formatOptionalPercent: (value: number | null | undefined) => string;
    alertSeverity: string;
    alertBreachesCount: number;
    onCopyAlertPayload: () => void;
    onRunMetricsSnapshot: (mode: MetricsSnapshotMode) => void;
    runningMetricsSnapshotMode: MetricsSnapshotMode | null;
    lastMetricsSnapshotJob: MetricsSnapshotJob | null;
    pageFilterClientId: string | null;
    weeklySnapshotsFetching: boolean;
    weeklySnapshots: WeeklySnapshot[];
    formatDateTimeLabel: (value?: string) => string;
};

function kpiCardClass(status: OperationalKpiStatus) {
    if (status === "critical") {
        return "rounded-lg border border-red-300 bg-red-50 px-3 py-2";
    }
    if (status === "warn") {
        return "rounded-lg border border-amber-300 bg-amber-50 px-3 py-2";
    }
    return "rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2";
}

function kpiStatusBadgeClass(status: OperationalKpiStatus) {
    if (status === "critical") {
        return "bg-red-100 text-red-700";
    }
    if (status === "warn") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-emerald-100 text-emerald-700";
}

export default function TenantsOperationalKpiPanel({
    isRefreshing,
    onRefresh,
    onExportJson,
    onExportCsv,
    onSaveWeeklySnapshot,
    canSaveWeeklySnapshot,
    operationalKpi,
    criticalKpiCount,
    warnKpiCount,
    kpiStatuses,
    kpiDrilldown,
    onRunKpiAction,
    onboardingThroughput,
    formatOptionalHours,
    formatOptionalPercent,
    alertSeverity,
    alertBreachesCount,
    onCopyAlertPayload,
    onRunMetricsSnapshot,
    runningMetricsSnapshotMode,
    lastMetricsSnapshotJob,
    pageFilterClientId,
    weeklySnapshotsFetching,
    weeklySnapshots,
    formatDateTimeLabel,
}: TenantsOperationalKpiPanelProps) {
    return (
        <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-operational-kpi">
            <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                    <h2 className="text-lg font-semibold">Операционные KPI</h2>
                    <p className="text-sm text-muted-foreground">
                        Прокси-метрики: портфель + attention + branch changes (последние 100 изменений)
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2" data-testid="tenants-kpi-export-controls">
                    <button
                        className="btn-ghost"
                        onClick={onRefresh}
                        disabled={isRefreshing}
                    >
                        {isRefreshing ? "Обновление..." : "Обновить KPI"}
                    </button>
                    <button
                        className="btn-ghost"
                        onClick={onExportJson}
                        data-testid="tenants-kpi-export-json"
                    >
                        Экспорт JSON
                    </button>
                    <button
                        className="btn-ghost"
                        onClick={onExportCsv}
                        data-testid="tenants-kpi-export-csv"
                    >
                        Экспорт CSV
                    </button>
                    <button
                        className="btn-ghost"
                        onClick={onSaveWeeklySnapshot}
                        data-testid="tenants-kpi-save-weekly-snapshot"
                        disabled={!canSaveWeeklySnapshot}
                        title={canSaveWeeklySnapshot ? undefined : "Выберите клиента в фильтрах страницы"}
                    >
                        Недельный снимок
                    </button>
                </div>
            </div>
            <div className="mb-3 text-xs text-muted-foreground">
                окно расчета изменений: {operationalKpi.sourceWindow} · опубликовано: {operationalKpi.publishedChanges} ·
                ошибок публикации: {operationalKpi.publishFailedChanges} · откатов: {operationalKpi.rolledBackChanges} ·
                критичных KPI: {criticalKpiCount} · предупреждений: {warnKpiCount}
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <div className={kpiCardClass(kpiStatuses.onboardingCoverage)} data-testid="tenants-kpi-onboarding-coverage">
                    <div className="text-xs text-muted-foreground">Покрытие онбординга (прокси)</div>
                    <div className="text-xl font-semibold">{operationalKpi.onboardingCoveragePct}%</div>
                    <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(kpiStatuses.onboardingCoverage)}`}>
                        {kpiStatuses.onboardingCoverage}
                    </div>
                </div>
                <div className={kpiCardClass(kpiStatuses.goLiveReadiness)} data-testid="tenants-kpi-go-live-readiness">
                    <div className="text-xs text-muted-foreground">Готовность к запуску (прокси)</div>
                    <div className="text-xl font-semibold">{operationalKpi.goLiveReadinessPct}%</div>
                    <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(kpiStatuses.goLiveReadiness)}`}>
                        {kpiStatuses.goLiveReadiness}
                    </div>
                </div>
                <div className={kpiCardClass(kpiStatuses.serviceStability)} data-testid="tenants-kpi-service-stability">
                    <div className="text-xs text-muted-foreground">Стабильность сервиса</div>
                    <div className="text-xl font-semibold">{operationalKpi.serviceStabilityPct}%</div>
                    <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(kpiStatuses.serviceStability)}`}>
                        {kpiStatuses.serviceStability}
                    </div>
                </div>
                <div className={kpiCardClass(kpiStatuses.decommissionShare)} data-testid="tenants-kpi-decommission-share">
                    <div className="text-xs text-muted-foreground">Доля вывода из эксплуатации</div>
                    <div className="text-xl font-semibold">{operationalKpi.decommissionSharePct}%</div>
                    <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(kpiStatuses.decommissionShare)}`}>
                        {kpiStatuses.decommissionShare}
                    </div>
                </div>
                <div className={kpiCardClass(kpiStatuses.changeFailure)} data-testid="tenants-kpi-change-failure">
                    <div className="text-xs text-muted-foreground">Доля ошибок публикации (прокси)</div>
                    <div className="text-xl font-semibold">{operationalKpi.changeFailurePct}%</div>
                    <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(kpiStatuses.changeFailure)}`}>
                        {kpiStatuses.changeFailure}
                    </div>
                </div>
                <div className={kpiCardClass(kpiStatuses.rollbackShare)} data-testid="tenants-kpi-rollback-share">
                    <div className="text-xs text-muted-foreground">Доля откатов (прокси)</div>
                    <div className="text-xl font-semibold">{operationalKpi.rollbackSharePct}%</div>
                    <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(kpiStatuses.rollbackShare)}`}>
                        {kpiStatuses.rollbackShare}
                    </div>
                </div>
                <div className={kpiCardClass(kpiStatuses.blockedSignals)} data-testid="tenants-kpi-blocked-signals">
                    <div className="text-xs text-muted-foreground">Блокирующие сигналы</div>
                    <div className="text-xl font-semibold">{operationalKpi.blockedSignalsCount}</div>
                    <div className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${kpiStatusBadgeClass(kpiStatuses.blockedSignals)}`}>
                        {kpiStatuses.blockedSignals}
                    </div>
                </div>
            </div>

            {onboardingThroughput ? (
                <div className="mt-4 rounded-lg border border-border/60 bg-background p-3" data-testid="tenants-onboarding-throughput">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                            Скорость онбординга
                        </div>
                        <div className="text-xs text-muted-foreground">
                            окно: {onboardingThroughput.window_hours ?? "—"}ч · approvals: {onboardingThroughput.approved_branches_total ?? "—"} · first-pass: {onboardingThroughput.first_pass_approved_branches ?? "—"}
                        </div>
                    </div>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                        <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2">
                            <div className="text-[11px] text-foreground/80">Медиана времени до запуска</div>
                            <div className="text-base font-semibold">{formatOptionalHours(onboardingThroughput.time_to_go_live_median_hours)}</div>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2">
                            <div className="text-[11px] text-foreground/80">Возраст блокера p95</div>
                            <div className="text-base font-semibold">{formatOptionalHours(onboardingThroughput.blocker_age_p95_hours)}</div>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2">
                            <div className="text-[11px] text-foreground/80">Запуск с первого прохода</div>
                            <div className="text-base font-semibold">{formatOptionalPercent(onboardingThroughput.first_pass_go_live_rate_pct)}</div>
                        </div>
                        <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2">
                            <div className="text-[11px] text-foreground/80">Переоткрытие инцидента &lt;24ч</div>
                            <div className="text-base font-semibold">{formatOptionalPercent(onboardingThroughput.incident_reopen_rate_24h_pct)}</div>
                        </div>
                    </div>
                </div>
            ) : null}

            <div className="mt-4 rounded-lg border border-border/60 bg-background p-3" data-testid="tenants-kpi-drilldown">
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                    Threshold drill-down
                </div>
                <div className="space-y-2">
                    {kpiDrilldown.map((item) => (
                        <div
                            key={item.id}
                            className="rounded-lg border border-border/60 p-2"
                            data-testid="tenants-kpi-drilldown-row"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="font-medium text-sm">{item.label}</div>
                                <div className="flex items-center gap-2 text-xs">
                                    <span className={`inline-flex rounded-full px-2 py-0.5 font-semibold ${kpiStatusBadgeClass(item.status)}`}>
                                        {item.status}
                                    </span>
                                    <span className="font-medium">{item.displayValue}</span>
                                </div>
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">
                                {item.reason}
                            </div>
                            <div className="mt-1 text-xs text-muted-foreground">
                                threshold: {item.thresholdLabel}
                            </div>
                            <div className="mt-2">
                                <button
                                    className="btn-ghost"
                                    onClick={() => onRunKpiAction(item.action)}
                                    data-testid={`tenants-kpi-action-${item.id}`}
                                >
                                    {item.actionLabel}
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="mt-4 grid gap-3 lg:grid-cols-2">
                <div className="rounded-lg border border-border/60 bg-background p-3" data-testid="tenants-kpi-alert-hooks">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Интеграция алертов
                    </div>
                    <div className="text-xs text-muted-foreground">
                        <span data-testid="tenants-kpi-alert-severity">severity: {alertSeverity}</span> · breaches: {alertBreachesCount}
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                        <button
                            className="btn-ghost"
                            onClick={onCopyAlertPayload}
                            data-testid="tenants-kpi-alert-copy"
                        >
                            Скопировать payload
                        </button>
                        <button
                            className="btn-ghost"
                            onClick={() => onRunMetricsSnapshot("dry_run")}
                            disabled={runningMetricsSnapshotMode !== null}
                            data-testid="tenants-kpi-alert-dryrun"
                        >
                            {runningMetricsSnapshotMode === "dry_run" ? "Пробный запуск..." : "Пробный запуск"}
                        </button>
                        <button
                            className="btn-ghost"
                            onClick={() => onRunMetricsSnapshot("execute")}
                            disabled={runningMetricsSnapshotMode !== null}
                            data-testid="tenants-kpi-alert-execute"
                        >
                            {runningMetricsSnapshotMode === "execute" ? "Запуск..." : "Запустить"}
                        </button>
                    </div>
                    {lastMetricsSnapshotJob ? (
                        <div className="mt-2 text-xs text-muted-foreground" data-testid="tenants-kpi-alert-last-job">
                            job: {lastMetricsSnapshotJob.job_type ?? "—"} · mode: {lastMetricsSnapshotJob.mode ?? "—"} · status: {lastMetricsSnapshotJob.status ?? "—"}
                        </div>
                    ) : null}
                </div>

                <div className="rounded-lg border border-border/60 bg-background p-3" data-testid="tenants-kpi-weekly-snapshots">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                        Недельные снимки
                    </div>
                    {!pageFilterClientId ? (
                        <div className="text-xs text-muted-foreground">
                            Выберите клиента в фильтрах страницы, чтобы загрузить снимки.
                        </div>
                    ) : weeklySnapshotsFetching ? (
                        <div className="text-xs text-muted-foreground">
                            Загрузка недельных снимков...
                        </div>
                    ) : weeklySnapshots.length === 0 ? (
                        <div className="text-xs text-muted-foreground">
                            Снимков пока нет. Сохраните первый недельный снимок.
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {weeklySnapshots.slice(0, 4).map((item, index) => {
                                const previous = weeklySnapshots[index + 1];
                                const currentFailure = item.report.kpi.changeFailure;
                                const previousFailure = previous?.report.kpi.changeFailure;
                                const delta = (
                                    typeof currentFailure === "number" && typeof previousFailure === "number"
                                )
                                    ? currentFailure - previousFailure
                                    : null;
                                return (
                                    <div key={item.id} className="rounded border border-border/50 px-2 py-1 text-xs">
                                        <div className="font-medium">
                                            {item.weekKey} · {formatDateTimeLabel(item.createdAt)}
                                        </div>
                                        <div className="text-muted-foreground">
                                            ошибки публикации: {item.report.kpi.changeFailure ?? "—"}% {delta === null ? "" : `(Δ ${delta >= 0 ? "+" : ""}${delta}%)`}
                                        </div>
                                        <div className="text-muted-foreground">
                                            блокирующие сигналы: {item.report.kpi.blockedSignals ?? "—"} · стабильность сервиса: {item.report.kpi.serviceStability ?? "—"}%
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </section>
    );
}
