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
    collectBookingCaseEffectMessages,
    createBooking,
    fetchBookings,
    getBookingAttentionLabel,
    getVisitActionOptions,
    registerNoShowFollowUp,
    type BookingQueueLane,
    type BookingQueueMode,
    type BookingStatusFilter,
    type BookingStatusUpdateRequest,
    updateBookingFollowUpGovernance,
    updateBookingStatus,
} from "@/lib/calendar-bookings";
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
    type ConsoleRole,
    type QueueSavedView,
    queueStateApi,
} from "@/lib/api-client";

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

function getApiErrorMessage(error: unknown, fallback: string): string {
    return (error as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message
        || (error as Error)?.message
        || fallback;
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
    owner: "Owner",
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
        parts.push("default");
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

    // Form state
    const [selectedSpecialist, setSelectedSpecialist] = useState<string>("");
    const [selectedDate, setSelectedDate] = useState<string>(defaultSelectedDate);
    const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
    const [selectedService, setSelectedService] = useState<{ name: string; duration_min: number; price: number } | null>(null);
    const [customerName, setCustomerName] = useState("");
    const [customerPhone, setCustomerPhone] = useState("");
    const [notes, setNotes] = useState("");
    const [showForm, setShowForm] = useState(false);
    const [showPastDates, setShowPastDates] = useState(false);
    const [statusUpdateBookingId, setStatusUpdateBookingId] = useState<string | null>(null);
    const [followUpBookingId, setFollowUpBookingId] = useState<string | null>(null);
    const [followUpGovernanceBookingId, setFollowUpGovernanceBookingId] = useState<string | null>(null);
    const [queueMode, setQueueMode] = useState<BookingQueueMode>(defaultQueueMode);
    const [queueLane, setQueueLane] = useState<BookingQueueLane>(defaultQueueLane);
    const [queueStatusFilter, setQueueStatusFilter] = useState<BookingStatusFilter>("all");
    const [queueSearch, setQueueSearch] = useState("");
    const [followUpOwnerId, setFollowUpOwnerId] = useState("");
    const [followUpOverdueOnly, setFollowUpOverdueOnly] = useState(false);
    const [followUpGovernanceDrafts, setFollowUpGovernanceDrafts] = useState<Record<string, { ownerAgentId: string; dueAt: string }>>({});
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
    const savedViews = useMemo(
        () => savedViewsQuery.data?.items ?? [],
        [savedViewsQuery.data?.items],
    );
    const followUpOwnerOptions = useMemo(
        () => (followUpOwnersQuery.data?.items ?? [])
            .filter((agent) => agent.is_active && canAccessConsole(agent.role, "calendar", "write"))
            .filter((agent) => !selectedBranchId || !agent.branch_id || agent.branch_id === selectedBranchId)
            .map((agent) => ({
                id: agent.id,
                name: agent.name?.trim() || agent.id,
            })),
        [followUpOwnersQuery.data?.items, selectedBranchId],
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
    const currentQueueSnapshot = useMemo<CalendarQueueStateSnapshot>(
        () => ({
            selectedDate,
            queueMode,
            queueLane,
            queueStatusFilter,
            queueSearch,
            followUpOwnerId,
            followUpOverdueOnly,
        }),
        [followUpOverdueOnly, followUpOwnerId, queueLane, queueMode, queueSearch, queueStatusFilter, selectedDate],
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
        setFollowUpGovernanceDrafts({});
        setSelectedDate(defaultSelectedDate);
        setQueueMode(defaultQueueMode);
        setQueueLane(defaultQueueLane);
        setQueueStatusFilter("all");
        setQueueSearch("");
        setFollowUpOwnerId("");
        setFollowUpOverdueOnly(false);
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
    }, [calendarWorkspaceScope, defaultQueueLane, defaultQueueMode, defaultSelectedDate, urlQueueStateKey]);

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
        setSelectedDate(queueSnapshot?.selectedDate ?? defaultSelectedDate);
        setQueueMode(queueSnapshot?.queueMode ?? defaultQueueMode);
        setQueueLane(queueSnapshot?.queueLane ?? defaultQueueLane);
        setQueueStatusFilter(queueSnapshot?.queueStatusFilter ?? "all");
        setQueueSearch(queueSnapshot?.queueSearch ?? "");
        setFollowUpOwnerId(queueSnapshot?.followUpOwnerId ?? "");
        setFollowUpOverdueOnly(queueSnapshot?.followUpOverdueOnly ?? false);
        setActiveSavedViewId(matchedSavedView?.id ?? null);
        setSaveViewDraftName("");
        setSaveViewComposerOpen(false);
        setSaveViewScopeDraft("personal");
        setSaveViewTargetBranchIdDraft("");
        setSaveViewTargetRoleDraft("");
        setSaveViewDefaultDraft(false);
        setSaveViewDefaultTouched(false);
        if (source === "server" && queueSnapshot) {
            lastSavedQueueStateRef.current = JSON.stringify({
                surface: "calendar",
                case_id: focusedCaseId || undefined,
                conversation_id: focusedConversationId || undefined,
                version: 1,
                query_state: buildCalendarQueueStatePayload(queueSnapshot),
            });
        }
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
    const { data: specialistsData, isError: specialistsError, error: specialistsErrorData } = useQuery({
        queryKey: ["specialists"],
        queryFn: fetchSpecialists,
        enabled: !!session && canReadCalendar,
        retry: 1,
    });

    const specialists = specialistsData?.items ?? [];
    const currentSpecialist = specialists.find(s => s.id === selectedSpecialist);
    const duration = selectedService?.duration_min || 60;

    const { data: slotsData, isLoading: slotsLoading } = useQuery({
        queryKey: ["slots", selectedSpecialist, selectedDate, duration],
        queryFn: () => fetchSlots(selectedSpecialist, selectedDate, duration),
        enabled: !!session && canReadCalendar && !!selectedSpecialist && !!selectedDate,
    });

    const slots = slotsData?.slots ?? [];

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
    const allowPastDateSelection = showPastDates || queueMode === "history";
    const queueHeading = selectedDate
        ? `Записи на ${new Date(selectedDate).toLocaleDateString("ru-RU", { day: "numeric", month: "short" })}`
        : queueMode === "history"
            ? "История записей"
            : "Записи";

    const applyCalendarQueueSnapshot = (
        snapshot: CalendarQueueStateSnapshot,
        {
            savedViewId = null,
        }: {
            savedViewId?: string | null;
        } = {},
    ) => {
        setSelectedDate(snapshot.selectedDate);
        setQueueMode(snapshot.queueMode);
        setQueueLane(snapshot.queueLane);
        setQueueStatusFilter(snapshot.queueStatusFilter);
        setQueueSearch(snapshot.queueSearch);
        setFollowUpOwnerId(snapshot.followUpOwnerId);
        setFollowUpOverdueOnly(snapshot.followUpOverdueOnly);
        setActiveSavedViewId(savedViewId);
        setFollowUpGovernanceDrafts({});
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

    // Create booking mutation
    const createMutation = useMutation({
        mutationFn: createBooking,
        onSuccess: () => {
            toast.success("Запись создана!");
            queryClient.invalidateQueries({ queryKey: ["slots"] });
            queryClient.invalidateQueries({ queryKey: ["bookings"] });
            resetForm();
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "BOOKING_CONFLICT") {
                toast.error("Это время уже занято. Выберите другой слот.");
            } else {
                toast.error("Не удалось создать запись");
            }
        },
    });

    const statusMutation = useMutation({
        mutationFn: async (payload: { bookingId: string; status: BookingStatusUpdateRequest["status"] }) => {
            setStatusUpdateBookingId(payload.bookingId);
            return updateBookingStatus(payload.bookingId, { status: payload.status });
        },
        onSuccess: (data, variables) => {
            const labels: Record<BookingStatusUpdateRequest["status"], string> = {
                COMPLETED: "Статус: клиент пришел",
                NO_SHOW: "Статус: клиент не пришел",
            };
            const effectMessages = collectBookingCaseEffectMessages(data);
            const suffix = effectMessages.length > 0 ? ` ${effectMessages.join(" ")}` : "";
            toast.success(`${labels[variables.status]}.${suffix}`.trim());
            queryClient.invalidateQueries({ queryKey: ["bookings"] });
            if (focusedCaseId) {
                queryClient.invalidateQueries({ queryKey: ["case", focusedCaseId] });
                queryClient.invalidateQueries({ queryKey: ["cases"] });
            }
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "BOOKING_STATUS_TRANSITION_DENIED") {
                toast.error("Недопустимый переход статуса для этой записи");
            } else if (code === "INVALID_STATUS") {
                toast.error("Некорректный статус визита");
            } else {
                toast.error("Не удалось обновить статус визита");
            }
        },
        onSettled: () => {
            setStatusUpdateBookingId(null);
        },
    });

    const followUpMutation = useMutation({
        mutationFn: async (payload: {
            bookingId: string;
            result: "contacted" | "rebooked";
            rebookedAppointmentId?: string;
        }) => {
            setFollowUpBookingId(payload.bookingId);
            return registerNoShowFollowUp(payload.bookingId, {
                result: payload.result,
                rebooked_appointment_id: payload.rebookedAppointmentId,
            });
        },
        onSuccess: (data, variables) => {
            const effectMessages = collectBookingCaseEffectMessages(data);
            const suffix = effectMessages.length > 0 ? ` ${effectMessages.join(" ")}` : "";
            if (variables.result === "rebooked") {
                toast.success(`Follow-up закрыт: клиент перезаписан.${suffix}`.trim());
            } else {
                toast.success(`Follow-up закрыт: с клиентом связались.${suffix}`.trim());
            }
            queryClient.invalidateQueries({ queryKey: ["bookings"] });
            if (focusedCaseId) {
                queryClient.invalidateQueries({ queryKey: ["case", focusedCaseId] });
                queryClient.invalidateQueries({ queryKey: ["cases"] });
            }
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "BOOKING_STATUS_REQUIRED") {
                toast.error("Follow-up доступен только для статуса 'Не пришел'");
            } else {
                toast.error("Не удалось зафиксировать follow-up");
            }
        },
        onSettled: () => {
            setFollowUpBookingId(null);
        },
    });

    const followUpGovernanceMutation = useMutation({
        mutationFn: async (payload: {
            bookingId: string;
            ownerAgentId: string;
            dueAt: string;
        }) => {
            setFollowUpGovernanceBookingId(payload.bookingId);
            return updateBookingFollowUpGovernance(payload.bookingId, {
                owner_agent_id: payload.ownerAgentId || null,
                due_at: payload.dueAt ? new Date(payload.dueAt).toISOString() : null,
            });
        },
        onSuccess: (data, variables) => {
            toast.success("Follow-up owner и дедлайн обновлены");
            queryClient.invalidateQueries({ queryKey: ["bookings"] });
            if (focusedCaseId) {
                queryClient.invalidateQueries({ queryKey: ["case", focusedCaseId] });
                queryClient.invalidateQueries({ queryKey: ["cases"] });
            }
            setFollowUpGovernanceDrafts((current) => {
                const next = { ...current };
                delete next[variables.bookingId];
                return next;
            });
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "FOLLOW_UP_ALREADY_CLOSED") {
                toast.error("Follow-up уже закрыт");
            } else if (code === "BOOKING_STATUS_REQUIRED") {
                toast.error("Governance доступен только для статуса 'Не пришел'");
            } else if (code === "ACCESS_DENIED") {
                toast.error("Недостаточно прав для управления follow-up");
            } else {
                toast.error("Не удалось обновить follow-up governance");
            }
        },
        onSettled: () => {
            setFollowUpGovernanceBookingId(null);
        },
    });

    const resetForm = () => {
        setSelectedSlot(null);
        setCustomerName("");
        setCustomerPhone("");
        setNotes("");
        setShowForm(false);
    };

    const handleQueueModeChange = (nextMode: BookingQueueMode) => {
        setQueueMode(nextMode);
        if (nextMode === "history") {
            setQueueLane("all");
            return;
        }
        if (!selectedDate) {
            setSelectedDate(today);
            setSelectedSlot(null);
        } else if (selectedDate < today && !showPastDates) {
            setSelectedDate(today);
            setSelectedSlot(null);
        }
    };

    const setFollowUpGovernanceDraft = (
        bookingId: string,
        patch: Partial<{ ownerAgentId: string; dueAt: string }>,
    ) => {
        setFollowUpGovernanceDrafts((current) => ({
            ...current,
            [bookingId]: {
                ownerAgentId: patch.ownerAgentId ?? current[bookingId]?.ownerAgentId ?? "",
                dueAt: patch.dueAt ?? current[bookingId]?.dueAt ?? "",
            },
        }));
    };

    const handleSlotClick = (slot: TimeSlot) => {
        if (!slot.available || !canWriteCalendar) return;
        setSelectedSlot(slot);
        setShowForm(true);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedSlot || !selectedSpecialist || !canWriteCalendar) return;

        const startAt = new Date(selectedSlot.start);
        const endAt = new Date(selectedSlot.end);

        createMutation.mutate({
            specialist_id: selectedSpecialist,
            start_at: startAt.toISOString(),
            end_at: endAt.toISOString(),
            customer_name: customerName || undefined,
            customer_phone: customerPhone || undefined,
            service_type: selectedService?.name || undefined,
            notes: notes || undefined,
            conversation_id: focusedConversationId || undefined,
            case_id: focusedCaseId || undefined,
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
                    <div className="badge mb-3">Calendar</div>
                    <h1 className="text-2xl font-semibold">Записи</h1>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Управляйте очередью визитов, подтверждайте статусы и возвращайтесь к нужной заявке без потери контекста.
                    </p>
                    {!canWriteCalendar && (
                        <p className="mt-2 text-xs text-muted-foreground">
                            Read-only доступ: создание и отмена записей недоступны.
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
                                className="rounded border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-background"
                                data-testid="calendar-clear-case-context"
                            >
                                Показать все записи
                            </Link>
                        </div>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left: Filters & Slots */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Debug/Error info */}
                    {specialistsError && (
                        <div className="card-surface p-4 text-destructive">
                            <h3 className="font-semibold mb-1">Не удалось загрузить список мастеров</h3>
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

                    {/* Filters */}
                    <div className="card-surface p-4 space-y-4">
                        <h2 className="font-semibold text-lg">Выберите мастера и дату</h2>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Specialist */}
                            <div>
                                <label className="block text-sm font-medium text-muted-foreground mb-1">
                                    Мастер
                                </label>
                                <select
                                    value={selectedSpecialist}
                                    onChange={(e) => {
                                        setSelectedSpecialist(e.target.value);
                                        setSelectedSlot(null);
                                        setSelectedService(null);
                                    }}
                                    className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                >
                                    <option value="">Выберите мастера</option>
                                    {specialists.map((s) => (
                                        <option key={s.id} value={s.id}>
                                            {s.name} {s.branch_name ? `(${s.branch_name})` : ""}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Service */}
                            {currentSpecialist && currentSpecialist.services.length > 0 && (
                                <div>
                                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                                        Услуга
                                    </label>
                                    <select
                                        value={selectedService?.name || ""}
                                        onChange={(e) => {
                                            const service = currentSpecialist.services.find(s => s.name === e.target.value);
                                            setSelectedService(service || null);
                                            setSelectedSlot(null);
                                        }}
                                        className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    >
                                        <option value="">Любая услуга</option>
                                        {currentSpecialist.services.map((s, i) => (
                                            <option key={i} value={s.name}>
                                                {s.name} ({s.duration_min} мин, {s.price}₸)
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {/* Date */}
                            <div>
                                <label
                                    className="block text-sm font-medium text-muted-foreground mb-1"
                                    htmlFor="calendar-date"
                                >
                                    Дата
                                </label>
                                <input
                                    id="calendar-date"
                                    type="date"
                                    value={selectedDate}
                                    onChange={(e) => {
                                        setSelectedDate(e.target.value);
                                        setSelectedSlot(null);
                                    }}
                                    min={allowPastDateSelection ? undefined : today}
                                    className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                />
                                {queueMode === "history" && !selectedDate ? (
                                    <p className="mt-2 text-xs text-muted-foreground" data-testid="calendar-history-all-dates-hint">
                                        История сейчас показывает все даты. Укажите день, только если хотите сузить архивный список.
                                    </p>
                                ) : focusedConversationId && !selectedDate && (
                                    <p className="mt-2 text-xs text-muted-foreground" data-testid="calendar-case-all-dates-hint">
                                        Сейчас показываем все даты по этой заявке. Выберите дату, только если хотите сузить список.
                                    </p>
                                )}
                                <label className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                                    <input
                                        type="checkbox"
                                        checked={allowPastDateSelection}
                                        onChange={(event) => {
                                            if (queueMode === "history") {
                                                return;
                                            }
                                            const enabled = event.target.checked;
                                            setShowPastDates(enabled);
                                            if (!enabled && selectedDate < today) {
                                                setSelectedDate(today);
                                                setSelectedSlot(null);
                                            }
                                        }}
                                        className="w-4 h-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                        disabled={queueMode === "history"}
                                        data-testid="calendar-show-past-dates"
                                    />
                                    {queueMode === "history" ? "История всегда разрешает прошлые даты" : "Показывать прошлые даты"}
                                </label>
                            </div>
                        </div>
                    </div>

                    {/* Slots Grid */}
                    {selectedSpecialist && selectedDate && (
                        <div className="card-surface p-4">
                            <h2 className="font-semibold text-lg mb-4">
                                Доступные слоты на {new Date(selectedDate).toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
                            </h2>

                            {slotsLoading ? (
                                <div className="animate-pulse grid grid-cols-4 md:grid-cols-6 gap-2">
                                    {[...Array(12)].map((_, i) => (
                                        <div key={i} className="h-12 bg-muted/70 rounded"></div>
                                    ))}
                                </div>
                            ) : slots.length === 0 ? (
                                <p className="text-muted-foreground text-center py-8">
                                    Нет доступных слотов на выбранную дату. Возможно, это выходной день.
                                </p>
                            ) : (
                                <div className="grid grid-cols-4 md:grid-cols-6 gap-2">
                                    {slots.map((slot, i) => (
                                        <button
                                            key={i}
                                            onClick={() => handleSlotClick(slot)}
                                            disabled={!slot.available}
                                            className={`
                                                py-3 px-2 rounded-lg text-sm font-medium transition-colors
                                                ${slot.available
                                                    ? selectedSlot?.start === slot.start
                                                        ? "bg-primary text-primary-foreground"
                                                        : "bg-green-50 text-green-800 hover:bg-green-100 border border-green-200"
                                                    : "bg-muted text-muted-foreground cursor-not-allowed"
                                                }
                                            `}
                                        >
                                            {slot.start_time}
                                        </button>
                                    ))}
                                </div>
                            )}

                            <div className="mt-4 flex gap-4 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 bg-green-100 border border-green-200 rounded"></span>
                                    Свободно
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 bg-muted rounded"></span>
                                    Занято
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 bg-primary rounded"></span>
                                    Выбрано
                                </span>
                            </div>
                        </div>
                    )}
                    {selectedSpecialist && !selectedDate && (
                        <div className="card-surface p-4 text-sm text-muted-foreground" data-testid="calendar-select-date-hint">
                            Выберите дату, чтобы посмотреть слоты по мастеру. Очередь справа уже показывает все связанные записи по заявке.
                        </div>
                    )}

                    {/* Booking Form */}
                    {showForm && selectedSlot && (
                        <div className="card-surface p-4">
                            <h2 className="font-semibold text-lg mb-4">Данные клиента</h2>

                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div className="bg-muted p-3 rounded-lg text-sm">
                                    <strong>Мастер:</strong> {currentSpecialist?.name}<br />
                                    <strong>Время:</strong> {selectedSlot.start_time} - {selectedSlot.end_time}<br />
                                    {selectedService && (
                                        <>
                                            <strong>Услуга:</strong> {selectedService.name} ({selectedService.price}₸)
                                        </>
                                    )}
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-muted-foreground mb-1">
                                            Имя клиента
                                        </label>
                                        <input
                                            type="text"
                                            value={customerName}
                                            onChange={(e) => setCustomerName(e.target.value)}
                                            placeholder="Иван Иванов"
                                            className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-muted-foreground mb-1">
                                            Телефон
                                        </label>
                                        <input
                                            type="tel"
                                            value={customerPhone}
                                            onChange={(e) => setCustomerPhone(e.target.value)}
                                            placeholder="+7 777 123 4567"
                                            className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                                        Примечания
                                    </label>
                                    <textarea
                                        value={notes}
                                        onChange={(e) => setNotes(e.target.value)}
                                        placeholder="Дополнительная информация..."
                                        rows={2}
                                        className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    />
                                </div>

                                <div className="flex gap-3">
                                    <button
                                        type="submit"
                                        disabled={createMutation.isPending}
                                        className="btn-primary disabled:opacity-50"
                                    >
                                        {createMutation.isPending ? "Создаём..." : "Записать клиента"}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={resetForm}
                                        className="btn-ghost"
                                    >
                                        Отмена
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}
                </div>

                {/* Right: Today's Bookings */}
                <div className="space-y-6">
                    <div className="card-surface p-4">
                        <h2 className="font-semibold text-lg mb-4">
                            {queueHeading}
                        </h2>
                        <div className="mb-3 flex flex-wrap gap-2 text-xs">
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
                        <div className="mb-4 space-y-2" data-testid="calendar-queue-controls">
                            <div className="flex flex-wrap items-center gap-2">
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
                                    Операции
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
                                    История
                                </button>
                            </div>
                            {queueMode === "ops" ? (
                                <div className="flex flex-wrap items-center gap-2">
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
                                        Только действия
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
                                <div className="rounded border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                                    История всегда показывает полный архивный срез без режима `Только действия`.
                                </div>
                            )}
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
                                <input
                                    type="text"
                                    value={queueSearch}
                                    onChange={(event) => setQueueSearch(event.target.value)}
                                    placeholder="Поиск по клиенту, телефону, услуге или ID записи"
                                    className="w-full rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    data-testid="calendar-queue-search"
                                />
                                <select
                                    value={queueStatusFilter}
                                    onChange={(event) => setQueueStatusFilter(event.target.value as BookingStatusFilter)}
                                    className="rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    data-testid="calendar-queue-status-filter"
                                >
                                    <option value="all">Все статусы</option>
                                    <option value="scheduled">Запланированные</option>
                                    <option value="completed">Пришёл</option>
                                    <option value="no_show">Не пришёл</option>
                                    <option value="cancelled">Отменённые</option>
                                </select>
                                {canReadTeam && (
                                    <select
                                        value={followUpOwnerId}
                                        onChange={(event) => setFollowUpOwnerId(event.target.value)}
                                        className="rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                                        data-testid="calendar-follow-up-owner-filter"
                                    >
                                        <option value="">Все follow-up owners</option>
                                        {followUpOwnerOptions.map((agent) => (
                                            <option key={agent.id} value={agent.id}>
                                                {agent.name}
                                            </option>
                                        ))}
                                    </select>
                                )}
                                <label className="flex min-h-[38px] items-center gap-2 rounded border border-border/60 bg-background px-3 py-2 text-xs text-muted-foreground">
                                    <input
                                        type="checkbox"
                                        checked={followUpOverdueOnly}
                                        onChange={(event) => setFollowUpOverdueOnly(event.target.checked)}
                                        className="h-4 w-4 rounded border-border/60"
                                        data-testid="calendar-follow-up-overdue-filter"
                                    />
                                    <span>Только просроченный follow-up</span>
                                </label>
                            </div>
                            <div className="rounded-lg border border-border/60 bg-background/80 p-3" data-testid="calendar-saved-views">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div>
                                        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                                            Сохранённые виды
                                        </p>
                                        <p className="mt-1 text-xs text-muted-foreground">
                                            Личные виды и командные пресеты календарной очереди.
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
                                                Сохранить targeting
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
                                        className="rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
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
                                                    default
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
                                                    targeting изменён
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
                                                className="w-full rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
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
                                                className="w-full rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
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
                                            className="min-w-[220px] flex-1 rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                                            data-testid="calendar-saved-view-name-input"
                                        />
                                        {canManageTeamPresets && (
                                            <div className="grid gap-2 sm:grid-cols-3">
                                                <label className="space-y-1">
                                                    <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                        Scope
                                                    </span>
                                                    <select
                                                        value={saveViewScopeDraft}
                                                        onChange={(event) => setSaveViewScopeDraft(event.target.value as "personal" | "team")}
                                                        className="w-full rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
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
                                                                className="w-full rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
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
                                                                className="w-full rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
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
                                                ? `Командных пресетов в этом targeting: ${matchingScopeSavedViewCount}`
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
                        </div>

                        {bookingsLoading ? (
                            <div className="animate-pulse space-y-3">
                                {[...Array(3)].map((_, i) => (
                                    <div key={i} className="h-16 bg-muted/70 rounded"></div>
                                ))}
                            </div>
                        ) : bookingsVisible.length === 0 ? (
                            <p className="text-muted-foreground text-center py-4">
                                {focusedConversationId
                                    ? "По этой заявке нет записей под выбранные фильтры"
                                    : "Нет записей под выбранные фильтры"}
                            </p>
                        ) : (
                            <div className="space-y-3">
                                {bookingsVisible.map((booking) => {
                                    const attentionLabel = getBookingAttentionLabel(booking);
                                    const isNoShow = booking.status.toUpperCase() === "NO_SHOW";
                                    const followUpOwnerLabel = booking.follow_up_owner_name?.trim()
                                        || (booking.follow_up_owner_id ? `Agent ${booking.follow_up_owner_id.slice(0, 8)}` : "Без владельца");
                                    const currentDueInput = formatDateTimeLocalInput(booking.follow_up_due_at);
                                    const followUpDueLabel = formatDueAtLabel(booking.follow_up_due_at);
                                    const followUpGovernanceDraft = followUpGovernanceDrafts[booking.id] ?? {
                                        ownerAgentId: booking.follow_up_owner_id ?? "",
                                        dueAt: currentDueInput,
                                    };
                                    const followUpGovernanceDirty = followUpGovernanceDraft.ownerAgentId !== (booking.follow_up_owner_id ?? "")
                                        || followUpGovernanceDraft.dueAt !== currentDueInput;
                                    const governancePending = followUpGovernanceMutation.isPending
                                        && followUpGovernanceBookingId === booking.id;
                                    return (
                                        <div
                                            key={booking.id}
                                            className="p-3 border border-border/60 rounded-lg hover:bg-muted/60"
                                            data-testid="calendar-booking-card"
                                        >
                                            <div className="flex justify-between items-start mb-1">
                                                <span className="font-medium text-sm">
                                                    {new Date(booking.start_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                                    {" - "}
                                                    {new Date(booking.end_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                                </span>
                                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getBookingStatusColor(booking.status)}`}>
                                                    {getBookingStatusLabel(booking.status)}
                                                </span>
                                            </div>
                                            <div className="text-sm text-muted-foreground">
                                                {booking.specialist_name}
                                            </div>
                                            {booking.customer_name && (
                                                <div className="text-sm">
                                                    {booking.customer_name}
                                                    {booking.customer_phone && (
                                                        <span className="text-muted-foreground"> • {booking.customer_phone}</span>
                                                    )}
                                                </div>
                                            )}
                                            {booking.service_type && (
                                                <div className="text-xs text-muted-foreground mt-1">
                                                    {booking.service_type}
                                                </div>
                                            )}
                                            {attentionLabel && (
                                                <div className="mt-2">
                                                    <span className="rounded bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                                                        {attentionLabel}
                                                    </span>
                                                </div>
                                            )}
                                            {isNoShow && (
                                                <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                                                    <span className="rounded bg-muted px-2 py-0.5 font-semibold text-foreground/80">
                                                        Owner: {followUpOwnerLabel}
                                                    </span>
                                                    <span className={`rounded px-2 py-0.5 font-semibold ${booking.follow_up_overdue ? "bg-red-100 text-red-900" : "bg-slate-100 text-slate-700"}`}>
                                                        {followUpDueLabel ? `Due: ${followUpDueLabel}` : "Due не задан"}
                                                    </span>
                                                    {booking.follow_up_overdue && !booking.no_show_followup_done && (
                                                        <span className="rounded bg-red-100 px-2 py-0.5 font-semibold text-red-900">
                                                            Просрочено
                                                        </span>
                                                    )}
                                                </div>
                                            )}
                                            {booking.case_id && (
                                                <div className="mt-2 flex items-center gap-2">
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
                                            {canWriteCalendar && getVisitActionOptions(booking.status).length > 0 && (
                                                <div className="mt-3 flex flex-wrap gap-2">
                                                    {getVisitActionOptions(booking.status).map((action) => {
                                                        const isPending = statusMutation.isPending && statusUpdateBookingId === booking.id;
                                                        return (
                                                            <button
                                                                key={`${booking.id}-${action.status}`}
                                                                type="button"
                                                                onClick={() => statusMutation.mutate({ bookingId: booking.id, status: action.status })}
                                                                disabled={isPending}
                                                                className="px-2.5 py-1.5 rounded-md border border-border/70 text-xs font-medium hover:bg-background disabled:opacity-50"
                                                            >
                                                                {isPending ? "Обновляем..." : action.label}
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                            {canWriteCalendar && isNoShow && (
                                                <div className="mt-2 flex flex-wrap gap-2">
                                                    {booking.no_show_followup_done ? (
                                                        <>
                                                            <span className="px-2.5 py-1.5 rounded-md bg-green-100 text-green-800 text-xs font-medium">
                                                                {booking.no_show_followup_result === "rebooked"
                                                                    ? "После неявки: перезаписан"
                                                                    : "После неявки: связались"}
                                                            </span>
                                                            {booking.no_show_followup_rebooked_appointment_id && (
                                                                <span className="px-2.5 py-1.5 rounded-md bg-muted text-muted-foreground text-xs font-medium">
                                                                    Новая запись: {booking.no_show_followup_rebooked_appointment_id.slice(0, 8)}
                                                                </span>
                                                            )}
                                                        </>
                                                    ) : (
                                                        <>
                                                            <button
                                                                type="button"
                                                                onClick={() =>
                                                                    followUpMutation.mutate({
                                                                        bookingId: booking.id,
                                                                        result: "contacted",
                                                                    })
                                                                }
                                                                disabled={followUpMutation.isPending && followUpBookingId === booking.id}
                                                                className="px-2.5 py-1.5 rounded-md border border-border/70 text-xs font-medium hover:bg-background disabled:opacity-50"
                                                            >
                                                                {followUpMutation.isPending && followUpBookingId === booking.id
                                                                    ? "Фиксируем..."
                                                                    : "Связались"}
                                                            </button>
                                                            <button
                                                                type="button"
                                                                onClick={() =>
                                                                    followUpMutation.mutate({
                                                                        bookingId: booking.id,
                                                                        result: "rebooked",
                                                                    })
                                                                }
                                                                disabled={followUpMutation.isPending && followUpBookingId === booking.id}
                                                                className="px-2.5 py-1.5 rounded-md border border-border/70 text-xs font-medium hover:bg-background disabled:opacity-50"
                                                            >
                                                                Перезаписали
                                                            </button>
                                                        </>
                                                    )}
                                                </div>
                                            )}
                                            {canManageFollowUpGovernance && isNoShow && !booking.no_show_followup_done && (
                                                <div className="mt-3 rounded-lg border border-border/60 bg-background/80 p-3" data-testid="calendar-follow-up-governance-card">
                                                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                                                        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                            Follow-up governance
                                                        </p>
                                                        {booking.follow_up_overdue && (
                                                            <span className="rounded bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-900">
                                                                overdue
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="grid gap-2 sm:grid-cols-2">
                                                        <label className="space-y-1">
                                                            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                                Owner
                                                            </span>
                                                            <select
                                                                value={followUpGovernanceDraft.ownerAgentId}
                                                                onChange={(event) => setFollowUpGovernanceDraft(booking.id, { ownerAgentId: event.target.value })}
                                                                className="w-full rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                                                                disabled={governancePending}
                                                                data-testid="calendar-follow-up-governance-owner"
                                                            >
                                                                <option value="">Без владельца</option>
                                                                {followUpOwnerOptions.map((agent) => (
                                                                    <option key={agent.id} value={agent.id}>
                                                                        {agent.name}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                        </label>
                                                        <label className="space-y-1">
                                                            <span className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                                                                Due
                                                            </span>
                                                            <input
                                                                type="datetime-local"
                                                                value={followUpGovernanceDraft.dueAt}
                                                                onChange={(event) => setFollowUpGovernanceDraft(booking.id, { dueAt: event.target.value })}
                                                                className="w-full rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
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
                                                            Назначить мне
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() => followUpGovernanceMutation.mutate({
                                                                bookingId: booking.id,
                                                                ownerAgentId: followUpGovernanceDraft.ownerAgentId,
                                                                dueAt: followUpGovernanceDraft.dueAt,
                                                            })}
                                                            className="rounded border border-primary/30 bg-primary/5 px-3 py-1 text-xs font-semibold text-primary disabled:opacity-50"
                                                            disabled={!followUpGovernanceDirty || governancePending}
                                                            data-testid="calendar-follow-up-governance-save"
                                                        >
                                                            {governancePending ? "Сохраняем..." : "Сохранить governance"}
                                                        </button>
                                                        {followUpGovernanceDirty && (
                                                            <button
                                                                type="button"
                                                                onClick={() => {
                                                                    setFollowUpGovernanceDrafts((current) => {
                                                                        const next = { ...current };
                                                                        delete next[booking.id];
                                                                        return next;
                                                                    });
                                                                }}
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
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
