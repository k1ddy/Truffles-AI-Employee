"use client";

import type { components } from "@/types/api.generated";
import TenantsSensitiveIdCell, { type TenantsSensitiveAction } from "@/components/TenantsSensitiveIdCell";

type BranchEditorState = {
    id: string;
    name: string;
    slug: string;
    timezone: string;
    phone: string;
    instanceId: string;
    telegramChatId: string;
    knowledgeTag: string;
    isActive: boolean;
    changeReason: string;
    confirmReason: string;
    rollbackReason: string;
    original: {
        name: string;
        slug: string;
        timezone: string;
        phone: string;
        instanceId: string;
        telegramChatId: string;
        knowledgeTag: string;
        isActive: boolean;
    };
};

type BranchChangePreview = {
    change?: {
        id?: string | number | null;
        status?: string | null;
    } | null;
} | null;

type PreviewDiffEntry = {
    field: string;
    before: string;
    after: string;
};

type BranchChangeHistoryItem = {
    id: string | number;
    status?: string | null;
    created_at?: string | null;
};

type TenantsBranchChangeManagementPanelProps = {
    branchesLoading: boolean;
    branchesErrored: boolean;
    branches: components["schemas"]["ConsoleBranch"][];

    pageFilterClientId: string | null;
    selectedClientName: string | null;
    branchQuery: string;
    onBranchQueryChange: (value: string) => void;

    isPlatformPreset: boolean;
    canWriteTenants: boolean;
    selectedBranchId: string | null;
    contextScope: string;

    onAuditSensitiveAccess: (input: {
        branchId: string;
        field: "instance_id";
        action: TenantsSensitiveAction;
        contextScope?: string;
    }) => Promise<void>;
    onStartBranchEdit: (branch: components["schemas"]["ConsoleBranch"]) => void;
    onSetBranchContext: (branch: components["schemas"]["ConsoleBranch"]) => void;

    branchEditor: BranchEditorState | null;
    onPatchBranchEditor: (patch: Partial<BranchEditorState>) => void;
    requiresBranchConfirmation: (editor: BranchEditorState) => boolean;

    savingBranch: boolean;
    publishingBranchChange: boolean;
    rollingBackBranchChange: boolean;
    onPreviewBranchChange: () => void;
    onPublishBranchChange: () => void;
    onRollbackBranchChange: () => void;
    onCancelBranchEdit: () => void;

    branchChangePreview: BranchChangePreview;
    previewValidationErrors: string[];
    previewDiffEntries: PreviewDiffEntry[];
    hasPublishedBranchChange: boolean;

    branchChangesLoading: boolean;
    branchChangesItems: BranchChangeHistoryItem[];
    formatBranchChangeStatus: (value?: string | null) => string;

    branchesHasNextPage: boolean;
    branchesFetchingNextPage: boolean;
    onFetchNextBranchesPage: () => void;
};

export default function TenantsBranchChangeManagementPanel({
    branchesLoading,
    branchesErrored,
    branches,
    pageFilterClientId,
    selectedClientName,
    branchQuery,
    onBranchQueryChange,
    isPlatformPreset,
    canWriteTenants,
    selectedBranchId,
    contextScope,
    onAuditSensitiveAccess,
    onStartBranchEdit,
    onSetBranchContext,
    branchEditor,
    onPatchBranchEditor,
    requiresBranchConfirmation,
    savingBranch,
    publishingBranchChange,
    rollingBackBranchChange,
    onPreviewBranchChange,
    onPublishBranchChange,
    onRollbackBranchChange,
    onCancelBranchEdit,
    branchChangePreview,
    previewValidationErrors,
    previewDiffEntries,
    hasPublishedBranchChange,
    branchChangesLoading,
    branchChangesItems,
    formatBranchChangeStatus,
    branchesHasNextPage,
    branchesFetchingNextPage,
    onFetchNextBranchesPage,
}: TenantsBranchChangeManagementPanelProps) {
    return (
        <section className="bg-card border border-border/60 rounded-lg p-5" data-testid="tenants-change-management">
            <div className="flex items-center justify-between gap-4 mb-4">
                <div>
                    <h2 className="text-lg font-semibold">Филиалы</h2>
                    <p className="text-sm text-muted-foreground">
                        {branchesLoading ? "—" : `${branches.length} всего`}
                    </p>
                    {pageFilterClientId ? (
                        <div className="mt-1 text-xs text-muted-foreground">
                            выбран клиент для изменений: {selectedClientName ?? pageFilterClientId}
                        </div>
                    ) : null}
                </div>
                <input
                    className="w-56 rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    placeholder="Поиск по филиалам"
                    value={branchQuery}
                    onChange={(event) => onBranchQueryChange(event.target.value)}
                />
            </div>
            <div className="space-y-3">
                {branchesLoading ? (
                    <div className="text-sm text-muted-foreground">Загрузка филиалов...</div>
                ) : branchesErrored ? (
                    <div className="text-sm text-muted-foreground">Не удалось загрузить филиалы.</div>
                ) : branches.length === 0 ? (
                    <div className="text-sm text-muted-foreground">Филиалы не найдены.</div>
                ) : (
                    branches.map((branch) => {
                        const isEditing = branchEditor?.id === branch.id;
                        const confirmationNeeded = isEditing && branchEditor
                            ? requiresBranchConfirmation(branchEditor)
                            : false;
                        const canRollback = branchChangePreview?.change?.status === "published" || hasPublishedBranchChange;

                        return (
                            <div
                                key={branch.id}
                                data-testid="tenants-branch-row"
                                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-3"
                            >
                                <div>
                                    <div className="font-medium">{branch.name ?? branch.slug ?? "Без названия"}</div>
                                    {isPlatformPreset ? (
                                        <div className="text-xs text-muted-foreground">{branch.id}</div>
                                    ) : null}
                                    <TenantsSensitiveIdCell
                                        branchId={branch.id}
                                        instanceId={branch.instance_id}
                                        contextScope={contextScope}
                                        onAudit={onAuditSensitiveAccess}
                                    />
                                    <div className="text-xs text-muted-foreground">
                                        {branch.onboarding_state ? `этап онбординга: ${branch.onboarding_state}` : "этап онбординга: —"}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <span>{branch.id === selectedBranchId ? "Выбран" : ""}</span>
                                    {canWriteTenants ? (
                                        <button
                                            className="btn-ghost"
                                            onClick={() => onStartBranchEdit(branch)}
                                            data-testid="tenants-branch-edit"
                                        >
                                            Редактировать
                                        </button>
                                    ) : null}
                                    <button
                                        className="btn-ghost"
                                        onClick={() => onSetBranchContext(branch)}
                                        disabled={branch.id === selectedBranchId}
                                    >
                                        В контекст
                                    </button>
                                </div>
                                {isEditing && branchEditor ? (
                                    <div className="w-full mt-3 rounded-lg border border-border/60 bg-muted/30 p-3">
                                        <div className="grid gap-3">
                                            <div className="rounded-lg border border-border/60 bg-background p-3 text-[11px] text-muted-foreground" data-testid="tenants-branch-input-contract">
                                                Перед публикацией проверьте данные филиала: код филиала без пробелов, корректный часовой пояс,
                                                рабочий телефон, канал WhatsApp/Telegram и актуальный тег базы знаний.
                                            </div>
                                            <div className="grid gap-3 sm:grid-cols-2">
                                                <label className="text-xs text-muted-foreground">
                                                    Название
                                                    <input
                                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={branchEditor.name}
                                                        onChange={(event) => onPatchBranchEditor({ name: event.target.value })}
                                                        disabled={!canWriteTenants || savingBranch}
                                                    />
                                                </label>
                                                <label className="text-xs text-muted-foreground">
                                                    Код филиала
                                                    <input
                                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={branchEditor.slug}
                                                        onChange={(event) => onPatchBranchEditor({ slug: event.target.value })}
                                                        disabled={!canWriteTenants || savingBranch}
                                                        placeholder="branch-slug"
                                                    />
                                                </label>
                                                <label className="text-xs text-muted-foreground">
                                                    Часовой пояс (опционально)
                                                    <input
                                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={branchEditor.timezone}
                                                        onChange={(event) => onPatchBranchEditor({ timezone: event.target.value })}
                                                        disabled={!canWriteTenants || savingBranch}
                                                        placeholder="Asia/Almaty"
                                                    />
                                                </label>
                                                <label className="text-xs text-muted-foreground">
                                                    Телефон (опционально)
                                                    <input
                                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={branchEditor.phone}
                                                        onChange={(event) => onPatchBranchEditor({ phone: event.target.value })}
                                                        disabled={!canWriteTenants || savingBranch}
                                                        placeholder="+7 700 000 00 00"
                                                    />
                                                </label>
                                                <label className="text-xs text-muted-foreground">
                                                    Идентификатор WhatsApp (опционально)
                                                    <input
                                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={branchEditor.instanceId}
                                                        onChange={(event) => onPatchBranchEditor({ instanceId: event.target.value })}
                                                        disabled={!canWriteTenants || savingBranch}
                                                        placeholder="instance-123"
                                                    />
                                                </label>
                                                <label className="text-xs text-muted-foreground">
                                                    Чат Telegram (опционально)
                                                    <input
                                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={branchEditor.telegramChatId}
                                                        onChange={(event) => onPatchBranchEditor({ telegramChatId: event.target.value })}
                                                        disabled={!canWriteTenants || savingBranch}
                                                        placeholder="-1001234567890"
                                                    />
                                                </label>
                                                <label className="text-xs text-muted-foreground">
                                                    Тег базы знаний (опционально)
                                                    <input
                                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={branchEditor.knowledgeTag}
                                                        onChange={(event) => onPatchBranchEditor({ knowledgeTag: event.target.value })}
                                                        disabled={!canWriteTenants || savingBranch}
                                                        placeholder="demo_salon"
                                                    />
                                                </label>
                                            </div>
                                            <label className="flex items-center gap-2 text-xs text-muted-foreground">
                                                <input
                                                    type="checkbox"
                                                    className="h-4 w-4"
                                                    checked={branchEditor.isActive}
                                                    onChange={(event) => onPatchBranchEditor({ isActive: event.target.checked })}
                                                    disabled={!canWriteTenants || savingBranch}
                                                />
                                                Активен
                                            </label>
                                            <label className="text-xs text-muted-foreground">
                                                Причина изменения (аудит)
                                                <input
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={branchEditor.changeReason}
                                                    onChange={(event) => onPatchBranchEditor({ changeReason: event.target.value })}
                                                    disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                />
                                            </label>
                                            {confirmationNeeded ? (
                                                <label className="text-xs text-muted-foreground">
                                                    Причина подтверждения
                                                    <input
                                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                        value={branchEditor.confirmReason}
                                                        onChange={(event) => onPatchBranchEditor({ confirmReason: event.target.value })}
                                                        disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                    />
                                                </label>
                                            ) : null}
                                            <div className="rounded-lg border border-border/60 bg-background p-3 text-xs" data-testid="tenants-branch-impact-preview">
                                                <div className="font-medium">Оценка влияния</div>
                                                <div className="mt-1 text-muted-foreground">
                                                    branch: {branchEditor.name || branchEditor.slug || branchEditor.id}
                                                </div>
                                                <div className="text-muted-foreground">
                                                    activation: {branchEditor.original.isActive ? "active" : "inactive"} {"->"} {branchEditor.isActive ? "active" : "inactive"}
                                                </div>
                                                {!branchEditor.original.isActive && branchEditor.isActive && !branchEditor.instanceId.trim() ? (
                                                    <div className="text-destructive">
                                                        Нельзя активировать без идентификатора WhatsApp.
                                                    </div>
                                                ) : null}
                                                {confirmationNeeded ? (
                                                    <div className="text-amber-700">
                                                        Изменение требует подтверждения по политике деактивации.
                                                    </div>
                                                ) : (
                                                    <div className="text-muted-foreground">
                                                        Подтверждение не требуется для текущего изменения.
                                                    </div>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    className="btn-primary"
                                                    onClick={onPreviewBranchChange}
                                                    data-testid="tenants-branch-change-preview"
                                                    disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                >
                                                    {savingBranch ? "Подготовка..." : "Черновик + проверка"}
                                                </button>
                                                <button
                                                    className="btn-primary"
                                                    onClick={onPublishBranchChange}
                                                    data-testid="tenants-branch-change-publish"
                                                    disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange || !branchChangePreview?.change?.id}
                                                >
                                                    {publishingBranchChange ? "Применение..." : "Применить"}
                                                </button>
                                                <button
                                                    className="btn-ghost"
                                                    onClick={onRollbackBranchChange}
                                                    data-testid="tenants-branch-change-rollback"
                                                    disabled={
                                                        !canWriteTenants
                                                        || savingBranch
                                                        || publishingBranchChange
                                                        || rollingBackBranchChange
                                                        || !canRollback
                                                    }
                                                >
                                                    {rollingBackBranchChange ? "Откат..." : "Откат"}
                                                </button>
                                                <button
                                                    className="btn-ghost"
                                                    onClick={onCancelBranchEdit}
                                                    disabled={savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                >
                                                    Отмена
                                                </button>
                                            </div>
                                            <label className="text-xs text-muted-foreground">
                                                Причина отката
                                                <input
                                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                                    value={branchEditor.rollbackReason}
                                                    onChange={(event) => onPatchBranchEditor({ rollbackReason: event.target.value })}
                                                    disabled={!canWriteTenants || savingBranch || publishingBranchChange || rollingBackBranchChange}
                                                />
                                            </label>
                                            {branchChangePreview?.change ? (
                                                <div className="rounded-lg border border-border/60 bg-background p-3 text-xs">
                                                    <div className="font-medium mb-1">
                                                        Изменение #{branchChangePreview.change.id}
                                                    </div>
                                                    <div className="text-muted-foreground mb-2">
                                                        статус: {formatBranchChangeStatus(branchChangePreview.change.status)}
                                                    </div>
                                                    {previewValidationErrors.length > 0 ? (
                                                        <div className="mb-2 text-red-600">
                                                            проверка: {previewValidationErrors.join("; ")}
                                                        </div>
                                                    ) : null}
                                                    {previewDiffEntries.length > 0 ? (
                                                        <div className="space-y-1">
                                                            {previewDiffEntries.map((entry) => (
                                                                <div key={entry.field} className="grid grid-cols-3 gap-2">
                                                                    <span className="font-medium">{entry.field}</span>
                                                                    <span className="truncate text-muted-foreground">{entry.before}</span>
                                                                    <span className="truncate text-foreground">{entry.after}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    ) : (
                                                        <div className="text-muted-foreground">изменений нет</div>
                                                    )}
                                                </div>
                                            ) : null}
                                            <div className="rounded-lg border border-border/60 bg-background p-3 text-xs">
                                                <div className="font-medium mb-2">История изменений</div>
                                                {branchChangesLoading ? (
                                                    <div className="text-muted-foreground">Загрузка...</div>
                                                ) : !branchChangesItems.length ? (
                                                    <div className="text-muted-foreground">Пока нет изменений</div>
                                                ) : (
                                                    <div className="space-y-1">
                                                        {branchChangesItems.slice(0, 5).map((item) => (
                                                            <div key={item.id} className="flex items-center justify-between gap-2">
                                                                <span>{formatBranchChangeStatus(item.status)}</span>
                                                                <span className="text-muted-foreground">{item.created_at ? new Date(item.created_at).toLocaleString("ru-RU") : "—"}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ) : null}
                            </div>
                        );
                    })
                )}
            </div>
            {branchesHasNextPage ? (
                <div className="flex justify-center pt-3">
                    <button
                        className="btn-ghost"
                        onClick={onFetchNextBranchesPage}
                        disabled={branchesFetchingNextPage}
                    >
                        {branchesFetchingNextPage ? "Загрузка..." : "Показать еще"}
                    </button>
                </div>
            ) : null}
        </section>
    );
}
