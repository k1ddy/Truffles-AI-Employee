import { useCallback, useMemo, useReducer } from "react";

export type BookingComposerMode = "create" | "edit";

type BookingComposerSnapshot<TService, TSlot> = {
    mode: BookingComposerMode;
    editingBookingId: string | null;
    selectedService: TService | null;
    selectedSpecialist: string;
    bookingDate: string;
    selectedSlot: TSlot | null;
    customerName: string;
    customerPhoneInput: string;
    notes: string;
};

type BookingComposerState<TService, TSlot> = BookingComposerSnapshot<TService, TSlot> & {
    isOpen: boolean;
    baseline: BookingComposerSnapshot<TService, TSlot>;
};

type OpenCreatePayload = {
    bookingDate: string;
    customerName: string;
    customerPhoneInput: string;
    preserveSelections: boolean;
};

type OpenEditPayload<TService, TSlot> = {
    editingBookingId: string;
    selectedService: TService | null;
    selectedSpecialist: string;
    bookingDate: string;
    selectedSlot: TSlot | null;
    customerName: string;
    customerPhoneInput: string;
    notes: string;
};

type ResetPayload = {
    keepOpen: boolean;
    resetSelections: boolean;
    bookingDate: string;
    customerName: string;
    customerPhoneInput: string;
};

type BookingComposerAction<TService, TSlot> =
    | { type: "open-create"; payload: OpenCreatePayload }
    | { type: "open-edit"; payload: OpenEditPayload<TService, TSlot> }
    | { type: "reset"; payload: ResetPayload }
    | { type: "close" }
    | { type: "set-service"; service: TService | null; resetSpecialist: boolean }
    | { type: "set-specialist"; specialistId: string }
    | { type: "set-booking-date"; bookingDate: string }
    | { type: "set-slot"; slot: TSlot | null }
    | { type: "set-customer-name"; customerName: string }
    | { type: "set-customer-phone"; customerPhoneInput: string }
    | { type: "set-notes"; notes: string }
    | { type: "apply-case-prefill-if-empty"; customerName: string; customerPhoneInput: string }
    | { type: "restore-baseline"; keepOpen: boolean };

type UseBookingComposerMachineOptions<TService, TSlot> = {
    initialBookingDate: string;
    initialCustomerName: string;
    initialCustomerPhoneInput: string;
    getServiceKey: (service: TService | null) => string;
    getSlotKey: (slot: TSlot | null) => string;
};

function createSnapshot<TService, TSlot>(
    payload: Partial<BookingComposerSnapshot<TService, TSlot>>,
    defaults: Pick<BookingComposerSnapshot<TService, TSlot>, "bookingDate" | "customerName" | "customerPhoneInput">,
): BookingComposerSnapshot<TService, TSlot> {
    return {
        mode: payload.mode ?? "create",
        editingBookingId: payload.editingBookingId ?? null,
        selectedService: payload.selectedService ?? null,
        selectedSpecialist: payload.selectedSpecialist ?? "",
        bookingDate: payload.bookingDate ?? defaults.bookingDate,
        selectedSlot: payload.selectedSlot ?? null,
        customerName: payload.customerName ?? defaults.customerName,
        customerPhoneInput: payload.customerPhoneInput ?? defaults.customerPhoneInput,
        notes: payload.notes ?? "",
    };
}

function reducer<TService, TSlot>(
    state: BookingComposerState<TService, TSlot>,
    action: BookingComposerAction<TService, TSlot>,
): BookingComposerState<TService, TSlot> {
    switch (action.type) {
        case "open-create": {
            const payload = action.payload;
            const nextSnapshot = createSnapshot<TService, TSlot>({
                mode: "create",
                editingBookingId: null,
                selectedService: payload.preserveSelections ? state.selectedService : null,
                selectedSpecialist: payload.preserveSelections ? state.selectedSpecialist : "",
                bookingDate: payload.preserveSelections ? state.bookingDate || payload.bookingDate : payload.bookingDate,
                selectedSlot: null,
                customerName: payload.customerName,
                customerPhoneInput: payload.customerPhoneInput,
                notes: "",
            }, payload);
            return {
                ...state,
                ...nextSnapshot,
                isOpen: true,
                baseline: nextSnapshot,
            };
        }
        case "open-edit": {
            const nextSnapshot = createSnapshot<TService, TSlot>({
                mode: "edit",
                editingBookingId: action.payload.editingBookingId,
                selectedService: action.payload.selectedService,
                selectedSpecialist: action.payload.selectedSpecialist,
                bookingDate: action.payload.bookingDate,
                selectedSlot: action.payload.selectedSlot,
                customerName: action.payload.customerName,
                customerPhoneInput: action.payload.customerPhoneInput,
                notes: action.payload.notes,
            }, action.payload);
            return {
                ...state,
                ...nextSnapshot,
                isOpen: true,
                baseline: nextSnapshot,
            };
        }
        case "reset": {
            const payload = action.payload;
            const nextSnapshot = createSnapshot<TService, TSlot>({
                mode: "create",
                editingBookingId: null,
                selectedService: payload.resetSelections ? null : state.selectedService,
                selectedSpecialist: payload.resetSelections ? "" : state.selectedSpecialist,
                bookingDate: payload.resetSelections ? payload.bookingDate : state.bookingDate || payload.bookingDate,
                selectedSlot: null,
                customerName: payload.customerName,
                customerPhoneInput: payload.customerPhoneInput,
                notes: "",
            }, payload);
            return {
                ...state,
                ...nextSnapshot,
                isOpen: payload.keepOpen,
                baseline: nextSnapshot,
            };
        }
        case "close":
            return {
                ...state,
                isOpen: false,
            };
        case "set-service":
            return {
                ...state,
                selectedService: action.service,
                selectedSpecialist: action.resetSpecialist ? "" : state.selectedSpecialist,
                selectedSlot: null,
            };
        case "set-specialist":
            return {
                ...state,
                selectedSpecialist: action.specialistId,
                selectedSlot: null,
            };
        case "set-booking-date":
            return {
                ...state,
                bookingDate: action.bookingDate,
                selectedSlot: null,
            };
        case "set-slot":
            return {
                ...state,
                selectedSlot: action.slot,
            };
        case "set-customer-name":
            return {
                ...state,
                customerName: action.customerName,
            };
        case "set-customer-phone":
            return {
                ...state,
                customerPhoneInput: action.customerPhoneInput,
            };
        case "set-notes":
            return {
                ...state,
                notes: action.notes,
            };
        case "apply-case-prefill-if-empty":
            return {
                ...state,
                customerName: state.customerName.trim() ? state.customerName : action.customerName,
                customerPhoneInput: state.customerPhoneInput.trim() ? state.customerPhoneInput : action.customerPhoneInput,
            };
        case "restore-baseline":
            return {
                ...state,
                ...state.baseline,
                isOpen: action.keepOpen,
            };
        default:
            return state;
    }
}

function snapshotsEqual<TService, TSlot>(
    left: BookingComposerSnapshot<TService, TSlot>,
    right: BookingComposerSnapshot<TService, TSlot>,
    getServiceKey: (service: TService | null) => string,
    getSlotKey: (slot: TSlot | null) => string,
): boolean {
    return left.mode === right.mode
        && left.editingBookingId === right.editingBookingId
        && getServiceKey(left.selectedService) === getServiceKey(right.selectedService)
        && left.selectedSpecialist === right.selectedSpecialist
        && left.bookingDate === right.bookingDate
        && getSlotKey(left.selectedSlot) === getSlotKey(right.selectedSlot)
        && left.customerName === right.customerName
        && left.customerPhoneInput === right.customerPhoneInput
        && left.notes === right.notes;
}

export function useBookingComposerMachine<TService, TSlot>(options: UseBookingComposerMachineOptions<TService, TSlot>) {
    const initialSnapshot = createSnapshot<TService, TSlot>({}, {
        bookingDate: options.initialBookingDate,
        customerName: options.initialCustomerName,
        customerPhoneInput: options.initialCustomerPhoneInput,
    });
    const [state, dispatch] = useReducer(reducer<TService, TSlot>, {
        ...initialSnapshot,
        isOpen: false,
        baseline: initialSnapshot,
    });

    const isDirty = useMemo(
        () => !snapshotsEqual(state, state.baseline, options.getServiceKey, options.getSlotKey),
        [options.getServiceKey, options.getSlotKey, state],
    );
    const openCreate = useCallback((payload: OpenCreatePayload) => dispatch({ type: "open-create", payload }), []);
    const openEdit = useCallback((payload: OpenEditPayload<TService, TSlot>) => dispatch({ type: "open-edit", payload }), []);
    const reset = useCallback((payload: ResetPayload) => dispatch({ type: "reset", payload }), []);
    const close = useCallback(() => dispatch({ type: "close" }), []);
    const setService = useCallback((service: TService | null, resetSpecialist: boolean) => dispatch({ type: "set-service", service, resetSpecialist }), []);
    const setSpecialist = useCallback((specialistId: string) => dispatch({ type: "set-specialist", specialistId }), []);
    const setBookingDate = useCallback((bookingDate: string) => dispatch({ type: "set-booking-date", bookingDate }), []);
    const setSlot = useCallback((slot: TSlot | null) => dispatch({ type: "set-slot", slot }), []);
    const setCustomerName = useCallback((customerName: string) => dispatch({ type: "set-customer-name", customerName }), []);
    const setCustomerPhoneInput = useCallback((customerPhoneInput: string) => dispatch({ type: "set-customer-phone", customerPhoneInput }), []);
    const setNotes = useCallback((notes: string) => dispatch({ type: "set-notes", notes }), []);
    const applyCasePrefillIfEmpty = useCallback(
        (customerName: string, customerPhoneInput: string) => dispatch({
            type: "apply-case-prefill-if-empty",
            customerName,
            customerPhoneInput,
        }),
        [],
    );
    const restoreBaseline = useCallback((keepOpen = true) => dispatch({ type: "restore-baseline", keepOpen }), []);

    return {
        state,
        isOpen: state.isOpen,
        mode: state.mode,
        editingBookingId: state.editingBookingId,
        selectedService: state.selectedService,
        selectedSpecialist: state.selectedSpecialist,
        bookingDate: state.bookingDate,
        selectedSlot: state.selectedSlot,
        customerName: state.customerName,
        customerPhoneInput: state.customerPhoneInput,
        notes: state.notes,
        isDirty,
        openCreate,
        openEdit,
        reset,
        close,
        setService,
        setSpecialist,
        setBookingDate,
        setSlot,
        setCustomerName,
        setCustomerPhoneInput,
        setNotes,
        applyCasePrefillIfEmpty,
        restoreBaseline,
    };
}
