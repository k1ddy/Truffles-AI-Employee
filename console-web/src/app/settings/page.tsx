"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { authApi, canAccessConsole, settingsApi, telegramApi } from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";
import AccessDenied from "@/components/AccessDenied";
import ProvisioningWizard from "@/components/ProvisioningWizard";

interface Branch {
    id: string;
    slug: string;
    name: string;
    is_active: boolean;
    instance_id?: string | null;
    telegram_chat_id?: string | null;
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
    learning_consent_status?: string | null;
    learning_anonymization_mode?: string | null;
    learning_retention_days?: number | null;
    data_sharing?: string | null;
}

interface SettingsData {
    branches: Branch[];
    bot_config: BotConfig | null;
}

interface SimpleSettingsForm {
    reminder1: string;
    reminder2: string;
    escalation: string;
}

interface SettingsPreset {
    id: string;
    label: string;
    reminder1: number;
    reminder2: number;
    escalation: number;
    description: string;
}

async function fetchSettings(): Promise<SettingsData> {
    const response = await api.get("/settings");
    return response.data;
}

const SETTINGS_PRESETS: SettingsPreset[] = [
    {
        id: "fast",
        label: "Быстрый сервис",
        reminder1: 5,
        reminder2: 30,
        escalation: 60,
        description: "Подходит для активного sales-окна и быстрой реакции менеджера.",
    },
    {
        id: "balanced",
        label: "Сбалансированный",
        reminder1: 10,
        reminder2: 45,
        escalation: 120,
        description: "Рекомендуемый профиль по умолчанию для стабильной нагрузки.",
    },
    {
        id: "careful",
        label: "Бережный к команде",
        reminder1: 15,
        reminder2: 60,
        escalation: 180,
        description: "Для небольших команд, когда важнее снизить давление на менеджеров.",
    },
];

function parsePositiveInt(value: string): number | null {
    const parsed = Number(value.trim());
    if (!Number.isInteger(parsed) || parsed <= 0) {
        return null;
    }
    return parsed;
}


function ConfigCard({ label, value, type = "text" }: { label: string; value: string | number | boolean | null | undefined; type?: string }) {
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
    const buildSha = process.env.NEXT_PUBLIC_BUILD_SHA;
    const buildTime = process.env.NEXT_PUBLIC_BUILD_TIME;
    const buildShaLabel = buildSha ? buildSha.slice(0, 7) : "unknown";
    const buildTimeLabel = buildTime ?? "unknown";

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadSettings = canAccessConsole(role, "settings", "read");
    const canWriteSettings = canAccessConsole(role, "settings", "write");
    const canReadProvisioning = canAccessConsole(role, "provisioning", "read");
    const canViewSettings = canReadSettings || canReadProvisioning;

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ["settings"],
        queryFn: fetchSettings,
        enabled: !!session && canReadSettings,
    });
    const config = data?.bot_config;
    const [simpleSettings, setSimpleSettings] = useState<SimpleSettingsForm>({
        reminder1: "",
        reminder2: "",
        escalation: "",
    });
    const [selectedPresetId, setSelectedPresetId] = useState<string>("balanced");

    useEffect(() => {
        if (!config) {
            return;
        }
        setSimpleSettings({
            reminder1: String(config.reminder_timeout_1 ?? 10),
            reminder2: String(config.reminder_timeout_2 ?? 45),
            escalation: String(config.auto_close_timeout ?? 120),
        });
        if (config.reminder_timeout_1 === 5 && config.reminder_timeout_2 === 30 && config.auto_close_timeout === 60) {
            setSelectedPresetId("fast");
            return;
        }
        if (config.reminder_timeout_1 === 15 && config.reminder_timeout_2 === 60 && config.auto_close_timeout === 180) {
            setSelectedPresetId("careful");
            return;
        }
        setSelectedPresetId("balanced");
    }, [config]);

    const updateSettingsMutation = useMutation({
        mutationFn: async (payload: { reminder_1_minutes: number; reminder_2_minutes: number; escalation_timeout_minutes: number }) => {
            const { data } = await settingsApi.update(payload);
            return data;
        },
        onSuccess: () => {
            toast.success("Простые настройки сохранены");
            refetch();
        },
        onError: (updateError) => {
            handleError(updateError);
        },
    });

    const explainabilityLines = useMemo(() => {
        const reminder1 = parsePositiveInt(simpleSettings.reminder1);
        const reminder2 = parsePositiveInt(simpleSettings.reminder2);
        const escalation = parsePositiveInt(simpleSettings.escalation);
        if (!reminder1 || !reminder2 || !escalation) {
            return [
                "Введите корректные значения, чтобы увидеть прогноз влияния.",
            ];
        }
        return [
            `Через ${reminder1} мин система напомнит менеджеру о необработанной заявке.`,
            `Через ${reminder2} мин включится повторное напоминание и риск потери лида растет.`,
            `Через ${escalation} мин заявка попадет в авто-контур эскалации/закрытия.`,
        ];
    }, [simpleSettings.escalation, simpleSettings.reminder1, simpleSettings.reminder2]);

    function applyPreset(preset: SettingsPreset): void {
        setSelectedPresetId(preset.id);
        setSimpleSettings({
            reminder1: String(preset.reminder1),
            reminder2: String(preset.reminder2),
            escalation: String(preset.escalation),
        });
    }

    function updateSimpleSetting(field: keyof SimpleSettingsForm, value: string): void {
        setSimpleSettings((current) => ({
            ...current,
            [field]: value,
        }));
    }

    function saveSimpleSettings(): void {
        const reminder1 = parsePositiveInt(simpleSettings.reminder1);
        const reminder2 = parsePositiveInt(simpleSettings.reminder2);
        const escalation = parsePositiveInt(simpleSettings.escalation);

        if (!reminder1 || reminder1 < 5 || reminder1 > 60) {
            toast.error("Первое напоминание должно быть 5-60 мин");
            return;
        }
        if (!reminder2 || reminder2 < 30 || reminder2 > 180) {
            toast.error("Второе напоминание должно быть 30-180 мин");
            return;
        }
        if (!escalation || escalation < 30 || escalation > 360) {
            toast.error("Таймаут эскалации должен быть 30-360 мин");
            return;
        }
        if (reminder1 >= reminder2) {
            toast.error("Первое напоминание должно быть меньше второго");
            return;
        }
        if (reminder2 >= escalation) {
            toast.error("Второе напоминание должно быть меньше таймаута эскалации");
            return;
        }

        updateSettingsMutation.mutate({
            reminder_1_minutes: reminder1,
            reminder_2_minutes: reminder2,
            escalation_timeout_minutes: escalation,
        });
    }

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

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра настроек.
            </div>
        );
    }

    if (meLoading) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Загрузка роли...
            </div>
        );
    }

    if (!canViewSettings) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к настройкам." />
        );
    }

    if (isLoading) {
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

    if (error) {
        return (
            <div className="max-w-5xl mx-auto p-6" data-testid="settings-page">
                <h1 className="text-2xl font-bold mb-6" data-testid="settings-title">Настройки</h1>
                <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center" data-testid="settings-error">
                    <p className="text-destructive mb-4">Не удалось загрузить настройки</p>
                    <button
                        onClick={() => {
                            refetch();
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

    const provisioningAccessSection = canReadSettings ? "settings" : "provisioning";

    return (
        <div className="max-w-5xl mx-auto p-6" data-testid="settings-page">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold" data-testid="settings-title">Настройки</h1>
                <Link href="/" className="text-primary hover:text-primary/80">
                    ← Назад в Inbox
                </Link>
            </div>
            <div className="mb-4 text-xs text-muted-foreground" data-testid="settings-build-info">
                Build: <span className="font-mono" title={buildSha ?? "unknown"}>{buildShaLabel}</span> |{" "}
                <span className="font-mono">{buildTimeLabel}</span>
            </div>

            {canReadProvisioning && (
                <ProvisioningWizard session={session} accessSection={provisioningAccessSection} />
            )}

            {canReadSettings && (
                <section className="mb-6 grid grid-cols-1 gap-6 md:grid-cols-2">
                    <div className="rounded-xl border border-border/60 bg-card p-5" data-testid="settings-simple-card">
                        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-semibold">Простые бизнес-настройки</h2>
                                <p className="text-sm text-muted-foreground">
                                    Меняет скорость реакции менеджеров и таймаут эскалации.
                                </p>
                            </div>
                            {!canWriteSettings && (
                                <span className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
                                    Только owner/admin
                                </span>
                            )}
                        </div>
                        <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-3" data-testid="settings-simple-presets">
                            {SETTINGS_PRESETS.map((preset) => (
                                <button
                                    key={preset.id}
                                    type="button"
                                    className={`rounded-lg border px-3 py-2 text-left text-xs transition ${selectedPresetId === preset.id
                                        ? "border-primary bg-primary/5 text-primary"
                                        : "border-border/60 hover:bg-muted"
                                        }`}
                                    onClick={() => {
                                        applyPreset(preset);
                                    }}
                                    disabled={!canWriteSettings || updateSettingsMutation.isPending}
                                    data-testid={`settings-preset-${preset.id}`}
                                >
                                    <p className="font-semibold">{preset.label}</p>
                                    <p className="mt-1 text-muted-foreground">
                                        {preset.reminder1}/{preset.reminder2}/{preset.escalation} мин
                                    </p>
                                </button>
                            ))}
                        </div>
                        <p className="mb-4 text-xs text-muted-foreground">
                            {SETTINGS_PRESETS.find((item) => item.id === selectedPresetId)?.description}
                        </p>

                        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                            <label className="text-sm">
                                <span className="mb-1 block text-xs text-muted-foreground">1-е напоминание (5-60)</span>
                                <input
                                    type="number"
                                    min={5}
                                    max={60}
                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                    value={simpleSettings.reminder1}
                                    onChange={(event) => {
                                        updateSimpleSetting("reminder1", event.target.value);
                                    }}
                                    disabled={!canWriteSettings || updateSettingsMutation.isPending}
                                    data-testid="settings-input-reminder1"
                                />
                            </label>
                            <label className="text-sm">
                                <span className="mb-1 block text-xs text-muted-foreground">2-е напоминание (30-180)</span>
                                <input
                                    type="number"
                                    min={30}
                                    max={180}
                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                    value={simpleSettings.reminder2}
                                    onChange={(event) => {
                                        updateSimpleSetting("reminder2", event.target.value);
                                    }}
                                    disabled={!canWriteSettings || updateSettingsMutation.isPending}
                                    data-testid="settings-input-reminder2"
                                />
                            </label>
                            <label className="text-sm">
                                <span className="mb-1 block text-xs text-muted-foreground">Эскалация (30-360)</span>
                                <input
                                    type="number"
                                    min={30}
                                    max={360}
                                    className="w-full rounded-lg border border-border/60 bg-background px-3 py-2 text-sm"
                                    value={simpleSettings.escalation}
                                    onChange={(event) => {
                                        updateSimpleSetting("escalation", event.target.value);
                                    }}
                                    disabled={!canWriteSettings || updateSettingsMutation.isPending}
                                    data-testid="settings-input-escalation"
                                />
                            </label>
                        </div>

                        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                            <p className="text-xs text-muted-foreground" data-testid="settings-save-hint">
                                Сохраняется в `client_settings` и сразу влияет на SLA-процессы.
                            </p>
                            <button
                                type="button"
                                onClick={() => {
                                    saveSimpleSettings();
                                }}
                                className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                                disabled={!canWriteSettings || updateSettingsMutation.isPending}
                                data-testid="settings-save-simple"
                            >
                                {updateSettingsMutation.isPending ? "Сохраняю..." : "Сохранить"}
                            </button>
                        </div>
                    </div>

                    <div className="rounded-xl border border-border/60 bg-card p-5" data-testid="settings-explainability">
                        <h2 className="text-lg font-semibold">Объяснение для владельца</h2>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Как текущие значения влияют на продажи, SLA и нагрузку команды.
                        </p>
                        <div className="mt-4 space-y-2">
                            {explainabilityLines.map((line) => (
                                <p key={line} className="rounded-lg border border-border/50 bg-muted/20 px-3 py-2 text-sm text-foreground">
                                    {line}
                                </p>
                            ))}
                        </div>
                        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                            Если видите рост `pending` и просроченных диалогов на странице `Команда KPI`, выбирайте более быстрый профиль.
                        </div>
                    </div>
                </section>
            )}

            {canReadSettings && (
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
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

                    {/* Learning & Data */}
                    <div className="bg-card border border-border/60 rounded-lg p-5" data-testid="settings-learning">
                        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            🧠 Обучение и данные
                        </h2>
                        {config ? (
                            <div>
                                <ConfigCard label="Consent статус" value={config.learning_consent_status} />
                                <ConfigCard label="Анонимизация" value={config.learning_anonymization_mode} />
                                <ConfigCard label="Retention (дней)" value={config.learning_retention_days} />
                                <ConfigCard label="Data sharing" value={config.data_sharing} />
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
                            Проверка и тест отправки в Telegram (client scope, owner/admin/platform admin).
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
                                disabled={verifyTarget === "client" || !canWriteSettings}
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
                                disabled={testTarget === "client" || !canWriteSettings}
                                data-testid="settings-telegram-test"
                            >
                                {testTarget === "client" ? "Отправка..." : "Send test"}
                            </button>
                            {!canWriteSettings && (
                                <span className="text-xs text-muted-foreground">Только owner/admin/platform admin</span>
                            )}
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
                                            disabled={!branch.telegram_chat_id || verifyTarget === branch.id || !canWriteSettings}
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
                                            disabled={!branch.telegram_chat_id || testTarget === branch.id || !canWriteSettings}
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
            )}

            <div className="card-surface p-5 mt-6" data-testid="settings-team-link">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h2 className="text-lg font-semibold mb-1">Команда</h2>
                        <p className="text-sm text-muted-foreground">
                            Пользователи и специалисты перенесены в отдельный раздел.
                        </p>
                    </div>
                    <Link className="btn-ghost" href="/team">
                        Открыть команду
                    </Link>
                </div>
            </div>
        </div>
    );
}
