"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { inboxApi } from "@/lib/api-client";
import type { components } from "@/types/api.generated";

const DEFAULT_SCOPE: components["schemas"]["InboxMacro"]["scope"] = "personal";

type InboxMacro = components["schemas"]["InboxMacro"];
type InboxMacroListResponse = components["schemas"]["InboxMacroListResponse"];

type InboxMacrosProps = {
    onSelect: (text: string) => void;
    disabled?: boolean;
    canManage?: boolean;
    branchId?: string | null;
};

type MacroFormState = {
    scope: InboxMacro["scope"];
    label: string;
    body: string;
};

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
    if (!macro) {
        return { scope: DEFAULT_SCOPE, label: "", body: "" };
    }
    return {
        scope: macro.scope,
        label: macro.label ?? "",
        body: macro.body ?? "",
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
        mutationFn: async (payload: components["schemas"]["InboxMacroCreateRequest"]) => {
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
            payload: components["schemas"]["InboxMacroUpdateRequest"];
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

    const canEdit = canManage;
    const isSaving = createMutation.isPending || updateMutation.isPending;
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
        if (editing) {
            await updateMutation.mutateAsync({
                macroId: editing.id,
                payload: { label, body },
            });
        } else {
            await createMutation.mutateAsync({
                scope: form.scope,
                label,
                body,
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
                <div className="flex flex-wrap items-center gap-2">
                    {primaryMacros.map((macro) => (
                        <button
                            key={macro.id}
                            type="button"
                            onClick={() => onSelect(macro.body)}
                            disabled={disabled}
                            className="rounded-full border border-border/60 bg-card px-3 py-1 text-xs font-semibold transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            {macro.label}
                        </button>
                    ))}
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
                                                        onClick={() => onSelect(macro.body)}
                                                        disabled={disabled}
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
                                <button
                                    type="submit"
                                    className="w-full rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-60"
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
