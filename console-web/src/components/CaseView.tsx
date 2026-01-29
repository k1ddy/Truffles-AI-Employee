"use client";

import CaseConversation from "./CaseConversation";
import CaseDetailsPanel from "./CaseDetailsPanel";
import { useCaseData } from "@/hooks/useCaseData";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import AccessDenied from "@/components/AccessDenied";
import { authApi, canAccessConsole } from "@/lib/api-client";

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
            <div className="grid grid-cols-3 gap-6">
                <div className="col-span-2 h-96 bg-muted/70 rounded"></div>
                <div className="col-span-1 h-48 bg-muted/70 rounded"></div>
            </div>
        </div>
    );
}

export default function CaseView({ caseId }: CaseViewProps) {
    const { data: session } = useSession();
    const {
        caseDetail,
        caseLoading,
        caseError,
        refetchCase,
        messages,
        messagesLoading,
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

    return (
        <div className="grid grid-cols-3 gap-6" data-testid="case-view">
            <div className="col-span-2">
                <CaseConversation
                    caseDetail={caseDetail}
                    caseId={caseId}
                    messages={messages}
                    messagesLoading={messagesLoading}
                    canSend={canReply}
                    canWrite={canWriteInbox}
                />
            </div>
            <CaseDetailsPanel caseDetail={caseDetail} messages={messages} />
        </div>
    );
}
