"use client";

import type {
    ConsultantVerificationCompareCaseRecord,
    ConsultantVerificationCompareReadiness,
    ConsultantVerificationFindingRecord,
    ConsultantVerificationSessionListResponse,
    ConsultantVerificationSessionResponse,
    ConsultantVerificationTurnRecord,
} from "@/lib/api-client";

import ConsultantVerificationSessionSummaryPanel from "./ConsultantVerificationSessionSummaryPanel";
import ConsultantVerificationTeamToolsPanel from "./ConsultantVerificationTeamToolsPanel";
import {
    buildExplanationBlocks,
    getOutcomeLabel,
    getVerdictPresentation,
} from "../_lib/presentation";

type ConsultantVerificationReviewLaneProps = {
    inspectedTurn: ConsultantVerificationTurnRecord | null;
    selectedChallengeModeLabel: string;
    selectedSourceModeLabel: string;
    selectedSessionSummary: ConsultantVerificationSessionResponse["session"] | null;
    selectedSessionIndex: number;
    selectedSessionSummaryData: ConsultantVerificationSessionResponse["summary"] | null;
    isBusy: boolean;
    lastOwnerPrompt: string | null;
    onReplayLastPrompt: () => void;
    onReplayWholeSession: () => void;
    onReplayWeakPrompt: (prompt: string) => void;
    findingNote: string;
    onFindingNoteChange: (value: string) => void;
    teamToolsEnabled: boolean;
    onCreateFinding: () => void;
    createFindingPending: boolean;
    sessions: ConsultantVerificationSessionListResponse["items"];
    sessionsLoading: boolean;
    sessionsError: boolean;
    selectedSessionId: string | null;
    onSelectSession: (sessionId: string) => void;
    compareReadiness: ConsultantVerificationCompareReadiness | null;
    compareCases: ConsultantVerificationCompareCaseRecord[];
    canCompareLastPrompt: boolean;
    onCompareLastPrompt: () => void;
    findings: ConsultantVerificationFindingRecord[];
    onUpdateFindingStatus: (findingId: string, status: ConsultantVerificationFindingRecord["status"]) => void;
    onRetestFinding: (findingId: string) => void;
    defaultOpen: boolean;
};

export default function ConsultantVerificationReviewLane({
    inspectedTurn,
    selectedChallengeModeLabel,
    selectedSourceModeLabel,
    selectedSessionSummary,
    selectedSessionIndex,
    selectedSessionSummaryData,
    isBusy,
    lastOwnerPrompt,
    onReplayLastPrompt,
    onReplayWholeSession,
    onReplayWeakPrompt,
    findingNote,
    onFindingNoteChange,
    teamToolsEnabled,
    onCreateFinding,
    createFindingPending,
    sessions,
    sessionsLoading,
    sessionsError,
    selectedSessionId,
    onSelectSession,
    compareReadiness,
    compareCases,
    canCompareLastPrompt,
    onCompareLastPrompt,
    findings,
    onUpdateFindingStatus,
    onRetestFinding,
    defaultOpen,
}: ConsultantVerificationReviewLaneProps) {
    const inspectedTurnVerdict = getVerdictPresentation(inspectedTurn?.business_verdict ?? null);
    const explanationBlocks = buildExplanationBlocks(inspectedTurn);
    const sourceRefs = inspectedTurn?.source_refs ?? [];
    const technicalMeta = inspectedTurn?.decision_meta ?? null;
    const technicalTrace = inspectedTurn?.decision_trace ?? null;

    return (
        <aside>
            <div className="rounded-xl border border-border/60 bg-card p-4" data-testid="consultant-verification-explainer">
                <div className={`rounded-2xl border p-4 ${inspectedTurnVerdict.panelClass}`}>
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Вердикт по выбранному ответу</p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${inspectedTurnVerdict.chipClass}`}>
                            {inspectedTurnVerdict.label}
                        </span>
                        {inspectedTurn ? (
                            <span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                                {getOutcomeLabel(inspectedTurn.outcome)}
                            </span>
                        ) : null}
                    </div>
                    <p className="mt-3 text-sm text-foreground">{inspectedTurnVerdict.summary}</p>
                </div>

                <div className="mt-4 space-y-3">
                    {explanationBlocks.map((block) => (
                        <article key={block.id} className="rounded-xl border border-border/60 bg-muted/10 p-3">
                            <p className="text-sm font-semibold text-foreground">{block.title}</p>
                            <p className="mt-1 text-sm text-muted-foreground">{block.body}</p>
                        </article>
                    ))}
                </div>

                <article className="mt-4 rounded-xl border border-border/60 bg-muted/10 p-3">
                    <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-foreground">Источники ответа</p>
                        <span className="text-xs text-muted-foreground">{sourceRefs.length}</span>
                    </div>
                    {sourceRefs.length > 0 ? (
                        <div className="mt-3 flex flex-wrap gap-2">
                            {sourceRefs.map((sourceRef) => (
                                <span key={sourceRef} className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
                                    {sourceRef}
                                </span>
                            ))}
                        </div>
                    ) : (
                        <p className="mt-2 text-sm text-muted-foreground">
                            Явные source refs не попали в этот turn. Если это важный коммерческий вопрос, проверьте knowledge и повторите сценарий.
                        </p>
                    )}
                </article>

                <article className="mt-4 rounded-xl border border-border/60 bg-muted/10 p-3">
                    <p className="text-sm font-semibold text-foreground">Что это значит для реального клиента</p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        <span className="rounded-full border border-border px-2 py-0.5">Запись: {inspectedTurn?.would_book ? "только preview" : "не инициирована"}</span>
                        <span className="rounded-full border border-border px-2 py-0.5">Эскалация: {inspectedTurn?.would_handoff ? "только preview" : "не нужна"}</span>
                        <span className="rounded-full border border-border px-2 py-0.5">Пробел: {inspectedTurn?.gap_detected ? "да" : "нет"}</span>
                    </div>
                </article>

                {teamToolsEnabled ? (
                    <article className="mt-4 rounded-xl border border-border/60 bg-muted/10 p-3" data-testid="consultant-verification-flag-finding">
                        <p className="text-sm font-semibold text-foreground">Зафиксировать слабое место</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Если этот ответ выглядит слабым или подозрительным, превратите его в trackable finding с видимым статусом.
                        </p>
                        <textarea
                            value={findingNote}
                            onChange={(event) => onFindingNoteChange(event.target.value)}
                            rows={3}
                            className="mt-3 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none ring-0 transition focus:border-foreground"
                            placeholder="Коротко опишите, что именно выглядит плохо или почему владельцу это не понравится."
                            disabled={isBusy || !inspectedTurn}
                            data-testid="consultant-verification-finding-note"
                        />
                        <div className="mt-3 flex items-center justify-end">
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={onCreateFinding}
                                disabled={isBusy || !inspectedTurn}
                                data-testid="consultant-verification-create-finding"
                            >
                                {createFindingPending ? "Фиксирую..." : "Зафиксировать проблему"}
                            </button>
                        </div>
                    </article>
                ) : (
                    <article className="mt-4 rounded-xl border border-border/60 bg-muted/10 p-3" data-testid="consultant-verification-team-tools-note">
                        <p className="text-sm font-semibold text-foreground">Командные follow-up инструменты</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Preview-chat уже доступен. Compare, findings и remediation подключаются отдельно и не блокируют эту проверку.
                        </p>
                    </article>
                )}

                <details className="mt-4 rounded-xl border border-border/60 bg-muted/10 p-3" data-testid="consultant-verification-advanced-details">
                    <summary className="cursor-pointer text-sm font-semibold text-foreground">Детали для команды</summary>
                    <div className="mt-3 space-y-3 text-xs text-muted-foreground">
                        <div className="rounded-lg border border-border/60 bg-background/80 p-3">
                            <p className="font-semibold text-foreground">Контекст проверки</p>
                            <p className="mt-1">Версия данных: {selectedSourceModeLabel}</p>
                            <p className="mt-1">Режим: {selectedChallengeModeLabel}</p>
                            <p className="mt-1">Trace entries: {technicalTrace?.length ?? 0}</p>
                        </div>
                        {technicalMeta && Object.keys(technicalMeta).length > 0 ? (
                            <pre className="overflow-x-auto rounded-lg border border-border/60 bg-background/80 p-3 whitespace-pre-wrap">
                                {JSON.stringify(technicalMeta, null, 2)}
                            </pre>
                        ) : (
                            <p>Decision meta для этого turn пока не сохранен.</p>
                        )}
                    </div>
                </details>
            </div>

            <ConsultantVerificationSessionSummaryPanel
                session={selectedSessionSummary}
                summary={selectedSessionSummaryData}
                index={selectedSessionIndex >= 0 ? selectedSessionIndex : 0}
                isBusy={isBusy}
                lastOwnerPrompt={lastOwnerPrompt}
                onReplayLastPrompt={onReplayLastPrompt}
                onReplayWholeSession={onReplayWholeSession}
                onReplayWeakPrompt={onReplayWeakPrompt}
            />

            {teamToolsEnabled ? (
                <ConsultantVerificationTeamToolsPanel
                    defaultOpen={defaultOpen}
                    sessions={sessions}
                    sessionsLoading={sessionsLoading}
                    sessionsError={sessionsError}
                    selectedSessionId={selectedSessionId}
                    selectedSessionIndex={selectedSessionIndex >= 0 ? selectedSessionIndex : 0}
                    onSelectSession={onSelectSession}
                    compareReadiness={compareReadiness}
                    compareCases={compareCases}
                    isBusy={isBusy}
                    canCompareLastPrompt={canCompareLastPrompt}
                    onCompareLastPrompt={onCompareLastPrompt}
                    findings={findings}
                    onUpdateFindingStatus={(findingId, status) => onUpdateFindingStatus(findingId, status)}
                    onRetestFinding={onRetestFinding}
                />
            ) : null}
        </aside>
    );
}
