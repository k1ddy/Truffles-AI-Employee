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
                    Очередь → диалог → детали. Диагностика скрыта по умолчанию.
                </p>
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[320px_minmax(0,1fr)_320px]">
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
                            <div className="flex items-center justify-between xl:hidden">
                                <p className="text-sm font-semibold">Детали заявки</p>
                                <button
                                    type="button"
                                    onClick={() => setDetailsOpen((prev) => !prev)}
                                    className="text-xs text-muted-foreground hover:text-foreground"
                                >
                                    {detailsOpen ? "Скрыть" : "Показать"}
                                </button>
                            </div>
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
                            />
                        </div>
                    )}
                    {selectedCaseId && !caseLoading && !caseError && !caseDetail && (
                        <div className="card-surface p-6 text-center text-muted-foreground">
                            Заявка не найдена
                        </div>
                    )}
                </section>

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
            </div>
        </div>
    );
}
