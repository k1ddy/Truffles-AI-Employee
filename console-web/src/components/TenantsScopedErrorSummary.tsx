"use client";

import type { InlineErrorSummaryItem } from "@/lib/use-inline-error-summary";

type TenantsScopedErrorSummaryProps = {
    errors: InlineErrorSummaryItem[];
    scopeLabel: string;
    showScopeClear: boolean;
    onClearScope: () => void;
    onClearAll: () => void;
};

export default function TenantsScopedErrorSummary({
    errors,
    scopeLabel,
    showScopeClear,
    onClearScope,
    onClearAll,
}: TenantsScopedErrorSummaryProps) {
    if (errors.length === 0) {
        return null;
    }

    return (
        <section className="rounded-lg border border-red-300/60 bg-red-50 p-3" data-testid="tenants-error-summary">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-semibold text-red-900">
                    Ошибки последних операций ({scopeLabel})
                </div>
                <div className="flex items-center gap-2">
                    {showScopeClear ? (
                        <button className="btn-ghost" onClick={onClearScope}>
                            Очистить зону
                        </button>
                    ) : null}
                    <button className="btn-ghost" onClick={onClearAll}>Очистить все</button>
                </div>
            </div>
            <div className="mt-1 text-xs text-red-900/80">
                Исправьте отмеченные поля и повторите действие. Для API ошибок используйте `trace` из записи ниже.
            </div>
            <div className="mt-2 space-y-2">
                {errors.map((error) => (
                    <div key={error.id} className="rounded-md border border-red-200/80 bg-background/90 p-2 text-xs">
                        <div className="font-mono text-red-900">{error.code} · scope={error.scope}</div>
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
