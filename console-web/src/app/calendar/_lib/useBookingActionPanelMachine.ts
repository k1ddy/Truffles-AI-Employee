import { useCallback, useMemo, useReducer } from "react";

type BookingActionPanelState = {
    bookingId: string | null;
    cancelReasonDraft: string;
    statusUpdateBookingId: string | null;
    cancelBookingId: string | null;
};

type BookingActionPanelAction =
    | { type: "open"; bookingId: string }
    | { type: "close" }
    | { type: "set-cancel-reason"; value: string }
    | { type: "set-status-pending"; bookingId: string }
    | { type: "clear-status-pending" }
    | { type: "set-cancel-pending"; bookingId: string }
    | { type: "clear-cancel-pending" };

const initialState: BookingActionPanelState = {
    bookingId: null,
    cancelReasonDraft: "",
    statusUpdateBookingId: null,
    cancelBookingId: null,
};

function reducer(state: BookingActionPanelState, action: BookingActionPanelAction): BookingActionPanelState {
    switch (action.type) {
        case "open":
            return {
                ...state,
                bookingId: action.bookingId,
                cancelReasonDraft: "",
            };
        case "close":
            return {
                ...state,
                bookingId: null,
                cancelReasonDraft: "",
            };
        case "set-cancel-reason":
            return {
                ...state,
                cancelReasonDraft: action.value,
            };
        case "set-status-pending":
            return {
                ...state,
                statusUpdateBookingId: action.bookingId,
            };
        case "clear-status-pending":
            return {
                ...state,
                statusUpdateBookingId: null,
            };
        case "set-cancel-pending":
            return {
                ...state,
                cancelBookingId: action.bookingId,
            };
        case "clear-cancel-pending":
            return {
                ...state,
                cancelBookingId: null,
            };
        default:
            return state;
    }
}

export function useBookingActionPanelMachine() {
    const [state, dispatch] = useReducer(reducer, initialState);
    const isDirty = useMemo(() => state.cancelReasonDraft.trim().length > 0, [state.cancelReasonDraft]);
    const open = useCallback((bookingId: string) => dispatch({ type: "open", bookingId }), []);
    const close = useCallback(() => dispatch({ type: "close" }), []);
    const setCancelReasonDraft = useCallback((value: string) => dispatch({ type: "set-cancel-reason", value }), []);
    const setStatusUpdatePending = useCallback((bookingId: string) => dispatch({ type: "set-status-pending", bookingId }), []);
    const clearStatusUpdatePending = useCallback(() => dispatch({ type: "clear-status-pending" }), []);
    const setCancelPending = useCallback((bookingId: string) => dispatch({ type: "set-cancel-pending", bookingId }), []);
    const clearCancelPending = useCallback(() => dispatch({ type: "clear-cancel-pending" }), []);

    return {
        state,
        bookingId: state.bookingId,
        cancelReasonDraft: state.cancelReasonDraft,
        statusUpdateBookingId: state.statusUpdateBookingId,
        cancelBookingId: state.cancelBookingId,
        isDirty,
        open,
        close,
        setCancelReasonDraft,
        setStatusUpdatePending,
        clearStatusUpdatePending,
        setCancelPending,
        clearCancelPending,
    };
}
