import type {
    ConsultantVerificationSessionRecord,
    ConsultantVerificationSessionSummary,
} from "@/lib/api-client";

import {
    formatSessionTitle,
    getVerdictPresentation,
} from "../_lib/presentation";

type SessionSummaryPanelProps = {
    session: ConsultantVerificationSessionRecord | null;
    summary: ConsultantVerificationSessionSummary | null;
    index: number;
    isBusy: boolean;
    lastOwnerPrompt: string | null;
    onReplayLastPrompt: () => void;
    onReplayWholeSession: () => void;
    onReplayWeakPrompt: (prompt: string) => void;
};

function summaryCardClass(kind: "answered" | "clarify" | "handoff" | "gap"): string {
    if (kind === "answered") {
        return "border-emerald-200 bg-emerald-50/80";
    }
    if (kind === "clarify") {
        return "border-sky-200 bg-sky-50/80";
    }
    if (kind === "handoff") {
        return "border-amber-200 bg-amber-50/80";
    }
    return "border-rose-200 bg-rose-50/80";
}

export default function ConsultantVerificationSessionSummaryPanel({
    session,
    summary,
    index,
    isBusy,
    lastOwnerPrompt,
    onReplayLastPrompt,
    onReplayWholeSession,
    onReplayWeakPrompt,
}: SessionSummaryPanelProps) {
    if (!session || !summary) {
        return (
            <article
                className="mt-4 rounded-xl border border-border/60 bg-card p-4"
                data-testid="consultant-verification-session-summary"
            >
                <p className="text-sm font-semibold text-foreground">Итог по сессии</p>
                <p className="mt-2 text-sm text-muted-foreground">
                    После первой проверки здесь появится короткая сводка: что консультант закрыл сам, где уточнял, где корректно передавал человеку и где выглядел слабо.
                </p>
            </article>
        );
    }

    return (
        <article
            className="mt-4 rounded-xl border border-border/60 bg-card p-4"
            data-testid="consultant-verification-session-summary"
        >
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <p className="text-sm font-semibold text-foreground">Итог по сессии</p>
                    <p className="mt-1 text-sm text-muted-foreground">{formatSessionTitle(session, index)}</p>
                </div>
                <span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                    Проверок: {summary.assistant_turns_total}
                </span>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2 xl:grid-cols-4">
                <div className={`rounded-xl border p-3 ${summaryCardClass("answered")}`} data-testid="consultant-verification-summary-answered">
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Ответил</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{summary.answered_total}</p>
                </div>
                <div className={`rounded-xl border p-3 ${summaryCardClass("clarify")}`} data-testid="consultant-verification-summary-clarify">
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Уточнял</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{summary.needs_clarification_total}</p>
                </div>
                <div className={`rounded-xl border p-3 ${summaryCardClass("handoff")}`} data-testid="consultant-verification-summary-handoff">
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Передал человеку</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{summary.handoff_total}</p>
                </div>
                <div className={`rounded-xl border p-3 ${summaryCardClass("gap")}`} data-testid="consultant-verification-summary-gap">
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Пробелы</p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">{summary.gap_detected_total}</p>
                </div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
                <button
                    type="button"
                    className="btn-ghost"
                    onClick={onReplayWholeSession}
                    disabled={isBusy || summary.replay_prompt_total === 0}
                    data-testid="consultant-verification-summary-replay-session"
                >
                    Повторить всю сессию
                </button>
                <button
                    type="button"
                    className="btn-ghost"
                    onClick={onReplayLastPrompt}
                    disabled={isBusy || !lastOwnerPrompt}
                    data-testid="consultant-verification-summary-replay-last"
                >
                    Повторить последний вопрос
                </button>
            </div>

            {summary.weak_turns.length > 0 ? (
                <div className="mt-4 space-y-2">
                    <p className="text-sm font-semibold text-foreground">Где система выглядела слабо</p>
                    {summary.weak_turns.map((weakTurn) => {
                        const verdict = getVerdictPresentation(weakTurn.business_verdict);
                        return (
                            <article
                                key={weakTurn.assistant_turn_id}
                                className="rounded-xl border border-rose-200 bg-rose-50/70 p-3"
                            >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${verdict.chipClass}`}>
                                        {verdict.label}
                                    </span>
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={() => {
                                            onReplayWeakPrompt(weakTurn.owner_prompt);
                                        }}
                                        disabled={isBusy}
                                        data-testid={`consultant-verification-summary-replay-weak-${weakTurn.assistant_turn_index}`}
                                    >
                                        Повторить вопрос
                                    </button>
                                </div>
                                <p className="mt-2 text-sm font-medium text-foreground">{weakTurn.owner_prompt}</p>
                                <p className="mt-1 text-sm text-muted-foreground">{weakTurn.assistant_excerpt}</p>
                            </article>
                        );
                    })}
                </div>
            ) : (
                <p className="mt-4 text-sm text-muted-foreground">
                    В этой сессии явных weak turns пока не найдено. Это не значит, что проверка исчерпана — можно прогнать готовые стресс-сценарии сверху.
                </p>
            )}
        </article>
    );
}
