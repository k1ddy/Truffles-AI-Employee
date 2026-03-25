"use client";

import Link from "next/link";

import type { KnowledgeHistoryItem } from "@/lib/api-client";
import ConsoleSupportDisclosure from "@/components/ConsoleSupportDisclosure";

import KnowledgePackInspectorPanel, { type KnowledgePackInspectorSummary, type KnowledgePackInspectorItem } from "./KnowledgePackInspectorPanel";

type KnowledgeStepId = "draft" | "validate" | "preview" | "publish" | "history" | "rollback";

type KnowledgeStep = {
    id: KnowledgeStepId;
    label: string;
    hint: string;
};

type GuidedHours = {
    days: string;
    open: string;
    close: string;
};

type GuidedService = {
    id: string;
    name: string;
};

type GuidedSalonProfile = {
    salonName: string;
    city: string;
    addressFull: string;
    servicesSummary: string;
    languages: string;
    guestPolicy: string;
};

type GuidedBooking = {
    collectFields: string;
    botCanConfirm: boolean;
};

type GuidedPolicy = {
    paymentInfo: string;
    reschedule: string;
    cancel: string;
    discounts: string;
};

type SpecialistSummary = {
    id: string;
    name: string;
    services?: Array<Record<string, unknown>>;
};

type SpecialistsByBranchItem = {
    label: string;
    count: number;
};

type ValidationState = {
    ran: boolean;
    errors: string[];
    warnings: string[];
    diff: string;
    draftSaved: boolean;
};

type FlowSidebarProps = {
    steps: readonly KnowledgeStep[];
    stepIndex: number;
    stepStatus: Record<KnowledgeStepId, boolean>;
    onSelectStep: (index: number) => void;
};

type DraftStageProps = {
    canEdit: boolean;
    draftText: string;
    onDraftTextChange: (value: string) => void;
    currentText: string;
    editBaseText: string;
    hasSavedDraft: boolean;
    editBaseSource: "draft" | "published" | "none";
    editBaseSourceLabel: string;
    editBaseUpdatedAt?: string | null;
    draftUpdatedAt?: string | null;
    formatTimestamp: (value?: string | null) => string;
    structuredGuidedFields: string[];
    supportToolsDefaultOpen: boolean;
    inspectorSummary: KnowledgePackInspectorSummary;
    packInspectorQuery: string;
    onPackInspectorQueryChange: (value: string) => void;
    filteredPackPaths: KnowledgePackInspectorItem[];
    applyStructuredDraft: () => void;
    guidedHours: GuidedHours;
    onGuidedHoursChange: (next: GuidedHours) => void;
    guidedSalonProfile: GuidedSalonProfile;
    onGuidedSalonProfileChange: (next: GuidedSalonProfile) => void;
    guidedBooking: GuidedBooking;
    onGuidedBookingChange: (next: GuidedBooking) => void;
    guidedPolicy: GuidedPolicy;
    onGuidedPolicyChange: (next: GuidedPolicy) => void;
    guidedServices: GuidedService[];
    onAddGuidedService: () => void;
    onUpdateGuidedService: (id: string, name: string) => void;
    onRemoveGuidedService: (id: string) => void;
    specialistsLoading: boolean;
    allSpecialistsLoading: boolean;
    specialists: SpecialistSummary[];
    allSpecialists: SpecialistSummary[];
    missingBranchSpecialistsButClientHasSome: boolean;
    specialistsInOtherBranchesCount: number;
    specialistsByBranch: SpecialistsByBranchItem[];
    onOpenTeam: () => void;
    teamButtonDisabled: boolean;
    onLoadEditBase: () => void;
    onLoadPublished: () => void;
    onLoadSavedDraft: () => void;
};

type ValidateStageProps = {
    canEdit: boolean;
    apiUnavailable: boolean;
    draftText: string;
    validation: ValidationState;
    hasErrors: boolean;
    isDraftDirty: boolean;
    onValidate: () => void;
    isValidating: boolean;
    formatKnowledgeValidationIssue: (message: string) => { title: string; detail?: string };
};

type PreviewStageProps = {
    validation: ValidationState;
    currentText: string;
    draftText: string;
};

type PublishStageProps = {
    validation: ValidationState;
    hasErrors: boolean;
    hasWarnings: boolean;
    isDraftDirty: boolean;
    compareReady: boolean;
    compareRequired: boolean;
    compareStatusLabel: string;
    consultantVerificationReadinessSummary?: string | null;
    consultantVerificationReadinessErrorMessage?: string | null;
    lastValidatedDraftHash?: string | null;
    currentVersionId?: string | null;
    currentSyncStatus?: string | null;
    currentSyncStatusLabel: string;
    currentSyncError?: string | null;
    knowledgeSyncStatusClass: (status?: string | null) => string;
    resolveKnowledgeSyncMessage: (status?: string | null) => string;
    resolveKnowledgeSyncDetails: (error?: string | null) => string | null;
    ackWarnings: boolean;
    onAckWarningsChange: (value: boolean) => void;
    canEdit: boolean;
    canPublish: boolean;
    isPublishing: boolean;
    onPublish: () => void;
};

type HistoryStageProps = {
    items: KnowledgeHistoryItem[];
    selectedVersionId: string;
    onSelectVersion: (versionId: string) => void;
    knowledgeSyncStatusClass: (status?: string | null) => string;
};

type RollbackStageProps = {
    selectedVersionId: string;
    lastRollbackAt?: string | null;
    canEdit: boolean;
    apiUnavailable: boolean;
    isRollbackPending: boolean;
    onOpenRollbackConfirm: () => void;
};

type KnowledgeStudioFlowProps = {
    sidebar: FlowSidebarProps;
    currentStep: KnowledgeStep;
    draftStage: DraftStageProps;
    validateStage: ValidateStageProps;
    previewStage: PreviewStageProps;
    publishStage: PublishStageProps;
    historyStage: HistoryStageProps;
    rollbackStage: RollbackStageProps;
    onPrevStep: () => void;
    onNextStep: () => void;
    isFirstStep: boolean;
    isLastStep: boolean;
};

function KnowledgeFlowSidebar({ steps, stepIndex, stepStatus, onSelectStep }: FlowSidebarProps) {
    return (
        <div className="card-surface p-4">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                Flow
            </h2>
            <div className="flex flex-col gap-2">
                {steps.map((step, index) => {
                    const active = index === stepIndex;
                    const done = stepStatus[step.id];
                    return (
                        <button
                            key={step.id}
                            type="button"
                            onClick={() => onSelectStep(index)}
                            className={`flex items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition ${
                                active ? "border-primary bg-primary/10" : "border-border/60 hover:bg-muted"
                            }`}
                            data-testid={`knowledge-step-${step.id}`}
                        >
                            <div>
                                <div className="font-medium">{step.label}</div>
                                <div className="text-xs text-muted-foreground">{step.hint}</div>
                            </div>
                            {done ? <span className="text-xs text-green-600">✓</span> : null}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

function KnowledgeDraftStage({
    canEdit,
    draftText,
    onDraftTextChange,
    currentText,
    editBaseText,
    hasSavedDraft,
    editBaseSource,
    editBaseSourceLabel,
    editBaseUpdatedAt,
    draftUpdatedAt,
    formatTimestamp,
    structuredGuidedFields,
    supportToolsDefaultOpen,
    inspectorSummary,
    packInspectorQuery,
    onPackInspectorQueryChange,
    filteredPackPaths,
    applyStructuredDraft,
    guidedHours,
    onGuidedHoursChange,
    guidedSalonProfile,
    onGuidedSalonProfileChange,
    guidedBooking,
    onGuidedBookingChange,
    guidedPolicy,
    onGuidedPolicyChange,
    guidedServices,
    onAddGuidedService,
    onUpdateGuidedService,
    onRemoveGuidedService,
    specialistsLoading,
    allSpecialistsLoading,
    specialists,
    allSpecialists,
    missingBranchSpecialistsButClientHasSome,
    specialistsInOtherBranchesCount,
    specialistsByBranch,
    onOpenTeam,
    teamButtonDisabled,
    onLoadEditBase,
    onLoadPublished,
    onLoadSavedDraft,
}: DraftStageProps) {
    return (
        <div className="mt-4 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
                <button
                    type="button"
                    className="btn-ghost"
                    onClick={onLoadEditBase}
                    disabled={!(editBaseText || currentText) || !canEdit}
                    data-testid="knowledge-load-edit-base"
                >
                    Загрузить базу редактирования
                </button>
                <button
                    type="button"
                    className="btn-ghost"
                    onClick={onLoadPublished}
                    disabled={!currentText || !canEdit}
                    data-testid="knowledge-load-published"
                >
                    Загрузить опубликованную версию
                </button>
                <button
                    type="button"
                    className="btn-ghost"
                    onClick={onLoadSavedDraft}
                    disabled={!hasSavedDraft || !canEdit}
                    data-testid="knowledge-load-saved-draft"
                >
                    Загрузить сохраненный draft
                </button>
                <span className="text-xs text-muted-foreground">
                    Draft сохраняется на сервере после Validate и автоматически восстанавливается для текущего филиала.
                </span>
            </div>
            <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm" data-testid="knowledge-edit-base-card">
                <p className="font-medium text-foreground">Сейчас редактируете на базе: {editBaseSourceLabel}</p>
                <p className="mt-1 text-muted-foreground">
                    {editBaseSource === "draft"
                        ? "Console поднимает последний сохраненный draft этого филиала. Это безопаснее, чем собирать черновик с нуля."
                        : editBaseSource === "published"
                            ? "Сохраненного draft пока нет, поэтому редактор стартует от опубликованной версии."
                            : "Для этого филиала еще нет опубликованной версии и сохраненного draft. Начните с минимального черновика и Validate."}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                    База обновлена: {formatTimestamp(editBaseUpdatedAt)}
                    {hasSavedDraft ? ` · saved draft: ${formatTimestamp(draftUpdatedAt)}` : ""}
                </p>
            </div>
            {structuredGuidedFields.length > 0 ? (
                <div className="rounded-lg border border-amber-300/60 bg-amber-50 p-3 text-sm text-amber-900" data-testid="knowledge-structured-warning">
                    <p className="font-medium">Важное ограничение structured builder</p>
                    <p className="mt-1">
                        В этом филиале часть policy-полей хранится как структурные объекты: {structuredGuidedFields.join(", ")}. Если оставить эти поля пустыми, builder сохранит серверные значения как есть и не сотрет их.
                    </p>
                </div>
            ) : null}
            <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                        <p className="text-sm font-medium">Structured Draft Builder</p>
                        <p className="text-xs text-muted-foreground">Обновите часы и каталог услуг без ручного редактирования JSON.</p>
                    </div>
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={applyStructuredDraft}
                        disabled={!canEdit}
                        data-testid="knowledge-build-structured-draft"
                    >
                        Собрать structured draft
                    </button>
                </div>

                <ConsoleSupportDisclosure
                    rootTestId="knowledge-support-tools-disclosure"
                    title="Инструменты команды"
                    description="Инспектор Client Pack нужен для точечной диагностики, а не для первого прохода владельца бизнеса."
                    defaultOpen={supportToolsDefaultOpen}
                    className="mt-4"
                >
                    <KnowledgePackInspectorPanel
                        summary={inspectorSummary}
                        query={packInspectorQuery}
                        onQueryChange={onPackInspectorQueryChange}
                        items={filteredPackPaths}
                    />
                </ConsoleSupportDisclosure>

                <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <label className="text-xs text-muted-foreground">
                        Дни работы
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedHours.days}
                            onChange={(event) => onGuidedHoursChange({ ...guidedHours, days: event.target.value })}
                            disabled={!canEdit}
                            placeholder="Пн-Вс"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Открытие
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedHours.open}
                            onChange={(event) => onGuidedHoursChange({ ...guidedHours, open: event.target.value })}
                            disabled={!canEdit}
                            placeholder="10:00"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Закрытие
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedHours.close}
                            onChange={(event) => onGuidedHoursChange({ ...guidedHours, close: event.target.value })}
                            disabled={!canEdit}
                            placeholder="21:00"
                        />
                    </label>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <label className="text-xs text-muted-foreground">
                        Название салона
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedSalonProfile.salonName}
                            onChange={(event) => onGuidedSalonProfileChange({ ...guidedSalonProfile, salonName: event.target.value })}
                            disabled={!canEdit}
                            placeholder="Например: Truffles Beauty"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Город
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedSalonProfile.city}
                            onChange={(event) => onGuidedSalonProfileChange({ ...guidedSalonProfile, city: event.target.value })}
                            disabled={!canEdit}
                            placeholder="Алматы"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground sm:col-span-2">
                        Полный адрес
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedSalonProfile.addressFull}
                            onChange={(event) => onGuidedSalonProfileChange({ ...guidedSalonProfile, addressFull: event.target.value })}
                            disabled={!canEdit}
                            placeholder="ул. Пример, 10"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Языки общения (через запятую)
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedSalonProfile.languages}
                            onChange={(event) => onGuidedSalonProfileChange({ ...guidedSalonProfile, languages: event.target.value })}
                            disabled={!canEdit}
                            placeholder="ru, kk"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Guest policy
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedSalonProfile.guestPolicy}
                            onChange={(event) => onGuidedSalonProfileChange({ ...guidedSalonProfile, guestPolicy: event.target.value })}
                            disabled={!canEdit}
                            placeholder="например: работаем только по записи"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground sm:col-span-2">
                        Кратко об услугах
                        <textarea
                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedSalonProfile.servicesSummary}
                            onChange={(event) => onGuidedSalonProfileChange({ ...guidedSalonProfile, servicesSummary: event.target.value })}
                            disabled={!canEdit}
                            placeholder="Короткое описание специализации салона"
                        />
                    </label>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <label className="text-xs text-muted-foreground">
                        Booking: collect_fields (через запятую)
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedBooking.collectFields}
                            onChange={(event) => onGuidedBookingChange({ ...guidedBooking, collectFields: event.target.value })}
                            disabled={!canEdit}
                            placeholder="service, date, time, name, phone"
                        />
                    </label>
                    <label className="flex items-center gap-2 rounded-lg border border-border/60 px-3 py-2 text-xs text-muted-foreground">
                        <input
                            type="checkbox"
                            checked={guidedBooking.botCanConfirm}
                            onChange={(event) => onGuidedBookingChange({ ...guidedBooking, botCanConfirm: event.target.checked })}
                            disabled={!canEdit}
                        />
                        Booking: bot_can_confirm
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Policy: payment_info
                        <textarea
                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedPolicy.paymentInfo}
                            onChange={(event) => onGuidedPolicyChange({ ...guidedPolicy, paymentInfo: event.target.value })}
                            disabled={!canEdit}
                            placeholder="Как проходит оплата"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Policy: reschedule
                        <textarea
                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedPolicy.reschedule}
                            onChange={(event) => onGuidedPolicyChange({ ...guidedPolicy, reschedule: event.target.value })}
                            disabled={!canEdit}
                            placeholder="Правила переноса"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Policy: cancel
                        <textarea
                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedPolicy.cancel}
                            onChange={(event) => onGuidedPolicyChange({ ...guidedPolicy, cancel: event.target.value })}
                            disabled={!canEdit}
                            placeholder="Правила отмены"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        Policy: discounts
                        <textarea
                            className="mt-1 min-h-[68px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={guidedPolicy.discounts}
                            onChange={(event) => onGuidedPolicyChange({ ...guidedPolicy, discounts: event.target.value })}
                            disabled={!canEdit}
                            placeholder="Скидки и акции"
                        />
                    </label>
                </div>

                <div className="mt-4 space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-medium">Услуги</p>
                        <button type="button" className="btn-ghost" onClick={onAddGuidedService} disabled={!canEdit}>
                            Добавить услугу
                        </button>
                    </div>
                    {guidedServices.map((service) => (
                        <div key={service.id} className="flex items-center gap-2">
                            <input
                                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                value={service.name}
                                onChange={(event) => onUpdateGuidedService(service.id, event.target.value)}
                                disabled={!canEdit}
                                placeholder="Название услуги"
                            />
                            <button
                                type="button"
                                className="btn-ghost"
                                onClick={() => onRemoveGuidedService(service.id)}
                                disabled={!canEdit || guidedServices.length <= 1}
                            >
                                Удалить
                            </button>
                        </div>
                    ))}
                </div>

                <div className="mt-4 rounded-lg border border-border/60 bg-background p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-medium">Мастера филиала</p>
                        <button type="button" className="btn-ghost" onClick={onOpenTeam} disabled={teamButtonDisabled}>
                            Управлять в Team
                        </button>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                        {specialistsLoading ? "Загрузка мастеров..." : null}
                        {!specialistsLoading && specialists.length === 0 && !missingBranchSpecialistsButClientHasSome ? "В выбранном филиале пока нет мастеров в Calendar." : null}
                        {!allSpecialistsLoading && allSpecialists.length > 0 ? <div className="mt-1">Всего по клиенту: {allSpecialists.length}</div> : null}
                    </div>
                    {!specialistsLoading && missingBranchSpecialistsButClientHasSome ? (
                        <div className="mt-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700">
                            В этом филиале мастеров нет. В других филиалах клиента найдено {specialistsInOtherBranchesCount}.
                            {specialistsByBranch.length > 0 ? (
                                <div className="mt-1">
                                    {specialistsByBranch
                                        .slice(0, 3)
                                        .map((item) => `${item.label}: ${item.count}`)
                                        .join(" · ")}
                                </div>
                            ) : null}
                        </div>
                    ) : null}
                    {!specialistsLoading && specialists.length > 0 ? (
                        <div className="mt-2 grid gap-1 text-xs text-muted-foreground">
                            {specialists.slice(0, 6).map((specialist) => (
                                <div key={specialist.id}>
                                    {specialist.name} · услуг {specialist.services?.length ?? 0}
                                </div>
                            ))}
                        </div>
                    ) : null}
                </div>
            </div>
            <textarea
                className="min-h-[240px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono"
                placeholder="Вставьте YAML/JSON draft знаний..."
                value={draftText}
                onChange={(event) => onDraftTextChange(event.target.value)}
                disabled={!canEdit}
                data-testid="knowledge-draft-textarea"
            />
            <div className="text-xs text-muted-foreground">{draftText.trim().length} символов</div>
        </div>
    );
}

function KnowledgeValidateStage({
    canEdit,
    apiUnavailable,
    draftText,
    validation,
    hasErrors,
    isDraftDirty,
    onValidate,
    isValidating,
    formatKnowledgeValidationIssue,
}: ValidateStageProps) {
    return (
        <div className="mt-4 space-y-4">
            <button
                type="button"
                className="btn-primary"
                onClick={onValidate}
                disabled={!canEdit || apiUnavailable || !draftText.trim() || isValidating}
                data-testid="knowledge-validate-button"
            >
                {isValidating ? "Проверка..." : "Запустить валидацию"}
            </button>
            {validation.ran ? (
                <div className="space-y-3" data-testid="knowledge-validation-results">
                    <div className={`rounded-lg border p-3 text-sm ${hasErrors ? "border-destructive/40 bg-destructive/10 text-destructive" : "border-border/60 bg-muted/30"}`}>
                        {hasErrors ? "Ошибки найдены" : "Ошибок нет"}
                    </div>
                    {validation.errors.length > 0 ? (
                        <ul className="list-disc space-y-1 pl-5 text-sm text-destructive" data-testid="knowledge-validation-errors">
                            {validation.errors.map((error, idx) => {
                                const issue = formatKnowledgeValidationIssue(error);
                                return (
                                    <li key={`${error}-${idx}`}>
                                        <div>{issue.title}</div>
                                        {issue.detail ? <div className="text-xs text-destructive/80">{issue.detail}</div> : null}
                                    </li>
                                );
                            })}
                        </ul>
                    ) : null}
                    {validation.warnings.length > 0 ? (
                        <div>
                            <p className="text-sm font-medium text-muted-foreground">Warnings</p>
                            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                                {validation.warnings.map((warning, idx) => (
                                    <li key={`${warning}-${idx}`}>{warning}</li>
                                ))}
                            </ul>
                        </div>
                    ) : null}
                    {!validation.draftSaved ? (
                        <div className="rounded-lg border border-amber-300/60 bg-amber-50 p-3 text-sm text-amber-900" data-testid="knowledge-validation-draft-save-blocked">
                            Черновик не сохранён на сервере: обнаружена потеря structured данных. Исправьте типы полей и повторите Validate.
                        </div>
                    ) : null}
                    {isDraftDirty ? (
                        <div className="text-xs text-muted-foreground">Draft изменён после валидации — повторите Validate перед Publish.</div>
                    ) : null}
                </div>
            ) : null}
        </div>
    );
}

function KnowledgePreviewStage({ validation, currentText, draftText }: PreviewStageProps) {
    return (
        <div className="mt-4 space-y-4">
            {validation.diff ? (
                <pre className="max-h-[340px] overflow-auto rounded-lg border border-border bg-muted/40 p-4 text-xs font-mono">
                    {validation.diff}
                </pre>
            ) : (
                <div className="grid gap-4 lg:grid-cols-2">
                    <div>
                        <p className="mb-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">Current</p>
                        <pre className="max-h-[300px] overflow-auto rounded-lg border border-border bg-muted/40 p-4 text-xs font-mono">
                            {currentText || "Нет данных"}
                        </pre>
                    </div>
                    <div>
                        <p className="mb-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">Draft</p>
                        <pre className="max-h-[300px] overflow-auto rounded-lg border border-border bg-muted/40 p-4 text-xs font-mono">
                            {draftText || "Draft пуст"}
                        </pre>
                    </div>
                </div>
            )}
            {!validation.ran ? <p className="text-sm text-muted-foreground">Запустите Validate, чтобы получить diff.</p> : null}
        </div>
    );
}

function KnowledgePublishStage({
    validation,
    hasErrors,
    hasWarnings,
    isDraftDirty,
    compareReady,
    compareRequired,
    compareStatusLabel,
    consultantVerificationReadinessSummary,
    consultantVerificationReadinessErrorMessage,
    lastValidatedDraftHash,
    currentVersionId,
    currentSyncStatus,
    currentSyncStatusLabel,
    currentSyncError,
    knowledgeSyncStatusClass,
    resolveKnowledgeSyncMessage,
    resolveKnowledgeSyncDetails,
    ackWarnings,
    onAckWarningsChange,
    canEdit,
    canPublish,
    isPublishing,
    onPublish,
}: PublishStageProps) {
    return (
        <div className="mt-4 space-y-4">
            <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm">
                <div className="flex items-center justify-between">
                    <span>Validation</span>
                    <span className={validation.ran && !hasErrors ? "text-green-600" : "text-muted-foreground"}>
                        {validation.ran ? (hasErrors ? "errors" : "ok") : "not run"}
                    </span>
                </div>
                <div className="mt-2 flex items-center justify-between">
                    <span>Warnings</span>
                    <span className={hasWarnings ? "text-amber-600" : "text-muted-foreground"}>{hasWarnings ? validation.warnings.length : "0"}</span>
                </div>
                <div className="mt-2 flex items-center justify-between">
                    <span>Draft dirty</span>
                    <span className={isDraftDirty ? "text-amber-600" : "text-muted-foreground"}>{isDraftDirty ? "yes" : "no"}</span>
                </div>
                <div className="mt-2 flex items-center justify-between">
                    <span>Consultant compare</span>
                    <span className={consultantVerificationReadinessErrorMessage ? "text-destructive" : compareReady ? "text-green-600" : "text-amber-600"}>
                        {compareStatusLabel}
                    </span>
                </div>
            </div>

            <div className="rounded-lg border border-border/60 bg-muted/20 p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <p className="font-medium text-foreground">Проверка live vs draft</p>
                        <p className="mt-1 text-muted-foreground">
                            {consultantVerificationReadinessErrorMessage ?? consultantVerificationReadinessSummary ?? "После Validate откройте проверку консультанта и прогоните хотя бы один compare-кейс."}
                        </p>
                    </div>
                    <Link href="/business/consultant-verification" className="text-sm font-medium text-foreground underline underline-offset-4">
                        Открыть compare
                    </Link>
                </div>
                {lastValidatedDraftHash ? <p className="mt-3 text-xs text-muted-foreground">Draft hash: {lastValidatedDraftHash}</p> : null}
            </div>

            {hasWarnings ? (
                <label className="flex items-start gap-2 text-sm text-muted-foreground">
                    <input
                        type="checkbox"
                        className="mt-1"
                        checked={ackWarnings}
                        onChange={(event) => onAckWarningsChange(event.target.checked)}
                        disabled={!canEdit}
                    />
                    Я подтверждаю предупреждения и понимаю риски изменений.
                </label>
            ) : null}

            {currentVersionId ? (
                <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-sm" data-testid="knowledge-publish-sync-status">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-medium text-foreground">Статус текущей публикации</p>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${knowledgeSyncStatusClass(currentSyncStatus)}`}>
                            {currentSyncStatusLabel}
                        </span>
                    </div>
                    <p className="mt-2 text-muted-foreground">{resolveKnowledgeSyncMessage(currentSyncStatus)}</p>
                    {resolveKnowledgeSyncDetails(currentSyncError) ? (
                        <p className="mt-2 text-xs text-muted-foreground">{resolveKnowledgeSyncDetails(currentSyncError)}</p>
                    ) : null}
                </div>
            ) : null}

            <button type="button" className="btn-primary" onClick={onPublish} disabled={!canPublish || isPublishing}>
                {isPublishing ? "Публикация..." : "Опубликовать"}
            </button>
            {!canPublish ? (
                <p className="text-xs text-muted-foreground">
                    {compareRequired
                        ? "Publish доступен только после Validate без ошибок, подтверждения warnings и green compare для текущего draft."
                        : "Publish доступен после Validate без ошибок и подтверждения warnings. Для первого publish или branch без rollout compare сейчас не требуется."}
                </p>
            ) : null}
        </div>
    );
}

function KnowledgeHistoryStage({ items, selectedVersionId, onSelectVersion, knowledgeSyncStatusClass }: HistoryStageProps) {
    return (
        <div className="mt-4 space-y-4">
            {items.length === 0 ? <p className="text-sm text-muted-foreground">История пока пуста.</p> : null}
            {items.length > 0 ? (
                <div className="space-y-3">
                    {items.map((item, index) => (
                        <label
                            key={item.id ?? `history-${index}`}
                            className={`flex cursor-pointer items-start justify-between rounded-lg border p-3 text-sm ${selectedVersionId === item.id ? "border-primary bg-primary/10" : "border-border/60"}`}
                        >
                            <div>
                                <div className="font-medium">{item.summary || item.id || "unknown-version"}</div>
                                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                    <span>{item.status ?? "status неизвестен"}</span>
                                    {item.sync_status_label ? (
                                        <span className={`rounded-full px-2 py-0.5 ${knowledgeSyncStatusClass(item.sync_status)}`}>
                                            {item.sync_status_label}
                                        </span>
                                    ) : null}
                                </div>
                                {item.published_at ? (
                                    <div className="text-xs text-muted-foreground">
                                        Published: {new Date(item.published_at).toLocaleString("ru-RU")}
                                    </div>
                                ) : null}
                                {item.sync_status === "failed" ? <div className="text-xs text-red-700">Синхронизация требует внимания.</div> : null}
                            </div>
                            <input
                                type="radio"
                                name="knowledge-version"
                                className="mt-1"
                                value={item.id ?? ""}
                                checked={selectedVersionId === item.id}
                                onChange={() => onSelectVersion(item.id ?? "")}
                                disabled={!item.id}
                            />
                        </label>
                    ))}
                </div>
            ) : null}
        </div>
    );
}

function KnowledgeRollbackStage({
    selectedVersionId,
    lastRollbackAt,
    canEdit,
    apiUnavailable,
    isRollbackPending,
    onOpenRollbackConfirm,
}: RollbackStageProps) {
    return (
        <div className="mt-4 space-y-4">
            <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm">
                <div className="flex items-center justify-between">
                    <span>Выбранная версия</span>
                    <span className="font-mono text-xs">{selectedVersionId || "не выбрана"}</span>
                </div>
                {lastRollbackAt ? (
                    <div className="mt-2 text-xs text-muted-foreground">Last rollback: {new Date(lastRollbackAt).toLocaleString("ru-RU")}</div>
                ) : null}
            </div>
            <button
                type="button"
                className="btn-primary"
                onClick={onOpenRollbackConfirm}
                disabled={!canEdit || apiUnavailable || !selectedVersionId || isRollbackPending}
            >
                {isRollbackPending ? "Откат..." : "Выполнить rollback"}
            </button>
            <p className="text-xs text-muted-foreground">Rollback возвращает выбранную версию и фиксируется в audit.</p>
        </div>
    );
}

export default function KnowledgeStudioFlow({
    sidebar,
    currentStep,
    draftStage,
    validateStage,
    previewStage,
    publishStage,
    historyStage,
    rollbackStage,
    onPrevStep,
    onNextStep,
    isFirstStep,
    isLastStep,
}: KnowledgeStudioFlowProps) {
    return (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <KnowledgeFlowSidebar {...sidebar} />

            <div className="card-surface p-6 lg:col-span-2">
                <div className="flex items-center justify-between">
                    <h2 className="text-lg font-semibold">{currentStep.label}</h2>
                    <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{currentStep.hint}</span>
                </div>

                {currentStep.id === "draft" ? <KnowledgeDraftStage {...draftStage} /> : null}
                {currentStep.id === "validate" ? <KnowledgeValidateStage {...validateStage} /> : null}
                {currentStep.id === "preview" ? <KnowledgePreviewStage {...previewStage} /> : null}
                {currentStep.id === "publish" ? <KnowledgePublishStage {...publishStage} /> : null}
                {currentStep.id === "history" ? <KnowledgeHistoryStage {...historyStage} /> : null}
                {currentStep.id === "rollback" ? <KnowledgeRollbackStage {...rollbackStage} /> : null}

                <div className="mt-8 flex items-center justify-between border-t border-border/60 pt-4">
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={onPrevStep}
                        disabled={isFirstStep}
                        data-testid="knowledge-step-prev"
                    >
                        Назад
                    </button>
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={onNextStep}
                        disabled={isLastStep}
                        data-testid="knowledge-step-next"
                    >
                        Далее
                    </button>
                </div>
            </div>
        </div>
    );
}
