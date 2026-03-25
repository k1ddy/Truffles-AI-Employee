"use client";

import type { LearningCandidate } from "@/lib/api-client";

type KnowledgeLearningCandidatesPanelProps = {
    candidates: LearningCandidate[];
    isLoading: boolean;
    canEdit: boolean;
    approvePending: boolean;
    rejectPending: boolean;
    onApprove: (candidateId: string) => void;
    onReject: (candidateId: string) => void;
    formatTimestamp: (value?: string | null) => string;
};

export default function KnowledgeLearningCandidatesPanel({
    candidates,
    isLoading,
    canEdit,
    approvePending,
    rejectPending,
    onApprove,
    onReject,
    formatTimestamp,
}: KnowledgeLearningCandidatesPanelProps) {
    return (
        <div data-testid="learning-candidates">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                    <h2 className="text-lg font-semibold">Кандидаты обучения</h2>
                    <p className="text-sm text-muted-foreground">
                        Pending-кандидаты из ответов менеджера. Одобрение добавляет их в draft.
                    </p>
                </div>
                {!canEdit ? <span className="text-xs text-muted-foreground">Только owner/admin</span> : null}
            </div>

            {isLoading ? <p className="mt-4 text-sm text-muted-foreground">Загрузка кандидатов...</p> : null}
            {!isLoading && candidates.length === 0 ? (
                <p className="mt-4 text-sm text-muted-foreground">Пока нет pending-кандидатов.</p>
            ) : null}
            {!isLoading && candidates.length > 0 ? (
                <div className="mt-4 space-y-4">
                    {candidates.map((candidate) => (
                        <div
                            key={candidate.id ?? candidate.question_text}
                            className="rounded-lg border border-border/60 p-4"
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
                                <span>Статус: {candidate.status ?? "unknown"}</span>
                                <span>Создано: {formatTimestamp(candidate.created_at)}</span>
                                <span>Retention: {formatTimestamp(candidate.retention_expires_at)}</span>
                            </div>
                            <div className="mt-3 text-sm">
                                <div className="font-medium">Вопрос</div>
                                <div className="text-muted-foreground">{candidate.question_text}</div>
                            </div>
                            <div className="mt-3 text-sm">
                                <div className="font-medium">Ответ</div>
                                <div className="text-muted-foreground">{candidate.response_text}</div>
                            </div>
                            <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                <span>Источник: {candidate.source_name ?? "—"}</span>
                                <span>Роль: {candidate.source_role ?? "—"}</span>
                            </div>
                            <div className="mt-4 flex flex-wrap items-center gap-2">
                                <button
                                    type="button"
                                    className="btn-primary"
                                    onClick={() => {
                                        if (candidate.id) {
                                            onApprove(candidate.id);
                                        }
                                    }}
                                    disabled={!candidate.id || !canEdit || !candidate.can_approve || approvePending}
                                >
                                    {approvePending ? "Одобрение..." : "Одобрить"}
                                </button>
                                <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={() => {
                                        if (candidate.id) {
                                            onReject(candidate.id);
                                        }
                                    }}
                                    disabled={!candidate.id || !canEdit || rejectPending}
                                >
                                    {rejectPending ? "Отклонение..." : "Отклонить"}
                                </button>
                                {!candidate.can_approve && candidate.ineligible_reason ? (
                                    <span className="text-xs text-muted-foreground">Блокировка: {candidate.ineligible_reason}</span>
                                ) : null}
                            </div>
                        </div>
                    ))}
                </div>
            ) : null}
        </div>
    );
}
