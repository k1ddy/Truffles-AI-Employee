import type {
    ConsultantVerificationCompareCaseRecord,
    ConsultantVerificationCompareReadiness,
} from "@/lib/api-client";

import {
    formatTimestamp,
    getCompareDeltaPresentation,
    getCompareReadinessPresentation,
    getOutcomeLabel,
    getVerdictPresentation,
} from "../_lib/presentation";

type ComparePanelProps = {
    readiness: ConsultantVerificationCompareReadiness | null;
    cases: ConsultantVerificationCompareCaseRecord[];
    isBusy: boolean;
    canCompareLastPrompt: boolean;
    onCompareLastPrompt: () => void;
};

export default function ConsultantVerificationComparePanel({
    readiness,
    cases,
    isBusy,
    canCompareLastPrompt,
    onCompareLastPrompt,
}: ComparePanelProps) {
    const readinessPresentation = getCompareReadinessPresentation(readiness?.status);

    return (
        <article
            className="mt-4 rounded-xl border border-border/60 bg-card p-4"
            data-testid="consultant-verification-compare"
        >
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className="text-sm font-semibold text-foreground">Сравнение live vs draft</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Один и тот же сценарий прогоняется по текущей опубликованной версии и по сохраненному draft.
                    </p>
                </div>
                <button
                    type="button"
                    className="btn-ghost"
                    onClick={onCompareLastPrompt}
                    disabled={isBusy || !canCompareLastPrompt}
                    data-testid="consultant-verification-compare-last-prompt"
                >
                    {isBusy ? "Сравниваю..." : "Сравнить последний вопрос"}
                </button>
            </div>

            <div className={`mt-4 rounded-2xl border p-4 ${readinessPresentation.panelClass}`}>
                <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${readinessPresentation.chipClass}`}>
                        {readiness?.status_label ?? readinessPresentation.label}
                    </span>
                    {readiness?.draft_hash ? (
                        <span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                            Draft hash: {readiness.draft_hash}
                        </span>
                    ) : null}
                    {readiness?.compared_at ? (
                        <span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                            Compare: {formatTimestamp(readiness.compared_at)}
                        </span>
                    ) : null}
                </div>
                <p className="mt-3 text-sm text-foreground">
                    {readiness?.summary
                        ?? "Сначала сохраните draft в Knowledge, затем прогоните хотя бы один сценарий live vs draft."}
                </p>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full border border-border px-2 py-0.5">
                        Кейсов: {readiness?.total_cases ?? 0}
                    </span>
                    <span className="rounded-full border border-border px-2 py-0.5">
                        Лучше: {readiness?.improved_total ?? 0}
                    </span>
                    <span className="rounded-full border border-border px-2 py-0.5">
                        Без изменений: {readiness?.unchanged_total ?? 0}
                    </span>
                    <span className="rounded-full border border-border px-2 py-0.5">
                        Регрессии: {readiness?.regressed_total ?? 0}
                    </span>
                    <span className="rounded-full border border-border px-2 py-0.5">
                        Ручная проверка: {readiness?.manual_review_total ?? 0}
                    </span>
                </div>
            </div>

            {cases.length > 0 ? (
                <div className="mt-4 space-y-3" data-testid="consultant-verification-compare-cases">
                    {cases.map((item) => {
                        const deltaPresentation = getCompareDeltaPresentation(item.delta);
                        const liveVerdict = getVerdictPresentation(item.live_turn.business_verdict);
                        const draftVerdict = getVerdictPresentation(item.draft_turn.business_verdict);
                        return (
                            <article
                                key={item.case_id}
                                className="rounded-xl border border-border/60 bg-muted/10 p-3"
                                data-testid={`consultant-verification-compare-case-${item.case_id}`}
                            >
                                <div className="flex flex-wrap items-start justify-between gap-2">
                                    <div>
                                        <p className="text-sm font-semibold text-foreground">{item.label}</p>
                                        <p className="mt-1 text-sm text-muted-foreground">{item.summary}</p>
                                    </div>
                                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${deltaPresentation.chipClass}`}>
                                        {item.delta_label}
                                    </span>
                                </div>

                                <div className="mt-3 grid gap-3 lg:grid-cols-2">
                                    <div className="rounded-xl border border-border/60 bg-background/80 p-3">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                                Live
                                            </span>
                                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${liveVerdict.chipClass}`}>
                                                {liveVerdict.label}
                                            </span>
                                            <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                                                {getOutcomeLabel(item.live_turn.outcome)}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-sm text-foreground">{item.live_turn.content}</p>
                                    </div>

                                    <div className="rounded-xl border border-border/60 bg-background/80 p-3">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                                Draft
                                            </span>
                                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${draftVerdict.chipClass}`}>
                                                {draftVerdict.label}
                                            </span>
                                            <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                                                {getOutcomeLabel(item.draft_turn.outcome)}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-sm text-foreground">{item.draft_turn.content}</p>
                                    </div>
                                </div>
                            </article>
                        );
                    })}
                </div>
            ) : (
                <p className="mt-4 text-sm text-muted-foreground">
                    Пока нет compare-кейсов. Сравните последний вопрос или выполните retest по finding&apos;у ниже.
                </p>
            )}
        </article>
    );
}
