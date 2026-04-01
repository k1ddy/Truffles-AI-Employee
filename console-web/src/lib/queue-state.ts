"use client";

import {
    buildCaseListSearchParams,
    normalizeOwnerScopeForRole,
    normalizeStoredSortBy,
} from "@/lib/inbox-case-filters";
import type { BookingQueueLane, BookingQueueMode, BookingStatusFilter } from "@/lib/calendar-bookings";
import {
    normalizeInboxCaseModeScope,
    normalizeInboxOwnerScope,
    normalizeInboxQueueViewId,
    type InboxCaseFilters,
    type InboxCaseModeScope,
    type InboxOwnerScope,
    type InboxQueueViewId,
    type InboxSortBy,
} from "@/lib/inbox-workspace";

type SearchParamsLike = {
    get(name: string): string | null;
};

type SearchParamsInput = string | URLSearchParams | SearchParamsLike;

export type QueueStateSurface = "cases" | "calendar";

type QueueStateRecord = {
    found?: boolean;
    surface?: QueueStateSurface;
    selected_branch_id?: string | null;
    case_id?: string | null;
    conversation_id?: string | null;
    version?: number;
    query_state?: Record<string, unknown> | null;
    updated_at?: string | null;
};

export interface QueueStateSavedViewLike {
    id?: string;
    name?: string;
    query_state?: Record<string, unknown> | null;
    is_default?: boolean;
    scope?: "personal" | "team";
    is_applicable?: boolean;
    target_branch_id?: string | null;
    target_role?: string | null;
}

export interface CasesQueueStateSnapshot {
    filters: InboxCaseFilters;
    ownerScope: InboxOwnerScope;
    modeScope: InboxCaseModeScope;
    activeViewId: InboxQueueViewId;
    searchValue: string;
}

export interface CalendarQueueStateSnapshot {
    selectedDate: string;
    queueMode: BookingQueueMode;
    queueLane: BookingQueueLane;
    queueStatusFilter: BookingStatusFilter;
    queueSearch: string;
    followUpOwnerId: string;
    followUpOverdueOnly: boolean;
}

const CASE_QUEUE_URL_PARAM_KEYS = [
    "view_id",
    "status",
    "queue_view",
    "assigned_to_me",
    "assignee_id",
    "unassigned",
    "branch_id",
    "q",
    "has_delivery_error",
    "has_pending_outbox",
    "has_human_lock",
    "date_from",
    "date_to",
    "resolved_from",
    "resolved_to",
    "sort_by",
] as const;

const CALENDAR_QUEUE_URL_PARAM_KEYS = [
    "view_id",
    "date",
    "date_from",
    "date_to",
    "mode",
    "lane",
    "status",
    "q",
    "follow_up_owner_id",
    "follow_up_overdue",
] as const;

function trimToUndefined(value: string | null | undefined): string | undefined {
    if (typeof value !== "string") {
        return undefined;
    }
    const trimmed = value.trim();
    return trimmed || undefined;
}

function parseBooleanParam(value: string | null | undefined): boolean {
    return value === "true" || value === "1";
}

function normalizeSortByFromUrl(value: string | undefined): InboxSortBy | undefined {
    if (!value) {
        return undefined;
    }
    if (value === "activity" || value === "last_activity") {
        return "activity";
    }
    if (value === "created_at" || value === "resolved_at" || value === "sla") {
        return value;
    }
    return undefined;
}

function resolveServerQueueView(viewId: InboxQueueViewId): "needs_reply" | "waiting_client" | "snoozed" | "delivery" | undefined {
    if (
        viewId === "needs_reply"
        || viewId === "waiting_client"
        || viewId === "snoozed"
        || viewId === "delivery"
    ) {
        return viewId;
    }
    return undefined;
}

function normalizeCalendarLane(value: unknown, fallback: BookingQueueLane): BookingQueueLane {
    if (value === "all" || value === "attention") {
        return value;
    }
    return fallback;
}

function normalizeCalendarQueueMode(value: unknown): BookingQueueMode {
    return value === "history" ? "history" : "ops";
}

function normalizeCalendarStatusFilter(value: unknown): BookingStatusFilter {
    return value === "scheduled"
        || value === "completed"
        || value === "no_show"
        || value === "cancelled"
        ? value
        : "all";
}

function toMutableSearchParams(searchParams: SearchParamsInput): URLSearchParams {
    if (typeof searchParams === "string") {
        return new URLSearchParams(searchParams.startsWith("?") ? searchParams.slice(1) : searchParams);
    }
    if (searchParams instanceof URLSearchParams) {
        return new URLSearchParams(searchParams.toString());
    }
    const params = new URLSearchParams();
    for (const key of [...CASE_QUEUE_URL_PARAM_KEYS, ...CALENDAR_QUEUE_URL_PARAM_KEYS]) {
        const value = searchParams.get(key);
        if (value != null) {
            params.set(key, value);
        }
    }
    return params;
}

function stripQueueUrlParams(params: URLSearchParams, surface: QueueStateSurface): URLSearchParams {
    const next = new URLSearchParams(params.toString());
    const keys = surface === "cases" ? CASE_QUEUE_URL_PARAM_KEYS : CALENDAR_QUEUE_URL_PARAM_KEYS;
    for (const key of keys) {
        next.delete(key);
    }
    return next;
}

function buildHref(pathname: string, params: URLSearchParams): string {
    const queryString = params.toString();
    return queryString ? `${pathname}?${queryString}` : pathname;
}

export function readQueueStateViewIdFromUrl(searchParams: SearchParamsLike): string | null {
    return trimToUndefined(searchParams.get("view_id")) ?? null;
}

export function readCasesQueueStateFromServer(
    record: QueueStateRecord | null | undefined,
    {
        branchFilterEnabled,
        privilegedOwnerFilterVisible,
    }: {
        branchFilterEnabled: boolean;
        privilegedOwnerFilterVisible: boolean;
    },
): CasesQueueStateSnapshot | null {
    if (!record?.found || !record.query_state || typeof record.query_state !== "object") {
        return null;
    }
    const queryState = record.query_state as Record<string, unknown>;
    const refinements = typeof queryState.refinements === "object" && queryState.refinements
        ? queryState.refinements as Record<string, unknown>
        : {};
    const rawOwnerScope = typeof queryState.owner_scope === "object" && queryState.owner_scope
        ? queryState.owner_scope as Record<string, unknown>
        : {};
    const activeViewId = normalizeInboxQueueViewId(queryState.base_view);
    const modeScope = normalizeInboxCaseModeScope(queryState.mode_scope);
    const ownerScope = normalizeOwnerScopeForRole(
        normalizeInboxOwnerScope({
            kind: rawOwnerScope.kind,
            agentId: rawOwnerScope.agent_id,
        }),
        privilegedOwnerFilterVisible,
    );
    const query = trimToUndefined(refinements.query as string | undefined);
    return {
        filters: {
            status: undefined,
            branchId: branchFilterEnabled ? trimToUndefined(refinements.branch_id as string | undefined) : undefined,
            query,
            hasDeliveryError: modeScope === "open" ? Boolean(refinements.has_delivery_error) : false,
            hasPendingOutbox: modeScope === "open" ? Boolean(refinements.has_pending_outbox) : false,
            hasHumanLock: modeScope === "open" ? Boolean(refinements.has_human_lock) : false,
            dateFrom: trimToUndefined(refinements.date_from as string | undefined),
            dateTo: trimToUndefined(refinements.date_to as string | undefined),
            sortBy: normalizeStoredSortBy(normalizeSortByFromUrl(refinements.sort_by as string | undefined), {
                activeViewId,
                modeScope,
            }),
        },
        ownerScope,
        modeScope,
        activeViewId,
        searchValue: query ?? "",
    };
}

export function readCasesQueueStateFromSavedView(
    savedView: QueueStateSavedViewLike | null | undefined,
    options: {
        branchFilterEnabled: boolean;
        privilegedOwnerFilterVisible: boolean;
    },
): CasesQueueStateSnapshot | null {
    if (!savedView?.query_state || typeof savedView.query_state !== "object") {
        return null;
    }
    return readCasesQueueStateFromServer(
        {
            found: true,
            surface: "cases",
            query_state: savedView.query_state,
        },
        options,
    );
}

export function readCasesQueueStateFromUrl(
    searchParams: SearchParamsLike,
    {
        branchFilterEnabled,
        privilegedOwnerFilterVisible,
    }: {
        branchFilterEnabled: boolean;
        privilegedOwnerFilterVisible: boolean;
    },
): CasesQueueStateSnapshot | null {
    const hasRelevantParams = [
        "status",
        "queue_view",
        "assigned_to_me",
        "assignee_id",
        "unassigned",
        "branch_id",
        "q",
        "has_delivery_error",
        "has_pending_outbox",
        "has_human_lock",
        "date_from",
        "date_to",
        "resolved_from",
        "resolved_to",
        "sort_by",
    ].some((key) => searchParams.get(key) != null);
    if (!hasRelevantParams) {
        return null;
    }

    const rawStatus = trimToUndefined(searchParams.get("status"));
    const modeScope = normalizeInboxCaseModeScope(rawStatus);
    const activeViewId = normalizeInboxQueueViewId(
        modeScope === "open" ? searchParams.get("queue_view") : "all_open",
    );
    const rawOwnerScope = parseBooleanParam(searchParams.get("assigned_to_me"))
        ? { kind: "mine" }
        : parseBooleanParam(searchParams.get("unassigned"))
            ? { kind: "unassigned" }
            : trimToUndefined(searchParams.get("assignee_id"))
                ? { kind: "agent", agentId: trimToUndefined(searchParams.get("assignee_id")) }
                : { kind: "all" };
    const ownerScope = normalizeOwnerScopeForRole(
        normalizeInboxOwnerScope(rawOwnerScope),
        privilegedOwnerFilterVisible,
    );
    const query = trimToUndefined(searchParams.get("q"));
    const rawSortBy = normalizeSortByFromUrl(trimToUndefined(searchParams.get("sort_by")));
    return {
        filters: {
            status: undefined,
            branchId: branchFilterEnabled ? trimToUndefined(searchParams.get("branch_id")) : undefined,
            query,
            hasDeliveryError: modeScope === "open" ? parseBooleanParam(searchParams.get("has_delivery_error")) : false,
            hasPendingOutbox: modeScope === "open" ? parseBooleanParam(searchParams.get("has_pending_outbox")) : false,
            hasHumanLock: modeScope === "open" ? parseBooleanParam(searchParams.get("has_human_lock")) : false,
            dateFrom: trimToUndefined(
                modeScope === "resolved" ? searchParams.get("resolved_from") : searchParams.get("date_from"),
            ),
            dateTo: trimToUndefined(
                modeScope === "resolved" ? searchParams.get("resolved_to") : searchParams.get("date_to"),
            ),
            sortBy: normalizeStoredSortBy(rawSortBy, { activeViewId, modeScope }),
        },
        ownerScope,
        modeScope,
        activeViewId,
        searchValue: query ?? "",
    };
}

export function buildCasesQueueStatePayload(
    snapshot: CasesQueueStateSnapshot,
    {
        branchFilterEnabled,
    }: {
        branchFilterEnabled: boolean;
    },
): Record<string, unknown> {
    return {
        mode_scope: snapshot.modeScope,
        base_view: snapshot.activeViewId,
        owner_scope: {
            kind: snapshot.ownerScope.kind,
            agent_id: snapshot.ownerScope.kind === "agent" ? snapshot.ownerScope.agentId ?? null : null,
        },
        refinements: {
            branch_id: branchFilterEnabled ? snapshot.filters.branchId ?? null : null,
            query: snapshot.filters.query ?? null,
            has_delivery_error: Boolean(snapshot.filters.hasDeliveryError),
            has_pending_outbox: Boolean(snapshot.filters.hasPendingOutbox),
            has_human_lock: Boolean(snapshot.filters.hasHumanLock),
            date_from: snapshot.filters.dateFrom ?? null,
            date_to: snapshot.filters.dateTo ?? null,
            sort_by: snapshot.filters.sortBy ?? null,
        },
    };
}

export function getCasesQueueStateFingerprint(
    snapshot: CasesQueueStateSnapshot,
    options: {
        branchFilterEnabled: boolean;
    },
): string {
    return JSON.stringify(buildCasesQueueStatePayload(snapshot, options));
}

export function getSavedViewFingerprint(
    savedView: QueueStateSavedViewLike | null | undefined,
): string {
    if (!savedView?.query_state || typeof savedView.query_state !== "object") {
        return JSON.stringify({});
    }
    return JSON.stringify(savedView.query_state);
}

export function isTeamSavedView(savedView: QueueStateSavedViewLike | null | undefined): boolean {
    return savedView?.scope === "team";
}

export function isApplicableTeamSavedView(savedView: QueueStateSavedViewLike | null | undefined): boolean {
    return isTeamSavedView(savedView) && savedView?.is_applicable !== false;
}

export function findManagedDefaultSavedView<T extends QueueStateSavedViewLike>(
    savedViews: T[],
): T | null {
    return savedViews.find((view) => isApplicableTeamSavedView(view) && view.is_default) ?? null;
}

export function findPersonalDefaultSavedView<T extends QueueStateSavedViewLike>(
    savedViews: T[],
): T | null {
    return savedViews.find((view) => !isTeamSavedView(view) && view.is_default) ?? null;
}

export function findPreferredDefaultSavedView<T extends QueueStateSavedViewLike>(
    savedViews: T[],
): T | null {
    return findManagedDefaultSavedView(savedViews) ?? findPersonalDefaultSavedView(savedViews);
}

function getSavedViewMatchPriority(savedView: QueueStateSavedViewLike): number {
    if (!isTeamSavedView(savedView)) {
        return 2;
    }
    return savedView.is_applicable === false ? 0 : 1;
}

export function findSavedViewByFingerprint<T extends QueueStateSavedViewLike>(
    savedViews: T[],
    fingerprint: string,
    {
        includeNonApplicableTeam = true,
    }: {
        includeNonApplicableTeam?: boolean;
    } = {},
): T | null {
    let bestMatch: T | null = null;
    let bestPriority = -1;
    for (const view of savedViews) {
        if (getSavedViewFingerprint(view) !== fingerprint) {
            continue;
        }
        const priority = getSavedViewMatchPriority(view);
        if (!includeNonApplicableTeam && priority === 0) {
            continue;
        }
        if (priority > bestPriority) {
            bestMatch = view;
            bestPriority = priority;
        }
    }
    return bestMatch;
}

export function buildCasesQueueUrlParams(
    snapshot: CasesQueueStateSnapshot,
    {
        branchFilterEnabled,
        privilegedOwnerFilterVisible,
    }: {
        branchFilterEnabled: boolean;
        privilegedOwnerFilterVisible: boolean;
    },
): URLSearchParams {
    const params = buildCaseListSearchParams({
        filters: snapshot.filters,
        ownerScope: snapshot.ownerScope,
        modeScope: snapshot.modeScope,
        activeViewId: snapshot.activeViewId,
        privilegedOwnerFilterVisible,
        activeServerQueueView: snapshot.modeScope === "open" ? resolveServerQueueView(snapshot.activeViewId) : undefined,
        limit: 20,
    });
    params.delete("limit");
    params.delete("cursor");
    if (!branchFilterEnabled) {
        params.delete("branch_id");
    }
    return params;
}

export function buildCasesQueueHref(
    snapshot: CasesQueueStateSnapshot,
    {
        pathname,
        currentSearch,
        branchFilterEnabled,
        privilegedOwnerFilterVisible,
        viewId,
    }: {
        pathname: string;
        currentSearch: SearchParamsInput;
        branchFilterEnabled: boolean;
        privilegedOwnerFilterVisible: boolean;
        viewId?: string | null;
    },
): string {
    const params = stripQueueUrlParams(toMutableSearchParams(currentSearch), "cases");
    if (viewId) {
        params.set("view_id", viewId);
    }
    const queueParams = buildCasesQueueUrlParams(snapshot, {
        branchFilterEnabled,
        privilegedOwnerFilterVisible,
    });
    if (Array.from(queueParams.keys()).length === 0) {
        queueParams.set("status", snapshot.modeScope);
    }
    queueParams.forEach((value, key) => {
        params.set(key, value);
    });
    return buildHref(pathname, params);
}

export function readCalendarQueueStateFromServer(
    record: QueueStateRecord | null | undefined,
    {
        defaultSelectedDate,
        defaultQueueMode,
        defaultQueueLane,
    }: {
        defaultSelectedDate: string;
        defaultQueueMode: BookingQueueMode;
        defaultQueueLane: BookingQueueLane;
    },
): CalendarQueueStateSnapshot | null {
    if (!record?.found || !record.query_state || typeof record.query_state !== "object") {
        return null;
    }
    const queryState = record.query_state as Record<string, unknown>;
    const queueMode = normalizeCalendarQueueMode(queryState.queue_mode ?? defaultQueueMode);
    return {
        selectedDate: trimToUndefined(queryState.selected_date as string | undefined) ?? defaultSelectedDate,
        queueMode,
        queueLane: queueMode === "history"
            ? "all"
            : normalizeCalendarLane(queryState.queue_lane, defaultQueueLane),
        queueStatusFilter: normalizeCalendarStatusFilter(queryState.status_filter),
        queueSearch: trimToUndefined(queryState.query as string | undefined) ?? "",
        followUpOwnerId: trimToUndefined(queryState.follow_up_owner_id as string | undefined) ?? "",
        followUpOverdueOnly: Boolean(queryState.follow_up_overdue_only),
    };
}

export function readCalendarQueueStateFromSavedView(
    savedView: QueueStateSavedViewLike | null | undefined,
    options: {
        defaultSelectedDate: string;
        defaultQueueMode: BookingQueueMode;
        defaultQueueLane: BookingQueueLane;
    },
): CalendarQueueStateSnapshot | null {
    if (!savedView?.query_state || typeof savedView.query_state !== "object") {
        return null;
    }
    return readCalendarQueueStateFromServer(
        {
            found: true,
            surface: "calendar",
            query_state: savedView.query_state,
        },
        options,
    );
}

export function readCalendarQueueStateFromUrl(
    searchParams: SearchParamsLike,
    {
        defaultSelectedDate,
        defaultQueueMode,
        defaultQueueLane,
    }: {
        defaultSelectedDate: string;
        defaultQueueMode: BookingQueueMode;
        defaultQueueLane: BookingQueueLane;
    },
): CalendarQueueStateSnapshot | null {
    const hasRelevantParams = ["date", "date_from", "date_to", "mode", "lane", "status", "q", "follow_up_owner_id", "follow_up_overdue"].some(
        (key) => searchParams.get(key) != null,
    );
    if (!hasRelevantParams) {
        return null;
    }
    const explicitDate = trimToUndefined(searchParams.get("date"));
    const dateFrom = trimToUndefined(searchParams.get("date_from"));
    const dateTo = trimToUndefined(searchParams.get("date_to"));
    const selectedDate = explicitDate ?? (dateFrom && dateFrom === dateTo ? dateFrom : undefined) ?? defaultSelectedDate;
    const queueMode = normalizeCalendarQueueMode(searchParams.get("mode") ?? defaultQueueMode);
    return {
        selectedDate,
        queueMode,
        queueLane: queueMode === "history"
            ? "all"
            : normalizeCalendarLane(searchParams.get("lane"), defaultQueueLane),
        queueStatusFilter: normalizeCalendarStatusFilter(searchParams.get("status")),
        queueSearch: trimToUndefined(searchParams.get("q")) ?? "",
        followUpOwnerId: trimToUndefined(searchParams.get("follow_up_owner_id")) ?? "",
        followUpOverdueOnly: parseBooleanParam(searchParams.get("follow_up_overdue")),
    };
}

export function buildCalendarQueueStatePayload(snapshot: CalendarQueueStateSnapshot): Record<string, unknown> {
    return {
        selected_date: snapshot.selectedDate || null,
        queue_mode: snapshot.queueMode,
        queue_lane: snapshot.queueMode === "history" ? "all" : snapshot.queueLane,
        status_filter: snapshot.queueStatusFilter,
        query: snapshot.queueSearch.trim() || null,
        follow_up_owner_id: snapshot.followUpOwnerId || null,
        follow_up_overdue_only: snapshot.followUpOverdueOnly,
    };
}

export function getCalendarQueueStateFingerprint(snapshot: CalendarQueueStateSnapshot): string {
    return JSON.stringify(buildCalendarQueueStatePayload(snapshot));
}

export function buildCalendarQueueUrlParams(
    snapshot: CalendarQueueStateSnapshot,
    {
        defaultSelectedDate,
        defaultQueueLane,
    }: {
        defaultSelectedDate: string;
        defaultQueueLane: BookingQueueLane;
    },
): URLSearchParams {
    const params = new URLSearchParams();
    if (snapshot.selectedDate && snapshot.selectedDate !== defaultSelectedDate) {
        params.set("date", snapshot.selectedDate);
    }
    if (snapshot.queueMode !== "ops") {
        params.set("mode", snapshot.queueMode);
    }
    const effectiveQueueLane = snapshot.queueMode === "history" ? "all" : snapshot.queueLane;
    if (effectiveQueueLane !== defaultQueueLane) {
        params.set("lane", effectiveQueueLane);
    }
    if (snapshot.queueStatusFilter !== "all") {
        params.set("status", snapshot.queueStatusFilter);
    }
    const query = snapshot.queueSearch.trim();
    if (query) {
        params.set("q", query);
    }
    if (snapshot.followUpOwnerId) {
        params.set("follow_up_owner_id", snapshot.followUpOwnerId);
    }
    if (snapshot.followUpOverdueOnly) {
        params.set("follow_up_overdue", "1");
    }
    return params;
}

export function buildCalendarQueueHref(
    snapshot: CalendarQueueStateSnapshot,
    {
        pathname,
        currentSearch,
        defaultSelectedDate,
        defaultQueueLane,
        viewId,
    }: {
        pathname: string;
        currentSearch: SearchParamsInput;
        defaultSelectedDate: string;
        defaultQueueLane: BookingQueueLane;
        viewId?: string | null;
    },
): string {
    const params = stripQueueUrlParams(toMutableSearchParams(currentSearch), "calendar");
    if (viewId) {
        params.set("view_id", viewId);
    }
    const queueParams = buildCalendarQueueUrlParams(snapshot, {
        defaultSelectedDate,
        defaultQueueLane,
    });
    if (Array.from(queueParams.keys()).length === 0) {
        queueParams.set("lane", snapshot.queueLane);
    }
    queueParams.forEach((value, key) => {
        params.set(key, value);
    });
    return buildHref(pathname, params);
}
