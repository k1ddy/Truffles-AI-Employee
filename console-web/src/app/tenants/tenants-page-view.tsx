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
    onOpenOpsFromOnboarding: () => void;
};

export default function TenantsPageView<TActionItem extends TenantsActionQueueItem>({
    session,
    meLoading,
    canReadTenants,
    canWriteTenants,
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
    onOpenOpsFromOnboarding,
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
                <div className="flex flex-wrap items-center gap-2 pt-1" data-testid="tenants-lifecycle-controls">
                    <span className="text-xs text-muted-foreground">Режим списка:</span>
                    <button
                        className={tenantLifecycle === "active" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onTenantLifecycleChange("active")}
                        data-testid="tenants-lifecycle-active"
                    >
                        Активные
                    </button>
                    <button
                        className={tenantLifecycle === "archived" ? "btn-primary" : "btn-ghost"}
                        onClick={() => onTenantLifecycleChange("archived")}
                        data-testid="tenants-lifecycle-archived"
                    >
                        Архив
                    </button>
                </div>
                <div className="rounded-lg border border-emerald-300/60 bg-emerald-50 p-3 text-xs text-emerald-900" data-testid="tenants-intent-map">
                    Роль вкладки: <span className="font-semibold">факт и приоритизация</span>. Выбираем задачу здесь, выполняем действие в Workspace, затем сверяем результат в Ops.
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
                        Канонический рабочий поток: действия по исправлению и допуску к запуску выполняйте в `Company Workspace`.
                        <button
                            className="btn-ghost ml-2"
                            onClick={onOpenWorkspaceFromOnboarding}
                            data-testid="tenants-open-workspace-from-onboarding"
                        >
                            Открыть Workspace
                        </button>
                        <button
                            className="btn-ghost ml-2"
                            onClick={onOpenOpsFromOnboarding}
                            data-testid="tenants-onboarding-open-ops"
                        >
                            Открыть Ops
                        </button>
                        <div className="mt-2 text-blue-900/80" data-testid="tenants-onboarding-loop-hint">
                            Последовательность: откройте Workspace, выполните действие по филиалу, затем проверьте результат в Ops через подсказку в Workspace.
                        </div>
                    </div>
                    <ProvisioningWizard session={session} accessSection="tenants" />
                </div>
            ) : null}
        </div>
    );
}
