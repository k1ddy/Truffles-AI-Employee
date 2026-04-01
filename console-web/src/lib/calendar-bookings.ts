import api from "@/lib/api";
import {
    buildCalendarBookingActionAvailabilityMap,
    getCalendarVisitActionOptions,
    type CalendarActionPermissions,
    type CalendarBookingLike,
} from "@/lib/calendar-action-registry";

export interface Booking {
    id: string;
    specialist_id: string;
    specialist_name: string;
    start_at: string;
    end_at: string;
    customer_name: string | null;
    customer_phone: string | null;
    service_type: string | null;
    notes?: string | null;
    status: string;
    no_show_followup_done?: boolean;
    no_show_followup_result?: "contacted" | "rebooked" | null;
    no_show_followup_closed_at?: string | null;
    no_show_followup_closed_by?: string | null;
    no_show_followup_rebooked_appointment_id?: string | null;
    follow_up_owner_id?: string | null;
    follow_up_owner_name?: string | null;
    follow_up_due_at?: string | null;
    follow_up_overdue?: boolean;
    conversation_id?: string | null;
    case_id?: string | null;
    needs_action?: boolean;
    attention_reason?: string | null;
    version: number;
    allowed_actions?: Array<
        | "edit_booking"
        | "cancel_booking"
        | "mark_completed"
        | "mark_no_show"
        | "record_follow_up_contacted"
        | "record_follow_up_rebooked"
        | "manage_follow_up_governance"
        | "open_case_from_booking"
    >;
    blocked_actions?: Array<{
        action_id:
            | "edit_booking"
            | "cancel_booking"
            | "mark_completed"
            | "mark_no_show"
            | "record_follow_up_contacted"
            | "record_follow_up_rebooked"
            | "manage_follow_up_governance"
            | "open_case_from_booking";
        reason_code:
            | "permission_required"
            | "active_status_only"
            | "open_no_show_required"
            | "follow_up_already_closed"
            | "case_link_required";
    }>;
    last_actor_type?: string | null;
    created_at: string;
}

export interface BookingCreateRequest {
    specialist_id: string;
    start_at: string;
    end_at: string;
    customer_name?: string;
    customer_phone?: string;
    service_type?: string;
    notes?: string;
    conversation_id?: string;
    case_id?: string;
}

export interface BookingStatusUpdateRequest {
    status: "COMPLETED" | "NO_SHOW";
    reason?: string;
    version: number;
}

export interface BookingUpdateRequest {
    specialist_id: string;
    start_at: string;
    end_at: string;
    customer_name: string;
    customer_phone: string;
    service_type: string;
    notes?: string;
    version: number;
}

export interface BookingCancelRequest {
    reason?: string;
    version: number;
}

export interface BookingNoShowFollowUpRequest {
    result?: "contacted" | "rebooked";
    rebooked_appointment_id?: string;
    note?: string;
    version: number;
}

export interface BookingFollowUpGovernanceRequest {
    owner_agent_id?: string | null;
    due_at?: string | null;
    version: number;
}

export interface BookingActionResponse {
    success: boolean;
    booking: Booking;
    case_effects?: Array<{
        case_id: string;
        action: "reopened_for_booking_attention" | "linked_rebooked_booking";
        message: string;
    }>;
}

export interface BookingsListResponse {
    items: Booking[];
    cursor?: string | null;
    has_more?: boolean;
}

export interface CalendarOperatorEventRequest {
    event_type: "filter_apply" | "filter_reset" | "double_submit_blocked";
    action_id:
        | "apply_filters"
        | "reset_filters"
        | "create_booking"
        | "edit_booking"
        | "reschedule_booking"
        | "cancel_booking"
        | "mark_completed"
        | "mark_no_show"
        | "record_follow_up_contacted"
        | "record_follow_up_rebooked"
        | "manage_follow_up_governance";
    surface: "filter_panel" | "booking_panel" | "follow_up_panel" | "follow_up_governance" | "composer";
    booking_id?: string;
}

const DEFAULT_CALENDAR_WRITE_PERMISSIONS: CalendarActionPermissions = {
    canWriteCalendar: true,
    canManageFollowUpGovernance: false,
};

export type BookingQueueLane = "attention" | "all";
export type BookingQueueMode = "ops" | "history";
export type BookingStatusFilter = "all" | "scheduled" | "completed" | "no_show" | "cancelled";

export async function fetchBookings(options?: {
    date?: string;
    conversationId?: string;
    caseId?: string;
    lane?: BookingQueueLane;
    status?: BookingStatusFilter;
    needsAction?: boolean;
    followUpOwnerId?: string;
    followUpOverdue?: boolean;
    cursor?: string;
}): Promise<BookingsListResponse> {
    const params = new URLSearchParams();
    if (options?.date) {
        params.set("date_from", options.date);
        params.set("date_to", options.date);
    }
    if (options?.conversationId) {
        params.set("conversation_id", options.conversationId);
    }
    if (options?.caseId) {
        params.set("case_id", options.caseId);
    }
    if (options?.lane) {
        params.set("lane", options.lane);
    }
    if (options?.status && options.status !== "all") {
        params.set("status", options.status);
    }
    if (typeof options?.needsAction === "boolean") {
        params.set("needs_action", String(options.needsAction));
    }
    if (options?.followUpOwnerId) {
        params.set("follow_up_owner_id", options.followUpOwnerId);
    }
    if (typeof options?.followUpOverdue === "boolean") {
        params.set("follow_up_overdue", String(options.followUpOverdue));
    }
    if (options?.cursor) {
        params.set("cursor", options.cursor);
    }
    const suffix = params.toString() ? `?${params.toString()}` : "";
    const response = await api.get(`/calendar/bookings${suffix}`);
    return response.data;
}

export async function createBooking(data: BookingCreateRequest): Promise<BookingActionResponse> {
    const response = await api.post("/calendar/bookings", data);
    return response.data;
}

export async function updateBookingStatus(bookingId: string, data: BookingStatusUpdateRequest): Promise<BookingActionResponse> {
    const response = await api.post(`/calendar/bookings/${bookingId}/status`, data);
    return response.data;
}

export async function updateBooking(bookingId: string, data: BookingUpdateRequest): Promise<BookingActionResponse> {
    const response = await api.patch(`/calendar/bookings/${bookingId}`, data);
    return response.data;
}

export async function cancelBooking(bookingId: string, data: BookingCancelRequest): Promise<BookingActionResponse> {
    const response = await api.post(`/calendar/bookings/${bookingId}/cancel`, data);
    return response.data;
}

export async function registerNoShowFollowUp(
    bookingId: string,
    data: BookingNoShowFollowUpRequest,
): Promise<BookingActionResponse> {
    const response = await api.post(`/calendar/bookings/${bookingId}/no-show-followup`, data);
    return response.data;
}

export async function updateBookingFollowUpGovernance(
    bookingId: string,
    data: BookingFollowUpGovernanceRequest,
): Promise<BookingActionResponse> {
    const response = await api.post(`/calendar/bookings/${bookingId}/follow-up-governance`, data);
    return response.data;
}

export async function recordCalendarOperatorEvent(data: CalendarOperatorEventRequest): Promise<void> {
    await api.post("/calendar/operator-events", data);
}

export function getVisitActionOptions(status: string): Array<{ status: BookingStatusUpdateRequest["status"]; label: string }> {
    return getCalendarVisitActionOptions(
        { status } satisfies CalendarBookingLike,
        DEFAULT_CALENDAR_WRITE_PERMISSIONS,
    ).map((action) => ({
        status: action.status,
        label: action.label,
    }));
}

export function canEditBooking(status: string): boolean {
    return buildCalendarBookingActionAvailabilityMap(
        { status } satisfies CalendarBookingLike,
        DEFAULT_CALENDAR_WRITE_PERMISSIONS,
    ).edit_booking.state === "enabled";
}

export function canCancelBooking(status: string): boolean {
    return buildCalendarBookingActionAvailabilityMap(
        { status } satisfies CalendarBookingLike,
        DEFAULT_CALENDAR_WRITE_PERMISSIONS,
    ).cancel_booking.state === "enabled";
}

export function bookingNeedsAttention(booking: Booking): boolean {
    if (typeof booking.needs_action === "boolean") {
        return booking.needs_action;
    }
    const normalized = booking.status.toUpperCase();
    if (normalized === "NO_SHOW" && !booking.no_show_followup_done) {
        return true;
    }
    return ["PENDING_CONFIRMATION", "RESCHEDULE_REQUESTED", "NO_SHOW", "HOLD"].includes(normalized);
}

export function getBookingAttentionLabel(booking: Booking): string | null {
    if (booking.attention_reason && booking.attention_reason.trim()) {
        return booking.attention_reason;
    }
    const normalized = booking.status.toUpperCase();
    if (normalized === "PENDING_CONFIRMATION") {
        return "Нужно подтвердить визит";
    }
    if (normalized === "RESCHEDULE_REQUESTED") {
        return "Клиент просит перенос";
    }
    if (normalized === "HOLD") {
        return "Нужно решение менеджера";
    }
    if (normalized === "NO_SHOW" && !booking.no_show_followup_done) {
        return "Связаться после неявки";
    }
    return null;
}

export function collectBookingCaseEffectMessages(response?: BookingActionResponse | null): string[] {
    if (!response?.case_effects?.length) {
        return [];
    }
    return response.case_effects
        .map((effect) => effect?.message?.trim())
        .filter((message): message is string => Boolean(message));
}
