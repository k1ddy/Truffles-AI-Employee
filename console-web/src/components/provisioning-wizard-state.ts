import { parseOptionalJson, stringifyOptionalJson } from "@/components/provisioning-wizard-utils";
import { readBillingInfoPayload, readBookingSettingsPayload, readWorkingHoursPayload } from "@/components/provisioning-wizard-json-payloads";

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
