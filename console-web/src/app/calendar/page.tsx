"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import {
    bookingNeedsAttention,
    cancelBooking,
    collectBookingCaseEffectMessages,
    createBooking,
    fetchBookings,
    getBookingAttentionLabel,
    recordCalendarOperatorEvent,
    registerNoShowFollowUp,
    updateBooking,
    type BookingQueueLane,
    type BookingQueueMode,
    type CalendarOperatorEventRequest,
    type BookingStatusFilter,
    type BookingStatusUpdateRequest,
    updateBookingFollowUpGovernance,
    updateBookingStatus,
} from "@/lib/calendar-bookings";
import {
    buildCalendarBookingActionAvailabilityMap,
    getCalendarActorClassForRole,
    getCalendarVisitActionOptions,
} from "@/lib/calendar-action-registry";
import {
    buildCalendarWorkspaceScope,
    buildInboxWorkspaceScope,
    readCalendarWorkspacePrefs,
    type InboxSidePanelMode,
    writeCalendarWorkspacePrefs,
} from "@/lib/inbox-workspace";
import {
    buildCalendarQueueHref,
    buildCalendarQueueStatePayload,
    findPreferredDefaultSavedView,
    findSavedViewByFingerprint,
    getCalendarQueueStateFingerprint,
    getSavedViewFingerprint,
    isTeamSavedView,
    readCalendarQueueStateFromServer,
    readCalendarQueueStateFromSavedView,
    readCalendarQueueStateFromUrl,
    readQueueStateViewIdFromUrl,
    type CalendarQueueStateSnapshot,
} from "@/lib/queue-state";
import { getBookingStatusLabel, getBookingStatusColor } from "@/utils/labels";
import AccessDenied from "@/components/AccessDenied";
import {
    agentsApi,
    authApi,
    canAccessConsole,
    casesApi,
    type ConsoleRole,
    type QueueSavedView,
    queueStateApi,
} from "@/lib/api-client";
import {
    useCalendarFiltersMachine,
} from "./_lib/useCalendarFiltersMachine";
import { useBookingActionPanelMachine } from "./_lib/useBookingActionPanelMachine";
import {
    type NoShowFollowUpDraft,
    useBookingFollowUpMachine,
} from "./_lib/useBookingFollowUpMachine";
import {
    useBookingComposerMachine,
} from "./_lib/useBookingComposerMachine";

interface Specialist {
    id: string;
    name: string;
    branch_id: string | null;
    branch_name: string | null;
    services: Array<{ name: string; duration_min: number; price: number }>;
    is_active: boolean;
}

interface TimeSlot {
    start: string;
    end: string;
    start_time: string;
    end_time: string;
    available: boolean;
}

type CalendarSecondaryPanelSection = "filters" | "saved_views";
type FollowUpOwnerOption = {
    id: string;
    name: string;
    isTechnical: boolean;
};
type CalendarServiceOption = {
    name: string;
    duration_min: number;
    price: number;
    specialistCount: number;
};

const CALENDAR_STATUS_FILTER_LABELS: Record<BookingStatusFilter, string> = {
    all: "Все статусы",
    scheduled: "Запланированные",
    completed: "Пришёл",
    no_show: "Не пришёл",
    cancelled: "Отменённые",
};

const CALENDAR_SECONDARY_PANEL_TABS: Array<{ id: CalendarSecondaryPanelSection; label: string }> = [
    { id: "filters", label: "Уточнить список" },
    { id: "saved_views", label: "Виды и ссылка" },
];

const TECHNICAL_AGENT_NAME_PATTERNS = [
    /\bconsole\b/i,
    /\bci[-_\s]?console\b/i,
    /^ci(?:[-_\s]|$)/i,
    /\b(system|service|sync|bot|autotest|test)\b/i,
];

async function fetchSpecialists(): Promise<{ items: Specialist[] }> {
    const response = await api.get("/calendar/specialists");
    return response.data;
}

async function fetchSlots(specialistId: string, date: string, duration: number): Promise<{ slots: TimeSlot[] }> {
    const response = await api.get(`/calendar/slots?specialist_id=${specialistId}&date=${date}&duration=${duration}`);
    return response.data;
}

function formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function formatDateLabel(value: string): string {
    if (!value) {
        return "";
    }
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "short",
    });
}

function formatVerboseDateLabel(value: string): string {
    if (!value) {
        return "";
    }
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleDateString("ru-RU", {
        weekday: "long",
        day: "numeric",
        month: "long",
    });
}

function formatBookingRangeLabel(startAt: string, endAt: string): string {
    const start = new Date(startAt);
    const end = new Date(endAt);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        return "";
    }
    return `${start.toLocaleDateString("ru-RU", { day: "numeric", month: "short" })} · ${start.toLocaleTimeString("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
    })} - ${end.toLocaleTimeString("ru-RU", {
        hour: "2-digit",
        minute: "2-digit",
    })}`;
}

function formatDateTimeLocalInput(value: string | null | undefined): string {
    if (!value) {
        return "";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return "";
    }
    const year = parsed.getFullYear();
    const month = String(parsed.getMonth() + 1).padStart(2, "0");
    const day = String(parsed.getDate()).padStart(2, "0");
    const hours = String(parsed.getHours()).padStart(2, "0");
    const minutes = String(parsed.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function formatDueAtLabel(value: string | null | undefined): string | null {
    if (!value) {
        return null;
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return null;
    }
    return parsed.toLocaleString("ru-RU", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatContactTaskOwnerChipLabel(value: string): string {
    return `За звонок отвечает: ${value}`;
}

function formatContactTaskDueChipLabel(value: string | null): string {
    return value ? `Позвонить до: ${value}` : "Срок звонка не задан";
}

function getContactTaskResultLabel(value: string | null | undefined): string {
    return value === "rebooked"
        ? "Результат звонка: клиента переписали"
        : "Результат звонка: с клиентом связались";
}

function formatBookingQuickDateLabel(value: string, today: string, tomorrow: string): string {
    if (value === today) {
        return "Сегодня";
    }
    if (value === tomorrow) {
        return "Завтра";
    }
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleDateString("ru-RU", {
        weekday: "short",
        day: "numeric",
        month: "short",
    });
}

function buildBookingQuickDates(startDate: string, count = 5): string[] {
    const parsed = new Date(`${startDate}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) {
        return [startDate];
    }
    return Array.from({ length: count }, (_, index) => {
        const next = new Date(parsed);
        next.setDate(parsed.getDate() + index);
        return formatDate(next);
    });
}

function getSlotPeriodLabel(startTime: string): "Утро" | "День" | "Вечер" {
    const hours = Number.parseInt(startTime.split(":")[0] ?? "", 10);
    if (Number.isNaN(hours) || hours < 12) {
        return "Утро";
    }
    if (hours < 17) {
        return "День";
    }
    return "Вечер";
}

function normalizeHumanText(value: string | null | undefined): string {
    return (value || "").trim().replace(/\s+/g, " ");
}

function normalizePhoneForSubmit(value: string | null | undefined): string | null {
    const rawValue = (value || "").trim();
    const digits = rawValue.replace(/\D/g, "");
    if (!digits) {
        return null;
    }
    if (digits.length === 10) {
        if (rawValue.startsWith("+") || /^7(?:[\s().-]|$)/.test(rawValue) || /^8(?:[\s().-]|$)/.test(rawValue)) {
            return null;
        }
        return `+7${digits}`;
    }
    if (digits.length === 11 && digits.startsWith("7")) {
        return `+${digits}`;
    }
    if (digits.length === 11 && digits.startsWith("8")) {
        return `+7${digits.slice(1)}`;
    }
    return null;
}

function formatPhoneInput(value: string | null | undefined): string {
    const digits = (value || "").replace(/\D/g, "");
    if (!digits) {
        return "";
    }
    let canonical = digits;
    if (digits.length <= 10) {
        canonical = `7${digits}`;
    } else if (digits.length >= 11 && digits.startsWith("8")) {
        canonical = `7${digits.slice(1)}`;
    } else if (digits.length >= 11 && !digits.startsWith("7")) {
        canonical = `7${digits.slice(-10)}`;
    }
    const limited = canonical.slice(0, 11);
    const country = limited.slice(0, 1);
    const area = limited.slice(1, 4);
    const first = limited.slice(4, 7);
    const second = limited.slice(7, 9);
    const third = limited.slice(9, 11);
    const parts = [`+${country}`];
    if (area) {
        parts.push(area);
    }
    if (first) {
        parts.push(first);
    }
    if (second) {
        parts.push(second);
    }
    if (third) {
        parts.push(third);
    }
    return parts.join(" ");
}

function buildBookingSlot(startAt: string, endAt: string): TimeSlot | null {
    const start = new Date(startAt);
    const end = new Date(endAt);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        return null;
    }
    return {
        start: start.toISOString(),
        end: end.toISOString(),
        start_time: start.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }),
        end_time: end.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }),
        available: true,
    };
}

function isTechnicalAgentName(value: string | null | undefined): boolean {
    const normalized = normalizeHumanText(value);
    if (!normalized) {
        return true;
    }
    if (/^[0-9a-f-]{8,}$/i.test(normalized)) {
        return true;
    }
    return TECHNICAL_AGENT_NAME_PATTERNS.some((pattern) => pattern.test(normalized));
}

function getFollowUpOwnerDisplayLabel({
    name,
    id,
}: {
    name?: string | null;
    id?: string | null;
}): string {
    const normalizedName = normalizeHumanText(name);
    if (normalizedName && !isTechnicalAgentName(normalizedName)) {
        return normalizedName;
    }
    if (normalizedName && isTechnicalAgentName(normalizedName)) {
        return "Служебный аккаунт";
    }
    if (id) {
        return "Скрытая учетная запись";
    }
    return "Не назначено";
}

function getApiErrorMessage(error: unknown, fallback: string): string {
    return (error as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message
        || (error as Error)?.message
        || fallback;
}

function getApiErrorCode(error: unknown): string | undefined {
    return (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
}

async function copyText(text: string): Promise<void> {
    try {
        await navigator.clipboard.writeText(text);
        return;
    } catch {
        window.prompt("Скопируйте ссылку", text);
    }
}

const SAVED_VIEW_SCOPE_LABELS = {
    personal: "Личный",
    team: "Команда",
} as const;
const SAVED_VIEW_ROLE_LABELS: Record<ConsoleRole, string> = {
    platform_admin: "Платформа",
    owner: "Владелец",
    admin: "Админ",
    manager: "Менеджер",
    support: "Поддержка",
    specialist: "Специалист",
    viewer: "Наблюдатель",
};
const SAVED_VIEW_TARGET_ROLES: ConsoleRole[] = [
    "platform_admin",
    "owner",
    "admin",
    "manager",
    "support",
    "specialist",
    "viewer",
];

function getSavedViewBranchLabel(branchId: string | null | undefined, branchMap: Map<string, string>): string | null {
    if (!branchId) {
        return null;
    }
    return branchMap.get(branchId) ?? branchId;
}

function getSavedViewRoleLabel(role: string | null | undefined): string | null {
    if (!role) {
        return null;
    }
    return SAVED_VIEW_ROLE_LABELS[role as ConsoleRole] ?? role;
}

function buildSavedViewOptionLabel(view: QueueSavedView, branchMap: Map<string, string>): string {
    const parts = [view.name, SAVED_VIEW_SCOPE_LABELS[view.scope ?? "personal"]];
    const branchLabel = getSavedViewBranchLabel(view.target_branch_id, branchMap);
    const roleLabel = getSavedViewRoleLabel(view.target_role);
    if (branchLabel) {
        parts.push(branchLabel);
    }
    if (roleLabel) {
        parts.push(roleLabel);
    }
    if (view.is_default) {
        parts.push("основной");
    }
    if (isTeamSavedView(view) && view.is_applicable === false) {
        parts.push("вне текущего контура");
    }
    return parts.join(" · ");
}

function countMatchingSavedViews(
    savedViews: QueueSavedView[],
    {
        scope,
        targetBranchId,
        targetRole,
    }: {
        scope: "personal" | "team";
        targetBranchId: string;
        targetRole: string;
    },
): number {
    return savedViews.filter((view) => {
        if ((view.scope ?? "personal") !== scope) {
            return false;
        }
        if (scope === "personal") {
            return true;
        }
        return (view.target_branch_id ?? "") === targetBranchId
            && (view.target_role ?? "") === targetRole;
    }).length;
}

function hasDefaultSavedViewForTarget(
    savedViews: QueueSavedView[],
    {
        scope,
        targetBranchId,
        targetRole,
    }: {
        scope: "personal" | "team";
        targetBranchId: string;
        targetRole: string;
    },
): boolean {
    return savedViews.some((view) => {
        if (!view.is_default || (view.scope ?? "personal") !== scope) {
            return false;
        }
        if (scope === "personal") {
            return true;
        }
        return (view.target_branch_id ?? "") === targetBranchId
            && (view.target_role ?? "") === targetRole;
    });
}

export default function CalendarPage() {
    const { data: session } = useSession();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();
    const today = formatDate(new Date());
    const tomorrow = formatDate(new Date(Date.now() + 24 * 60 * 60 * 1000));
    const focusedConversationId = searchParams.get("conversation_id") || "";
    const focusedCaseId = searchParams.get("case_id") || "";
    const returnPanelParam = searchParams.get("return_panel");
    const returnPanel: InboxSidePanelMode | null = returnPanelParam === "details"
        ? "details"
        : returnPanelParam === "bookings" || focusedConversationId || focusedCaseId
            ? "bookings"
            : null;

    const { data: meData } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadCalendar = canAccessConsole(role, "calendar", "read");
    const canWriteCalendar = canAccessConsole(role, "calendar", "write");
    const canReadTeam = canAccessConsole(role, "team", "read");
    const canManageTeamPresets = canAccessConsole(role, "team", "write");
    const canManageFollowUpGovernance = canManageTeamPresets;
    const calendarActorClass = useMemo(() => getCalendarActorClassForRole(role), [role]);
    const calendarActionPermissions = useMemo(
        () => ({
            canWriteCalendar,
            canManageFollowUpGovernance,
        }),
        [canManageFollowUpGovernance, canWriteCalendar],
    );
    const selectedBranchId = meData?.selected_branch_id ?? meData?.agent?.branch_id ?? "";
    const selectableBranches = useMemo(
        () => (meData?.branches ?? []).filter((branch) => !!branch.id),
        [meData?.branches],
    );
    const branchMap = useMemo(
        () => new Map(selectableBranches.map((branch) => [branch.id as string, branch.name ?? branch.id as string])),
        [selectableBranches],
    );
    const savedViewTargetRoleOptions = useMemo(
        () => SAVED_VIEW_TARGET_ROLES.filter((item) => canAccessConsole(item, "calendar", "read")),
        [],
    );
    const inboxWorkspaceScope = useMemo(
        () =>
            buildInboxWorkspaceScope({
                role,
                agentId: meData?.agent?.id,
                clientId: meData?.client?.id,
                branchId: selectedBranchId,
            }),
        [role, meData?.agent?.id, meData?.client?.id, selectedBranchId],
    );
    const calendarWorkspaceScope = useMemo(
        () =>
            buildCalendarWorkspaceScope({
                scope: inboxWorkspaceScope,
                caseId: focusedCaseId || null,
                conversationId: focusedConversationId || null,
            }),
        [inboxWorkspaceScope, focusedCaseId, focusedConversationId],
    );
    const restoredCalendarScopeRef = useRef<string | null>(null);
    const lastSavedQueueStateRef = useRef<string>("");
    const bookingPrefillScopeRef = useRef<string>("");
    const saveViewInputRef = useRef<HTMLInputElement | null>(null);
    const defaultQueueMode: BookingQueueMode = focusedConversationId || focusedCaseId ? "history" : "ops";
    const defaultSelectedDate = focusedConversationId || focusedCaseId ? "" : today;
    const defaultQueueLane: BookingQueueLane = defaultQueueMode === "history" ? "all" : "attention";
    const urlSavedViewId = useMemo(
        () => readQueueStateViewIdFromUrl(searchParams),
        [searchParams],
    );
    const urlQueueState = useMemo(
        () =>
            readCalendarQueueStateFromUrl(searchParams, {
                defaultSelectedDate,
                defaultQueueMode,
                defaultQueueLane,
            }),
        [defaultQueueLane, defaultQueueMode, defaultSelectedDate, searchParams],
    );
    const urlQueueStateKey = useMemo(
        () => JSON.stringify({
            viewId: urlSavedViewId,
            queueState: urlQueueState ?? null,
        }),
        [urlQueueState, urlSavedViewId],
    );

    const calendarFiltersMachine = useCalendarFiltersMachine({
        selectedDate: defaultSelectedDate,
        queueMode: defaultQueueMode,
        queueLane: defaultQueueLane,
        queueStatusFilter: "all",
        queueSearch: "",
        followUpOwnerId: "",
        followUpOverdueOnly: false,
    });
    const {
        snapshot: currentQueueSnapshot,
        draft: currentFilterDraft,
        queueFiltersDirty,
        hydrate: hydrateCalendarQueueSnapshot,
        setSelectedDate,
        setQueueMode: setCalendarQueueMode,
        setQueueLane,
        updateDraft: updateCalendarFilterDraft,
        resetDraft: resetQueueFilterDraft,
        applyDraft: applyQueueFilterDraft,
    } = calendarFiltersMachine;
    const {
        selectedDate,
        queueMode,
        queueLane,
        queueStatusFilter,
        queueSearch,
        followUpOwnerId,
        followUpOverdueOnly,
    } = currentQueueSnapshot;
    const {
        queueSearch: draftQueueSearch,
        queueStatusFilter: draftQueueStatusFilter,
        followUpOwnerId: draftFollowUpOwnerId,
        followUpOverdueOnly: draftFollowUpOverdueOnly,
    } = currentFilterDraft;
    const bookingComposerMachine = useBookingComposerMachine<CalendarServiceOption, TimeSlot>({
        initialBookingDate: defaultSelectedDate && defaultSelectedDate >= today ? defaultSelectedDate : today,
        initialCustomerName: "",
        initialCustomerPhoneInput: "",
        getServiceKey: (service) => service?.name ?? "",
        getSlotKey: (slot) => slot ? `${slot.start}|${slot.end}` : "",
    });
    const {
        isOpen: bookingComposerOpen,
        mode: bookingComposerMode,
        editingBookingId,
        selectedService,
        selectedSpecialist,
        bookingDate,
        selectedSlot,
        customerName,
        customerPhoneInput,
        notes,
        isDirty: bookingComposerDirty,
        openCreate: openCreateBookingComposer,
        openEdit: openEditBookingComposerState,
        reset: resetBookingComposer,
        setService: setSelectedService,
        setSpecialist: setSelectedSpecialist,
        setBookingDate,
        setSlot: setSelectedSlot,
        setCustomerName,
        setCustomerPhoneInput,
        setNotes,
        applyCasePrefillIfEmpty,
        restoreBaseline: restoreBookingComposerBaseline,
    } = bookingComposerMachine;
    const bookingActionPanelMachine = useBookingActionPanelMachine();
    const {
        bookingId: bookingActionsBookingId,
        cancelReasonDraft,
        statusUpdateBookingId,
        cancelBookingId,
        isDirty: bookingActionsDirty,
        open: openBookingActionsPanelState,
        close: closeBookingActionsPanelState,
        setCancelReasonDraft,
        setStatusUpdatePending,
        clearStatusUpdatePending,
        setCancelPending,
        clearCancelPending,
    } = bookingActionPanelMachine;
    const bookingFollowUpMachine = useBookingFollowUpMachine();
    const {
        followUpBookingId,
        followUpGovernanceBookingId,
        noShowFollowUpDrafts,
        followUpGovernanceDrafts,
        setFollowUpPending,
        clearFollowUpPending,
        setGovernancePending,
        clearGovernancePending,
        setNoShowDraft,
        clearNoShowDraft,
        setGovernanceDraft,
        clearBooking: clearBookingFollowUpDrafts,
        clearAll: clearAllFollowUpDrafts,
    } = bookingFollowUpMachine;
    const [activeSavedViewId, setActiveSavedViewId] = useState<string | null>(null);
    const [saveViewDraftName, setSaveViewDraftName] = useState("");
    const [saveViewComposerOpen, setSaveViewComposerOpen] = useState(false);
    const [saveViewScopeDraft, setSaveViewScopeDraft] = useState<"personal" | "team">("personal");
    const [saveViewTargetBranchIdDraft, setSaveViewTargetBranchIdDraft] = useState("");
    const [saveViewTargetRoleDraft, setSaveViewTargetRoleDraft] = useState<ConsoleRole | "">("");
    const [saveViewDefaultDraft, setSaveViewDefaultDraft] = useState(false);
    const [saveViewDefaultTouched, setSaveViewDefaultTouched] = useState(false);
    const [selectedTeamTargetBranchIdDraft, setSelectedTeamTargetBranchIdDraft] = useState("");
    const [selectedTeamTargetRoleDraft, setSelectedTeamTargetRoleDraft] = useState<ConsoleRole | "">("");
    const [secondaryPanelOpen, setSecondaryPanelOpen] = useState(false);
    const [secondaryPanelSection, setSecondaryPanelSection] = useState<CalendarSecondaryPanelSection>("filters");

    const currentQueueStateQuery = useQuery({
        queryKey: ["queue-state", "calendar", calendarWorkspaceScope, focusedCaseId, focusedConversationId],
        queryFn: async () => {
            const response = await api.get("/queue-state/current", {
                params: {
                    surface: "calendar",
                    case_id: focusedCaseId || undefined,
                    conversation_id: focusedConversationId || undefined,
                },
            });
            return response.data as {
                found?: boolean;
                query_state?: Record<string, unknown> | null;
                updated_at?: string | null;
            };
        },
        enabled: !!session && canReadCalendar && !!calendarWorkspaceScope,
        retry: 1,
        staleTime: 60_000,
    });
    const savedViewsQuery = useQuery({
        queryKey: ["queue-state-views", "calendar"],
        queryFn: async () => {
            const response = await queueStateApi.listViews("calendar");
            return response.data;
        },
        enabled: !!session && canReadCalendar,
        retry: 1,
        staleTime: 60_000,
    });
    const urlSavedViewQuery = useQuery({
        queryKey: ["queue-state-view", "calendar", urlSavedViewId],
        queryFn: async () => {
            const response = await queueStateApi.getView(urlSavedViewId as string);
            return response.data;
        },
        enabled: !!session && canReadCalendar && !!urlSavedViewId,
        retry: false,
        staleTime: 60_000,
    });
    const followUpOwnersQuery = useQuery({
        queryKey: ["agents", "calendar-follow-up-owners", selectedBranchId],
        queryFn: async () => {
            const response = await agentsApi.list();
            return response.data;
        },
        enabled: !!session && canReadTeam,
        retry: 1,
        staleTime: 60_000,
    });
    const focusedCaseQuery = useQuery({
        queryKey: ["case", focusedCaseId],
        queryFn: async () => {
            const response = await casesApi.get(focusedCaseId);
            return response.data;
        },
        enabled: !!session && canReadCalendar && !!focusedCaseId,
        retry: 1,
        staleTime: 60_000,
    });
    const savedViews = useMemo(
        () => savedViewsQuery.data?.items ?? [],
        [savedViewsQuery.data?.items],
    );
    const followUpOwnerCandidates = useMemo<FollowUpOwnerOption[]>(
        () => (followUpOwnersQuery.data?.items ?? [])
            .filter((agent) => agent.is_active && canAccessConsole(agent.role, "calendar", "write"))
            .filter((agent) => !selectedBranchId || !agent.branch_id || agent.branch_id === selectedBranchId)
            .map((agent) => ({
                id: agent.id,
                name: getFollowUpOwnerDisplayLabel({ name: agent.name, id: agent.id }),
                isTechnical: isTechnicalAgentName(agent.name),
            })),
        [followUpOwnersQuery.data?.items, selectedBranchId],
    );
    const hiddenTechnicalFollowUpOwnersCount = useMemo(
        () => followUpOwnerCandidates.filter((agent) => agent.isTechnical).length,
        [followUpOwnerCandidates],
    );
    const followUpOwnerOptions = useMemo(
        () => followUpOwnerCandidates.filter((agent) => !agent.isTechnical),
        [followUpOwnerCandidates],
    );
    const defaultSavedView = useMemo(
        () => findPreferredDefaultSavedView(savedViews),
        [savedViews],
    );
    const personalSavedViews = useMemo(
        () => savedViews.filter((view) => !isTeamSavedView(view)),
        [savedViews],
    );
    const teamSavedViews = useMemo(
        () => savedViews.filter((view) => isTeamSavedView(view)),
        [savedViews],
    );
    const urlSavedView = useMemo(
        () => urlSavedViewQuery.data ?? savedViews.find((view) => view.id === urlSavedViewId) ?? null,
        [savedViews, urlSavedViewId, urlSavedViewQuery.data],
    );
    const currentQueueFingerprint = useMemo(
        () => getCalendarQueueStateFingerprint(currentQueueSnapshot),
        [currentQueueSnapshot],
    );
    const selectedSavedView = useMemo(
        () => savedViews.find((view) => view.id === activeSavedViewId) ?? null,
        [activeSavedViewId, savedViews],
    );
    const matchingScopeSavedViewCount = useMemo(
        () => countMatchingSavedViews(savedViews, {
            scope: saveViewScopeDraft,
            targetBranchId: saveViewTargetBranchIdDraft,
            targetRole: saveViewTargetRoleDraft,
        }),
        [saveViewScopeDraft, saveViewTargetBranchIdDraft, saveViewTargetRoleDraft, savedViews],
    );
    const suggestedSaveViewDefault = useMemo(
        () => !hasDefaultSavedViewForTarget(savedViews, {
            scope: saveViewScopeDraft,
            targetBranchId: saveViewTargetBranchIdDraft,
            targetRole: saveViewTargetRoleDraft,
        }),
        [saveViewScopeDraft, saveViewTargetBranchIdDraft, saveViewTargetRoleDraft, savedViews],
    );
    const selectedSavedViewScope = selectedSavedView?.scope ?? "personal";
    const selectedSavedViewBranchLabel = getSavedViewBranchLabel(selectedSavedView?.target_branch_id, branchMap);
    const selectedSavedViewRoleLabel = getSavedViewRoleLabel(selectedSavedView?.target_role);
    const canMutateSelectedSavedView = Boolean(
        selectedSavedView && (
            selectedSavedViewScope === "personal"
            || canManageTeamPresets
        ),
    );
    const selectedTeamTargetingDirty = selectedSavedViewScope === "team" && (
        (selectedSavedView?.target_branch_id ?? "") !== selectedTeamTargetBranchIdDraft
        || (selectedSavedView?.target_role ?? "") !== selectedTeamTargetRoleDraft
    );
    const savedViewDirty = selectedSavedView
        ? getSavedViewFingerprint(selectedSavedView) !== currentQueueFingerprint
        : false;
    const savedViewsLoading = savedViewsQuery.isFetching && savedViews.length === 0;
    const queueShareHref = useMemo(() => {
        if (typeof window === "undefined") {
            return "";
        }
        return buildCalendarQueueHref(currentQueueSnapshot, {
            pathname: window.location.pathname,
            currentSearch: window.location.search,
            defaultSelectedDate,
            defaultQueueLane,
            viewId: activeSavedViewId,
        });
    }, [
        activeSavedViewId,
        currentQueueSnapshot,
        defaultQueueLane,
        defaultSelectedDate,
    ]);

    useEffect(() => {
        restoredCalendarScopeRef.current = null;
        lastSavedQueueStateRef.current = "";
        clearAllFollowUpDrafts();
        closeBookingActionsPanelState();
        resetBookingComposer({
            keepOpen: false,
            resetSelections: true,
            bookingDate: defaultSelectedDate && defaultSelectedDate >= today ? defaultSelectedDate : today,
            customerName: "",
            customerPhoneInput: "",
        });
        hydrateCalendarQueueSnapshot({
            selectedDate: defaultSelectedDate,
            queueMode: defaultQueueMode,
            queueLane: defaultQueueLane,
            queueStatusFilter: "all",
            queueSearch: "",
            followUpOwnerId: "",
            followUpOverdueOnly: false,
        });
        setActiveSavedViewId(null);
        setSaveViewDraftName("");
        setSaveViewComposerOpen(false);
        setSaveViewScopeDraft("personal");
        setSaveViewTargetBranchIdDraft("");
        setSaveViewTargetRoleDraft("");
        setSaveViewDefaultDraft(false);
        setSaveViewDefaultTouched(false);
        setSelectedTeamTargetBranchIdDraft("");
        setSelectedTeamTargetRoleDraft("");
    }, [
        calendarWorkspaceScope,
        clearAllFollowUpDrafts,
        closeBookingActionsPanelState,
        defaultQueueLane,
        defaultQueueMode,
        defaultSelectedDate,
        hydrateCalendarQueueSnapshot,
        resetBookingComposer,
        today,
        urlQueueStateKey,
    ]);

    useEffect(() => {
        if (!calendarWorkspaceScope) {
            return;
        }
        const restoreKey = `${calendarWorkspaceScope}::${urlQueueStateKey}`;
        const currentQueueStateSettled = Boolean(urlQueueState)
            || !session
            || currentQueueStateQuery.isFetched
            || currentQueueStateQuery.isError;
        const savedViewsSettled = !session || !canReadCalendar || savedViewsQuery.isFetched || savedViewsQuery.isError;
        const urlSavedViewSettled = !urlSavedViewId || urlSavedViewQuery.isFetched || urlSavedViewQuery.isError;
        if (
            !currentQueueStateSettled
            || !savedViewsSettled
            || !urlSavedViewSettled
            || restoredCalendarScopeRef.current === restoreKey
        ) {
            return;
        }
        const prefs = readCalendarWorkspacePrefs(calendarWorkspaceScope);
        const localSnapshot = prefs
            ? {
                selectedDate: prefs.selectedDate ?? defaultSelectedDate,
                queueMode: prefs.queueMode ?? defaultQueueMode,
                queueLane: prefs.queueLane ?? defaultQueueLane,
                queueStatusFilter: prefs.queueStatusFilter ?? "all",
                queueSearch: prefs.queueSearch ?? "",
                followUpOwnerId: prefs.followUpOwnerId ?? "",
                followUpOverdueOnly: prefs.followUpOverdueOnly ?? false,
            }
            : null;
        const serverSnapshot = readCalendarQueueStateFromServer(currentQueueStateQuery.data, {
            defaultSelectedDate,
            defaultQueueMode,
            defaultQueueLane,
        });
        const urlSavedViewSnapshot = readCalendarQueueStateFromSavedView(urlSavedView, {
            defaultSelectedDate,
            defaultQueueMode,
            defaultQueueLane,
        });
        const defaultSavedViewSnapshot = readCalendarQueueStateFromSavedView(defaultSavedView, {
            defaultSelectedDate,
            defaultQueueMode,
            defaultQueueLane,
        });
        const queueSnapshot = urlQueueState ?? urlSavedViewSnapshot ?? serverSnapshot ?? defaultSavedViewSnapshot ?? localSnapshot;
        const source = urlQueueState
            ? "url"
            : urlSavedViewSnapshot
                ? "url_view"
            : serverSnapshot
                ? "server"
                : defaultSavedViewSnapshot
                    ? "saved_default"
                    : localSnapshot
                    ? "local"
                    : "default";
        const matchedSavedView = (urlSavedView && (source === "url" || source === "url_view"))
            ? urlSavedView
            : source === "saved_default"
            ? defaultSavedView
            : queueSnapshot
                ? findSavedViewByFingerprint(savedViews, getCalendarQueueStateFingerprint(queueSnapshot), {
                    includeNonApplicableTeam: false,
                })
                : null;
        const nextSnapshot = queueSnapshot ?? {
            selectedDate: defaultSelectedDate,
            queueMode: defaultQueueMode,
            queueLane: defaultQueueLane,
            queueStatusFilter: "all" as BookingStatusFilter,
            queueSearch: "",
            followUpOwnerId: "",
            followUpOverdueOnly: false,
        };
        hydrateCalendarQueueSnapshot(nextSnapshot);
        setActiveSavedViewId(matchedSavedView?.id ?? null);
        setSaveViewDraftName("");
        setSaveViewComposerOpen(false);
        setSaveViewScopeDraft("personal");
        setSaveViewTargetBranchIdDraft("");
        setSaveViewTargetRoleDraft("");
        setSaveViewDefaultDraft(false);
        setSaveViewDefaultTouched(false);
        lastSavedQueueStateRef.current = JSON.stringify({
            surface: "calendar",
            case_id: focusedCaseId || undefined,
            conversation_id: focusedConversationId || undefined,
            version: 1,
            query_state: buildCalendarQueueStatePayload(nextSnapshot),
        });
        restoredCalendarScopeRef.current = restoreKey;
    }, [
        calendarWorkspaceScope,
        currentQueueStateQuery.data,
        currentQueueStateQuery.isError,
        currentQueueStateQuery.isFetched,
        defaultQueueLane,
        defaultQueueMode,
        defaultSelectedDate,
        focusedCaseId,
        focusedConversationId,
        session,
        canReadCalendar,
        defaultSavedView,
        savedViews,
        savedViewsQuery.isError,
        savedViewsQuery.isFetched,
        hydrateCalendarQueueSnapshot,
        urlSavedView,
        urlSavedViewId,
        urlSavedViewQuery.isError,
        urlSavedViewQuery.isFetched,
        urlQueueState,
        urlQueueStateKey,
    ]);

    useEffect(() => {
        if (!saveViewComposerOpen) {
            return;
        }
        const timeoutId = window.setTimeout(() => {
            saveViewInputRef.current?.focus();
            saveViewInputRef.current?.select();
        }, 0);
        return () => window.clearTimeout(timeoutId);
    }, [saveViewComposerOpen]);

    useEffect(() => {
        if (!saveViewComposerOpen || saveViewDefaultTouched) {
            return;
        }
        setSaveViewDefaultDraft(suggestedSaveViewDefault);
    }, [saveViewComposerOpen, saveViewDefaultTouched, suggestedSaveViewDefault]);

    useEffect(() => {
        const prefillName = normalizeHumanText(focusedCaseQuery.data?.customer_name);
        const prefillPhone = formatPhoneInput(focusedCaseQuery.data?.customer_phone);
        if (!focusedCaseId || (!prefillName && !prefillPhone)) {
            return;
        }
        const scopeKey = `${focusedCaseId}::${prefillName}::${prefillPhone}`;
        if (bookingPrefillScopeRef.current === scopeKey) {
            return;
        }
        applyCasePrefillIfEmpty(prefillName, prefillPhone);
        bookingPrefillScopeRef.current = scopeKey;
    }, [
        applyCasePrefillIfEmpty,
        customerName,
        customerPhoneInput,
        focusedCaseId,
        focusedCaseQuery.data?.customer_name,
        focusedCaseQuery.data?.customer_phone,
    ]);

    useEffect(() => {
        if (selectedSavedViewScope !== "team") {
            setSelectedTeamTargetBranchIdDraft("");
            setSelectedTeamTargetRoleDraft("");
            return;
        }
        setSelectedTeamTargetBranchIdDraft(selectedSavedView?.target_branch_id ?? "");
        setSelectedTeamTargetRoleDraft(selectedSavedView?.target_role ?? "");
    }, [
        selectedSavedView?.id,
        selectedSavedView?.target_branch_id,
        selectedSavedView?.target_role,
        selectedSavedViewScope,
    ]);

    useEffect(() => {
        if (activeSavedViewId && selectedSavedView) {
            return;
        }
        if (activeSavedViewId && !selectedSavedView && !savedViewsQuery.isFetching) {
            setActiveSavedViewId(null);
            return;
        }
        if (activeSavedViewId || savedViews.length === 0) {
            return;
        }
        const matchedSavedView = findSavedViewByFingerprint(savedViews, currentQueueFingerprint, {
            includeNonApplicableTeam: false,
        });
        if (matchedSavedView) {
            setActiveSavedViewId(matchedSavedView.id);
        }
    }, [
        activeSavedViewId,
        currentQueueFingerprint,
        savedViews,
        savedViewsQuery.isFetching,
        selectedSavedView,
    ]);

    useEffect(() => {
        if (!restoredCalendarScopeRef.current || typeof window === "undefined") {
            return;
        }
        if (!queueShareHref) {
            return;
        }
        const currentHref = `${window.location.pathname}${window.location.search}`;
        if (currentHref === queueShareHref) {
            return;
        }
        window.history.replaceState(window.history.state, "", queueShareHref);
    }, [queueShareHref]);

    useEffect(() => {
        if (!calendarWorkspaceScope || !restoredCalendarScopeRef.current) {
            return;
        }
        writeCalendarWorkspacePrefs(calendarWorkspaceScope, {
            selectedDate,
            queueMode,
            queueLane,
            queueStatusFilter,
            queueSearch,
            followUpOwnerId,
            followUpOverdueOnly,
        });
    }, [
        calendarWorkspaceScope,
        followUpOverdueOnly,
        followUpOwnerId,
        queueLane,
        queueMode,
        queueSearch,
        queueStatusFilter,
        selectedDate,
    ]);

    useEffect(() => {
        if (!calendarWorkspaceScope || !session || !canReadCalendar || !restoredCalendarScopeRef.current) {
            return;
        }
        const payload = {
            surface: "calendar" as const,
            case_id: focusedCaseId || undefined,
            conversation_id: focusedConversationId || undefined,
            version: 1,
            query_state: buildCalendarQueueStatePayload(currentQueueSnapshot),
        };
        const fingerprint = JSON.stringify(payload);
        if (lastSavedQueueStateRef.current === fingerprint) {
            return;
        }
        const timeoutId = window.setTimeout(() => {
            if (lastSavedQueueStateRef.current === fingerprint) {
                return;
            }
            lastSavedQueueStateRef.current = fingerprint;
            void api.put("/queue-state/current", payload).catch(() => {
                if (lastSavedQueueStateRef.current === fingerprint) {
                    lastSavedQueueStateRef.current = "";
                }
            });
        }, 250);
        return () => window.clearTimeout(timeoutId);
    }, [
        calendarWorkspaceScope,
        canReadCalendar,
        currentQueueSnapshot,
        focusedCaseId,
        focusedConversationId,
        session,
    ]);

    // Queries
    const {
        data: specialistsData,
        isError: specialistsError,
        error: specialistsErrorData,
    } = useQuery({
        queryKey: ["specialists"],
        queryFn: fetchSpecialists,
        enabled: !!session && canReadCalendar,
        retry: 1,
    });

    const specialists = useMemo(
        () => specialistsData?.items ?? [],
        [specialistsData?.items],
    );
    const activeSpecialists = useMemo(
        () => specialists.filter((specialist) => specialist.is_active),
        [specialists],
    );
    const serviceCatalog = useMemo<CalendarServiceOption[]>(() => {
        const services = new Map<string, CalendarServiceOption>();
        activeSpecialists.forEach((specialist) => {
            specialist.services.forEach((service) => {
                const serviceName = normalizeHumanText(service.name);
                if (!serviceName) {
                    return;
                }
                const existing = services.get(serviceName);
                if (!existing) {
                    services.set(serviceName, {
                        name: serviceName,
                        duration_min: service.duration_min,
                        price: service.price,
                        specialistCount: 1,
                    });
                    return;
                }
                services.set(serviceName, {
                    ...existing,
                    duration_min: Math.min(existing.duration_min, service.duration_min),
                    price: Math.min(existing.price, service.price),
                    specialistCount: existing.specialistCount + 1,
                });
            });
        });
        return [...services.values()].sort((left, right) => left.name.localeCompare(right.name, "ru"));
    }, [activeSpecialists]);
    const specialistsForSelectedService = useMemo(
        () => selectedService
            ? activeSpecialists.filter((specialist) =>
                specialist.services.some((service) => normalizeHumanText(service.name) === selectedService.name))
            : [],
        [activeSpecialists, selectedService],
    );
    const currentSpecialist = activeSpecialists.find((specialist) => specialist.id === selectedSpecialist);
    const selectedSpecialistService = useMemo(
        () => currentSpecialist?.services.find((service) => normalizeHumanText(service.name) === selectedService?.name) ?? null,
        [currentSpecialist, selectedService],
    );
    const selectedServicePrice = selectedSpecialistService?.price ?? selectedService?.price ?? null;
    const selectedServiceDuration = selectedSpecialistService?.duration_min ?? selectedService?.duration_min ?? 60;
    const bookingDateSuggestion = selectedDate && selectedDate >= today ? selectedDate : today;

    const {
        data: slotsData,
        isLoading: slotsLoading,
        isError: slotsError,
        error: slotsErrorData,
        refetch: refetchSlots,
    } = useQuery({
        queryKey: ["slots", selectedSpecialist, bookingDate, selectedServiceDuration],
        queryFn: () => fetchSlots(selectedSpecialist, bookingDate, selectedServiceDuration),
        enabled: !!session && canReadCalendar && !!selectedSpecialist && !!bookingDate && !!selectedService,
        retry: 1,
    });

    const slots = useMemo(
        () => slotsData?.slots ?? [],
        [slotsData?.slots],
    );
    const groupedSlots = useMemo(() => {
        const groups = new Map<"Утро" | "День" | "Вечер", TimeSlot[]>();
        slots.forEach((slot) => {
            const period = getSlotPeriodLabel(slot.start_time);
            const current = groups.get(period) ?? [];
            current.push(slot);
            groups.set(period, current);
        });
        return [
            { label: "Утро" as const, slots: groups.get("Утро") ?? [] },
            { label: "День" as const, slots: groups.get("День") ?? [] },
            { label: "Вечер" as const, slots: groups.get("Вечер") ?? [] },
        ].filter((group) => group.slots.length > 0);
    }, [slots]);
    const bookingQuickDates = useMemo(
        () => buildBookingQuickDates(bookingDateSuggestion, 5),
        [bookingDateSuggestion],
    );

    useEffect(() => {
        if (!selectedService || !selectedSpecialist) {
            return;
        }
        const stillAvailable = specialistsForSelectedService.some((specialist) => specialist.id === selectedSpecialist);
        if (!stillAvailable) {
            setSelectedSpecialist("");
            setSelectedSlot(null);
        }
    }, [selectedService, selectedSlot, selectedSpecialist, setSelectedSlot, setSelectedSpecialist, specialistsForSelectedService]);

    const { data: bookingsData, isLoading: bookingsLoading } = useQuery({
        queryKey: [
            "bookings",
            selectedDate,
            focusedConversationId,
            focusedCaseId,
            queueMode,
            queueLane,
            queueStatusFilter,
            followUpOwnerId,
            followUpOverdueOnly,
        ],
        queryFn: () =>
            fetchBookings({
                date: selectedDate || undefined,
                conversationId: focusedConversationId || undefined,
                caseId: focusedCaseId || undefined,
                lane: queueMode === "history" ? "all" : queueLane,
                status: queueStatusFilter,
                followUpOwnerId: followUpOwnerId || undefined,
                followUpOverdue: followUpOverdueOnly || undefined,
            }),
        enabled: !!session && canReadCalendar,
    });

    const bookings = useMemo(() => bookingsData?.items ?? [], [bookingsData?.items]);
    const bookingsSorted = useMemo(() => {
        return [...bookings].sort((left, right) => {
            if (queueMode === "history") {
                return new Date(right.start_at).getTime() - new Date(left.start_at).getTime();
            }
            const leftPriority = bookingNeedsAttention(left) ? 1 : 0;
            const rightPriority = bookingNeedsAttention(right) ? 1 : 0;
            if (leftPriority !== rightPriority) {
                return rightPriority - leftPriority;
            }
            return new Date(left.start_at).getTime() - new Date(right.start_at).getTime();
        });
    }, [bookings, queueMode]);
    const attentionCount = bookingsSorted.filter((booking) => bookingNeedsAttention(booking)).length;
    const noShowAttentionCount = bookingsSorted.filter(
        (booking) => booking.status.toUpperCase() === "NO_SHOW" && !booking.no_show_followup_done
    ).length;
    const queueSearchNormalized = queueSearch.trim().toLowerCase();
    const bookingsVisible = useMemo(() => {
        return bookingsSorted.filter((booking) => {
            if (!queueSearchNormalized) {
                return true;
            }
            const haystack = [
                booking.customer_name || "",
                booking.customer_phone || "",
                booking.service_type || "",
                booking.specialist_name || "",
                booking.id || "",
            ]
                .join(" ")
                .toLowerCase();
            return haystack.includes(queueSearchNormalized);
        });
    }, [bookingsSorted, queueSearchNormalized]);
    const queueHeading = selectedDate
        ? `Записи на ${formatDateLabel(selectedDate)}`
        : queueMode === "history"
            ? "Архив записей"
            : "Записи";
    const followUpOwnerFilterLabel = followUpOwnerId
        ? followUpOwnerCandidates.find((agent) => agent.id === followUpOwnerId)?.name
            ?? getFollowUpOwnerDisplayLabel({ id: followUpOwnerId })
        : null;
    const queueSummaryChips = [
        queueMode === "history"
            ? {
                key: "mode",
                label: "История",
            }
            : {
                key: "lane",
                label: queueLane === "attention" ? "Нужны действия" : "Все записи",
            },
        selectedDate
            ? {
                key: "date",
                label: `День: ${formatDateLabel(selectedDate)}`,
            }
            : queueMode === "history"
                ? {
                    key: "date",
                    label: "Все даты",
                }
                : null,
        queueSearch.trim()
            ? {
                key: "search",
                label: `Найти: ${queueSearch.trim()}`,
            }
            : null,
        queueStatusFilter !== "all"
            ? {
                key: "status",
                label: `Статус: ${CALENDAR_STATUS_FILTER_LABELS[queueStatusFilter]}`,
            }
            : null,
        followUpOwnerFilterLabel
            ? {
                key: "owner",
                label: `Звонок: ${followUpOwnerFilterLabel}`,
            }
            : null,
        followUpOverdueOnly
            ? {
                key: "overdue",
                label: "Только просроченные звонки",
            }
            : null,
        selectedSavedView
            ? {
                key: "view",
                label: `Вид: ${selectedSavedView.name}`,
            }
            : null,
    ].filter((chip): chip is { key: string; label: string } => Boolean(chip));
    const schedulingSummary = [
        selectedService?.name ?? null,
        selectedSpecialist
            ? activeSpecialists.find((specialist) => specialist.id === selectedSpecialist)?.name ?? selectedSpecialist
            : null,
        bookingDate
            ? formatDateLabel(bookingDate)
            : null,
        selectedSlot?.start_time ?? null,
    ].filter((part): part is string => Boolean(part));
    const queueScopeHint = queueMode === "history" && !selectedDate
        ? "Архив сейчас показывает все даты. Укажите день, только если хотите сузить список."
        : focusedConversationId && !selectedDate
            ? "Сейчас показываем все даты по этой заявке. Выберите дату, только если хотите сузить список."
            : null;
    const schedulingSummaryLabel = schedulingSummary.length > 0
        ? schedulingSummary.join(" · ")
        : "Выберите услугу, мастера, день и время для новой записи.";
    const prefilledCaseName = normalizeHumanText(focusedCaseQuery.data?.customer_name);
    const prefilledCasePhone = formatPhoneInput(focusedCaseQuery.data?.customer_phone);
    const hasCasePrefill = Boolean(prefilledCaseName || prefilledCasePhone);
    const normalizedCustomerName = normalizeHumanText(customerName);
    const normalizedCustomerPhone = normalizePhoneForSubmit(customerPhoneInput);
    const normalizedCustomerPhoneDisplay = normalizedCustomerPhone
        ? formatPhoneInput(normalizedCustomerPhone)
        : "";
    const shouldShowBookingValidation = Boolean(
        selectedSpecialist || selectedService || selectedSlot || normalizedCustomerName || customerPhoneInput,
    );
    const shouldShowCustomerValidation = Boolean(selectedSlot || normalizedCustomerName || customerPhoneInput);
    const bookingFormErrors = {
        service: selectedService
            ? null
            : "Выберите услугу.",
        specialist: !selectedService
            ? null
            : specialistsForSelectedService.length === 0
                ? "Для этой услуги пока нет доступных мастеров."
                : selectedSpecialist
                    ? null
                    : "Выберите мастера.",
        bookingDate: !selectedService || !selectedSpecialist
            ? null
            : bookingDate
                ? null
                : "Выберите день новой записи.",
        slot: !selectedService || !selectedSpecialist || !bookingDate
            ? null
            : selectedSlot
                ? null
                : "Выберите свободное время.",
        customerName: !normalizedCustomerName
            ? "Укажите имя клиента."
            : normalizedCustomerName.length < 2
                ? "Имя должно содержать минимум 2 символа."
                : null,
        customerPhone: !normalizedCustomerPhone
            ? "Укажите телефон в формате +7 700 123 45 67."
            : null,
    };
    const bookingFormErrorList = Object.values(bookingFormErrors).filter((value): value is string => Boolean(value));
    const visibleBookingFormErrorList = [
        shouldShowBookingValidation ? bookingFormErrors.service : null,
        selectedService ? bookingFormErrors.specialist : null,
        shouldShowBookingValidation ? bookingFormErrors.bookingDate : null,
        selectedSpecialist ? bookingFormErrors.slot : null,
        shouldShowCustomerValidation ? bookingFormErrors.customerName : null,
        shouldShowCustomerValidation ? bookingFormErrors.customerPhone : null,
    ].filter((value): value is string => Boolean(value));
    const bookingFormReady = bookingFormErrorList.length === 0 && canWriteCalendar;
    const bookingSlotState = !selectedService
        ? {
            kind: "blocked" as const,
            title: "Сначала выберите услугу",
            description: "Услуга задаёт длительность визита и помогает показать правильное свободное время.",
        }
        : specialistsForSelectedService.length === 0
            ? {
                kind: "blocked" as const,
                title: "Для этой услуги пока нет доступных мастеров",
                description: "Выберите другую услугу или сначала настройте услуги у мастеров.",
            }
            : !selectedSpecialist
                ? {
                    kind: "blocked" as const,
                    title: "Выберите мастера",
                    description: "Покажем свободное время только для мастеров, которые делают эту услугу.",
                }
                : !bookingDate
                    ? {
                        kind: "blocked" as const,
                        title: "Выберите день",
                        description: "После выбора дня покажем свободное время для этого мастера.",
                    }
                    : slotsLoading
                        ? {
                            kind: "loading" as const,
                            title: "Ищем свободное время",
                            description: "Собираем доступные слоты для выбранных услуги, мастера и дня.",
                        }
                        : slotsError
                            ? {
                                kind: "error" as const,
                                title: "Не удалось загрузить свободное время",
                                description: getApiErrorMessage(slotsErrorData, "Повторите попытку или выберите другой день."),
                            }
                            : slots.length === 0
                                ? {
                                    kind: "empty" as const,
                                    title: `На ${formatVerboseDateLabel(bookingDate)} свободного времени нет`,
                                    description: "Выберите другой день или другого мастера — рабочий список сверху не изменится.",
                                }
                                : {
                                    kind: "ready" as const,
                                    title: `Свободное время на ${formatVerboseDateLabel(bookingDate)}`,
                                    description: "Выберите удобный слот, затем подтвердите данные клиента.",
                                };
    const customerStepState = normalizedCustomerName && normalizedCustomerPhone
        ? "ready"
        : normalizedCustomerName || customerPhoneInput
            ? "review"
            : "empty";
    const bookingNextAction = !selectedService
        ? {
            title: "1. Выберите услугу",
            description: "От услуги зависит длительность визита и список мастеров.",
        }
        : specialistsForSelectedService.length === 0
            ? {
                title: "Выберите другую услугу",
                description: "Для текущей услуги пока нет доступных мастеров.",
            }
            : !selectedSpecialist
                ? {
                    title: "2. Выберите мастера",
                    description: "Покажем только тех специалистов, которые делают выбранную услугу.",
                }
                : !bookingDate
                    ? {
                        title: "3. Выберите день",
                        description: "Можно взять ближайший день из быстрых кнопок или указать дату вручную.",
                    }
                    : bookingSlotState.kind === "loading"
                        ? {
                            title: "Ищем свободное время",
                            description: "Подождите несколько секунд, пока загрузятся слоты.",
                        }
                        : bookingSlotState.kind === "error"
                            ? {
                                title: "Повторите поиск времени",
                                description: "Попробуйте ещё раз или переключитесь на другой день.",
                            }
                            : bookingSlotState.kind === "empty"
                                ? {
                                    title: "Выберите другой день",
                                    description: "На текущий день времени нет — переключитесь на следующий или выберите другого мастера.",
                                }
                                : !selectedSlot
                                    ? {
                                        title: "4. Выберите время",
                                        description: "Нажмите на удобный слот, чтобы перейти к данным клиента.",
                                    }
                                    : !normalizedCustomerName
                                        ? {
                                            title: "5. Заполните имя клиента",
                                            description: "Укажите, как обращаться к клиенту при звонке и подтверждении записи.",
                                        }
                                        : !normalizedCustomerPhone
                                            ? {
                                                title: "Добавьте телефон клиента",
                                                description: "Номер нужен, чтобы быстро связаться и подтвердить запись.",
                                            }
                                            : {
                                                title: bookingComposerMode === "edit" ? "Сохраните изменения" : "Подтвердите и создайте запись",
                                                description: bookingComposerMode === "edit"
                                                    ? "Все обязательные данные заполнены. Проверьте сводку справа и сохраните изменения."
                                                    : "Все обязательные данные заполнены. Проверьте сводку справа и сохраните запись.",
                                            };
    const bookingActionsBooking = bookingActionsBookingId
        ? bookings.find((booking) => booking.id === bookingActionsBookingId) ?? null
        : null;
    const editingBooking = editingBookingId
        ? bookings.find((booking) => booking.id === editingBookingId) ?? null
        : null;
    const selectedSlotVisibleInChoices = selectedSlot
        ? slots.some((slot) => slot.start === selectedSlot.start && slot.end === selectedSlot.end)
        : false;
    const showPinnedEditSlot = bookingComposerMode === "edit" && Boolean(selectedSlot && !selectedSlotVisibleInChoices);
    const bookingComposerTitle = bookingComposerMode === "edit" ? "Изменить запись" : "Новая запись";
    const bookingComposerDescription = bookingComposerMode === "edit"
        ? "Проверьте услугу, мастера, день, время и контакты клиента. Если меняете расписание, список слотов подскажет, что ещё свободно."
        : "Здесь оператор проходит один понятный путь: услуга, мастер, день, время, клиент, подтверждение.";
    const bookingResetLabel = bookingComposerMode === "edit" ? "Вернуть данные записи" : "Очистить всё";
    const bookingSubmitLabel = bookingComposerMode === "edit" ? "Сохранить изменения" : "Подтвердить и создать запись";
    const bookingActionsNoShowDraft = bookingActionsBooking
        ? noShowFollowUpDrafts[bookingActionsBooking.id]
        : null;
    const bookingActionsGovernanceDraft = bookingActionsBooking
        ? followUpGovernanceDrafts[bookingActionsBooking.id]
        : null;
    const bookingActionsDefaultDueInput = formatDateTimeLocalInput(bookingActionsBooking?.follow_up_due_at);
    const bookingActionsNoShowDirty = Boolean(
        bookingActionsNoShowDraft
        && (
            bookingActionsNoShowDraft.result !== "contacted"
            || bookingActionsNoShowDraft.rebookedAppointmentId
            || bookingActionsNoShowDraft.note
        ),
    );
    const bookingActionsGovernanceDirty = Boolean(
        bookingActionsBooking
        && bookingActionsGovernanceDraft
        && (
            bookingActionsGovernanceDraft.ownerAgentId !== (bookingActionsBooking.follow_up_owner_id ?? "")
            || bookingActionsGovernanceDraft.dueAt !== bookingActionsDefaultDueInput
        ),
    );
    const bookingActionPanelHasUnsavedChanges = bookingActionsDirty || bookingActionsNoShowDirty || bookingActionsGovernanceDirty;

    useEffect(() => {
        if (bookingActionsBookingId && !bookingActionsBooking) {
            closeBookingActionsPanelState();
        }
    }, [bookingActionsBooking, bookingActionsBookingId, closeBookingActionsPanelState]);

    useEffect(() => {
        if (editingBookingId && !editingBooking) {
            resetBookingComposer({
                keepOpen: false,
                resetSelections: true,
                bookingDate: bookingDateSuggestion,
                customerName: normalizeHumanText(focusedCaseQuery.data?.customer_name),
                customerPhoneInput: formatPhoneInput(focusedCaseQuery.data?.customer_phone),
            });
        }
    }, [
        bookingDateSuggestion,
        editingBooking,
        editingBookingId,
        focusedCaseQuery.data?.customer_name,
        focusedCaseQuery.data?.customer_phone,
        resetBookingComposer,
    ]);

    const applyCalendarQueueSnapshot = (
        snapshot: CalendarQueueStateSnapshot,
        {
            savedViewId = null,
        }: {
            savedViewId?: string | null;
        } = {},
    ) => {
        hydrateCalendarQueueSnapshot(snapshot);
        setActiveSavedViewId(savedViewId);
        clearAllFollowUpDrafts();
        setSaveViewDraftName("");
        setSaveViewComposerOpen(false);
        setSaveViewScopeDraft("personal");
        setSaveViewTargetBranchIdDraft("");
        setSaveViewTargetRoleDraft("");
        setSaveViewDefaultDraft(false);
        setSaveViewDefaultTouched(false);
    };

    const createSavedViewMutation = useMutation({
        mutationFn: async (payload: {
            name: string;
            isDefault: boolean;
            scope: "personal" | "team";
            targetBranchId: string;
            targetRole: ConsoleRole | "";
        }) => {
            const response = await queueStateApi.createView({
                surface: "calendar",
                name: payload.name,
                scope: payload.scope,
                version: 1,
                query_state: buildCalendarQueueStatePayload(currentQueueSnapshot),
                is_default: payload.isDefault,
                target_branch_id: payload.scope === "team" ? (payload.targetBranchId || null) : null,
                target_role: payload.scope === "team" ? (payload.targetRole || null) : null,
            });
            return response.data;
        },
        onSuccess: async (savedView) => {
            setActiveSavedViewId(savedView.id);
            setSaveViewDraftName("");
            setSaveViewComposerOpen(false);
            setSaveViewScopeDraft("personal");
            setSaveViewTargetBranchIdDraft("");
            setSaveViewTargetRoleDraft("");
            setSaveViewDefaultDraft(false);
            setSaveViewDefaultTouched(false);
            await queryClient.invalidateQueries({ queryKey: ["queue-state-views", "calendar"] });
            toast.success(`Вид «${savedView.name}» сохранён`);
        },
        onError: (error: unknown) => {
            toast.error(getApiErrorMessage(error, "Не удалось сохранить вид"));
        },
    });

    const updateSavedViewMutation = useMutation({
        mutationFn: async (payload: {
            viewId: string;
            queryState?: Record<string, unknown>;
            isDefault?: boolean;
            targetBranchId?: string | null;
            targetRole?: ConsoleRole | null;
        }) => {
            const response = await queueStateApi.updateView(payload.viewId, {
                query_state: payload.queryState,
                is_default: payload.isDefault,
                target_branch_id: payload.targetBranchId,
                target_role: payload.targetRole,
            });
            return response.data;
        },
        onSuccess: async (savedView) => {
            setActiveSavedViewId(savedView.id);
            setSelectedTeamTargetBranchIdDraft(savedView.target_branch_id ?? "");
            setSelectedTeamTargetRoleDraft(savedView.target_role ?? "");
            await queryClient.invalidateQueries({ queryKey: ["queue-state-views", "calendar"] });
            toast.success(`Вид «${savedView.name}» обновлён`);
        },
        onError: (error: unknown) => {
            toast.error(getApiErrorMessage(error, "Не удалось обновить вид"));
        },
    });

    const deleteSavedViewMutation = useMutation({
        mutationFn: async (viewId: string) => {
            await queueStateApi.deleteView(viewId);
            return viewId;
        },
        onSuccess: async (viewId) => {
            if (activeSavedViewId === viewId) {
                setActiveSavedViewId(null);
            }
            await queryClient.invalidateQueries({ queryKey: ["queue-state-views", "calendar"] });
            toast.success("Вид удалён");
        },
        onError: (error: unknown) => {
            toast.error(getApiErrorMessage(error, "Не удалось удалить вид"));
        },
    });
    const savedViewMutationPending = createSavedViewMutation.isPending
        || updateSavedViewMutation.isPending
        || deleteSavedViewMutation.isPending;

    const handleCopyQueueLink = async () => {
        if (!queueShareHref || typeof window === "undefined") {
            toast.error("Не удалось собрать ссылку на очередь");
            return;
        }
        const absoluteHref = new URL(queueShareHref, window.location.origin).toString();
        await copyText(absoluteHref);
        toast.success("Ссылка на очередь скопирована");
    };

    const handleOpenSaveViewComposer = () => {
        setSaveViewDraftName("");
        const nextScope = canManageTeamPresets && selectedSavedViewScope === "team"
            ? "team"
            : "personal";
        const nextTargetBranchId = nextScope === "team" ? (selectedSavedView?.target_branch_id ?? "") : "";
        const nextTargetRole = nextScope === "team" ? (selectedSavedView?.target_role ?? "") : "";
        setSaveViewScopeDraft(nextScope);
        setSaveViewTargetBranchIdDraft(nextTargetBranchId);
        setSaveViewTargetRoleDraft(nextTargetRole);
        setSaveViewDefaultTouched(false);
        setSaveViewDefaultDraft(!hasDefaultSavedViewForTarget(savedViews, {
            scope: nextScope,
            targetBranchId: nextTargetBranchId,
            targetRole: nextTargetRole,
        }));
        setSaveViewComposerOpen(true);
    };

    const handleSaveCurrentView = () => {
        const name = saveViewDraftName.trim();
        if (!name) {
            toast.error("Введите название вида");
            return;
        }
        createSavedViewMutation.mutate({
            name,
            isDefault: saveViewDefaultDraft,
            scope: saveViewScopeDraft,
            targetBranchId: saveViewTargetBranchIdDraft,
            targetRole: saveViewTargetRoleDraft,
        });
    };

    const handleApplySavedView = (viewId: string) => {
        const savedView = savedViews.find((item) => item.id === viewId);
        const snapshot = readCalendarQueueStateFromSavedView(savedView, {
            defaultSelectedDate,
            defaultQueueMode,
            defaultQueueLane,
        });
        if (!savedView || !snapshot) {
            toast.error("Не удалось прочитать сохранённый вид");
            return;
        }
        applyCalendarQueueSnapshot(snapshot, { savedViewId: savedView.id });
        toast.success(`Применён вид «${savedView.name}»`);
    };

    const handleResetQueueFilterDraft = () => {
        if (!queueFiltersDirty) {
            return;
        }
        resetQueueFilterDraft();
        emitCalendarOperatorEvent({
            event_type: "filter_reset",
            action_id: "reset_filters",
            surface: "filter_panel",
        });
    };

    const handleApplyQueueFilterDraft = () => {
        if (!queueFiltersDirty) {
            return;
        }
        applyQueueFilterDraft();
        emitCalendarOperatorEvent({
            event_type: "filter_apply",
            action_id: "apply_filters",
            surface: "filter_panel",
        });
    };

    const handleUpdateSavedView = () => {
        if (!selectedSavedView || !canMutateSelectedSavedView) {
            return;
        }
        updateSavedViewMutation.mutate({
            viewId: selectedSavedView.id,
            queryState: buildCalendarQueueStatePayload(currentQueueSnapshot),
            targetBranchId: selectedSavedViewScope === "team" ? (selectedTeamTargetBranchIdDraft || null) : undefined,
            targetRole: selectedSavedViewScope === "team" ? (selectedTeamTargetRoleDraft || null) : undefined,
        });
    };

    const handleToggleSavedViewDefault = () => {
        if (!selectedSavedView || !canMutateSelectedSavedView) {
            return;
        }
        updateSavedViewMutation.mutate({
            viewId: selectedSavedView.id,
            isDefault: !selectedSavedView.is_default,
        });
    };

    const handleDeleteSavedView = () => {
        if (!selectedSavedView || !canMutateSelectedSavedView) {
            return;
        }
        const confirmed = window.confirm(`Удалить вид «${selectedSavedView.name}»?`);
        if (!confirmed) {
            return;
        }
        deleteSavedViewMutation.mutate(selectedSavedView.id);
    };

    const invalidateCalendarBookingQueries = () => {
        queryClient.invalidateQueries({ queryKey: ["slots"] });
        queryClient.invalidateQueries({ queryKey: ["bookings"] });
        if (focusedCaseId) {
            queryClient.invalidateQueries({ queryKey: ["case", focusedCaseId] });
            queryClient.invalidateQueries({ queryKey: ["cases"] });
        }
    };

    const emitCalendarOperatorEvent = (payload: CalendarOperatorEventRequest) => {
        if (!session || !canReadCalendar) {
            return;
        }
        void recordCalendarOperatorEvent(payload).catch(() => undefined);
    };

    const emitCalendarDoubleSubmitBlocked = (
        actionId: Exclude<CalendarOperatorEventRequest["action_id"], "apply_filters" | "reset_filters">,
        surface: Exclude<CalendarOperatorEventRequest["surface"], "filter_panel">,
        bookingId?: string,
    ) => {
        emitCalendarOperatorEvent({
            event_type: "double_submit_blocked",
            action_id: actionId,
            surface,
            booking_id: bookingId,
        });
    };

    // Create booking mutation
    const createMutation = useMutation({
        mutationFn: createBooking,
        onSuccess: () => {
            toast.success("Запись создана!");
            invalidateCalendarBookingQueries();
            resetForm({ keepComposerOpen: false, resetSelections: false });
        },
        onError: (error: unknown) => {
            const code = getApiErrorCode(error);
            if (code === "BOOKING_CONFLICT") {
                toast.error("Это время уже занято. Выберите другой слот.");
            } else {
                toast.error("Не удалось создать запись");
            }
        },
    });

    const updateMutation = useMutation({
        mutationFn: async (payload: {
            bookingId: string;
            specialist_id: string;
            start_at: string;
            end_at: string;
            customer_name: string;
            customer_phone: string;
            service_type: string;
            notes?: string;
            version: number;
        }) => {
            const { bookingId, ...data } = payload;
            return updateBooking(bookingId, data);
        },
        onSuccess: () => {
            toast.success("Запись обновлена");
            invalidateCalendarBookingQueries();
            resetForm({ keepComposerOpen: false, resetSelections: true });
        },
        onError: (error: unknown) => {
            const code = getApiErrorCode(error);
            if (code === "BOOKING_CONFLICT") {
                toast.error("Это время уже занято. Выберите другой слот.");
            } else if (code === "BOOKING_VERSION_CONFLICT") {
                toast.error("Запись уже изменили в другом окне. Обновите список и откройте её заново.");
                invalidateCalendarBookingQueries();
                resetForm({ keepComposerOpen: false, resetSelections: true });
            } else if (code === "BOOKING_UPDATE_DENIED") {
                toast.error("Эту запись больше нельзя менять из-за её текущего статуса.");
            } else {
                toast.error("Не удалось обновить запись");
            }
        },
    });

    const cancelMutation = useMutation({
        mutationFn: async (payload: { bookingId: string; reason?: string; version: number }) =>
            cancelBooking(payload.bookingId, { reason: payload.reason, version: payload.version }),
        onMutate: ({ bookingId }) => {
            setCancelPending(bookingId);
        },
        onSuccess: () => {
            toast.success("Запись отменена");
            invalidateCalendarBookingQueries();
            setCancelReasonDraft("");
            discardBookingActionsPanel();
        },
        onError: (error: unknown) => {
            const code = getApiErrorCode(error);
            if (code === "BOOKING_CANCEL_DENIED") {
                toast.error("Эту запись больше нельзя отменить из-за её текущего статуса.");
            } else if (code === "BOOKING_VERSION_CONFLICT") {
                toast.error("Запись уже изменилась. Обновите список и проверьте текущий статус.");
                invalidateCalendarBookingQueries();
                discardBookingActionsPanel();
            } else {
                toast.error("Не удалось отменить запись");
            }
        },
        onSettled: () => {
            clearCancelPending();
        },
    });

    const statusMutation = useMutation({
        mutationFn: async (payload: { bookingId: string; status: BookingStatusUpdateRequest["status"]; version: number }) =>
            updateBookingStatus(payload.bookingId, { status: payload.status, version: payload.version }),
        onMutate: ({ bookingId }) => {
            setStatusUpdatePending(bookingId);
        },
        onSuccess: (data, variables) => {
            const labels: Record<BookingStatusUpdateRequest["status"], string> = {
                COMPLETED: "Статус: клиент пришел",
                NO_SHOW: "Статус: клиент не пришел",
            };
            const effectMessages = collectBookingCaseEffectMessages(data);
            const suffix = effectMessages.length > 0 ? ` ${effectMessages.join(" ")}` : "";
            toast.success(`${labels[variables.status]}.${suffix}`.trim());
            invalidateCalendarBookingQueries();
        },
        onError: (error: unknown) => {
            const code = getApiErrorCode(error);
            if (code === "BOOKING_STATUS_TRANSITION_DENIED") {
                toast.error("Недопустимый переход статуса для этой записи");
            } else if (code === "BOOKING_VERSION_CONFLICT") {
                toast.error("Статус уже изменили в другом окне. Список обновлён.");
                invalidateCalendarBookingQueries();
                discardBookingActionsPanel();
            } else if (code === "INVALID_STATUS") {
                toast.error("Некорректный статус визита");
            } else {
                toast.error("Не удалось обновить статус визита");
            }
        },
        onSettled: () => {
            clearStatusUpdatePending();
        },
    });

    const followUpMutation = useMutation({
        mutationFn: async (payload: {
            bookingId: string;
            result: "contacted" | "rebooked";
            rebookedAppointmentId?: string;
            note?: string;
            version: number;
        }) =>
            registerNoShowFollowUp(payload.bookingId, {
                result: payload.result,
                rebooked_appointment_id: payload.rebookedAppointmentId,
                note: payload.note,
                version: payload.version,
            }),
        onMutate: ({ bookingId }) => {
            setFollowUpPending(bookingId);
        },
        onSuccess: (data, variables) => {
            const effectMessages = collectBookingCaseEffectMessages(data);
            const suffix = effectMessages.length > 0 ? ` ${effectMessages.join(" ")}` : "";
            if (variables.result === "rebooked") {
                toast.success(`Связь после неявки закрыта: клиента переписали.${suffix}`.trim());
            } else {
                toast.success(`Связь после неявки закрыта: с клиентом связались.${suffix}`.trim());
            }
            invalidateCalendarBookingQueries();
            clearNoShowDraft(variables.bookingId);
        },
        onError: (error: unknown) => {
            const code = getApiErrorCode(error);
            if (code === "BOOKING_STATUS_REQUIRED") {
                toast.error("Связь после неявки доступна только для статуса «Не пришёл»");
            } else if (code === "FOLLOW_UP_ALREADY_CLOSED") {
                toast.error("Результат связи уже зафиксирован. Обновите карточку, чтобы увидеть текущее состояние.");
                invalidateCalendarBookingQueries();
                discardBookingActionsPanel();
            } else if (code === "BOOKING_VERSION_CONFLICT") {
                toast.error("Карточка устарела. Список обновлён, откройте запись снова.");
                invalidateCalendarBookingQueries();
                discardBookingActionsPanel();
            } else if (code === "INVALID_PARAM") {
                const message = getApiErrorMessage(error, "Проверьте данные результата связи");
                if (message.includes("rebooked_appointment_id")) {
                    toast.error("Для результата «Клиента переписали» выберите новую запись.");
                } else {
                    toast.error("Проверьте данные результата связи после неявки.");
                }
            } else {
                toast.error("Не удалось сохранить результат связи после неявки");
            }
        },
        onSettled: () => {
            clearFollowUpPending();
        },
    });

    const followUpGovernanceMutation = useMutation({
        mutationFn: async (payload: {
            bookingId: string;
            ownerAgentId: string;
            dueAt: string;
            version: number;
        }) =>
            updateBookingFollowUpGovernance(payload.bookingId, {
                owner_agent_id: payload.ownerAgentId || null,
                due_at: payload.dueAt ? new Date(payload.dueAt).toISOString() : null,
                version: payload.version,
            }),
        onMutate: ({ bookingId }) => {
            setGovernancePending(bookingId);
        },
        onSuccess: (data, variables) => {
            toast.success("Ответственный и срок связи обновлены");
            invalidateCalendarBookingQueries();
            clearBookingFollowUpDrafts(variables.bookingId);
        },
        onError: (error: unknown) => {
            const code = getApiErrorCode(error);
            if (code === "FOLLOW_UP_ALREADY_CLOSED") {
                toast.error("Задача по связи уже закрыта");
                invalidateCalendarBookingQueries();
                discardBookingActionsPanel();
            } else if (code === "BOOKING_VERSION_CONFLICT") {
                toast.error("Карточка уже изменилась. Обновите список и назначьте заново.");
                invalidateCalendarBookingQueries();
                discardBookingActionsPanel();
            } else if (code === "BOOKING_STATUS_REQUIRED") {
                toast.error("Назначение ответственного доступно только после неявки");
            } else if (code === "ACCESS_DENIED") {
                toast.error("Недостаточно прав для управления связью после неявки");
            } else {
                toast.error("Не удалось обновить ответственного и срок связи");
            }
        },
        onSettled: () => {
            clearGovernancePending();
        },
    });

    const resetForm = ({
        keepComposerOpen = true,
        resetSelections = true,
    }: {
        keepComposerOpen?: boolean;
        resetSelections?: boolean;
    } = {}) => {
        resetBookingComposer({
            keepOpen: keepComposerOpen,
            resetSelections,
            bookingDate: bookingDateSuggestion,
            customerName: normalizeHumanText(focusedCaseQuery.data?.customer_name),
            customerPhoneInput: formatPhoneInput(focusedCaseQuery.data?.customer_phone),
        });
    };

    const applyCasePrefill = () => {
        setCustomerName(normalizeHumanText(focusedCaseQuery.data?.customer_name));
        setCustomerPhoneInput(formatPhoneInput(focusedCaseQuery.data?.customer_phone));
    };

    const handleQueueModeChange = (nextMode: BookingQueueMode) => {
        setCalendarQueueMode(nextMode, today);
        if (nextMode !== "history" && (!selectedDate || selectedDate < today)) {
            setSelectedSlot(null);
        }
    };

    const handleRefreshCalendarSurface = async () => {
        await Promise.all([
            queryClient.invalidateQueries({ queryKey: ["bookings"] }),
            queryClient.invalidateQueries({ queryKey: ["specialists"] }),
            queryClient.invalidateQueries({ queryKey: ["agents", "calendar-follow-up-owners"] }),
            queryClient.invalidateQueries({ queryKey: ["queue-state-views", "calendar"] }),
        ]);
        toast.success("Календарь обновлён");
    };

    const openSecondaryPanel = (section: CalendarSecondaryPanelSection) => {
        closeBookingActionsPanel();
        if (section === "filters") {
            resetQueueFilterDraft();
        }
        setSecondaryPanelSection(section);
        setSecondaryPanelOpen(true);
    };

    const openBookingComposer = () => {
        closeBookingActionsPanel();
        setSecondaryPanelOpen(false);
        openCreateBookingComposer({
            bookingDate: (!bookingDate || bookingDate < today) ? bookingDateSuggestion : bookingDate,
            customerName: normalizeHumanText(focusedCaseQuery.data?.customer_name),
            customerPhoneInput: formatPhoneInput(focusedCaseQuery.data?.customer_phone),
            preserveSelections: true,
        });
    };

    const openEditBookingComposer = (booking: (typeof bookings)[number]) => {
        const matchedService = serviceCatalog.find((service) => service.name === (booking.service_type ?? ""));
        const fallbackDuration = Math.max(
            30,
            Math.round((new Date(booking.end_at).getTime() - new Date(booking.start_at).getTime()) / (60 * 1000)),
        );
        const nextService = matchedService ?? (booking.service_type
            ? {
                name: booking.service_type,
                duration_min: fallbackDuration,
                price: 0,
                specialistCount: 1,
            }
            : null);
        const nextSlot = buildBookingSlot(booking.start_at, booking.end_at);
        const nextDate = booking.start_at.slice(0, 10);

        setSecondaryPanelOpen(false);
        closeBookingActionsPanel();
        openEditBookingComposerState({
            editingBookingId: booking.id,
            selectedService: nextService,
            selectedSpecialist: booking.specialist_id,
            bookingDate: nextDate || bookingDateSuggestion,
            selectedSlot: nextSlot,
            customerName: normalizeHumanText(booking.customer_name),
            customerPhoneInput: formatPhoneInput(booking.customer_phone),
            notes: booking.notes ?? "",
        });
    };

    const closeBookingComposer = () => {
        if (bookingComposerDirty && !window.confirm("Закрыть форму и потерять несохранённые изменения записи?")) {
            return;
        }
        resetForm({ keepComposerOpen: false, resetSelections: true });
    };

    const closeSecondaryPanel = () => {
        setSecondaryPanelOpen(false);
    };

    const openBookingActionsPanel = (bookingId: string) => {
        setSecondaryPanelOpen(false);
        openBookingActionsPanelState(bookingId);
    };

    const discardBookingActionsPanel = () => {
        if (bookingActionsBookingId) {
            clearBookingFollowUpDrafts(bookingActionsBookingId);
        }
        closeBookingActionsPanelState();
    };

    const closeBookingActionsPanel = () => {
        if (bookingActionPanelHasUnsavedChanges && !window.confirm("Закрыть действия по записи и потерять несохранённые изменения?")) {
            return;
        }
        discardBookingActionsPanel();
    };

    const setFollowUpGovernanceDraft = (
        bookingId: string,
        patch: Partial<{ ownerAgentId: string; dueAt: string }>,
    ) => {
        setGovernanceDraft(bookingId, patch);
    };

    const setNoShowFollowUpDraft = (
        bookingId: string,
        patch: Partial<NoShowFollowUpDraft>,
    ) => {
        setNoShowDraft(bookingId, patch);
    };

    const handleSlotClick = (slot: TimeSlot) => {
        if (!slot.available || !canWriteCalendar) return;
        setSelectedSlot(slot);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (createMutation.isPending || updateMutation.isPending) {
            emitCalendarDoubleSubmitBlocked(
                bookingComposerMode === "edit" ? "edit_booking" : "create_booking",
                "composer",
                editingBookingId ?? undefined,
            );
            return;
        }
        if (!selectedSlot || !selectedSpecialist || !selectedService || !canWriteCalendar || !bookingFormReady) {
            toast.error(bookingFormErrorList[0] ?? "Проверьте данные записи");
            return;
        }

        const startAt = new Date(selectedSlot.start);
        const endAt = new Date(selectedSlot.end);

        const payload = {
            specialist_id: selectedSpecialist,
            start_at: startAt.toISOString(),
            end_at: endAt.toISOString(),
            customer_name: normalizedCustomerName,
            customer_phone: normalizedCustomerPhone ?? undefined,
            service_type: selectedService.name,
            notes: notes || undefined,
            conversation_id: focusedConversationId || undefined,
            case_id: focusedCaseId || undefined,
        };
        if (bookingComposerMode === "edit" && editingBookingId) {
            const editingBooking = bookings.find((booking) => booking.id === editingBookingId);
            if (!editingBooking) {
                toast.error("Не удалось найти актуальную запись. Обновите список и откройте её заново.");
                invalidateCalendarBookingQueries();
                resetForm({ keepComposerOpen: false, resetSelections: true });
                return;
            }
            updateMutation.mutate({
                bookingId: editingBookingId,
                specialist_id: payload.specialist_id,
                start_at: payload.start_at,
                end_at: payload.end_at,
                customer_name: payload.customer_name,
                customer_phone: normalizedCustomerPhone ?? "",
                service_type: payload.service_type,
                notes: payload.notes,
                version: editingBooking.version,
            });
            return;
        }
        createMutation.mutate(payload);
    };

    const handleVisitStatusSubmit = (bookingId: string, status: BookingStatusUpdateRequest["status"], version: number) => {
        if (statusMutation.isPending && statusUpdateBookingId === bookingId) {
            emitCalendarDoubleSubmitBlocked(
                status === "COMPLETED" ? "mark_completed" : "mark_no_show",
                "booking_panel",
                bookingId,
            );
            return;
        }
        statusMutation.mutate({ bookingId, status, version });
    };

    const handleCancelBookingSubmit = (bookingId: string, version: number) => {
        if (cancelMutation.isPending && cancelBookingId === bookingId) {
            emitCalendarDoubleSubmitBlocked("cancel_booking", "booking_panel", bookingId);
            return;
        }
        cancelMutation.mutate({ bookingId, reason: cancelReasonDraft || undefined, version });
    };

    const handleFollowUpSubmit = (
        bookingId: string,
        version: number,
        draft: NoShowFollowUpDraft,
    ) => {
        if (followUpMutation.isPending && followUpBookingId === bookingId) {
            emitCalendarDoubleSubmitBlocked(
                draft.result === "rebooked" ? "record_follow_up_rebooked" : "record_follow_up_contacted",
                "follow_up_panel",
                bookingId,
            );
            return;
        }
        followUpMutation.mutate({
            bookingId,
            result: draft.result,
            rebookedAppointmentId: draft.rebookedAppointmentId || undefined,
            note: draft.note || undefined,
            version,
        });
    };

    const handleFollowUpGovernanceSubmit = (
        bookingId: string,
        version: number,
        ownerAgentId: string,
        dueAt: string,
    ) => {
        if (followUpGovernanceMutation.isPending && followUpGovernanceBookingId === bookingId) {
            emitCalendarDoubleSubmitBlocked("manage_follow_up_governance", "follow_up_governance", bookingId);
            return;
        }
        followUpGovernanceMutation.mutate({
            bookingId,
            ownerAgentId,
            dueAt,
            version,
        });
    };

    const buildCaseHref = (caseId: string) =>
        returnPanel
            ? `/cases/${encodeURIComponent(caseId)}?panel=${returnPanel}`
            : `/cases/${encodeURIComponent(caseId)}`;
    const backToCasesHref = focusedCaseId ? buildCaseHref(focusedCaseId) : "/";

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Войдите в систему для просмотра календаря.
            </div>
        );
    }

    if (!canReadCalendar) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к календарю." />
        );
    }

    return (
        <div className="space-y-6" data-testid="calendar-page">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <div className="badge mb-3">Операторский календарь</div>
                    <h1 className="text-2xl font-semibold">Записи</h1>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Здесь оператор видит рабочий список записей, быстро назначает новый визит и не теряет связь с заявкой.
                    </p>
                    {!canWriteCalendar && (
                        <p className="mt-2 text-xs text-muted-foreground">
                            Только просмотр: создание новых записей и изменения статусов недоступны.
                        </p>
                    )}
                </div>
                <Link
                    href={backToCasesHref}
                    className="btn-ghost"
                    data-testid="calendar-back-to-cases"
                >
                    ← {focusedCaseId ? "Вернуться в заявку" : "Назад к заявкам"}
                </Link>
            </div>

            {focusedConversationId && (
                <div
                    className="card-surface border border-primary/30 bg-primary/5 p-4"
                    data-testid="calendar-case-context-banner"
                >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <p className="text-sm font-semibold">Режим по заявке включен</p>
                            <p className="text-xs text-muted-foreground">
                                Показываются записи, связанные с выбранной заявкой. Дата по умолчанию не ограничивает список, пока вы не выберете её вручную.
                            </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {focusedCaseId && (
                                <Link
                                    href={buildCaseHref(focusedCaseId)}
                                    className="rounded border border-border/60 px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-background"
                                    data-testid="calendar-open-linked-case"
                                >
                                    Открыть заявку
                                </Link>
                            )}
                            <Link
                                href="/calendar"
                                className="rounded border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-background hover:text-foreground"
                                data-testid="calendar-clear-case-context"
                            >
                                Показать все записи
                            </Link>
                        </div>
                    </div>
                </div>
            )}

            {specialistsError && (
                <div className="card-surface p-4 text-destructive">
                    <h3 className="mb-1 font-semibold">Не удалось загрузить список мастеров</h3>
                    <p className="text-sm text-muted-foreground">
                        Проверьте соединение и попробуйте обновить страницу.
                    </p>
                    <details className="mt-2 text-xs text-muted-foreground">
                        <summary className="cursor-pointer">Технические детали</summary>
                        <pre className="mt-2 overflow-auto whitespace-pre-wrap">
                            {JSON.stringify(specialistsErrorData, null, 2)}
                        </pre>
                    </details>
                </div>
            )}

            <div className="card-surface space-y-4 p-4 sm:p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1">
                        <h2 className="text-lg font-semibold">{queueHeading}</h2>
                        <p className="text-xs text-muted-foreground">
                            На первом экране оставляем только рабочий срез: режим, день, приоритет списка и быстрый переход к уточняющим панелям.
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={() => openSecondaryPanel("filters")}
                            className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-background hover:text-foreground"
                            data-testid="calendar-secondary-panel-toggle"
                        >
                            Уточнить список
                        </button>
                        <button
                            type="button"
                            onClick={() => openSecondaryPanel("saved_views")}
                            className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-background hover:text-foreground"
                            data-testid="calendar-saved-views-panel-toggle"
                        >
                            Виды и ссылка
                        </button>
                        <button
                            type="button"
                            onClick={openBookingComposer}
                            className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-primary/10"
                            data-testid="calendar-scheduling-panel-toggle"
                        >
                            Новая запись
                        </button>
                        <button
                            type="button"
                            onClick={() => {
                                void handleRefreshCalendarSurface();
                            }}
                            className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-background hover:text-foreground"
                            data-testid="calendar-queue-refresh"
                        >
                            Обновить
                        </button>
                    </div>
                </div>

                <div className="flex flex-wrap gap-2 text-xs">
                    <span className="rounded bg-muted px-2.5 py-1 text-muted-foreground">
                        Всего: <span className="font-semibold text-foreground">{bookingsSorted.length}</span>
                    </span>
                    <span className="rounded bg-amber-100 px-2.5 py-1 text-amber-900">
                        Требуют внимания: <span className="font-semibold">{attentionCount}</span>
                    </span>
                    <span className="rounded bg-red-100 px-2.5 py-1 text-red-900">
                        Неявки без связи: <span className="font-semibold">{noShowAttentionCount}</span>
                    </span>
                    {bookingsData?.has_more && (
                        <span className="rounded bg-primary/10 px-2.5 py-1 text-primary">
                            Показаны первые {bookingsSorted.length}
                        </span>
                    )}
                </div>

                <div className="space-y-3" data-testid="calendar-queue-controls">
                    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.9fr)]">
                        <div className="rounded-xl border border-border/60 bg-background/80 p-3">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                Режим списка
                            </p>
                            <div className="mt-3 flex flex-wrap items-center gap-2">
                                <button
                                    type="button"
                                    onClick={() => handleQueueModeChange("ops")}
                                    className={`rounded border px-2.5 py-1 text-xs font-semibold ${
                                        queueMode === "ops"
                                            ? "border-primary/40 bg-primary/10 text-primary"
                                            : "border-border/60 text-muted-foreground hover:text-foreground"
                                    }`}
                                    data-testid="calendar-queue-mode-ops"
                                >
                                    Рабочий день
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleQueueModeChange("history")}
                                    className={`rounded border px-2.5 py-1 text-xs font-semibold ${
                                        queueMode === "history"
                                            ? "border-slate-300 bg-slate-100 text-slate-900"
                                            : "border-border/60 text-muted-foreground hover:text-foreground"
                                    }`}
                                    data-testid="calendar-queue-mode-history"
                                >
                                    Архив
                                </button>
                            </div>
                            {queueMode === "ops" ? (
                                <div className="mt-3 flex flex-wrap items-center gap-2">
                                    <button
                                        type="button"
                                        onClick={() => setQueueLane("attention")}
                                        className={`rounded border px-2.5 py-1 text-xs font-semibold ${
                                            queueLane === "attention"
                                                ? "border-amber-300 bg-amber-100 text-amber-900"
                                                : "border-border/60 text-muted-foreground hover:text-foreground"
                                        }`}
                                        data-testid="calendar-queue-lane-attention"
                                    >
                                        Нужны действия
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setQueueLane("all")}
                                        className={`rounded border px-2.5 py-1 text-xs font-semibold ${
                                            queueLane === "all"
                                                ? "border-primary/40 bg-primary/10 text-primary"
                                                : "border-border/60 text-muted-foreground hover:text-foreground"
                                        }`}
                                        data-testid="calendar-queue-lane-all"
                                    >
                                        Все записи
                                    </button>
                                </div>
                            ) : (
                                <p className="mt-3 text-xs text-muted-foreground">
                                    В архиве всегда доступен полный список без отдельного режима «Нужны действия».
                                </p>
                            )}
                        </div>

                        <div className="rounded-xl border border-border/60 bg-background/80 p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                    День в списке
                                </p>
                                {queueMode === "history" && !selectedDate && (
                                    <span className="rounded-full bg-muted px-2.5 py-1 text-[11px] font-semibold text-foreground/80">
                                        Все даты
                                    </span>
                                )}
                            </div>
                            <div className="mt-3 flex flex-wrap gap-2">
                                <button
                                    type="button"
                                    onClick={() => setSelectedDate(today)}
                                    className={`rounded border px-2.5 py-1 text-xs font-semibold ${
                                        selectedDate === today
                                            ? "border-primary/40 bg-primary/10 text-primary"
                                            : "border-border/60 text-muted-foreground hover:text-foreground"
                                    }`}
                                >
                                    Сегодня
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setSelectedDate(tomorrow)}
                                    className={`rounded border px-2.5 py-1 text-xs font-semibold ${
                                        selectedDate === tomorrow
                                            ? "border-primary/40 bg-primary/10 text-primary"
                                            : "border-border/60 text-muted-foreground hover:text-foreground"
                                    }`}
                                >
                                    Завтра
                                </button>
                                {queueMode === "history" && (
                                    <button
                                        type="button"
                                        onClick={() => setSelectedDate("")}
                                        className={`rounded border px-2.5 py-1 text-xs font-semibold ${
                                            !selectedDate
                                                ? "border-primary/40 bg-primary/10 text-primary"
                                                : "border-border/60 text-muted-foreground hover:text-foreground"
                                        }`}
                                    >
                                        Все даты
                                    </button>
                                )}
                            </div>
                            <label className="mt-3 block space-y-1">
                                <span className="text-xs font-medium text-muted-foreground">
                                    Выбрать день вручную
                                </span>
                                <input
                                    id="calendar-queue-date"
                                    type="date"
                                    value={selectedDate}
                                    onChange={(event) => {
                                        setSelectedDate(event.target.value);
                                        setSelectedSlot(null);
                                    }}
                                    min={queueMode === "ops" ? today : undefined}
                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    data-testid="calendar-queue-date"
                                />
                            </label>
                        </div>
                    </div>
                </div>

                {queueScopeHint && (
                    <div
                        className="rounded border border-border/60 bg-muted/40 px-3 py-2 text-xs text-muted-foreground"
                        data-testid={queueMode === "history" && !selectedDate ? "calendar-history-all-dates-hint" : "calendar-case-all-dates-hint"}
                    >
                        {queueScopeHint}
                    </div>
                )}

                <div className="grid gap-3 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.9fr)]">
                    <div className="rounded-xl border border-border/60 bg-background/80 p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                Что сейчас показано
                            </p>
                            {queueSummaryChips.length > 0 && (
                                <button
                                    type="button"
                                    onClick={() => openSecondaryPanel("filters")}
                                    className="text-xs font-semibold text-primary"
                                >
                                    Изменить
                                </button>
                            )}
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2 text-xs">
                            {queueSummaryChips.length > 0 ? (
                                queueSummaryChips.map((chip) => (
                                    <span key={chip.key} className="rounded-full bg-muted px-2.5 py-1 font-semibold text-foreground/80">
                                        {chip.label}
                                    </span>
                                ))
                            ) : (
                                <span className="rounded-full bg-muted px-2.5 py-1 font-semibold text-foreground/80">
                                    Только основной рабочий срез без дополнительных уточнений
                                </span>
                            )}
                        </div>
                    </div>
                    <div className="rounded-xl border border-border/60 bg-background/80 p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                Новая запись
                            </p>
                            <button
                                type="button"
                                onClick={openBookingComposer}
                                className="text-xs font-semibold text-primary"
                            >
                                Открыть
                            </button>
                        </div>
                        <p className="mt-3 text-sm text-foreground/90">
                            {schedulingSummaryLabel}
                        </p>
                        {selectedSlot && (
                            <p className="mt-2 text-xs text-amber-700">
                                Выбрано время для новой записи. Осталось подтвердить данные клиента.
                            </p>
                        )}
                    </div>
                </div>

                {bookingsLoading ? (
                    <div className="animate-pulse space-y-3">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="h-24 rounded bg-muted/70"></div>
                        ))}
                    </div>
                ) : bookingsVisible.length === 0 ? (
                    <p className="py-4 text-center text-muted-foreground">
                        {focusedConversationId
                            ? "По этой заявке нет записей под выбранные фильтры"
                            : "Нет записей под выбранные фильтры"}
                    </p>
                ) : (
                    <div className="space-y-3">
                        {bookingsVisible.map((booking) => {
                            const attentionLabel = getBookingAttentionLabel(booking);
                            const isNoShow = booking.status.toUpperCase() === "NO_SHOW";
                            const followUpOwnerLabel = getFollowUpOwnerDisplayLabel({
                                name: booking.follow_up_owner_name,
                                id: booking.follow_up_owner_id,
                            });
                            const followUpDueLabel = formatDueAtLabel(booking.follow_up_due_at);
                            const bookingActionMap = buildCalendarBookingActionAvailabilityMap(booking, calendarActionPermissions, calendarActorClass);
                            const visitActions = getCalendarVisitActionOptions(booking, calendarActionPermissions, calendarActorClass);
                            const hasBookingActionSurface = visitActions.length > 0
                                || bookingActionMap.edit_booking.visible
                                || bookingActionMap.cancel_booking.visible
                                || bookingActionMap.record_follow_up_contacted.visible
                                || bookingActionMap.record_follow_up_rebooked.visible
                                || bookingActionMap.manage_follow_up_governance.visible;
                            return (
                                <div
                                    key={booking.id}
                                    className="rounded-xl border border-border/60 p-4 transition hover:bg-muted/40"
                                    data-testid="calendar-booking-card"
                                >
                                    <div className="flex flex-wrap items-start justify-between gap-3">
                                        <div className="space-y-1">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <span className="text-sm font-semibold">
                                                    {new Date(booking.start_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                                    {" - "}
                                                    {new Date(booking.end_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                                </span>
                                                <span className={`rounded px-2 py-0.5 text-xs font-medium ${getBookingStatusColor(booking.status)}`}>
                                                    {getBookingStatusLabel(booking.status)}
                                                </span>
                                            </div>
                                            <div className="text-sm text-muted-foreground">{booking.specialist_name}</div>
                                            {booking.customer_name && (
                                                <div className="text-sm">
                                                    {booking.customer_name}
                                                    {booking.customer_phone && (
                                                        <span className="text-muted-foreground"> • {formatPhoneInput(booking.customer_phone) || booking.customer_phone}</span>
                                                    )}
                                                </div>
                                            )}
                                            {booking.service_type && (
                                                <div className="text-xs text-muted-foreground">
                                                    {booking.service_type}
                                                </div>
                                            )}
                                        </div>
                                        {hasBookingActionSurface && (
                                            <button
                                                type="button"
                                                onClick={() => openBookingActionsPanel(booking.id)}
                                                className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:bg-background hover:text-foreground"
                                                data-testid="calendar-booking-open-actions"
                                            >
                                                Открыть действия
                                            </button>
                                        )}
                                    </div>

                                    {attentionLabel && (
                                        <div className="mt-3">
                                            <span className="rounded bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                                                {attentionLabel}
                                            </span>
                                        </div>
                                    )}

                                    {isNoShow && (
                                        <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                                            <span className="rounded bg-muted px-2 py-0.5 font-semibold text-foreground/80">
                                                {formatContactTaskOwnerChipLabel(followUpOwnerLabel)}
                                            </span>
                                            <span className={`rounded px-2 py-0.5 font-semibold ${booking.follow_up_overdue ? "bg-red-100 text-red-900" : "bg-slate-100 text-slate-700"}`}>
                                                {formatContactTaskDueChipLabel(followUpDueLabel)}
                                            </span>
                                            {booking.follow_up_overdue && !booking.no_show_followup_done && (
                                                <span className="rounded bg-red-100 px-2 py-0.5 font-semibold text-red-900">
                                                    Просрочено
                                                </span>
                                            )}
                                            {booking.no_show_followup_done && (
                                                <span className="rounded bg-green-100 px-2 py-0.5 font-semibold text-green-800">
                                                    {getContactTaskResultLabel(booking.no_show_followup_result)}
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    {booking.case_id && bookingActionMap.open_case_from_booking.visible && (
                                        <div className="mt-3 flex flex-wrap items-center gap-2">
                                            <Link
                                                href={buildCaseHref(booking.case_id)}
                                                className="rounded border border-border/60 px-2.5 py-1 text-xs font-semibold text-foreground hover:bg-background"
                                                data-testid="calendar-booking-open-case"
                                            >
                                                Открыть чат заявки
                                            </Link>
                                            {focusedCaseId && booking.case_id === focusedCaseId && (
                                                <span className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                                                    Текущая заявка
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {secondaryPanelOpen && (
                <div className="fixed inset-0 z-40" data-testid="calendar-secondary-panel-overlay">
                    <div
                        className="absolute inset-0 bg-foreground/20"
                        onClick={closeSecondaryPanel}
                        aria-hidden="true"
                    />
                    <div
                        className="absolute inset-y-0 right-0 flex h-full w-full max-w-[640px] flex-col gap-4 overflow-y-auto bg-background p-4 shadow-xl"
                        data-testid="calendar-secondary-panel"
                    >
                        <div className="flex items-start justify-between gap-3">
                            <div className="space-y-1">
                                <p className="text-sm font-semibold">Боковая панель календаря</p>
                                <p className="text-xs text-muted-foreground">
                                    Здесь собраны уточняющие действия: фильтры списка и сохранённые виды.
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={closeSecondaryPanel}
                                className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                data-testid="calendar-secondary-panel-close"
                            >
                                Закрыть
                            </button>
                        </div>

                        <div className="flex flex-wrap gap-2">
                            {CALENDAR_SECONDARY_PANEL_TABS.map((tab) => (
                                <button
                                    key={tab.id}
                                    type="button"
                                    onClick={() => openSecondaryPanel(tab.id)}
                                    className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                                        secondaryPanelSection === tab.id
                                            ? "border-primary/40 bg-primary/10 text-primary"
                                            : "border-border/60 text-muted-foreground hover:text-foreground"
                                    }`}
                                    data-testid={`calendar-secondary-tab-${tab.id}`}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        {secondaryPanelSection === "filters" && (
                            <div className="rounded-xl border border-border/60 bg-card/80 p-4" data-testid="calendar-secondary-filters">
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div>
                                        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                            Уточнить список
                                        </p>
                                        <p className="mt-1 text-xs text-muted-foreground">
                                            Изменения в этой панели не трогают список сразу. Они применятся к очереди, ссылке и сохранённому состоянию только после кнопки «Применить».
                                        </p>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={handleResetQueueFilterDraft}
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                        disabled={!queueFiltersDirty}
                                        data-testid="calendar-filters-reset"
                                    >
                                        Сбросить изменения
                                    </button>
                                </div>
                                <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                                    <label className="space-y-1">
                                        <span className="text-xs font-medium text-muted-foreground">
                                            Найти запись
                                        </span>
                                        <input
                                            type="text"
                                            value={draftQueueSearch}
                                            onChange={(event) => updateCalendarFilterDraft({ queueSearch: event.target.value })}
                                            placeholder="Клиент, телефон, услуга, мастер или ID"
                                            className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                            data-testid="calendar-queue-search"
                                        />
                                    </label>
                                    <label className="space-y-1">
                                        <span className="text-xs font-medium text-muted-foreground">
                                            Статус визита
                                        </span>
                                        <select
                                            value={draftQueueStatusFilter}
                                            onChange={(event) => updateCalendarFilterDraft({ queueStatusFilter: event.target.value as BookingStatusFilter })}
                                            className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                            data-testid="calendar-queue-status-filter"
                                        >
                                            <option value="all">Все статусы</option>
                                            <option value="scheduled">Запланированные</option>
                                            <option value="completed">Пришёл</option>
                                            <option value="no_show">Не пришёл</option>
                                            <option value="cancelled">Отменённые</option>
                                        </select>
                                    </label>
                                    {canReadTeam && (
                                        <label className="space-y-1">
                                            <span className="text-xs font-medium text-muted-foreground">
                                                Кто отвечает за звонок
                                            </span>
                                            <select
                                                value={draftFollowUpOwnerId}
                                                onChange={(event) => updateCalendarFilterDraft({ followUpOwnerId: event.target.value })}
                                                className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                data-testid="calendar-follow-up-owner-filter"
                                            >
                                                <option value="">Все, кто звонит клиентам</option>
                                                {followUpOwnerOptions.map((agent) => (
                                                    <option key={agent.id} value={agent.id}>
                                                        {agent.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </label>
                                    )}
                                    <label className="flex min-h-[48px] items-center gap-2 rounded-lg border border-border/60 bg-background px-3 py-2 text-sm text-muted-foreground">
                                        <input
                                            type="checkbox"
                                            checked={draftFollowUpOverdueOnly}
                                            onChange={(event) => updateCalendarFilterDraft({ followUpOverdueOnly: event.target.checked })}
                                            className="h-4 w-4 rounded border-border/60"
                                            data-testid="calendar-follow-up-overdue-filter"
                                        />
                                        <span className="break-words">Только просроченные задачи по звонкам</span>
                                    </label>
                                </div>
                                {queueFiltersDirty && (
                                    <div
                                        className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900"
                                        data-testid="calendar-filter-draft-banner"
                                    >
                                        Изменения пока только в панели. Основной список и ссылка обновятся после кнопки «Применить».
                                    </div>
                                )}
                                {hiddenTechnicalFollowUpOwnersCount > 0 && (
                                    <p className="mt-3 text-xs text-muted-foreground">
                                        Служебные учётные записи не показываем оператору: {hiddenTechnicalFollowUpOwnersCount}
                                    </p>
                                )}
                                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                                    {queueSummaryChips.length > 0 ? (
                                        queueSummaryChips.map((chip) => (
                                            <span key={chip.key} className="rounded-full bg-muted px-2.5 py-1 font-semibold text-foreground/80">
                                                {chip.label}
                                            </span>
                                        ))
                                    ) : (
                                        <span className="rounded-full bg-muted px-2.5 py-1 font-semibold text-foreground/80">
                                            Дополнительные фильтры не заданы
                                        </span>
                                    )}
                                </div>
                                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-border/60 pt-4">
                                    <p className="text-xs text-muted-foreground">
                                        Сейчас в списке применён только тот набор уточнений, который виден в плашках выше.
                                    </p>
                                    <button
                                        type="button"
                                        onClick={handleApplyQueueFilterDraft}
                                        className="rounded-full border border-primary/30 bg-primary/5 px-4 py-2 text-xs font-semibold text-primary disabled:cursor-not-allowed disabled:border-border/60 disabled:bg-muted disabled:text-muted-foreground"
                                        disabled={!queueFiltersDirty}
                                        data-testid="calendar-filters-apply"
                                    >
                                        Применить
                                    </button>
                                </div>
                            </div>
                        )}

                        {secondaryPanelSection === "saved_views" && (
                            <div className="rounded-xl border border-border/60 bg-card/80 p-4" data-testid="calendar-saved-views">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div>
                                        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                            Сохранённые виды
                                        </p>
                                        <p className="mt-1 text-xs text-muted-foreground">
                                            Личные виды, командные пресеты и ссылка на текущий срез календаря.
                                        </p>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-2">
                                        <button
                                            type="button"
                                            onClick={() => {
                                                void handleCopyQueueLink();
                                            }}
                                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                            data-testid="calendar-queue-copy-link"
                                        >
                                            Копировать ссылку
                                        </button>
                                        <button
                                            type="button"
                                            onClick={handleOpenSaveViewComposer}
                                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                            disabled={savedViewMutationPending}
                                            data-testid="calendar-saved-view-save"
                                        >
                                            Сохранить текущий
                                        </button>
                                        {selectedSavedView && savedViewDirty && (
                                            <>
                                                <button
                                                    type="button"
                                                    onClick={() => handleApplySavedView(selectedSavedView.id)}
                                                    className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                                    disabled={savedViewMutationPending}
                                                    data-testid="calendar-saved-view-reapply"
                                                >
                                                    Вернуть вид
                                                </button>
                                                {canMutateSelectedSavedView && (
                                                    <button
                                                        type="button"
                                                        onClick={handleUpdateSavedView}
                                                        className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary"
                                                        disabled={savedViewMutationPending}
                                                        data-testid="calendar-saved-view-update"
                                                    >
                                                        Обновить вид
                                                    </button>
                                                )}
                                            </>
                                        )}
                                        {selectedSavedView && !savedViewDirty && selectedTeamTargetingDirty && canMutateSelectedSavedView && (
                                            <button
                                                type="button"
                                                onClick={handleUpdateSavedView}
                                                className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary"
                                                disabled={savedViewMutationPending}
                                                data-testid="calendar-saved-view-update"
                                            >
                                                Сохранить доступ
                                            </button>
                                        )}
                                        {selectedSavedView && canMutateSelectedSavedView && (
                                            <>
                                                <button
                                                    type="button"
                                                    onClick={handleToggleSavedViewDefault}
                                                    className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                                    disabled={savedViewMutationPending}
                                                    data-testid="calendar-saved-view-default"
                                                >
                                                    {selectedSavedView.is_default ? "Снять дефолт" : "Сделать дефолтом"}
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={handleDeleteSavedView}
                                                    className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-destructive"
                                                    disabled={savedViewMutationPending}
                                                    data-testid="calendar-saved-view-delete"
                                                >
                                                    Удалить
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>
                                <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1fr)_auto]">
                                    <select
                                        value={activeSavedViewId ?? ""}
                                        onChange={(event) => {
                                            const nextId = event.target.value;
                                            if (!nextId) {
                                                setActiveSavedViewId(null);
                                                return;
                                            }
                                            handleApplySavedView(nextId);
                                        }}
                                        className="rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                        disabled={savedViewsLoading || savedViewMutationPending}
                                        data-testid="calendar-saved-view-select"
                                    >
                                        <option value="">
                                            {savedViewsLoading
                                                ? "Загружаем виды..."
                                                : savedViews.length === 0
                                                    ? "Нет сохранённых видов"
                                                    : "Выберите сохранённый вид"}
                                        </option>
                                        {teamSavedViews.length > 0 && (
                                            <optgroup label="Командные пресеты">
                                                {teamSavedViews.map((view) => (
                                                    <option key={view.id} value={view.id}>
                                                        {buildSavedViewOptionLabel(view, branchMap)}
                                                    </option>
                                                ))}
                                            </optgroup>
                                        )}
                                        {personalSavedViews.length > 0 && (
                                            <optgroup label="Личные виды">
                                                {personalSavedViews.map((view) => (
                                                    <option key={view.id} value={view.id}>
                                                        {buildSavedViewOptionLabel(view, branchMap)}
                                                    </option>
                                                ))}
                                            </optgroup>
                                        )}
                                    </select>
                                    {selectedSavedView && (
                                        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                            <span className="rounded-full bg-muted px-2 py-1 font-semibold text-foreground/80">
                                                {selectedSavedView.name}
                                            </span>
                                            <span className="rounded-full bg-muted px-2 py-1 font-semibold text-foreground/80">
                                                {SAVED_VIEW_SCOPE_LABELS[selectedSavedViewScope]}
                                            </span>
                                            {selectedSavedViewBranchLabel && (
                                                <span className="rounded-full bg-muted px-2 py-1 font-semibold text-foreground/80">
                                                    {selectedSavedViewBranchLabel}
                                                </span>
                                            )}
                                            {selectedSavedViewRoleLabel && (
                                                <span className="rounded-full bg-muted px-2 py-1 font-semibold text-foreground/80">
                                                    {selectedSavedViewRoleLabel}
                                                </span>
                                            )}
                                            {selectedSavedView.is_default && (
                                                <span className="rounded-full bg-primary/10 px-2 py-1 font-semibold text-primary">
                                                    по умолчанию
                                                </span>
                                            )}
                                            {isTeamSavedView(selectedSavedView) && selectedSavedView.is_applicable === false && (
                                                <span className="rounded-full bg-slate-100 px-2 py-1 font-semibold text-slate-700">
                                                    вне текущего контура
                                                </span>
                                            )}
                                            {savedViewDirty && (
                                                <span className="rounded-full bg-amber-100 px-2 py-1 font-semibold text-amber-900">
                                                    изменён
                                                </span>
                                            )}
                                            {selectedTeamTargetingDirty && (
                                                <span className="rounded-full bg-amber-100 px-2 py-1 font-semibold text-amber-900">
                                                    доступ изменён
                                                </span>
                                            )}
                                        </div>
                                    )}
                                </div>
                                {selectedSavedViewScope === "team" && canManageTeamPresets && selectedSavedView && (
                                    <div className="mt-3 grid gap-2 border-t border-border/60 pt-3 sm:grid-cols-2">
                                        <label className="space-y-1">
                                            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                Командный филиал
                                            </span>
                                            <select
                                                value={selectedTeamTargetBranchIdDraft}
                                                onChange={(event) => setSelectedTeamTargetBranchIdDraft(event.target.value)}
                                                className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                disabled={savedViewMutationPending}
                                                data-testid="calendar-saved-view-team-branch"
                                            >
                                                <option value="">Все филиалы</option>
                                                {selectableBranches.map((branch) => (
                                                    <option key={branch.id} value={branch.id}>
                                                        {branch.name ?? branch.id}
                                                    </option>
                                                ))}
                                            </select>
                                        </label>
                                        <label className="space-y-1">
                                            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                Командная роль
                                            </span>
                                            <select
                                                value={selectedTeamTargetRoleDraft}
                                                onChange={(event) => setSelectedTeamTargetRoleDraft(event.target.value as ConsoleRole | "")}
                                                className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                disabled={savedViewMutationPending}
                                                data-testid="calendar-saved-view-team-role"
                                            >
                                                <option value="">Все роли</option>
                                                {savedViewTargetRoleOptions.map((item) => (
                                                    <option key={item} value={item}>
                                                        {SAVED_VIEW_ROLE_LABELS[item]}
                                                    </option>
                                                ))}
                                            </select>
                                        </label>
                                    </div>
                                )}
                                {saveViewComposerOpen && (
                                    <div className="mt-3 flex flex-col gap-3 border-t border-border/60 pt-3">
                                        <input
                                            ref={saveViewInputRef}
                                            type="text"
                                            value={saveViewDraftName}
                                            onChange={(event) => setSaveViewDraftName(event.target.value)}
                                            onKeyDown={(event) => {
                                                if (event.key === "Enter") {
                                                    event.preventDefault();
                                                    handleSaveCurrentView();
                                                }
                                            }}
                                            placeholder="Например: Неявки сегодня"
                                            className="min-w-[220px] flex-1 rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                            data-testid="calendar-saved-view-name-input"
                                        />
                                        {canManageTeamPresets && (
                                            <div className="grid gap-2 sm:grid-cols-3">
                                                <label className="space-y-1">
                                                    <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                        Кому доступен вид
                                                    </span>
                                                    <select
                                                        value={saveViewScopeDraft}
                                                        onChange={(event) => setSaveViewScopeDraft(event.target.value as "personal" | "team")}
                                                        className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                        disabled={createSavedViewMutation.isPending}
                                                        data-testid="calendar-saved-view-scope"
                                                    >
                                                        <option value="personal">Личный</option>
                                                        <option value="team">Команда</option>
                                                    </select>
                                                </label>
                                                {saveViewScopeDraft === "team" && (
                                                    <>
                                                        <label className="space-y-1">
                                                            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                                Филиал
                                                            </span>
                                                            <select
                                                                value={saveViewTargetBranchIdDraft}
                                                                onChange={(event) => setSaveViewTargetBranchIdDraft(event.target.value)}
                                                                className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                                disabled={createSavedViewMutation.isPending}
                                                                data-testid="calendar-saved-view-target-branch"
                                                            >
                                                                <option value="">Все филиалы</option>
                                                                {selectableBranches.map((branch) => (
                                                                    <option key={branch.id} value={branch.id}>
                                                                        {branch.name ?? branch.id}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </label>
                                                        <label className="space-y-1">
                                                            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                                Роль
                                                            </span>
                                                            <select
                                                                value={saveViewTargetRoleDraft}
                                                                onChange={(event) => setSaveViewTargetRoleDraft(event.target.value as ConsoleRole | "")}
                                                                className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                                disabled={createSavedViewMutation.isPending}
                                                                data-testid="calendar-saved-view-target-role"
                                                            >
                                                                <option value="">Все роли</option>
                                                                {savedViewTargetRoleOptions.map((item) => (
                                                                    <option key={item} value={item}>
                                                                        {SAVED_VIEW_ROLE_LABELS[item]}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </label>
                                                    </>
                                                )}
                                            </div>
                                        )}
                                        <label className="flex items-center gap-2 text-xs text-muted-foreground">
                                            <input
                                                type="checkbox"
                                                checked={saveViewDefaultDraft}
                                                onChange={(event) => {
                                                    setSaveViewDefaultTouched(true);
                                                    setSaveViewDefaultDraft(event.target.checked);
                                                }}
                                                className="h-4 w-4 rounded border-border/60"
                                                disabled={createSavedViewMutation.isPending}
                                                data-testid="calendar-saved-view-default-checkbox"
                                            />
                                            <span>
                                                {saveViewScopeDraft === "team"
                                                    ? "Сделать дефолтным командным пресетом"
                                                    : "Сделать дефолтным личным видом"}
                                            </span>
                                            {!saveViewDefaultTouched && (
                                                <span className="text-muted-foreground/80">
                                                    {suggestedSaveViewDefault ? "рекомендуется" : "по желанию"}
                                                </span>
                                            )}
                                        </label>
                                        <div className="text-xs text-muted-foreground">
                                            {saveViewScopeDraft === "team"
                                                ? `Командных пресетов с таким доступом: ${matchingScopeSavedViewCount}`
                                                : `Личных видов: ${matchingScopeSavedViewCount}`}
                                        </div>
                                        <div className="flex flex-wrap items-center gap-2">
                                            <button
                                                type="button"
                                                onClick={handleSaveCurrentView}
                                                className="rounded-full border border-primary/30 bg-primary/5 px-3 py-2 text-xs font-semibold text-primary"
                                                disabled={createSavedViewMutation.isPending}
                                                data-testid="calendar-saved-view-name-submit"
                                            >
                                                {createSavedViewMutation.isPending ? "Сохраняем..." : "Сохранить"}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setSaveViewDraftName("");
                                                    setSaveViewComposerOpen(false);
                                                    setSaveViewScopeDraft("personal");
                                                    setSaveViewTargetBranchIdDraft("");
                                                    setSaveViewTargetRoleDraft("");
                                                    setSaveViewDefaultDraft(false);
                                                    setSaveViewDefaultTouched(false);
                                                }}
                                                className="rounded-full border border-border/60 px-3 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                                disabled={createSavedViewMutation.isPending}
                                            >
                                                Отмена
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {bookingComposerOpen && (
    <div className="fixed inset-0 z-40" data-testid="calendar-booking-composer-overlay">
        <div
            className="absolute inset-0 bg-foreground/20"
            onClick={closeBookingComposer}
            aria-hidden="true"
        />
        <div
            className="absolute inset-y-0 right-0 flex h-full w-full max-w-[1080px] flex-col gap-4 overflow-y-auto bg-background p-4 shadow-xl"
            data-testid="calendar-booking-composer"
        >
            <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                    <p className="text-sm font-semibold">{bookingComposerTitle}</p>
                    <p className="text-xs text-muted-foreground">
                        {bookingComposerDescription}
                    </p>
                </div>
                <button
                    type="button"
                    onClick={closeBookingComposer}
                    className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                    data-testid="calendar-booking-composer-close"
                >
                    Закрыть
                </button>
            </div>

            <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                            Что уже выбрано
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Следующий шаг всегда виден. Если время не показано, ниже есть явная причина.
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={() => {
                            if (bookingComposerMode === "edit") {
                                restoreBookingComposerBaseline(true);
                                return;
                            }
                            resetForm({ keepComposerOpen: true, resetSelections: true });
                        }}
                        className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                        data-testid="calendar-booking-reset"
                    >
                        {bookingResetLabel}
                    </button>
                </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-5">
                    <div className={`rounded-xl border p-3 ${selectedService ? "border-primary/30 bg-primary/5" : "border-border/60 bg-background/80"}`}>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                            1. Услуга
                        </p>
                        <p className="mt-2 text-sm font-semibold text-foreground">
                            {selectedService?.name ?? "Не выбрана"}
                        </p>
                    </div>
                    <div className={`rounded-xl border p-3 ${selectedSpecialist ? "border-primary/30 bg-primary/5" : "border-border/60 bg-background/80"}`}>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                            2. Мастер
                        </p>
                        <p className="mt-2 text-sm font-semibold text-foreground">
                            {currentSpecialist?.name ?? "Не выбран"}
                        </p>
                    </div>
                    <div className={`rounded-xl border p-3 ${bookingDate ? "border-primary/30 bg-primary/5" : "border-border/60 bg-background/80"}`}>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                            3. День
                        </p>
                        <p className="mt-2 text-sm font-semibold text-foreground">
                            {bookingDate ? formatDateLabel(bookingDate) : "Не выбран"}
                        </p>
                    </div>
                    <div className={`rounded-xl border p-3 ${selectedSlot ? "border-primary/30 bg-primary/5" : "border-border/60 bg-background/80"}`}>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                            4. Время
                        </p>
                        <p className="mt-2 text-sm font-semibold text-foreground">
                            {selectedSlot ? `${selectedSlot.start_time} - ${selectedSlot.end_time}` : "Не выбрано"}
                        </p>
                    </div>
                    <div className={`rounded-xl border p-3 ${customerStepState === "ready" ? "border-primary/30 bg-primary/5" : customerStepState === "review" ? "border-amber-300 bg-amber-50" : "border-border/60 bg-background/80"}`}>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                            5. Клиент
                        </p>
                        <p className="mt-2 text-sm font-semibold text-foreground">
                            {customerStepState === "ready"
                                ? "Готово к подтверждению"
                                : customerStepState === "review"
                                    ? "Проверьте контакт"
                                    : "Нужно заполнить"}
                        </p>
                    </div>
                </div>
                <div className="mt-4 rounded-xl border border-primary/20 bg-primary/5 p-4" data-testid="calendar-booking-next-step">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                        Что делать дальше
                    </p>
                    <p className="mt-2 text-sm font-semibold text-foreground">
                        {bookingNextAction.title}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                        {bookingNextAction.description}
                    </p>
                </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]" data-testid="calendar-scheduling-panel">
                <div className="space-y-4">
                    <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                        <div className="space-y-1">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                1. Что нужно сделать
                            </p>
                            <p className="text-xs text-muted-foreground">
                                Сначала выберите услугу. После этого мы покажем только подходящих мастеров и корректное время.
                            </p>
                        </div>
                        {serviceCatalog.length === 0 ? (
                            <div className="mt-4 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-3 text-sm text-destructive">
                                Пока нет ни одной настроенной услуги. Без этого запись создавать нельзя.
                            </div>
                        ) : (
                            <label className="mt-4 block space-y-1">
                                <span className="text-sm font-medium text-muted-foreground">
                                    Услуга
                                </span>
                                <select
                                    value={selectedService?.name ?? ""}
                                    onChange={(event) => {
                                        const nextService = serviceCatalog.find((service) => service.name === event.target.value) ?? null;
                                        const currentSpecialistStillAvailable = nextService
                                            ? activeSpecialists.some((specialist) =>
                                                specialist.id === selectedSpecialist
                                                && specialist.services.some((service) => normalizeHumanText(service.name) === nextService.name))
                                            : false;
                                        setSelectedService(nextService, !currentSpecialistStillAvailable);
                                    }}
                                    className={`w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 ${(shouldShowBookingValidation && bookingFormErrors.service) ? "border-destructive/60" : "border-border/60"}`}
                                    data-testid="calendar-schedule-service"
                                >
                                    <option value="">Выберите услугу</option>
                                    {serviceCatalog.map((service) => (
                                        <option key={service.name} value={service.name}>
                                            {service.name} · от {service.duration_min} мин · от {service.price}₸ · {service.specialistCount} маст.
                                        </option>
                                    ))}
                                </select>
                                {shouldShowBookingValidation && bookingFormErrors.service && (
                                    <p className="text-xs text-destructive">{bookingFormErrors.service}</p>
                                )}
                            </label>
                        )}
                    </div>

                    <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                        <div className="space-y-1">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                2. Кто принимает клиента
                            </p>
                            <p className="text-xs text-muted-foreground">
                                В списке остаются только мастера, которые умеют делать выбранную услугу.
                            </p>
                        </div>
                        {!selectedService ? (
                            <p className="mt-4 rounded-lg border border-dashed border-border/60 bg-background/70 px-3 py-3 text-sm text-muted-foreground">
                                Сначала выберите услугу.
                            </p>
                        ) : specialistsForSelectedService.length === 0 ? (
                            <div className="mt-4 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-3 text-sm text-destructive" data-testid="calendar-schedule-specialist-missing">
                                Для выбранной услуги пока нет доступных мастеров.
                            </div>
                        ) : (
                            <label className="mt-4 block space-y-1">
                                <span className="text-sm font-medium text-muted-foreground">
                                    Мастер
                                </span>
                                <select
                                    value={selectedSpecialist}
                                    onChange={(event) => {
                                        setSelectedSpecialist(event.target.value);
                                        setSelectedSlot(null);
                                    }}
                                    className={`w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 ${(selectedService && bookingFormErrors.specialist) ? "border-destructive/60" : "border-border/60"}`}
                                    data-testid="calendar-schedule-specialist"
                                >
                                    <option value="">Выберите мастера</option>
                                    {specialistsForSelectedService.map((specialist) => {
                                        const matchedService = specialist.services.find((service) => normalizeHumanText(service.name) === selectedService?.name);
                                        return (
                                            <option key={specialist.id} value={specialist.id}>
                                                {specialist.name} {matchedService ? `· ${matchedService.duration_min} мин · ${matchedService.price}₸` : ""}
                                            </option>
                                        );
                                    })}
                                </select>
                                {selectedService && bookingFormErrors.specialist && (
                                    <p className="text-xs text-destructive">{bookingFormErrors.specialist}</p>
                                )}
                            </label>
                        )}
                    </div>

                    <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                        <div className="space-y-1">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                3. Когда приходит клиент
                            </p>
                            <p className="text-xs text-muted-foreground">
                                Выберите день, а затем свободное время. Если времени нет, ниже будет явная причина и следующий шаг.
                            </p>
                        </div>
                        <div className="mt-4 flex flex-wrap gap-2">
                            {bookingQuickDates.map((dateValue) => (
                                <button
                                    key={dateValue}
                                    type="button"
                                    onClick={() => {
                                        setBookingDate(dateValue);
                                        setSelectedSlot(null);
                                    }}
                                    className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                                        bookingDate === dateValue
                                            ? "border-primary/40 bg-primary/10 text-primary"
                                            : "border-border/60 text-muted-foreground hover:text-foreground"
                                    }`}
                                    data-testid={`calendar-booking-quick-date-${dateValue}`}
                                >
                                    {formatBookingQuickDateLabel(dateValue, today, tomorrow)}
                                </button>
                            ))}
                        </div>
                        <label className="mt-4 block space-y-1">
                            <span className="text-sm font-medium text-muted-foreground">
                                День новой записи
                            </span>
                            <input
                                id="calendar-booking-date"
                                type="date"
                                value={bookingDate}
                                onChange={(event) => {
                                    setBookingDate(event.target.value);
                                    setSelectedSlot(null);
                                }}
                                min={today}
                                className={`w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 ${(shouldShowBookingValidation && bookingFormErrors.bookingDate) ? "border-destructive/60" : "border-border/60"}`}
                                data-testid="calendar-booking-date"
                            />
                            {shouldShowBookingValidation && bookingFormErrors.bookingDate && (
                                <p className="text-xs text-destructive">{bookingFormErrors.bookingDate}</p>
                            )}
                        </label>

                        <div className="mt-4 rounded-xl border border-border/60 bg-background/80 p-4" data-testid="calendar-slot-state">
                            <div className="space-y-1">
                                <p className="text-sm font-semibold text-foreground">{bookingSlotState.title}</p>
                                <p className="text-xs text-muted-foreground">{bookingSlotState.description}</p>
                            </div>

                            {bookingSlotState.kind === "loading" && (
                                <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-4">
                                    {[...Array(8)].map((_, index) => (
                                        <div key={index} className="h-12 animate-pulse rounded-lg bg-muted/70" />
                                    ))}
                                </div>
                            )}

                            {bookingSlotState.kind === "error" && (
                                <div className="mt-4 flex flex-wrap gap-2">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            void refetchSlots();
                                        }}
                                        className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-semibold text-primary"
                                        data-testid="calendar-booking-retry-slots"
                                    >
                                        Повторить
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setBookingDate(formatDate(new Date(new Date(`${bookingDate}T00:00:00`).getTime() + 24 * 60 * 60 * 1000)));
                                            setSelectedSlot(null);
                                        }}
                                        className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                    >
                                        Попробовать другой день
                                    </button>
                                </div>
                            )}

                            {bookingSlotState.kind === "empty" && (
                                <div className="mt-4 flex flex-wrap gap-2">
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setBookingDate(formatDate(new Date(new Date(`${bookingDate}T00:00:00`).getTime() + 24 * 60 * 60 * 1000)));
                                            setSelectedSlot(null);
                                        }}
                                        className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-semibold text-primary"
                                        data-testid="calendar-booking-next-day"
                                    >
                                        Следующий день
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setSelectedSpecialist("")}
                                        className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                    >
                                        Выбрать другого мастера
                                    </button>
                                </div>
                            )}

                            {bookingSlotState.kind === "ready" && (
                                <div className="mt-4 space-y-4">
                                    {showPinnedEditSlot && selectedSlot && (
                                        <div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-3 text-sm" data-testid="calendar-edit-current-slot">
                                            <p className="font-semibold text-foreground">Текущее время записи</p>
                                            <p className="mt-1 text-xs text-muted-foreground">
                                                {selectedSlot.start_time} - {selectedSlot.end_time}. Можно оставить как есть или выбрать другой свободный слот ниже.
                                            </p>
                                        </div>
                                    )}
                                    {groupedSlots.map((group) => (
                                        <div key={group.label} className="space-y-2">
                                            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                                                {group.label}
                                            </p>
                                            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                                                {group.slots.map((slot) => (
                                                    <button
                                                        key={slot.start}
                                                        type="button"
                                                        onClick={() => handleSlotClick(slot)}
                                                        disabled={!slot.available}
                                                        className={`rounded-xl border px-3 py-3 text-left text-sm font-medium transition-colors ${
                                                            slot.available
                                                                ? selectedSlot?.start === slot.start
                                                                    ? "border-primary bg-primary text-primary-foreground"
                                                                    : "border-green-200 bg-green-50 text-green-900 hover:bg-green-100"
                                                                : "cursor-not-allowed border-border/60 bg-muted text-muted-foreground"
                                                        }`}
                                                        data-testid={`calendar-slot-${slot.start_time.replace(':', '-')}`}
                                                    >
                                                        <span className="block text-base font-semibold">{slot.start_time}</span>
                                                        <span className="mt-1 block text-xs opacity-80">до {slot.end_time}</span>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                    {selectedSpecialist && bookingFormErrors.slot && (
                                        <p className="text-xs text-destructive">{bookingFormErrors.slot}</p>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="space-y-4">
                    <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                        <div className="space-y-1">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                4. Кого записываем
                            </p>
                            <p className="text-xs text-muted-foreground">
                                Проверьте контакт клиента и только потом подтверждайте запись.
                            </p>
                        </div>

                        <form onSubmit={handleSubmit} className="mt-4 space-y-4" data-testid="calendar-booking-form">
                            <div className="rounded-lg bg-muted p-3 text-sm" data-testid="calendar-booking-summary">
                                <p><strong>Услуга:</strong> {selectedService ? `${selectedService.name}${selectedServicePrice ? ` · ${selectedServicePrice}₸` : ""}` : "Не выбрана"}</p>
                                <p><strong>Мастер:</strong> {currentSpecialist?.name ?? "Не выбран"}</p>
                                <p><strong>День:</strong> {bookingDate ? formatDateLabel(bookingDate) : "Не выбран"}</p>
                                <p><strong>Время:</strong> {selectedSlot ? `${selectedSlot.start_time} - ${selectedSlot.end_time}` : "Не выбрано"}</p>
                            </div>

                            {hasCasePrefill && (
                                <div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-3 text-sm">
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div>
                                            <p className="font-semibold text-foreground">Есть данные из заявки</p>
                                            <p className="text-xs text-muted-foreground">
                                                Можно одним нажатием подставить имя и телефон из текущей заявки.
                                            </p>
                                        </div>
                                        <button
                                            type="button"
                                            onClick={applyCasePrefill}
                                            className="rounded border border-primary/30 bg-background px-3 py-1.5 text-xs font-semibold text-primary"
                                            data-testid="calendar-booking-prefill-case"
                                        >
                                            Подставить из заявки
                                        </button>
                                    </div>
                                </div>
                            )}

                            {shouldShowBookingValidation && visibleBookingFormErrorList.length > 0 && (
                                <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-3 text-sm text-destructive" data-testid="calendar-booking-error-summary">
                                    <p className="font-semibold">Что нужно исправить перед записью:</p>
                                    <ul className="mt-2 list-disc pl-5">
                                        {visibleBookingFormErrorList.map((error) => (
                                            <li key={error}>{error}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                <label className="space-y-1">
                                    <span className="text-sm font-medium text-muted-foreground">
                                        Имя клиента
                                    </span>
                                    <input
                                        type="text"
                                        value={customerName}
                                        onChange={(event) => setCustomerName(event.target.value)}
                                        placeholder="Например, Айгуль С."
                                        maxLength={80}
                                        autoComplete="name"
                                        className={`w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 ${(shouldShowCustomerValidation && bookingFormErrors.customerName) ? "border-destructive/60" : "border-border/60"}`}
                                        data-testid="calendar-booking-customer-name"
                                    />
                                    <p className="text-xs text-muted-foreground">
                                        Как к клиенту обратиться в звонке или подтверждении записи.
                                    </p>
                                    {shouldShowCustomerValidation && bookingFormErrors.customerName && (
                                        <p className="text-xs text-destructive">{bookingFormErrors.customerName}</p>
                                    )}
                                </label>
                                <label className="space-y-1">
                                    <span className="text-sm font-medium text-muted-foreground">
                                        Телефон
                                    </span>
                                    <input
                                        type="tel"
                                        value={customerPhoneInput}
                                        onChange={(event) => setCustomerPhoneInput(event.target.value)}
                                        placeholder="+7 700 123 45 67"
                                        inputMode="tel"
                                        autoComplete="tel"
                                        maxLength={32}
                                        className={`w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 ${(shouldShowCustomerValidation && bookingFormErrors.customerPhone) ? "border-destructive/60" : "border-border/60"}`}
                                        data-testid="calendar-booking-customer-phone"
                                    />
                                    {customerPhoneInput ? (
                                        normalizedCustomerPhoneDisplay ? (
                                            <p className="text-xs text-emerald-700">
                                                Сохраним номер как {normalizedCustomerPhoneDisplay}.
                                            </p>
                                        ) : (
                                            <p className="text-xs text-muted-foreground">
                                                Можно писать как удобно: +7, 8, со скобками или без. Сохраним номер, когда он станет полным.
                                            </p>
                                        )
                                    ) : (
                                        <p className="text-xs text-muted-foreground">
                                            Можно ввести +7 700 123 45 67, 8 700 123 45 67 или вставить номер как есть.
                                        </p>
                                    )}
                                    {shouldShowCustomerValidation && bookingFormErrors.customerPhone && (
                                        <p className="text-xs text-destructive">{bookingFormErrors.customerPhone}</p>
                                    )}
                                </label>
                            </div>

                            <label className="space-y-1">
                                <span className="text-sm font-medium text-muted-foreground">
                                    Примечания
                                </span>
                                <textarea
                                    value={notes}
                                    onChange={(event) => setNotes(event.target.value)}
                                    placeholder="Что важно учесть по клиенту или записи"
                                    rows={3}
                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    data-testid="calendar-booking-notes"
                                />
                                <p className="text-xs text-muted-foreground">
                                    Необязательно. Оставьте только то, что поможет коллеге быстро понять контекст записи.
                                </p>
                            </label>

                            <div className="flex flex-wrap gap-3">
                                <button
                                    type="submit"
                                    disabled={!bookingFormReady || createMutation.isPending || updateMutation.isPending}
                                    className="btn-primary disabled:opacity-50"
                                    data-testid="calendar-booking-submit"
                                >
                                    {createMutation.isPending
                                        ? "Создаём..."
                                        : updateMutation.isPending
                                            ? "Сохраняем..."
                                            : bookingSubmitLabel}
                                </button>
                                <button
                                    type="button"
                                    onClick={closeBookingComposer}
                                    className="btn-ghost"
                                    data-testid="calendar-booking-cancel"
                                >
                                    Вернуться к списку
                                </button>
                            </div>
                            <p className="text-xs text-muted-foreground" data-testid="calendar-booking-submit-hint">
                                {bookingNextAction.description}
                            </p>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
)}

{bookingActionsBooking && (() => {
                const booking = bookingActionsBooking;
                const isNoShow = booking.status.toUpperCase() === "NO_SHOW";
                const currentDueInput = formatDateTimeLocalInput(booking.follow_up_due_at);
                const followUpGovernanceDraft = followUpGovernanceDrafts[booking.id] ?? {
                    ownerAgentId: booking.follow_up_owner_id ?? "",
                    dueAt: currentDueInput,
                };
                const noShowFollowUpDraft = noShowFollowUpDrafts[booking.id] ?? {
                    result: "contacted",
                    rebookedAppointmentId: "",
                    note: "",
                };
                const followUpGovernanceDirty = followUpGovernanceDraft.ownerAgentId !== (booking.follow_up_owner_id ?? "")
                    || followUpGovernanceDraft.dueAt !== currentDueInput;
                const governancePending = followUpGovernanceMutation.isPending && followUpGovernanceBookingId === booking.id;
                const followUpOwnerLabel = getFollowUpOwnerDisplayLabel({
                    name: booking.follow_up_owner_name,
                    id: booking.follow_up_owner_id,
                });
                const followUpDueLabel = formatDueAtLabel(booking.follow_up_due_at);
                const rebookCandidateOptions = bookings.filter((candidate) => {
                    if (candidate.id === booking.id) {
                        return false;
                    }
                    if (booking.case_id && candidate.case_id) {
                        return booking.case_id === candidate.case_id;
                    }
                    if (booking.customer_phone && candidate.customer_phone) {
                        return booking.customer_phone === candidate.customer_phone;
                    }
                    return false;
                });
                const rebookedBookingLabel = booking.no_show_followup_rebooked_appointment_id
                    ? (() => {
                        const linkedBooking = bookings.find((candidate) => candidate.id === booking.no_show_followup_rebooked_appointment_id);
                        return linkedBooking
                            ? formatBookingRangeLabel(linkedBooking.start_at, linkedBooking.end_at)
                            : "Новая запись сохранена";
                    })()
                    : null;
                const followUpSubmitBlocked = noShowFollowUpDraft.result === "rebooked" && !noShowFollowUpDraft.rebookedAppointmentId;
                const bookingActionMap = buildCalendarBookingActionAvailabilityMap(booking, calendarActionPermissions, calendarActorClass);
                const visitActions = getCalendarVisitActionOptions(booking, calendarActionPermissions, calendarActorClass);
                const editBookingAction = bookingActionMap.edit_booking;
                const cancelBookingAction = bookingActionMap.cancel_booking;
                const canEditCurrentBooking = editBookingAction.state === "enabled";
                const canCancelCurrentBooking = cancelBookingAction.state === "enabled";
                const canShowFollowUpGovernance = bookingActionMap.manage_follow_up_governance.visible;
                const cancelPending = cancelMutation.isPending && cancelBookingId === booking.id;
                return (
                    <div className="fixed inset-0 z-50" data-testid="calendar-booking-panel-overlay">
                        <div
                            className="absolute inset-0 bg-foreground/20"
                            onClick={closeBookingActionsPanel}
                            aria-hidden="true"
                        />
                        <div
                            className="absolute inset-y-0 right-0 flex h-full w-full max-w-[560px] flex-col gap-4 overflow-y-auto bg-background p-4 shadow-xl"
                            data-testid="calendar-booking-panel"
                        >
                            <div className="flex items-start justify-between gap-3">
                                <div className="space-y-1">
                                    <p className="text-sm font-semibold">Действия по записи</p>
                                    <p className="text-xs text-muted-foreground">
                                        Здесь оператор фиксирует результат визита, выбирает итог разговора после неявки и назначает, кто звонит клиенту.
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={closeBookingActionsPanel}
                                    className="rounded-full border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                    data-testid="calendar-booking-panel-close"
                                >
                                    Закрыть
                                </button>
                            </div>

                            <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                                <div className="flex flex-wrap items-center gap-2">
                                    <span className="text-sm font-semibold">
                                        {new Date(booking.start_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                        {" - "}
                                        {new Date(booking.end_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                    </span>
                                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${getBookingStatusColor(booking.status)}`}>
                                        {getBookingStatusLabel(booking.status)}
                                    </span>
                                </div>
                                <p className="mt-2 text-sm text-foreground/90">{booking.specialist_name}</p>
                                {booking.customer_name && (
                                    <p className="text-sm text-foreground/90">
                                        {booking.customer_name}
                                        {booking.customer_phone && <span className="text-muted-foreground"> • {formatPhoneInput(booking.customer_phone) || booking.customer_phone}</span>}
                                    </p>
                                )}
                                {booking.service_type && (
                                    <p className="mt-1 text-xs text-muted-foreground">{booking.service_type}</p>
                                )}
                                {isNoShow && (
                                    <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                                        <span className="rounded bg-muted px-2 py-0.5 font-semibold text-foreground/80">
                                            {formatContactTaskOwnerChipLabel(followUpOwnerLabel)}
                                        </span>
                                        <span className={`rounded px-2 py-0.5 font-semibold ${booking.follow_up_overdue ? "bg-red-100 text-red-900" : "bg-slate-100 text-slate-700"}`}>
                                            {formatContactTaskDueChipLabel(followUpDueLabel)}
                                        </span>
                                        {booking.follow_up_overdue && !booking.no_show_followup_done && (
                                            <span className="rounded bg-red-100 px-2 py-0.5 font-semibold text-red-900">
                                                Просрочено
                                            </span>
                                        )}
                                    </div>
                                )}
                                {booking.case_id && (
                                    <div className="mt-3">
                                        <Link
                                            href={buildCaseHref(booking.case_id)}
                                            className="rounded border border-border/60 px-2.5 py-1 text-xs font-semibold text-foreground hover:bg-background"
                                            data-testid="calendar-booking-open-case"
                                        >
                                            Открыть чат заявки
                                        </Link>
                                    </div>
                                )}
                            </div>

                            {canWriteCalendar && (
                                <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                        Исправить запись
                                    </p>
                                    <p className="mt-1 text-xs text-muted-foreground">
                                        Если время, услуга или контакт указаны неверно, откройте запись в режиме редактирования и сохраните новые данные.
                                    </p>
                                    {canEditCurrentBooking ? (
                                        <div className="mt-3 flex flex-wrap gap-2">
                                            <button
                                                type="button"
                                                onClick={() => openEditBookingComposer(booking)}
                                                className="rounded-md border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-semibold text-primary"
                                                data-testid="calendar-booking-edit"
                                            >
                                                Изменить запись
                                            </button>
                                        </div>
                                    ) : (
                                        <p className="mt-3 rounded-lg border border-border/60 bg-background/80 px-3 py-3 text-xs text-muted-foreground" data-testid="calendar-booking-edit-disabled">
                                            {editBookingAction.blockedReason ?? `Для статуса «${getBookingStatusLabel(booking.status)}» редактирование недоступно.`}
                                        </p>
                                    )}
                                </div>
                            )}

                            {canWriteCalendar && visitActions.length > 0 && (
                                <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                        Что с визитом
                                    </p>
                                    <p className="mt-1 text-xs text-muted-foreground">
                                        Выберите итог визита, чтобы список сразу показал корректный следующий шаг.
                                    </p>
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        {visitActions.map((action) => {
                                            const isPending = statusMutation.isPending && statusUpdateBookingId === booking.id;
                                            return (
                                                <button
                                                    key={`${booking.id}-${action.actionId}`}
                                                    type="button"
                                                    onClick={() => handleVisitStatusSubmit(booking.id, action.status, booking.version)}
                                                    disabled={isPending}
                                                    className="rounded-md border border-border/70 px-2.5 py-1.5 text-xs font-medium hover:bg-background disabled:opacity-50"
                                                >
                                                    {isPending ? "Обновляем..." : action.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {canWriteCalendar && (
                                <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                        Отменить запись
                                    </p>
                                    <p className="mt-1 text-xs text-muted-foreground">
                                        Используйте отмену только если визит действительно не состоится. Причина поможет коллеге быстро понять, что произошло.
                                    </p>
                                    {canCancelCurrentBooking ? (
                                        <div className="mt-3 space-y-3">
                                            <label className="block space-y-1">
                                                <span className="text-xs font-medium text-muted-foreground">
                                                    Причина отмены
                                                </span>
                                                <textarea
                                                    value={cancelReasonDraft}
                                                    onChange={(event) => setCancelReasonDraft(event.target.value)}
                                                    rows={2}
                                                    placeholder="Например, клиент отменил визит или время выбрали ошибочно"
                                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                    data-testid="calendar-booking-cancel-reason"
                                                />
                                            </label>
                                            <div className="flex flex-wrap gap-2">
                                                <button
                                                    type="button"
                                                    onClick={() => handleCancelBookingSubmit(booking.id, booking.version)}
                                                    disabled={cancelPending}
                                                    className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-1.5 text-xs font-semibold text-destructive disabled:opacity-50"
                                                    data-testid="calendar-booking-cancel-submit"
                                                >
                                                    {cancelPending ? "Отменяем..." : "Подтвердить отмену"}
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <p className="mt-3 rounded-lg border border-border/60 bg-background/80 px-3 py-3 text-xs text-muted-foreground" data-testid="calendar-booking-cancel-disabled">
                                            {cancelBookingAction.blockedReason ?? `Для статуса «${getBookingStatusLabel(booking.status)}» отмена недоступна.`}
                                        </p>
                                    )}
                                </div>
                            )}

                            {canWriteCalendar && isNoShow && (
                                <div className="rounded-xl border border-border/60 bg-card/80 p-4">
                                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                        Что решили после неявки
                                    </p>
                                    <p className="mt-1 text-xs text-muted-foreground">
                                        Зафиксируйте итог разговора с клиентом. Если клиента переписали, обязательно привяжите новую запись.
                                    </p>
                                    <div className="mt-3 space-y-3">
                                        {booking.no_show_followup_done ? (
                                            <>
                                                <span className="rounded-md bg-green-100 px-2.5 py-1.5 text-xs font-medium text-green-800">
                                                    {getContactTaskResultLabel(booking.no_show_followup_result)}
                                                </span>
                                                {rebookedBookingLabel && (
                                                    <span className="rounded-md bg-muted px-2.5 py-1.5 text-xs font-medium text-muted-foreground">
                                                        Новая запись: {rebookedBookingLabel}
                                                    </span>
                                                )}
                                            </>
                                        ) : (
                                            <div className="space-y-3">
                                                <p className="text-xs text-muted-foreground">
                                                    Сначала выберите итог разговора. Если клиента переписали, обязательно привяжите новую запись.
                                                </p>
                                                <div className="flex flex-wrap gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() => setNoShowFollowUpDraft(booking.id, { result: "contacted", rebookedAppointmentId: "" })}
                                                        className={`rounded-md border px-2.5 py-1.5 text-xs font-medium ${noShowFollowUpDraft.result === "contacted" ? "border-primary/30 bg-primary/5 text-primary" : "border-border/70 hover:bg-background"}`}
                                                        data-testid="calendar-follow-up-result-contacted"
                                                    >
                                                        Связались
                                                    </button>
                                                    <button
                                                        type="button"
                                                        onClick={() => setNoShowFollowUpDraft(booking.id, { result: "rebooked" })}
                                                        className={`rounded-md border px-2.5 py-1.5 text-xs font-medium ${noShowFollowUpDraft.result === "rebooked" ? "border-primary/30 bg-primary/5 text-primary" : "border-border/70 hover:bg-background"}`}
                                                        data-testid="calendar-follow-up-result-rebooked"
                                                    >
                                                        Клиента переписали
                                                    </button>
                                                </div>
                                                {noShowFollowUpDraft.result === "rebooked" && (
                                                    <label className="block space-y-1">
                                                        <span className="text-xs font-medium text-muted-foreground">
                                                            На какую новую запись переписали
                                                        </span>
                                                        <select
                                                            value={noShowFollowUpDraft.rebookedAppointmentId}
                                                            onChange={(event) => setNoShowFollowUpDraft(booking.id, { rebookedAppointmentId: event.target.value })}
                                                            className={`w-full rounded-lg border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 ${followUpSubmitBlocked ? "border-destructive/60" : "border-border/60"}`}
                                                            data-testid="calendar-follow-up-rebooked-select"
                                                        >
                                                            <option value="">
                                                                {rebookCandidateOptions.length > 0
                                                                    ? "Выберите новую запись"
                                                                    : "Нет доступных связанных записей"}
                                                            </option>
                                                            {rebookCandidateOptions.map((candidate) => (
                                                                <option key={candidate.id} value={candidate.id}>
                                                                    {formatBookingRangeLabel(candidate.start_at, candidate.end_at)}
                                                                </option>
                                                            ))}
                                                        </select>
                                                        {rebookCandidateOptions.length === 0 ? (
                                                            <p className="text-xs text-destructive">
                                                                Сначала создайте новую запись по этой же заявке, затем зафиксируйте результат.
                                                            </p>
                                                        ) : followUpSubmitBlocked ? (
                                                            <p className="text-xs text-destructive">
                                                                Выберите новую запись, чтобы закрыть неявку как переписанную.
                                                            </p>
                                                        ) : null}
                                                    </label>
                                                )}
                                                <label className="block space-y-1">
                                                    <span className="text-xs font-medium text-muted-foreground">
                                                        Комментарий
                                                    </span>
                                                    <textarea
                                                        value={noShowFollowUpDraft.note}
                                                        onChange={(event) => setNoShowFollowUpDraft(booking.id, { note: event.target.value })}
                                                        rows={2}
                                                        placeholder="Что произошло и что важно знать дальше"
                                                        className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                        data-testid="calendar-follow-up-note"
                                                    />
                                                </label>
                                                <div className="flex flex-wrap gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() => handleFollowUpSubmit(booking.id, booking.version, noShowFollowUpDraft)}
                                                        disabled={followUpSubmitBlocked || (followUpMutation.isPending && followUpBookingId === booking.id)}
                                                        className="rounded-md border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-semibold text-primary disabled:opacity-50"
                                                        data-testid="calendar-follow-up-submit"
                                                    >
                                                        {followUpMutation.isPending && followUpBookingId === booking.id
                                                            ? "Сохраняем..."
                                                            : "Сохранить результат связи"}
                                                    </button>
                                                    {(noShowFollowUpDraft.note || noShowFollowUpDraft.rebookedAppointmentId || noShowFollowUpDraft.result !== "contacted") && (
                                                        <button
                                                            type="button"
                                                            onClick={() => clearNoShowDraft(booking.id)}
                                                            className="rounded-md border border-border/70 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-background"
                                                        >
                                                            Сбросить
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}

                            {canShowFollowUpGovernance && (
                                <div className="rounded-xl border border-border/60 bg-card/80 p-4" data-testid="calendar-follow-up-governance-card">
                                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                                        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                            Кто отвечает за звонок
                                        </p>
                                        {booking.follow_up_overdue && (
                                            <span className="rounded bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-900">
                                                Просрочено
                                            </span>
                                        )}
                                    </div>
                                    <p className="mb-3 text-xs text-muted-foreground">
                                        Назначьте ответственного и крайний срок, чтобы просроченные звонки не терялись в очереди.
                                    </p>
                                    <div className="grid gap-2 sm:grid-cols-2">
                                        <label className="space-y-1">
                                            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                Кто звонит клиенту
                                            </span>
                                            <select
                                                value={followUpGovernanceDraft.ownerAgentId}
                                                onChange={(event) => setFollowUpGovernanceDraft(booking.id, { ownerAgentId: event.target.value })}
                                                className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                disabled={governancePending}
                                                data-testid="calendar-follow-up-governance-owner"
                                            >
                                                <option value="">Пока не назначено</option>
                                                {followUpOwnerOptions.map((agent) => (
                                                    <option key={agent.id} value={agent.id}>
                                                        {agent.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </label>
                                        <label className="space-y-1">
                                            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                Позвонить до
                                            </span>
                                            <input
                                                type="datetime-local"
                                                value={followUpGovernanceDraft.dueAt}
                                                onChange={(event) => setFollowUpGovernanceDraft(booking.id, { dueAt: event.target.value })}
                                                className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                disabled={governancePending}
                                                data-testid="calendar-follow-up-governance-due"
                                            />
                                        </label>
                                    </div>
                                    <div className="mt-3 flex flex-wrap items-center gap-2">
                                        <button
                                            type="button"
                                            onClick={() => setFollowUpGovernanceDraft(booking.id, { ownerAgentId: meData?.agent?.id ?? followUpGovernanceDraft.ownerAgentId })}
                                            className="rounded border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground disabled:opacity-50"
                                            disabled={governancePending}
                                        >
                                            Назначить звонок мне
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => handleFollowUpGovernanceSubmit(
                                                booking.id,
                                                booking.version,
                                                followUpGovernanceDraft.ownerAgentId,
                                                followUpGovernanceDraft.dueAt,
                                            )}
                                            className="rounded border border-primary/30 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary disabled:opacity-50"
                                            disabled={!followUpGovernanceDirty || governancePending}
                                            data-testid="calendar-follow-up-governance-save"
                                        >
                                            {governancePending ? "Сохраняем..." : "Сохранить ответственного и срок"}
                                        </button>
                                        {followUpGovernanceDirty && (
                                            <button
                                                type="button"
                                                onClick={() => clearBookingFollowUpDrafts(booking.id)}
                                                className="rounded border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
                                                disabled={governancePending}
                                            >
                                                Сбросить
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                );
            })()}
        </div>
    );

}
