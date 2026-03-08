"use client";

import { useEffect, useState } from "react";
import CaseBookingsPanel from "./CaseBookingsPanel";
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

type SidePanelMode = "details" | "bookings" | null;

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
    const [sidePanelMode, setSidePanelMode] = useState<SidePanelMode>(null);
    const [isDesktopViewport, setIsDesktopViewport] = useState(false);
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
    const canReadCalendar = canAccessConsole(role, "calendar", "read");
    const canWriteCalendar = canAccessConsole(role, "calendar", "write");
    const canReadOutreach = canAccessConsole(role, "outreach", "read");
    const canWriteOutreach = canAccessConsole(role, "outreach", "write");
    const canViewDiagnostics = role === "support" || role === "platform_admin" || role === "owner" || role === "admin";
    const detailsOpen = sidePanelMode === "details";
    const bookingsOpen = sidePanelMode === "bookings";

    useEffect(() => {
        if (typeof window === "undefined") {
            return;
        }
        const media = window.matchMedia("(min-width: 1280px)");
        const syncViewport = () => setIsDesktopViewport(media.matches);
        syncViewport();
        if (typeof media.addEventListener === "function") {
            media.addEventListener("change", syncViewport);
            return () => media.removeEventListener("change", syncViewport);
        }
        media.addListener(syncViewport);
        return () => media.removeListener(syncViewport);
    }, []);

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
                detailsOpen || bookingsOpen ? "xl:grid-cols-[minmax(0,1fr)_320px]" : "xl:grid-cols-[minmax(0,1fr)]"
            }`}
            data-testid="case-view"
        >
            <div className="flex flex-col gap-4">
                {(detailsOpen || bookingsOpen) && !isDesktopViewport && (
                    <div className="xl:hidden">
                        {bookingsOpen ? (
                            <CaseBookingsPanel
                                caseId={caseId}
                                conversationId={caseDetail.conversation_id}
                                canWriteCalendar={canWriteCalendar}
                                fullCalendarHref={
                                    caseDetail.conversation_id
                                        ? `/calendar?conversation_id=${encodeURIComponent(caseDetail.conversation_id)}&case_id=${encodeURIComponent(caseId)}&return_panel=bookings`
                                        : `/calendar?case_id=${encodeURIComponent(caseId)}&return_panel=bookings`
                                }
                            />
                        ) : (
                            <CaseDetailsPanel
                                caseDetail={caseDetail}
                                messages={messages}
                                canViewDiagnostics={canViewDiagnostics}
                            />
                        )}
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
                            disabled={!caseId || !canWriteInbox}
                            canManage={canWriteInbox}
                            branchId={macroBranchId}
                            caseId={caseId}
                        />
                    }
                    detailsOpen={detailsOpen}
                    bookingsOpen={bookingsOpen}
                    onToggleDetails={() => setSidePanelMode((prev) => prev === "details" ? null : "details")}
                    onToggleBookings={() => setSidePanelMode((prev) => prev === "bookings" ? null : "bookings")}
                    canReadCalendar={canReadCalendar}
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
            {bookingsOpen && (
                <div className="hidden xl:block">
                    <CaseBookingsPanel
                        caseId={caseId}
                        conversationId={caseDetail.conversation_id}
                        canWriteCalendar={canWriteCalendar}
                        fullCalendarHref={
                            caseDetail.conversation_id
                                ? `/calendar?conversation_id=${encodeURIComponent(caseDetail.conversation_id)}&case_id=${encodeURIComponent(caseId)}&return_panel=bookings`
                                : `/calendar?case_id=${encodeURIComponent(caseId)}&return_panel=bookings`
                        }
                    />
                </div>
            )}
        </div>
    );
}
