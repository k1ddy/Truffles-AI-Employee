import type { components } from "@/types/api.generated";
import {
    WIZARD_STEPS,
    type CapabilitiesPayload,
    type WizardStepId,
} from "@/components/provisioning-wizard-domain";
import {
    isNonEmptyRecord,
    type OnboardingStepStatusValue,
} from "@/components/provisioning-wizard-utils";

type ProvisioningBranch = components["schemas"]["ConsoleBranch"];
type OnboardingStatus = components["schemas"]["ConsoleOnboardingStatusResponse"];
type OnboardingStepStatus = components["schemas"]["ConsoleOnboardingStepStatus"];

type BuildStepStatusParams = {
    onboardingStatus?: OnboardingStatus | null;
    branchData?: ProvisioningBranch | null;
    createdAgentsCount: number;
    capabilitiesSavedAt?: string | null;
    onboardingContractSavedAt?: string | null;
};

type BuildReadinessItemsParams = {
    branchData?: ProvisioningBranch | null;
    capabilitiesPreview: CapabilitiesPayload;
    bookingEnabled: boolean;
    knowledgeUploadEnabled: boolean;
    documentIngestionValid: boolean;
    hasWorkingHours: boolean;
    hasBookingSettings: boolean;
    specialistsConfirmed: boolean;
    hasOnboardingContractRecord: boolean;
    paymentStatusEffective: string;
    referencePackDomainSlug: string;
    hasActiveReferencePack: boolean;
};

export type WizardStepStateMap = Partial<Record<WizardStepId, OnboardingStepStatus>>;

export type WizardStepStatusMap = Record<WizardStepId, boolean>;

export type OnboardingTimelineItem = {
    id: WizardStepId;
    index: number;
    label: string;
    hint: string;
    status: OnboardingStepStatusValue;
    required: boolean;
    missing: string[];
};

export type ReadinessItem = {
    id: string;
    label: string;
    required: boolean;
    ok: boolean;
};

export function buildStepStateById(onboardingStatus?: OnboardingStatus | null): WizardStepStateMap {
    const map: WizardStepStateMap = {};
    if (onboardingStatus?.steps?.length) {
        onboardingStatus.steps.forEach((step) => {
            map[step.id as WizardStepId] = step;
        });
    }
    return map;
}

export function buildStepStatus({
    onboardingStatus,
    branchData,
    createdAgentsCount,
    capabilitiesSavedAt,
    onboardingContractSavedAt,
}: BuildStepStatusParams): WizardStepStatusMap {
    if (onboardingStatus?.steps?.length) {
        const status: WizardStepStatusMap = {
            branch_draft: false,
            integrations: false,
            team: false,
            telegram: false,
            knowledge: false,
            booking: false,
            go_no_go: false,
        };
        onboardingStatus.steps.forEach((step) => {
            status[step.id as WizardStepId] = step.status === "complete" || step.status === "skipped";
        });
        return status;
    }
    const hasWorkingHours = isNonEmptyRecord(branchData?.working_hours);
    const hasBookingSettings = isNonEmptyRecord(branchData?.booking_settings);
    return {
        branch_draft: !!branchData?.id,
        integrations: !!branchData?.instance_id && !!branchData?.phone,
        team: createdAgentsCount > 0,
        telegram: !!branchData?.telegram_chat_id,
        knowledge: !!branchData?.knowledge_tag,
        booking: hasWorkingHours && hasBookingSettings,
        go_no_go: !!capabilitiesSavedAt || !!onboardingContractSavedAt,
    };
}

export function buildOnboardingTimeline(
    stepStateById: WizardStepStateMap,
    stepStatus: WizardStepStatusMap,
): OnboardingTimelineItem[] {
    return WIZARD_STEPS.map((step, index) => {
        const stepState = stepStateById[step.id];
        const status = normalizeTimelineStatus(stepState?.status, stepStatus[step.id] ? "complete" : "locked");
        return {
            id: step.id,
            index: index + 1,
            label: step.label,
            hint: step.hint,
            status,
            required: stepState?.required ?? true,
            missing: stepState?.missing ?? [],
        };
    });
}

function normalizeTimelineStatus(
    status?: string,
    fallback: OnboardingStepStatusValue = "locked",
): OnboardingStepStatusValue {
    if (status === "complete" || status === "available" || status === "locked" || status === "skipped") {
        return status;
    }
    return fallback;
}

export function buildReadinessItems({
    branchData,
    capabilitiesPreview,
    bookingEnabled,
    knowledgeUploadEnabled,
    documentIngestionValid,
    hasWorkingHours,
    hasBookingSettings,
    specialistsConfirmed,
    hasOnboardingContractRecord,
    paymentStatusEffective,
    referencePackDomainSlug,
    hasActiveReferencePack,
}: BuildReadinessItemsParams): ReadinessItem[] {
    return [
        {
            id: "wa_instance",
            label: "WhatsApp instance_id",
            required: capabilitiesPreview.channels?.whatsapp === true,
            ok: !!branchData?.instance_id,
        },
        {
            id: "wa_active",
            label: "Филиал активен",
            required: capabilitiesPreview.channels?.whatsapp === true,
            ok: !!branchData?.is_active,
        },
        {
            id: "tg_chat",
            label: "Telegram chat_id",
            required: capabilitiesPreview.channels?.telegram === true,
            ok: !!branchData?.telegram_chat_id,
        },
        {
            id: "knowledge_tag",
            label: "Knowledge tag",
            required: knowledgeUploadEnabled,
            ok: !!branchData?.knowledge_tag,
        },
        {
            id: "document_ingestion",
            label: "Document ingestion gate",
            required: knowledgeUploadEnabled,
            ok: knowledgeUploadEnabled ? documentIngestionValid : true,
        },
        {
            id: "booking_hours",
            label: "Working hours",
            required: bookingEnabled,
            ok: hasWorkingHours,
        },
        {
            id: "booking_settings",
            label: "Booking settings",
            required: bookingEnabled,
            ok: hasBookingSettings,
        },
        {
            id: "booking_specialists",
            label: "Specialists подтверждены",
            required: bookingEnabled,
            ok: specialistsConfirmed,
        },
        {
            id: "onboarding_contract",
            label: "Onboarding contract",
            required: true,
            ok: hasOnboardingContractRecord,
        },
        {
            id: "payment_confirmed",
            label: "Payment confirmed",
            required: true,
            ok: paymentStatusEffective === "confirmed",
        },
        {
            id: "reference_pack",
            label: "Reference pack active",
            required: true,
            ok: referencePackDomainSlug.length > 0 && hasActiveReferencePack,
        },
    ];
}
