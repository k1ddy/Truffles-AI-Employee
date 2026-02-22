"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import CaseList from "@/components/CaseList";
import CaseConversation from "@/components/CaseConversation";
import CaseDetailsPanel from "@/components/CaseDetailsPanel";
import { InboxMacroChips } from "@/components/InboxMacros";
import AccessDenied from "@/components/AccessDenied";
import { useCaseData } from "@/hooks/useCaseData";
import { authApi, canAccessConsole, outreachApi } from "@/lib/api-client";
import {
    buildInboxWorkspaceScope,
    readInboxSelectedCase,
    writeInboxSelectedCase,
} from "@/lib/inbox-workspace";
import toast from "react-hot-toast";

interface InboxViewProps {
    initialCaseId?: string | null;
}

export default function InboxView({ initialCaseId }: InboxViewProps) {
    const router = useRouter();
    const pathname = usePathname();
    const { data: session } = useSession();
    const queryClient = useQueryClient();
    const [selectedCaseId, setSelectedCaseId] = useState(initialCaseId ?? "");
    const [draft, setDraft] = useState("");
    const [detailsOpen, setDetailsOpen] = useState(false);
    const [visibleCaseIds, setVisibleCaseIds] = useState<string[]>([]);
    const [selectionHydrated, setSelectionHydrated] = useState(Boolean(initialCaseId));
    const restoredScopeRef = useRef<string | null>(null);
    const [standaloneOutreachOpen, setStandaloneOutreachOpen] = useState(false);
    const [standaloneOutreachDestination, setStandaloneOutreachDestination] = useState("");
    const [standaloneOutreachContent, setStandaloneOutreachContent] = useState("");
    const [standaloneOutreachBranchId, setStandaloneOutreachBranchId] = useState("");
    const [standalonePauseEnabled, setStandalonePauseEnabled] = useState(true);
    const [standalonePauseMinutes, setStandalonePauseMinutes] = useState(30);

    const { data: meData } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadInbox = canAccessConsole(role, "inbox", "read");
    const canWriteInbox = canAccessConsole(role, "inbox", "write");
    const canReadOutreach = canAccessConsole(role, "outreach", "read");
    const canWriteOutreach = canAccessConsole(role, "outreach", "write");
    const branches = useMemo(
        () => (meData?.branches ?? []) as { id?: string; name?: string }[],
        [meData?.branches],
    );
    const selectedBranchId = meData?.selected_branch_id ?? "";
    const isPrivileged = role === "owner" || role === "admin" || role === "platform_admin";
    const showBranchFilter = isPrivileged && branches.length > 1 && !selectedBranchId;
    const showStandaloneBranchSelect = !selectedBranchId && branches.length > 1;
    const workspaceScope = useMemo(
        () =>
            buildInboxWorkspaceScope({
                role,
                agentId: meData?.agent?.id,
                clientId: meData?.client?.id,
                branchId: selectedBranchId || meData?.agent?.branch_id,
            }),
        [role, meData?.agent?.id, meData?.agent?.branch_id, meData?.client?.id, selectedBranchId],
    );

    useEffect(() => {
        if (workspaceScope && restoredScopeRef.current !== workspaceScope) {
            setSelectionHydrated(false);
        }
    }, [workspaceScope]);

    useEffect(() => {
        if (initialCaseId) {
            setSelectedCaseId(initialCaseId);
            if (workspaceScope) {
                restoredScopeRef.current = workspaceScope;
            }
            setSelectionHydrated(true);
        }
    }, [initialCaseId, workspaceScope]);

    useEffect(() => {
        if (!workspaceScope || initialCaseId || restoredScopeRef.current === workspaceScope) {
            return;
        }
        const restoredCaseId = readInboxSelectedCase(workspaceScope);
        if (restoredCaseId) {
            setSelectedCaseId(restoredCaseId);
            router.replace(`/cases/${restoredCaseId}`);
        }
        restoredScopeRef.current = workspaceScope;
        setSelectionHydrated(true);
    }, [workspaceScope, initialCaseId, router]);

    useEffect(() => {
        if (!workspaceScope || !selectionHydrated) {
            return;
        }
        writeInboxSelectedCase(workspaceScope, selectedCaseId || null);
    }, [workspaceScope, selectionHydrated, selectedCaseId]);

    useEffect(() => {
        setDraft("");
        setDetailsOpen(false);
    }, [selectedCaseId]);

    useEffect(() => {
        if (selectedBranchId) {
            setStandaloneOutreachBranchId(selectedBranchId);
            return;
        }
        const defaultBranch = branches.find((branch) => branch.id)?.id ?? "";
        setStandaloneOutreachBranchId((prev) => prev || defaultBranch);
    }, [branches, selectedBranchId]);

    useEffect(() => {
        if (!workspaceScope) {
            return;
        }
        if (visibleCaseIds.length === 0) {
            return;
        }
        if (initialCaseId && selectedCaseId === initialCaseId && pathname === `/cases/${initialCaseId}`) {
            return;
        }
        const selectedVisible = selectedCaseId ? visibleCaseIds.includes(selectedCaseId) : false;
        if (selectedVisible) {
            return;
        }
        const preferred = readInboxSelectedCase(workspaceScope);
        const nextCaseId = preferred && visibleCaseIds.includes(preferred) ? preferred : visibleCaseIds[0];
        if (!nextCaseId) {
            return;
        }
        setSelectedCaseId(nextCaseId);
        if (pathname !== `/cases/${nextCaseId}`) {
            router.replace(`/cases/${nextCaseId}`);
        }
    }, [workspaceScope, visibleCaseIds, initialCaseId, selectedCaseId, pathname, router]);

    const {
        caseDetail,
        caseLoading,
        caseError,
        refetchCase,
        messages,
        messagesLoading,
        messagesHasMore,
        messagesLoadingMore,
        loadMoreMessages,
    } = useCaseData(selectedCaseId);

    const canSend = Boolean(caseDetail && caseDetail.status === "active" && canWriteInbox);
    const canViewDiagnostics = role === "support" || role === "platform_admin" || role === "owner" || role === "admin";
    const macroBranchId = caseDetail?.branch_id ?? selectedBranchId;
    const canManageMacros = canWriteInbox;
    const canToggleDetails = Boolean(selectedCaseId && caseDetail && !caseLoading && !caseError);
    const showDetailsColumn = detailsOpen && !!selectedCaseId;
    const hasSelection = Boolean(selectedCaseId);
    const gridClass = showDetailsColumn
        ? hasSelection
            ? "xl:grid-cols-[220px_minmax(0,1fr)_320px]"
            : "xl:grid-cols-[280px_minmax(0,1fr)_320px]"
        : hasSelection
            ? "xl:grid-cols-[220px_minmax(0,1fr)]"
            : "xl:grid-cols-[280px_minmax(0,1fr)]";

    const handleSelectCase = (caseId: string) => {
        setSelectedCaseId(caseId);
        router.push(`/cases/${caseId}`);
    };

    const nextCaseId = useMemo(() => {
        if (!selectedCaseId || visibleCaseIds.length === 0) {
            return null;
        }
        const currentIndex = visibleCaseIds.indexOf(selectedCaseId);
        if (currentIndex < 0) {
            return visibleCaseIds[0] ?? null;
        }
        if (currentIndex === visibleCaseIds.length - 1) {
            return visibleCaseIds[0] ?? null;
        }
        return visibleCaseIds[currentIndex + 1] ?? null;
    }, [selectedCaseId, visibleCaseIds]);

    const handleNextCase = () => {
        if (!nextCaseId || nextCaseId === selectedCaseId) {
            return;
        }
        setSelectedCaseId(nextCaseId);
        router.replace(`/cases/${nextCaseId}`);
    };

    const handleMacroSelect = (text: string) => {
        setDraft((prev) => (prev.trim() ? `${prev}\n${text}` : text));
    };

    const handleToggleDetails = () => {
        if (!canToggleDetails) {
            return;
        }
        setDetailsOpen((prev) => !prev);
    };

    const standaloneOutreachMutation = useMutation({
        mutationFn: async () => {
            const response = await outreachApi.sendMessage({
                destination: standaloneOutreachDestination.trim(),
                content: standaloneOutreachContent.trim(),
                conversation_id: null,
                branch_id: selectedBranchId || standaloneOutreachBranchId || null,
                pause_bot_minutes: standalonePauseEnabled ? standalonePauseMinutes : 0,
                pause_reason: standalonePauseEnabled ? "manual_pause" : null,
            });
            return response.data;
        },
        onSuccess: (response) => {
            if (!response.success) {
                const suffix = response.error_code ? ` (${response.error_code})` : "";
                toast.error(`Не удалось отправить сообщение${suffix}`);
                return;
            }
            if (response.delivery_status === "queued") {
                toast.success("Сообщение поставлено в очередь");
            } else {
                toast.success("Сообщение отправлено");
            }
            setStandaloneOutreachContent("");
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "INTEGRATION_UNAVAILABLE") {
                toast.error("Интеграция WhatsApp не настроена для выбранного филиала");
                return;
            }
            if (code === "BRANCH_SELECTION_REQUIRED") {
                toast.error("Выберите филиал для отправки");
                return;
            }
            toast.error("Не удалось отправить сообщение");
        },
    });

    const renderEmptyPane = (title: string, subtitle: string) => (
        <div className="card-surface p-6 text-center text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">{title}</p>
            <p>{subtitle}</p>
        </div>
    );

    const renderErrorPane = () => (
        <div className="card-surface p-6 text-center text-sm text-destructive">
            <p className="mb-4">Не удалось загрузить заявку</p>
            <button
                onClick={() => refetchCase()}
                className="btn-ghost"
                data-testid="case-retry"
            >
                Повторить
            </button>
        </div>
    );

    const renderLoadingPane = () => (
        <div className="card-surface p-6 animate-pulse text-sm text-muted-foreground">
            Загрузка...
        </div>
    );

    const composerBefore = (
        <InboxMacroChips
            onSelect={handleMacroSelect}
            disabled={!selectedCaseId || !canSend}
            canManage={canManageMacros}
            branchId={macroBranchId}
        />
    );

    if (!canReadInbox) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к заявкам." />
        );
    }

    return (
        <div className="flex h-full min-h-0 flex-col gap-4" data-testid="inbox-view">
            <div>
                <h1 className="text-2xl font-semibold">Заявки</h1>
                <p className="text-sm text-muted-foreground">
                    Очередь слева, чат по центру, детали по кнопке. Фильтры и последняя заявка сохраняются на 24 часа.
                </p>
            </div>

            {canWriteOutreach && (
                <section className="card-surface p-4" data-testid="inbox-standalone-outreach">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <p className="text-sm font-semibold">Сообщение без заявки</p>
                            <p className="text-xs text-muted-foreground">
                                Используйте, когда нужно написать клиенту до появления чата в очереди.
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => setStandaloneOutreachOpen((prev) => !prev)}
                            className="rounded border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                            data-testid="inbox-standalone-outreach-toggle"
                        >
                            {standaloneOutreachOpen ? "Свернуть" : "Открыть"}
                        </button>
                    </div>

                    {standaloneOutreachOpen && (
                        <div className="mt-3 grid gap-3">
                            {showStandaloneBranchSelect && (
                                <label className="space-y-1">
                                    <span className="text-xs text-muted-foreground">Филиал</span>
                                    <select
                                        value={standaloneOutreachBranchId}
                                        onChange={(event) => setStandaloneOutreachBranchId(event.target.value)}
                                        className="w-full rounded border border-border/60 bg-background px-3 py-2 text-sm"
                                        data-testid="inbox-standalone-outreach-branch"
                                    >
                                        <option value="">Выберите филиал</option>
                                        {branches
                                            .filter((branch) => Boolean(branch.id))
                                            .map((branch) => (
                                                <option key={branch.id} value={branch.id}>
                                                    {branch.name || branch.id}
                                                </option>
                                            ))}
                                    </select>
                                </label>
                            )}

                            <label className="space-y-1">
                                <span className="text-xs text-muted-foreground">WhatsApp номер или JID</span>
                                <input
                                    type="text"
                                    value={standaloneOutreachDestination}
                                    onChange={(event) => setStandaloneOutreachDestination(event.target.value)}
                                    className="w-full rounded border border-border/60 bg-background px-3 py-2 text-sm"
                                    placeholder="+7 777 123 45 67"
                                    data-testid="inbox-standalone-outreach-destination"
                                />
                            </label>

                            <label className="space-y-1">
                                <span className="text-xs text-muted-foreground">Сообщение</span>
                                <textarea
                                    value={standaloneOutreachContent}
                                    onChange={(event) => setStandaloneOutreachContent(event.target.value)}
                                    rows={3}
                                    className="w-full resize-y rounded border border-border/60 bg-background px-3 py-2 text-sm"
                                    placeholder="Например: Мы на связи, можем продолжить общение здесь"
                                    data-testid="inbox-standalone-outreach-message"
                                />
                            </label>

                            <div className="grid gap-2 md:grid-cols-[auto_140px_1fr] md:items-center">
                                <label className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <input
                                        type="checkbox"
                                        checked={standalonePauseEnabled}
                                        onChange={(event) => setStandalonePauseEnabled(event.target.checked)}
                                        className="h-4 w-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                        data-testid="inbox-standalone-outreach-pause-enabled"
                                    />
                                    Пауза бота после отправки
                                </label>
                                <input
                                    type="number"
                                    min={0}
                                    max={1440}
                                    value={standalonePauseMinutes}
                                    onChange={(event) => {
                                        const next = Number(event.target.value);
                                        const normalized = Number.isFinite(next)
                                            ? Math.min(Math.max(next, 0), 1440)
                                            : 0;
                                        setStandalonePauseMinutes(normalized);
                                    }}
                                    disabled={!standalonePauseEnabled}
                                    className="w-full rounded border border-border/60 bg-background px-3 py-2 text-sm"
                                    data-testid="inbox-standalone-outreach-pause-minutes"
                                />
                                <button
                                    type="button"
                                    onClick={() => {
                                        const destination = standaloneOutreachDestination.trim();
                                        const message = standaloneOutreachContent.trim();
                                        if (!destination || !message) {
                                            toast.error("Заполните номер и текст сообщения");
                                            return;
                                        }
                                        if (showStandaloneBranchSelect && !standaloneOutreachBranchId) {
                                            toast.error("Выберите филиал");
                                            return;
                                        }
                                        standaloneOutreachMutation.mutate();
                                    }}
                                    disabled={standaloneOutreachMutation.isPending}
                                    className="rounded bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-50"
                                    data-testid="inbox-standalone-outreach-send"
                                >
                                    {standaloneOutreachMutation.isPending ? "Отправка..." : "Отправить"}
                                </button>
                            </div>
                        </div>
                    )}
                </section>
            )}

            <div
                className={`grid flex-1 min-h-0 grid-cols-1 gap-4 ${gridClass}`}
            >
                <section className="card-surface flex h-full min-h-0 flex-col p-4 xl:overflow-hidden" data-testid="inbox-list">
                    <CaseList
                        variant="compact"
                        selectedCaseId={selectedCaseId}
                        onSelectCase={handleSelectCase}
                        branches={branches}
                        showBranchFilter={showBranchFilter}
                        workspaceScope={workspaceScope}
                        onCaseIdsChange={setVisibleCaseIds}
                    />
                </section>

                <section className="flex h-full min-h-0 flex-col gap-4" data-testid="inbox-conversation">
                    {!selectedCaseId && renderEmptyPane("Выберите заявку", "Кликните по карточке слева, чтобы открыть диалог.")}
                    {selectedCaseId && (
                        <div className="flex min-h-0 flex-1 flex-col gap-4">
                            {caseLoading && renderLoadingPane()}
                            {caseError && renderErrorPane()}
                            {!caseLoading && !caseError && caseDetail && (
                                <div className="card-surface flex min-h-0 flex-1 flex-col overflow-hidden">
                                    <CaseConversation
                                        caseDetail={caseDetail}
                                        caseId={selectedCaseId}
                                        messages={messages}
                                        messagesLoading={messagesLoading}
                                        messagesHasMore={messagesHasMore}
                                        messagesLoadingMore={messagesLoadingMore}
                                        onLoadMoreMessages={loadMoreMessages}
                                        canSend={canSend}
                                        canWrite={canWriteInbox}
                                        canOutreach={canWriteOutreach}
                                        canReadOutreach={canReadOutreach}
                                        draft={draft}
                                        onDraftChange={setDraft}
                                        composerBefore={composerBefore}
                                        detailsOpen={detailsOpen}
                                        onToggleDetails={handleToggleDetails}
                                        onNextCase={handleNextCase}
                                        canGoNextCase={Boolean(nextCaseId && nextCaseId !== selectedCaseId)}
                                        chatFrame="plain"
                                        layout="inbox"
                                    />
                                </div>
                            )}
                            {!caseLoading && !caseError && !caseDetail && (
                                <div className="card-surface p-6 text-center text-muted-foreground">
                                    Заявка не найдена
                                </div>
                            )}
                        </div>
                    )}
                </section>

                {showDetailsColumn && (
                    <section className="hidden h-full min-h-0 flex-col gap-4 overflow-y-auto xl:flex" data-testid="inbox-details">
                        {!selectedCaseId && renderEmptyPane("Детали", "Выберите заявку, чтобы увидеть контекст и trace.")}
                        {selectedCaseId && (
                            <div className="flex flex-col gap-4" data-testid="case-details">
                                {caseLoading && renderLoadingPane()}
                                {caseError && renderErrorPane()}
                                {!caseLoading && !caseError && caseDetail && (
                                    <>
                                        <div className="sticky top-0 z-10 flex items-center justify-between rounded-2xl border border-border/60 bg-background/90 px-4 py-3 backdrop-blur">
                                            <p className="text-sm font-semibold">Детали заявки</p>
                                            <button
                                                type="button"
                                                onClick={() => setDetailsOpen(false)}
                                                className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                            >
                                                Скрыть детали
                                            </button>
                                        </div>
                                        <CaseDetailsPanel
                                            caseDetail={caseDetail}
                                            messages={messages}
                                            canViewDiagnostics={canViewDiagnostics}
                                        />
                                    </>
                                )}
                                {!caseLoading && !caseError && !caseDetail && (
                                    <div className="card-surface p-6 text-center text-muted-foreground">
                                        Детали недоступны
                                    </div>
                                )}
                            </div>
                        )}
                    </section>
                )}
            </div>

            {detailsOpen && canToggleDetails && caseDetail && (
                <div className="fixed inset-0 z-40 xl:hidden">
                    <div
                        className="absolute inset-0 bg-foreground/20"
                        onClick={() => setDetailsOpen(false)}
                        aria-hidden="true"
                    />
                    <div className="absolute inset-y-0 right-0 flex h-full w-full max-w-[420px] flex-col gap-3 overflow-y-auto bg-background p-4 shadow-xl">
                        <div className="flex items-center justify-between">
                            <p className="text-sm font-semibold">Детали заявки</p>
                            <button
                                type="button"
                                onClick={() => setDetailsOpen(false)}
                                className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                            >
                                Скрыть детали
                            </button>
                        </div>
                        <CaseDetailsPanel
                            caseDetail={caseDetail}
                            messages={messages}
                            canViewDiagnostics={canViewDiagnostics}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}
