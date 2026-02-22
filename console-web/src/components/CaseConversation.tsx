"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { casesApi, outreachApi, type CaseActionResponse } from "@/lib/api-client";
import type { Case, Message } from "@/types";
import ChatInterface from "./ChatInterface";
import { getSlaCountdown, getStatusLabel, getSlaLabel } from "@/utils/labels";

interface CaseConversationProps {
    caseDetail: Case;
    caseId: string;
    messages: Message[];
    messagesLoading: boolean;
    messagesHasMore?: boolean;
    messagesLoadingMore?: boolean;
    onLoadMoreMessages?: () => void;
    canSend: boolean;
    canWrite: boolean;
    canOutreach?: boolean;
    canReadOutreach?: boolean;
    draft?: string;
    onDraftChange?: (value: string) => void;
    onResolved?: () => void;
    composerBefore?: ReactNode;
    detailsOpen?: boolean;
    onToggleDetails?: () => void;
    onNextCase?: () => void;
    canGoNextCase?: boolean;
    chatFrame?: "card" | "plain";
    layout?: "default" | "inbox";
}

async function takeCase(caseId: string): Promise<CaseActionResponse> {
    const response = await casesApi.take(caseId);
    return response.data;
}

async function resolveCase(caseId: string): Promise<CaseActionResponse> {
    const response = await casesApi.resolve(caseId);
    return response.data;
}

async function returnCase(caseId: string): Promise<CaseActionResponse> {
    const response = await casesApi.returnToBot(caseId);
    return response.data;
}

function collectSyncIssues(sync?: CaseActionResponse["sync"]) {
    const issues: string[] = [];
    if (sync?.telegram?.status === "failed") {
        issues.push(`Telegram: ${sync.telegram.detail || "ошибка синхронизации"}`);
    }
    if (sync?.client_notify?.status === "failed") {
        issues.push(`Клиент: ${sync.client_notify.detail || "уведомление не доставлено"}`);
    }
    return issues;
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

const HUMAN_LOCK_SOURCE_LABELS: Record<string, string> = {
    console_message: "Ответ менеджера",
    console_outreach: "Outreach",
    console_pause: "Ручная пауза",
    console_media: "Медиа",
};

const HUMAN_LOCK_REASON_LABELS: Record<string, string> = {
    manual_reply: "Ответ менеджера",
    manual_pause: "Ручная пауза",
};

function formatHumanLockLabel(value?: string | null, lookup?: Record<string, string>) {
    if (!value) {
        return null;
    }
    if (lookup && lookup[value]) {
        return lookup[value];
    }
    return value;
}

export default function CaseConversation({
    caseDetail,
    caseId,
    messages,
    messagesLoading,
    messagesHasMore = false,
    messagesLoadingMore = false,
    onLoadMoreMessages,
    canSend,
    canWrite,
    canOutreach = false,
    canReadOutreach = canOutreach,
    draft,
    onDraftChange,
    onResolved,
    composerBefore,
    detailsOpen = false,
    onToggleDetails,
    onNextCase,
    canGoNextCase = false,
    chatFrame = "card",
    layout = "default",
}: CaseConversationProps) {
    const router = useRouter();
    const queryClient = useQueryClient();
    const handleResolved = onResolved ?? (() => router.push("/"));

    const takeMutation = useMutation({
        mutationFn: () => takeCase(caseId),
        onSuccess: (response) => {
            toast.success("Заявка назначена на вас!");
            const issues = collectSyncIssues(response.sync);
            if (issues.length > 0) {
                toast.error(issues.join(" · "));
            }
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
        onSuccess: (response) => {
            toast.success("Заявка закрыта!");
            const issues = collectSyncIssues(response.sync);
            if (issues.length > 0) {
                toast.error(issues.join(" · "));
            }
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

    const returnMutation = useMutation({
        mutationFn: () => returnCase(caseId),
        onSuccess: (response) => {
            toast.success("Заявка передана боту");
            const issues = collectSyncIssues(response.sync);
            if (issues.length > 0) {
                toast.error(issues.join(" · "));
            }
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
                toast.error("Не удалось передать заявку");
            }
        },
    });

    const defaultDestination = caseDetail.customer_phone || caseDetail.customer_remote_jid || "";
    const [outreachDestination, setOutreachDestination] = useState(defaultDestination);
    const [outreachContent, setOutreachContent] = useState("");
    const [pauseMinutes, setPauseMinutes] = useState(30);
    const [outreachPauseEnabled, setOutreachPauseEnabled] = useState(true);
    const [replyPauseEnabled, setReplyPauseEnabled] = useState(true);
    const [replyPauseMinutes, setReplyPauseMinutes] = useState(30);
    const [outreachExpanded, setOutreachExpanded] = useState(false);
    const outreachPanelRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        setOutreachDestination(caseDetail.customer_phone || caseDetail.customer_remote_jid || "");
        setOutreachContent("");
        setPauseMinutes(30);
        setOutreachPauseEnabled(true);
        setReplyPauseEnabled(true);
        setReplyPauseMinutes(30);
        setOutreachExpanded(false);
    }, [caseId, caseDetail.customer_phone, caseDetail.customer_remote_jid]);

    const humanLockQuery = useQuery({
        queryKey: ["human-lock", caseDetail.conversation_id],
        queryFn: async () => {
            const response = await outreachApi.getHumanLockStatus(caseDetail.conversation_id);
            return response.data;
        },
        enabled: canReadOutreach && Boolean(caseDetail.conversation_id),
        refetchInterval: 15000,
    });

    const sendOutreachMutation = useMutation({
        mutationFn: async () => {
            const response = await outreachApi.sendMessage({
                destination: outreachDestination.trim(),
                content: outreachContent.trim(),
                conversation_id: caseDetail.conversation_id,
                branch_id: caseDetail.branch_id || null,
                pause_bot_minutes: outreachPauseEnabled ? pauseMinutes : 0,
                pause_reason: outreachPauseEnabled ? "manual_pause" : undefined,
            });
            return response.data;
        },
        onSuccess: (response) => {
            if (!response.success) {
                const suffix = response.error_code ? ` (${response.error_code})` : "";
                toast.error(`Не удалось отправить outreach${suffix}`);
                return;
            }
            if (response.delivery_status === "queued") {
                toast.success("Outreach поставлен в очередь");
            } else {
                toast.success("Outreach отправлен");
            }
            setOutreachContent("");
            queryClient.invalidateQueries({ queryKey: ["messages", caseId] });
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
            queryClient.invalidateQueries({ queryKey: ["human-lock", caseDetail.conversation_id] });
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "INTEGRATION_UNAVAILABLE") {
                toast.error("Интеграция WhatsApp не настроена для филиала");
                return;
            }
            if (code === "CONVERSATION_REQUIRED") {
                toast.error("Outreach доступен только в рамках заявки");
                return;
            }
            toast.error("Не удалось отправить outreach");
        },
    });

    const pauseMutation = useMutation({
        mutationFn: async () => {
            const response = await outreachApi.pauseHumanLock(caseDetail.conversation_id, {
                minutes: pauseMinutes,
                reason: "manual_pause",
            });
            return response.data;
        },
        onSuccess: () => {
            toast.success("Бот поставлен на паузу");
            queryClient.invalidateQueries({ queryKey: ["human-lock", caseDetail.conversation_id] });
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        },
        onError: () => {
            toast.error("Не удалось включить паузу бота");
        },
    });

    const releasePauseMutation = useMutation({
        mutationFn: async () => {
            const response = await outreachApi.releaseHumanLock(caseDetail.conversation_id);
            return response.data;
        },
        onSuccess: () => {
            toast.success("Пауза бота снята");
            queryClient.invalidateQueries({ queryKey: ["human-lock", caseDetail.conversation_id] });
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        },
        onError: () => {
            toast.error("Не удалось снять паузу бота");
        },
    });

    const isActive = caseDetail.status === "active";
    const isPending = caseDetail.status === "pending";
    const contextText = caseDetail.context_summary || caseDetail.user_message || "Сводка недоступна";
    const contextTitle = caseDetail.context_summary ? "Суть запроса" : "Последнее сообщение";
    const lastInbound = caseDetail.last_inbound_at
        ? new Date(caseDetail.last_inbound_at).toLocaleString("ru-RU")
        : "—";
    const assignedLabel = caseDetail.assigned_to_name ?? "Не назначен";
    const showDetailsToggle = typeof onToggleDetails === "function";
    const detailsLabel = detailsOpen ? "Скрыть детали" : "Детали";
    const isInboxLayout = layout === "inbox";
    const slaCountdown = getSlaCountdown(caseDetail.created_at || new Date().toISOString());
    const issueHints: string[] = [];
    if (caseDetail.has_delivery_error) {
        issueHints.push("Есть ошибка доставки. Ответ мог не дойти до клиента.");
    }
    if (caseDetail.has_pending_outbox) {
        issueHints.push("Есть сообщения в очереди отправки. Доставка может задерживаться.");
    }
    const headerClass = `flex flex-col gap-4 border-b border-border/60 pb-4 ${
        isInboxLayout ? "px-5 pt-5" : ""
    }`;
    const contextClass = `rounded-lg border border-border/60 bg-card p-3 text-sm ${
        isInboxLayout ? "mx-5" : ""
    }`;
    const humanLockStatus = humanLockQuery.data?.status;
    const fallbackLockStatus = {
        active: Boolean(caseDetail.human_lock_active),
        lock_until: caseDetail.human_lock_until ?? null,
        remaining_seconds: caseDetail.human_lock_remaining_seconds ?? null,
        source: caseDetail.human_lock_source ?? null,
        reason: caseDetail.human_lock_reason ?? null,
        locked_by_name: caseDetail.human_lock_by ?? null,
    };
    const effectiveLockStatus = (humanLockStatus ?? fallbackLockStatus) as typeof fallbackLockStatus;
    const lockRemainingSeconds =
        effectiveLockStatus?.remaining_seconds ??
        (effectiveLockStatus?.lock_until
            ? Math.max(
                0,
                Math.floor((new Date(effectiveLockStatus.lock_until).getTime() - Date.now()) / 1000)
            )
            : null);
    const lockRemainingLabel =
        lockRemainingSeconds && lockRemainingSeconds > 0
            ? `${Math.ceil(lockRemainingSeconds / 60)} мин`
            : null;
    const humanLockActive = Boolean(effectiveLockStatus?.active);
    const lockSourceLabel = formatHumanLockLabel(effectiveLockStatus?.source, HUMAN_LOCK_SOURCE_LABELS);
    const lockReasonLabel = formatHumanLockLabel(effectiveLockStatus?.reason, HUMAN_LOCK_REASON_LABELS);
    const lockByLabel = effectiveLockStatus?.locked_by_name || null;
    const lockMeta = [
        lockByLabel ? `Кто: ${lockByLabel}` : null,
        lockReasonLabel ? `Причина: ${lockReasonLabel}` : null,
        lockSourceLabel ? `Источник: ${lockSourceLabel}` : null,
    ]
        .filter(Boolean)
        .join(" · ");
    const outreachBusy =
        sendOutreachMutation.isPending || pauseMutation.isPending || releasePauseMutation.isPending;
    const canSubmitOutreach = Boolean(outreachDestination.trim() && outreachContent.trim());
    const openOutreachPanel = () => {
        setOutreachExpanded(true);
        window.requestAnimationFrame(() => {
            outreachPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    };
    const replyPauseConfig = {
        enabled: replyPauseEnabled,
        minutes: replyPauseMinutes,
        reason: "manual_reply",
    };
    const replyPauseControls = canWrite ? (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border/60 bg-muted/20 px-3 py-2 text-xs">
            <label className="flex items-center gap-2">
                <input
                    type="checkbox"
                    checked={replyPauseEnabled}
                    onChange={(event) => setReplyPauseEnabled(event.target.checked)}
                    className="h-4 w-4 rounded border-border/60 text-primary focus:ring-primary/40"
                    data-testid="reply-pause-toggle"
                />
                Пауза после ответа
            </label>
            <input
                type="number"
                min={0}
                max={1440}
                value={replyPauseMinutes}
                onChange={(event) => {
                    const next = Number(event.target.value);
                    const normalized = Number.isFinite(next) ? Math.min(Math.max(next, 0), 1440) : 0;
                    setReplyPauseMinutes(normalized);
                }}
                disabled={!replyPauseEnabled}
                className="w-20 rounded border border-border/60 bg-background px-2 py-1 text-xs"
                data-testid="reply-pause-minutes"
            />
            <span className="text-muted-foreground">мин</span>
            <div className="flex items-center gap-1">
                {[15, 30, 60, 120].map((preset) => (
                    <button
                        key={preset}
                        type="button"
                        onClick={() => setReplyPauseMinutes(preset)}
                        className="rounded border border-border/60 px-2 py-0.5 text-[10px] font-semibold text-muted-foreground hover:text-foreground"
                        disabled={!replyPauseEnabled}
                        data-testid={`reply-pause-preset-${preset}`}
                    >
                        {preset}
                    </button>
                ))}
            </div>
        </div>
    ) : null;
    const composerExtras = composerBefore ? (
        <div className="flex flex-col gap-2">
            {composerBefore}
            {replyPauseControls}
        </div>
    ) : (
        replyPauseControls
    );
    const humanLockPanel = (
        <div
            className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-xs ${
                humanLockActive
                    ? "border-emerald-200 bg-emerald-50 text-emerald-900"
                    : "border-border/60 bg-muted/30 text-muted-foreground"
            }`}
            data-testid="human-lock-header"
        >
            <div className="flex flex-col gap-1">
                <span className="font-semibold">
                    {humanLockActive
                        ? `Бот на паузе${lockRemainingLabel ? ` · ${lockRemainingLabel}` : ""}`
                        : "Бот активен"}
                </span>
                {humanLockActive && lockMeta && (
                    <span className="text-[11px] text-emerald-900/80">{lockMeta}</span>
                )}
            </div>
            {humanLockActive && canOutreach && (
                <button
                    type="button"
                    onClick={() => releasePauseMutation.mutate()}
                    disabled={releasePauseMutation.isPending}
                    className="rounded border border-emerald-200 bg-white/80 px-2.5 py-1 text-[11px] font-semibold text-emerald-800 hover:bg-white disabled:opacity-50"
                    data-testid="human-lock-release-header"
                >
                    {releasePauseMutation.isPending ? "Снимаем..." : "Снять паузу"}
                </button>
            )}
        </div>
    );

    return (
        <div className={`flex flex-col h-full ${isInboxLayout ? "gap-4" : "gap-5"}`} data-testid="case-conversation">
            <div className={headerClass}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                            <h1 className="text-2xl font-bold" data-testid="case-title">
                                Заявка {caseDetail.id.slice(0, 8)}
                            </h1>
                            <SlaBadge status={caseDetail.sla_status} />
                            <span className={`rounded px-2 py-1 text-[11px] font-medium ${slaCountdown.className}`} data-testid="case-sla-countdown">
                                {slaCountdown.label}
                            </span>
                            {caseDetail.needs_reply && (
                                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-yellow-100 text-yellow-800">
                                    Нужно ответить
                                </span>
                            )}
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                            <span
                                className={`px-2 py-0.5 rounded font-semibold ${caseDetail.status === "resolved"
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
                            <span
                                className={`px-2 py-0.5 rounded font-semibold ${
                                    caseDetail.assigned_to_name ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground"
                                }`}
                            >
                                👤 {assignedLabel}
                            </span>
                        </div>
                    </div>

                    <div className="flex flex-col items-end gap-2">
                        {showDetailsToggle && (
                            <button
                                type="button"
                                onClick={onToggleDetails}
                                className={`inline-flex items-center gap-2 rounded-full border border-border/60 px-3 py-2 text-xs font-semibold transition ${
                                    detailsOpen ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground"
                                }`}
                                aria-pressed={detailsOpen}
                                aria-label={detailsLabel}
                                data-testid="case-details-toggle"
                            >
                                {detailsLabel}
                            </button>
                        )}
                        <div className="flex gap-2">
                            {canOutreach && (
                                <button
                                    type="button"
                                    onClick={openOutreachPanel}
                                    className="rounded border border-border/60 px-4 py-2 text-sm font-semibold text-foreground hover:bg-muted"
                                    data-testid="outreach-open"
                                >
                                    Связаться с клиентом
                                </button>
                            )}
                            {canGoNextCase && (
                                <button
                                    type="button"
                                    onClick={onNextCase}
                                    className="border border-border/60 px-4 py-2 rounded text-sm font-semibold text-muted-foreground hover:text-foreground hover:bg-muted"
                                    data-testid="case-next"
                                >
                                    Следующая заявка
                                </button>
                            )}
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
                                        <>
                                            <button
                                                onClick={() => resolveMutation.mutate()}
                                                disabled={resolveMutation.isPending}
                                                className="bg-foreground text-background px-4 py-2 rounded hover:bg-foreground/90 disabled:opacity-50"
                                            >
                                                {resolveMutation.isPending ? "Закрываем..." : "Закрыть заявку"}
                                            </button>
                                            <button
                                                onClick={() => returnMutation.mutate()}
                                                disabled={returnMutation.isPending}
                                                className="border border-border/60 px-4 py-2 rounded text-sm font-semibold text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
                                            >
                                                {returnMutation.isPending ? "Возвращаем..." : "Вернуть боту"}
                                            </button>
                                        </>
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
                {caseDetail.conversation_id && humanLockPanel}
            </div>

            <div className={contextClass}>
                <div className="flex flex-wrap items-center justify-between text-xs text-muted-foreground mb-1">
                    <span>{contextTitle}</span>
                    <span>Последнее входящее: {lastInbound}</span>
                </div>
                <p className="text-sm text-foreground">{contextText}</p>
            </div>
            {issueHints.length > 0 && (
                <div className={`rounded-lg border border-amber-300/70 bg-amber-50 px-3 py-2 text-xs text-amber-900 ${
                    isInboxLayout ? "mx-5" : ""
                }`}>
                    {issueHints.join(" ")}
                </div>
            )}
            {canOutreach && (
                <div
                    ref={outreachPanelRef}
                    className={`rounded-lg border border-border/60 bg-card px-3 py-3 text-sm ${
                        isInboxLayout ? "mx-5" : ""
                    }`}
                    data-testid="outreach-panel"
                >
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            Ручное сообщение клиенту (WhatsApp)
                        </p>
                        <div className="flex items-center gap-2">
                            <span
                                className={`rounded px-2 py-0.5 text-xs font-semibold ${
                                    humanLockActive
                                        ? "bg-emerald-100 text-emerald-800"
                                        : "bg-muted text-muted-foreground"
                                }`}
                                data-testid="human-lock-badge"
                            >
                                {humanLockActive
                                    ? `Бот на паузе${lockRemainingLabel ? ` (${lockRemainingLabel})` : ""}`
                                    : "Бот активен"}
                            </span>
                            <button
                                type="button"
                                onClick={() => setOutreachExpanded((value) => !value)}
                                className="rounded border border-border/60 px-2 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                data-testid="outreach-toggle"
                            >
                                {outreachExpanded ? "Свернуть" : "Открыть"}
                            </button>
                        </div>
                    </div>
                    {!outreachExpanded && (
                        <p className="rounded border border-border/50 bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
                            Откройте блок, чтобы отправить сообщение клиенту и при необходимости включить паузу бота.
                        </p>
                    )}
                    {outreachExpanded && (
                        <>
                            <div className="grid gap-2 md:grid-cols-[2fr_1fr]">
                                <label className="space-y-1">
                                    <span className="text-xs text-muted-foreground">WhatsApp номер или JID</span>
                                    <input
                                        type="text"
                                        value={outreachDestination}
                                        onChange={(event) => setOutreachDestination(event.target.value)}
                                        className="w-full rounded border border-border/60 bg-background px-3 py-2 text-sm"
                                        placeholder="+7 777 123 45 67"
                                        data-testid="outreach-destination"
                                    />
                                </label>
                                <label className="space-y-1">
                                    <span className="text-xs text-muted-foreground">Пауза (мин)</span>
                                    <input
                                        type="number"
                                        min={0}
                                        max={1440}
                                        value={pauseMinutes}
                                        onChange={(event) => {
                                            const next = Number(event.target.value);
                                            const normalized = Number.isFinite(next) ? Math.min(Math.max(next, 0), 1440) : 0;
                                            setPauseMinutes(normalized);
                                        }}
                                        disabled={!outreachPauseEnabled}
                                        className="w-full rounded border border-border/60 bg-background px-3 py-2 text-sm"
                                        data-testid="human-lock-minutes"
                                    />
                                </label>
                            </div>
                            <label className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                                <input
                                    type="checkbox"
                                    checked={outreachPauseEnabled}
                                    onChange={(event) => setOutreachPauseEnabled(event.target.checked)}
                                    className="h-4 w-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                    data-testid="outreach-pause-toggle"
                                />
                                Ставить паузу после отправки
                            </label>
                            <label className="mt-2 block space-y-1">
                                <span className="text-xs text-muted-foreground">Сообщение клиенту</span>
                                <textarea
                                    value={outreachContent}
                                    onChange={(event) => setOutreachContent(event.target.value)}
                                    rows={3}
                                    className="w-full resize-y rounded border border-border/60 bg-background px-3 py-2 text-sm"
                                    placeholder="Например: Мы на связи, продолжаем вручную"
                                    data-testid="outreach-message"
                                />
                            </label>
                            <div className="mt-3 flex flex-wrap gap-2">
                                <button
                                    type="button"
                                    onClick={() => {
                                        if (!canSubmitOutreach) {
                                            toast.error("Заполните номер и текст сообщения");
                                            return;
                                        }
                                        sendOutreachMutation.mutate();
                                    }}
                                    disabled={outreachBusy || !canSubmitOutreach}
                                    className="rounded bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-50"
                                    data-testid="outreach-send"
                                >
                                    {sendOutreachMutation.isPending ? "Отправка..." : "Отправить клиенту"}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => {
                                        if (!pauseMinutes || pauseMinutes < 1) {
                                            toast.error("Укажите длительность паузы");
                                            return;
                                        }
                                        pauseMutation.mutate();
                                    }}
                                    disabled={outreachBusy}
                                    className="rounded border border-border/60 px-3 py-2 text-xs font-semibold text-foreground disabled:opacity-50"
                                    data-testid="human-lock-pause"
                                >
                                    {pauseMutation.isPending ? "Ставим паузу..." : "Пауза бота"}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => releasePauseMutation.mutate()}
                                    disabled={outreachBusy || !humanLockActive}
                                    className="rounded border border-border/60 px-3 py-2 text-xs font-semibold text-muted-foreground disabled:opacity-50"
                                    data-testid="human-lock-release"
                                >
                                    {releasePauseMutation.isPending ? "Снимаем..." : "Снять паузу"}
                                </button>
                            </div>
                        </>
                    )}
                </div>
            )}

            <div className="flex-1 min-h-0">
                <ChatInterface
                    messages={messages}
                    conversationId={caseDetail.conversation_id}
                    caseId={caseId}
                    isLoading={messagesLoading}
                    hasMoreMessages={messagesHasMore}
                    loadingMoreMessages={messagesLoadingMore}
                    onLoadMoreMessages={onLoadMoreMessages}
                    canSend={canSend}
                    draft={draft}
                    onDraftChange={onDraftChange}
                    composerBefore={composerExtras}
                    pauseConfig={replyPauseConfig}
                    frame={chatFrame}
                />
            </div>
        </div>
    );
}
