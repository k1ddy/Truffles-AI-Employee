"use client";

import { useState, useRef, useEffect, type ReactNode } from "react";
import { Message } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import toast from "react-hot-toast";

interface ChatInterfaceProps {
    messages: Message[];
    conversationId: string;
    caseId: string;  // For query invalidation (handover ID)
    isLoading?: boolean;
    canSend?: boolean; // Allow sending messages (case must be active)
    draft?: string;
    onDraftChange?: (value: string) => void;
    composerBefore?: ReactNode;
    frame?: "card" | "plain";
}

async function sendMessage(conversationId: string, content: string) {
    const response = await api.post(`/conversations/${conversationId}/messages`, {
        content,
    });
    return response.data;
}

export default function ChatInterface({
    messages,
    conversationId,
    caseId,
    isLoading,
    canSend = true,
    draft,
    onDraftChange,
    composerBefore,
    frame = "card",
}: ChatInterfaceProps) {
    const isControlled = typeof onDraftChange === "function";
    const [internalDraft, setInternalDraft] = useState("");
    const inputValue = isControlled ? draft ?? "" : internalDraft;
    const setInputValue = isControlled ? onDraftChange : setInternalDraft;
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const lastMessageIdRef = useRef<string | null>(null);
    const queryClient = useQueryClient();
    const isPlain = frame === "plain";

    // Reverse messages for chronological display (oldest first)
    const sortedMessages = [...messages].reverse();

    // Scroll to bottom on new messages
    useEffect(() => {
        const latestId = messages[0]?.id || null;
        if (latestId && latestId !== lastMessageIdRef.current) {
            lastMessageIdRef.current = latestId;
            if (scrollContainerRef.current) {
                scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
            }
        }
    }, [messages]);

    // Send message mutation with optimistic updates
    const sendMutation = useMutation({
        mutationFn: (content: string) => sendMessage(conversationId, content),
        onMutate: async (content) => {
            // Cancel any outgoing refetches
            await queryClient.cancelQueries({ queryKey: ["messages", caseId] });

            // Snapshot previous value
            const previousMessages = queryClient.getQueryData(["messages", caseId]);

            // Optimistically add the new message
            const optimisticMessage: Message = {
                id: `temp-${Date.now()}`,
                role: "manager",
                content,
                created_at: new Date().toISOString(),
            };

            queryClient.setQueryData(["messages", caseId], (old: { items: Message[] } | undefined) => ({
                items: [optimisticMessage, ...(old?.items || [])],
            }));

            // Scroll to bottom on optimistic update
            if (scrollContainerRef.current) {
                scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
            }

            return { previousMessages };
        },
        onSuccess: () => {
            setInputValue("");
            queryClient.invalidateQueries({ queryKey: ["messages", caseId] });
            toast.success("Сообщение отправлено");
        },
        onError: (error: unknown, _, context) => {
            // Rollback on error
            if (context?.previousMessages) {
                queryClient.setQueryData(["messages", caseId], context.previousMessages);
            }
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "NOT_ASSIGNED") {
                toast.error("Вы не назначены на эту заявку");
            } else if (code === "CASE_NOT_ACTIVE") {
                toast.error("Заявка должна быть активной для отправки сообщений");
            } else {
                toast.error("Не удалось отправить сообщение");
            }
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const content = inputValue.trim();
        if (!content) return;
        setInputValue(""); // Clear immediately for better UX
        sendMutation.mutate(content);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        // Enter (without shift) or Ctrl+Enter to send
        if ((e.key === "Enter" && !e.shiftKey) || (e.key === "Enter" && e.ctrlKey)) {
            e.preventDefault();
            handleSubmit(e);
        }
        // Escape to clear input
        if (e.key === "Escape") {
            setInputValue("");
        }
    };

    if (isLoading) {
        return (
            <div
                className={`flex flex-col gap-4 p-4 min-h-[520px] overflow-y-auto ${
                    isPlain ? "" : "bg-muted/60 rounded-xl"
                }`}
            >
                <div className="animate-pulse space-y-4">
                    <div className="h-16 bg-muted/70 rounded-lg w-3/4"></div>
                    <div className="h-16 bg-muted/70 rounded-lg w-2/3 self-end ml-auto"></div>
                    <div className="h-16 bg-muted/70 rounded-lg w-3/4"></div>
                </div>
            </div>
        );
    }

    return (
        <div
            className={`flex flex-col h-full min-h-[480px] ${
                isPlain ? "" : "bg-muted/60 rounded-xl overflow-hidden"
            }`}
        >
            {/* Messages area */}
            <div
                ref={scrollContainerRef}
                className="flex-1 overflow-y-auto p-4 space-y-4"
            >
                {sortedMessages.length === 0 ? (
                    <div className="text-center text-muted-foreground my-auto">
                        Нет сообщений
                    </div>
                ) : (
                    sortedMessages.map((msg) => {
                        const isOptimistic = msg.id.startsWith("temp-");
                        return (
                            <div
                                key={msg.id}
                                className={`flex flex-col max-w-[92%] ${msg.role === "user" ? "self-start" : "self-end items-end"} ${isOptimistic ? "opacity-70" : ""}`}
                            >
                                <div className="text-xs text-muted-foreground mb-1">
                                    {msg.role === "user" ? "Клиент" :
                                        msg.role === "manager" ? "Менеджер" : "Бот"}
                                    {isOptimistic && " (отправка...)"}
                                </div>
                                <div
                                    className={`p-3 rounded-lg ${msg.role === "user"
                                        ? "bg-card border border-border/60"
                                        : msg.role === "manager"
                                            ? "bg-primary text-primary-foreground"
                                            : "bg-foreground text-background"
                                        }`}
                                >
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                </div>
                                <span className="text-xs text-muted-foreground mt-1">
                                    {isOptimistic ? "..." : new Date(msg.created_at).toLocaleString("ru-RU")}
                                </span>
                            </div>
                        );
                    })
                )}
            </div>

            {/* Input area */}
            {canSend && (
                <form onSubmit={handleSubmit} className="border-t border-border/60 p-3 bg-card">
                    {composerBefore && (
                        <div className="mb-2">
                            {composerBefore}
                        </div>
                    )}
                    <div className="flex gap-2">
                        <textarea
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Введите сообщение. Enter — отправить, Shift+Enter — новая строка."
                            rows={2}
                            disabled={sendMutation.isPending}
                            className="flex-1 px-3 py-2 border border-border/60 rounded-lg text-sm resize-none bg-background focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:bg-muted"
                        />
                        <button
                            type="submit"
                            disabled={!inputValue.trim() || sendMutation.isPending}
                            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors"
                        >
                            {sendMutation.isPending ? (
                                <span className="flex items-center gap-1">
                                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                </span>
                            ) : (
                                "Отправить"
                            )}
                        </button>
                    </div>
                </form>
            )}

            {!canSend && (
                <div className="border-t border-border/60 p-3 bg-muted text-center text-sm text-muted-foreground">
                    Возьмите заявку, чтобы отвечать клиенту
                </div>
            )}
        </div>
    );
}
