"use client";

import { type ReactNode } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import api from "@/lib/api";
import type { Case, Message } from "@/types";
import ChatInterface from "./ChatInterface";
import { getStatusLabel, getSlaLabel } from "@/utils/labels";

interface CaseConversationProps {
    caseDetail: Case;
    caseId: string;
    messages: Message[];
    messagesLoading: boolean;
    canSend: boolean;
    canWrite: boolean;
    draft?: string;
    onDraftChange?: (value: string) => void;
    onResolved?: () => void;
    composerBefore?: ReactNode;
    detailsOpen?: boolean;
    onToggleDetails?: () => void;
}

async function takeCase(caseId: string): Promise<void> {
    await api.post(`/cases/${caseId}/take`);
}

async function resolveCase(caseId: string): Promise<void> {
    await api.post(`/cases/${caseId}/resolve`);
}

function SlaBadge({ status }: { status?: string }) {
    const styles = {
        ok: "bg-green-100 text-green-800",
        warning: "bg-yellow-100 text-yellow-800",
        breached: "bg-red-100 text-red-800",
    };
    const style = styles[status as keyof typeof styles] || styles.ok;
    return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${style}`}>
            SLA: {getSlaLabel(status)}
        </span>
    );
}

export default function CaseConversation({
    caseDetail,
    caseId,
    messages,
    messagesLoading,
    canSend,
    canWrite,
    draft,
    onDraftChange,
    onResolved,
    composerBefore,
    detailsOpen = false,
    onToggleDetails,
}: CaseConversationProps) {
    const router = useRouter();
    const queryClient = useQueryClient();
    const handleResolved = onResolved ?? (() => router.push("/"));

    const takeMutation = useMutation({
        mutationFn: () => takeCase(caseId),
        onSuccess: () => {
            toast.success("Заявка назначена на вас!");
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "CASE_ALREADY_TAKEN") {
                toast.error("Заявка уже взята другим менеджером");
            } else {
                toast.error("Не удалось взять заявку");
            }
        },
    });

    const resolveMutation = useMutation({
        mutationFn: () => resolveCase(caseId),
        onSuccess: () => {
            toast.success("Заявка закрыта!");
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
            handleResolved();
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "CASE_ALREADY_RESOLVED") {
                toast.error("Заявка уже закрыта");
                queryClient.invalidateQueries({ queryKey: ["case", caseId] });
                queryClient.invalidateQueries({ queryKey: ["cases"] });
            } else {
                toast.error("Не удалось закрыть заявку");
            }
        },
    });

    const isActive = caseDetail.status === "active";
    const isPending = caseDetail.status === "pending";
    const contextText = caseDetail.context_summary || caseDetail.user_message || "Сводка недоступна";
    const contextTitle = caseDetail.context_summary ? "Суть запроса" : "Последнее сообщение";
    const lastInbound = caseDetail.last_inbound_at
        ? new Date(caseDetail.last_inbound_at).toLocaleString("ru-RU")
        : "—";
    const showDetailsToggle = typeof onToggleDetails === "function";

    return (
        <div className="flex flex-col gap-5 h-full" data-testid="case-conversation">
            <div className="flex flex-col gap-4 border-b border-border/60 pb-4">
                <div className="flex items-start justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <h1 className="text-2xl font-bold" data-testid="case-title">
                                Заявка {caseDetail.id.slice(0, 8)}
                            </h1>
                            <SlaBadge status={caseDetail.sla_status} />
                        </div>
                        <div className="flex flex-wrap gap-2 text-sm">
                            <span
                                className={`px-2 py-1 rounded font-medium ${caseDetail.status === "resolved"
                                    ? "bg-muted text-muted-foreground"
                                    : isActive
                                        ? "bg-green-100 text-green-800"
                                        : isPending
                                            ? "bg-yellow-100 text-yellow-800"
                                            : "bg-muted text-muted-foreground"
                                    }`}
                            >
                                {getStatusLabel(caseDetail.status)}
                            </span>
                            {caseDetail.assigned_to_name && (
                                <span className="px-2 py-1 rounded bg-secondary text-secondary-foreground">
                                    👤 {caseDetail.assigned_to_name}
                                </span>
                            )}
                            <span className="bg-muted px-2 py-1 rounded">Канал: {caseDetail.channel}</span>
                            <span className="bg-muted px-2 py-1 rounded">Триггер: {caseDetail.trigger_type}</span>
                        </div>
                    </div>

                    <div className="flex flex-col items-end gap-2">
                        {showDetailsToggle && (
                            <button
                                type="button"
                                onClick={onToggleDetails}
                                className={`text-xs font-semibold transition ${
                                    detailsOpen ? "text-foreground" : "text-muted-foreground hover:text-foreground"
                                }`}
                                aria-pressed={detailsOpen}
                                data-testid="case-details-toggle"
                            >
                                {detailsOpen ? "Скрыть детали" : "Детали"}
                            </button>
                        )}
                        <div className="flex gap-2">
                            {canWrite ? (
                                <>
                                    {isPending && (
                                        <button
                                            onClick={() => takeMutation.mutate()}
                                            disabled={takeMutation.isPending}
                                            className="bg-primary text-primary-foreground px-4 py-2 rounded hover:bg-primary/90 disabled:opacity-50"
                                        >
                                            {takeMutation.isPending ? "Берём..." : "Взять заявку"}
                                        </button>
                                    )}
                                    {isActive && (
                                        <button
                                            onClick={() => resolveMutation.mutate()}
                                            disabled={resolveMutation.isPending}
                                            className="bg-foreground text-background px-4 py-2 rounded hover:bg-foreground/90 disabled:opacity-50"
                                        >
                                            {resolveMutation.isPending ? "Закрываем..." : "Закрыть заявку"}
                                        </button>
                                    )}
                                </>
                            ) : (
                                <span className="text-xs text-muted-foreground self-center">
                                    Только просмотр
                                </span>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <div className="rounded-lg border border-border/60 bg-card p-3 text-sm">
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                    <span>{contextTitle}</span>
                    <span>Последнее входящее: {lastInbound}</span>
                </div>
                <p className="text-sm text-foreground">{contextText}</p>
            </div>

            <div className="flex-1 min-h-[480px]">
                <ChatInterface
                    messages={messages}
                    conversationId={caseDetail.conversation_id}
                    caseId={caseId}
                    isLoading={messagesLoading}
                    canSend={canSend}
                    draft={draft}
                    onDraftChange={onDraftChange}
                    composerBefore={composerBefore}
                />
            </div>
        </div>
    );
}
