import api from "@/lib/api";

export interface Booking {
    id: string;
    specialist_id: string;
    specialist_name: string;
    start_at: string;
    end_at: string;
    customer_name: string | null;
    customer_phone: string | null;
    service_type: string | null;
    status: string;
    no_show_followup_done?: boolean;
    no_show_followup_result?: "contacted" | "rebooked" | null;
    no_show_followup_closed_at?: string | null;
    no_show_followup_closed_by?: string | null;
    no_show_followup_rebooked_appointment_id?: string | null;
    conversation_id?: string | null;
    case_id?: string | null;
    needs_action?: boolean;
    attention_reason?: string | null;
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
}

export interface BookingNoShowFollowUpRequest {
    result?: "contacted" | "rebooked";
    rebooked_appointment_id?: string;
    note?: string;
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

export type BookingQueueLane = "attention" | "all";
export type BookingStatusFilter = "all" | "scheduled" | "completed" | "no_show" | "cancelled";

export async function fetchBookings(options?: {
    date?: string;
    conversationId?: string;
    caseId?: string;
    lane?: BookingQueueLane;
    status?: BookingStatusFilter;
    needsAction?: boolean;
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

export async function registerNoShowFollowUp(
    bookingId: string,
    data: BookingNoShowFollowUpRequest = {},
): Promise<BookingActionResponse> {
    const response = await api.post(`/calendar/bookings/${bookingId}/no-show-followup`, data);
    return response.data;
}

export function getVisitActionOptions(status: string): Array<{ status: BookingStatusUpdateRequest["status"]; label: string }> {
    const normalized = status.toUpperCase();
    if (["HOLD", "PENDING_CONFIRMATION", "CONFIRMED", "RESCHEDULE_REQUESTED", "CHECKED_IN"].includes(normalized)) {
        return [
            { status: "COMPLETED", label: "Пришел" },
            { status: "NO_SHOW", label: "Не пришел" },
        ];
    }
    return [];
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
