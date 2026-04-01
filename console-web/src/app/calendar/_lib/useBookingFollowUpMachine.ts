import { useCallback, useReducer } from "react";

export type NoShowFollowUpDraft = {
    result: "contacted" | "rebooked";
    rebookedAppointmentId: string;
    note: string;
};

export type FollowUpGovernanceDraft = {
    ownerAgentId: string;
    dueAt: string;
};

type BookingFollowUpState = {
    followUpBookingId: string | null;
    followUpGovernanceBookingId: string | null;
    noShowFollowUpDrafts: Record<string, NoShowFollowUpDraft>;
    followUpGovernanceDrafts: Record<string, FollowUpGovernanceDraft>;
};

type BookingFollowUpAction =
    | { type: "set-follow-up-pending"; bookingId: string }
    | { type: "clear-follow-up-pending" }
    | { type: "set-governance-pending"; bookingId: string }
    | { type: "clear-governance-pending" }
    | { type: "set-no-show-draft"; bookingId: string; patch: Partial<NoShowFollowUpDraft> }
    | { type: "clear-no-show-draft"; bookingId: string }
    | { type: "set-governance-draft"; bookingId: string; patch: Partial<FollowUpGovernanceDraft> }
    | { type: "clear-governance-draft"; bookingId: string }
    | { type: "clear-booking"; bookingId: string }
    | { type: "clear-all" };

const initialState: BookingFollowUpState = {
    followUpBookingId: null,
    followUpGovernanceBookingId: null,
    noShowFollowUpDrafts: {},
    followUpGovernanceDrafts: {},
};

function reducer(state: BookingFollowUpState, action: BookingFollowUpAction): BookingFollowUpState {
    switch (action.type) {
        case "set-follow-up-pending":
            return {
                ...state,
                followUpBookingId: action.bookingId,
            };
        case "clear-follow-up-pending":
            return {
                ...state,
                followUpBookingId: null,
            };
        case "set-governance-pending":
            return {
                ...state,
                followUpGovernanceBookingId: action.bookingId,
            };
        case "clear-governance-pending":
            return {
                ...state,
                followUpGovernanceBookingId: null,
            };
        case "set-no-show-draft": {
            const currentDraft = state.noShowFollowUpDrafts[action.bookingId] ?? {
                result: "contacted" as const,
                rebookedAppointmentId: "",
                note: "",
            };
            return {
                ...state,
                noShowFollowUpDrafts: {
                    ...state.noShowFollowUpDrafts,
                    [action.bookingId]: {
                        result: action.patch.result ?? currentDraft.result,
                        rebookedAppointmentId: action.patch.rebookedAppointmentId ?? currentDraft.rebookedAppointmentId,
                        note: action.patch.note ?? currentDraft.note,
                    },
                },
            };
        }
        case "clear-no-show-draft": {
            const next = { ...state.noShowFollowUpDrafts };
            delete next[action.bookingId];
            return {
                ...state,
                noShowFollowUpDrafts: next,
            };
        }
        case "set-governance-draft": {
            const currentDraft = state.followUpGovernanceDrafts[action.bookingId] ?? {
                ownerAgentId: "",
                dueAt: "",
            };
            return {
                ...state,
                followUpGovernanceDrafts: {
                    ...state.followUpGovernanceDrafts,
                    [action.bookingId]: {
                        ownerAgentId: action.patch.ownerAgentId ?? currentDraft.ownerAgentId,
                        dueAt: action.patch.dueAt ?? currentDraft.dueAt,
                    },
                },
            };
        }
        case "clear-governance-draft": {
            const next = { ...state.followUpGovernanceDrafts };
            delete next[action.bookingId];
            return {
                ...state,
                followUpGovernanceDrafts: next,
            };
        }
        case "clear-booking": {
            const nextNoShow = { ...state.noShowFollowUpDrafts };
            delete nextNoShow[action.bookingId];
            const nextGovernance = { ...state.followUpGovernanceDrafts };
            delete nextGovernance[action.bookingId];
            return {
                ...state,
                noShowFollowUpDrafts: nextNoShow,
                followUpGovernanceDrafts: nextGovernance,
            };
        }
        case "clear-all":
            return initialState;
        default:
            return state;
    }
}

export function useBookingFollowUpMachine() {
    const [state, dispatch] = useReducer(reducer, initialState);
    const setFollowUpPending = useCallback((bookingId: string) => dispatch({ type: "set-follow-up-pending", bookingId }), []);
    const clearFollowUpPending = useCallback(() => dispatch({ type: "clear-follow-up-pending" }), []);
    const setGovernancePending = useCallback((bookingId: string) => dispatch({ type: "set-governance-pending", bookingId }), []);
    const clearGovernancePending = useCallback(() => dispatch({ type: "clear-governance-pending" }), []);
    const setNoShowDraft = useCallback(
        (bookingId: string, patch: Partial<NoShowFollowUpDraft>) => dispatch({ type: "set-no-show-draft", bookingId, patch }),
        [],
    );
    const clearNoShowDraft = useCallback((bookingId: string) => dispatch({ type: "clear-no-show-draft", bookingId }), []);
    const setGovernanceDraft = useCallback(
        (bookingId: string, patch: Partial<FollowUpGovernanceDraft>) => dispatch({ type: "set-governance-draft", bookingId, patch }),
        [],
    );
    const clearGovernanceDraft = useCallback((bookingId: string) => dispatch({ type: "clear-governance-draft", bookingId }), []);
    const clearBooking = useCallback((bookingId: string) => dispatch({ type: "clear-booking", bookingId }), []);
    const clearAll = useCallback(() => dispatch({ type: "clear-all" }), []);

    return {
        state,
        followUpBookingId: state.followUpBookingId,
        followUpGovernanceBookingId: state.followUpGovernanceBookingId,
        noShowFollowUpDrafts: state.noShowFollowUpDrafts,
        followUpGovernanceDrafts: state.followUpGovernanceDrafts,
        setFollowUpPending,
        clearFollowUpPending,
        setGovernancePending,
        clearGovernancePending,
        setNoShowDraft,
        clearNoShowDraft,
        setGovernanceDraft,
        clearGovernanceDraft,
        clearBooking,
        clearAll,
    };
}
