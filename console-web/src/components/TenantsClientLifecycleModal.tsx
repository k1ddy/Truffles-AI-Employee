"use client";

type ClientLifecycleMode = "archive" | "restore";

export type TenantsClientLifecycleDraft = {
    clientId: string;
    clientLabel: string;
    companyLabel: string;
    mode: ClientLifecycleMode;
    currentLifecycleLabel: string;
    targetLifecycleLabel: string;
    activeBranches: number;
    totalBranches: number;
    degradedBranches: number;
    reason: string;
    confirmChecked: boolean;
    checkClientScope: boolean;
    checkImpactReview: boolean;
    checkOwnerAligned: boolean;
};

type TenantsClientLifecycleModalProps = {
    draft: TenantsClientLifecycleDraft | null;
    pending: boolean;
    onClose: () => void;
    onSubmit: () => void;
    onPatchDraft: (patch: Partial<TenantsClientLifecycleDraft>) => void;
};

export default function TenantsClientLifecycleModal({
    draft,
    pending,
    onClose,
    onSubmit,
    onPatchDraft,
}: TenantsClientLifecycleModalProps) {
    if (!draft) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" data-testid="tenants-client-lifecycle-modal-overlay">
            <div
                className="card-surface w-full max-w-xl space-y-4 p-6"
                role="dialog"
                aria-modal="true"
                data-testid="tenants-client-lifecycle-modal"
            >
                <div>
                    <h3 className="text-lg font-semibold">
                        {draft.mode === "archive" ? "Архивировать клиента" : "Восстановить клиента"}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                        Подтвердите lifecycle-действие перед отправкой в API. Заполнение checklist обязательно.
                    </p>
                </div>
                <div className="rounded-lg border border-border/60 bg-background p-3 text-xs" data-testid="tenants-client-lifecycle-impact">
                    <div className="font-medium mb-1">Оценка влияния</div>
                    <div className="text-muted-foreground">
                        клиент: {draft.clientLabel} · компания: {draft.companyLabel}
                    </div>
                    <div className="text-muted-foreground">
                        переход: {draft.currentLifecycleLabel}{" -> "}{draft.targetLifecycleLabel}
                    </div>
                    <div className="text-muted-foreground">
                        филиалы: активные {draft.activeBranches}/{draft.totalBranches} · деградация {draft.degradedBranches}
                    </div>
                </div>
                <div className="rounded-lg border border-border/60 bg-background p-3 text-xs" data-testid="tenants-client-lifecycle-checklist">
                    <div className="font-medium mb-1">Pre-submit checklist</div>
                    <label className="mb-2 flex items-start gap-2 text-muted-foreground">
                        <input
                            type="checkbox"
                            className="mt-0.5 h-4 w-4"
                            checked={draft.checkClientScope}
                            data-testid="tenants-client-lifecycle-check-context"
                            onChange={(event) => onPatchDraft({ checkClientScope: event.target.checked })}
                            disabled={pending}
                        />
                        <span>Проверил контекст клиента/компании перед действием.</span>
                    </label>
                    <label className="mb-2 flex items-start gap-2 text-muted-foreground">
                        <input
                            type="checkbox"
                            className="mt-0.5 h-4 w-4"
                            checked={draft.checkImpactReview}
                            data-testid="tenants-client-lifecycle-check-impact"
                            onChange={(event) => onPatchDraft({ checkImpactReview: event.target.checked })}
                            disabled={pending}
                        />
                        <span>
                            Проверил impact:
                            {draft.mode === "archive"
                                ? " клиент уйдет из активного списка и деактивация отразится в операционном контуре."
                                : " клиент вернется в активный список и потребует операционного контроля после восстановления."}
                        </span>
                    </label>
                    <label className="flex items-start gap-2 text-muted-foreground">
                        <input
                            type="checkbox"
                            className="mt-0.5 h-4 w-4"
                            checked={draft.checkOwnerAligned}
                            data-testid="tenants-client-lifecycle-check-owner"
                            onChange={(event) => onPatchDraft({ checkOwnerAligned: event.target.checked })}
                            disabled={pending}
                        />
                        <span>Подтвердил решение с ответственным владельцем клиента.</span>
                    </label>
                </div>
                <label className="text-xs text-muted-foreground">
                    Причина действия (обязательно)
                    <input
                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={draft.reason}
                        data-testid="tenants-client-lifecycle-reason"
                        onChange={(event) => onPatchDraft({ reason: event.target.value })}
                        disabled={pending}
                    />
                </label>
                <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={draft.confirmChecked}
                        data-testid="tenants-client-lifecycle-confirm"
                        onChange={(event) => onPatchDraft({ confirmChecked: event.target.checked })}
                        disabled={pending}
                    />
                    Подтверждаю выполнение действия и влияние на lifecycle клиента
                </label>
                <div className="flex flex-wrap justify-end gap-2">
                    <button
                        className="btn-ghost"
                        onClick={onClose}
                        data-testid="tenants-client-lifecycle-cancel"
                        disabled={pending}
                    >
                        Отмена
                    </button>
                    <button
                        className="btn-primary"
                        onClick={onSubmit}
                        data-testid="tenants-client-lifecycle-submit"
                        disabled={
                            pending
                            || !draft.reason.trim()
                            || !draft.confirmChecked
                            || !draft.checkClientScope
                            || !draft.checkImpactReview
                            || !draft.checkOwnerAligned
                        }
                    >
                        {pending
                            ? "Выполняется..."
                            : draft.mode === "archive"
                                ? "Подтвердить архив"
                                : "Подтвердить восстановление"}
                    </button>
                </div>
            </div>
        </div>
    );
}
