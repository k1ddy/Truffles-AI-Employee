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

import {
    buildReplayTitle,
    buildSessionTitle,
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

function shouldOpenTeamToolsByDefault(role: string): boolean {
    return role === "admin" || role === "platform_admin";
}

type UseConsultantVerificationWorkspaceStateParams = {
    overview: ConsultantVerificationOverviewResponse;
    role: string;
};

export function useConsultantVerificationWorkspaceState({ overview, role }: UseConsultantVerificationWorkspaceStateParams) {
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

    return {
        selectedSessionSummary,
        selectedSourceModeLabel,
        selectedChallengeModeLabel,
        ownerSetupLaneProps: {
            selectedSourceMode,
            selectedChallengeMode,
            selectedSessionSummary,
            isBusy,
            createSessionPending: createSessionMutation.isPending,
            onResetSelection: () => {
                setSelectedSessionId(null);
                setSelectedTurnId(null);
                setDraft("");
                setErrorMessage(null);
            },
            onSelectSourceMode: setSelectedSourceMode,
            onSelectChallengeMode: setSelectedChallengeMode,
            onStartSession: () => {
                void (async () => {
                    try {
                        await createSessionMutation.mutateAsync(undefined);
                    } catch {
                        // Mutation handlers already surface a human-readable error banner.
                    }
                })();
            },
            scenarios: scenarioCatalog,
            onFillPrompt: setDraft,
            onRunScenario: (scenario: ConsultantVerificationScenarioItem) => {
                void handleRunScenario(scenario);
            },
        },
        transcriptLaneProps: {
            selectedSessionSummary,
            selectedTurns,
            selectedTurnId,
            onSelectTurn: setSelectedTurnId,
            quickPrompts,
            onQuickPrompt: setDraft,
            errorMessage,
            lastSubmittedContent,
            onRetryDraft: () => {
                setDraft(lastSubmittedContent);
            },
            selectedSessionLoading: selectedSessionQuery.isLoading,
            selectedSessionError: Boolean(selectedSessionQuery.error),
            selectedSessionId,
            isSending: sendMessageMutation.isPending,
            isReplaying: replaySessionMutation.isPending,
            draft,
            onDraftChange: setDraft,
            onSend: () => {
                void handleSend();
            },
            currentPlaceholder,
        },
        reviewLaneProps: {
            inspectedTurn,
            selectedChallengeModeLabel,
            selectedSourceModeLabel,
            selectedSessionSummary,
            selectedSessionIndex: selectedSessionIndex >= 0 ? selectedSessionIndex : 0,
            selectedSessionSummaryData: selectedSessionQuery.data?.summary ?? null,
            isBusy,
            lastOwnerPrompt,
            onReplayLastPrompt: () => {
                void handleReplayLastPrompt();
            },
            onReplayWholeSession: () => {
                void handleReplayWholeSession();
            },
            onReplayWeakPrompt: (prompt: string) => {
                void runReplay([prompt], {
                    sourceMode: selectedSessionSummary?.source_mode ?? selectedSourceMode,
                    challengeMode: selectedSessionSummary?.challenge_mode ?? selectedChallengeMode,
                    title: buildReplayTitle(
                        "Replay слабого вопроса",
                        selectedSessionSummary?.source_mode ?? selectedSourceMode,
                        selectedSessionSummary?.challenge_mode ?? selectedChallengeMode,
                    ),
                });
            },
            findingNote,
            onFindingNoteChange: setFindingNote,
            onCreateFinding: () => {
                void handleCreateFinding();
            },
            createFindingPending: createFindingMutation.isPending,
            sessions: sessionsQuery.data?.items ?? [],
            sessionsLoading: sessionsQuery.isLoading,
            sessionsError: Boolean(sessionsQuery.error),
            selectedSessionId,
            onSelectSession: (sessionId: string) => {
                setSelectedSessionId(sessionId);
                setErrorMessage(null);
            },
            compareReadiness,
            compareCases,
            canCompareLastPrompt: Boolean(lastOwnerPrompt),
            onCompareLastPrompt: () => {
                void handleCompareLastPrompt();
            },
            findings,
            onUpdateFindingStatus: (findingId: string, status: ConsultantVerificationFindingRecord["status"]) => {
                void updateFindingMutation.mutateAsync({ findingId, status });
            },
            onRetestFinding: (findingId: string) => {
                void handleRetestFinding(findingId);
            },
            defaultOpen: shouldOpenTeamToolsByDefault(role),
        },
    };
}
