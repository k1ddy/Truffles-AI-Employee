"use client";

type KnowledgeRollbackConfirmDialogProps = {
    open: boolean;
    selectedVersionId: string;
    rollbackReason: string;
    onRollbackReasonChange: (value: string) => void;
    onCancel: () => void;
    onConfirm: () => void;
    isPending: boolean;
};

export default function KnowledgeRollbackConfirmDialog({
    open,
    selectedVersionId,
    rollbackReason,
    onRollbackReasonChange,
    onCancel,
    onConfirm,
    isPending,
}: KnowledgeRollbackConfirmDialogProps) {
    if (!open) {
        return null;
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="card-surface w-full max-w-lg space-y-4 p-6">
                <div>
                    <h3 className="text-lg font-semibold">Подтвердите rollback</h3>
                    <p className="text-sm text-muted-foreground">
                        Версия: {selectedVersionId || "—"}. Откат изменит активные знания и требует причины.
                    </p>
                </div>
                <div className="space-y-2">
                    <label className="text-sm font-medium">Причина</label>
                    <textarea
                        className="min-h-[90px] w-full rounded-lg border border-border/60 bg-background p-3 text-sm"
                        value={rollbackReason}
                        onChange={(event) => onRollbackReasonChange(event.target.value)}
                        placeholder="Например: ошибка в опубликованном pack, откат до стабильной версии"
                    />
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                    <button type="button" className="btn-ghost" onClick={onCancel} disabled={isPending}>
                        Отмена
                    </button>
                    <button type="button" className="btn-primary" onClick={onConfirm} disabled={isPending}>
                        {isPending ? "Подтверждение..." : "Подтвердить rollback"}
                    </button>
                </div>
            </div>
        </div>
    );
}
