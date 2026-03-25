import { getBookingStatusLabel } from "@/utils/labels";

export type CalendarActorClass = "manager" | "owner_admin" | "consultant_bot";
export type CalendarActionState = "enabled" | "disabled" | "hidden";
export type CalendarPermissionKey = "calendar_write" | "follow_up_governance";
export type CalendarBookingStatus =
    | "DRAFT"
    | "HOLD"
    | "PENDING_CONFIRMATION"
    | "CONFIRMED"
    | "RESCHEDULE_REQUESTED"
    | "CHECKED_IN"
    | "COMPLETED"
    | "NO_SHOW"
    | "CANCELLED";
export type CalendarQueueActionId = "apply_filters" | "reset_filters" | "load_saved_view" | "copy_share_url";
export type CalendarBookingActionId =
    | "edit_booking"
    | "cancel_booking"
    | "mark_completed"
    | "mark_no_show"
    | "record_follow_up_contacted"
    | "record_follow_up_rebooked"
    | "manage_follow_up_governance"
    | "open_case_from_booking";
export type CalendarActionId = CalendarQueueActionId | CalendarBookingActionId;
export type CalendarActionSurface =
    | "filter_panel"
    | "saved_views"
    | "booking_panel"
    | "follow_up_panel"
    | "follow_up_governance"
    | "case_linked_view";
export type CalendarBlockedReasonCode =
    | "permission_required"
    | "active_status_only"
    | "open_no_show_required"
    | "follow_up_already_closed"
    | "case_link_required";

export interface CalendarBookingLike {
    status: string;
    no_show_followup_done?: boolean;
    case_id?: string | null;
    allowed_actions?: readonly CalendarBookingActionId[];
    blocked_actions?: readonly {
        action_id: CalendarBookingActionId;
        reason_code: CalendarBlockedReasonCode;
    }[];
}

export interface CalendarActionPermissions {
    canWriteCalendar: boolean;
    canManageFollowUpGovernance: boolean;
}

export interface CalendarQueueActionDefinition {
    id: CalendarQueueActionId;
    surface: CalendarActionSurface;
    label: string;
    requiredPermissions: readonly CalendarPermissionKey[];
    actorClasses: readonly CalendarActorClass[];
}

interface CalendarBookingActionDefinition {
    id: CalendarBookingActionId;
    surface: CalendarActionSurface;
    label: string;
    requiredPermissions: readonly CalendarPermissionKey[];
    actorClasses: readonly CalendarActorClass[];
    allowedStatuses?: readonly CalendarBookingStatus[];
    requiresOpenNoShow?: boolean;
    requiresCaseLink?: boolean;
    inactiveState: Exclude<CalendarActionState, "enabled">;
    blockedReasonCode?: Exclude<CalendarBlockedReasonCode, "permission_required" | "case_link_required">;
    disabledReason?: (statusLabel: string) => string;
    visitStatus?: "COMPLETED" | "NO_SHOW";
}

export interface CalendarBookingActionAvailability {
    id: CalendarBookingActionId;
    label: string;
    surface: CalendarActionSurface;
    state: CalendarActionState;
    visible: boolean;
    blockedReasonCode?: CalendarBlockedReasonCode;
    blockedReason?: string;
    visitStatus?: "COMPLETED" | "NO_SHOW";
}

export interface CalendarBookingActionScenario {
    id: string;
    actorClass: CalendarActorClass;
    booking: {
        status: CalendarBookingStatus;
        no_show_followup_done: boolean;
        case_id: string | null;
    };
    expectedEnabled: readonly CalendarBookingActionId[];
    expectedDisabled: readonly CalendarBookingActionId[];
    expectedHidden: readonly CalendarBookingActionId[];
}

export const CALENDAR_ACTIVE_BOOKING_STATUSES: readonly CalendarBookingStatus[] = [
    "HOLD",
    "PENDING_CONFIRMATION",
    "CONFIRMED",
    "RESCHEDULE_REQUESTED",
    "CHECKED_IN",
] as const;

export const CALENDAR_QUEUE_ACTION_REGISTRY: readonly CalendarQueueActionDefinition[] = [
    {
        id: "apply_filters",
        surface: "filter_panel",
        label: "Применить фильтры",
        requiredPermissions: [],
        actorClasses: ["manager", "owner_admin"],
    },
    {
        id: "reset_filters",
        surface: "filter_panel",
        label: "Сбросить фильтры",
        requiredPermissions: [],
        actorClasses: ["manager", "owner_admin"],
    },
    {
        id: "load_saved_view",
        surface: "saved_views",
        label: "Открыть сохранённый вид",
        requiredPermissions: [],
        actorClasses: ["manager", "owner_admin"],
    },
    {
        id: "copy_share_url",
        surface: "saved_views",
        label: "Скопировать ссылку",
        requiredPermissions: [],
        actorClasses: ["manager", "owner_admin"],
    },
] as const;

export const CALENDAR_BOOKING_ACTION_REGISTRY: readonly CalendarBookingActionDefinition[] = [
    {
        id: "edit_booking",
        surface: "booking_panel",
        label: "Изменить запись",
        requiredPermissions: ["calendar_write"],
        actorClasses: ["manager", "owner_admin"],
        allowedStatuses: CALENDAR_ACTIVE_BOOKING_STATUSES,
        inactiveState: "disabled",
        blockedReasonCode: "active_status_only",
        disabledReason: (statusLabel) => `Для статуса «${statusLabel}» редактирование недоступно. Историю визита уже нужно сохранять без скрытого переписывания.`,
    },
    {
        id: "cancel_booking",
        surface: "booking_panel",
        label: "Отменить запись",
        requiredPermissions: ["calendar_write"],
        actorClasses: ["manager", "owner_admin"],
        allowedStatuses: CALENDAR_ACTIVE_BOOKING_STATUSES,
        inactiveState: "disabled",
        blockedReasonCode: "active_status_only",
        disabledReason: (statusLabel) => `Для статуса «${statusLabel}» отмена недоступна. Историю визита нужно оставлять неизменной.`,
    },
    {
        id: "mark_completed",
        surface: "booking_panel",
        label: "Пришел",
        requiredPermissions: ["calendar_write"],
        actorClasses: ["manager", "owner_admin"],
        allowedStatuses: CALENDAR_ACTIVE_BOOKING_STATUSES,
        inactiveState: "hidden",
        blockedReasonCode: "active_status_only",
        visitStatus: "COMPLETED",
    },
    {
        id: "mark_no_show",
        surface: "booking_panel",
        label: "Не пришел",
        requiredPermissions: ["calendar_write"],
        actorClasses: ["manager", "owner_admin"],
        allowedStatuses: CALENDAR_ACTIVE_BOOKING_STATUSES,
        inactiveState: "hidden",
        blockedReasonCode: "active_status_only",
        visitStatus: "NO_SHOW",
    },
    {
        id: "record_follow_up_contacted",
        surface: "follow_up_panel",
        label: "Связались",
        requiredPermissions: ["calendar_write"],
        actorClasses: ["manager", "owner_admin"],
        requiresOpenNoShow: true,
        inactiveState: "hidden",
        blockedReasonCode: "open_no_show_required",
    },
    {
        id: "record_follow_up_rebooked",
        surface: "follow_up_panel",
        label: "Клиента переписали",
        requiredPermissions: ["calendar_write"],
        actorClasses: ["manager", "owner_admin"],
        requiresOpenNoShow: true,
        inactiveState: "hidden",
        blockedReasonCode: "open_no_show_required",
    },
    {
        id: "manage_follow_up_governance",
        surface: "follow_up_governance",
        label: "Изменить ответственного и срок",
        requiredPermissions: ["follow_up_governance"],
        actorClasses: ["owner_admin"],
        requiresOpenNoShow: true,
        inactiveState: "hidden",
        blockedReasonCode: "open_no_show_required",
    },
    {
        id: "open_case_from_booking",
        surface: "case_linked_view",
        label: "Открыть чат заявки",
        requiredPermissions: [],
        actorClasses: ["manager", "owner_admin"],
        requiresCaseLink: true,
        inactiveState: "hidden",
    },
] as const;

const ACTIVE_ACTION_IDS: readonly CalendarBookingActionId[] = [
    "edit_booking",
    "cancel_booking",
    "mark_completed",
    "mark_no_show",
    "record_follow_up_contacted",
    "record_follow_up_rebooked",
    "manage_follow_up_governance",
    "open_case_from_booking",
] as const;

function calendarActionIds(...actionIds: CalendarBookingActionId[]) {
    return actionIds as readonly CalendarBookingActionId[];
}

const WITH_CASE_ACTIONS = calendarActionIds(
    "edit_booking",
    "cancel_booking",
    "mark_completed",
    "mark_no_show",
    "open_case_from_booking",
);

const NO_SHOW_OPEN_MANAGER_ACTIONS = calendarActionIds(
    "record_follow_up_contacted",
    "record_follow_up_rebooked",
    "open_case_from_booking",
);

const NO_SHOW_OPEN_OWNER_ACTIONS = calendarActionIds(
    "record_follow_up_contacted",
    "record_follow_up_rebooked",
    "manage_follow_up_governance",
    "open_case_from_booking",
);

const DISABLED_ACTIVE_LIFECYCLE_ACTIONS = calendarActionIds(
    "edit_booking",
    "cancel_booking",
);

function uniqueActionIds(actionIds: readonly CalendarBookingActionId[]) {
    return [...new Set(actionIds)] as CalendarBookingActionId[];
}

function hiddenFromEnabledAndDisabled(
    enabled: readonly CalendarBookingActionId[],
    disabled: readonly CalendarBookingActionId[],
): CalendarBookingActionId[] {
    const hidden = ACTIVE_ACTION_IDS.filter((actionId) => !enabled.includes(actionId) && !disabled.includes(actionId));
    return hidden;
}

export const CALENDAR_BOOKING_ACTION_SCENARIO_MATRIX: readonly CalendarBookingActionScenario[] = [
    ...CALENDAR_ACTIVE_BOOKING_STATUSES.map((status) => ({
        id: `manager-${status.toLowerCase()}-with-case`,
        actorClass: "manager" as const,
        booking: { status, no_show_followup_done: false, case_id: "case-1" },
        expectedEnabled: WITH_CASE_ACTIONS,
        expectedDisabled: [],
        expectedHidden: hiddenFromEnabledAndDisabled(WITH_CASE_ACTIONS, []),
    })),
    ...CALENDAR_ACTIVE_BOOKING_STATUSES.map((status) => ({
        id: `owner-${status.toLowerCase()}-with-case`,
        actorClass: "owner_admin" as const,
        booking: { status, no_show_followup_done: false, case_id: "case-1" },
        expectedEnabled: WITH_CASE_ACTIONS,
        expectedDisabled: [],
        expectedHidden: hiddenFromEnabledAndDisabled(WITH_CASE_ACTIONS, []),
    })),
    {
        id: "manager-no-show-open-with-case",
        actorClass: "manager",
        booking: { status: "NO_SHOW", no_show_followup_done: false, case_id: "case-1" },
        expectedEnabled: NO_SHOW_OPEN_MANAGER_ACTIONS,
        expectedDisabled: DISABLED_ACTIVE_LIFECYCLE_ACTIONS,
        expectedHidden: hiddenFromEnabledAndDisabled(NO_SHOW_OPEN_MANAGER_ACTIONS, DISABLED_ACTIVE_LIFECYCLE_ACTIONS),
    },
    {
        id: "owner-no-show-open-with-case",
        actorClass: "owner_admin",
        booking: { status: "NO_SHOW", no_show_followup_done: false, case_id: "case-1" },
        expectedEnabled: NO_SHOW_OPEN_OWNER_ACTIONS,
        expectedDisabled: DISABLED_ACTIVE_LIFECYCLE_ACTIONS,
        expectedHidden: hiddenFromEnabledAndDisabled(NO_SHOW_OPEN_OWNER_ACTIONS, DISABLED_ACTIVE_LIFECYCLE_ACTIONS),
    },
    {
        id: "manager-no-show-closed-with-case",
        actorClass: "manager",
        booking: { status: "NO_SHOW", no_show_followup_done: true, case_id: "case-1" },
        expectedEnabled: calendarActionIds("open_case_from_booking"),
        expectedDisabled: DISABLED_ACTIVE_LIFECYCLE_ACTIONS,
        expectedHidden: hiddenFromEnabledAndDisabled(calendarActionIds("open_case_from_booking"), DISABLED_ACTIVE_LIFECYCLE_ACTIONS),
    },
    {
        id: "owner-no-show-closed-with-case",
        actorClass: "owner_admin",
        booking: { status: "NO_SHOW", no_show_followup_done: true, case_id: "case-1" },
        expectedEnabled: calendarActionIds("open_case_from_booking"),
        expectedDisabled: DISABLED_ACTIVE_LIFECYCLE_ACTIONS,
        expectedHidden: hiddenFromEnabledAndDisabled(calendarActionIds("open_case_from_booking"), DISABLED_ACTIVE_LIFECYCLE_ACTIONS),
    },
    ...(["COMPLETED", "CANCELLED"] as const).flatMap((status) => [
        {
            id: `manager-${status.toLowerCase()}-with-case`,
            actorClass: "manager" as const,
            booking: { status, no_show_followup_done: false, case_id: "case-1" },
            expectedEnabled: calendarActionIds("open_case_from_booking"),
            expectedDisabled: DISABLED_ACTIVE_LIFECYCLE_ACTIONS,
            expectedHidden: hiddenFromEnabledAndDisabled(calendarActionIds("open_case_from_booking"), DISABLED_ACTIVE_LIFECYCLE_ACTIONS),
        },
        {
            id: `owner-${status.toLowerCase()}-with-case`,
            actorClass: "owner_admin" as const,
            booking: { status, no_show_followup_done: false, case_id: "case-1" },
            expectedEnabled: calendarActionIds("open_case_from_booking"),
            expectedDisabled: DISABLED_ACTIVE_LIFECYCLE_ACTIONS,
            expectedHidden: hiddenFromEnabledAndDisabled(calendarActionIds("open_case_from_booking"), DISABLED_ACTIVE_LIFECYCLE_ACTIONS),
        },
    ]),
    {
        id: "consultant-bot-confirmed-with-case",
        actorClass: "consultant_bot",
        booking: { status: "CONFIRMED", no_show_followup_done: false, case_id: "case-1" },
        expectedEnabled: calendarActionIds(),
        expectedDisabled: calendarActionIds(),
        expectedHidden: ACTIVE_ACTION_IDS,
    },
    {
        id: "manager-confirmed-without-case",
        actorClass: "manager",
        booking: { status: "CONFIRMED", no_show_followup_done: false, case_id: null },
        expectedEnabled: uniqueActionIds(
            WITH_CASE_ACTIONS.filter(
                (actionId): actionId is CalendarBookingActionId => actionId !== "open_case_from_booking",
            ),
        ),
        expectedDisabled: [],
        expectedHidden: hiddenFromEnabledAndDisabled(
            uniqueActionIds(
                WITH_CASE_ACTIONS.filter(
                    (actionId): actionId is CalendarBookingActionId => actionId !== "open_case_from_booking",
                ),
            ),
            [],
        ),
    },
] as const;

export function getCalendarActionPermissionsForActor(actorClass: CalendarActorClass): CalendarActionPermissions {
    if (actorClass === "owner_admin") {
        return { canWriteCalendar: true, canManageFollowUpGovernance: true };
    }
    if (actorClass === "manager") {
        return { canWriteCalendar: true, canManageFollowUpGovernance: false };
    }
    return { canWriteCalendar: false, canManageFollowUpGovernance: false };
}

export function getCalendarActorClassForRole(role: string | null | undefined): CalendarActorClass {
    const normalized = String(role || "").trim().toLowerCase();
    if (normalized === "consultant_bot") {
        return "consultant_bot";
    }
    if (normalized === "platform_admin" || normalized === "owner" || normalized === "admin") {
        return "owner_admin";
    }
    return "manager";
}

export function normalizeCalendarBookingStatus(status: string | null | undefined): CalendarBookingStatus {
    const normalized = String(status || "").trim().toUpperCase();
    if (!normalized) {
        return "DRAFT";
    }
    if (normalized === "ACTIVE") {
        return "HOLD";
    }
    return normalized as CalendarBookingStatus;
}

function hasPermission(permissions: CalendarActionPermissions, permission: CalendarPermissionKey) {
    if (permission === "calendar_write") {
        return permissions.canWriteCalendar;
    }
    if (permission === "follow_up_governance") {
        return permissions.canManageFollowUpGovernance;
    }
    return false;
}

function hasRequiredPermissions(
    permissions: CalendarActionPermissions,
    requiredPermissions: readonly CalendarPermissionKey[],
) {
    return requiredPermissions.every((permission) => hasPermission(permissions, permission));
}

function isOpenNoShowFollowUp(booking: CalendarBookingLike, normalizedStatus: CalendarBookingStatus) {
    return normalizedStatus === "NO_SHOW" && !booking.no_show_followup_done;
}

function hasServerBookingActionContract(booking: CalendarBookingLike) {
    return Array.isArray(booking.allowed_actions) || Array.isArray(booking.blocked_actions);
}

function buildServerBackedCalendarBookingActionAvailabilityMap(
    booking: CalendarBookingLike,
): Record<CalendarBookingActionId, CalendarBookingActionAvailability> {
    const normalizedStatus = normalizeCalendarBookingStatus(booking.status);
    const statusLabel = getBookingStatusLabel(normalizedStatus);
    const allowedActions = new Set(booking.allowed_actions ?? []);
    const blockedReasonByAction = new Map(
        (booking.blocked_actions ?? []).map((payload) => [payload.action_id, payload.reason_code]),
    );

    return CALENDAR_BOOKING_ACTION_REGISTRY.reduce((result, definition) => {
        const base: CalendarBookingActionAvailability = {
            id: definition.id,
            label: definition.label,
            surface: definition.surface,
            state: "hidden",
            visible: false,
            visitStatus: definition.visitStatus,
        };
        if (allowedActions.has(definition.id)) {
            result[definition.id] = {
                ...base,
                state: "enabled",
                visible: true,
            };
            return result;
        }
        const blockedReasonCode = blockedReasonByAction.get(definition.id);
        if (!blockedReasonCode) {
            result[definition.id] = base;
            return result;
        }
        const state = blockedReasonCode === "active_status_only" ? definition.inactiveState : "hidden";
        result[definition.id] = {
            ...base,
            state,
            visible: state !== "hidden",
            blockedReasonCode,
            blockedReason:
                state === "disabled" && definition.disabledReason
                    ? definition.disabledReason(statusLabel)
                    : undefined,
        };
        return result;
    }, {} as Record<CalendarBookingActionId, CalendarBookingActionAvailability>);
}

export function buildCalendarBookingActionAvailabilityMap(
    booking: CalendarBookingLike,
    permissions: CalendarActionPermissions,
    actorClass: CalendarActorClass = "manager",
): Record<CalendarBookingActionId, CalendarBookingActionAvailability> {
    if (hasServerBookingActionContract(booking)) {
        return buildServerBackedCalendarBookingActionAvailabilityMap(booking);
    }
    const normalizedStatus = normalizeCalendarBookingStatus(booking.status);
    const statusLabel = getBookingStatusLabel(normalizedStatus);

    return CALENDAR_BOOKING_ACTION_REGISTRY.reduce((result, definition) => {
        const base: CalendarBookingActionAvailability = {
            id: definition.id,
            label: definition.label,
            surface: definition.surface,
            state: "hidden",
            visible: false,
            visitStatus: definition.visitStatus,
        };

        if (!definition.actorClasses.includes(actorClass)) {
            result[definition.id] = base;
            return result;
        }

        if (!hasRequiredPermissions(permissions, definition.requiredPermissions)) {
            result[definition.id] = {
                ...base,
                blockedReasonCode: "permission_required",
            };
            return result;
        }

        if (definition.requiresCaseLink && !booking.case_id) {
            result[definition.id] = {
                ...base,
                blockedReasonCode: "case_link_required",
            };
            return result;
        }

        if (definition.requiresOpenNoShow && !isOpenNoShowFollowUp(booking, normalizedStatus)) {
            result[definition.id] = {
                ...base,
                blockedReasonCode: booking.no_show_followup_done ? "follow_up_already_closed" : "open_no_show_required",
            };
            return result;
        }

        if (definition.allowedStatuses && !definition.allowedStatuses.includes(normalizedStatus)) {
            result[definition.id] = {
                ...base,
                state: definition.inactiveState,
                visible: definition.inactiveState !== "hidden",
                blockedReasonCode: definition.blockedReasonCode,
                blockedReason: definition.disabledReason ? definition.disabledReason(statusLabel) : undefined,
            };
            return result;
        }

        result[definition.id] = {
            ...base,
            state: "enabled",
            visible: true,
        };
        return result;
    }, {} as Record<CalendarBookingActionId, CalendarBookingActionAvailability>);
}

export function getCalendarVisitActionOptions(
    booking: CalendarBookingLike,
    permissions: CalendarActionPermissions,
    actorClass: CalendarActorClass = "manager",
): Array<{ actionId: "mark_completed" | "mark_no_show"; status: "COMPLETED" | "NO_SHOW"; label: string }> {
    const actionMap = buildCalendarBookingActionAvailabilityMap(booking, permissions, actorClass);
    return (["mark_completed", "mark_no_show"] as const)
        .map((actionId) => actionMap[actionId])
        .filter((action): action is CalendarBookingActionAvailability & { visitStatus: "COMPLETED" | "NO_SHOW" } => action.state === "enabled" && Boolean(action.visitStatus))
        .map((action) => ({
            actionId: action.id as "mark_completed" | "mark_no_show",
            status: action.visitStatus,
            label: action.label,
        }));
}

export function getCalendarBookingActionAvailability(
    booking: CalendarBookingLike,
    permissions: CalendarActionPermissions,
    actionId: CalendarBookingActionId,
    actorClass: CalendarActorClass = "manager",
) {
    return buildCalendarBookingActionAvailabilityMap(booking, permissions, actorClass)[actionId];
}
