"use client";

import type {
    ConsultantVerificationSessionResponse,
    ConsultantVerificationTurnRecord,
} from "@/lib/api-client";

import {
    buildTurnSignals,
    formatSessionTitle,
    formatTimestamp,
    getChallengeModeLabel,
    getOutcomeLabel,
    getSourceModeLabel,
    getVerdictPresentation,
    roleLabel,
} from "../_lib/presentation";

function transcriptBubbleClass(turn: ConsultantVerificationTurnRecord, active: boolean): string {
    if (turn.role === "owner") {
        return active
            ? "border-slate-400 bg-slate-900 text-white"
            : "border-slate-300 bg-slate-800 text-white";
    }
    if (turn.business_verdict === "gap_detected") {
        return active ? "border-rose-300 bg-rose-50" : "border-rose-200 bg-rose-50/60";
    }
    if (turn.business_verdict === "handoff") {
        return active ? "border-amber-300 bg-amber-50" : "border-amber-200 bg-amber-50/60";
    }
    if (turn.business_verdict === "needs_clarification") {
        return active ? "border-sky-300 bg-sky-50" : "border-sky-200 bg-sky-50/60";
    }
    return active ? "border-emerald-300 bg-emerald-50" : "border-border bg-muted/10";
}

type ConsultantVerificationTranscriptLaneProps = {
    selectedSessionSummary: ConsultantVerificationSessionResponse["session"] | null;
    selectedTurns: ConsultantVerificationTurnRecord[];
    selectedTurnId: string | null;
    onSelectTurn: (turnId: string) => void;
    quickPrompts: string[];
    onQuickPrompt: (prompt: string) => void;
    errorMessage: string | null;
    lastSubmittedContent: string;
    onRetryDraft: () => void;
    selectedSessionLoading: boolean;
    selectedSessionError: boolean;
    selectedSessionId: string | null;
    isSending: boolean;
    isReplaying: boolean;
    draft: string;
    onDraftChange: (value: string) => void;
    onSend: () => void;
    currentPlaceholder: string;
};

export default function ConsultantVerificationTranscriptLane({
    selectedSessionSummary,
    selectedTurns,
    selectedTurnId,
    onSelectTurn,
    quickPrompts,
    onQuickPrompt,
    errorMessage,
    lastSubmittedContent,
    onRetryDraft,
    selectedSessionLoading,
    selectedSessionError,
    selectedSessionId,
    isSending,
    isReplaying,
    draft,
    onDraftChange,
    onSend,
    currentPlaceholder,
}: ConsultantVerificationTranscriptLaneProps) {
    return (
        <article className="rounded-xl border border-border/60 bg-card p-4" data-testid="consultant-verification-transcript">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h3 className="text-base font-semibold text-foreground">Чат проверки</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                        {selectedSessionSummary
                            ? `${getChallengeModeLabel(selectedSessionSummary.challenge_mode)} • ${getSourceModeLabel(selectedSessionSummary.source_mode)}`
                            : "Сначала выберите режим или просто начните писать свой вопрос."}
                    </p>
                </div>
                {selectedSessionSummary ? (
                    <span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                        {formatSessionTitle(selectedSessionSummary, 0)}
                    </span>
                ) : null}
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
                {quickPrompts.map((example, index) => (
                    <button
                        key={`${example}-${index}`}
                        type="button"
                        className="rounded-full border border-border px-3 py-1.5 text-left text-xs text-muted-foreground hover:bg-muted/30"
                        onClick={() => onQuickPrompt(example)}
                        data-testid={`consultant-verification-quick-prompt-${index}`}
                    >
                        {example}
                    </button>
                ))}
            </div>

            {errorMessage ? (
                <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-800" data-testid="consultant-verification-composer-error">
                    <p>{errorMessage}</p>
                    {lastSubmittedContent ? (
                        <button
                            type="button"
                            className="mt-2 text-xs font-semibold underline underline-offset-4"
                            onClick={onRetryDraft}
                            data-testid="consultant-verification-retry-draft"
                        >
                            Вернуть последний вопрос в поле ввода
                        </button>
                    ) : null}
                </div>
            ) : null}

            <div className="mt-4 space-y-3" data-testid="consultant-verification-transcript-list">
                {selectedSessionLoading && selectedSessionId ? <p className="text-sm text-muted-foreground">Загружаю сообщения этой проверки...</p> : null}
                {selectedSessionError && selectedSessionId ? <p className="text-sm text-rose-700">Не удалось загрузить выбранную сессию. Попробуйте выбрать ее заново.</p> : null}
                {!selectedSessionId && !selectedTurns.length ? (
                    <div className="rounded-2xl border border-dashed border-border bg-muted/10 px-4 py-6 text-sm text-muted-foreground" data-testid="consultant-verification-empty-state">
                        <p className="font-semibold text-foreground">Здесь появится диалог с консультантом</p>
                        <p className="mt-2">Напишите первый вопрос. Если сессии еще нет, она создастся автоматически в выбранном режиме.</p>
                        <p className="mt-2">Главное правило: проверяйте честно и неудобно, а не только happy-path.</p>
                    </div>
                ) : null}

                {selectedTurns.map((turn) => {
                    const verdict = getVerdictPresentation(turn.business_verdict);
                    const isActive = turn.id === selectedTurnId;
                    const selectable = turn.role !== "owner";
                    const turnSignalItems = buildTurnSignals(turn);
                    const content = (
                        <>
                            <div className="flex flex-wrap items-start justify-between gap-2">
                                <div>
                                    <p className="text-xs font-semibold uppercase tracking-[0.14em] opacity-75">{roleLabel(turn.role)}</p>
                                    <p className="mt-1 whitespace-pre-wrap text-sm leading-6">{turn.content}</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-[11px] opacity-75">{formatTimestamp(turn.created_at)}</p>
                                    {turn.role !== "owner" ? (
                                        <div className="mt-2 flex flex-wrap justify-end gap-1">
                                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${verdict.chipClass}`} data-testid="consultant-verification-turn-verdict">
                                                {verdict.label}
                                            </span>
                                            <span className="rounded-full border border-current/20 px-2 py-0.5 text-[10px] font-semibold opacity-80">
                                                {getOutcomeLabel(turn.outcome)}
                                            </span>
                                        </div>
                                    ) : null}
                                </div>
                            </div>

                            {turn.role !== "owner" && turnSignalItems.length > 0 ? (
                                <div className="mt-3 flex flex-wrap gap-2 text-[11px] opacity-80">
                                    {turnSignalItems.map((signal) => (
                                        <span key={signal} className="rounded-full border border-current/15 px-2 py-0.5">
                                            {signal}
                                        </span>
                                    ))}
                                </div>
                            ) : null}
                        </>
                    );

                    if (!selectable) {
                        return (
                            <div key={turn.id} className={`block w-full rounded-2xl border p-4 text-left ${transcriptBubbleClass(turn, isActive)}`} data-testid={`consultant-verification-turn-${turn.turn_index}`}>
                                {content}
                            </div>
                        );
                    }

                    return (
                        <button
                            key={turn.id}
                            type="button"
                            onClick={() => onSelectTurn(turn.id)}
                            className={`block w-full rounded-2xl border p-4 text-left ${transcriptBubbleClass(turn, isActive)}`}
                            data-testid={`consultant-verification-turn-${turn.turn_index}`}
                        >
                            {content}
                        </button>
                    );
                })}

                {isSending || isReplaying ? (
                    <div className="rounded-2xl border border-border/60 bg-muted/10 px-4 py-3 text-sm text-muted-foreground">
                        Консультант формирует ответ в simulation mode...
                    </div>
                ) : null}
            </div>

            <div className="mt-4 rounded-xl border border-border/60 bg-muted/10 p-3" data-testid="consultant-verification-composer">
                <label className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground" htmlFor="consultant-verification-draft">
                    Ваш вопрос
                </label>
                <textarea
                    id="consultant-verification-draft"
                    value={draft}
                    onChange={(event) => onDraftChange(event.target.value)}
                    onKeyDown={(event) => {
                        if (event.key === "Enter" && !event.shiftKey) {
                            event.preventDefault();
                            onSend();
                        }
                    }}
                    rows={4}
                    className="mt-2 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none ring-0 transition focus:border-foreground"
                    placeholder={currentPlaceholder}
                    disabled={isSending || isReplaying}
                    data-testid="consultant-verification-composer-input"
                />
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs text-muted-foreground">Сессия создается автоматически при первой отправке, если вы еще не выбрали сохраненную проверку.</p>
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={onSend}
                        disabled={isSending || isReplaying || !draft.trim()}
                        data-testid="consultant-verification-send"
                    >
                        {isSending ? "Отправляю..." : "Отправить в проверку"}
                    </button>
                </div>
            </div>
        </article>
    );
}
