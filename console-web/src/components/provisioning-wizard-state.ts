import { parseOptionalJson, stringifyOptionalJson } from "@/components/provisioning-wizard-utils";
import {
    buildBillingInfoPayload as buildBillingInfoPayloadDraft,
    buildBookingSettingsPayload as buildBookingSettingsPayloadDraft,
    buildWorkingHoursPayload as buildWorkingHoursPayloadDraft,
    readBillingInfoPayload,
    readBookingSettingsPayload,
    readWorkingHoursPayload,
} from "@/components/provisioning-wizard-json-payloads";

export type ProvisioningBranchFormState = {
    name: string;
    slug: string;
    timezone: string;
    phone: string;
    instanceId: string;
    telegramChatId: string;
    knowledgeTag: string;
    workingHours: string;
    bookingSettings: string;
};

export type ProvisioningBranchBootstrapState = {
    enabled: boolean;
    createOwner: boolean;
    createAdmin: boolean;
    createManager: boolean;
    ownerName: string;
    ownerOidcSubject: string;
    adminName: string;
    adminOidcSubject: string;
    managerName: string;
    managerOidcSubject: string;
};

export type ProvisioningAutopilotFormState = {
    companyName: string;
    clientSlug: string;
    branchName: string;
    branchSlug: string;
    timezone: string;
    phone: string;
    instanceId: string;
    domainSlug: string;
    paymentStatus: "pending" | "confirmed" | "rejected";
    providerBindingProvider: string;
    providerBindingWebhookStatus: "configured" | "pending" | "rebind_required";
    providerBindingPaidUntil: string;
    providerBindingOwner: string;
    providerBindingNextRenewalAt: string;
    providerBindingLastRebindAt: string;
    providerBindingRebindRequired: boolean;
    providerBindingAlertState: "ok" | "warn" | "critical";
    providerBindingNotes: string;
    clientDataText: string;
};

export type ProvisioningWizardResetState = {
    branchForm: ProvisioningBranchFormState;
    branchBootstrap: ProvisioningBranchBootstrapState;
    autopilotForm: ProvisioningAutopilotFormState;
};

type BranchLike = {
    id?: string | null;
    name?: string | null;
    slug?: string | null;
    timezone?: string | null;
    phone?: string | null;
    instance_id?: string | null;
    telegram_chat_id?: string | null;
    knowledge_tag?: string | null;
    working_hours?: unknown;
    booking_settings?: unknown;
};

export function createInitialBranchForm(defaultTimezone: string): ProvisioningBranchFormState {
    return {
        name: "",
        slug: "",
        timezone: defaultTimezone,
        phone: "",
        instanceId: "",
        telegramChatId: "",
        knowledgeTag: "",
        workingHours: "",
        bookingSettings: "",
    };
}

export function createInitialBranchBootstrapState(): ProvisioningBranchBootstrapState {
    return {
        enabled: true,
        createOwner: true,
        createAdmin: true,
        createManager: true,
        ownerName: "",
        ownerOidcSubject: "",
        adminName: "",
        adminOidcSubject: "",
        managerName: "",
        managerOidcSubject: "",
    };
}

export function createInitialAutopilotForm(defaultTimezone: string): ProvisioningAutopilotFormState {
    return {
        companyName: "",
        clientSlug: "",
        branchName: "",
        branchSlug: "",
        timezone: defaultTimezone,
        phone: "",
        instanceId: "",
        domainSlug: "beauty",
        paymentStatus: "pending",
        providerBindingProvider: "chatflow",
        providerBindingWebhookStatus: "pending",
        providerBindingPaidUntil: "",
        providerBindingOwner: "",
        providerBindingNextRenewalAt: "",
        providerBindingLastRebindAt: "",
        providerBindingRebindRequired: false,
        providerBindingAlertState: "warn",
        providerBindingNotes: "",
        clientDataText: "",
    };
}

export function createProvisioningWizardResetState(defaultTimezone: string): ProvisioningWizardResetState {
    return {
        branchForm: createInitialBranchForm(defaultTimezone),
        branchBootstrap: createInitialBranchBootstrapState(),
        autopilotForm: createInitialAutopilotForm(defaultTimezone),
    };
}

export function buildBranchFormFromBranchData(
    branchData: BranchLike,
    defaultTimezone: string,
): ProvisioningBranchFormState {
    return {
        name: branchData.name ?? "",
        slug: branchData.slug ?? "",
        timezone: branchData.timezone ?? defaultTimezone,
        phone: branchData.phone ?? "",
        instanceId: branchData.instance_id ?? "",
        telegramChatId: branchData.telegram_chat_id ?? "",
        knowledgeTag: branchData.knowledge_tag ?? "",
        workingHours: stringifyOptionalJson(branchData.working_hours),
        bookingSettings: stringifyOptionalJson(branchData.booking_settings),
    };
}

export function resolveNextAgentBranchId(currentBranchId: string, nextBranchId: string | null | undefined): string {
    if (currentBranchId) {
        return currentBranchId;
    }
    return nextBranchId ?? "";
}

export function hydrateBillingFieldsFromJson(input: {
    billingInfo: string;
    billingContract: string;
    billingCurrency: string;
}): { contract: string; currency: string } | null {
    if (!input.billingInfo.trim()) {
        return null;
    }
    if (input.billingContract || input.billingCurrency) {
        return null;
    }
    const parsed = parseOptionalJson(input.billingInfo, "billing_info");
    if (!parsed.value) {
        return null;
    }
    return readBillingInfoPayload(parsed.value as Record<string, unknown>);
}

export function hydrateWorkingHoursFieldsFromJson(input: {
    workingHoursJson: string;
    currentDaysCount: number;
    currentStart: string;
    currentEnd: string;
    orderedDays: string[];
}): { days: string[]; start: string; end: string } | null {
    if (!input.workingHoursJson.trim()) {
        return null;
    }
    if (input.currentDaysCount || input.currentStart || input.currentEnd) {
        return null;
    }
    const parsed = parseOptionalJson(input.workingHoursJson, "working_hours");
    if (!parsed.value) {
        return null;
    }
    return readWorkingHoursPayload(parsed.value as Record<string, unknown>, {
        orderedDays: input.orderedDays,
    });
}

export function hydrateBookingSettingsFieldsFromJson(input: {
    bookingSettingsJson: string;
    currentDefaultDuration: string;
    currentBufferMin: string;
}): { defaultDuration: string; bufferMin: string } | null {
    if (!input.bookingSettingsJson.trim()) {
        return null;
    }
    if (input.currentDefaultDuration || input.currentBufferMin) {
        return null;
    }
    const parsed = parseOptionalJson(input.bookingSettingsJson, "booking_settings");
    if (!parsed.value) {
        return null;
    }
    return readBookingSettingsPayload(parsed.value as Record<string, unknown>);
}

export function buildBillingInfoJsonFromFields(input: {
    contract: string;
    currency: string;
}): { json: string; error?: string } {
    const built = buildBillingInfoPayloadDraft({
        contract: input.contract,
        currency: input.currency,
    });
    if (built.error) {
        return { json: "", error: built.error };
    }
    return { json: built.value ? JSON.stringify(built.value, null, 2) : "" };
}

export function loadBillingInfoFieldsFromJson(input: {
    billingInfo: string;
}): { contract: string; currency: string; error?: string } {
    const parsed = parseOptionalJson(input.billingInfo, "billing_info");
    if (parsed.error) {
        return { contract: "", currency: "", error: parsed.error };
    }
    const payload = (parsed.value ?? {}) as Record<string, unknown>;
    const next = readBillingInfoPayload(payload);
    return { contract: next.contract, currency: next.currency };
}

export function buildWorkingHoursJsonFromFields(input: {
    selectedDays: string[];
    start: string;
    end: string;
}): { json: string; error?: string } {
    const built = buildWorkingHoursPayloadDraft({
        selectedDays: input.selectedDays,
        start: input.start,
        end: input.end,
    });
    if (built.error) {
        return { json: "", error: built.error };
    }
    return { json: built.value ? JSON.stringify(built.value, null, 2) : "" };
}

export function loadWorkingHoursFieldsFromJson(input: {
    workingHoursJson: string;
    orderedDays: string[];
}): { days: string[]; start: string; end: string; error?: string } {
    const parsed = parseOptionalJson(input.workingHoursJson, "working_hours");
    if (parsed.error) {
        return { days: [], start: "", end: "", error: parsed.error };
    }
    const payload = (parsed.value ?? {}) as Record<string, unknown>;
    const next = readWorkingHoursPayload(payload, {
        orderedDays: input.orderedDays,
    });
    return { days: next.days, start: next.start, end: next.end };
}

export function buildBookingSettingsJsonFromFields(input: {
    defaultDuration: string;
    bufferMin: string;
}): { json: string; error?: string } {
    const built = buildBookingSettingsPayloadDraft({
        defaultDuration: input.defaultDuration,
        bufferMin: input.bufferMin,
    });
    if (built.error) {
        return { json: "", error: built.error };
    }
    return { json: built.value ? JSON.stringify(built.value, null, 2) : "" };
}

export function loadBookingSettingsFieldsFromJson(input: {
    bookingSettingsJson: string;
}): { defaultDuration: string; bufferMin: string; error?: string } {
    const parsed = parseOptionalJson(input.bookingSettingsJson, "booking_settings");
    if (parsed.error) {
        return { defaultDuration: "", bufferMin: "", error: parsed.error };
    }
    const payload = (parsed.value ?? {}) as Record<string, unknown>;
    const next = readBookingSettingsPayload(payload);
    return { defaultDuration: next.defaultDuration, bufferMin: next.bufferMin };
}
