"use client";

import { useMemo } from "react";
import type { TenantsFilterOption } from "@/components/TenantsTopControls";
import type { components } from "@/types/api.generated";

type ConsoleCompany = components["schemas"]["ConsoleCompany"];
type ConsoleClient = components["schemas"]["ConsoleClient"];
type ConsoleBranch = components["schemas"]["ConsoleBranch"];

type KnownCompany = Pick<ConsoleCompany, "id" | "name">;
type KnownClient = Pick<ConsoleClient, "id" | "name" | "company_id">;
type KnownBranch = Pick<ConsoleBranch, "id" | "name" | "slug"> & {
    client_id?: string | null;
    company_id?: string | null;
};

type UseTenantsScopeDerivedStateParams = {
    companies: ConsoleCompany[];
    clients: ConsoleClient[];
    branches: ConsoleBranch[];
    knownCompanies: KnownCompany[];
    knownClients: KnownClient[];
    knownBranches: KnownBranch[];
    selectedCompanyId: string | null;
    selectedClientId: string | null;
    selectedBranchId: string | null;
    meClientId: string | null;
    meClientName: string | null;
};

function normalizeOptionalId(value: string | null | undefined): string | null {
    const normalized = (value ?? "").trim();
    return normalized.length > 0 ? normalized : null;
}

function readBranchClientId(branch: ConsoleBranch | KnownBranch): string | null {
    return normalizeOptionalId(branch.client_id);
}

function readBranchCompanyId(branch: ConsoleBranch | KnownBranch): string | null {
    return normalizeOptionalId(branch.company_id);
}

function toFilterOptions(
    values: Array<{ id: string | null | undefined; label: string | null | undefined }>,
): TenantsFilterOption[] {
    const unique = new Map<string, string>();
    values.forEach((item) => {
        if (!item.id) {
            return;
        }
        const normalizedLabel = (item.label ?? "").trim();
        if (!unique.has(item.id)) {
            unique.set(item.id, normalizedLabel || item.id);
        }
    });
    return [...unique.entries()]
        .map(([id, label]) => ({ id, label }))
        .sort((left, right) => left.label.localeCompare(right.label, "ru"));
}

export function useTenantsScopeDerivedState({
    companies,
    clients,
    branches,
    knownCompanies,
    knownClients,
    knownBranches,
    selectedCompanyId,
    selectedClientId,
    selectedBranchId,
    meClientId,
    meClientName,
}: UseTenantsScopeDerivedStateParams) {
    const selectedCompanyNameFromContext = useMemo(() => {
        if (!selectedCompanyId) {
            return null;
        }
        return knownCompanies.find((company) => company.id === selectedCompanyId)?.name ?? null;
    }, [knownCompanies, selectedCompanyId]);

    const selectedBranchNameFromContext = useMemo(() => {
        if (!selectedBranchId) {
            return null;
        }
        return knownBranches.find((branch) => branch.id === selectedBranchId)?.name ?? null;
    }, [knownBranches, selectedBranchId]);

    const clientCompanyIdById = useMemo(() => {
        const mapping = new Map<string, string>();
        clients.forEach((client) => {
            if (client.id && client.company_id) {
                mapping.set(client.id, client.company_id);
            }
        });
        knownClients.forEach((client) => {
            if (client.id && client.company_id && !mapping.has(client.id)) {
                mapping.set(client.id, client.company_id);
            }
        });
        return mapping;
    }, [clients, knownClients]);

    const branchClientIdById = useMemo(() => {
        const mapping = new Map<string, string>();
        branches.forEach((branch) => {
            if (branch.id) {
                const clientId = readBranchClientId(branch);
                if (clientId) {
                    mapping.set(branch.id, clientId);
                }
            }
        });
        knownBranches.forEach((branch) => {
            if (branch.id && !mapping.has(branch.id)) {
                const clientId = readBranchClientId(branch);
                if (clientId) {
                    mapping.set(branch.id, clientId);
                }
            }
        });
        return mapping;
    }, [branches, knownBranches]);

    const branchCompanyIdById = useMemo(() => {
        const mapping = new Map<string, string>();
        branches.forEach((branch) => {
            if (branch.id) {
                const companyId = readBranchCompanyId(branch);
                if (companyId) {
                    mapping.set(branch.id, companyId);
                }
            }
        });
        knownBranches.forEach((branch) => {
            if (branch.id && !mapping.has(branch.id)) {
                const companyId = readBranchCompanyId(branch);
                if (companyId) {
                    mapping.set(branch.id, companyId);
                }
            }
        });
        return mapping;
    }, [branches, knownBranches]);

    const selectedCompanyName = useMemo(() => {
        if (!selectedCompanyId) {
            return null;
        }
        return (
            companies.find((company) => company.id === selectedCompanyId)?.name
            ?? selectedCompanyNameFromContext
            ?? null
        );
    }, [companies, selectedCompanyId, selectedCompanyNameFromContext]);

    const selectedClientName = useMemo(() => {
        if (!selectedClientId) {
            return null;
        }
        if (meClientId === selectedClientId && meClientName) {
            return meClientName;
        }
        return clients.find((client) => client.id === selectedClientId)?.name ?? null;
    }, [clients, meClientId, meClientName, selectedClientId]);

    const selectedBranchName = useMemo(() => {
        if (!selectedBranchId) {
            return null;
        }
        return (
            branches.find((branch) => branch.id === selectedBranchId)?.name
            ?? selectedBranchNameFromContext
            ?? null
        );
    }, [branches, selectedBranchId, selectedBranchNameFromContext]);

    const pageFilterCompanyOptions = useMemo(
        () => toFilterOptions([
            ...knownCompanies.map((company) => ({
                id: company.id,
                label: company.name ?? company.id ?? "",
            })),
            ...companies.map((company) => ({
                id: company.id,
                label: company.name ?? company.id ?? "",
            })),
            {
                id: selectedCompanyId,
                label: selectedCompanyNameFromContext ?? selectedCompanyId ?? "",
            },
        ]),
        [knownCompanies, companies, selectedCompanyId, selectedCompanyNameFromContext],
    );

    const pageFilterClientOptions = useMemo(
        () => toFilterOptions([
            ...clients.map((client) => ({
                id: client.id,
                label: client.name ?? client.slug ?? client.id ?? "",
            })),
            {
                id: meClientId,
                label: meClientName ?? meClientId ?? "",
            },
            {
                id: selectedClientId,
                label: selectedClientName ?? selectedClientId ?? "",
            },
        ]),
        [clients, meClientId, meClientName, selectedClientId, selectedClientName],
    );

    const pageFilterBranchOptions = useMemo(() => {
        const branchItems = branches.map((branch) => ({
            id: branch.id,
            label: branch.name ?? branch.slug ?? branch.id ?? "",
        }));
        return toFilterOptions([
            ...knownBranches.map((branch) => ({
                id: branch.id,
                label: branch.name ?? branch.id ?? "",
            })),
            ...branchItems,
            {
                id: selectedBranchId,
                label: selectedBranchNameFromContext ?? selectedBranchId ?? "",
            },
        ]);
    }, [branches, knownBranches, selectedBranchId, selectedBranchNameFromContext]);

    return {
        clientCompanyIdById,
        branchClientIdById,
        branchCompanyIdById,
        selectedCompanyName,
        selectedClientName,
        selectedBranchName,
        pageFilterCompanyOptions,
        pageFilterClientOptions,
        pageFilterBranchOptions,
    };
}
