"use client";

// useState removed - messaging state now handled in ChatInterface
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Case, Message } from "@/types";
import ChatInterface from "./ChatInterface";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { getStatusLabel, getSlaLabel } from "@/utils/labels";

interface CaseViewProps {
    caseId: string;
}

// API functions
async function fetchCase(caseId: string): Promise<Case> {
    const response = await api.get(`/cases/${caseId}`);
    return response.data;
}

async function fetchMessages(caseId: string): Promise<{ items: Message[] }> {
    const response = await api.get(`/cases/${caseId}/messages`);
    return response.data;
}

async function takeCase(caseId: string): Promise<void> {
    await api.post(`/cases/${caseId}/take`);
}

async function resolveCase(caseId: string): Promise<void> {
    await api.post(`/cases/${caseId}/resolve`);
}

// sendMessage moved to ChatInterface component

// Loading skeleton
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

// SLA Badge component
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

export default function CaseView({ caseId }: CaseViewProps) {
    const router = useRouter();
    const queryClient = useQueryClient();


    // Fetch case details
    const {
        data: caseDetail,
        isLoading: caseLoading,
        error: caseError,
        refetch: refetchCase,
    } = useQuery({
        queryKey: ["case", caseId],
        queryFn: () => fetchCase(caseId),
        refetchInterval: 10000,
        refetchIntervalInBackground: true,
        refetchOnWindowFocus: true,
    });

    // Fetch messages
    const {
        data: messagesData,
        isLoading: messagesLoading,
    } = useQuery({
        queryKey: ["messages", caseId],
        queryFn: () => fetchMessages(caseId),
        refetchInterval: 5000,
        refetchIntervalInBackground: true,
        refetchOnWindowFocus: true,
    });

    // Take mutation
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

    // Resolve mutation
    const resolveMutation = useMutation({
        mutationFn: () => resolveCase(caseId),
        onSuccess: () => {
            toast.success("Заявка закрыта!");
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
            router.push("/");
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



    // Loading state
    if (caseLoading) {
        return <CaseViewSkeleton />;
    }

    // Error state
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

    const messages = messagesData?.items ?? [];
    const isActive = caseDetail.status === "active";
    const isPending = caseDetail.status === "pending";
    const canReply = isActive;

    return (
        <div className="flex flex-col gap-6 h-full" data-testid="case-view">
            {/* Header */}
            <div className="flex justify-between items-start border-b border-border/60 pb-4" data-testid="case-header">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <h1 className="text-2xl font-bold" data-testid="case-title">
                            Заявка {caseDetail.id.slice(0, 8)}
                        </h1>
                        <SlaBadge status={caseDetail.sla_status} />
                    </div>
                    <div className="flex gap-2 text-sm flex-wrap">
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
                        <span className="bg-muted px-2 py-1 rounded">{caseDetail.channel}</span>
                        <span className="bg-muted px-2 py-1 rounded">{caseDetail.trigger_type}</span>
                    </div>
                </div>

                <div className="flex gap-2">
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
                </div>
            </div>

            {/* Content */}
            <div className="grid grid-cols-3 gap-6 flex-1" data-testid="case-content">
                {/* Chat area */}
                <div className="col-span-2 flex flex-col" data-testid="case-chat">
                    <h2 className="text-lg font-semibold mb-2">Диалог</h2>
                    <div className="flex-1 min-h-[400px]">
                        <ChatInterface
                            messages={messages}
                            conversationId={caseDetail.conversation_id}
                            caseId={caseId}
                            isLoading={messagesLoading}
                            canSend={canReply}
                        />
                    </div>
                </div>

                {/* Details sidebar */}
                <div className="col-span-1 bg-card border border-border/60 p-4 rounded-lg h-fit space-y-4">
                    {/* Customer Info */}
                    <div className="bg-muted -m-4 mb-0 p-4 rounded-t-lg border-b border-border/60">
                        <h2 className="text-lg font-semibold text-foreground mb-2">👤 Клиент</h2>
                        <div className="text-sm space-y-1">
                            <p className="font-medium">
                                {caseDetail.customer_name || "Имя не указано"}
                            </p>
                            <p className="text-muted-foreground">
                                📱 {caseDetail.customer_phone || caseDetail.customer_remote_jid?.split("@")[0] || "Номер не указан"}
                            </p>
                            {caseDetail.customer_remote_jid && (
                                <p className="text-xs text-muted-foreground font-mono">
                                    {caseDetail.customer_remote_jid}
                                </p>
                            )}
                        </div>
                    </div>

                    <h2 className="text-lg font-semibold">Детали</h2>
                    <div className="flex flex-col gap-3 text-sm">
                        <div>
                            <span className="font-medium text-muted-foreground">Создано:</span>
                            <p>{new Date(caseDetail.created_at).toLocaleString("ru-RU")}</p>
                        </div>
                        <div>
                            <span className="font-medium text-muted-foreground">Назначено:</span>
                            <p>{caseDetail.assigned_to_name || "Не назначено"}</p>
                        </div>
                        <div>
                            <span className="font-medium text-muted-foreground">Триггер:</span>
                            <p className="font-mono text-xs bg-muted px-2 py-1 rounded inline-block">
                                {caseDetail.trigger_type}
                                {caseDetail.trigger_value && `: ${caseDetail.trigger_value}`}
                            </p>
                        </div>
                        <div>
                            <span className="font-medium text-muted-foreground">Контекст:</span>
                            <p className="bg-background p-2 rounded border border-border/60 mt-1 text-xs">
                                {caseDetail.context_summary || caseDetail.user_message || "Контекст недоступен"}
                            </p>
                        </div>
                    </div>

                    {/* Case Health */}
                    <div className="border-t border-border/60 pt-4">
                        <h3 className="font-medium text-muted-foreground mb-2">📌 Case Health</h3>
                        <div className="space-y-2 text-xs">
                            <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">Последнее входящее:</span>
                                <span>
                                    {caseDetail.last_inbound_at
                                        ? new Date(caseDetail.last_inbound_at).toLocaleString("ru-RU")
                                        : "—"}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">Последнее исходящее:</span>
                                <span>
                                    {caseDetail.last_outbound_at
                                        ? new Date(caseDetail.last_outbound_at).toLocaleString("ru-RU")
                                        : "—"}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">Канал активности:</span>
                                <span>{caseDetail.last_activity_channel || "—"}</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {caseDetail.needs_reply && (
                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-yellow-100 text-yellow-800">
                                        NEW
                                    </span>
                                )}
                                {caseDetail.has_pending_outbox && (
                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-800">
                                        QUEUED
                                    </span>
                                )}
                                {caseDetail.has_delivery_error && (
                                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-100 text-red-800">
                                        FAILED
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Decision Trace Section */}
                    {caseDetail.decision_trace && caseDetail.decision_trace.length > 0 && (
                        <div className="border-t border-border/60 pt-4">
                            <h3 className="font-medium text-muted-foreground mb-2">🧠 Логика решения</h3>

                            {/* Key stages summary */}
                            <div className="space-y-1 mb-3">
                                {caseDetail.decision_trace
                                    .filter((t) => ["policy_gate", "state_transition", "escalation", "booking"].includes(t.stage))
                                    .slice(-5)
                                    .map((trace, idx) => (
                                        <div key={idx} className="flex items-center gap-2 text-xs">
                                            <span className={`px-1.5 py-0.5 rounded ${trace.stage === "policy_gate" ? "bg-purple-100 text-purple-700" :
                                                trace.stage === "escalation" ? "bg-red-100 text-red-700" :
                                                    trace.stage === "booking" ? "bg-green-100 text-green-700" :
                                                        "bg-secondary text-secondary-foreground"
                                                }`}>
                                                {trace.stage}
                                            </span>
                                            {trace.decision && (
                                                <span className="text-muted-foreground">→ {trace.decision}</span>
                                            )}
                                        </div>
                                    ))}
                            </div>

                            {/* Expandable full trace */}
                            <details className="group">
                                <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                                    Показать все ({caseDetail.decision_trace.length} записей)
                                </summary>
                                <div className="mt-2 max-h-48 overflow-y-auto space-y-1">
                                    {caseDetail.decision_trace.map((trace, idx) => (
                                        <div key={idx} className="text-xs bg-background p-1.5 rounded border border-border/60 flex items-start gap-2">
                                            <span className="font-mono text-muted-foreground w-6">{idx + 1}.</span>
                                            <span className="font-medium text-foreground">{trace.stage}</span>
                                            {trace.decision && (
                                                <span className="text-muted-foreground">: {trace.decision}</span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </details>
                        </div>
                    )}

                    {/* Telegram Trail Section (TG-01) */}
                    {caseDetail.telegram_trail && (
                        <div className="border-t border-border/60 pt-4">
                            <h3 className="font-medium text-muted-foreground mb-2">📨 Telegram</h3>
                            <div className="space-y-2 text-sm">
                                {/* Delivery status badge */}
                                <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">Статус:</span>
                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${caseDetail.telegram_trail.delivery_status === "sent"
                                        ? "bg-green-100 text-green-800"
                                        : caseDetail.telegram_trail.delivery_status === "failed"
                                            ? "bg-red-100 text-red-800"
                                            : "bg-yellow-100 text-yellow-800"
                                        }`}>
                                        {caseDetail.telegram_trail.delivery_status === "sent" ? "✓ Доставлено" :
                                            caseDetail.telegram_trail.delivery_status === "failed" ? "✗ Ошибка" :
                                                "⏳ Ожидает"}
                                    </span>
                                </div>

                                {/* Message ID */}
                                {caseDetail.telegram_trail.message_id && (
                                    <div className="flex items-center gap-2">
                                        <span className="text-muted-foreground">Message ID:</span>
                                        <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">
                                            {caseDetail.telegram_trail.message_id}
                                        </span>
                                    </div>
                                )}

                                {/* Topic ID */}
                                {caseDetail.telegram_trail.topic_id && (
                                    <div className="flex items-center gap-2">
                                        <span className="text-muted-foreground">Topic ID:</span>
                                        <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">
                                            {caseDetail.telegram_trail.topic_id}
                                        </span>
                                    </div>
                                )}

                                {/* Delivered at */}
                                {caseDetail.telegram_trail.delivered_at && (
                                    <div className="flex items-center gap-2">
                                        <span className="text-muted-foreground">Отправлено:</span>
                                        <span className="text-xs">
                                            {new Date(caseDetail.telegram_trail.delivered_at).toLocaleString("ru-RU")}
                                        </span>
                                    </div>
                                )}

                                {/* Open in Telegram links */}
                                {(caseDetail.telegram_trail.telegram_desktop_link || caseDetail.telegram_trail.telegram_link) && (
                                    <div className="flex flex-wrap gap-2">
                                        {caseDetail.telegram_trail.telegram_desktop_link && (
                                            <a
                                                href={caseDetail.telegram_trail.telegram_desktop_link}
                                                className="inline-flex items-center gap-1 px-3 py-1.5 bg-primary text-primary-foreground rounded text-xs hover:bg-primary/90 transition-colors"
                                            >
                                                <span>📲</span>
                                                Открыть в Telegram
                                            </a>
                                        )}
                                        {caseDetail.telegram_trail.telegram_link && (
                                            <a
                                                href={caseDetail.telegram_trail.telegram_link}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="inline-flex items-center gap-1 px-3 py-1.5 border border-border/60 rounded text-xs hover:bg-muted transition-colors"
                                            >
                                                <span>🌐</span>
                                                Открыть в Web
                                            </a>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
