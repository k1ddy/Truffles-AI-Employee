"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
    type ConsultantVerificationChallengeMode,
    type ConsultantVerificationCompareCaseRecord,
    type ConsultantVerificationCompareReadiness,
    type ConsultantVerificationFindingRecord,
    type ConsultantVerificationOverviewResponse,
    type ConsultantVerificationScenarioItem,
    type ConsultantVerificationSessionListResponse,
    type ConsultantVerificationSessionRecord,
    type ConsultantVerificationSessionResponse,
    type ConsultantVerificationSourceMode,
    businessApi,
} from "@/lib/api-client";
import { QUERY_PROFILE_DASHBOARD, keepPreviousData } from "@/lib/query-profiles";

import ConsultantVerificationOwnerSetupLane from "./ConsultantVerificationOwnerSetupLane";
import ConsultantVerificationTranscriptLane from "./ConsultantVerificationTranscriptLane";
import ConsultantVerificationReviewLane from "./ConsultantVerificationReviewLane";
import {
    buildReplayTitle,
    buildSessionTitle,
    formatTimestamp,
    getChallengeModeLabel,
    getSourceModeLabel,
} from "../_lib/presentation";

const SESSIONS_QUERY_KEY = ["business-consultant-verification-sessions"] as const;
const FINDINGS_QUERY_KEY = ["business-consultant-verification-findings"] as const;
const READINESS_QUERY_KEY = ["business-consultant-verification-readiness"] as const;

function extractErrorMessage(error: unknown, fallback: string): string {
    if (typeof error === "object" && error !== null) {
        const responseData = (error as { response?: { data?: { message?: string; detail?: string } } }).response?.data;
        if (responseData?.message) {
            return responseData.message;
        }
        if (responseData?.detail) {
            return responseData.detail;
        }
        const message = (error as { message?: string }).message;
        if (message) {
            return message;
        }
    }
    return fallback;
}

function mergeSessionIntoList(
    existing: ConsultantVerificationSessionListResponse | undefined,
    session: ConsultantVerificationSessionRecord,
): ConsultantVerificationSessionListResponse {
    const previousItems = existing?.items ?? [];
    const nextItems = [session, ...previousItems.filter((item) => item.id !== session.id)];
    nextItems.sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime());
    return { items: nextItems };
}

type WorkspaceProps = {
    overview: ConsultantVerificationOverviewResponse;
    role: string;
};

function shouldOpenTeamToolsByDefault(role: string): boolean {
    return role === "admin" || role === "platform_admin";
}

export default function ConsultantVerificationWorkspace({ overview, role }: WorkspaceProps) {
    const queryClient = useQueryClient();
    const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
    const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null);
    const [draft, setDraft] = useState("");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [lastSubmittedContent, setLastSubmittedContent] = useState<string>("");
    const [findingNote, setFindingNote] = useState("");
    const [selectedSourceMode, setSelectedSourceMode] = useState<ConsultantVerificationSourceMode>("live");
    const [selectedChallengeMode, setSelectedChallengeMode] = useState<ConsultantVerificationChallengeMode>("as_client");

    const sessionsQuery = useQuery({
        queryKey: SESSIONS_QUERY_KEY,
        queryFn: async () => {
            const response = await businessApi.listConsultantVerificationSessions();
            return response.data;
        },
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const selectedSessionQuery = useQuery({
        queryKey: ["business-consultant-verification-session", selectedSessionId],
        queryFn: async () => {
            const response = await businessApi.getConsultantVerificationSession(selectedSessionId as string);
            return response.data;
        },
        enabled: !!selectedSessionId,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const findingsQuery = useQuery({
        queryKey: FINDINGS_QUERY_KEY,
        queryFn: async () => {
            const response = await businessApi.listConsultantVerificationFindings({ limit: 12 });
            return response.data;
        },
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    const readinessQuery = useQuery({
        queryKey: READINESS_QUERY_KEY,
        queryFn: async () => {
            const response = await businessApi.getConsultantVerificationReadiness();
            return response.data;
        },
        refetchInterval: 30000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    useEffect(() => {
        const firstSession = sessionsQuery.data?.items[0];
        if (!selectedSessionId && firstSession) {
            setSelectedSessionId(firstSession.id);
        }
    }, [selectedSessionId, sessionsQuery.data]);

    useEffect(() => {
        const items = sessionsQuery.data?.items ?? [];
        if (!selectedSessionId) {
            return;
        }
        if (!items.some((item) => item.id === selectedSessionId)) {
            setSelectedSessionId(items[0]?.id ?? null);
        }
    }, [selectedSessionId, sessionsQuery.data]);

    const selectedSessionSummary = useMemo(() => {
        if (selectedSessionQuery.data?.session?.id === selectedSessionId) {
            return selectedSessionQuery.data.session;
        }
        return sessionsQuery.data?.items.find((item) => item.id === selectedSessionId) ?? null;
    }, [selectedSessionId, selectedSessionQuery.data, sessionsQuery.data]);

    useEffect(() => {
        if (!selectedSessionSummary) {
            return;
        }
        setSelectedSourceMode(selectedSessionSummary.source_mode);
        setSelectedChallengeMode(selectedSessionSummary.challenge_mode);
    }, [selectedSessionSummary]);

    const applySessionPayload = (payload: ConsultantVerificationSessionResponse) => {
        queryClient.setQueryData(["business-consultant-verification-session", payload.session.id], payload);
        queryClient.setQueryData<ConsultantVerificationSessionListResponse | undefined>(
            SESSIONS_QUERY_KEY,
            (existing) => mergeSessionIntoList(existing, payload.session),
        );
        setSelectedSessionId(payload.session.id);
        const lastAssistantTurn = [...payload.turns].reverse().find((turn) => turn.role !== "owner");
        setSelectedTurnId(lastAssistantTurn?.id ?? null);
    };

    const createSessionMutation = useMutation({
        mutationFn: async (variables?: {
            sourceMode?: ConsultantVerificationSourceMode;
            challengeMode?: ConsultantVerificationChallengeMode;
            title?: string;
        }) => {
            const response = await businessApi.createConsultantVerificationSession({
                source_mode: variables?.sourceMode ?? selectedSourceMode,
                challenge_mode: variables?.challengeMode ?? selectedChallengeMode,
                title:
                    variables?.title
                    ?? buildSessionTitle(
                        variables?.challengeMode ?? selectedChallengeMode,
                        variables?.sourceMode ?? selectedSourceMode,
                    ),
            });
            return response.data;
        },
        onSuccess: (payload) => {
            setErrorMessage(null);
            applySessionPayload(payload);
        },
        onError: (error) => {
            setErrorMessage(extractErrorMessage(error, "Не удалось создать новую проверку"));
        },
    });

    const sendMessageMutation = useMutation({
        mutationFn: async (variables: { sessionId: string; content: string }) => {
            const response = await businessApi.sendConsultantVerificationMessage(variables.sessionId, {
                content: variables.content,
            });
            return response.data;
        },
        onSuccess: (payload) => {
            setErrorMessage(null);
            applySessionPayload(payload);
            setDraft("");
        },
        onError: (error, variables) => {
            setLastSubmittedContent(variables.content);
            setErrorMessage(extractErrorMessage(error, "Не удалось отправить сообщение в проверку"));
        },
    });

    const replaySessionMutation = useMutation({
        mutationFn: async (variables: {
            prompts: string[];
            sourceMode: ConsultantVerificationSourceMode;
            challengeMode: ConsultantVerificationChallengeMode;
            title: string;
        }) => {
            let payload = (
                await businessApi.createConsultantVerificationSession({
                    source_mode: variables.sourceMode,
                    challenge_mode: variables.challengeMode,
                    title: variables.title,
                })
            ).data;
            for (const prompt of variables.prompts) {
                payload = (await businessApi.sendConsultantVerificationMessage(payload.session.id, { content: prompt })).data;
            }
            return payload;
        },
        onSuccess: (payload) => {
            setErrorMessage(null);
            applySessionPayload(payload);
            setDraft("");
        },
        onError: (error) => {
            setErrorMessage(extractErrorMessage(error, "Не удалось повторить выбранный сценарий"));
        },
    });

    const createFindingMutation = useMutation({
        mutationFn: async (variables: { assistantTurnId: string; ownerNote?: string }) => {
            const response = await businessApi.createConsultantVerificationFinding({
                assistant_turn_id: variables.assistantTurnId,
                owner_note: variables.ownerNote?.trim() ? variables.ownerNote.trim() : undefined,
            });
            return response.data;
        },
        onSuccess: async () => {
            setErrorMessage(null);
            setFindingNote("");
            await queryClient.invalidateQueries({ queryKey: FINDINGS_QUERY_KEY });
        },
        onError: (error) => {
            setErrorMessage(extractErrorMessage(error, "Не удалось зафиксировать слабое место"));
        },
    });

    const updateFindingMutation = useMutation({
        mutationFn: async (variables: { findingId: string; status: ConsultantVerificationFindingRecord["status"] }) => {
            const response = await businessApi.updateConsultantVerificationFinding(variables.findingId, {
                status: variables.status,
            });
            return response.data;
        },
        onSuccess: async () => {
            setErrorMessage(null);
            await queryClient.invalidateQueries({ queryKey: FINDINGS_QUERY_KEY });
        },
        onError: (error) => {
            setErrorMessage(extractErrorMessage(error, "Не удалось обновить статус слабого места"));
        },
    });

    const compareMutation = useMutation({
        mutationFn: async (variables: { prompt?: string; findingId?: string; markFindingRetested?: boolean }) => {
            const response = await businessApi.runConsultantVerificationCompare({
                prompt: variables.prompt,
                finding_id: variables.findingId,
                mark_finding_retested: variables.markFindingRetested ?? false,
            });
            return response.data;
        },
        onSuccess: async () => {
            setErrorMessage(null);
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: READINESS_QUERY_KEY }),
                queryClient.invalidateQueries({ queryKey: FINDINGS_QUERY_KEY }),
            ]);
        },
        onError: (error) => {
            setErrorMessage(extractErrorMessage(error, "Не удалось сравнить live и draft"));
        },
    });

    const selectedTurns = useMemo(
        () => (selectedSessionId ? selectedSessionQuery.data?.turns ?? [] : []),
        [selectedSessionId, selectedSessionQuery.data],
    );
    const assistantTurns = useMemo(
        () => selectedTurns.filter((turn) => turn.role !== "owner"),
        [selectedTurns],
    );
    const ownerTurns = useMemo(
        () => selectedTurns.filter((turn) => turn.role === "owner"),
        [selectedTurns],
    );

    useEffect(() => {
        if (!assistantTurns.length) {
            setSelectedTurnId(null);
            return;
        }
        if (selectedTurnId && assistantTurns.some((turn) => turn.id === selectedTurnId)) {
            return;
        }
        setSelectedTurnId(assistantTurns[assistantTurns.length - 1]?.id ?? null);
    }, [assistantTurns, selectedTurnId]);

    const inspectedTurn = useMemo(() => {
        if (!assistantTurns.length) {
            return null;
        }
        if (selectedTurnId) {
            return assistantTurns.find((turn) => turn.id === selectedTurnId) ?? assistantTurns[assistantTurns.length - 1];
        }
        return assistantTurns[assistantTurns.length - 1];
    }, [assistantTurns, selectedTurnId]);

    const selectedSessionIndex = useMemo(
        () => sessionsQuery.data?.items.findIndex((item) => item.id === selectedSessionSummary?.id) ?? 0,
        [selectedSessionSummary?.id, sessionsQuery.data],
    );
    const findings = findingsQuery.data?.items ?? [];
    const compareCases: ConsultantVerificationCompareCaseRecord[] = compareMutation.data?.cases ?? [];
    const compareReadiness: ConsultantVerificationCompareReadiness | null =
        compareMutation.data?.readiness ?? readinessQuery.data?.readiness ?? null;
    const lastOwnerPrompt = ownerTurns[ownerTurns.length - 1]?.content ?? null;
    const scenarioCatalog = overview.scenario_catalog ?? [];
    const stressTestExamples = overview.stress_test_examples ?? [];
    const selectedSourceModeLabel = getSourceModeLabel(selectedSessionSummary?.source_mode ?? selectedSourceMode);
    const selectedChallengeModeLabel = getChallengeModeLabel(selectedSessionSummary?.challenge_mode ?? selectedChallengeMode);
    const isBusy = createSessionMutation.isPending
        || sendMessageMutation.isPending
        || replaySessionMutation.isPending
        || createFindingMutation.isPending
        || updateFindingMutation.isPending
        || compareMutation.isPending;

    const ensureSession = async (): Promise<string | null> => {
        if (selectedSessionId) {
            return selectedSessionId;
        }
        const payload = await createSessionMutation.mutateAsync(undefined);
        return payload.session.id;
    };

    const runReplay = async (
        prompts: string[],
        options: {
            sourceMode: ConsultantVerificationSourceMode;
            challengeMode: ConsultantVerificationChallengeMode;
            title: string;
        },
    ) => {
        const normalizedPrompts = prompts.map((prompt) => prompt.trim()).filter(Boolean);
        if (!normalizedPrompts.length) {
            return;
        }
        setLastSubmittedContent(normalizedPrompts[normalizedPrompts.length - 1] ?? "");
        setErrorMessage(null);
        try {
            await replaySessionMutation.mutateAsync({
                prompts: normalizedPrompts,
                sourceMode: options.sourceMode,
                challengeMode: options.challengeMode,
                title: options.title,
            });
        } catch {
            // Mutation handlers already surface a human-readable error banner.
        }
    };

    const handleSend = async () => {
        const normalizedDraft = draft.trim();
        if (!normalizedDraft) {
            return;
        }
        setErrorMessage(null);
        setLastSubmittedContent(normalizedDraft);
        try {
            const sessionId = await ensureSession();
            if (!sessionId) {
                return;
            }
            await sendMessageMutation.mutateAsync({ sessionId, content: normalizedDraft });
        } catch {
            // Mutation handlers already surface a human-readable error banner.
        }
    };

    const handleRunScenario = async (scenario: ConsultantVerificationScenarioItem) => {
        await runReplay([scenario.prompt], {
            sourceMode: selectedSourceMode,
            challengeMode: scenario.recommended_challenge_mode,
            title: buildReplayTitle(scenario.title, selectedSourceMode, scenario.recommended_challenge_mode),
        });
    };

    const handleReplayLastPrompt = async () => {
        if (!lastOwnerPrompt) {
            return;
        }
        await runReplay([lastOwnerPrompt], {
            sourceMode: selectedSessionSummary?.source_mode ?? selectedSourceMode,
            challengeMode: selectedSessionSummary?.challenge_mode ?? selectedChallengeMode,
            title: buildReplayTitle(
                "Повтор последнего вопроса",
                selectedSessionSummary?.source_mode ?? selectedSourceMode,
                selectedSessionSummary?.challenge_mode ?? selectedChallengeMode,
            ),
        });
    };

    const handleReplayWholeSession = async () => {
        await runReplay(
            ownerTurns.map((turn) => turn.content),
            {
                sourceMode: selectedSessionSummary?.source_mode ?? selectedSourceMode,
                challengeMode: selectedSessionSummary?.challenge_mode ?? selectedChallengeMode,
                title: buildReplayTitle(
                    "Replay сессии",
                    selectedSessionSummary?.source_mode ?? selectedSourceMode,
                    selectedSessionSummary?.challenge_mode ?? selectedChallengeMode,
                ),
            },
        );
    };

    const handleCreateFinding = async () => {
        if (!inspectedTurn?.id) {
            return;
        }
        setErrorMessage(null);
        try {
            await createFindingMutation.mutateAsync({
                assistantTurnId: inspectedTurn.id,
                ownerNote: findingNote,
            });
        } catch {
            // Mutation handlers already surface a human-readable error banner.
        }
    };

    const handleCompareLastPrompt = async () => {
        if (!lastOwnerPrompt) {
            return;
        }
        setErrorMessage(null);
        try {
            await compareMutation.mutateAsync({ prompt: lastOwnerPrompt });
        } catch {
            // Mutation handlers already surface a human-readable error banner.
        }
    };

    const handleRetestFinding = async (findingId: string) => {
        setErrorMessage(null);
        try {
            await compareMutation.mutateAsync({
                findingId,
                markFindingRetested: true,
            });
        } catch {
            // Mutation handlers already surface a human-readable error banner.
        }
    };

    const currentPlaceholder =
        selectedChallengeMode === "stress"
            ? "Попробуйте каверзный вопрос, смешанный сценарий или проверку на эскалацию."
            : "Напишите так, как написал бы реальный клиент вашего бизнеса.";
    const quickPrompts = scenarioCatalog.length > 0
        ? scenarioCatalog.slice(0, 4).map((item) => item.prompt)
        : stressTestExamples.slice(0, 4);
    const teamToolsDefaultOpen = shouldOpenTeamToolsByDefault(role);

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
                <ConsultantVerificationOwnerSetupLane
                    selectedSourceMode={selectedSourceMode}
                    selectedChallengeMode={selectedChallengeMode}
                    selectedSessionSummary={selectedSessionSummary}
                    isBusy={isBusy}
                    createSessionPending={createSessionMutation.isPending}
                    onResetSelection={() => {
                        setSelectedSessionId(null);
                        setSelectedTurnId(null);
                        setDraft("");
                        setErrorMessage(null);
                    }}
                    onSelectSourceMode={setSelectedSourceMode}
                    onSelectChallengeMode={setSelectedChallengeMode}
                    onStartSession={() => {
                        void (async () => {
                            try {
                                await createSessionMutation.mutateAsync(undefined);
                            } catch {
                                // Mutation handlers already surface a human-readable error banner.
                            }
                        })();
                    }}
                    scenarios={scenarioCatalog}
                    onFillPrompt={setDraft}
                    onRunScenario={(scenario) => {
                        void handleRunScenario(scenario);
                    }}
                />

                <ConsultantVerificationTranscriptLane
                    selectedSessionSummary={selectedSessionSummary}
                    selectedTurns={selectedTurns}
                    selectedTurnId={selectedTurnId}
                    onSelectTurn={setSelectedTurnId}
                    quickPrompts={quickPrompts}
                    onQuickPrompt={setDraft}
                    errorMessage={errorMessage}
                    lastSubmittedContent={lastSubmittedContent}
                    onRetryDraft={() => {
                        setDraft(lastSubmittedContent);
                    }}
                    selectedSessionLoading={selectedSessionQuery.isLoading}
                    selectedSessionError={Boolean(selectedSessionQuery.error)}
                    selectedSessionId={selectedSessionId}
                    isSending={sendMessageMutation.isPending}
                    isReplaying={replaySessionMutation.isPending}
                    draft={draft}
                    onDraftChange={setDraft}
                    onSend={() => {
                        void handleSend();
                    }}
                    currentPlaceholder={currentPlaceholder}
                />

                <ConsultantVerificationReviewLane
                    inspectedTurn={inspectedTurn}
                    selectedChallengeModeLabel={selectedChallengeModeLabel}
                    selectedSourceModeLabel={selectedSourceModeLabel}
                    selectedSessionSummary={selectedSessionSummary}
                    selectedSessionIndex={selectedSessionIndex >= 0 ? selectedSessionIndex : 0}
                    selectedSessionSummaryData={selectedSessionQuery.data?.summary ?? null}
                    isBusy={isBusy}
                    lastOwnerPrompt={lastOwnerPrompt}
                    onReplayLastPrompt={() => {
                        void handleReplayLastPrompt();
                    }}
                    onReplayWholeSession={() => {
                        void handleReplayWholeSession();
                    }}
                    onReplayWeakPrompt={(prompt) => {
                        void runReplay([prompt], {
                            sourceMode: selectedSessionSummary?.source_mode ?? selectedSourceMode,
                            challengeMode: selectedSessionSummary?.challenge_mode ?? selectedChallengeMode,
                            title: buildReplayTitle(
                                "Replay слабого вопроса",
                                selectedSessionSummary?.source_mode ?? selectedSourceMode,
                                selectedSessionSummary?.challenge_mode ?? selectedChallengeMode,
                            ),
                        });
                    }}
                    findingNote={findingNote}
                    onFindingNoteChange={setFindingNote}
                    onCreateFinding={() => {
                        void handleCreateFinding();
                    }}
                    createFindingPending={createFindingMutation.isPending}
                    sessions={sessionsQuery.data?.items ?? []}
                    sessionsLoading={sessionsQuery.isLoading}
                    sessionsError={Boolean(sessionsQuery.error)}
                    selectedSessionId={selectedSessionId}
                    onSelectSession={(sessionId) => {
                        setSelectedSessionId(sessionId);
                        setErrorMessage(null);
                    }}
                    compareReadiness={compareReadiness}
                    compareCases={compareCases}
                    canCompareLastPrompt={Boolean(lastOwnerPrompt)}
                    onCompareLastPrompt={() => {
                        void handleCompareLastPrompt();
                    }}
                    findings={findings}
                    onUpdateFindingStatus={(findingId, status) => {
                        void updateFindingMutation.mutateAsync({ findingId, status });
                    }}
                    onRetestFinding={(findingId) => {
                        void handleRetestFinding(findingId);
                    }}
                    defaultOpen={teamToolsDefaultOpen}
                />
            </div>
        </section>
    );
}
