import type { components } from "@/types/api.generated";
import type { ProvisioningAutopilotFormState } from "@/components/provisioning-wizard-state";

type OnboardingAutopilotRequest = components["schemas"]["ConsoleOnboardingAutopilotRequest"];
type OnboardingPurchasedService = NonNullable<OnboardingAutopilotRequest["purchased_services"]>[number];

type DeriveAutopilotStateInput = {
    form: ProvisioningAutopilotFormState;
    companyId: string;
    clientId: string;
    branchId?: string;
    purchasedServices: OnboardingPurchasedService[];
};

export type DerivedAutopilotState = {
    phone: string;
    instanceId: string;
    companyRef: string;
    clientRef: string;
    branchName: string;
    clientDataText: string;
    providerBindingProvider: string;
    providerBindingPaidUntil: string;
    providerBindingOwner: string;
    providerBindingNextRenewalAt: string;
    providerBindingLastRebindAt: string;
    needsBranchName: boolean;
    missingInputs: string[];
};

type BuildRunAutopilotPayloadInput = {
    form: ProvisioningAutopilotFormState;
    companyId: string;
    clientId: string;
    branchId?: string;
    canManagePayment: boolean;
    purchasedServices: OnboardingPurchasedService[];
    derived?: DerivedAutopilotState;
};

type BuildAutopilotRunStateInput = {
    canEdit: boolean;
    isPending: boolean;
    branchId?: string;
    scorecardFailed: boolean;
    missingInputs: string[];
};

type BuildAutopilotRunValidationErrorInput = {
    missingInputs: string[];
    blockedByScorecard: boolean;
    scorecardMissingLabels: string[];
};

export type AutopilotRunState = {
    missingInputs: string[];
    blockedByScorecard: boolean;
    canRun: boolean;
};

export function deriveAutopilotState(input: DeriveAutopilotStateInput): DerivedAutopilotState {
    const phone = input.form.phone.trim();
    const instanceId = input.form.instanceId.trim();
    const companyRef = input.companyId.trim() || input.form.companyName.trim();
    const clientRef = input.clientId.trim() || input.form.clientSlug.trim();
    const needsBranchName = !input.branchId;
    const branchName = input.form.branchName.trim();
    const clientDataText = input.form.clientDataText.trim();
    const providerBindingProvider = input.form.providerBindingProvider.trim();
    const providerBindingPaidUntil = input.form.providerBindingPaidUntil.trim();
    const providerBindingOwner = input.form.providerBindingOwner.trim();
    const providerBindingNextRenewalAt = input.form.providerBindingNextRenewalAt.trim();
    const providerBindingLastRebindAt = input.form.providerBindingLastRebindAt.trim();

    const missingInputs: string[] = [];
    if (!phone) {
        missingInputs.push("phone");
    }
    if (!instanceId) {
        missingInputs.push("instance_id");
    }
    if (!companyRef) {
        missingInputs.push("company_id или company_name");
    }
    if (!clientRef) {
        missingInputs.push("client_id или client_slug");
    }
    if (needsBranchName && !branchName) {
        missingInputs.push("branch_name (для нового branch)");
    }
    if (!input.purchasedServices.length) {
        missingInputs.push("минимум 1 подключённая услуга");
    }
    if (!clientDataText) {
        missingInputs.push("client_data_text");
    }
    if (input.purchasedServices.includes("whatsapp")) {
        if (!providerBindingProvider) {
            missingInputs.push("provider_binding.provider");
        }
        if (!input.form.providerBindingWebhookStatus) {
            missingInputs.push("provider_binding.webhook_status");
        }
        if (!providerBindingOwner) {
            missingInputs.push("provider_binding.owner");
        }
        if (!providerBindingPaidUntil && !providerBindingNextRenewalAt) {
            missingInputs.push("provider_binding.next_renewal_at | paid_until");
        }
    }

    return {
        phone,
        instanceId,
        companyRef,
        clientRef,
        branchName,
        clientDataText,
        providerBindingProvider,
        providerBindingPaidUntil,
        providerBindingOwner,
        providerBindingNextRenewalAt,
        providerBindingLastRebindAt,
        needsBranchName,
        missingInputs,
    };
}

export function toggleAutopilotServiceSelection(
    selected: OnboardingPurchasedService[],
    serviceId: OnboardingPurchasedService,
): OnboardingPurchasedService[] {
    return selected.includes(serviceId)
        ? selected.filter((item) => item !== serviceId)
        : [...selected, serviceId];
}

export function buildAutopilotRunState(input: BuildAutopilotRunStateInput): AutopilotRunState {
    const blockedByScorecard = Boolean(input.branchId && input.scorecardFailed);
    const canRun = input.canEdit
        && !input.isPending
        && input.missingInputs.length === 0
        && !blockedByScorecard;
    return {
        missingInputs: input.missingInputs,
        blockedByScorecard,
        canRun,
    };
}

export function buildAutopilotRunValidationError(input: BuildAutopilotRunValidationErrorInput): string | null {
    if (input.missingInputs.length > 0) {
        return `Не хватает данных: ${input.missingInputs.join(", ")}`;
    }
    if (input.blockedByScorecard) {
        return `Автопроцесс заблокирован scorecard: ${input.scorecardMissingLabels.join(", ") || "есть незавершенные проверки"}`;
    }
    return null;
}

export function buildRunAutopilotPayload(input: BuildRunAutopilotPayloadInput): OnboardingAutopilotRequest {
    const derived = input.derived ?? deriveAutopilotState({
        form: input.form,
        companyId: input.companyId,
        clientId: input.clientId,
        branchId: input.branchId,
        purchasedServices: input.purchasedServices,
    });
    return {
        company_id: input.companyId.trim() || undefined,
        company_name: input.form.companyName.trim() || undefined,
        client_id: input.clientId.trim() || undefined,
        client_slug: input.form.clientSlug.trim() || undefined,
        branch_id: input.branchId || undefined,
        branch_slug: input.form.branchSlug.trim() || undefined,
        branch_name: input.form.branchName.trim() || undefined,
        timezone: input.form.timezone.trim() || undefined,
        phone: derived.phone,
        instance_id: derived.instanceId,
        payment_status: input.canManagePayment ? input.form.paymentStatus : "pending",
        domain_slug: input.form.domainSlug.trim() || undefined,
        purchased_services: input.purchasedServices.length ? input.purchasedServices : undefined,
        provider_binding: input.purchasedServices.includes("whatsapp")
            ? {
                whatsapp: {
                    provider: derived.providerBindingProvider || null,
                    instance_id: derived.instanceId,
                    webhook_status: input.form.providerBindingWebhookStatus || null,
                    paid_until: derived.providerBindingPaidUntil || null,
                    owner: derived.providerBindingOwner || null,
                    next_renewal_at: derived.providerBindingNextRenewalAt || null,
                    last_rebind_at: derived.providerBindingLastRebindAt || null,
                    rebind_required: input.form.providerBindingRebindRequired,
                    alert_state: input.form.providerBindingAlertState || null,
                    notes: input.form.providerBindingNotes.trim() || null,
                },
            }
            : undefined,
        client_data_text: derived.clientDataText || undefined,
        activate_branch: false,
        auto_create_reference_pack: true,
        auto_publish_knowledge: false,
    };
}
