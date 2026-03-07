"use client";

import {
    buildCaseListSearchParams,
    normalizeOwnerScopeForRole,
    normalizeStoredSortBy,
} from "@/lib/inbox-case-filters";
import type { BookingQueueLane, BookingStatusFilter } from "@/lib/calendar-bookings";
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

type QueueStateSurface = "cases" | "calendar";

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

export interface CasesQueueStateSnapshot {
    filters: InboxCaseFilters;
    ownerScope: InboxOwnerScope;
    modeScope: InboxCaseModeScope;
    activeViewId: InboxQueueViewId;
    searchValue: string;
}

export interface CalendarQueueStateSnapshot {
    selectedDate: string;
    queueLane: BookingQueueLane;
    queueStatusFilter: BookingStatusFilter;
    queueSearch: string;
}

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

function normalizeCalendarStatusFilter(value: unknown): BookingStatusFilter {
    return value === "scheduled"
        || value === "completed"
        || value === "no_show"
        || value === "cancelled"
        ? value
        : "all";
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

export function readCalendarQueueStateFromServer(
    record: QueueStateRecord | null | undefined,
    {
        defaultSelectedDate,
        defaultQueueLane,
    }: {
        defaultSelectedDate: string;
        defaultQueueLane: BookingQueueLane;
    },
): CalendarQueueStateSnapshot | null {
    if (!record?.found || !record.query_state || typeof record.query_state !== "object") {
        return null;
    }
    const queryState = record.query_state as Record<string, unknown>;
    return {
        selectedDate: trimToUndefined(queryState.selected_date as string | undefined) ?? defaultSelectedDate,
        queueLane: normalizeCalendarLane(queryState.queue_lane, defaultQueueLane),
        queueStatusFilter: normalizeCalendarStatusFilter(queryState.status_filter),
        queueSearch: trimToUndefined(queryState.query as string | undefined) ?? "",
    };
}

export function readCalendarQueueStateFromUrl(
    searchParams: SearchParamsLike,
    {
        defaultSelectedDate,
        defaultQueueLane,
    }: {
        defaultSelectedDate: string;
        defaultQueueLane: BookingQueueLane;
    },
): CalendarQueueStateSnapshot | null {
    const hasRelevantParams = ["date", "date_from", "date_to", "lane", "status", "q"].some(
        (key) => searchParams.get(key) != null,
    );
    if (!hasRelevantParams) {
        return null;
    }
    const explicitDate = trimToUndefined(searchParams.get("date"));
    const dateFrom = trimToUndefined(searchParams.get("date_from"));
    const dateTo = trimToUndefined(searchParams.get("date_to"));
    const selectedDate = explicitDate ?? (dateFrom && dateFrom === dateTo ? dateFrom : undefined) ?? defaultSelectedDate;
    return {
        selectedDate,
        queueLane: normalizeCalendarLane(searchParams.get("lane"), defaultQueueLane),
        queueStatusFilter: normalizeCalendarStatusFilter(searchParams.get("status")),
        queueSearch: trimToUndefined(searchParams.get("q")) ?? "",
    };
}

export function buildCalendarQueueStatePayload(snapshot: CalendarQueueStateSnapshot): Record<string, unknown> {
    return {
        selected_date: snapshot.selectedDate || null,
        queue_lane: snapshot.queueLane,
        status_filter: snapshot.queueStatusFilter,
        query: snapshot.queueSearch.trim() || null,
    };
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
    if (snapshot.queueLane !== defaultQueueLane) {
        params.set("lane", snapshot.queueLane);
    }
    if (snapshot.queueStatusFilter !== "all") {
        params.set("status", snapshot.queueStatusFilter);
    }
    const query = snapshot.queueSearch.trim();
    if (query) {
        params.set("q", query);
    }
    return params;
}
