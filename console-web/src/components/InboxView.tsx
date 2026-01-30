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
    } = useCaseData(selectedCaseId);

    const canSend = Boolean(caseDetail && caseDetail.status === "active" && canWriteInbox);
    const canViewDiagnostics = role === "support" || role === "platform_admin" || role === "owner" || role === "admin";
    const macroBranchId = caseDetail?.branch_id ?? selectedBranchId;
    const canManageMacros = canWriteInbox;

    const handleSelectCase = (caseId: string) => {
        setSelectedCaseId(caseId);
        router.push(`/cases/${caseId}`);
    };

    const handleMacroSelect = (text: string) => {
        setDraft((prev) => (prev.trim() ? `${prev}\n${text}` : text));
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
                    Очередь слева, чат по центру, детали справа. Ответы и быстрые действия рядом с вводом.
                </p>
            </div>

            <div
                className={`grid grid-cols-1 gap-6 ${
                    detailsOpen ? "xl:grid-cols-[280px_minmax(0,1fr)_320px]" : "xl:grid-cols-[280px_minmax(0,1fr)]"
                }`}
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
                    {selectedCaseId && caseLoading && renderLoadingPane()}
                    {selectedCaseId && caseError && renderErrorPane()}
                    {selectedCaseId && !caseLoading && !caseError && caseDetail && (
                        <div className="card-surface p-5 flex flex-col gap-4 h-full">
                            {detailsOpen && (
                                <div className="xl:hidden">
                                    <CaseDetailsPanel
                                        caseDetail={caseDetail}
                                        messages={messages}
                                        canViewDiagnostics={canViewDiagnostics}
                                    />
                                </div>
                            )}
                            <CaseConversation
                                caseDetail={caseDetail}
                                caseId={selectedCaseId}
                                messages={messages}
                                messagesLoading={messagesLoading}
                                canSend={canSend}
                                canWrite={canWriteInbox}
                                draft={draft}
                                onDraftChange={setDraft}
                                composerBefore={composerBefore}
                                detailsOpen={detailsOpen}
                                onToggleDetails={() => setDetailsOpen((prev) => !prev)}
                            />
                        </div>
                    )}
                    {selectedCaseId && !caseLoading && !caseError && !caseDetail && (
                        <div className="card-surface p-6 text-center text-muted-foreground">
                            Заявка не найдена
                        </div>
                    )}
                </section>

                {detailsOpen && (
                    <section className="hidden xl:flex flex-col gap-4 min-h-[620px] xl:h-[calc(100vh-240px)] xl:overflow-y-auto" data-testid="inbox-details">
                        {!selectedCaseId && renderEmptyPane("Детали", "Выберите заявку, чтобы увидеть контекст и trace.")}
                        {selectedCaseId && caseLoading && renderLoadingPane()}
                        {selectedCaseId && caseError && renderErrorPane()}
                        {selectedCaseId && !caseLoading && !caseError && caseDetail && (
                            <CaseDetailsPanel
                                caseDetail={caseDetail}
                                messages={messages}
                                canViewDiagnostics={canViewDiagnostics}
                            />
                        )}
                        {selectedCaseId && !caseLoading && !caseError && !caseDetail && (
                            <div className="card-surface p-6 text-center text-muted-foreground">
                                Детали недоступны
                            </div>
                        )}
                    </section>
                )}
            </div>
        </div>
    );
}
