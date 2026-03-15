import { useMemo, useState } from "react";

import type { ConsultantVerificationFindingRecord } from "@/lib/api-client";

import { formatTimestamp, getFindingStatusPresentation } from "../_lib/presentation";

type FindingsPanelProps = {
    findings: ConsultantVerificationFindingRecord[];
    isBusy: boolean;
    onUpdateStatus: (findingId: string, status: ConsultantVerificationFindingRecord["status"]) => void;
    onRetestFinding: (findingId: string) => void;
};

const STATUS_OPTIONS: ConsultantVerificationFindingRecord["status"][] = [
    "new",
    "in_review",
    "needs_data",
    "fixed",
    "retested",
];

export default function ConsultantVerificationFindingsPanel({
    findings,
    isBusy,
    onUpdateStatus,
    onRetestFinding,
}: FindingsPanelProps) {
    const [draftStatuses, setDraftStatuses] = useState<Record<string, ConsultantVerificationFindingRecord["status"]>>({});
    const findingItems = findings ?? [];

    const emptyState = useMemo(
        () => (
            <p className="mt-2 text-sm text-muted-foreground">
                Когда владелец зафиксирует слабый ответ, здесь появится его статус, repeat count и связь с remediation.
            </p>
        ),
        [],
    );

    return (
        <article
            className="mt-4 rounded-xl border border-border/60 bg-card p-4"
            data-testid="consultant-verification-findings"
        >
            <div className="flex items-start justify-between gap-3">
                <div>
                    <p className="text-sm font-semibold text-foreground">Найденные слабые места</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Это уже не просто чат: найденные проблемные ответы попадают в trackable remediation loop.
                    </p>
                </div>
                <span className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground">
                    {findingItems.length}
                </span>
            </div>

            {findingItems.length === 0 ? emptyState : null}

            <div className="mt-3 space-y-3">
                {findingItems.map((finding) => {
                    const status = draftStatuses[finding.id] ?? finding.status;
                    const statusPresentation = getFindingStatusPresentation(finding.status);
                    return (
                        <article
                            key={finding.id}
                            className="rounded-xl border border-border/60 bg-muted/10 p-3"
                            data-testid={`consultant-verification-finding-${finding.id}`}
                        >
                            <div className="flex flex-wrap items-start justify-between gap-2">
                                <div>
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusPresentation.chipClass}`}>
                                            {finding.status_label}
                                        </span>
                                        <span className="rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">
                                            Повторов: {finding.repeat_count}
                                        </span>
                                    </div>
                                    <p className="mt-2 text-sm font-semibold text-foreground">{finding.family_label}</p>
                                    <p className="mt-1 text-sm text-muted-foreground">{finding.owner_prompt}</p>
                                </div>
                                <p className="text-[11px] text-muted-foreground">
                                    Обновлено: {formatTimestamp(finding.updated_at)}
                                </p>
                            </div>

                            <p className="mt-2 rounded-lg border border-border/60 bg-background/80 px-3 py-2 text-sm text-foreground">
                                {finding.assistant_excerpt}
                            </p>

                            <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                                {finding.linked_knowledge_backlog_id ? (
                                    <span className="rounded-full border border-border px-2 py-0.5">
                                        Backlog: {finding.linked_knowledge_backlog_id.slice(0, 8)}
                                    </span>
                                ) : null}
                                {finding.linked_learning_candidate_id ? (
                                    <span className="rounded-full border border-border px-2 py-0.5">
                                        Learning: {finding.linked_learning_candidate_id.slice(0, 8)}
                                    </span>
                                ) : null}
                                {finding.decision_reason_code ? (
                                    <span className="rounded-full border border-border px-2 py-0.5">
                                        Reason: {finding.decision_reason_code}
                                    </span>
                                ) : null}
                            </div>

                            <div className="mt-3 flex flex-wrap items-center gap-2">
                                <select
                                    value={status}
                                    onChange={(event) => {
                                        setDraftStatuses((current) => ({
                                            ...current,
                                            [finding.id]: event.target.value as ConsultantVerificationFindingRecord["status"],
                                        }));
                                    }}
                                    className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
                                    disabled={isBusy}
                                    data-testid={`consultant-verification-finding-status-${finding.id}`}
                                >
                                    {STATUS_OPTIONS.map((item) => (
                                        <option key={item} value={item}>
                                            {getFindingStatusPresentation(item).label}
                                        </option>
                                    ))}
                                </select>
                                <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={() => {
                                        onUpdateStatus(finding.id, status);
                                    }}
                                    disabled={isBusy || status === finding.status}
                                    data-testid={`consultant-verification-finding-apply-${finding.id}`}
                                >
                                    Обновить статус
                                </button>
                                <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={() => {
                                        onRetestFinding(finding.id);
                                    }}
                                    disabled={isBusy}
                                    data-testid={`consultant-verification-finding-retest-${finding.id}`}
                                >
                                    Проверить в draft
                                </button>
                            </div>
                        </article>
                    );
                })}
            </div>
        </article>
    );
}
