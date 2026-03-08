type JsonBuildResult = { value?: Record<string, unknown>; error?: string };

const ISO_CURRENCY_RE = /^[A-Z]{3}$/;

export function buildBillingInfoPayload(input: {
    contract: string;
    currency: string;
}): JsonBuildResult {
    const payload: Record<string, unknown> = {};
    const contract = input.contract.trim();
    const currency = input.currency.trim().toUpperCase();
    if (contract && contract.length < 2) {
        return { error: "billing_info.contract: минимум 2 символа" };
    }
    if (currency && !ISO_CURRENCY_RE.test(currency)) {
        return { error: "billing_info.currency: используйте ISO-код (например KZT)" };
    }
    if (contract) {
        payload.contract = contract;
    }
    if (currency) {
        payload.currency = currency;
    }
    return { value: Object.keys(payload).length ? payload : undefined };
}

export function readBillingInfoPayload(payload: Record<string, unknown>): {
    contract: string;
    currency: string;
} {
    const contract = payload.contract;
    const currency = payload.currency;
    return {
        contract: typeof contract === "string" ? contract : "",
        currency: typeof currency === "string" ? currency.toUpperCase() : "",
    };
}

export function buildWorkingHoursPayload(input: {
    selectedDays: string[];
    start: string;
    end: string;
}): JsonBuildResult {
    const selectedDays = input.selectedDays;
    const start = input.start.trim();
    const end = input.end.trim();
    if (!selectedDays.length && !start && !end) {
        return {};
    }
    if (!selectedDays.length) {
        return { error: "Укажите рабочие дни" };
    }
    if (!start || !end) {
        return { error: "Укажите время открытия и закрытия" };
    }
    if (start >= end) {
        return { error: "working_hours: время закрытия должно быть позже открытия" };
    }
    const payload: Record<string, unknown> = {};
    selectedDays.forEach((day) => {
        payload[day] = [{ start, end }];
    });
    return { value: payload };
}

function readFirstSlotTimes(slots: unknown): { start: string; end: string } {
    if (!Array.isArray(slots) || !slots[0] || typeof slots[0] !== "object") {
        return { start: "", end: "" };
    }
    const slot = slots[0] as { start?: unknown; end?: unknown };
    return {
        start: typeof slot.start === "string" ? slot.start : "",
        end: typeof slot.end === "string" ? slot.end : "",
    };
}

export function readWorkingHoursPayload(
    payload: Record<string, unknown>,
    options: { orderedDays: string[] },
): { days: string[]; start: string; end: string } {
    const { orderedDays } = options;
    const dayKeys = orderedDays.filter((day) => Array.isArray(payload[day]));
    const firstDay = dayKeys[0];
    if (!firstDay) {
        return { days: dayKeys, start: "", end: "" };
    }
    const firstSlot = readFirstSlotTimes(payload[firstDay]);
    return {
        days: dayKeys,
        start: firstSlot.start,
        end: firstSlot.end,
    };
}

export function buildBookingSettingsPayload(input: {
    defaultDuration: string;
    bufferMin: string;
}): JsonBuildResult {
    const defaultDurationRaw = input.defaultDuration.trim();
    const bufferMinRaw = input.bufferMin.trim();
    if (!defaultDurationRaw && !bufferMinRaw) {
        return {};
    }
    const payload: Record<string, unknown> = {};
    if (defaultDurationRaw) {
        const parsed = Number(defaultDurationRaw);
        if (!Number.isInteger(parsed)) {
            return { error: "default_duration_min: укажите целое число" };
        }
        if (parsed < 5 || parsed > 480) {
            return { error: "default_duration_min: допустимо от 5 до 480" };
        }
        payload.default_duration_min = parsed;
    }
    if (bufferMinRaw) {
        const parsed = Number(bufferMinRaw);
        if (!Number.isInteger(parsed)) {
            return { error: "buffer_min: укажите целое число" };
        }
        if (parsed < 0 || parsed > 240) {
            return { error: "buffer_min: допустимо от 0 до 240" };
        }
        payload.buffer_min = parsed;
    }
    return { value: payload };
}

export function readBookingSettingsPayload(payload: Record<string, unknown>): {
    defaultDuration: string;
    bufferMin: string;
} {
    const defaultDuration = payload.default_duration_min;
    const bufferMin = payload.buffer_min;
    return {
        defaultDuration: (typeof defaultDuration === "number" || typeof defaultDuration === "string")
            ? String(defaultDuration)
            : "",
        bufferMin: (typeof bufferMin === "number" || typeof bufferMin === "string")
            ? String(bufferMin)
            : "",
    };
}
