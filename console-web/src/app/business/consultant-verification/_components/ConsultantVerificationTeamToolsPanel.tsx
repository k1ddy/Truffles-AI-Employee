"use client";

import type {
    ConsultantVerificationCompareCaseRecord,
    ConsultantVerificationCompareReadiness,
    ConsultantVerificationFindingRecord,
    ConsultantVerificationSessionRecord,
} from "@/lib/api-client";
import ConsoleSupportDisclosure from "@/components/ConsoleSupportDisclosure";

import ConsultantVerificationComparePanel from "./ConsultantVerificationComparePanel";
import ConsultantVerificationFindingsPanel from "./ConsultantVerificationFindingsPanel";
import {
    describeSessionLatest,
    formatSessionTitle,
    formatTimestamp,
} from "../_lib/presentation";

type ConsultantVerificationTeamToolsPanelProps = {
    defaultOpen: boolean;
    sessions: ConsultantVerificationSessionRecord[];
    sessionsLoading: boolean;
    sessionsError: boolean;
    selectedSessionId: string | null;
    selectedSessionIndex: number;
    onSelectSession: (sessionId: string) => void;
    compareReadiness: ConsultantVerificationCompareReadiness | null;
    compareCases: ConsultantVerificationCompareCaseRecord[];
    isBusy: boolean;
    canCompareLastPrompt: boolean;
    onCompareLastPrompt: () => void;
    findings: ConsultantVerificationFindingRecord[];
    onUpdateFindingStatus: (findingId: string, status: ConsultantVerificationFindingRecord["status"]) => void;
    onRetestFinding: (findingId: string) => void;
};

export default function ConsultantVerificationTeamToolsPanel({
    defaultOpen,
    sessions,
    sessionsLoading,
    sessionsError,
    selectedSessionId,
    selectedSessionIndex,
    onSelectSession,
    compareReadiness,
    compareCases,
    isBusy,
    canCompareLastPrompt,
    onCompareLastPrompt,
    findings,
    onUpdateFindingStatus,
    onRetestFinding,
}: ConsultantVerificationTeamToolsPanelProps) {
    const sessionItems = sessions ?? [];

    return (
        <ConsoleSupportDisclosure
            rootTestId="consultant-verification-team-tools"
            title="Инструменты команды"
            description="Повторные проверки, compare, findings и история сессий нужны не для первого прохода владельца бизнеса."
            defaultOpen={defaultOpen}
        >
            <div className="space-y-4">
                <article className="rounded-xl border border-border/60 bg-card p-4">
                    <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-semibold">Последние сессии</h3>
                        <span className="text-xs text-muted-foreground">{sessionItems.length}</span>
                    </div>
                    {sessionsLoading ? (
                        <p className="mt-3 text-sm text-muted-foreground">Загружаю сохраненные проверки...</p>
                    ) : null}
                    {sessionsError ? (
                        <p className="mt-3 text-sm text-rose-700">Не удалось загрузить список сессий. Обновите страницу.</p>
                    ) : null}
                    {!sessionsLoading && !sessionsError && sessionItems.length === 0 ? (
                        <p className="mt-3 text-sm text-muted-foreground">Сессии появятся после первой проверки.</p>
                    ) : (
                        <div className="mt-3 space-y-2">
                            {sessionItems.map((session, index) => (
                                <button
                                    key={session.id}
                                    type="button"
                                    className={`block w-full rounded-xl border px-3 py-3 text-left text-sm ${selectedSessionId === session.id ? "border-foreground bg-muted/30" : "border-border/60 hover:bg-muted/20"}`}
                                    onClick={() => {
                                        onSelectSession(session.id);
                                    }}
                                    data-testid={`consultant-verification-session-${index}`}
                                >
                                    <div className="flex items-center justify-between gap-2">
                                        <span className="font-medium text-foreground">{formatSessionTitle(session, index)}</span>
                                        <span className="text-[11px] text-muted-foreground">
                                            {index === selectedSessionIndex ? "Текущая" : `#${index + 1}`}
                                        </span>
                                    </div>
                                    <p className="mt-2 text-xs text-muted-foreground">{describeSessionLatest(session)}</p>
                                    <p className="mt-1 text-[11px] text-muted-foreground">
                                        Обновлено: {formatTimestamp(session.updated_at)}
                                    </p>
                                </button>
                            ))}
                        </div>
                    )}
                </article>

                <ConsultantVerificationComparePanel
                    readiness={compareReadiness}
                    cases={compareCases}
                    isBusy={isBusy}
                    canCompareLastPrompt={canCompareLastPrompt}
                    onCompareLastPrompt={onCompareLastPrompt}
                />

                <ConsultantVerificationFindingsPanel
                    findings={findings}
                    isBusy={isBusy}
                    onUpdateStatus={onUpdateFindingStatus}
                    onRetestFinding={onRetestFinding}
                />
            </div>
        </ConsoleSupportDisclosure>
    );
}
