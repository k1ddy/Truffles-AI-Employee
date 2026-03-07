"use client";

import type { CaseAssigneeOption } from "@/lib/api-client";
import type {
    InboxCaseFilters,
    InboxOwnerScope,
    InboxQueueViewId,
    InboxSortBy,
} from "@/lib/inbox-workspace";

export const DEFAULT_OWNER_SCOPE: InboxOwnerScope = { kind: "all" };

export type OwnerScopeOption = {
    value: string;
    label: string;
};

const VALID_STATUS_VALUES = new Set(["open", "all", "pending", "active", "resolved"]);
const VALID_SORT_VALUES = new Set(["activity", "created_at", "sla"]);

export function getDefaultSortForQueueView(viewId: InboxQueueViewId): InboxSortBy {
    return viewId === "needs_reply" ? "sla" : "activity";
}

export function normalizeOwnerScopeForRole(ownerScope: InboxOwnerScope, privileged: boolean): InboxOwnerScope {
    if (ownerScope.kind === "mine" || ownerScope.kind === "all") {
        return ownerScope;
    }
    if (!privileged) {
        return { ...DEFAULT_OWNER_SCOPE };
    }
    if (ownerScope.kind === "unassigned") {
        return ownerScope;
    }
    if (ownerScope.kind === "agent" && ownerScope.agentId) {
        return ownerScope;
    }
    return { ...DEFAULT_OWNER_SCOPE };
}

export function normalizeStoredStatus(raw: unknown): InboxCaseFilters["status"] {
    if (typeof raw !== "string") {
        return undefined;
    }
    const value = raw.trim().toLowerCase();
    if (!value || value === "open") {
        return undefined;
    }
    return VALID_STATUS_VALUES.has(value) ? value : undefined;
}

export function normalizeStoredSortBy(
    raw: unknown,
    {
        activeViewId,
    }: {
        activeViewId: InboxQueueViewId;
    },
): InboxCaseFilters["sortBy"] {
    if (typeof raw !== "string") {
        return undefined;
    }
    const value = raw.trim().toLowerCase();
    if (!VALID_SORT_VALUES.has(value)) {
        return undefined;
    }
    return value === getDefaultSortForQueueView(activeViewId) ? undefined : (value as InboxSortBy);
}

export function resolveEffectiveStatus(status?: string): string | undefined {
    if (!status || status === "open") {
        return "open";
    }
    if (status === "all") {
        return undefined;
    }
    return status;
}

export function resolveStatusSelectValue(status?: string): string {
    if (!status || status === "open") {
        return "open";
    }
    return status;
}

export function resolveEffectiveSortBy(activeViewId: InboxQueueViewId, sortBy?: InboxSortBy): InboxSortBy {
    return sortBy ?? getDefaultSortForQueueView(activeViewId);
}

export function resolveOwnerScopeLabel(scope: InboxOwnerScope, assignees: CaseAssigneeOption[]): string {
    if (scope.kind === "mine") {
        return "Мои заявки";
    }
    if (scope.kind === "unassigned") {
        return "Без владельца";
    }
    if (scope.kind === "agent") {
        return assignees.find((item) => String(item.agent_id) === scope.agentId)?.agent_name
            ?? scope.agentId
            ?? "Менеджер";
    }
    return "Все заявки";
}

export function buildOwnerScopeOptions({
    privileged,
    assignees,
}: {
    privileged: boolean;
    assignees: CaseAssigneeOption[];
}): OwnerScopeOption[] {
    const options: OwnerScopeOption[] = [
        { value: "__all__", label: "Все заявки" },
        { value: "__mine__", label: "Мои заявки" },
    ];
    if (!privileged) {
        return options;
    }
    options.push({ value: "__unassigned__", label: "Без владельца" });
    assignees.forEach((option) => {
        options.push({
            value: String(option.agent_id),
            label: `${option.agent_name} · ${option.open_case_count ?? 0} в работе`,
        });
    });
    return options;
}

export function ownerScopeToSelectValue(ownerScope: InboxOwnerScope): string {
    return ownerScope.kind === "agent" ? ownerScope.agentId || "__all__" : `__${ownerScope.kind}__`;
}

export function parseOwnerScopeValue(nextValue: string, privileged: boolean): InboxOwnerScope {
    if (!nextValue || nextValue === "__all__") {
        return { ...DEFAULT_OWNER_SCOPE };
    }
    if (nextValue === "__mine__") {
        return { kind: "mine" };
    }
    if (privileged && nextValue === "__unassigned__") {
        return { kind: "unassigned" };
    }
    if (privileged) {
        return { kind: "agent", agentId: nextValue };
    }
    return { ...DEFAULT_OWNER_SCOPE };
}

export function hasAdvancedCaseRefinements(
    filters: InboxCaseFilters,
    {
        branchFilterEnabled,
    }: {
        branchFilterEnabled: boolean;
    },
): boolean {
    return Boolean(
        filters.status
        || (branchFilterEnabled && filters.branchId)
        || filters.dateFrom
        || filters.dateTo
        || filters.hasDeliveryError
        || filters.hasPendingOutbox
        || filters.hasHumanLock
        || filters.sortBy
    );
}

export function hasAnyCaseFiltersApplied({
    activeViewId,
    filters,
    ownerScope,
    branchFilterEnabled,
}: {
    activeViewId: InboxQueueViewId;
    filters: InboxCaseFilters;
    ownerScope: InboxOwnerScope;
    branchFilterEnabled: boolean;
}): boolean {
    return Boolean(
        activeViewId !== "all_open"
        || ownerScope.kind !== "all"
        || filters.query
        || hasAdvancedCaseRefinements(filters, { branchFilterEnabled })
    );
}

export function buildCaseListSearchParams({
    filters,
    ownerScope,
    activeViewId,
    privilegedOwnerFilterVisible,
    activeServerQueueView,
    cursor,
    limit,
}: {
    filters: InboxCaseFilters;
    ownerScope: InboxOwnerScope;
    activeViewId: InboxQueueViewId;
    privilegedOwnerFilterVisible: boolean;
    activeServerQueueView?: "needs_reply" | "waiting_client" | "snoozed" | "delivery";
    cursor?: string;
    limit: number;
}): URLSearchParams {
    const params = new URLSearchParams();
    const effectiveOwnerScope = normalizeOwnerScopeForRole(ownerScope, privilegedOwnerFilterVisible);
    const effectiveStatus = resolveEffectiveStatus(filters.status);
    const effectiveSort = resolveEffectiveSortBy(activeViewId, filters.sortBy);

    if (effectiveStatus) {
        params.append("status", effectiveStatus);
    }
    if (filters.branchId) params.append("branch_id", filters.branchId);
    if (effectiveOwnerScope.kind === "mine") params.append("assigned_to_me", "true");
    if (effectiveOwnerScope.kind === "agent" && effectiveOwnerScope.agentId) params.append("assignee_id", effectiveOwnerScope.agentId);
    if (effectiveOwnerScope.kind === "unassigned") params.append("unassigned", "true");
    if (filters.query) params.append("q", filters.query);
    if (filters.hasDeliveryError) params.append("has_delivery_error", "true");
    if (filters.hasPendingOutbox) params.append("has_pending_outbox", "true");
    if (filters.hasHumanLock) params.append("has_human_lock", "true");
    if (filters.dateFrom) params.append("date_from", filters.dateFrom);
    if (filters.dateTo) params.append("date_to", filters.dateTo);
    if (activeServerQueueView) params.append("queue_view", activeServerQueueView);
    if (effectiveSort === "activity") params.append("sort_by", "last_activity");
    if (effectiveSort === "created_at") params.append("sort_by", "created_at");
    if (effectiveSort === "sla") params.append("sort_by", "sla");
    if (cursor) params.append("cursor", cursor);
    params.append("limit", String(limit));

    return params;
}
