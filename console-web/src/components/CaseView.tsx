"use client";

import { useState } from "react";
import CaseConversation from "./CaseConversation";
import CaseDetailsPanel from "./CaseDetailsPanel";
import { useCaseData } from "@/hooks/useCaseData";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import AccessDenied from "@/components/AccessDenied";
import { authApi, canAccessConsole } from "@/lib/api-client";
import { InboxMacroChips } from "@/components/InboxMacros";

interface CaseViewProps {
    caseId: string;
}

function CaseViewSkeleton() {
    return (
        <div className="animate-pulse space-y-6">
            <div className="flex justify-between">
                <div className="h-8 bg-muted/70 rounded w-48"></div>
                <div className="h-10 bg-muted/70 rounded w-24"></div>
            </div>
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
                <div className="h-96 bg-muted/70 rounded"></div>
                <div className="h-48 bg-muted/70 rounded hidden xl:block"></div>
            </div>
        </div>
    );
}

export default function CaseView({ caseId }: CaseViewProps) {
    const { data: session } = useSession();
    const [draft, setDraft] = useState("");
    const [detailsOpen, setDetailsOpen] = useState(false);
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
    } = useCaseData(caseId);

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
    const canViewDiagnostics = role === "support" || role === "platform_admin" || role === "owner" || role === "admin";

    if (!canReadInbox) {
        return <AccessDenied message="Эта роль не имеет доступа к заявкам." />;
    }

    if (caseLoading) {
        return <CaseViewSkeleton />;
    }

    if (caseError) {
        return (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center" data-testid="case-error">
                <p className="text-destructive mb-4">Не удалось загрузить заявку</p>
                <button
                    onClick={() => refetchCase()}
                    className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                    data-testid="case-retry"
                >
                    Повторить
                </button>
            </div>
        );
    }

    if (!caseDetail) {
        return (
            <div className="text-center p-8 text-muted-foreground" data-testid="case-missing">
                Заявка не найдена
            </div>
        );
    }

    const canReply = caseDetail.status === "active" && canWriteInbox;
    const macroBranchId = caseDetail.branch_id ?? "";

    const handleMacroSelect = (text: string) => {
        setDraft((prev) => (prev.trim() ? `${prev}\n${text}` : text));
    };

    return (
        <div
            className={`grid grid-cols-1 gap-6 ${
                detailsOpen ? "xl:grid-cols-[minmax(0,1fr)_320px]" : "xl:grid-cols-[minmax(0,1fr)]"
            }`}
            data-testid="case-view"
        >
            <div className="flex flex-col gap-4">
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
                    caseId={caseId}
                    messages={messages}
                    messagesLoading={messagesLoading}
                    messagesHasMore={messagesHasMore}
                    messagesLoadingMore={messagesLoadingMore}
                    onLoadMoreMessages={loadMoreMessages}
                    canSend={canReply}
                    canWrite={canWriteInbox}
                    canOutreach={canWriteOutreach}
                    canReadOutreach={canReadOutreach}
                    draft={draft}
                    onDraftChange={setDraft}
                    composerBefore={
                        <InboxMacroChips
                            onSelect={handleMacroSelect}
                            disabled={!canReply}
                            canManage={canWriteInbox}
                            branchId={macroBranchId}
                        />
                    }
                    detailsOpen={detailsOpen}
                    onToggleDetails={() => setDetailsOpen((prev) => !prev)}
                />
            </div>
            {detailsOpen && (
                <div className="hidden xl:block">
                    <CaseDetailsPanel
                        caseDetail={caseDetail}
                        messages={messages}
                        canViewDiagnostics={canViewDiagnostics}
                    />
                </div>
            )}
        </div>
    );
}
