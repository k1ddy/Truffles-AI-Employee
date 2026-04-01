import type { components } from "@/types/api.generated";
import { parseOptionalJson } from "@/components/provisioning-wizard-utils";
import { buildBillingInfoJsonFromFields } from "@/components/provisioning-wizard-state";

type ConsoleCompanyCreateRequest = components["schemas"]["ConsoleCompanyCreateRequest"];
type ConsoleClientCreateRequest = components["schemas"]["ConsoleClientCreateRequest"];
type ConsoleAgentCreateRequest = components["schemas"]["ConsoleAgentCreateRequest"];

type ActionResult<T> = {
    error?: string;
    payload?: T;
};

type CreateCompanyResult = ActionResult<ConsoleCompanyCreateRequest> & {
    nextBillingInfoJson?: string;
};

export function buildCreateCompanyPayload(input: {
    companyName: string;
    billingInfoJson: string;
    billingContract: string;
    billingCurrency: string;
}): CreateCompanyResult {
    const name = input.companyName.trim();
    if (!name) {
        return { error: "Укажите название компании" };
    }

    const builtBilling = buildBillingInfoJsonFromFields({
        contract: input.billingContract,
        currency: input.billingCurrency,
    });
    if (builtBilling.error) {
        return { error: builtBilling.error };
    }

    const billing = parseOptionalJson(input.billingInfoJson, "billing_info");
    if (billing.error) {
        return { error: billing.error };
    }

    let billingPayload = billing.value;
    let nextBillingInfoJson: string | undefined;
    if (!billingPayload && builtBilling.json) {
        const builtParsed = parseOptionalJson(builtBilling.json, "billing_info");
        if (builtParsed.error) {
            return { error: builtParsed.error };
        }
        billingPayload = builtParsed.value;
        if (billingPayload) {
            nextBillingInfoJson = builtBilling.json;
        }
    }

    return {
        payload: {
            name,
            billing_info: (billingPayload as Record<string, never> | undefined) ?? undefined,
        },
        nextBillingInfoJson,
    };
}

export function buildCreateClientPayload(input: {
    clientSlug: string;
    companyId: string;
}): ActionResult<ConsoleClientCreateRequest> {
    const slug = input.clientSlug.trim();
    if (!slug) {
        return { error: "Укажите slug клиента" };
    }
    const companyId = input.companyId.trim();
    if (!companyId) {
        return { error: "Укажите company_id компании" };
    }

    return {
        payload: {
            slug,
            company_id: companyId,
            status: null,
        },
    };
}

export function buildCreateAgentPayload(input: {
    clientId: string;
    role: ConsoleAgentCreateRequest["role"];
    name: string;
    oidcSubject: string;
    selectedBranchId?: string | null;
    fallbackBranchId?: string | null;
}): ActionResult<ConsoleAgentCreateRequest> {
    if (!input.clientId) {
        return { error: "Укажите client_id" };
    }

    const payload: ConsoleAgentCreateRequest = {
        client_id: input.clientId,
        role: input.role,
        name: input.name.trim() || undefined,
        oidc_subject: input.oidcSubject.trim() || undefined,
        is_active: true,
        sso_temp_password: null,
    };

    if (input.role === "manager") {
        const branchId = input.selectedBranchId || input.fallbackBranchId;
        if (!branchId) {
            return { error: "branch_id обязателен для manager" };
        }
        payload.branch_id = branchId;
    }

    return { payload };
}
