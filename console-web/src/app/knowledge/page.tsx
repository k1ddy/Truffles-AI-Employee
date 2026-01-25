"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import axios from "axios";
import toast from "react-hot-toast";
import { authApi, knowledgeApi, type KnowledgeHistoryItem } from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";

type SessionData = ReturnType<typeof useSession>["data"];

const KNOWLEDGE_STEPS = [
    { id: "draft", label: "Draft", hint: "редактирование" },
    { id: "validate", label: "Validate", hint: "валидация" },
    { id: "preview", label: "Preview", hint: "diff" },
    { id: "publish", label: "Publish", hint: "go/no-go" },
    { id: "history", label: "History", hint: "версии" },
    { id: "rollback", label: "Rollback", hint: "восстановление" },
] as const;

type KnowledgeStepId = (typeof KNOWLEDGE_STEPS)[number]["id"];

type ValidationState = {
    ran: boolean;
    errors: string[];
    warnings: string[];
    diff: string;
};

function isApiUnavailable(error: unknown) {
    return axios.isAxiosError(error)
        && [404, 501].includes(error.response?.status ?? 0);
}

function normalizeStringList(value: unknown): string[] {
    if (!Array.isArray(value)) {
        return [];
    }
    return value.filter((item): item is string => typeof item === "string");
}

function formatPayload(value: unknown): string {
    if (typeof value === "string") {
        return value;
    }
    if (value === null || value === undefined) {
        return "";
    }
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
}

function extractHistoryItems(value: unknown): KnowledgeHistoryItem[] {
    if (!value || typeof value !== "object") {
        return [];
    }
    const payload = value as Record<string, unknown>;
    const items = payload.items ?? payload.history ?? payload.versions;
    if (!Array.isArray(items)) {
        return [];
    }
    return items as KnowledgeHistoryItem[];
}

function KnowledgeStudio({ session }: { session: SessionData }) {
    const { handleError } = useErrorHandler();
    const [stepIndex, setStepIndex] = useState(0);
    const [draftText, setDraftText] = useState("");
    const [ackWarnings, setAckWarnings] = useState(false);
    const [apiUnavailable, setApiUnavailable] = useState(false);
    const [selectedVersionId, setSelectedVersionId] = useState("");
    const [lastValidatedDraft, setLastValidatedDraft] = useState<string | null>(null);
    const [lastPublishAt, setLastPublishAt] = useState<string | null>(null);
    const [lastRollbackAt, setLastRollbackAt] = useState<string | null>(null);
    const [validation, setValidation] = useState<ValidationState>({
        ran: false,
        errors: [],
        warnings: [],
        diff: "",
    });

    const { data: meData } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canEdit = role === "owner" || role === "admin";

    const currentQuery = useQuery({
        queryKey: ["knowledge-current"],
        queryFn: async () => {
            const response = await knowledgeApi.getCurrent();
            return response.data;
        },
        enabled: !!session && !apiUnavailable,
        retry: false,
    });

    const historyQuery = useQuery({
        queryKey: ["knowledge-history"],
        queryFn: async () => {
            const response = await knowledgeApi.history();
            return response.data;
        },
        enabled: !!session && !apiUnavailable,
        retry: false,
    });

    useEffect(() => {
        const error = currentQuery.error;
        if (!error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        handleError(error);
    }, [currentQuery.error, apiUnavailable, handleError]);

    useEffect(() => {
        const error = historyQuery.error;
        if (!error || apiUnavailable) {
            return;
        }
        if (isApiUnavailable(error)) {
            setApiUnavailable(true);
            return;
        }
        handleError(error);
    }, [historyQuery.error, apiUnavailable, handleError]);

    const currentText = useMemo(() => {
        if (!currentQuery.data) {
            return "";
        }
        const payload = currentQuery.data.content ?? currentQuery.data.payload ?? currentQuery.data;
        return formatPayload(payload);
    }, [currentQuery.data]);

    const historyItems = useMemo(
        () => extractHistoryItems(historyQuery.data),
        [historyQuery.data]
    );

    const hasErrors = validation.errors.length > 0;
    const hasWarnings = validation.warnings.length > 0;
    const isDraftDirty = lastValidatedDraft !== null && lastValidatedDraft !== draftText;
    const canPublish = canEdit
        && !apiUnavailable
        && validation.ran
        && !hasErrors
        && !isDraftDirty
        && (!hasWarnings || ackWarnings)
        && draftText.trim().length > 0;

    const validateMutation = useMutation({
        mutationFn: async () => {
            const response = await knowledgeApi.validate(draftText.trim());
            return response.data;
        },
        onSuccess: (data) => {
            const errors = normalizeStringList(data?.errors);
            const warnings = normalizeStringList(data?.warnings);
            const diff = typeof data?.diff === "string" ? data.diff : "";
            const valid = data?.valid ?? errors.length === 0;
            setValidation({ ran: true, errors, warnings, diff });
            setLastValidatedDraft(draftText);
            setAckWarnings(false);
            if (valid) {
                toast.success("Валидация пройдена");
            } else {
                toast.error("Валидация не пройдена");
            }
        },
        onError: (error) => {
            if (isApiUnavailable(error)) {
                setApiUnavailable(true);
                return;
            }
            handleError(error);
        },
    });

    const publishMutation = useMutation({
        mutationFn: async () => {
            const response = await knowledgeApi.publish(draftText.trim());
            return response.data;
        },
        onSuccess: (data) => {
            setLastPublishAt(data?.published_at ?? new Date().toISOString());
            toast.success(data?.message || "Знания опубликованы");
            currentQuery.refetch();
            historyQuery.refetch();
        },
        onError: (error) => {
            if (isApiUnavailable(error)) {
                setApiUnavailable(true);
                return;
            }
            handleError(error);
        },
    });

    const rollbackMutation = useMutation({
        mutationFn: async () => {
            const response = await knowledgeApi.rollback(selectedVersionId);
            return response.data;
        },
        onSuccess: () => {
            setLastRollbackAt(new Date().toISOString());
            toast.success("Версия восстановлена");
            currentQuery.refetch();
            historyQuery.refetch();
        },
        onError: (error) => {
            if (isApiUnavailable(error)) {
                setApiUnavailable(true);
                return;
            }
            handleError(error);
        },
    });

    const stepStatus: Record<KnowledgeStepId, boolean> = {
        draft: draftText.trim().length > 0,
        validate: validation.ran && !hasErrors,
        preview: validation.ran && !hasErrors,
        publish: !!lastPublishAt,
        history: historyItems.length > 0,
        rollback: !!lastRollbackAt,
    };

    const currentStep = KNOWLEDGE_STEPS[stepIndex];

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
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${canEdit ? "bg-secondary text-secondary-foreground" : "bg-muted text-muted-foreground"}`}>
                        {canEdit ? "write" : "read-only"}
                    </span>
                    {lastPublishAt && (
                        <span className="text-xs text-muted-foreground">
                            Published: {new Date(lastPublishAt).toLocaleString("ru-RU")}
                        </span>
                    )}
                </div>
            </div>

            {apiUnavailable && (
                <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                    <div>Knowledge API недоступен. UI работает в режиме просмотра до появления endpoints.</div>
                    <button
                        type="button"
                        className="btn-ghost mt-3"
                        onClick={() => {
                            setApiUnavailable(false);
                            currentQuery.refetch();
                            historyQuery.refetch();
                        }}
                    >
                        Проверить снова
                    </button>
                </div>
            )}

            {!canEdit && (
                <div className="rounded-xl border border-border/60 bg-muted/40 p-4 text-sm text-muted-foreground">
                    Роль {role}: доступ только для просмотра. Публикация и откат доступны owner/admin.
                </div>
            )}

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <div className="card-surface p-4">
                    <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-4">
                        Flow
                    </h2>
                    <div className="flex flex-col gap-2">
                        {KNOWLEDGE_STEPS.map((step, index) => {
                            const active = index === stepIndex;
                            const done = stepStatus[step.id];
                            return (
                                <button
                                    key={step.id}
                                    type="button"
                                    onClick={() => setStepIndex(index)}
                                    className={`flex items-center justify-between rounded-lg border px-3 py-2 text-left text-sm transition ${
                                        active ? "border-primary bg-primary/10" : "border-border/60 hover:bg-muted"
                                    }`}
                                >
                                    <div>
                                        <div className="font-medium">{step.label}</div>
                                        <div className="text-xs text-muted-foreground">{step.hint}</div>
                                    </div>
                                    {done && <span className="text-xs text-green-600">✓</span>}
                                </button>
                            );
                        })}
                    </div>
                </div>

                <div className="card-surface p-6 lg:col-span-2">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold">{currentStep.label}</h2>
                        <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                            {currentStep.hint}
                        </span>
                    </div>

                    {currentStep.id === "draft" && (
                        <div className="mt-4 space-y-4">
                            <div className="flex flex-wrap items-center gap-3">
                                <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={() => setDraftText(currentText)}
                                    disabled={!currentText || !canEdit}
                                >
                                    Загрузить current в draft
                                </button>
                                <span className="text-xs text-muted-foreground">
                                    Draft хранится локально до публикации.
                                </span>
                            </div>
                            <textarea
                                className="min-h-[240px] w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono"
                                placeholder="Вставьте YAML/JSON draft знаний..."
                                value={draftText}
                                onChange={(event) => {
                                    setDraftText(event.target.value);
                                    setValidation((prev) => prev.ran ? { ...prev, ran: false } : prev);
                                }}
                                disabled={!canEdit}
                            />
                            <div className="text-xs text-muted-foreground">
                                {draftText.trim().length} символов
                            </div>
                        </div>
                    )}

                    {currentStep.id === "validate" && (
                        <div className="mt-4 space-y-4">
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={() => validateMutation.mutate()}
                                disabled={!canEdit || apiUnavailable || !draftText.trim() || validateMutation.isPending}
                            >
                                {validateMutation.isPending ? "Проверка..." : "Запустить валидацию"}
                            </button>
                            {validation.ran && (
                                <div className="space-y-3">
                                    <div className={`rounded-lg border p-3 text-sm ${hasErrors ? "border-destructive/40 bg-destructive/10 text-destructive" : "border-border/60 bg-muted/30"}`}>
                                        {hasErrors ? "Ошибки найдены" : "Ошибок нет"}
                                    </div>
                                    {validation.errors.length > 0 && (
                                        <ul className="list-disc space-y-1 pl-5 text-sm text-destructive">
                                            {validation.errors.map((error, idx) => (
                                                <li key={`${error}-${idx}`}>{error}</li>
                                            ))}
                                        </ul>
                                    )}
                                    {validation.warnings.length > 0 && (
                                        <div>
                                            <p className="text-sm font-medium text-muted-foreground">Warnings</p>
                                            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                                                {validation.warnings.map((warning, idx) => (
                                                    <li key={`${warning}-${idx}`}>{warning}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {isDraftDirty && (
                                        <div className="text-xs text-muted-foreground">
                                            Draft изменён после валидации — повторите Validate перед Publish.
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {currentStep.id === "preview" && (
                        <div className="mt-4 space-y-4">
                            {validation.diff ? (
                                <pre className="max-h-[340px] overflow-auto rounded-lg border border-border bg-muted/40 p-4 text-xs font-mono">
                                    {validation.diff}
                                </pre>
                            ) : (
                                <div className="grid gap-4 lg:grid-cols-2">
                                    <div>
                                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Current</p>
                                        <pre className="max-h-[300px] overflow-auto rounded-lg border border-border bg-muted/40 p-4 text-xs font-mono">
                                            {currentText || "Нет данных"}
                                        </pre>
                                    </div>
                                    <div>
                                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-2">Draft</p>
                                        <pre className="max-h-[300px] overflow-auto rounded-lg border border-border bg-muted/40 p-4 text-xs font-mono">
                                            {draftText || "Draft пуст"}
                                        </pre>
                                    </div>
                                </div>
                            )}
                            {!validation.ran && (
                                <p className="text-sm text-muted-foreground">
                                    Запустите Validate, чтобы получить diff.
                                </p>
                            )}
                        </div>
                    )}

                    {currentStep.id === "publish" && (
                        <div className="mt-4 space-y-4">
                            <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm">
                                <div className="flex items-center justify-between">
                                    <span>Validation</span>
                                    <span className={validation.ran && !hasErrors ? "text-green-600" : "text-muted-foreground"}>
                                        {validation.ran ? (hasErrors ? "errors" : "ok") : "not run"}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between mt-2">
                                    <span>Warnings</span>
                                    <span className={hasWarnings ? "text-amber-600" : "text-muted-foreground"}>
                                        {hasWarnings ? validation.warnings.length : "0"}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between mt-2">
                                    <span>Draft dirty</span>
                                    <span className={isDraftDirty ? "text-amber-600" : "text-muted-foreground"}>
                                        {isDraftDirty ? "yes" : "no"}
                                    </span>
                                </div>
                            </div>

                            {hasWarnings && (
                                <label className="flex items-start gap-2 text-sm text-muted-foreground">
                                    <input
                                        type="checkbox"
                                        className="mt-1"
                                        checked={ackWarnings}
                                        onChange={(event) => setAckWarnings(event.target.checked)}
                                        disabled={!canEdit}
                                    />
                                    Я подтверждаю предупреждения и понимаю риски изменений.
                                </label>
                            )}

                            <button
                                type="button"
                                className="btn-primary"
                                onClick={() => publishMutation.mutate()}
                                disabled={!canPublish || publishMutation.isPending}
                            >
                                {publishMutation.isPending ? "Публикация..." : "Опубликовать"}
                            </button>
                            {!canPublish && (
                                <p className="text-xs text-muted-foreground">
                                    Publish доступен только после валидации без ошибок и подтверждения warnings.
                                </p>
                            )}
                        </div>
                    )}

                    {currentStep.id === "history" && (
                        <div className="mt-4 space-y-4">
                            {historyItems.length === 0 && (
                                <p className="text-sm text-muted-foreground">История пока пуста.</p>
                            )}
                            {historyItems.length > 0 && (
                                <div className="space-y-3">
                                    {historyItems.map((item, index) => (
                                        <label
                                            key={item.id ?? `history-${index}`}
                                            className={`flex cursor-pointer items-start justify-between rounded-lg border p-3 text-sm ${
                                                selectedVersionId === item.id ? "border-primary bg-primary/10" : "border-border/60"
                                            }`}
                                        >
                                            <div>
                                                <div className="font-medium">
                                                    {item.summary || item.id || "unknown-version"}
                                                </div>
                                                <div className="text-xs text-muted-foreground">
                                                    {item.status ?? "status неизвестен"}
                                                </div>
                                                {item.published_at && (
                                                    <div className="text-xs text-muted-foreground">
                                                        Published: {new Date(item.published_at).toLocaleString("ru-RU")}
                                                    </div>
                                                )}
                                            </div>
                                            <input
                                                type="radio"
                                                name="knowledge-version"
                                                className="mt-1"
                                                value={item.id ?? ""}
                                                checked={selectedVersionId === item.id}
                                                onChange={() => setSelectedVersionId(item.id ?? "")}
                                                disabled={!item.id}
                                            />
                                        </label>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {currentStep.id === "rollback" && (
                        <div className="mt-4 space-y-4">
                            <div className="rounded-lg border border-border/60 bg-muted/30 p-4 text-sm">
                                <div className="flex items-center justify-between">
                                    <span>Выбранная версия</span>
                                    <span className="font-mono text-xs">{selectedVersionId || "не выбрана"}</span>
                                </div>
                                {lastRollbackAt && (
                                    <div className="mt-2 text-xs text-muted-foreground">
                                        Last rollback: {new Date(lastRollbackAt).toLocaleString("ru-RU")}
                                    </div>
                                )}
                            </div>
                            <button
                                type="button"
                                className="btn-primary"
                                onClick={() => rollbackMutation.mutate()}
                                disabled={!canEdit || apiUnavailable || !selectedVersionId || rollbackMutation.isPending}
                            >
                                {rollbackMutation.isPending ? "Откат..." : "Выполнить rollback"}
                            </button>
                            <p className="text-xs text-muted-foreground">
                                Rollback возвращает выбранную версию и фиксируется в audit.
                            </p>
                        </div>
                    )}

                    <div className="mt-8 flex items-center justify-between border-t border-border/60 pt-4">
                        <button
                            type="button"
                            className="btn-ghost"
                            onClick={() => setStepIndex((prev) => Math.max(prev - 1, 0))}
                            disabled={stepIndex === 0}
                        >
                            Назад
                        </button>
                        <button
                            type="button"
                            className="btn-primary"
                            onClick={() => setStepIndex((prev) => Math.min(prev + 1, KNOWLEDGE_STEPS.length - 1))}
                            disabled={stepIndex === KNOWLEDGE_STEPS.length - 1}
                        >
                            Далее
                        </button>
                    </div>
                </div>
            </div>
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
