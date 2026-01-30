"use client";

import { useMemo, useState } from "react";

const MACROS = [
    {
        id: "system-greeting",
        group: "Системные",
        label: "Приветствие",
        body: "Здравствуйте! Я менеджер Truffles. Чем можем помочь?",
    },
    {
        id: "system-clarify",
        group: "Системные",
        label: "Уточнить",
        body: "Подскажите, пожалуйста, удобное время и услугу, чтобы я всё проверил.",
    },
    {
        id: "system-escalate",
        group: "Системные",
        label: "Эскалация",
        body: "Передаю вопрос владельцу. Вернусь с ответом в ближайшее время.",
    },
    {
        id: "client-pricing",
        group: "Клиентские",
        label: "Цена",
        body: "Стоимость зависит от выбранной услуги. Напишите, что именно вас интересует.",
    },
    {
        id: "client-booking",
        group: "Клиентские",
        label: "Запись",
        body: "Могу записать вас на удобное время. Напишите предпочтительную дату и время.",
    },
] as const;

type Macro = (typeof MACROS)[number];

function getMacroGroups(macros: readonly Macro[]) {
    const groups = Array.from(new Set(macros.map((macro) => macro.group)));
    return groups.map((group) => ({
        group,
        items: macros.filter((macro) => macro.group === group),
    }));
}

type InboxMacrosProps = {
    onSelect: (text: string) => void;
    disabled?: boolean;
};

export function InboxMacroChips({ onSelect, disabled }: InboxMacrosProps) {
    const [expanded, setExpanded] = useState(false);
    const primaryMacros = MACROS.slice(0, 4);
    const groups = useMemo(() => getMacroGroups(MACROS), []);

    return (
        <div className="space-y-3">
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
                <button
                    type="button"
                    onClick={() => setExpanded((prev) => !prev)}
                    className="text-xs text-muted-foreground hover:text-foreground"
                    disabled={disabled}
                >
                    {expanded ? "Скрыть макросы" : "Все макросы"}
                </button>
            </div>
            {expanded && (
                <div className="rounded-lg border border-border/60 bg-card p-3">
                    <div className="space-y-4">
                        {groups.map((group) => (
                            <div key={group.group} className="space-y-2">
                                <p className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                                    {group.group}
                                </p>
                                <div className="grid gap-2">
                                    {group.items.map((macro) => (
                                        <button
                                            key={macro.id}
                                            type="button"
                                            onClick={() => onSelect(macro.body)}
                                            disabled={disabled}
                                            className="rounded-xl border border-border/60 bg-background px-3 py-2 text-left text-xs font-medium transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            <div className="text-sm font-semibold">{macro.label}</div>
                                            <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                                {macro.body}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default function InboxMacros({ onSelect, disabled }: InboxMacrosProps) {
    const groups = useMemo(() => getMacroGroups(MACROS), []);

    return (
        <div className="card-surface p-4" data-testid="inbox-macros">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold">Quick Replies</h3>
                <span className="text-xs text-muted-foreground">макросы</span>
            </div>
            <div className="space-y-4">
                {groups.map((group) => (
                    <div key={group.group} className="space-y-2">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                            {group.group}
                        </p>
                        <div className="grid gap-2">
                            {group.items.map((macro) => (
                                <button
                                    key={macro.id}
                                    type="button"
                                    onClick={() => onSelect(macro.body)}
                                    disabled={disabled}
                                    className="rounded-xl border border-border/60 bg-card px-3 py-2 text-left text-xs font-medium transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    <div className="text-sm font-semibold">{macro.label}</div>
                                    <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                        {macro.body}
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
