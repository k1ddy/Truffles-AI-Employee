import type { ReactNode } from "react";
import type { Case, DecisionTraceEntry, Message } from "@/types";

function formatTimestamp(value?: string | null) {
    if (!value) {
        return "—";
    }
    return new Date(value).toLocaleString("ru-RU");
}

function getRoleLabel(role: string) {
    if (role === "user") {
        return "Клиент";
    }
    if (role === "manager") {
        return "Менеджер";
    }
    return "Бот";
}

function truncateText(value: string, max = 140) {
    if (value.length <= max) {
        return value;
    }
    return `${value.slice(0, max)}…`;
}

function getPrimaryContact(caseDetail: Case) {
    const phone = caseDetail.customer_phone
        || caseDetail.customer_remote_jid?.split("@")[0]
        || null;
    const name = caseDetail.customer_name || "Клиент";
    return { name, phone };
}

function extractExplainEntry(trace: DecisionTraceEntry[] | undefined) {
    if (!trace || trace.length === 0) {
        return null;
    }
    return [...trace].reverse().find((entry) => entry.decision || entry.meta) ?? null;
}

type DecisionMeta = Record<string, unknown>;

const META_LABELS: Record<string, string> = {
    action: "Действие",
    intent: "Интент",
    source: "Источник",
    policy_gate: "Policy",
    fact_source: "Источник фактов",
    info_sections: "Секции",
    service_query: "Запрос услуги",
    price_item: "Прайс",
    duration_item: "Длительность",
    consult_playbook_id: "Playbook",
    consult_selector: "Selector",
    rag_reason: "RAG",
    trace_id: "Trace ID",
    llm_used: "LLM",
    llm_degradation_reason: "LLM fallback",
};

const SUMMARY_GROUPS = [
    {
        title: "Что произошло",
        keys: ["action", "intent"],
    },
    {
        title: "Почему",
        keys: ["source", "policy_gate", "rag_reason"],
    },
    {
        title: "Что использовано",
        keys: [
            "info_sections",
            "service_query",
            "price_item",
            "duration_item",
            "consult_playbook_id",
            "consult_selector",
            "fact_source",
        ],
    },
    {
        title: "Тех. метки",
        keys: ["trace_id", "llm_used", "llm_degradation_reason"],
    },
];

const MESSAGE_META_KEYS = ["action", "intent", "source", "policy_gate", "fact_source"];

function extractDecisionMeta(metadata: Message["metadata"]): DecisionMeta | null {
    if (!metadata || typeof metadata !== "object") {
        return null;
    }
    const raw = (metadata as Record<string, unknown>).decision_meta;
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
        return null;
    }
    return raw as DecisionMeta;
}

function formatMetaValue(value: unknown) {
    if (value === null || value === undefined) {
        return null;
    }
    if (["string", "number", "boolean"].includes(typeof value)) {
        return String(value);
    }
    if (Array.isArray(value)) {
        const flat = value
            .filter((item) => ["string", "number", "boolean"].includes(typeof item))
            .map((item) => String(item));
        if (flat.length === 0) {
            return null;
        }
        const visible = flat.slice(0, 4);
        const suffix = flat.length > 4 ? ` +${flat.length - 4}` : "";
        return `${visible.join(", ")}${suffix}`;
    }
    return null;
}

function buildMetaItems(meta: DecisionMeta | null, keys: string[]) {
    if (!meta) {
        return [];
    }
    return keys.flatMap((key) => {
        const value = formatMetaValue(meta[key]);
        if (!value) {
            return [];
        }
        return [
            {
                label: META_LABELS[key] ?? key,
                value,
            },
        ];
    });
}

function DetailCard({
    title,
    defaultOpen = false,
    children,
    emptyText,
}: {
    title: string;
    defaultOpen?: boolean;
    children: ReactNode;
    emptyText?: string;
}) {
    return (
        <details className="card-surface p-4 group" open={defaultOpen}>
            <summary className="flex items-center justify-between text-sm font-semibold cursor-pointer">
                <span>{title}</span>
                <span className="text-xs text-muted-foreground transition-transform group-open:rotate-180">▾</span>
            </summary>
            <div className="mt-3 text-sm text-foreground/90">
                {children ?? (
                    <p className="text-xs text-muted-foreground">{emptyText ?? "Нет данных"}</p>
                )}
            </div>
        </details>
    );
}

export default function CaseDetailsPanel({
    caseDetail,
    messages = [],
}: {
    caseDetail: Case;
    messages?: Message[];
}) {
    const contact = getPrimaryContact(caseDetail);
    const contextText = caseDetail.context_summary || caseDetail.user_message || "Контекст недоступен";
    const explainEntry = extractExplainEntry(caseDetail.decision_trace);
    const trace = caseDetail.decision_trace ?? [];
    const keyStages = trace
        .filter((entry) => ["policy_gate", "state_transition", "escalation", "booking"].includes(entry.stage))
        .slice(-5);
    const messageDiagnostics = messages.flatMap((message) => {
        const meta = extractDecisionMeta(message.metadata);
        if (!meta) {
            return [];
        }
        return [{ message, meta }];
    });
    const latestDecision = messageDiagnostics[0];
    const summaryGroups = latestDecision
        ? SUMMARY_GROUPS.map((group) => ({
            title: group.title,
            items: buildMetaItems(latestDecision.meta, group.keys),
        })).filter((group) => group.items.length > 0)
        : [];
    const hasTrace = trace.length > 0;
    const hasMessageDiagnostics = messageDiagnostics.length > 0;

    return (
        <div className="flex flex-col gap-4" data-testid="case-details">
            <DetailCard title="Контекст" defaultOpen>
                <div className="space-y-3">
                    <div>
                        <p className="font-medium">{contact.name}</p>
                        <p className="text-muted-foreground text-xs">
                            📱 {contact.phone ?? "Номер не указан"}
                        </p>
                        {caseDetail.customer_remote_jid && (
                            <p className="text-xs text-muted-foreground font-mono">
                                {caseDetail.customer_remote_jid}
                            </p>
                        )}
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground mb-1">Сводка</p>
                        <p className="bg-muted p-2 rounded border border-border/60 text-xs">
                            {contextText}
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs">
                        <span className="bg-muted px-2 py-1 rounded">
                            Триггер: {caseDetail.trigger_type}
                            {caseDetail.trigger_value ? ` • ${caseDetail.trigger_value}` : ""}
                        </span>
                        <span className="bg-muted px-2 py-1 rounded">Канал: {caseDetail.channel}</span>
                    </div>
                </div>
            </DetailCard>

            <DetailCard title="Health" defaultOpen>
                <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Последнее входящее:</span>
                        <span>{formatTimestamp(caseDetail.last_inbound_at)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Последнее исходящее:</span>
                        <span>{formatTimestamp(caseDetail.last_outbound_at)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Канал активности:</span>
                        <span>{caseDetail.last_activity_channel || "—"}</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {caseDetail.needs_reply && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-yellow-100 text-yellow-800">
                                NEW
                            </span>
                        )}
                        {caseDetail.has_pending_outbox && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-800">
                                QUEUED
                            </span>
                        )}
                        {caseDetail.has_delivery_error && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-red-100 text-red-800">
                                FAILED
                            </span>
                        )}
                    </div>
                </div>
            </DetailCard>

            <DetailCard title="Explain" defaultOpen={false}>
                {latestDecision ? (
                    <div className="space-y-4 text-xs">
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                            <span className="bg-muted px-2 py-1 rounded">Последнее решение</span>
                            <span className="text-muted-foreground">{formatTimestamp(latestDecision.message.created_at)}</span>
                        </div>
                        <div className="rounded border border-border/60 bg-background px-3 py-2">
                            <p className="text-[11px] text-muted-foreground mb-1">
                                {getRoleLabel(latestDecision.message.role)} • {latestDecision.message.role}
                            </p>
                            <p className="text-sm font-medium">
                                {truncateText(latestDecision.message.content)}
                            </p>
                        </div>
                        {summaryGroups.length > 0 ? (
                            <div className="grid gap-3 sm:grid-cols-2">
                                {summaryGroups.map((group) => (
                                    <div key={group.title} className="space-y-2">
                                        <p className="text-[11px] uppercase text-muted-foreground">{group.title}</p>
                                        <div className="flex flex-wrap gap-2">
                                            {group.items.map((item) => (
                                                <span key={`${group.title}-${item.label}`} className="bg-muted px-2 py-1 rounded">
                                                    {item.label}: {item.value}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-xs text-muted-foreground">decision_meta есть, но без ключевых полей.</p>
                        )}
                    </div>
                ) : explainEntry ? (
                    <div className="space-y-2 text-xs">
                        <div className="flex flex-wrap gap-2">
                            <span className="bg-muted px-2 py-1 rounded">{explainEntry.stage}</span>
                            {explainEntry.decision && (
                                <span className="bg-muted px-2 py-1 rounded">{explainEntry.decision}</span>
                            )}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            decision_meta не записан для сообщений, показаны последние trace‑стадии.
                        </p>
                    </div>
                ) : (
                    <p className="text-xs text-muted-foreground">Объяснение недоступно.</p>
                )}
            </DetailCard>

            <DetailCard title="Trace" defaultOpen={false}>
                {hasTrace || hasMessageDiagnostics ? (
                    <div className="space-y-3">
                        {hasTrace && keyStages.length > 0 && (
                            <div className="flex flex-wrap gap-2 text-xs">
                                {keyStages.map((entry, idx) => {
                                    const stageClass = entry.stage === "policy_gate"
                                        ? "bg-purple-100 text-purple-700"
                                        : entry.stage === "escalation"
                                            ? "bg-red-100 text-red-700"
                                            : entry.stage === "booking"
                                                ? "bg-green-100 text-green-700"
                                                : "bg-secondary text-secondary-foreground";
                                    return (
                                        <span key={`${entry.stage}-${idx}`} className={`px-2 py-0.5 rounded ${stageClass}`}>
                                            {entry.stage}
                                        </span>
                                    );
                                })}
                            </div>
                        )}
                        {hasMessageDiagnostics && (
                            <div className="space-y-2">
                                <p className="text-xs text-muted-foreground">По сообщениям</p>
                                <div className="max-h-64 overflow-y-auto space-y-2 text-xs">
                                    {messageDiagnostics.map(({ message, meta }) => (
                                        <div
                                            key={message.id}
                                            className="bg-background p-3 rounded border border-border/60 space-y-2"
                                        >
                                            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                                                <span>{getRoleLabel(message.role)} • {message.role}</span>
                                                <span>{formatTimestamp(message.created_at)}</span>
                                            </div>
                                            <p className="text-xs text-foreground/90">
                                                {truncateText(message.content, 160)}
                                            </p>
                                            <div className="flex flex-wrap gap-2">
                                                {buildMetaItems(meta, MESSAGE_META_KEYS).map((item) => (
                                                    <span key={`${message.id}-${item.label}`} className="bg-muted px-2 py-1 rounded">
                                                        {item.label}: {item.value}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        <div className="space-y-2">
                            <p className="text-xs text-muted-foreground">Стадии пайплайна</p>
                            {hasTrace ? (
                                <div className="max-h-48 overflow-y-auto space-y-1 text-xs">
                                    {trace.map((entry, idx) => (
                                        <div
                                            key={`${entry.stage}-${idx}`}
                                            className="bg-background p-2 rounded border border-border/60"
                                        >
                                            <div className="flex items-center justify-between gap-2">
                                                <div className="flex items-center gap-2">
                                                    <span className="font-mono text-muted-foreground w-6">{idx + 1}.</span>
                                                    <span className="font-medium text-foreground">{entry.stage}</span>
                                                    {entry.decision && (
                                                        <span className="text-muted-foreground">: {entry.decision}</span>
                                                    )}
                                                </div>
                                                {entry.recorded_at && (
                                                    <span className="text-[11px] text-muted-foreground">
                                                        {formatTimestamp(entry.recorded_at)}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-xs text-muted-foreground">Trace ещё не записан.</p>
                            )}
                        </div>
                    </div>
                ) : (
                    <p className="text-xs text-muted-foreground">Trace ещё не записан.</p>
                )}
            </DetailCard>

            <DetailCard title="Telegram" defaultOpen={false}>
                {caseDetail.telegram_trail ? (
                    <div className="space-y-2 text-xs">
                        <div className="flex items-center gap-2">
                            <span className="text-muted-foreground">Статус:</span>
                            <span className={`px-2 py-0.5 rounded font-medium ${caseDetail.telegram_trail.delivery_status === "sent"
                                ? "bg-green-100 text-green-800"
                                : caseDetail.telegram_trail.delivery_status === "failed"
                                    ? "bg-red-100 text-red-800"
                                    : "bg-yellow-100 text-yellow-800"
                                }`}>
                                {caseDetail.telegram_trail.delivery_status === "sent"
                                    ? "✓ Доставлено"
                                    : caseDetail.telegram_trail.delivery_status === "failed"
                                        ? "✗ Ошибка"
                                        : "⏳ Ожидает"}
                            </span>
                        </div>
                        {caseDetail.telegram_trail.message_id && (
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground">Message ID:</span>
                                <span className="font-mono bg-muted px-1.5 py-0.5 rounded">
                                    {caseDetail.telegram_trail.message_id}
                                </span>
                            </div>
                        )}
                        {caseDetail.telegram_trail.topic_id && (
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground">Topic ID:</span>
                                <span className="font-mono bg-muted px-1.5 py-0.5 rounded">
                                    {caseDetail.telegram_trail.topic_id}
                                </span>
                            </div>
                        )}
                        {caseDetail.telegram_trail.delivered_at && (
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground">Отправлено:</span>
                                <span>{formatTimestamp(caseDetail.telegram_trail.delivered_at)}</span>
                            </div>
                        )}
                        {(caseDetail.telegram_trail.telegram_desktop_link || caseDetail.telegram_trail.telegram_link) && (
                            <div className="flex flex-wrap gap-2">
                                {caseDetail.telegram_trail.telegram_desktop_link && (
                                    <a
                                        href={caseDetail.telegram_trail.telegram_desktop_link}
                                        className="inline-flex items-center gap-1 px-3 py-1.5 bg-primary text-primary-foreground rounded text-xs hover:bg-primary/90 transition-colors"
                                    >
                                        📲 Открыть в Telegram
                                    </a>
                                )}
                                {caseDetail.telegram_trail.telegram_link && (
                                    <a
                                        href={caseDetail.telegram_trail.telegram_link}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-1 px-3 py-1.5 border border-border/60 rounded text-xs hover:bg-muted transition-colors"
                                    >
                                        🌐 Открыть в Web
                                    </a>
                                )}
                            </div>
                        )}
                    </div>
                ) : (
                    <p className="text-xs text-muted-foreground">Telegram‑trail недоступен.</p>
                )}
            </DetailCard>
        </div>
    );
}
