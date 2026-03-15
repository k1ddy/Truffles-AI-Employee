"use client";

import type { ConsultantVerificationOverviewResponse } from "@/lib/api-client";

import ConsultantVerificationOwnerSetupLane from "./ConsultantVerificationOwnerSetupLane";
import ConsultantVerificationTranscriptLane from "./ConsultantVerificationTranscriptLane";
import ConsultantVerificationReviewLane from "./ConsultantVerificationReviewLane";
import { formatTimestamp } from "../_lib/presentation";
import { useConsultantVerificationWorkspaceState } from "../_hooks/useConsultantVerificationWorkspaceState";

type WorkspaceProps = {
    overview: ConsultantVerificationOverviewResponse;
    role: string;
};

export default function ConsultantVerificationWorkspace({ overview, role }: WorkspaceProps) {
    const {
        selectedSessionSummary,
        selectedSourceModeLabel,
        selectedChallengeModeLabel,
        ownerSetupLaneProps,
        transcriptLaneProps,
        reviewLaneProps,
    } = useConsultantVerificationWorkspaceState({ overview, role });

    return (
        <section className="mt-6" data-testid="consultant-verification-workspace">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                    <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Интерактивная проверка</p>
                    <h2 className="mt-1 text-lg font-semibold">Проверьте, как консультант отвечает на ваши сценарии</h2>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Тот же runtime, что и в production, но без реальных записей, handoff и исходящих сообщений.
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full border border-border px-3 py-1">
                        Данные: {selectedSourceModeLabel}
                    </span>
                    <span className="rounded-full border border-border px-3 py-1">
                        Режим: {selectedChallengeModeLabel}
                    </span>
                    {selectedSessionSummary ? (
                        <span className="rounded-full border border-border px-3 py-1">
                            Последний ответ: {formatTimestamp(selectedSessionSummary.last_message_at)}
                        </span>
                    ) : null}
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-[0.95fr_1.35fr_1fr]">
                <ConsultantVerificationOwnerSetupLane {...ownerSetupLaneProps} />
                <ConsultantVerificationTranscriptLane {...transcriptLaneProps} />
                <ConsultantVerificationReviewLane {...reviewLaneProps} />
            </div>
        </section>
    );
}
