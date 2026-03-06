"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import {
    casesApi,
    outreachApi,
    type CaseActionResponse,
    type CaseAssigneeOption,
} from "@/lib/api-client";
import type { Case, Message } from "@/types";
import ChatInterface from "./ChatInterface";
import {
    collectCaseActionFollowupMessages,
    getCaseBusinessStatusBadge,
    getCaseSlaIndicator,
} from "@/utils/labels";

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
    bookingsOpen?: boolean;
    onToggleBookings?: () => void;
    canReadCalendar?: boolean;
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

async function reopenCase(caseId: string): Promise<CaseActionResponse> {
    const response = await casesApi.reopen(caseId);
    return response.data;
}

function extractErrorCode(error: unknown): string | undefined {
    return (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
}

function showActionFollowupWarnings(sync?: CaseActionResponse["sync"] | null) {
    const messages = collectCaseActionFollowupMessages(sync);
    if (messages.length === 0) {
        return;
    }
    toast(messages.join(" "), { icon: "⚠️" });
}

const HUMAN_LOCK_SOURCE_LABELS: Record<string, string> = {
    console_message: "Ответ менеджера",
    console_outreach: "Ручное сообщение",
    console_pause: "Ручная пауза",
    console_media: "Медиа",
};

const HUMAN_LOCK_REASON_LABELS: Record<string, string> = {
    manual_reply: "Ответ менеджера",
    manual_pause: "Ручная пауза",
};

const ASSIGNEE_ROLE_LABELS: Record<string, string> = {
    owner: "Owner",
    admin: "Admin",
    manager: "Manager",
};

const CASE_SNOOZE_PRESETS = [30, 60, 120, 240];

type ActionPanel = "reassign" | "snooze" | null;

function formatHumanLockLabel(value?: string | null, lookup?: Record<string, string>) {
    if (!value) {
        return null;
    }
    if (lookup && lookup[value]) {
        return lookup[value];
    }
    return value;
}

function formatAssigneeLoadLabel(option: CaseAssigneeOption) {
    return `${option.open_case_count ?? 0} в работе`;
}

function formatAssigneeRoleLabel(option: CaseAssigneeOption) {
    const roleLabel = ASSIGNEE_ROLE_LABELS[option.role];
    if (!roleLabel) {
        return null;
    }
    return roleLabel.toLowerCase() === option.agent_name.toLowerCase() ? null : roleLabel;
}

function sortAssigneeOptionsByLoad(options: CaseAssigneeOption[]) {
    return [...options].sort((left, right) => {
        if (left.is_current !== right.is_current) {
            return left.is_current ? -1 : 1;
        }
        const leftLoad = left.open_case_count ?? 0;
        const rightLoad = right.open_case_count ?? 0;
        if (leftLoad !== rightLoad) {
            return leftLoad - rightLoad;
        }
        return left.agent_name.localeCompare(right.agent_name, "ru");
    });
}

function resolveRecommendedAssignee(
    options: CaseAssigneeOption[],
    currentAssigneeId?: string | null,
) {
    const currentOption = currentAssigneeId
        ? options.find((item) => String(item.agent_id) === currentAssigneeId)
        : null;
    const candidateOptions = options.filter((item) => String(item.agent_id) !== (currentAssigneeId ?? ""));
    if (candidateOptions.length === 0) {
        return null;
    }
    const bestCandidate = [...candidateOptions].sort((left, right) => {
        const leftLoad = left.open_case_count ?? 0;
        const rightLoad = right.open_case_count ?? 0;
        if (leftLoad !== rightLoad) {
            return leftLoad - rightLoad;
        }
        return left.agent_name.localeCompare(right.agent_name, "ru");
    })[0];
    if (!currentOption) {
        return bestCandidate;
    }
    return (bestCandidate.open_case_count ?? 0) < (currentOption.open_case_count ?? 0) ? bestCandidate : null;
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
    bookingsOpen = false,
    onToggleBookings,
    canReadCalendar = false,
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
            showActionFollowupWarnings(response.sync);
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
            showActionFollowupWarnings(response.sync);
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
            showActionFollowupWarnings(response.sync);
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

    const isActive = caseDetail.status === "active";
    const isPending = caseDetail.status === "pending";
    const isResolved = caseDetail.status === "resolved";
    const defaultDestination = caseDetail.customer_phone || caseDetail.customer_remote_jid || "";
    const [actionPanel, setActionPanel] = useState<ActionPanel>(null);
    const [selectedAssigneeId, setSelectedAssigneeId] = useState("");
    const [snoozeMinutes, setSnoozeMinutes] = useState(60);
    const [snoozeReason, setSnoozeReason] = useState("");
    const [outreachDestination, setOutreachDestination] = useState(defaultDestination);
    const [outreachContent, setOutreachContent] = useState("");
    const [pauseMinutes, setPauseMinutes] = useState(30);
    const [outreachPauseEnabled, setOutreachPauseEnabled] = useState(true);
    const [replyPauseEnabled, setReplyPauseEnabled] = useState(true);
    const [replyPauseMinutes, setReplyPauseMinutes] = useState(30);
    const [outreachExpanded, setOutreachExpanded] = useState(false);
    const [contextExpanded, setContextExpanded] = useState(layout !== "inbox");
    const outreachPanelRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        setActionPanel(null);
        setSelectedAssigneeId("");
        setSnoozeMinutes(60);
        setSnoozeReason("");
        setOutreachDestination(caseDetail.customer_phone || caseDetail.customer_remote_jid || "");
        setOutreachContent("");
        setPauseMinutes(30);
        setOutreachPauseEnabled(true);
        setReplyPauseEnabled(true);
        setReplyPauseMinutes(30);
        setOutreachExpanded(false);
        setContextExpanded(layout !== "inbox");
    }, [caseId, caseDetail.customer_phone, caseDetail.customer_remote_jid, layout]);

    const assigneeOptionsQuery = useQuery({
        queryKey: ["case-assignees", caseId],
        queryFn: async () => {
            const response = await casesApi.listAssignees(caseId);
            return response.data;
        },
        enabled: canWrite && isActive && actionPanel === "reassign",
        staleTime: 30_000,
    });

    useEffect(() => {
        if (actionPanel !== "reassign") {
            return;
        }
        const items = assigneeOptionsQuery.data?.items ?? [];
        if (items.length === 0) {
            return;
        }
        setSelectedAssigneeId((current) => {
            if (current && items.some((item) => item.agent_id === current)) {
                return current;
            }
            const routedTargetId = assigneeOptionsQuery.data?.routing?.recommended_agent_id;
            const preferred = items.find((item) => String(item.agent_id) === String(routedTargetId))
                ?? items.find((item) => !item.is_current)
                ?? items[0];
            return preferred.agent_id;
        });
    }, [actionPanel, assigneeOptionsQuery.data]);

    const reassignMutation = useMutation({
        mutationFn: async (mode: "manual" | "policy") => {
            if (mode === "policy") {
                const policy = assigneeOptionsQuery.data?.routing?.policy ?? "least_open_cases";
                const response = await casesApi.reassign(caseId, { mode: "policy", policy });
                return { response: response.data, mode };
            }
            const agentId = selectedAssigneeId.trim();
            if (!agentId) {
                throw new Error("assignee_required");
            }
            const response = await casesApi.reassign(caseId, { agent_id: agentId, mode: "manual" });
            return { response: response.data, mode };
        },
        onSuccess: ({ response, mode }) => {
            const routingSummary = response.routing?.reason_summary;
            setActionPanel(null);
            if (mode === "policy" && routingSummary) {
                toast.success(routingSummary);
            } else {
                toast.success(`Заявка передана: ${response.case.assigned_to_name ?? "новый менеджер"}`);
            }
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
            queryClient.invalidateQueries({ queryKey: ["case-assignees", caseId] });
        },
        onError: (error: unknown) => {
            if (error instanceof Error && error.message === "assignee_required") {
                toast.error("Выберите менеджера");
                return;
            }
            const code = extractErrorCode(error);
            if (code === "NOT_ASSIGNED") {
                toast.error("Передавать заявку может только ответственный или администратор");
                return;
            }
            if (code === "CASE_NOT_ACTIVE") {
                toast.error("Передача доступна только для активной заявки");
                return;
            }
            toast.error("Не удалось передать заявку");
        },
    });

    const snoozeMutation = useMutation({
        mutationFn: async () => {
            const minutes = Math.min(Math.max(Number(snoozeMinutes) || 0, 1), 1440);
            const response = await casesApi.snooze(caseId, {
                minutes,
                reason: snoozeReason.trim() || undefined,
            });
            return response.data;
        },
        onSuccess: (response) => {
            setActionPanel(null);
            const untilLabel = response.case.snoozed_until
                ? new Date(response.case.snoozed_until).toLocaleTimeString("ru-RU", {
                    hour: "2-digit",
                    minute: "2-digit",
                })
                : null;
            toast.success(untilLabel ? `Заявка отложена до ${untilLabel}` : "Заявка отложена");
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        },
        onError: (error: unknown) => {
            const code = extractErrorCode(error);
            if (code === "NOT_ASSIGNED") {
                toast.error("Отложить заявку может только ответственный или администратор");
                return;
            }
            if (code === "CASE_NOT_ACTIVE") {
                toast.error("Отложить можно только активную заявку");
                return;
            }
            toast.error("Не удалось отложить заявку");
        },
    });

    const reopenMutation = useMutation({
        mutationFn: () => reopenCase(caseId),
        onSuccess: (response) => {
            toast.success(`Заявка возвращена в работу${response.case.assigned_to_name ? `: ${response.case.assigned_to_name}` : ""}`);
            showActionFollowupWarnings(response.sync);
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        },
        onError: () => {
            toast.error("Не удалось вернуть заявку в работу");
        },
    });

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
                toast.error(`Не удалось отправить ручное сообщение${suffix}`);
                return;
            }
            if (response.delivery_status === "queued") {
                toast.success("Сообщение поставлено в очередь");
            } else {
                toast.success("Сообщение отправлено");
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
                toast.error("Ручное сообщение доступно только в рамках заявки");
                return;
            }
            toast.error("Не удалось отправить ручное сообщение");
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

    const caseActionBusy =
        reassignMutation.isPending || snoozeMutation.isPending || reopenMutation.isPending;
    const sortedAssigneeOptions = useMemo(
        () => sortAssigneeOptionsByLoad(assigneeOptionsQuery.data?.items ?? []),
        [assigneeOptionsQuery.data?.items],
    );
    const fallbackRecommendedAssignee = useMemo(
        () => resolveRecommendedAssignee(sortedAssigneeOptions, caseDetail.assigned_to_id),
        [sortedAssigneeOptions, caseDetail.assigned_to_id],
    );
    const routingRecommendation = assigneeOptionsQuery.data?.routing ?? null;
    const recommendedAssignee = useMemo(
        () => {
            if (routingRecommendation?.recommended_agent_id) {
                return sortedAssigneeOptions.find(
                    (item) => String(item.agent_id) === String(routingRecommendation.recommended_agent_id),
                ) ?? fallbackRecommendedAssignee;
            }
            return fallbackRecommendedAssignee;
        },
        [fallbackRecommendedAssignee, routingRecommendation?.recommended_agent_id, sortedAssigneeOptions],
    );
    const contextText = caseDetail.context_summary || caseDetail.user_message || "Сводка недоступна";
    const compactContextLimit = layout === "inbox" ? 110 : 180;
    const contextTitle = caseDetail.context_summary ? "Суть запроса" : "Последнее сообщение";
    const lastInbound = caseDetail.last_inbound_at
        ? new Date(caseDetail.last_inbound_at).toLocaleString("ru-RU")
        : "—";
    const assignedLabel = caseDetail.assigned_to_name ?? "Не назначен";
    const showDetailsToggle = typeof onToggleDetails === "function";
    const detailsLabel = detailsOpen ? "Скрыть детали" : "Детали";
    const showBookingsToggle = canReadCalendar;
    const bookingsLabel = bookingsOpen ? "Скрыть записи" : "Записи по заявке";
    const isInboxLayout = layout === "inbox";
    const contextCanExpand = isInboxLayout && contextText.length > compactContextLimit;
    const contextBody = contextCanExpand && !contextExpanded
        ? `${contextText.slice(0, compactContextLimit).trimEnd()}...`
        : contextText;
    const headerClass = `flex flex-col gap-4 border-b border-border/60 pb-4 ${
        isInboxLayout ? "px-5 pt-5" : ""
    }`;
    const contextClass = `rounded-lg border border-border/60 bg-card ${isInboxLayout ? "p-2.5" : "p-3"} text-sm ${
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
    const slaIndicator = getCaseSlaIndicator(caseDetail);
    const businessStatus = getCaseBusinessStatusBadge(caseDetail);
    const outreachBusy =
        sendOutreachMutation.isPending || pauseMutation.isPending || releasePauseMutation.isPending;
    const canSubmitOutreach = Boolean(outreachDestination.trim() && outreachContent.trim());
    const toggleOutreachPanel = () => {
        const nextExpanded = !outreachExpanded;
        setOutreachExpanded(nextExpanded);
        if (nextExpanded) {
            window.requestAnimationFrame(() => {
                outreachPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        }
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
    const calendarHref = caseDetail.conversation_id
        ? `/calendar?conversation_id=${encodeURIComponent(caseDetail.conversation_id)}&case_id=${encodeURIComponent(caseId)}&return_panel=bookings`
        : `/calendar?case_id=${encodeURIComponent(caseId)}&return_panel=bookings`;
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
    const currentSnoozeLabel = caseDetail.snoozed_until
        ? new Date(caseDetail.snoozed_until).toLocaleString("ru-RU", {
            day: "2-digit",
            month: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        })
        : null;
    const actionPanelClass = `rounded-lg border border-border/60 bg-card px-4 py-3 text-sm ${
        isInboxLayout ? "mx-5" : ""
    }`;
    const actionPanelContent = actionPanel === "reassign" ? (
        <div className={actionPanelClass} data-testid="case-reassign-panel">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground">Передать заявку</p>
                    <p className="text-xs text-muted-foreground">
                        Смена ответственного без закрытия заявки и потери контекста.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => setActionPanel(null)}
                    className="rounded border border-border/60 px-2 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                >
                    Скрыть
                </button>
            </div>
            <div className="mt-3 space-y-3">
                {assigneeOptionsQuery.isLoading ? (
                    <p className="text-xs text-muted-foreground">Загружаем список менеджеров...</p>
                ) : sortedAssigneeOptions.length ? (
                    <label className="block space-y-1">
                        <span className="text-xs text-muted-foreground">Новый ответственный</span>
                        <select
                            value={selectedAssigneeId}
                            onChange={(event) => setSelectedAssigneeId(event.target.value)}
                            className="w-full rounded border border-border/60 bg-background px-3 py-2 text-sm"
                            data-testid="case-reassign-select"
                        >
                            {sortedAssigneeOptions.map((item) => (
                                <option key={item.agent_id} value={item.agent_id}>
                                    {item.agent_name}
                                    {formatAssigneeRoleLabel(item) ? ` · ${formatAssigneeRoleLabel(item)}` : ""}
                                    {` · ${formatAssigneeLoadLabel(item)}`}
                                    {item.is_current ? " · текущий" : ""}
                                </option>
                            ))}
                        </select>
                        <span className="text-[11px] text-muted-foreground">
                            После текущего ответственного список отсортирован по открытым заявкам.
                        </span>
                        {routingRecommendation && recommendedAssignee && (
                            <span
                                className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-[11px] text-emerald-900"
                                data-testid="case-reassign-recommendation"
                            >
                                {routingRecommendation.reason_summary}
                                {" "}Сейчас у {recommendedAssignee.agent_name} {formatAssigneeLoadLabel(recommendedAssignee)}.
                            </span>
                        )}
                    </label>
                ) : (
                    <p className="text-xs text-muted-foreground">
                        Нет доступных менеджеров для передачи в текущем контексте.
                    </p>
                )}
                <div className="flex flex-wrap gap-2">
                    {recommendedAssignee && (
                        <button
                            type="button"
                            onClick={() => setSelectedAssigneeId(String(recommendedAssignee.agent_id))}
                            disabled={caseActionBusy || selectedAssigneeId === String(recommendedAssignee.agent_id)}
                            className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900 disabled:opacity-50"
                            data-testid="case-reassign-recommend-button"
                        >
                            {selectedAssigneeId === String(recommendedAssignee.agent_id)
                                ? "Рекомендация выбрана"
                                : "Выбрать рекомендацию"}
                        </button>
                    )}
                    {routingRecommendation && (
                        <button
                            type="button"
                            onClick={() => reassignMutation.mutate("policy")}
                            disabled={caseActionBusy || assigneeOptionsQuery.isLoading || !sortedAssigneeOptions.length}
                            className="rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-semibold text-emerald-900 disabled:opacity-50"
                            data-testid="case-reassign-policy-submit"
                        >
                            {reassignMutation.isPending ? "Распределяем..." : "Назначить по политике"}
                        </button>
                    )}
                    <button
                        type="button"
                        onClick={() => reassignMutation.mutate("manual")}
                        disabled={
                            caseActionBusy
                            || assigneeOptionsQuery.isLoading
                            || !sortedAssigneeOptions.length
                            || !selectedAssigneeId
                        }
                        className="rounded bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-50"
                        data-testid="case-reassign-submit"
                    >
                        {reassignMutation.isPending ? "Передаём..." : "Подтвердить передачу"}
                    </button>
                </div>
            </div>
        </div>
    ) : actionPanel === "snooze" ? (
        <div className={actionPanelClass} data-testid="case-snooze-panel">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground">Отложить заявку</p>
                    <p className="text-xs text-muted-foreground">
                        Уберите заявку из срочной очереди до конкретного времени. Новый входящий ответ клиента вернёт её в работу.
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => setActionPanel(null)}
                    className="rounded border border-border/60 px-2 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                >
                    Скрыть
                </button>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-[180px_1fr]">
                <label className="space-y-1">
                    <span className="text-xs text-muted-foreground">На сколько минут</span>
                    <input
                        type="number"
                        min={1}
                        max={1440}
                        value={snoozeMinutes}
                        onChange={(event) => {
                            const next = Number(event.target.value);
                            const normalized = Number.isFinite(next) ? Math.min(Math.max(next, 1), 1440) : 1;
                            setSnoozeMinutes(normalized);
                        }}
                        className="w-full rounded border border-border/60 bg-background px-3 py-2 text-sm"
                        data-testid="case-snooze-minutes"
                    />
                </label>
                <label className="space-y-1">
                    <span className="text-xs text-muted-foreground">Причина для команды</span>
                    <input
                        type="text"
                        value={snoozeReason}
                        onChange={(event) => setSnoozeReason(event.target.value)}
                        className="w-full rounded border border-border/60 bg-background px-3 py-2 text-sm"
                        placeholder="Например: ждём подтверждение времени"
                        maxLength={120}
                        data-testid="case-snooze-reason"
                    />
                </label>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
                {CASE_SNOOZE_PRESETS.map((preset) => (
                    <button
                        key={preset}
                        type="button"
                        onClick={() => setSnoozeMinutes(preset)}
                        className="rounded border border-border/60 px-2 py-1 text-[11px] font-semibold text-muted-foreground hover:text-foreground"
                        data-testid={`case-snooze-preset-${preset}`}
                    >
                        {preset} мин
                    </button>
                ))}
                {currentSnoozeLabel && (
                    <span className="text-xs text-muted-foreground">
                        Сейчас отложено до {currentSnoozeLabel}
                    </span>
                )}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
                <button
                    type="button"
                    onClick={() => snoozeMutation.mutate()}
                    disabled={caseActionBusy}
                    className="rounded bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-50"
                    data-testid="case-snooze-submit"
                >
                    {snoozeMutation.isPending ? "Сохраняем..." : "Отложить заявку"}
                </button>
            </div>
        </div>
    ) : null;

    return (
        <div className={`flex flex-col h-full ${isInboxLayout ? "gap-4" : "gap-5"}`} data-testid="case-conversation">
            <div className={headerClass}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                            <h1 className="text-2xl font-bold" data-testid="case-title">
                                Заявка {caseDetail.id.slice(0, 8)}
                            </h1>
                            <span className={`rounded px-2 py-1 text-[11px] font-semibold ${businessStatus.className}`} data-testid="case-business-status">
                                {businessStatus.label}
                            </span>
                            <span className={`rounded px-2 py-1 text-[11px] font-semibold ${slaIndicator.className}`} data-testid="case-next-action">
                                {slaIndicator.label}
                            </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                            <span data-testid="case-owner-label">
                                Владелец: <span className="font-semibold text-foreground">{assignedLabel}</span>
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
                        <div className="flex flex-wrap justify-end gap-2">
                            {canOutreach && (
                                <button
                                    type="button"
                                    onClick={toggleOutreachPanel}
                                    className="rounded border border-border/60 px-4 py-2 text-sm font-semibold text-foreground hover:bg-muted"
                                    data-testid="outreach-open"
                                >
                                    {outreachExpanded ? "Скрыть блок связи" : "Связаться с клиентом"}
                                </button>
                            )}
                            {showBookingsToggle && (
                                typeof onToggleBookings === "function" ? (
                                    <button
                                        type="button"
                                        onClick={onToggleBookings}
                                        className={`rounded border border-border/60 px-4 py-2 text-sm font-semibold ${
                                            bookingsOpen ? "bg-muted text-foreground" : "text-foreground hover:bg-muted"
                                        }`}
                                        aria-pressed={bookingsOpen}
                                        data-testid="case-open-calendar"
                                    >
                                        {bookingsLabel}
                                    </button>
                                ) : (
                                    <Link
                                        href={calendarHref}
                                        className="rounded border border-border/60 px-4 py-2 text-sm font-semibold text-foreground hover:bg-muted"
                                        data-testid="case-open-calendar"
                                    >
                                        {bookingsLabel}
                                    </Link>
                                )
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
                                            disabled={takeMutation.isPending || caseActionBusy}
                                            className="bg-primary text-primary-foreground px-4 py-2 rounded hover:bg-primary/90 disabled:opacity-50"
                                        >
                                            {takeMutation.isPending ? "Берём..." : "Взять заявку"}
                                        </button>
                                    )}
                                    {isActive && (
                                        <>
                                            <button
                                                type="button"
                                                onClick={() => setActionPanel((current) => current === "reassign" ? null : "reassign")}
                                                disabled={caseActionBusy}
                                                className="rounded border border-border/60 px-4 py-2 text-sm font-semibold text-foreground hover:bg-muted disabled:opacity-50"
                                                data-testid="case-reassign-toggle"
                                            >
                                                {actionPanel === "reassign" ? "Скрыть передачу" : "Передать"}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setActionPanel((current) => current === "snooze" ? null : "snooze")}
                                                disabled={caseActionBusy}
                                                className="rounded border border-border/60 px-4 py-2 text-sm font-semibold text-foreground hover:bg-muted disabled:opacity-50"
                                                data-testid="case-snooze-toggle"
                                            >
                                                {caseDetail.snoozed_until ? "Изменить отсрочку" : "Отложить"}
                                            </button>
                                            <button
                                                onClick={() => resolveMutation.mutate()}
                                                disabled={resolveMutation.isPending || caseActionBusy}
                                                className="bg-foreground text-background px-4 py-2 rounded hover:bg-foreground/90 disabled:opacity-50"
                                            >
                                                {resolveMutation.isPending ? "Закрываем..." : "Закрыть заявку"}
                                            </button>
                                            <button
                                                onClick={() => returnMutation.mutate()}
                                                disabled={returnMutation.isPending || caseActionBusy}
                                                className="border border-border/60 px-4 py-2 rounded text-sm font-semibold text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-50"
                                            >
                                                {returnMutation.isPending ? "Возвращаем..." : "Вернуть боту"}
                                            </button>
                                        </>
                                    )}
                                    {isResolved && (
                                        <button
                                            type="button"
                                            onClick={() => reopenMutation.mutate()}
                                            disabled={reopenMutation.isPending}
                                            className="rounded bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50"
                                            data-testid="case-reopen"
                                        >
                                            {reopenMutation.isPending ? "Возвращаем..." : "Вернуть в работу"}
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
                {caseDetail.conversation_id && humanLockPanel}
            </div>
            {actionPanelContent}

            <div className={contextClass}>
                <div className="flex flex-wrap items-center justify-between text-xs text-muted-foreground mb-1">
                    <span>{contextTitle}</span>
                    <span>Последнее входящее: {lastInbound}</span>
                </div>
                <p className="text-sm text-foreground">{contextBody}</p>
                {contextCanExpand && (
                    <button
                        type="button"
                        onClick={() => setContextExpanded((value) => !value)}
                        className="mt-2 rounded border border-border/60 px-2 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                        data-testid="case-context-toggle"
                    >
                        {contextExpanded ? "Свернуть контекст" : "Показать контекст"}
                    </button>
                )}
            </div>
            {canOutreach && outreachExpanded && (
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
                                onClick={toggleOutreachPanel}
                                className="rounded border border-border/60 px-2 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                data-testid="outreach-toggle"
                            >
                                Свернуть
                            </button>
                        </div>
                    </div>
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
