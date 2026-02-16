"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import CaseList from "@/components/CaseList";
import CaseConversation from "@/components/CaseConversation";
import CaseDetailsPanel from "@/components/CaseDetailsPanel";
import { InboxMacroChips } from "@/components/InboxMacros";
import AccessDenied from "@/components/AccessDenied";
import { useCaseData } from "@/hooks/useCaseData";
import { authApi, canAccessConsole } from "@/lib/api-client";

interface InboxViewProps {
    initialCaseId?: string | null;
}

export default function InboxView({ initialCaseId }: InboxViewProps) {
    const router = useRouter();
    const { data: session } = useSession();
    const [selectedCaseId, setSelectedCaseId] = useState(initialCaseId ?? "");
    const [draft, setDraft] = useState("");
    const [detailsOpen, setDetailsOpen] = useState(false);

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
    const branches = (meData?.branches ?? []) as { id?: string; name?: string }[];
    const selectedBranchId = meData?.selected_branch_id ?? "";
    const isPrivileged = role === "owner" || role === "admin" || role === "platform_admin";
    const showBranchFilter = isPrivileged && branches.length > 1 && !selectedBranchId;

    useEffect(() => {
        if (initialCaseId) {
            setSelectedCaseId(initialCaseId);
        }
    }, [initialCaseId]);

    useEffect(() => {
        setDraft("");
        setDetailsOpen(false);
    }, [selectedCaseId]);

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

    const handleMacroSelect = (text: string) => {
        setDraft((prev) => (prev.trim() ? `${prev}\n${text}` : text));
    };

    const handleToggleDetails = () => {
        if (!canToggleDetails) {
            return;
        }
        setDetailsOpen((prev) => !prev);
    };

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
        <div className="space-y-6" data-testid="inbox-view">
            <div>
                <h1 className="text-2xl font-semibold">Заявки</h1>
                <p className="text-sm text-muted-foreground">
                    Очередь слева, чат по центру, детали открываются по кнопке. Ответы и быстрые действия рядом с вводом.
                </p>
            </div>

            <div
                className={`grid grid-cols-1 gap-6 ${gridClass}`}
            >
                <section className="card-surface flex flex-col min-h-[620px] p-4 xl:overflow-hidden xl:h-[calc(100vh-240px)]" data-testid="inbox-list">
                    <CaseList
                        variant="compact"
                        selectedCaseId={selectedCaseId}
                        onSelectCase={handleSelectCase}
                        branches={branches}
                        showBranchFilter={showBranchFilter}
                    />
                </section>

                <section className="flex flex-col gap-4 min-h-[620px] xl:h-[calc(100vh-240px)]" data-testid="inbox-conversation">
                    {!selectedCaseId && renderEmptyPane("Выберите заявку", "Кликните по карточке слева, чтобы открыть диалог.")}
                    {selectedCaseId && (
                        <div className="flex flex-col gap-4 h-full">
                            {caseLoading && renderLoadingPane()}
                            {caseError && renderErrorPane()}
                            {!caseLoading && !caseError && caseDetail && (
                                <div className="card-surface flex flex-col h-full overflow-hidden">
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
                                        draft={draft}
                                        onDraftChange={setDraft}
                                        composerBefore={composerBefore}
                                        detailsOpen={detailsOpen}
                                        onToggleDetails={handleToggleDetails}
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
                    <section className="hidden xl:flex flex-col gap-4 min-h-[620px] xl:h-[calc(100vh-240px)] xl:overflow-y-auto" data-testid="inbox-details">
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
