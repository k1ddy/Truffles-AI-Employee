import type { components } from "@/types/api.generated";

type RawCapabilitiesPayload = components["schemas"]["CapabilitiesPayload-Output"];
type CapabilitiesPayload = RawCapabilitiesPayload & {
    channels: NonNullable<RawCapabilitiesPayload["channels"]>;
    providers: NonNullable<RawCapabilitiesPayload["providers"]>;
    features: NonNullable<RawCapabilitiesPayload["features"]>;
};
type OnboardingContractPayload = components["schemas"]["OnboardingContractPayload-Input"];

type OnboardingStepStatusValue = "complete" | "available" | "locked" | "skipped";

export function stringifyOptionalJson(value: unknown): string {
    if (!value || typeof value !== "object") {
        return "";
    }
    const keys = Object.keys(value as Record<string, unknown>);
    if (keys.length === 0) {
        return "";
    }
    return JSON.stringify(value, null, 2);
}

export function parseOptionalJson(value: string, label: string): { value?: Record<string, unknown>; error?: string } {
    const trimmed = value.trim();
    if (!trimmed) {
        return {};
    }
    try {
        return { value: JSON.parse(trimmed) as Record<string, unknown> };
    } catch {
        return { error: `${label}: некорректный JSON` };
    }
}

export function onboardingStepStatusLabel(status: OnboardingStepStatusValue): string {
    if (status === "complete") {
        return "выполнен";
    }
    if (status === "available") {
        return "доступен";
    }
    if (status === "locked") {
        return "заблокирован";
    }
    return "пропущен";
}

export function onboardingStepStatusClass(status: OnboardingStepStatusValue): string {
    if (status === "complete") {
        return "border-green-200 bg-green-50 text-green-800";
    }
    if (status === "available") {
        return "border-blue-200 bg-blue-50 text-blue-800";
    }
    if (status === "locked") {
        return "border-border/60 bg-muted/40 text-muted-foreground";
    }
    return "border-amber-200 bg-amber-50 text-amber-800";
}

export function intakePriorityLabel(value?: string): string {
    if (value === "critical") {
        return "critical";
    }
    if (value === "high") {
        return "high";
    }
    if (value === "medium") {
        return "medium";
    }
    return "low";
}

export function intakePriorityClass(value?: string): string {
    if (value === "critical") {
        return "border-destructive/30 bg-destructive/10 text-destructive";
    }
    if (value === "high") {
        return "border-amber-300/60 bg-amber-50 text-amber-800";
    }
    if (value === "medium") {
        return "border-blue-300/60 bg-blue-50 text-blue-800";
    }
    return "border-border/60 bg-muted/40 text-muted-foreground";
}

export function intakeStatusLabel(value?: string): string {
    if (value === "confirmed") {
        return "confirmed";
    }
    if (value === "assumed") {
        return "assumed";
    }
    return "unknown";
}

export function intakeStatusClass(value?: string): string {
    if (value === "confirmed") {
        return "border-green-200 bg-green-50 text-green-800";
    }
    if (value === "assumed") {
        return "border-blue-300/60 bg-blue-50 text-blue-800";
    }
    return "border-border/60 bg-muted/40 text-muted-foreground";
}

export function qualityStatusLabel(value?: string): string {
    if (value === "pass") {
        return "pass";
    }
    if (value === "warn") {
        return "warn";
    }
    if (value === "skip") {
        return "skip";
    }
    return "fail";
}

export function qualityStatusClass(value?: string): string {
    if (value === "pass") {
        return "border-green-200 bg-green-50 text-green-800";
    }
    if (value === "warn") {
        return "border-amber-300/60 bg-amber-50 text-amber-800";
    }
    if (value === "skip") {
        return "border-blue-300/60 bg-blue-50 text-blue-800";
    }
    return "border-destructive/30 bg-destructive/10 text-destructive";
}

export function normalizeCapabilities(payload?: RawCapabilitiesPayload | null): CapabilitiesPayload {
    return {
        domain_slug: payload?.domain_slug ?? null,
        channels: {
            whatsapp: payload?.channels?.whatsapp ?? null,
            telegram: payload?.channels?.telegram ?? null,
            instagram: payload?.channels?.instagram ?? null,
        },
        providers: {
            availability_provider: payload?.providers?.availability_provider ?? null,
            crm_provider: payload?.providers?.crm_provider ?? null,
            calendar_provider: payload?.providers?.calendar_provider ?? null,
        },
        features: {
            booking_mode: payload?.features?.booking_mode ?? null,
            knowledge_upload: payload?.features?.knowledge_upload ?? null,
            analytics: payload?.features?.analytics ?? null,
            auto_learn: payload?.features?.auto_learn ?? null,
        },
    };
}

export function normalizeOnboardingContractPayload(
    payload?: OnboardingContractPayload | null,
): OnboardingContractPayload {
    return {
        domain_slug: payload?.domain_slug ?? null,
        purchased: normalizeCapabilities(payload?.purchased ?? null),
        provider_binding: {
            whatsapp: {
                provider: payload?.provider_binding?.whatsapp?.provider ?? null,
                instance_id: payload?.provider_binding?.whatsapp?.instance_id ?? null,
                webhook_status: payload?.provider_binding?.whatsapp?.webhook_status ?? null,
                paid_until: payload?.provider_binding?.whatsapp?.paid_until ?? null,
                owner: payload?.provider_binding?.whatsapp?.owner ?? null,
                next_renewal_at: payload?.provider_binding?.whatsapp?.next_renewal_at ?? null,
                last_rebind_at: payload?.provider_binding?.whatsapp?.last_rebind_at ?? null,
                rebind_required: payload?.provider_binding?.whatsapp?.rebind_required ?? null,
                alert_state: payload?.provider_binding?.whatsapp?.alert_state ?? null,
                notes: payload?.provider_binding?.whatsapp?.notes ?? null,
            },
        },
    };
}

export function mergeCapabilities(base?: RawCapabilitiesPayload | null, override?: RawCapabilitiesPayload | null): CapabilitiesPayload {
    const merged = normalizeCapabilities(base);
    const overridePayload = normalizeCapabilities(override);

    if (overridePayload.domain_slug) {
        merged.domain_slug = overridePayload.domain_slug;
    }

    (["whatsapp", "telegram", "instagram"] as const).forEach((key) => {
        const value = overridePayload.channels?.[key];
        if (value !== null && value !== undefined) {
            merged.channels[key] = value;
        }
    });

    const availabilityProvider = overridePayload.providers?.availability_provider;
    if (availabilityProvider !== null && availabilityProvider !== undefined) {
        merged.providers.availability_provider = availabilityProvider;
    }

    const crmProvider = overridePayload.providers?.crm_provider;
    if (crmProvider !== null && crmProvider !== undefined) {
        merged.providers.crm_provider = crmProvider;
    }

    const calendarProvider = overridePayload.providers?.calendar_provider;
    if (calendarProvider !== null && calendarProvider !== undefined) {
        merged.providers.calendar_provider = calendarProvider;
    }

    const bookingMode = overridePayload.features?.booking_mode;
    if (bookingMode !== null && bookingMode !== undefined) {
        merged.features.booking_mode = bookingMode;
    }

    const knowledgeUpload = overridePayload.features?.knowledge_upload;
    if (knowledgeUpload !== null && knowledgeUpload !== undefined) {
        merged.features.knowledge_upload = knowledgeUpload;
    }

    const analytics = overridePayload.features?.analytics;
    if (analytics !== null && analytics !== undefined) {
        merged.features.analytics = analytics;
    }

    const autoLearn = overridePayload.features?.auto_learn;
    if (autoLearn !== null && autoLearn !== undefined) {
        merged.features.auto_learn = autoLearn;
    }

    return merged;
}

export function toTriState(value: boolean | null | undefined): string {
    if (value === true) {
        return "true";
    }
    if (value === false) {
        return "false";
    }
    return "inherit";
}

export function fromTriState(value: string): boolean | null {
    if (value === "true") {
        return true;
    }
    if (value === "false") {
        return false;
    }
    return null;
}

export function formatEffectiveValue(value: string | number | boolean | null | undefined): string {
    if (value === true) {
        return "Включено";
    }
    if (value === false) {
        return "Выключено";
    }
    if (value === null || value === undefined || value === "") {
        return "—";
    }
    return String(value);
}

export function isNonEmptyRecord(value: unknown): value is Record<string, unknown> {
    if (!value || typeof value !== "object") {
        return false;
    }
    return Object.keys(value as Record<string, unknown>).length > 0;
}

function hasCapabilityValue(value: boolean | string | null | undefined): boolean {
    return value !== null && value !== undefined && value !== "";
}

export function hasPurchasedSignal(payload: CapabilitiesPayload): boolean {
    return [
        payload.domain_slug,
        payload.channels.whatsapp,
        payload.channels.telegram,
        payload.channels.instagram,
        payload.providers.availability_provider,
        payload.providers.crm_provider,
        payload.providers.calendar_provider,
        payload.features.booking_mode,
        payload.features.knowledge_upload,
        payload.features.analytics,
        payload.features.auto_learn,
    ].some((value) => hasCapabilityValue(value));
}
