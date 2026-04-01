"use client";

import { useSession } from "next-auth/react";

import AccessDenied from "@/components/AccessDenied";
import ConsoleOwnerScopeGate from "@/components/ConsoleOwnerScopeGate";
import ConsoleSupportDisclosure from "@/components/ConsoleSupportDisclosure";

import KnowledgeBranchReadinessPanel from "./_components/KnowledgeBranchReadinessPanel";
import KnowledgeLearningCandidatesPanel from "./_components/KnowledgeLearningCandidatesPanel";
import KnowledgePlatformAdminFleetPanel from "./_components/KnowledgePlatformAdminFleetPanel";
import KnowledgeRollbackConfirmDialog from "./_components/KnowledgeRollbackConfirmDialog";
import KnowledgeStudioFlow from "./_components/KnowledgeStudioFlow";
import { useKnowledgeStudioState } from "./_hooks/useKnowledgeStudioState";

type SessionData = ReturnType<typeof useSession>["data"];

function KnowledgeStudio({ session }: { session: SessionData }) {
    const {
        role,
        canRead,
        canEdit,
        supportToolsDefaultOpen,
        lastPublishAt,
        platformAdminFleet,
        branchReadiness,
        branchGate,
        banners,
        flow,
        learningCandidates,
        rollbackDialog,
    } = useKnowledgeStudioState({ session });

    if (!canRead) {
        return <AccessDenied message="Эта роль не имеет доступа к знаниям." />;
    }

    if (branchGate.required) {
        if (branchGate.isPlatformAdmin) {
            return (
                <div className="space-y-4">
                    <KnowledgePlatformAdminFleetPanel state={platformAdminFleet} />
                    <div className="card-surface max-w-xl p-8" data-testid="knowledge-branch-gate-platform">
                        <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Требуется контекст</p>
                        <h2 className="mt-3 mb-4 text-2xl font-semibold">Выберите филиал в панели сети клиентов</h2>
                        <p className="mb-4 text-sm text-muted-foreground">
                            Для роли `platform admin` контекст филиала применяется автоматически после выбора клиента и филиала.
                            Кнопка `Применить контекст` нужна как резервный шаг.
                        </p>
                        <div className="rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground">
                            client_id: {branchGate.selectedClientId || "—"} · branch_id: {branchGate.selectedBranchId || "не выбран"}
                        </div>
                        {branchGate.fallbackBranchId ? (
                            <div className="mt-4">
                                <button
                                    className="btn-ghost"
                                    onClick={() => void branchGate.onApplyPlatformFallback()}
                                    disabled={branchGate.isSelectingBranch || !branchGate.selectedClientId}
                                >
                                    {branchGate.isSelectingBranch ? "Загрузка..." : "Открыть первый филиал (резерв)"}
                                </button>
                            </div>
                        ) : null}
                    </div>
                </div>
            );
        }

        return (
            <div className="space-y-4">
                <KnowledgePlatformAdminFleetPanel state={platformAdminFleet} />
                {branchReadiness ? <KnowledgeBranchReadinessPanel state={branchReadiness} /> : null}
                <ConsoleOwnerScopeGate
                    rootTestId="knowledge-branch-gate"
                    selectTestId="knowledge-branch-select"
                    applyTestId="knowledge-apply-branch"
                    title="Выберите филиал"
                    description="Управление знаниями выполняется отдельно для каждого филиала."
                    branchOptions={branchGate.branchOptions}
                    selectedBranchId={branchGate.branchId}
                    onSelectedBranchChange={branchGate.onBranchIdChange}
                    onApply={branchGate.onApply}
                    applyLabel="Продолжить"
                    isApplying={branchGate.isSelectingBranch}
                    disabled={branchGate.branchOptions.length === 0}
                    emptyStateDescription="Проверьте выбранного клиента в верхней панели или откройте Workspace и активируйте филиал."
                    links={[{ href: "/company-workspace", label: "Открыть Workspace" }]}
                    className="card-surface max-w-xl p-8"
                />
            </div>
        );
    }

    return (
        <div className="space-y-6" data-testid="knowledge-studio">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <div className="badge mb-3">Knowledge Studio</div>
                    <h1 className="text-2xl font-semibold">Управление знаниями</h1>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Draft → Validate → Preview → Publish → History → Rollback. Публикация только после валидного draft.
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`rounded-full px-3 py-1 text-xs font-medium ${canEdit ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground"}`}>
                        {canEdit ? "write" : "read-only"}
                    </span>
                    {lastPublishAt ? (
                        <span className="text-xs text-muted-foreground">
                            Published: {new Date(lastPublishAt).toLocaleString("ru-RU")}
                        </span>
                    ) : null}
                </div>
            </div>

            <KnowledgePlatformAdminFleetPanel state={platformAdminFleet} />
            {branchReadiness ? <KnowledgeBranchReadinessPanel state={branchReadiness} /> : null}

            {banners.gatewayError && !banners.apiUnavailable ? (
                <div className="rounded-xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-700">
                    <div>{banners.gatewayError}</div>
                    <button
                        type="button"
                        className="btn-ghost mt-3"
                        onClick={banners.retryGatewayRequests}
                    >
                        Повторить запросы
                    </button>
                </div>
            ) : null}

            {banners.apiUnavailable ? (
                <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                    <div>Knowledge API недоступен. UI работает в режиме просмотра до появления endpoints.</div>
                    <button
                        type="button"
                        className="btn-ghost mt-3"
                        onClick={banners.retryApiAvailability}
                    >
                        Проверить снова
                    </button>
                </div>
            ) : null}

            {!canEdit ? (
                <div className="rounded-xl border border-border/60 bg-muted/40 p-4 text-sm text-muted-foreground">
                    Роль {role}: доступ только для просмотра. Публикация и откат доступны owner/admin/platform admin.
                </div>
            ) : null}

            <KnowledgeStudioFlow
                sidebar={flow.sidebar}
                currentStep={flow.currentStep}
                draftStage={flow.draftStage}
                validateStage={flow.validateStage}
                previewStage={flow.previewStage}
                publishStage={flow.publishStage}
                historyStage={flow.historyStage}
                rollbackStage={flow.rollbackStage}
                onPrevStep={flow.onPrevStep}
                onNextStep={flow.onNextStep}
                isFirstStep={flow.isFirstStep}
                isLastStep={flow.isLastStep}
            />

            <div className="card-surface mt-6 p-5">
                <ConsoleSupportDisclosure
                    rootTestId="knowledge-learning-candidates-disclosure"
                    title="Кандидаты обучения"
                    description="Это вторичный поток для команды: сначала подготовьте branch knowledge, потом разбирайте новые ответы менеджеров."
                    defaultOpen={supportToolsDefaultOpen}
                >
                    <KnowledgeLearningCandidatesPanel
                        candidates={learningCandidates.candidates}
                        isLoading={learningCandidates.isLoading}
                        canEdit={learningCandidates.canEdit}
                        approvePending={learningCandidates.approvePending}
                        rejectPending={learningCandidates.rejectPending}
                        onApprove={learningCandidates.onApprove}
                        onReject={learningCandidates.onReject}
                        formatTimestamp={learningCandidates.formatTimestamp}
                    />
                </ConsoleSupportDisclosure>
            </div>

            <KnowledgeRollbackConfirmDialog
                open={rollbackDialog.open}
                selectedVersionId={rollbackDialog.selectedVersionId}
                rollbackReason={rollbackDialog.rollbackReason}
                onRollbackReasonChange={rollbackDialog.onRollbackReasonChange}
                onCancel={rollbackDialog.onCancel}
                onConfirm={rollbackDialog.onConfirm}
                isPending={rollbackDialog.isPending}
            />
        </div>
    );
}

export default function KnowledgePage() {
    const { data: session } = useSession();

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра знаний.
            </div>
        );
    }

    return <KnowledgeStudio session={session} />;
}
