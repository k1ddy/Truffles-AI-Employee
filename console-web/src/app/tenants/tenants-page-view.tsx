"use client";

import type { ComponentProps } from "react";
import type { Session } from "next-auth";
import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";
import TenantsActionQueuePanel, { type TenantsActionQueueItem } from "@/components/TenantsActionQueuePanel";
import TenantsBranchChangeManagementPanel from "@/components/TenantsBranchChangeManagementPanel";
import TenantsClientLifecycleModal from "@/components/TenantsClientLifecycleModal";
import TenantsClientsPanel from "@/components/TenantsClientsPanel";
import TenantsDecommissionPanel from "@/components/TenantsDecommissionPanel";
import TenantsFleetAttentionPanel from "@/components/TenantsFleetAttentionPanel";
import TenantsOperationalKpiPanel from "@/components/TenantsOperationalKpiPanel";
import TenantsPortfolioCompaniesPanel from "@/components/TenantsPortfolioCompaniesPanel";
import TenantsQuickCreatePanel from "@/components/TenantsQuickCreatePanel";
import TenantsScopedErrorSummary from "@/components/TenantsScopedErrorSummary";
import TenantsTopControls from "@/components/TenantsTopControls";

type TenantLifecycleMode = "active" | "archived" | "all";

type TenantsPageViewProps<TActionItem extends TenantsActionQueueItem> = {
    session: Session | null;
    meLoading: boolean;
    canReadTenants: boolean;
    canWriteTenants: boolean;
    controlTowerEnabled: boolean;
    tenantLifecycle: TenantLifecycleMode;
    onTenantLifecycleChange: (mode: TenantLifecycleMode) => void;
    topControlsProps: ComponentProps<typeof TenantsTopControls>;
    scopedErrorSummaryProps: ComponentProps<typeof TenantsScopedErrorSummary>;
    quickCreatePanelProps: ComponentProps<typeof TenantsQuickCreatePanel>;
    actionQueue: {
        show: boolean;
        items: TActionItem[];
        refreshing: boolean;
        onRefresh: () => void;
        onRunIntent: (item: TActionItem) => void;
        onSetClientContext: (clientId: string, companyId?: string | null) => void;
    };
    operationalKpiPanel: {
        show: boolean;
        props: ComponentProps<typeof TenantsOperationalKpiPanel>;
    };
    fleetAttentionPanel: {
        show: boolean;
        props: ComponentProps<typeof TenantsFleetAttentionPanel>;
    };
    portfolioCompaniesPanel: {
        show: boolean;
        props: ComponentProps<typeof TenantsPortfolioCompaniesPanel>;
    };
    decommissionPanel: {
        show: boolean;
        props: ComponentProps<typeof TenantsDecommissionPanel>;
    };
    clientsPanel: {
        show: boolean;
        props: ComponentProps<typeof TenantsClientsPanel>;
    };
    branchChangePanel: {
        show: boolean;
        props: ComponentProps<typeof TenantsBranchChangeManagementPanel>;
    };
    lifecycleModalProps: ComponentProps<typeof TenantsClientLifecycleModal>;
    showOnboarding: boolean;
    onOpenWorkspaceFromOnboarding: () => void;
};

export default function TenantsPageView<TActionItem extends TenantsActionQueueItem>({
    session,
    meLoading,
    canReadTenants,
    canWriteTenants,
    controlTowerEnabled,
    tenantLifecycle,
    onTenantLifecycleChange,
    topControlsProps,
    scopedErrorSummaryProps,
    quickCreatePanelProps,
    actionQueue,
    operationalKpiPanel,
    fleetAttentionPanel,
    portfolioCompaniesPanel,
    decommissionPanel,
    clientsPanel,
    branchChangePanel,
    lifecycleModalProps,
    showOnboarding,
    onOpenWorkspaceFromOnboarding,
}: TenantsPageViewProps<TActionItem>) {
    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра вкладки «Тенанты».
            </div>
        );
    }

    if (meLoading) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Загрузка роли...
            </div>
        );
    }

    if (!canReadTenants) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к вкладке Тенанты." />
        );
    }

    return (
        <div className="max-w-5xl mx-auto p-6" data-testid="tenants-page">
            <div className="flex flex-col gap-2 mb-6">
                {!controlTowerEnabled ? (
                    <div className="rounded-lg border border-amber-300/60 bg-amber-50 p-3 text-xs text-amber-900" data-testid="tenants-control-tower-flag-banner">
                        Включён базовый режим Tenants: доступен обзор портфеля и управление контекстом.
                    </div>
                ) : null}
                <TenantsTopControls {...topControlsProps} />
                <TenantsScopedErrorSummary {...scopedErrorSummaryProps} />
                {canWriteTenants ? (
                    <TenantsQuickCreatePanel {...quickCreatePanelProps} />
                ) : null}
                {actionQueue.show ? (
                    <TenantsActionQueuePanel
                        items={actionQueue.items}
                        refreshing={actionQueue.refreshing}
                        onRefresh={actionQueue.onRefresh}
                        onRunIntent={actionQueue.onRunIntent}
                        onSetClientContext={actionQueue.onSetClientContext}
                    />
                ) : null}
                <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-xs text-muted-foreground">Режим списка:</span>
                    <button
                        className={tenantLifecycle === "active" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onTenantLifecycleChange("active")}
                    >
                        Активные
                    </button>
                    <button
                        className={tenantLifecycle === "archived" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onTenantLifecycleChange("archived")}
                    >
                        Архив
                    </button>
                    <button
                        className={tenantLifecycle === "all" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onTenantLifecycleChange("all")}
                    >
                        Все
                    </button>
                </div>
            </div>

            <div className="grid gap-6">
                {operationalKpiPanel.show ? (
                    <TenantsOperationalKpiPanel {...operationalKpiPanel.props} />
                ) : null}

                {fleetAttentionPanel.show ? (
                    <TenantsFleetAttentionPanel {...fleetAttentionPanel.props} />
                ) : null}

                {portfolioCompaniesPanel.show ? (
                    <TenantsPortfolioCompaniesPanel {...portfolioCompaniesPanel.props} />
                ) : null}

                {decommissionPanel.show ? (
                    <TenantsDecommissionPanel {...decommissionPanel.props} />
                ) : null}

                {clientsPanel.show ? (
                    <TenantsClientsPanel {...clientsPanel.props} />
                ) : null}

                {branchChangePanel.show ? (
                    <TenantsBranchChangeManagementPanel {...branchChangePanel.props} />
                ) : null}
            </div>

            <TenantsClientLifecycleModal {...lifecycleModalProps} />

            {showOnboarding ? (
                <div className="mt-10" data-testid="tenants-onboarding-section">
                    <div className="mb-3 rounded-lg border border-blue-300/60 bg-blue-50 p-3 text-xs text-blue-900">
                        Канонический execution-flow: выполняйте remediation и go-live в `Company Workspace`.
                        <button
                            className="btn-ghost ml-2"
                            onClick={onOpenWorkspaceFromOnboarding}
                            data-testid="tenants-open-workspace-from-onboarding"
                        >
                            Открыть Workspace
                        </button>
                    </div>
                    <ProvisioningWizard session={session} accessSection="tenants" />
                </div>
            ) : null}
        </div>
    );
}
