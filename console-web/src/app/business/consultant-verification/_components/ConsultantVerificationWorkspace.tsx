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
    type ConsultantVerificationTurnRecord,
    businessApi,
} from "@/lib/api-client";
import { QUERY_PROFILE_DASHBOARD, keepPreviousData } from "@/lib/query-profiles";

import ConsultantVerificationScenarioLibrary from "./ConsultantVerificationScenarioLibrary";
import ConsultantVerificationComparePanel from "./ConsultantVerificationComparePanel";
import ConsultantVerificationFindingsPanel from "./ConsultantVerificationFindingsPanel";
import ConsultantVerificationSessionSummaryPanel from "./ConsultantVerificationSessionSummaryPanel";
import {
    buildExplanationBlocks,
    buildReplayTitle,
    buildSessionTitle,
    buildTurnSignals,
    describeSessionLatest,
    formatSessionTitle,
    formatTimestamp,
    getChallengeModeLabel,
    getOutcomeLabel,
    getSourceModeLabel,
    getVerdictPresentation,
    roleLabel,
} from "../_lib/presentation";

const SESSIONS_QUERY_KEY = ["business-consultant-verification-sessions"] as const;
const FINDINGS_QUERY_KEY = ["business-consultant-verification-findings"] as const;
const READINESS_QUERY_KEY = ["business-consultant-verification-readiness"] as const;

function sourceModeButtonClass(active: boolean): string {
    return active
        ? "border-foreground bg-foreground text-background"
        : "border-border bg-background text-foreground hover:bg-muted/40";
}

function challengeModeButtonClass(active: boolean): string {
    return active
        ? "border-foreground bg-foreground text-background"
        : "border-border bg-background text-foreground hover:bg-muted/40";
}

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
};

export default function ConsultantVerificationWorkspace({ overview }: WorkspaceProps) {
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
    const inspectedTurnVerdict = getVerdictPresentation(inspectedTurn?.business_verdict);
    const explanationBlocks = buildExplanationBlocks(inspectedTurn);
    const sourceRefs = inspectedTurn?.source_refs ?? [];
    const technicalMeta = inspectedTurn?.decision_meta as Record<string, unknown> | undefined;
    const technicalTrace = inspectedTurn?.decision_trace as unknown[] | undefined;
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
    const quickPrompts = overview.scenario_catalog.length > 0
        ? overview.scenario_catalog.slice(0, 4).map((item) => item.prompt)
        : overview.stress_test_examples.slice(0, 4);

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
                <aside className="space-y-4">
                    <article className="rounded-xl border border-border/60 bg-card p-4">
                        <div className="flex items-start justify-between gap-3">
                            <div>
                                <p className="text-sm font-semibold text-foreground">Новая проверка</p>
                                <p className="mt-1 text-sm text-muted-foreground">
                                    Выберите, как именно хотите атаковать систему, и начните отдельную сессию.
                                </p>
                            </div>
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={() => {
                                    setSelectedSessionId(null);
                                    setSelectedTurnId(null);
                                    setDraft("");
                                    setErrorMessage(null);
                                }}
                                data-testid="consultant-verification-reset-session"
                            >
                                Сбросить выбор
                            </button>
                        </div>

                        <div className="mt-4">
                            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                Версия данных
                            </p>
                            <div className="mt-2 flex flex-wrap gap-2">
                                {(["live", "draft"] as const).map((mode) => (
                                    <button
                                        key={mode}
                                        type="button"
                                        onClick={() => {
                                            setSelectedSourceMode(mode);
                                        }}
                                        className={`rounded-full border px-3 py-1.5 text-sm font-medium ${sourceModeButtonClass(selectedSourceMode === mode)}`}
                                        data-testid={`consultant-verification-source-${mode}`}
                                    >
                                        {getSourceModeLabel(mode)}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="mt-4">
                            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                Способ проверки
                            </p>
                            <div className="mt-2 space-y-2">
                                {(["as_client", "stress"] as const).map((mode) => (
                                    <button
                                        key={mode}
                                        type="button"
                                        onClick={() => {
                                            setSelectedChallengeMode(mode);
                                        }}
                                        className={`w-full rounded-xl border p-3 text-left ${challengeModeButtonClass(selectedChallengeMode === mode)}`}
                                        data-testid={`consultant-verification-mode-${mode}`}
                                    >
                                        <p className="text-sm font-semibold">{getChallengeModeLabel(mode)}</p>
                                        <p className="mt-1 text-xs opacity-80">
                                            {mode === "stress"
                                                ? "Провоцируйте сложные, смешанные и неудобные сценарии."
                                                : "Пишите так, как будто вы обычный клиент бизнеса."}
                                        </p>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <button
                            type="button"
                            className="btn-ghost mt-4 w-full"
                            onClick={() => {
                                void (async () => {
                                    try {
                                        await createSessionMutation.mutateAsync(undefined);
                                    } catch {
                                        // Mutation handlers already surface a human-readable error banner.
                                    }
                                })();
                            }}
                            disabled={isBusy}
                            data-testid="consultant-verification-start-session"
                        >
                            {createSessionMutation.isPending ? "Создаю сессию..." : "Начать новую проверку"}
                        </button>
                    </article>

                    <ConsultantVerificationScenarioLibrary
                        scenarios={overview.scenario_catalog}
                        isBusy={isBusy}
                        onFillPrompt={(prompt) => {
                            setDraft(prompt);
                        }}
                        onRunScenario={(scenario) => {
                            void handleRunScenario(scenario);
                        }}
                    />

                    <article
                        className="rounded-xl border border-border/60 bg-card p-4"
                        data-testid="consultant-verification-session-list"
                    >
                        <div className="flex items-center justify-between gap-2">
                            <h3 className="text-sm font-semibold">Последние сессии</h3>
                            <span className="text-xs text-muted-foreground">{sessionsQuery.data?.items.length ?? 0}</span>
                        </div>

                        {sessionsQuery.isLoading ? (
                            <p className="mt-3 text-sm text-muted-foreground">Загружаю сохраненные проверки...</p>
                        ) : null}

                        {sessionsQuery.error ? (
                            <p className="mt-3 text-sm text-rose-700">Не удалось загрузить список сессий. Обновите страницу.</p>
                        ) : null}

                        {!sessionsQuery.isLoading && (sessionsQuery.data?.items.length ?? 0) === 0 ? (
                            <p className="mt-3 text-sm text-muted-foreground">
                                Сессий пока нет. Можно сразу написать свой вопрос в центре — новая сессия создастся автоматически.
                            </p>
                        ) : null}

                        <div className="mt-3 space-y-2">
                            {(sessionsQuery.data?.items ?? []).map((session, index) => {
                                const verdict = getVerdictPresentation(session.latest_business_verdict);
                                const isSelected = selectedSessionId === session.id;
                                return (
                                    <button
                                        key={session.id}
                                        type="button"
                                        onClick={() => {
                                            setSelectedSessionId(session.id);
                                            setErrorMessage(null);
                                        }}
                                        className={`w-full rounded-xl border p-3 text-left transition ${
                                            isSelected
                                                ? "border-foreground bg-muted/40"
                                                : "border-border/60 bg-muted/10 hover:bg-muted/20"
                                        }`}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div>
                                                <p className="text-sm font-semibold text-foreground">
                                                    {formatSessionTitle(session, index)}
                                                </p>
                                                <p className="mt-1 text-xs text-muted-foreground">
                                                    {getChallengeModeLabel(session.challenge_mode)} • {getSourceModeLabel(session.source_mode)}
                                                </p>
                                            </div>
                                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${verdict.chipClass}`}>
                                                {verdict.label}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-xs text-muted-foreground">{describeSessionLatest(session)}</p>
                                        <p className="mt-1 text-[11px] text-muted-foreground">
                                            Обновлено: {formatTimestamp(session.updated_at)}
                                        </p>
                                    </button>
                                );
                            })}
                        </div>
                    </article>
                </aside>

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
                                onClick={() => {
                                    setDraft(example);
                                }}
                                data-testid={`consultant-verification-quick-prompt-${index}`}
                            >
                                {example}
                            </button>
                        ))}
                    </div>

                    {errorMessage ? (
                        <div
                            className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-800"
                            data-testid="consultant-verification-composer-error"
                        >
                            <p>{errorMessage}</p>
                            {lastSubmittedContent ? (
                                <button
                                    type="button"
                                    className="mt-2 text-xs font-semibold underline underline-offset-4"
                                    onClick={() => {
                                        setDraft(lastSubmittedContent);
                                    }}
                                    data-testid="consultant-verification-retry-draft"
                                >
                                    Вернуть последний вопрос в поле ввода
                                </button>
                            ) : null}
                        </div>
                    ) : null}

                    <div className="mt-4 space-y-3" data-testid="consultant-verification-transcript-list">
                        {selectedSessionQuery.isLoading && selectedSessionId ? (
                            <p className="text-sm text-muted-foreground">Загружаю сообщения этой проверки...</p>
                        ) : null}

                        {selectedSessionQuery.error && selectedSessionId ? (
                            <p className="text-sm text-rose-700">Не удалось загрузить выбранную сессию. Попробуйте выбрать ее заново.</p>
                        ) : null}

                        {!selectedSessionId && !selectedTurns.length ? (
                            <div
                                className="rounded-2xl border border-dashed border-border bg-muted/10 px-4 py-6 text-sm text-muted-foreground"
                                data-testid="consultant-verification-empty-state"
                            >
                                <p className="font-semibold text-foreground">Здесь появится диалог с консультантом</p>
                                <p className="mt-2">
                                    Напишите первый вопрос. Если сессии еще нет, она создастся автоматически в выбранном режиме.
                                </p>
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
                                            <p className="text-xs font-semibold uppercase tracking-[0.14em] opacity-75">
                                                {roleLabel(turn.role)}
                                            </p>
                                            <p className="mt-1 whitespace-pre-wrap text-sm leading-6">{turn.content}</p>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-[11px] opacity-75">{formatTimestamp(turn.created_at)}</p>
                                            {turn.role !== "owner" ? (
                                                <div className="mt-2 flex flex-wrap justify-end gap-1">
                                                    <span
                                                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${verdict.chipClass}`}
                                                        data-testid="consultant-verification-turn-verdict"
                                                    >
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
                                    <div
                                        key={turn.id}
                                        className={`block w-full rounded-2xl border p-4 text-left ${transcriptBubbleClass(turn, isActive)}`}
                                        data-testid={`consultant-verification-turn-${turn.turn_index}`}
                                    >
                                        {content}
                                    </div>
                                );
                            }
                            return (
                                <button
                                    key={turn.id}
                                    type="button"
                                    onClick={() => {
                                        setSelectedTurnId(turn.id);
                                    }}
                                    className={`block w-full rounded-2xl border p-4 text-left ${transcriptBubbleClass(turn, isActive)}`}
                                    data-testid={`consultant-verification-turn-${turn.turn_index}`}
                                >
                                    {content}
                                </button>
                            );
                        })}

                        {sendMessageMutation.isPending || replaySessionMutation.isPending ? (
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
                            onChange={(event) => {
                                setDraft(event.target.value);
                            }}
                            onKeyDown={(event) => {
                                if (event.key === "Enter" && !event.shiftKey) {
                                    event.preventDefault();
                                    void handleSend();
                                }
                            }}
                            rows={4}
                            className="mt-2 w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none ring-0 transition focus:border-foreground"
                            placeholder={currentPlaceholder}
                            disabled={isBusy}
                            data-testid="consultant-verification-composer-input"
                        />
                        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                            <p className="text-xs text-muted-foreground">
                                Сессия создается автоматически при первой отправке, если вы еще не выбрали сохраненную проверку.
                            </p>
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={() => {
                                    void handleSend();
                                }}
                                disabled={isBusy || !draft.trim()}
                                data-testid="consultant-verification-send"
                            >
                                {sendMessageMutation.isPending ? "Отправляю..." : "Отправить в проверку"}
                            </button>
                        </div>
                    </div>
                </article>

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
                                        <span
                                            key={sourceRef}
                                            className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground"
                                        >
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
                                <span className="rounded-full border border-border px-2 py-0.5">
                                    Запись: {inspectedTurn?.would_book ? "только preview" : "не инициирована"}
                                </span>
                                <span className="rounded-full border border-border px-2 py-0.5">
                                    Эскалация: {inspectedTurn?.would_handoff ? "только preview" : "не нужна"}
                                </span>
                                <span className="rounded-full border border-border px-2 py-0.5">
                                    Пробел: {inspectedTurn?.gap_detected ? "да" : "нет"}
                                </span>
                            </div>
                        </article>

                        <article className="mt-4 rounded-xl border border-border/60 bg-muted/10 p-3" data-testid="consultant-verification-flag-finding">
                            <p className="text-sm font-semibold text-foreground">Зафиксировать слабое место</p>
                            <p className="mt-1 text-sm text-muted-foreground">
                                Если этот ответ выглядит слабым или подозрительным, превратите его в trackable finding с видимым статусом.
                            </p>
                            <textarea
                                value={findingNote}
                                onChange={(event) => {
                                    setFindingNote(event.target.value);
                                }}
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
                                    onClick={() => {
                                        void handleCreateFinding();
                                    }}
                                    disabled={isBusy || !inspectedTurn}
                                    data-testid="consultant-verification-create-finding"
                                >
                                    {createFindingMutation.isPending ? "Фиксирую..." : "Зафиксировать проблему"}
                                </button>
                            </div>
                        </article>

                        <details className="mt-4 rounded-xl border border-border/60 bg-muted/10 p-3" data-testid="consultant-verification-advanced-details">
                            <summary className="cursor-pointer text-sm font-semibold text-foreground">
                                Детали для команды
                            </summary>
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
                        summary={selectedSessionQuery.data?.summary ?? null}
                        index={selectedSessionIndex >= 0 ? selectedSessionIndex : 0}
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
                    />

                    <ConsultantVerificationComparePanel
                        readiness={compareReadiness}
                        cases={compareCases}
                        isBusy={isBusy}
                        canCompareLastPrompt={Boolean(lastOwnerPrompt)}
                        onCompareLastPrompt={() => {
                            void handleCompareLastPrompt();
                        }}
                    />

                    <ConsultantVerificationFindingsPanel
                        findings={findings}
                        isBusy={isBusy}
                        onUpdateStatus={(findingId, status) => {
                            void updateFindingMutation.mutateAsync({ findingId, status });
                        }}
                        onRetestFinding={(findingId) => {
                            void handleRetestFinding(findingId);
                        }}
                    />
                </aside>
            </div>
        </section>
    );
}
