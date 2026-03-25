"use client";

import type { useKnowledgeStudioState } from "../_hooks/useKnowledgeStudioState";

type KnowledgeBranchReadinessState = NonNullable<ReturnType<typeof useKnowledgeStudioState>["branchReadiness"]>;

type KnowledgeBranchReadinessPanelProps = {
    state: KnowledgeBranchReadinessState;
};

export default function KnowledgeBranchReadinessPanel({
    state,
}: KnowledgeBranchReadinessPanelProps) {
    const branch = state.selectedBranchContext;

    return (
        <div className="card-surface p-5" data-testid="knowledge-branch-readiness">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold">Готовность знаний по филиалу</h2>
                    <p className="text-sm text-muted-foreground">
                        Оперативные настройки базы знаний для текущего филиала.
                    </p>
                </div>
                <div className="text-xs text-muted-foreground">
                    <div>{branch.name ?? branch.slug ?? branch.id}</div>
                    <div className="mt-1 font-mono">ID филиала: {branch.id}</div>
                    <div className="mt-1">Статус филиала: {branch.is_active ? "активен" : "неактивен"}</div>
                </div>
            </div>

            <div className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                <div className="rounded-lg border border-border/60 px-3 py-2">
                    Тег базы знаний: {state.hasKnowledgeTag ? branch.knowledge_tag : "не задан для этого филиала"}
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                    Часы работы филиала: {state.hasBranchWorkingHours ? "заданы для филиала" : "не заданы (используется опубликованный пакет)"}
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                    Онбординг: {branch.onboarding_state ?? "—"}
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                    Готовность к запуску: {branch.go_live_state ?? "ожидает решения"}
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                    Эффективные часы работы: {state.effectiveHoursSummary}
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                    Источник часов: {state.effectiveHoursSource} · версия публикации: {state.currentVersionId ?? "не опубликована"}
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                    Синхронизация знаний: <span className={`rounded-full px-2 py-0.5 ${state.currentSyncStatusClass}`}>{state.currentSyncStatusLabel}</span>
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                    Safe mode: {state.currentSafeMode ? "включен" : "выключен"}
                </div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">
                Поля ниже применятся только после кнопки `Сохранить изменение филиала`.
            </div>
            {state.currentSyncBlocked ? (
                <div
                    className={`mt-3 rounded-lg px-3 py-3 text-sm ${state.currentSyncFailed ? "border border-red-200 bg-red-50 text-red-800" : "border border-slate-300/70 bg-slate-50 text-slate-800"}`}
                    data-testid="knowledge-sync-warning"
                >
                    <p className="font-medium">{state.currentSyncMessage}</p>
                    {state.currentSyncDetails ? (
                        <p className="mt-2 text-xs">
                            {state.currentSyncDetails}
                        </p>
                    ) : null}
                    {state.canRetrySync ? (
                        <div className="mt-3">
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={state.onRetrySync}
                                disabled={state.isRetrySyncPending}
                                data-testid="knowledge-sync-retry"
                            >
                                {state.isRetrySyncPending ? "Повторяем..." : "Повторить синхронизацию"}
                            </button>
                        </div>
                    ) : null}
                </div>
            ) : null}

            {state.canEdit && (
                <div className="mt-4 grid gap-3">
                    <label className="text-xs text-muted-foreground">
                        Тег базы знаний филиала (`knowledge_tag`, опционально)
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={state.branchKnowledgeTagDraft}
                            onChange={(event) => state.onBranchKnowledgeTagDraftChange(event.target.value)}
                            disabled={state.isApplyingPatch}
                            placeholder="Например: demo_salon_main"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Часы работы филиала (`working_hours`, JSON-переопределение)
                        <textarea
                            className="mt-1 min-h-[140px] w-full rounded-lg border border-border bg-background px-3 py-2 text-xs font-mono"
                            value={state.branchWorkingHoursDraft}
                            onChange={(event) => state.onBranchWorkingHoursDraftChange(event.target.value)}
                            disabled={state.isApplyingPatch}
                        />
                        <div className="mt-1">
                            Пустой объект <span className="font-mono">{"{}"}</span> очистит часы работы филиала.
                        </div>
                        {state.parsedBranchWorkingHoursError && (
                            <div className="mt-1 text-destructive">{state.parsedBranchWorkingHoursError}</div>
                        )}
                    </label>
                    <div className="flex flex-wrap items-center gap-2">
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={state.onUsePublishedHours}
                            disabled={state.isApplyingPatch}
                        >
                            Подставить опубликованные часы
                        </button>
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={state.onResetHoursOverride}
                            disabled={state.isApplyingPatch}
                        >
                            Сбросить переопределение
                        </button>
                    </div>
                    <label className="text-xs text-muted-foreground">
                        Причина изменения (аудит)
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={state.branchChangeReason}
                            onChange={(event) => state.onBranchChangeReasonChange(event.target.value)}
                            disabled={state.isApplyingPatch}
                            placeholder="Например: обновление часов после смены графика"
                        />
                    </label>
                    {state.branchPatchHint && <div className="text-xs text-muted-foreground">{state.branchPatchHint}</div>}
                    <div className="flex flex-wrap items-center gap-2">
                        <button
                            type="button"
                            className="btn-primary"
                            onClick={state.onApplyPatch}
                            disabled={!state.canApplyPatch}
                        >
                            {state.isApplyingPatch ? "Применение..." : "Сохранить изменение филиала"}
                        </button>
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={state.onOpenTeam}
                            disabled={state.teamActionsDisabled}
                        >
                            Команда и мастера
                        </button>
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={state.onOpenCalendar}
                            disabled={state.teamActionsDisabled}
                        >
                            Календарь
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
