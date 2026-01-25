"use client";

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

type InboxMacrosProps = {
    onSelect: (text: string) => void;
    disabled?: boolean;
};

export default function InboxMacros({ onSelect, disabled }: InboxMacrosProps) {
    const groups = Array.from(new Set(MACROS.map((macro) => macro.group)));

    return (
        <div className="card-surface p-4" data-testid="inbox-macros">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold">Quick Replies</h3>
                <span className="text-xs text-muted-foreground">макросы</span>
            </div>
            <div className="space-y-4">
                {groups.map((group) => (
                    <div key={group} className="space-y-2">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                            {group}
                        </p>
                        <div className="grid gap-2">
                            {MACROS.filter((macro) => macro.group === group).map((macro) => (
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
