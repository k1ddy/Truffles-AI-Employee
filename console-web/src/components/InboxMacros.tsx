"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { inboxApi } from "@/lib/api-client";
import type { components } from "@/types/api.generated";
import { collectCaseActionFollowupMessages } from "@/utils/labels";

const DEFAULT_SCOPE: components["schemas"]["ConsoleMacro"]["scope"] = "personal";

type InboxMacro = components["schemas"]["ConsoleMacro"];
type InboxMacroAction = components["schemas"]["ConsoleMacroAction"];
type InboxMacroListResponse = components["schemas"]["ConsoleMacroListResponse"];

type InboxMacrosProps = {
    onSelect: (text: string) => void;
    disabled?: boolean;
    canManage?: boolean;
    branchId?: string | null;
    caseId?: string | null;
};

type MacroFormState = {
    scope: InboxMacro["scope"];
    label: string;
    body: string;
    actionType: InboxMacroAction["type"] | "none";
    snoozeMinutes: string;
    snoozeReason: string;
};

type MacroActionOption = {
    value: MacroFormState["actionType"];
    label: string;
};

const MACRO_ACTION_OPTIONS: MacroActionOption[] = [
    { value: "none", label: "Только текст" },
    { value: "take_case", label: "Взять в работу" },
    { value: "resolve_case", label: "Закрыть заявку" },
    { value: "return_to_bot", label: "Вернуть боту" },
    { value: "reopen_case", label: "Вернуть в работу" },
    { value: "snooze_case", label: "Отложить заявку" },
];

function getScopeLabel(scope: InboxMacro["scope"]) {
    return scope === "personal" ? "Личные" : "Командные";
}

function getMacroTimestamp(macro: InboxMacro) {
    const value = macro.updated_at || macro.created_at;
    return value ? new Date(value).getTime() : 0;
}

function sortMacros(macros: InboxMacro[]) {
    return [...macros].sort((a, b) => getMacroTimestamp(b) - getMacroTimestamp(a));
}

function buildFormState(macro?: InboxMacro | null): MacroFormState {
    const action = macro?.action ?? null;
    if (!macro) {
        return {
            scope: DEFAULT_SCOPE,
            label: "",
            body: "",
            actionType: "none",
            snoozeMinutes: "30",
            snoozeReason: "",
        };
    }
    return {
        scope: macro.scope,
        label: macro.label ?? "",
        body: macro.body ?? "",
        actionType: action?.type ?? "none",
        snoozeMinutes: action?.type === "snooze_case" && action.minutes ? String(action.minutes) : "30",
        snoozeReason: action?.type === "snooze_case" ? action.reason ?? "" : "",
    };
}

function getMacroActionLabel(action?: InboxMacro["action"] | null) {
    if (!action) {
        return "Только текст";
    }
    switch (action.type) {
        case "take_case":
            return "Взять в работу";
        case "resolve_case":
            return "Закрыть заявку";
        case "return_to_bot":
            return "Вернуть боту";
        case "reopen_case":
            return "Вернуть в работу";
        case "snooze_case":
            return `Отложить на ${action.minutes ?? 30} мин`;
        default:
            return "Только текст";
    }
}

function getMacroActionHint(action?: InboxMacro["action"] | null) {
    if (!action) {
        return "Подставит текст в поле ответа без изменения статуса заявки.";
    }
    switch (action.type) {
        case "take_case":
            return "Назначит заявку на вас и подставит текст ответа.";
        case "resolve_case":
            return "Закроет заявку и подставит текст ответа.";
        case "return_to_bot":
            return "Вернёт заявку боту и подставит текст ответа.";
        case "reopen_case":
            return "Вернёт закрытую заявку в работу и подставит текст ответа.";
        case "snooze_case":
            return "Уберёт заявку из срочной очереди на время и подставит текст ответа.";
        default:
            return "Подставит текст в поле ответа.";
    }
}

function buildActionPayload(form: MacroFormState): InboxMacroAction | null {
    if (form.actionType === "none") {
        return null;
    }
    if (form.actionType !== "snooze_case") {
        return { type: form.actionType };
    }
    const minutes = Number.parseInt(form.snoozeMinutes.trim(), 10);
    if (!Number.isFinite(minutes) || minutes <= 0) {
        throw new Error("INVALID_SNOOZE_MINUTES");
    }
    const reason = form.snoozeReason.trim();
    return {
        type: "snooze_case",
        minutes,
        reason: reason || undefined,
    };
}

function buildActionPreview(form: MacroFormState): InboxMacroAction | null {
    if (form.actionType === "none") {
        return null;
    }
    if (form.actionType !== "snooze_case") {
        return { type: form.actionType };
    }
    const minutes = Number.parseInt(form.snoozeMinutes.trim(), 10);
    return {
        type: "snooze_case",
        minutes: Number.isFinite(minutes) && minutes > 0 ? minutes : 30,
        reason: form.snoozeReason.trim() || undefined,
    };
}

type ApiErrorPayload = { error?: { code?: string } };

function getErrorCode(error: unknown): string | null {
    const errorWithResponse = error as { response?: { data?: ApiErrorPayload } };
    return errorWithResponse?.response?.data?.error?.code ?? null;
}

function InboxMacros({
    onSelect,
    disabled,
    canManage = false,
    branchId,
    caseId,
}: InboxMacrosProps) {
    const queryClient = useQueryClient();
    const [panelOpen, setPanelOpen] = useState(false);
    const [panelMode, setPanelMode] = useState<"use" | "manage">("use");
    const [searchValue, setSearchValue] = useState("");
    const [editing, setEditing] = useState<InboxMacro | null>(null);
    const [form, setForm] = useState<MacroFormState>(() => buildFormState());

    const macrosQuery = useQuery({
        queryKey: ["inbox-macros", branchId],
        queryFn: async () => {
            const response = await inboxApi.listMacros({ include_inactive: canManage }, branchId);
            return response.data;
        },
        enabled: Boolean(branchId),
    });

    const createMutation = useMutation({
        mutationFn: async (payload: components["schemas"]["ConsoleMacroCreateRequest"]) => {
            const response = await inboxApi.createMacro(payload, branchId);
            return response.data;
        },
        onSuccess: (data) => {
            const createdMacro = data.macro;
            if (createdMacro) {
                queryClient.setQueryData<InboxMacroListResponse | undefined>(
                    ["inbox-macros", branchId],
                    (current) => {
                        const items = current?.items ?? [];
                        const nextItems = items.filter((macro) => macro.id !== createdMacro.id);
                        return { items: [createdMacro, ...nextItems] };
                    }
                );
            }
            setSearchValue("");
            toast.success("Макрос сохранён");
        },
        onError: () => {
            toast.error("Не удалось сохранить макрос");
        },
    });

    const updateMutation = useMutation({
        mutationFn: async ({
            macroId,
            payload,
        }: {
            macroId: string;
            payload: components["schemas"]["ConsoleMacroUpdateRequest"];
        }) => {
            const response = await inboxApi.updateMacro(macroId, payload, branchId);
            return response.data;
        },
        onSuccess: (updatedMacro) => {
            queryClient.setQueryData<InboxMacroListResponse | undefined>(
                ["inbox-macros", branchId],
                (current) => {
                    if (!current?.items) {
                        return current;
                    }
                    return {
                        items: current.items.map((macro) =>
                            macro.id === updatedMacro.id ? updatedMacro : macro
                        ),
                    };
                }
            );
            toast.success("Макрос обновлён");
            queryClient.invalidateQueries({ queryKey: ["inbox-macros", branchId] });
        },
        onError: () => {
            toast.error("Не удалось обновить макрос");
        },
    });

    const executeMutation = useMutation({
        mutationFn: async (macro: InboxMacro) => {
            if (!caseId) {
                throw new Error("CASE_REQUIRED");
            }
            const response = await inboxApi.executeMacro(
                macro.id,
                { case_id: caseId },
                branchId,
            );
            return response.data;
        },
        onSuccess: (data) => {
            if (caseId) {
                queryClient.setQueryData(["case", caseId], data.case);
                queryClient.invalidateQueries({ queryKey: ["cases"] });
            }
            if (data.macro.body?.trim()) {
                onSelect(data.macro.body);
            }
            const actionLabel = getMacroActionLabel(data.macro.action);
            const suffix = data.macro.body?.trim() ? " Текст добавлен в черновик." : "";
            toast.success(`Применено: ${actionLabel}.${suffix}`);
            const followupMessages = collectCaseActionFollowupMessages(data.sync);
            if (followupMessages.length > 0) {
                toast(followupMessages.join(" "), { icon: "⚠️" });
            }
        },
        onError: (error: unknown) => {
            const code = getErrorCode(error);
            if (code === "CASE_NOT_ACTIVE") {
                toast.error("Это действие недоступно для текущего статуса заявки");
                return;
            }
            if (code === "CASE_ALREADY_RESOLVED") {
                toast.error("Заявка уже закрыта");
                return;
            }
            toast.error("Не удалось применить макрос");
        },
    });

    const macros = useMemo(() => macrosQuery.data?.items ?? [], [macrosQuery.data?.items]);
    const sortedMacros = useMemo(() => sortMacros(macros), [macros]);
    const activeMacros = macros.filter((macro) => macro.is_active);
    const sortedActiveMacros = useMemo(() => sortMacros(activeMacros), [activeMacros]);
    const primaryMacros = sortedActiveMacros.slice(0, 6);
    const macrosErrorCode = getErrorCode(macrosQuery.error);
    const selectionMessages: Record<string, string> = {
        COMPANY_SELECTION_REQUIRED: "Выберите компанию вверху, чтобы загрузить быстрые ответы.",
        CLIENT_SELECTION_REQUIRED: "Выберите клиента вверху, чтобы загрузить быстрые ответы.",
        BRANCH_SELECTION_REQUIRED: "Выберите филиал вверху, чтобы загрузить быстрые ответы.",
        BRANCH_ACCESS_DENIED: "Нет доступа к филиалу. Обновите контекст вверху.",
        TENANT_MISMATCH: "Контекст не совпадает с доступом. Обновите выбор.",
    };
    const selectionMessage = macrosErrorCode ? selectionMessages[macrosErrorCode] : null;
    const normalizedSearch = searchValue.trim().toLowerCase();
    const filteredMacros = useMemo(() => {
        if (!normalizedSearch) {
            return sortedMacros;
        }
        return sortedMacros.filter((macro) => {
            const label = macro.label?.toLowerCase() ?? "";
            const body = macro.body?.toLowerCase() ?? "";
            return label.includes(normalizedSearch) || body.includes(normalizedSearch);
        });
    }, [sortedMacros, normalizedSearch]);
    const filteredActiveMacros = filteredMacros.filter((macro) => macro.is_active);
    const personalMacros = filteredMacros.filter((macro) => macro.scope === "personal");
    const teamMacros = filteredMacros.filter((macro) => macro.scope === "team");
    const personalActiveMacros = filteredActiveMacros.filter((macro) => macro.scope === "personal");
    const teamActiveMacros = filteredActiveMacros.filter((macro) => macro.scope === "team");
    const previewAction = useMemo(() => buildActionPreview(form), [form]);

    const canEdit = canManage;
    const isSaving = createMutation.isPending || updateMutation.isPending;
    const isApplying = executeMutation.isPending;
    const tabClass = (active: boolean) => (
        `rounded-full border px-3 py-1 text-xs font-semibold transition ${
            active
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border/60 text-muted-foreground hover:text-foreground"
        }`
    );

    const resetForm = () => {
        setEditing(null);
        setForm(buildFormState());
    };

    const handleEdit = (macro: InboxMacro) => {
        setEditing(macro);
        setForm(buildFormState(macro));
        setPanelMode("manage");
        setPanelOpen(true);
    };

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault();
        const label = form.label.trim();
        const body = form.body.trim();
        if (!label || !body) {
            toast.error("Заполните заголовок и текст");
            return;
        }
        let action: InboxMacroAction | null = null;
        try {
            action = buildActionPayload(form);
        } catch (error) {
            if (error instanceof Error && error.message === "INVALID_SNOOZE_MINUTES") {
                toast.error("Укажите корректное время отсрочки в минутах");
                return;
            }
            throw error;
        }
        if (editing) {
            await updateMutation.mutateAsync({
                macroId: editing.id,
                payload: { label, body, action },
            });
        } else {
            await createMutation.mutateAsync({
                scope: form.scope,
                label,
                body,
                action,
                is_active: true,
            });
        }
        resetForm();
    };

    const handleToggleActive = async (macro: InboxMacro) => {
        await updateMutation.mutateAsync({
            macroId: macro.id,
            payload: { is_active: !macro.is_active },
        });
    };

    const handleApplyMacro = async (macro: InboxMacro) => {
        if (disabled) {
            return;
        }
        if (!macro.action) {
            onSelect(macro.body);
            return;
        }
        if (!caseId) {
            toast.error("Откройте заявку, чтобы применить действие макроса");
            return;
        }
        await executeMutation.mutateAsync(macro);
    };

    if (!branchId) {
        return (
            <div className="rounded-lg border border-border/60 bg-card px-3 py-2 text-xs text-muted-foreground">
                Выберите филиал, чтобы загрузить быстрые ответы.
            </div>
        );
    }

    return (
        <div className="space-y-2" data-testid="inbox-macros">
            <div className="flex items-center justify-between gap-3">
                <div className="text-xs text-muted-foreground">Быстрые ответы</div>
                <button
                    type="button"
                    onClick={() => {
                        setPanelMode("use");
                        setPanelOpen((prev) => !prev);
                    }}
                    className="text-xs font-semibold text-primary hover:text-primary/80"
                >
                    {panelOpen ? "Скрыть ответы" : "Все ответы"}
                </button>
            </div>

            {macrosQuery.isLoading ? (
                <div className="rounded-lg border border-border/60 bg-card px-3 py-2 text-xs text-muted-foreground">
                    Загружаем макросы...
                </div>
            ) : macrosQuery.isError ? (
                <div className="rounded-lg border border-border/60 bg-card px-3 py-2 text-xs text-muted-foreground flex items-center justify-between gap-3">
                    <span>{selectionMessage ?? "Не удалось загрузить быстрые ответы."}</span>
                    <button
                        type="button"
                        onClick={() => macrosQuery.refetch()}
                        className="text-xs font-semibold text-primary hover:text-primary/80 disabled:opacity-60"
                        disabled={macrosQuery.isFetching}
                    >
                        {selectionMessage ? "Обновить" : "Повторить"}
                    </button>
                </div>
            ) : primaryMacros.length === 0 ? (
                <div className="rounded-lg border border-border/60 bg-card px-3 py-2 text-xs text-muted-foreground flex items-center justify-between gap-3">
                    <span>Нет быстрых ответов.</span>
                    {canManage && (
                        <button
                            type="button"
                            onClick={() => {
                                setPanelMode("manage");
                                setPanelOpen(true);
                            }}
                            className="text-xs font-semibold text-primary hover:text-primary/80"
                        >
                            Создать
                        </button>
                    )}
                </div>
            ) : (
                <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                        {primaryMacros.map((macro) => (
                            <button
                                key={macro.id}
                                type="button"
                                onClick={() => void handleApplyMacro(macro)}
                                disabled={disabled || isApplying}
                                data-testid={`macro-chip-${macro.id}`}
                                className="inline-flex items-center gap-2 rounded-full border border-border/60 bg-card px-3 py-1 text-xs font-semibold transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                <span>{macro.label}</span>
                                {macro.action && (
                                    <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                                        Действие
                                    </span>
                                )}
                            </button>
                        ))}
                    </div>
                    {sortedActiveMacros.some((macro) => Boolean(macro.action)) && (
                        <p className="text-[11px] text-muted-foreground">
                            Макросы с пометкой «Действие» меняют статус заявки и добавляют текст в черновик.
                        </p>
                    )}
                </div>
            )}

            {panelOpen && (
                <div className="rounded-lg border border-border/60 bg-card p-3 space-y-4 max-h-[60vh] xl:max-h-[40vh] overflow-y-auto">
                    {canManage && (
                        <div className="flex flex-wrap gap-2">
                            <button type="button" onClick={() => setPanelMode("use")} className={tabClass(panelMode === "use")}>
                                Ответы
                            </button>
                            <button type="button" onClick={() => setPanelMode("manage")} className={tabClass(panelMode === "manage")}>
                                Управление
                            </button>
                        </div>
                    )}

                    <div className="flex items-center gap-2">
                        <input
                            type="text"
                            value={searchValue}
                            onChange={(event) => setSearchValue(event.target.value)}
                            placeholder="Поиск по быстрым ответам"
                            className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-xs"
                        />
                        {searchValue.trim() && (
                            <button
                                type="button"
                                onClick={() => setSearchValue("")}
                                className="text-xs text-muted-foreground hover:text-foreground"
                            >
                                Сбросить
                            </button>
                        )}
                    </div>

                    {panelMode === "use" && (
                        <div className="space-y-3">
                            {filteredActiveMacros.length === 0 ? (
                                <div className="rounded-lg border border-border/60 bg-background px-3 py-2 text-xs text-muted-foreground">
                                    Нет активных быстрых ответов.
                                </div>
                            ) : (
                                [{ title: "Мои ответы", items: personalActiveMacros }, { title: "Командные", items: teamActiveMacros }].map((section) => (
                                    <div key={section.title} className="space-y-2">
                                        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                                            {section.title}
                                        </p>
                                        {section.items.length === 0 ? (
                                            <p className="text-xs text-muted-foreground">Пока нет ответов.</p>
                                        ) : (
                                            <div className="grid gap-2">
                                                {section.items.map((macro) => (
                                                    <button
                                                        key={macro.id}
                                                        type="button"
                                                        onClick={() => void handleApplyMacro(macro)}
                                                        disabled={disabled || isApplying}
                                                        data-testid={`macro-apply-${macro.id}`}
                                                        className="rounded-xl border border-border/60 bg-background px-3 py-2 text-left text-xs transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                                                    >
                                                        <div className="flex items-start justify-between gap-2">
                                                            <div>
                                                                <div className="text-sm font-semibold">{macro.label}</div>
                                                                <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                                                    {macro.body}
                                                                </div>
                                                            </div>
                                                            <span className="text-[10px] text-muted-foreground">
                                                                {getScopeLabel(macro.scope)}
                                                            </span>
                                                        </div>
                                                        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
                                                            <span className="rounded-full bg-muted px-2 py-0.5 font-semibold text-foreground">
                                                                {getMacroActionLabel(macro.action)}
                                                            </span>
                                                            <span className="text-muted-foreground">
                                                                {getMacroActionHint(macro.action)}
                                                            </span>
                                                        </div>
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {panelMode === "manage" && (
                        <>
                            <div className="space-y-3">
                                {[{ title: "Личные", items: personalMacros }, { title: "Командные", items: teamMacros }].map((section) => (
                                    <div key={section.title} className="space-y-2">
                                        <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                                            {section.title}
                                        </p>
                                        {section.items.length === 0 ? (
                                            <p className="text-xs text-muted-foreground">Пока нет макросов.</p>
                                        ) : (
                                            <div className="grid gap-2">
                                                {section.items.map((macro) => (
                                                    <div
                                                        key={macro.id}
                                                        className={`rounded-xl border border-border/60 bg-background px-3 py-2 text-xs ${
                                                            macro.is_active ? "" : "opacity-70"
                                                        }`}
                                                    >
                                                        <div className="flex items-start justify-between gap-2">
                                                            <div>
                                                                <div className="text-sm font-semibold">{macro.label}</div>
                                                                <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                                                    {macro.body}
                                                                </div>
                                                                <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
                                                                    <span className="rounded-full bg-muted px-2 py-0.5 font-semibold text-foreground">
                                                                        {getMacroActionLabel(macro.action)}
                                                                    </span>
                                                                    <span className="text-muted-foreground">
                                                                        {getMacroActionHint(macro.action)}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                            <span className="text-[10px] text-muted-foreground">
                                                                {getScopeLabel(macro.scope)}
                                                            </span>
                                                        </div>
                                                        <div className="flex flex-wrap gap-2 mt-2">
                                                            <button
                                                                type="button"
                                                                onClick={() => handleEdit(macro)}
                                                                className="text-xs text-primary hover:text-primary/80"
                                                                disabled={!canEdit}
                                                            >
                                                                Изменить
                                                            </button>
                                                            <button
                                                                type="button"
                                                                onClick={() => handleToggleActive(macro)}
                                                                className="text-xs text-muted-foreground hover:text-foreground"
                                                                disabled={!canEdit}
                                                            >
                                                                {macro.is_active ? "Отключить" : "Включить"}
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>

                            <form onSubmit={handleSubmit} className="rounded-lg border border-border/60 bg-background p-3 space-y-3">
                                <div className="flex items-center justify-between">
                                    <p className="text-xs font-semibold text-foreground">
                                        {editing ? "Редактировать макрос" : "Новый макрос"}
                                    </p>
                                    {editing && (
                                        <button
                                            type="button"
                                            onClick={resetForm}
                                            className="text-xs text-muted-foreground hover:text-foreground"
                                        >
                                            Отмена
                                        </button>
                                    )}
                                </div>
                                {!editing && (
                                    <div className="flex items-center gap-4 text-xs">
                                        {["personal", "team"].map((value) => (
                                            <label key={value} className="flex items-center gap-2">
                                                <input
                                                    type="radio"
                                                    name="macro-scope"
                                                    value={value}
                                                    checked={form.scope === value}
                                                    onChange={() => setForm((prev) => ({
                                                        ...prev,
                                                        scope: value as InboxMacro["scope"],
                                                    }))}
                                                />
                                                {value === "personal" ? "Личный" : "Командный"}
                                            </label>
                                        ))}
                                    </div>
                                )}
                                <div className="space-y-2">
                                    <input
                                        type="text"
                                        value={form.label}
                                        onChange={(event) => setForm((prev) => ({ ...prev, label: event.target.value }))}
                                        placeholder="Заголовок"
                                        className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-xs"
                                        disabled={isSaving}
                                    />
                                    <textarea
                                        value={form.body}
                                        onChange={(event) => setForm((prev) => ({ ...prev, body: event.target.value }))}
                                        placeholder="Текст быстрого ответа"
                                        rows={3}
                                        className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-xs resize-none"
                                        disabled={isSaving}
                                    />
                                </div>
                                <div className="space-y-2 rounded-lg border border-border/60 bg-card px-3 py-3">
                                    <div>
                                        <p className="text-xs font-semibold text-foreground">Действие по заявке</p>
                                        <p className="mt-1 text-[11px] text-muted-foreground">
                                            Выполнится, когда менеджер применит макрос в открытой заявке.
                                        </p>
                                    </div>
                                    <select
                                        value={form.actionType}
                                        onChange={(event) =>
                                            setForm((prev) => ({
                                                ...prev,
                                                actionType: event.target.value as MacroFormState["actionType"],
                                            }))
                                        }
                                        className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-xs"
                                        data-testid="macro-action-select"
                                        disabled={isSaving}
                                    >
                                        {MACRO_ACTION_OPTIONS.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                    {form.actionType === "snooze_case" && (
                                        <div className="grid gap-2 sm:grid-cols-[140px_minmax(0,1fr)]">
                                            <input
                                                type="number"
                                                min={5}
                                                step={5}
                                                value={form.snoozeMinutes}
                                                onChange={(event) =>
                                                    setForm((prev) => ({
                                                        ...prev,
                                                        snoozeMinutes: event.target.value,
                                                    }))
                                                }
                                                placeholder="Минуты"
                                                className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-xs"
                                                data-testid="macro-action-minutes"
                                                disabled={isSaving}
                                            />
                                            <input
                                                type="text"
                                                value={form.snoozeReason}
                                                onChange={(event) =>
                                                    setForm((prev) => ({
                                                        ...prev,
                                                        snoozeReason: event.target.value,
                                                    }))
                                                }
                                                placeholder="Причина отсрочки"
                                                className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-xs"
                                                disabled={isSaving}
                                            />
                                        </div>
                                    )}
                                    <div className="rounded-lg border border-border/60 bg-background px-3 py-2 text-[11px]">
                                        <div className="font-semibold text-foreground">
                                            {getMacroActionLabel(previewAction)}
                                        </div>
                                        <div className="mt-1 text-muted-foreground">
                                            {getMacroActionHint(previewAction)}
                                        </div>
                                    </div>
                                </div>
                                <button
                                    type="submit"
                                    className="w-full rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-60"
                                    data-testid="macro-save-button"
                                    disabled={!canEdit || isSaving}
                                >
                                    {editing ? "Сохранить" : "Добавить"}
                                </button>
                            </form>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

export function InboxMacroChips(props: InboxMacrosProps) {
    return <InboxMacros {...props} />;
}

export default InboxMacros;
