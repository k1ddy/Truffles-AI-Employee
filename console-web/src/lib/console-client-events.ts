import { readConsoleContextScopeFromStorage } from "@/lib/console-context-storage";

export type ConsoleClientEventType =
    | "selection_gate_shown"
    | "selection_gate_confirmed"
    | "auth_session_expired_signout"
    | "scope_cleared_explicit_logout";

export type ConsoleClientEventSurface = "console_shell" | "login_button";
export type ConsoleSelectionGateKind = "company" | "client" | "branch" | "none";

export interface ConsoleClientScopePresence {
    company_id_present: boolean;
    client_id_present: boolean;
    branch_id_present: boolean;
}

export interface ConsoleClientEventPayload {
    event_type: ConsoleClientEventType;
    surface: ConsoleClientEventSurface;
    gate_kind?: ConsoleSelectionGateKind;
    reason_code?: string | null;
    session_error?: string | null;
    api_error_code?: string | null;
    company_selection_required?: boolean;
    selection_required?: boolean;
    branch_selection_required?: boolean;
    path?: string;
    scope_presence?: ConsoleClientScopePresence;
}

interface ConsoleClientEventEnvelope extends ConsoleClientEventPayload {
    event_id: string;
    emitted_at: string;
    gate_kind: ConsoleSelectionGateKind;
    path: string;
    scope_presence: ConsoleClientScopePresence;
}

const CONSOLE_CLIENT_EVENTS_ENDPOINT = "/api/console-client-events";

function normalizeOptionalString(value: string | null | undefined, maxLength: number): string | null {
    if (!value) {
        return null;
    }
    const normalized = value.trim();
    if (!normalized) {
        return null;
    }
    return normalized.slice(0, maxLength);
}

export function normalizeConsoleClientReasonCode(value: string | null | undefined): string | null {
    if (!value) {
        return null;
    }
    const normalized = value
        .trim()
        .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
    if (!normalized) {
        return null;
    }
    return normalized.slice(0, 80);
}

export function readConsoleScopePresence(): ConsoleClientScopePresence {
    const storedScope = readConsoleContextScopeFromStorage();
    return {
        company_id_present: Boolean(storedScope.companyId),
        client_id_present: Boolean(storedScope.clientId),
        branch_id_present: Boolean(storedScope.branchId),
    };
}

function buildConsoleClientEventEnvelope(payload: ConsoleClientEventPayload): ConsoleClientEventEnvelope {
    const path = typeof window !== "undefined" ? window.location.pathname : "/";
    return {
        event_id: typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
            ? crypto.randomUUID()
            : `console-client-event-${Date.now()}`,
        emitted_at: new Date().toISOString(),
        event_type: payload.event_type,
        surface: payload.surface,
        gate_kind: payload.gate_kind ?? "none",
        reason_code: normalizeConsoleClientReasonCode(payload.reason_code),
        session_error: normalizeOptionalString(payload.session_error, 120),
        api_error_code: normalizeOptionalString(payload.api_error_code, 120),
        company_selection_required: Boolean(payload.company_selection_required),
        selection_required: Boolean(payload.selection_required),
        branch_selection_required: Boolean(payload.branch_selection_required),
        path: normalizeOptionalString(payload.path, 160) ?? path,
        scope_presence: payload.scope_presence ?? readConsoleScopePresence(),
    };
}

function trySendBeacon(body: string): boolean {
    if (typeof navigator === "undefined" || typeof navigator.sendBeacon !== "function") {
        return false;
    }
    return navigator.sendBeacon(
        CONSOLE_CLIENT_EVENTS_ENDPOINT,
        new Blob([body], { type: "application/json" }),
    );
}

export async function emitConsoleClientEvent(
    payload: ConsoleClientEventPayload,
    options?: { keepalive?: boolean },
): Promise<void> {
    if (typeof window === "undefined") {
        return;
    }

    const body = JSON.stringify(buildConsoleClientEventEnvelope(payload));

    try {
        const response = await fetch(CONSOLE_CLIENT_EVENTS_ENDPOINT, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body,
            cache: "no-store",
            credentials: "same-origin",
            keepalive: options?.keepalive === true,
        });
        if (!response.ok && options?.keepalive === true) {
            trySendBeacon(body);
        }
    } catch {
        if (options?.keepalive === true) {
            trySendBeacon(body);
        }
    }
}
