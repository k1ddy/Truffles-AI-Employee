"use client";

// useState removed - messaging state now handled in ChatInterface
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Case, Message } from "@/types";
import ChatInterface from "./ChatInterface";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

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

// Status translation
function getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
        pending: "ожидает",
        active: "в работе",
        resolved: "закрыта",
    };
    return labels[status] || status;
}

// SLA translation
function getSlaLabel(status?: string): string {
    const labels: Record<string, string> = {
        ok: "норма",
        warning: "внимание",
        breached: "просрочено",
    };
    return labels[status || "ok"] || status || "норма";
}

// Loading skeleton
function CaseViewSkeleton() {
    return (
        <div className="animate-pulse space-y-6">
            <div className="flex justify-between">
                <div className="h-8 bg-gray-200 rounded w-48"></div>
                <div className="h-10 bg-gray-200 rounded w-24"></div>
            </div>
            <div className="grid grid-cols-3 gap-6">
                <div className="col-span-2 h-96 bg-gray-200 rounded"></div>
                <div className="col-span-1 h-48 bg-gray-200 rounded"></div>
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
    });

    // Fetch messages
    const {
        data: messagesData,
        isLoading: messagesLoading,
        refetch: refetchMessages,
    } = useQuery({
        queryKey: ["messages", caseId],
        queryFn: () => fetchMessages(caseId),
    });

    // Take mutation
    const takeMutation = useMutation({
        mutationFn: () => takeCase(caseId),
        onSuccess: () => {
            toast.success("Заявка назначена на вас!");
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        },
        onError: (error: any) => {
            const code = error?.response?.data?.error?.code;
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
        onError: () => {
            toast.error("Не удалось закрыть заявку");
        },
    });



    // Loading state
    if (caseLoading) {
        return <CaseViewSkeleton />;
    }

    // Error state
    if (caseError) {
        return (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                <p className="text-red-600 mb-4">Не удалось загрузить заявку</p>
                <button
                    onClick={() => refetchCase()}
                    className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                >
                    Повторить
                </button>
            </div>
        );
    }

    if (!caseDetail) {
        return <div className="text-center p-8 text-gray-500">Заявка не найдена</div>;
    }

    const messages = messagesData?.items ?? [];
    const isActive = caseDetail.status === "active";
    const isPending = caseDetail.status === "pending";
    const canReply = isActive;

    return (
        <div className="flex flex-col gap-6 h-full">
            {/* Header */}
            <div className="flex justify-between items-start border-b pb-4">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <h1 className="text-2xl font-bold">Заявка {caseDetail.id.slice(0, 8)}</h1>
                        <SlaBadge status={caseDetail.sla_status} />
                    </div>
                    <div className="flex gap-2 text-sm flex-wrap">
                        <span
                            className={`px-2 py-1 rounded font-medium ${caseDetail.status === "resolved"
                                ? "bg-gray-200 text-gray-700"
                                : isActive
                                    ? "bg-green-100 text-green-800"
                                    : isPending
                                        ? "bg-yellow-100 text-yellow-800"
                                        : "bg-gray-100 text-gray-800"
                                }`}
                        >
                            {getStatusLabel(caseDetail.status)}
                        </span>
                        {caseDetail.assigned_to_name && (
                            <span className="px-2 py-1 rounded bg-blue-100 text-blue-800">
                                👤 {caseDetail.assigned_to_name}
                            </span>
                        )}
                        <span className="bg-gray-100 px-2 py-1 rounded">{caseDetail.channel}</span>
                        <span className="bg-gray-100 px-2 py-1 rounded">{caseDetail.trigger_type}</span>
                    </div>
                </div>

                <div className="flex gap-2">
                    {isPending && (
                        <button
                            onClick={() => takeMutation.mutate()}
                            disabled={takeMutation.isPending}
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                            {takeMutation.isPending ? "Берём..." : "Взять заявку"}
                        </button>
                    )}
                    {isActive && (
                        <button
                            onClick={() => resolveMutation.mutate()}
                            disabled={resolveMutation.isPending}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50"
                        >
                            {resolveMutation.isPending ? "Закрываем..." : "Закрыть заявку"}
                        </button>
                    )}
                </div>
            </div>

            {/* Content */}
            <div className="grid grid-cols-3 gap-6 flex-1">
                {/* Chat area */}
                <div className="col-span-2 flex flex-col">
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
                <div className="col-span-1 bg-gray-50 p-4 rounded-lg h-fit space-y-4">
                    {/* Customer Info */}
                    <div className="bg-blue-50 -m-4 mb-0 p-4 rounded-t-lg border-b border-blue-100">
                        <h2 className="text-lg font-semibold text-blue-800 mb-2">👤 Клиент</h2>
                        <div className="text-sm space-y-1">
                            <p className="font-medium">
                                {caseDetail.customer_name || "Имя не указано"}
                            </p>
                            <p className="text-blue-700">
                                📱 {caseDetail.customer_phone || caseDetail.customer_remote_jid?.split("@")[0] || "Номер не указан"}
                            </p>
                            {caseDetail.customer_remote_jid && (
                                <p className="text-xs text-blue-600 font-mono">
                                    {caseDetail.customer_remote_jid}
                                </p>
                            )}
                        </div>
                    </div>

                    <h2 className="text-lg font-semibold">Детали</h2>
                    <div className="flex flex-col gap-3 text-sm">
                        <div>
                            <span className="font-medium text-gray-600">Создано:</span>
                            <p>{new Date(caseDetail.created_at).toLocaleString("ru-RU")}</p>
                        </div>
                        <div>
                            <span className="font-medium text-gray-600">Назначено:</span>
                            <p>{caseDetail.assigned_to_name || "Не назначено"}</p>
                        </div>
                        <div>
                            <span className="font-medium text-gray-600">Триггер:</span>
                            <p className="font-mono text-xs bg-gray-100 px-2 py-1 rounded inline-block">
                                {caseDetail.trigger_type}
                                {caseDetail.trigger_value && `: ${caseDetail.trigger_value}`}
                            </p>
                        </div>
                        <div>
                            <span className="font-medium text-gray-600">Контекст:</span>
                            <p className="bg-white p-2 rounded border mt-1 text-xs">
                                {caseDetail.context_summary || caseDetail.user_message || "Контекст недоступен"}
                            </p>
                        </div>
                    </div>

                    {/* Decision Trace Section */}
                    {caseDetail.decision_trace && caseDetail.decision_trace.length > 0 && (
                        <div className="border-t pt-4">
                            <h3 className="font-medium text-gray-600 mb-2">🧠 Логика решения</h3>

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
                                                            "bg-blue-100 text-blue-700"
                                                }`}>
                                                {trace.stage}
                                            </span>
                                            {trace.decision && (
                                                <span className="text-gray-600">→ {trace.decision}</span>
                                            )}
                                        </div>
                                    ))}
                            </div>

                            {/* Expandable full trace */}
                            <details className="group">
                                <summary className="text-xs text-gray-400 cursor-pointer hover:text-blue-600">
                                    Показать все ({caseDetail.decision_trace.length} записей)
                                </summary>
                                <div className="mt-2 max-h-48 overflow-y-auto space-y-1">
                                    {caseDetail.decision_trace.map((trace, idx) => (
                                        <div key={idx} className="text-xs bg-white p-1.5 rounded border flex items-start gap-2">
                                            <span className="font-mono text-gray-400 w-6">{idx + 1}.</span>
                                            <span className="font-medium text-gray-700">{trace.stage}</span>
                                            {trace.decision && (
                                                <span className="text-gray-500">: {trace.decision}</span>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </details>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
