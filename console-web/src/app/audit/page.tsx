"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useSession } from "next-auth/react";
import Link from "next/link";

interface AuditEvent {
    id: string;
    created_at: string;
    event_type: string;
    actor_name: string | null;
    entity_type: string | null;
    entity_id: string | null;
    payload: Record<string, unknown> | null;
}

async function fetchAuditEvents(): Promise<{ items: AuditEvent[] }> {
    const response = await api.get("/audit?limit=100");
    return response.data;
}

// Event type translation
function getEventTypeLabel(type: string): string {
    const labels: Record<string, string> = {
        case_taken: "Заявка взята",
        case_resolved: "Заявка закрыта",
        message_sent: "Сообщение отправлено",
        settings_changed: "Настройки изменены",
        login_failed: "Ошибка входа",
        access_denied: "Доступ запрещён",
    };
    return labels[type] || type.replace(/_/g, " ");
}

// Entity type translation
function getEntityTypeLabel(type: string | null): string {
    if (!type) return "";
    const labels: Record<string, string> = {
        handover: "заявка",
        conversation: "диалог",
        message: "сообщение",
        agent: "агент",
        client: "клиент",
        branch: "филиал",
    };
    return labels[type] || type;
}

function EventTypeBadge({ type }: { type: string }) {
    const styles: Record<string, string> = {
        case_taken: "bg-secondary text-secondary-foreground",
        case_resolved: "bg-green-100 text-green-800",
        message_sent: "bg-purple-100 text-purple-800",
        settings_changed: "bg-orange-100 text-orange-800",
    };
    return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${styles[type] || "bg-muted text-muted-foreground"}`}>
            {getEventTypeLabel(type)}
        </span>
    );
}

export default function AuditPage() {
    const { data: session } = useSession();

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ["audit"],
        queryFn: fetchAuditEvents,
        enabled: !!session,
    });

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Войдите в систему для просмотра журнала.
            </div>
        );
    }

    if (isLoading) {
        return (
            <div className="max-w-6xl mx-auto p-6" data-testid="audit-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="audit-title">Журнал действий</h1>
                <div className="animate-pulse space-y-3">
                    {[...Array(10)].map((_, i) => (
                        <div key={i} className="h-12 bg-muted/70 rounded"></div>
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="max-w-6xl mx-auto p-6" data-testid="audit-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="audit-title">Журнал действий</h1>
                <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center" data-testid="audit-error">
                    <p className="text-destructive mb-4">Не удалось загрузить журнал</p>
                    <button
                        onClick={() => refetch()}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="audit-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    const events = data?.items ?? [];

    return (
        <div className="max-w-6xl mx-auto p-6" data-testid="audit-page">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold" data-testid="audit-title">Журнал действий</h1>
                <Link href="/" className="text-primary hover:text-primary/80">
                    ← Назад к заявкам
                </Link>
            </div>

            <div className="bg-card border border-border/60 rounded-lg overflow-hidden" data-testid="audit-table">
                <table className="w-full text-left">
                    <thead className="bg-muted">
                        <tr>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Время</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Событие</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Исполнитель</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Объект</th>
                            <th className="p-4 text-sm font-medium text-muted-foreground">Детали</th>
                        </tr>
                    </thead>
                    <tbody>
                        {events.map((event) => (
                            <tr key={event.id} className="border-t border-border/60 hover:bg-muted/60" data-testid="audit-row">
                                <td className="p-4 text-sm text-muted-foreground">
                                    {new Date(event.created_at).toLocaleString("ru-RU")}
                                </td>
                                <td className="p-4">
                                    <EventTypeBadge type={event.event_type} />
                                </td>
                                <td className="p-4 text-sm">{event.actor_name || "-"}</td>
                                <td className="p-4 text-sm">
                                    {event.entity_type && event.entity_id ? (
                                        <span className="font-mono text-xs">
                                            {getEntityTypeLabel(event.entity_type)}:{event.entity_id.slice(0, 8)}
                                        </span>
                                    ) : (
                                        "-"
                                    )}
                                </td>
                                <td className="p-4 text-sm text-muted-foreground">
                                    {event.payload ? JSON.stringify(event.payload).slice(0, 50) : "-"}
                                </td>
                            </tr>
                        ))}
                        {events.length === 0 && (
                            <tr>
                                <td colSpan={5} className="p-8 text-center text-muted-foreground" data-testid="audit-empty">
                                    Записей в журнале пока нет.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
