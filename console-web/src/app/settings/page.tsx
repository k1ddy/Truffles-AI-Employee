"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { agentsApi, telegramApi } from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";

interface Branch {
    id: string;
    slug: string;
    name: string;
    is_active: boolean;
    instance_id?: string | null;
    telegram_chat_id?: string | null;
}

interface Agent {
    id: string;
    name: string | null;
    role: string;
    is_active: boolean;
    identities?: AgentIdentity[];
}

interface AgentIdentity {
    channel: "telegram";
    external_id: string;
    username?: string | null;
    linked_at?: string | null;
}

interface AgentLinkData {
    token: string;
    deep_link?: string | null;
    bot_username?: string | null;
    expires_at: string;
}

interface BotConfig {
    reminder_timeout_1: number | null;
    reminder_timeout_2: number | null;
    auto_close_timeout: number | null;
    quiet_hours_enabled: boolean;
    quiet_hours_start: string | null;
    quiet_hours_end: string | null;
    tone: string | null;
    autolearn_enabled: boolean;
    booking_enabled: boolean;
    enable_reminders: boolean;
    enable_owner_escalation: boolean;
}

interface SettingsData {
    branches: Branch[];
    bot_config: BotConfig | null;
}

async function fetchSettings(): Promise<SettingsData> {
    const response = await api.get("/settings");
    return response.data;
}

async function fetchAgents(): Promise<{ items: Agent[] }> {
    const response = await agentsApi.list();
    return response.data;
}

function RoleBadge({ role }: { role: string }) {
    const styles: Record<string, string> = {
        owner: "bg-purple-100 text-purple-800",
        admin: "bg-secondary text-secondary-foreground",
        manager: "bg-green-100 text-green-800",
        support: "bg-muted text-muted-foreground",
    };
    return (
        <span className={`px-2 py-1 rounded text-xs font-medium ${styles[role] || "bg-muted text-muted-foreground"}`}>
            {role}
        </span>
    );
}

function ConfigCard({ label, value, type = "text" }: { label: string; value: string | number | boolean | null; type?: string }) {
    let displayValue: React.ReactNode = value;

    if (type === "boolean") {
        displayValue = value ? (
            <span className="text-green-600 font-medium">✓ Включено</span>
        ) : (
            <span className="text-muted-foreground">Выключено</span>
        );
    } else if (type === "minutes" && typeof value === "number") {
        displayValue = `${value} мин`;
    } else if (value === null || value === undefined) {
        displayValue = <span className="text-muted-foreground">—</span>;
    }

    return (
        <div className="flex justify-between items-center py-2 border-b border-border/60 last:border-0">
            <span className="text-muted-foreground">{label}</span>
            <span className="font-medium">{displayValue}</span>
        </div>
    );
}

export default function SettingsPage() {
    const { data: session } = useSession();
    const { handleError } = useErrorHandler();
    const [verifyTarget, setVerifyTarget] = useState<string | null>(null);
    const [testTarget, setTestTarget] = useState<string | null>(null);
    const [linkTarget, setLinkTarget] = useState<string | null>(null);
    const [linkTokens, setLinkTokens] = useState<Record<string, AgentLinkData>>({});

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ["settings"],
        queryFn: fetchSettings,
        enabled: !!session,
    });

    const { data: agentsData, isLoading: agentsLoading, error: agentsError, refetch: refetchAgents } = useQuery({
        queryKey: ["agents"],
        queryFn: fetchAgents,
        enabled: !!session,
    });

    const verifyMutation = useMutation({
        mutationFn: async (action: { targetKey: string; label: string; payload: { scope: "client" | "branch"; branch_id?: string } }) => {
            const { data } = await telegramApi.verify(action.payload);
            return { data, action };
        },
        onMutate: (action) => {
            setVerifyTarget(action.targetKey);
        },
        onSuccess: ({ data, action }) => {
            if (data.success) {
                toast.success(`Код верификации (${action.label}): ${data.verification_code}`);
            } else {
                toast.error(data.error_message || `Не удалось отправить код (${action.label})`);
            }
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setVerifyTarget(null);
        },
    });

    const testMutation = useMutation({
        mutationFn: async (action: { targetKey: string; label: string; payload: { scope: "client" | "branch"; branch_id?: string; message?: string } }) => {
            const { data } = await telegramApi.test(action.payload);
            return { data, action };
        },
        onMutate: (action) => {
            setTestTarget(action.targetKey);
        },
        onSuccess: ({ data, action }) => {
            if (data.success) {
                toast.success(`Тестовое сообщение отправлено (${action.label})`);
            } else {
                toast.error(data.error_message || `Не удалось отправить тест (${action.label})`);
            }
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setTestTarget(null);
        },
    });

    const linkMutation = useMutation({
        mutationFn: async (agentId: string) => {
            const { data } = await agentsApi.linkTelegram(agentId);
            return { data, agentId };
        },
        onMutate: (agentId) => {
            setLinkTarget(agentId);
        },
        onSuccess: ({ data, agentId }) => {
            setLinkTokens((prev) => ({ ...prev, [agentId]: data }));
            toast.success("Ссылка для Telegram создана");
        },
        onError: (error) => {
            handleError(error);
        },
        onSettled: () => {
            setLinkTarget(null);
        },
    });

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра настроек.
            </div>
        );
    }

    if (isLoading || agentsLoading) {
        return (
            <div className="max-w-5xl mx-auto p-6" data-testid="settings-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="settings-title">Настройки</h1>
                <div className="animate-pulse grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="h-48 bg-muted/70 rounded-lg"></div>
                    <div className="h-48 bg-muted/70 rounded-lg"></div>
                    <div className="h-48 bg-muted/70 rounded-lg"></div>
                    <div className="h-48 bg-muted/70 rounded-lg"></div>
                </div>
            </div>
        );
    }

    if (error || agentsError) {
        return (
            <div className="max-w-5xl mx-auto p-6" data-testid="settings-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="settings-title">Настройки</h1>
                <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center" data-testid="settings-error">
                    <p className="text-destructive mb-4">Не удалось загрузить настройки</p>
                    <button
                        onClick={() => {
                            refetch();
                            refetchAgents();
                        }}
                        className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        data-testid="settings-retry"
                    >
                        Повторить
                    </button>
                </div>
            </div>
        );
    }

    const config = data?.bot_config;

    return (
        <div className="max-w-5xl mx-auto p-6" data-testid="settings-page">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold" data-testid="settings-title">Настройки</h1>
                <Link href="/" className="text-primary hover:text-primary/80">
                    ← Назад в Inbox
                </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* SLA & Reminders */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-sla">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        ⏱️ SLA и напоминания
                    </h2>
                    {config ? (
                        <div>
                            <ConfigCard label="Первое напоминание" value={config.reminder_timeout_1} type="minutes" />
                            <ConfigCard label="Второе напоминание" value={config.reminder_timeout_2} type="minutes" />
                            <ConfigCard label="Авто-закрытие" value={config.auto_close_timeout} type="minutes" />
                            <ConfigCard label="Напоминания включены" value={config.enable_reminders} type="boolean" />
                            <ConfigCard label="Эскалация на владельца" value={config.enable_owner_escalation} type="boolean" />
                        </div>
                    ) : (
                        <p className="text-muted-foreground text-center py-4">Нет данных</p>
                    )}
                </div>

                {/* Quiet Hours */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-quiet-hours">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        🌙 Тихие часы
                    </h2>
                    {config ? (
                        <div>
                            <ConfigCard label="Тихие часы" value={config.quiet_hours_enabled} type="boolean" />
                            <ConfigCard label="Начало" value={config.quiet_hours_start} />
                            <ConfigCard label="Конец" value={config.quiet_hours_end} />
                        </div>
                    ) : (
                        <p className="text-muted-foreground text-center py-4">Нет данных</p>
                    )}
                </div>

                {/* Bot Behavior */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-bot">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        🤖 Поведение бота
                    </h2>
                    {config ? (
                        <div>
                            <ConfigCard label="Тон общения" value={config.tone} />
                            <ConfigCard label="Авто-обучение" value={config.autolearn_enabled} type="boolean" />
                            <ConfigCard label="Бронирование" value={config.booking_enabled} type="boolean" />
                        </div>
                    ) : (
                        <p className="text-muted-foreground text-center py-4">Нет данных</p>
                    )}
                </div>

                {/* Telegram Connector */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-telegram-connector">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        📨 Telegram коннектор
                    </h2>
                    <p className="text-sm text-muted-foreground mb-3">
                        Проверка и тест отправки в Telegram (client scope, owner/admin).
                    </p>
                    <div className="flex items-center gap-2">
                        <button
                            type="button"
                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() =>
                                verifyMutation.mutate({
                                    targetKey: "client",
                                    label: "client",
                                    payload: { scope: "client" },
                                })
                            }
                            disabled={verifyTarget === "client"}
                            data-testid="settings-telegram-verify"
                        >
                            {verifyTarget === "client" ? "Отправка..." : "Verify"}
                        </button>
                        <button
                            type="button"
                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() =>
                                testMutation.mutate({
                                    targetKey: "client",
                                    label: "client",
                                    payload: { scope: "client" },
                                })
                            }
                            disabled={testTarget === "client"}
                            data-testid="settings-telegram-test"
                        >
                            {testTarget === "client" ? "Отправка..." : "Send test"}
                        </button>
                    </div>
                </div>

                {/* Branches (TG-02) */}
                <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-branches">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        🏢 Филиалы
                    </h2>
                    <div className="space-y-2">
                        {data?.branches.map((branch) => (
                            <div
                                key={branch.id}
                                className="flex items-center justify-between p-3 bg-muted rounded"
                                data-testid="settings-branch-row"
                            >
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className="font-medium">{branch.name}</span>
                                        <span className="text-sm text-muted-foreground">({branch.slug})</span>
                                    </div>
                                    <div className="text-xs text-muted-foreground mt-1">
                                        instance_id: {branch.instance_id || "—"}
                                    </div>
                                    {/* Telegram status */}
                                    <div className="flex items-center gap-1 mt-1">
                                        {branch.telegram_chat_id ? (
                                            <>
                                                <span className="text-primary text-xs">📨</span>
                                                <span className="text-xs text-muted-foreground font-mono">
                                                    {branch.telegram_chat_id.slice(0, 15)}...
                                                </span>
                                            </>
                                        ) : (
                                            <span className="text-xs text-muted-foreground">Telegram не настроен</span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span
                                        className={`px-2 py-0.5 rounded text-xs ${branch.is_active
                                            ? "bg-green-100 text-green-800"
                                            : "bg-muted text-muted-foreground"
                                            }`}
                                    >
                                        {branch.is_active ? "Активен" : "Неактивен"}
                                    </span>
                                    <button
                                        type="button"
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                        onClick={() =>
                                            verifyMutation.mutate({
                                                targetKey: branch.id,
                                                label: branch.name,
                                                payload: { scope: "branch", branch_id: branch.id },
                                            })
                                        }
                                        disabled={!branch.telegram_chat_id || verifyTarget === branch.id}
                                        data-testid="settings-branch-verify"
                                    >
                                        {verifyTarget === branch.id ? "Отправка..." : "Verify"}
                                    </button>
                                    <button
                                        type="button"
                                        className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                        onClick={() =>
                                            testMutation.mutate({
                                                targetKey: branch.id,
                                                label: branch.name,
                                                payload: { scope: "branch", branch_id: branch.id },
                                            })
                                        }
                                        disabled={!branch.telegram_chat_id || testTarget === branch.id}
                                        data-testid="settings-branch-test"
                                    >
                                        {testTarget === branch.id ? "Отправка..." : "Send test"}
                                    </button>
                                </div>
                            </div>
                        ))}
                        {data?.branches.length === 0 && (
                            <p className="text-muted-foreground text-center py-2" data-testid="settings-branches-empty">Нет филиалов</p>
                        )}
                    </div>
                </div>
            </div>

            {/* Team Members - Full Width */}
            <div className="bg-card border border-border/60 rounded-lg p-5 mt-6" data-testid="settings-team">
                <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    👥 Команда
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {agentsData?.items.map((agent) => {
                        const telegramIdentity = agent.identities?.find((identity) => identity.channel === "telegram");
                        const linkData = linkTokens[agent.id];
                        const displayHandle = telegramIdentity?.username
                            ? `@${telegramIdentity.username}`
                            : telegramIdentity?.external_id;

                        return (
                        <div
                            key={agent.id}
                            className="flex flex-col gap-2 p-3 bg-muted rounded"
                            data-testid="settings-team-row"
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-9 h-9 bg-secondary rounded-full flex items-center justify-center text-secondary-foreground font-medium">
                                        {agent.name?.charAt(0).toUpperCase() || "?"}
                                    </div>
                                    <span className="font-medium">{agent.name || "Без имени"}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <RoleBadge role={agent.role} />
                                    <span
                                        className={`w-2 h-2 rounded-full ${agent.is_active ? "bg-green-500" : "bg-muted"
                                            }`}
                                    ></span>
                                </div>
                            </div>
                            <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Telegram:</span>
                                <span className={telegramIdentity ? "font-medium" : "text-muted-foreground"}>
                                    {telegramIdentity ? displayHandle : "не подключен"}
                                </span>
                            </div>
                            <div className="flex items-center justify-between gap-2">
                                <button
                                    type="button"
                                    className="rounded-full border border-border/60 px-3 py-1 text-xs font-medium hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                                    onClick={() => linkMutation.mutate(agent.id)}
                                    disabled={linkTarget === agent.id}
                                    data-testid="settings-team-link"
                                >
                                    {linkTarget === agent.id
                                        ? "Генерация..."
                                        : telegramIdentity
                                            ? "Переподключить"
                                            : "Подключить Telegram"}
                                </button>
                                {telegramIdentity?.linked_at && (
                                    <span className="text-xs text-muted-foreground">
                                        {new Date(telegramIdentity.linked_at).toLocaleDateString("ru-RU")}
                                    </span>
                                )}
                            </div>
                            {linkData && (
                                <div className="text-xs bg-background p-2 rounded border border-border/60 space-y-1">
                                    <div>
                                        Код: <span className="font-mono">{linkData.token}</span>
                                    </div>
                                    {linkData.deep_link && (
                                        <Link className="text-primary underline" href={linkData.deep_link} target="_blank">
                                            Открыть в Telegram
                                        </Link>
                                    )}
                                    <div className="text-muted-foreground">
                                        Отправьте боту <span className="font-mono">/start {linkData.token}</span>
                                    </div>
                                    <div className="text-muted-foreground">
                                        Истекает: {new Date(linkData.expires_at).toLocaleString("ru-RU")}
                                    </div>
                                </div>
                            )}
                        </div>
                        );
                    })}
                    {agentsData?.items.length === 0 && (
                        <p className="text-muted-foreground text-center py-4 col-span-3" data-testid="settings-team-empty">
                            Нет участников команды
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
