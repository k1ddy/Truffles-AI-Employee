"use client";

export type OperationalKpiId =
    | "onboardingCoverage"
    | "goLiveReadiness"
    | "serviceStability"
    | "decommissionShare"
    | "changeFailure"
    | "rollbackShare"
    | "blockedSignals";

export type OperationalKpiStatus = "ok" | "warn" | "critical";
export type OperationalKpiAction = "portfolio" | "onboarding" | "changes" | "decommission";

type OperationalKpiRule = {
    id: OperationalKpiId;
    label: string;
    unit: "percent" | "count";
    direction: "higher_better" | "lower_better";
    warn: number;
    critical: number;
    action: OperationalKpiAction;
    actionLabel: string;
};

export type OperationalKpiDrilldown = {
    id: OperationalKpiId;
    label: string;
    value: number;
    displayValue: string;
    status: OperationalKpiStatus;
    thresholdLabel: string;
    reason: string;
    action: OperationalKpiAction;
    actionLabel: string;
};

const OPERATIONAL_KPI_RULES: OperationalKpiRule[] = [
    {
        id: "onboardingCoverage",
        label: "Покрытие онбординга",
        unit: "percent",
        direction: "higher_better",
        warn: 60,
        critical: 40,
        action: "onboarding",
        actionLabel: "Открыть онбординг",
    },
    {
        id: "goLiveReadiness",
        label: "Готовность к запуску",
        unit: "percent",
        direction: "higher_better",
        warn: 70,
        critical: 50,
        action: "onboarding",
        actionLabel: "Проверить запуск",
    },
    {
        id: "serviceStability",
        label: "Стабильность сервиса",
        unit: "percent",
        direction: "higher_better",
        warn: 95,
        critical: 85,
        action: "portfolio",
        actionLabel: "Открыть риски",
    },
    {
        id: "decommissionShare",
        label: "Доля вывода из эксплуатации",
        unit: "percent",
        direction: "lower_better",
        warn: 30,
        critical: 45,
        action: "decommission",
        actionLabel: "Открыть вывод из эксплуатации",
    },
    {
        id: "changeFailure",
        label: "Доля ошибок публикации",
        unit: "percent",
        direction: "lower_better",
        warn: 10,
        critical: 20,
        action: "changes",
        actionLabel: "Открыть изменения",
    },
    {
        id: "rollbackShare",
        label: "Доля откатов",
        unit: "percent",
        direction: "lower_better",
        warn: 15,
        critical: 30,
        action: "changes",
        actionLabel: "Проверить откаты",
    },
    {
        id: "blockedSignals",
        label: "Блокирующие сигналы",
        unit: "count",
        direction: "lower_better",
        warn: 1,
        critical: 5,
        action: "portfolio",
        actionLabel: "Разобрать блокеры",
    },
];

export function asPercent(numerator: number, denominator: number): number {
    if (denominator <= 0) {
        return 0;
    }
    return Math.round((numerator / denominator) * 100);
}

export function formatOptionalHours(value: number | null | undefined): string {
    if (typeof value !== "number" || Number.isNaN(value)) {
        return "—";
    }
    return `${Number(value.toFixed(1))}ч`;
}

export function formatOptionalPercent(value: number | null | undefined): string {
    if (typeof value !== "number" || Number.isNaN(value)) {
        return "—";
    }
    return `${Number(value.toFixed(1))}%`;
}

function computeKpiStatus(value: number, rule: OperationalKpiRule): OperationalKpiStatus {
    if (rule.direction === "higher_better") {
        if (value < rule.critical) {
            return "critical";
        }
        if (value < rule.warn) {
            return "warn";
        }
        return "ok";
    }
    if (value > rule.critical) {
        return "critical";
    }
    if (value > rule.warn) {
        return "warn";
    }
    return "ok";
}

function formatKpiValue(value: number, unit: "percent" | "count"): string {
    if (unit === "percent") {
        return `${value}%`;
    }
    return `${value}`;
}

function formatThresholdLabel(rule: OperationalKpiRule): string {
    const formatValue = (value: number) => (rule.unit === "percent" ? `${value}%` : `${value}`);
    if (rule.direction === "higher_better") {
        return `warn < ${formatValue(rule.warn)}, critical < ${formatValue(rule.critical)}`;
    }
    return `warn > ${formatValue(rule.warn)}, critical > ${formatValue(rule.critical)}`;
}

function formatKpiReason(value: number, rule: OperationalKpiRule, status: OperationalKpiStatus): string {
    const thresholdLabel = formatThresholdLabel(rule);
    if (status === "ok") {
        return `В норме (${thresholdLabel})`;
    }
    if (status === "critical") {
        return `Критично (${thresholdLabel})`;
    }
    return `Требует внимания (${thresholdLabel})`;
}

export function buildOperationalKpiDrilldown(
    values: Record<OperationalKpiId, number>,
): OperationalKpiDrilldown[] {
    return OPERATIONAL_KPI_RULES.map((rule) => {
        const value = values[rule.id];
        const status = computeKpiStatus(value, rule);
        return {
            id: rule.id,
            label: rule.label,
            value,
            displayValue: formatKpiValue(value, rule.unit),
            status,
            thresholdLabel: formatThresholdLabel(rule),
            reason: formatKpiReason(value, rule, status),
            action: rule.action,
            actionLabel: rule.actionLabel,
        };
    });
}
