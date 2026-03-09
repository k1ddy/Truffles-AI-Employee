import { useCallback, useMemo, useReducer } from "react";
import type { BookingQueueLane, BookingQueueMode } from "@/lib/calendar-bookings";
import type { CalendarQueueStateSnapshot } from "@/lib/queue-state";

export type CalendarFilterDraft = Pick<
    CalendarQueueStateSnapshot,
    "queueSearch" | "queueStatusFilter" | "followUpOwnerId" | "followUpOverdueOnly"
>;

type CalendarFiltersState = {
    snapshot: CalendarQueueStateSnapshot;
    draft: CalendarFilterDraft;
};

type CalendarFiltersAction =
    | { type: "hydrate"; snapshot: CalendarQueueStateSnapshot }
    | { type: "set-selected-date"; selectedDate: string }
    | { type: "set-queue-mode"; queueMode: BookingQueueMode; today: string }
    | { type: "set-queue-lane"; queueLane: BookingQueueLane }
    | { type: "update-draft"; patch: Partial<CalendarFilterDraft> }
    | { type: "reset-draft" }
    | { type: "apply-draft" };

export function buildCalendarFilterDraft(snapshot: CalendarQueueStateSnapshot): CalendarFilterDraft {
    return {
        queueSearch: snapshot.queueSearch,
        queueStatusFilter: snapshot.queueStatusFilter,
        followUpOwnerId: snapshot.followUpOwnerId,
        followUpOverdueOnly: snapshot.followUpOverdueOnly,
    };
}

export function calendarFilterDraftChanged(applied: CalendarFilterDraft, draft: CalendarFilterDraft): boolean {
    return JSON.stringify(applied) !== JSON.stringify(draft);
}

function calendarFiltersReducer(state: CalendarFiltersState, action: CalendarFiltersAction): CalendarFiltersState {
    switch (action.type) {
        case "hydrate": {
            return {
                snapshot: action.snapshot,
                draft: buildCalendarFilterDraft(action.snapshot),
            };
        }
        case "set-selected-date": {
            return {
                ...state,
                snapshot: {
                    ...state.snapshot,
                    selectedDate: action.selectedDate,
                },
            };
        }
        case "set-queue-mode": {
            if (action.queueMode === "history") {
                return {
                    ...state,
                    snapshot: {
                        ...state.snapshot,
                        queueMode: "history",
                        queueLane: "all",
                    },
                };
            }
            const nextSelectedDate = !state.snapshot.selectedDate || state.snapshot.selectedDate < action.today
                ? action.today
                : state.snapshot.selectedDate;
            return {
                ...state,
                snapshot: {
                    ...state.snapshot,
                    queueMode: "ops",
                    selectedDate: nextSelectedDate,
                },
            };
        }
        case "set-queue-lane": {
            return {
                ...state,
                snapshot: {
                    ...state.snapshot,
                    queueLane: action.queueLane,
                },
            };
        }
        case "update-draft": {
            return {
                ...state,
                draft: {
                    ...state.draft,
                    ...action.patch,
                },
            };
        }
        case "reset-draft": {
            return {
                ...state,
                draft: buildCalendarFilterDraft(state.snapshot),
            };
        }
        case "apply-draft": {
            return {
                ...state,
                snapshot: {
                    ...state.snapshot,
                    queueSearch: state.draft.queueSearch,
                    queueStatusFilter: state.draft.queueStatusFilter,
                    followUpOwnerId: state.draft.followUpOwnerId,
                    followUpOverdueOnly: state.draft.followUpOverdueOnly,
                },
            };
        }
        default:
            return state;
    }
}

export function useCalendarFiltersMachine(initialSnapshot: CalendarQueueStateSnapshot) {
    const [state, dispatch] = useReducer(calendarFiltersReducer, initialSnapshot, (snapshot) => ({
        snapshot,
        draft: buildCalendarFilterDraft(snapshot),
    }));
    const hydrate = useCallback(
        (snapshot: CalendarQueueStateSnapshot) => dispatch({ type: "hydrate", snapshot }),
        [],
    );
    const setSelectedDate = useCallback(
        (selectedDate: string) => dispatch({ type: "set-selected-date", selectedDate }),
        [],
    );
    const setQueueMode = useCallback(
        (queueMode: BookingQueueMode, today: string) => dispatch({ type: "set-queue-mode", queueMode, today }),
        [],
    );
    const setQueueLane = useCallback(
        (queueLane: BookingQueueLane) => dispatch({ type: "set-queue-lane", queueLane }),
        [],
    );
    const updateDraft = useCallback(
        (patch: Partial<CalendarFilterDraft>) => dispatch({ type: "update-draft", patch }),
        [],
    );
    const resetDraft = useCallback(
        () => dispatch({ type: "reset-draft" }),
        [],
    );
    const applyDraft = useCallback(
        () => dispatch({ type: "apply-draft" }),
        [],
    );

    const appliedFilterDraft = useMemo(
        () => buildCalendarFilterDraft(state.snapshot),
        [state.snapshot],
    );
    const queueFiltersDirty = useMemo(
        () => calendarFilterDraftChanged(appliedFilterDraft, state.draft),
        [appliedFilterDraft, state.draft],
    );

    return {
        state,
        snapshot: state.snapshot,
        draft: state.draft,
        appliedFilterDraft,
        queueFiltersDirty,
        hydrate,
        setSelectedDate,
        setQueueMode,
        setQueueLane,
        updateDraft,
        resetDraft,
        applyDraft,
    };
}
