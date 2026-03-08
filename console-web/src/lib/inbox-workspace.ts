"use client";

import { readBrowserStorage, writeBrowserStorage } from "@/lib/browser-storage";
import type { BookingQueueLane, BookingQueueMode, BookingStatusFilter } from "@/lib/calendar-bookings";

const WORKSPACE_TTL_MS = 24 * 60 * 60 * 1000;
const CASE_LIST_KEY_PREFIX = "console:inbox:case-list:v5:";
const SELECTED_CASE_KEY_PREFIX = "console:inbox:selected-case:v1:";
const SIDE_PANEL_KEY_PREFIX = "console:inbox:side-panel:v1:";
const CALENDAR_PREFS_KEY_PREFIX = "console:calendar:prefs:v1:";

export type InboxSortBy = "created_at" | "sla" | "activity" | "resolved_at";
export type InboxSidePanelMode = "details" | "bookings";
export type InboxCaseModeScope = "open" | "resolved" | "all";
export const INBOX_QUEUE_VIEW_IDS = [
    "all_open",
    "needs_reply",
    "waiting_client",
    "snoozed",
    "delivery",
] as const;
export type InboxQueueViewId = (typeof INBOX_QUEUE_VIEW_IDS)[number];
export type InboxOwnerScopeKind = "all" | "mine" | "unassigned" | "agent";
export type InboxCaseVisibleField = "branch" | "owner" | "channel" | "activity" | "priority";

export interface InboxOwnerScope {
    kind: InboxOwnerScopeKind;
    agentId?: string;
}

export interface InboxCaseFilters {
    status?: string;
    branchId?: string;
    query?: string;
    hasDeliveryError: boolean;
    hasPendingOutbox: boolean;
    hasHumanLock: boolean;
    dateFrom?: string;
    dateTo?: string;
    sortBy?: InboxSortBy;
}

export interface InboxCaseVisibleFields {
    branch: boolean;
    owner: boolean;
    channel: boolean;
    activity: boolean;
    priority: boolean;
}

export interface InboxCaseListPrefs {
    filters: InboxCaseFilters;
    ownerScope?: InboxOwnerScope;
    modeScope?: InboxCaseModeScope;
    searchValue: string;
    showAdvancedFilters: boolean;
    filtersCollapsed: boolean;
    autoRefreshEnabled: boolean;
    activeViewId?: InboxQueueViewId;
    visibleFields?: InboxCaseVisibleFields;
}

export function normalizeInboxQueueViewId(raw: unknown): InboxQueueViewId {
    if (raw === "paused") {
        return "waiting_client";
    }
    if (raw === "mine" || raw === "unassigned") {
        return "all_open";
    }
    if (typeof raw === "string" && (INBOX_QUEUE_VIEW_IDS as readonly string[]).includes(raw)) {
        return raw as InboxQueueViewId;
    }
    return "all_open";
}

export function normalizeInboxCaseModeScope(raw: unknown): InboxCaseModeScope {
    if (raw === "resolved" || raw === "all" || raw === "open") {
        return raw;
    }
    return "open";
}

export function normalizeInboxOwnerScope(raw: unknown): InboxOwnerScope {
    if (!raw || typeof raw !== "object") {
        return { kind: "all" };
    }
    const kind = (raw as { kind?: unknown }).kind;
    const agentId = (raw as { agentId?: unknown }).agentId;
    if (kind === "mine" || kind === "unassigned" || kind === "all") {
        return { kind };
    }
    if (kind === "agent" && typeof agentId === "string" && agentId.trim()) {
        return { kind: "agent", agentId };
    }
    return { kind: "all" };
}

export interface CalendarWorkspacePrefs {
    selectedDate: string;
    queueMode?: BookingQueueMode;
    queueLane: BookingQueueLane;
    queueStatusFilter: BookingStatusFilter;
    queueSearch?: string;
    followUpOwnerId?: string;
    followUpOverdueOnly?: boolean;
}

type StoredValue<T> = {
    savedAt: number;
    value: T;
};

function isFresh(savedAt: number): boolean {
    return Number.isFinite(savedAt) && Date.now() - savedAt <= WORKSPACE_TTL_MS;
}

function readStoredValue<T>(key: string): T | null {
    const raw = readBrowserStorage(key);
    if (!raw) {
        return null;
    }
    try {
        const parsed = JSON.parse(raw) as StoredValue<T>;
        if (!parsed || typeof parsed !== "object" || typeof parsed.savedAt !== "number" || !("value" in parsed)) {
            writeBrowserStorage(key, null);
            return null;
        }
        if (!isFresh(parsed.savedAt)) {
            writeBrowserStorage(key, null);
            return null;
        }
        return parsed.value;
    } catch {
        writeBrowserStorage(key, null);
        return null;
    }
}

function writeStoredValue<T>(key: string, value: T | null) {
    if (value == null) {
        writeBrowserStorage(key, null);
        return;
    }
    writeBrowserStorage(
        key,
        JSON.stringify({
            savedAt: Date.now(),
            value,
        } satisfies StoredValue<T>)
    );
}

function buildScopedKey(prefix: string, scope: string): string {
    return `${prefix}${scope}`;
}

export function buildInboxWorkspaceScope({
    role,
    agentId,
    clientId,
    branchId,
}: {
    role?: string | null;
    agentId?: string | null;
    clientId?: string | null;
    branchId?: string | null;
}): string {
    const safeRole = (role || "unknown").trim() || "unknown";
    const safeAgent = (agentId || "unknown").trim() || "unknown";
    const safeClient = (clientId || "unknown").trim() || "unknown";
    const safeBranch = (branchId || "all").trim() || "all";
    return `${safeRole}:${safeAgent}:${safeClient}:${safeBranch}`;
}

export function readInboxCaseListPrefs(scope: string): InboxCaseListPrefs | null {
    return readStoredValue<InboxCaseListPrefs>(buildScopedKey(CASE_LIST_KEY_PREFIX, scope));
}

export function writeInboxCaseListPrefs(scope: string, prefs: InboxCaseListPrefs | null) {
    writeStoredValue(buildScopedKey(CASE_LIST_KEY_PREFIX, scope), prefs);
}

export function readInboxSelectedCase(scope: string): string | null {
    return readStoredValue<string>(buildScopedKey(SELECTED_CASE_KEY_PREFIX, scope));
}

export function writeInboxSelectedCase(scope: string, caseId: string | null) {
    writeStoredValue(buildScopedKey(SELECTED_CASE_KEY_PREFIX, scope), caseId);
}

export function readInboxSidePanelMode(scope: string): InboxSidePanelMode | null {
    return readStoredValue<InboxSidePanelMode>(buildScopedKey(SIDE_PANEL_KEY_PREFIX, scope));
}

export function writeInboxSidePanelMode(scope: string, mode: InboxSidePanelMode | null) {
    writeStoredValue(buildScopedKey(SIDE_PANEL_KEY_PREFIX, scope), mode);
}

export function buildCalendarWorkspaceScope({
    scope,
    caseId,
    conversationId,
}: {
    scope: string;
    caseId?: string | null;
    conversationId?: string | null;
}): string {
    const safeCaseId = (caseId || "all").trim() || "all";
    const safeConversationId = (conversationId || "all").trim() || "all";
    return `${scope}:${safeCaseId}:${safeConversationId}`;
}

export function readCalendarWorkspacePrefs(scope: string): CalendarWorkspacePrefs | null {
    return readStoredValue<CalendarWorkspacePrefs>(buildScopedKey(CALENDAR_PREFS_KEY_PREFIX, scope));
}

export function writeCalendarWorkspacePrefs(scope: string, prefs: CalendarWorkspacePrefs | null) {
    writeStoredValue(buildScopedKey(CALENDAR_PREFS_KEY_PREFIX, scope), prefs);
}
