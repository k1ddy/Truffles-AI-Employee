"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";

import AccessDenied from "@/components/AccessDenied";
import {
    adminApi,
    authApi,
    canAccessConsole,
    confirmationsApi,
    onboardingApi,
    parseApiError,
    type IntegrationBranchActionRequest,
    type ProviderOpsAction,
} from "@/lib/api-client";
import { useErrorHandler } from "@/lib/api-hooks";

const COMPANY_ID_STORAGE_KEY = "console:company_id";
const CLIENT_ID_STORAGE_KEY = "console:client_id";
const BRANCH_ID_STORAGE_KEY = "console:branch_id";
const WORKSPACE_RECOMMENDED_ACTION_KEY = "console:workspace_recommended_action";

type ProviderActionDialogState = {
    action: ProviderOpsAction;
    mode: "dry_run" | "execute";
    reason: string;
    notes: string;
    paidUntil: string;
    nextRenewalAt: string;
    instanceId: string;
};

type WorkspaceRecommendedActionContext = {
    branch_id: string;
    action: ProviderOpsAction;
    reasons: string[];
    source: "queue" | "matrix";
    captured_at: string;
};

type WizardStep = {
    id: string;
    title: string;
    passed: boolean;
    detail: string;
    fix: string;
};

function readLocalStorageValue(key: string): string | null {
    if (typeof window === "undefined") {
        return null;
    }
    return window.localStorage.getItem(key);
}

function setLocalStorageValue(key: string, value?: string | null) {
    if (typeof window === "undefined") {
        return;
    }
    if (!value) {
        window.localStorage.removeItem(key);
        return;
    }
    window.localStorage.setItem(key, value);
}

function readWorkspaceRecommendedActionContext(): WorkspaceRecommendedActionContext | null {
    const raw = readLocalStorageValue(WORKSPACE_RECOMMENDED_ACTION_KEY);
    if (!raw) {
        return null;
    }
    try {
        const parsed = JSON.parse(raw) as WorkspaceRecommendedActionContext;
        if (!parsed?.branch_id || !parsed?.action) {
            return null;
        }
        return parsed;
    } catch {
        return null;
    }
}

function formatDateLabel(value?: string | null): string {
    if (!value) {
        return "-";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return value;
    }
    return parsed.toLocaleString("ru-RU");
}

function statusPill(status: "ok" | "warn" | "error"): string {
    if (status === "error") {
        return "bg-red-100 text-red-700";
    }
    if (status === "warn") {
        return "bg-amber-100 text-amber-700";
    }
    return "bg-green-100 text-green-700";
}

function providerOpsActionLabel(action: ProviderOpsAction): string {
    if (action === "provider_start_rebind") {
        return "Старт перепривязки";
    }
    if (action === "provider_complete_rebind") {
        return "Завершить перепривязку";
    }
    if (action === "provider_renewal_confirmed") {
        return "Подтвердить продление";
    }
    if (action === "provider_webhook_updated") {
        return "Webhook обновлен";
    }
    if (action === "provider_send_reminder") {
        return "Отправить напоминание";
    }
    return "Сверка интеграции";
}

function providerOpsReasonLabel(reason: string): string {
    const labels: Record<string, string> = {
        provider_binding_rebind_required: "нужна перепривязка provider",
        provider_binding_expired: "подписка provider истекла",
        provider_binding_expiring_soon: "подписка provider скоро истекает",
        no_recent_inbound: "давно нет входящих сообщений",
        instance_id_mismatch: "instance_id не совпадает",
        invalid_webhook_url: "webhook URL невалиден",
        integration_degraded: "интеграция деградировала",
        provider_binding_alert_critical: "критичный alert у provider",
        provider_binding_alert_warn: "предупреждение у provider",
    };
    return labels[reason] ?? reason;
}

function defaultExecuteReason(action: ProviderOpsAction): string {
    if (action === "provider_send_reminder") {
        return "provider lifecycle reminder from workspace";
    }
    if (action === "provider_renewal_confirmed") {
        return "provider renewal confirmed in workspace";
    }
    if (action === "provider_webhook_updated") {
        return "provider webhook updated in workspace";
    }
    if (action === "provider_complete_rebind") {
        return "provider rebind completed in workspace";
    }
    if (action === "provider_start_rebind") {
        return "provider rebind started in workspace";
    }
    return "workspace integration reconcile";
}

function wizardStatusLabel(passed: boolean): string {
    return passed ? "ok" : "блокер";
}

function shortId(value?: string | null): string {
    const normalized = (value ?? "").trim();
    if (!normalized) {
        return "-";
    }
    if (normalized.length <= 16) {
        return normalized;
    }
    return `${normalized.slice(0, 8)}...${normalized.slice(-6)}`;
}

function statusCardClass(ok: boolean): string {
    return ok
        ? "border-emerald-300/70 bg-emerald-50 text-emerald-900"
        : "border-red-300/70 bg-red-50 text-red-900";
}

export default function CompanyWorkspacePage() {
    const { data: session } = useSession();
    const { handleError } = useErrorHandler();

    const [scopeCompanyId, setScopeCompanyId] = useState("");
    const [scopeClientId, setScopeClientId] = useState("");
    const [scopeBranchId, setScopeBranchId] = useState("");
    const [scopeInitialized, setScopeInitialized] = useState(false);

    const [staleAfterMinutes] = useState(60);

    const [branchPhone, setBranchPhone] = useState("");
    const [branchInstanceId, setBranchInstanceId] = useState("");
    const [goLiveReason, setGoLiveReason] = useState("go-live подтвержден из центра компании");

    const [webhookSecret, setWebhookSecret] = useState("");
    const [webhookUrl, setWebhookUrl] = useState("");

    const [runningAction, setRunningAction] = useState<{
        branchId: string;
        mode: "dry_run" | "execute";
        action: ProviderOpsAction;
    } | null>(null);
    const [actionSummary, setActionSummary] = useState<string>("");
    const [providerActionDialog, setProviderActionDialog] = useState<ProviderActionDialogState | null>(null);
    const [branchSaving, setBranchSaving] = useState(false);
    const [goLiveSaving, setGoLiveSaving] = useState<"approve" | "reject" | "waive" | null>(null);
    const [recommendedActionContext, setRecommendedActionContext] = useState<WorkspaceRecommendedActionContext | null>(null);

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadTenants = canAccessConsole(role, "tenants", "read");
    const canWriteTenants = canAccessConsole(role, "tenants", "write");
    const canReadIntegrations = canAccessConsole(role, "integrations", "read");

    useEffect(() => {
        if (!meData || scopeInitialized) {
            return;
        }
        const storedCompanyId = readLocalStorageValue(COMPANY_ID_STORAGE_KEY);
        const storedClientId = readLocalStorageValue(CLIENT_ID_STORAGE_KEY);
        const storedBranchId = readLocalStorageValue(BRANCH_ID_STORAGE_KEY);
        setScopeCompanyId(meData.selected_company_id ?? meData.client?.company_id ?? storedCompanyId ?? "");
        setScopeClientId(meData.client?.id ?? storedClientId ?? "");
        setScopeBranchId(meData.selected_branch_id ?? storedBranchId ?? "");
        setScopeInitialized(true);
    }, [meData, scopeInitialized]);

    const syncScopeFromContext = () => {
        const storedCompanyId = readLocalStorageValue(COMPANY_ID_STORAGE_KEY);
        const storedClientId = readLocalStorageValue(CLIENT_ID_STORAGE_KEY);
        const storedBranchId = readLocalStorageValue(BRANCH_ID_STORAGE_KEY);
        setScopeCompanyId(meData?.selected_company_id ?? meData?.client?.company_id ?? storedCompanyId ?? "");
        setScopeClientId(meData?.client?.id ?? storedClientId ?? "");
        setScopeBranchId(meData?.selected_branch_id ?? storedBranchId ?? "");
    };

    const persistScopeAsContext = () => {
        setLocalStorageValue(COMPANY_ID_STORAGE_KEY, scopeCompanyId || null);
        setLocalStorageValue(CLIENT_ID_STORAGE_KEY, scopeClientId || null);
        setLocalStorageValue(BRANCH_ID_STORAGE_KEY, scopeBranchId || null);
        toast.success("Контекст сохранен");
    };

    const copyToClipboard = async (label: string, value?: string | null) => {
        const normalizedValue = (value ?? "").trim();
        if (!normalizedValue) {
            toast.error(`${label}: нечего копировать`);
            return;
        }
        if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) {
            toast.error("Копирование недоступно в этом браузере");
            return;
        }
        try {
            await navigator.clipboard.writeText(normalizedValue);
            toast.success(`${label} скопирован`);
        } catch {
            toast.error(`Не удалось скопировать ${label.toLowerCase()}`);
        }
    };

    const { data: clientsData } = useQuery({
        queryKey: ["company-workspace-clients", scopeCompanyId],
        queryFn: async () => {
            const response = await adminApi.listClients({
                limit: 100,
                lifecycle: "active",
                company_id: scopeCompanyId || undefined,
                include_fleet: "true",
            });
            return response.data;
        },
        enabled: !!session && canReadTenants,
    });
    const clientOptions = useMemo(() => clientsData?.items ?? [], [clientsData?.items]);

    const { data: branchesData } = useQuery({
        queryKey: ["company-workspace-branches", scopeClientId],
        queryFn: async () => {
            const response = await adminApi.listBranches({
                limit: 100,
                lifecycle: "active",
                client_id: scopeClientId || undefined,
            });
            return response.data;
        },
        enabled: !!session && canReadTenants && !!scopeClientId,
    });
    const branchOptions = useMemo(() => branchesData?.items ?? [], [branchesData?.items]);

    const {
        data: integrationsData,
        isLoading: integrationsLoading,
        error: integrationsError,
        refetch: refetchIntegrations,
    } = useQuery({
        queryKey: ["company-workspace-integrations", staleAfterMinutes, scopeCompanyId, scopeClientId, scopeBranchId],
        queryFn: async () => {
            const response = await adminApi.listIntegrations({
                stale_after_minutes: staleAfterMinutes,
                company_id: scopeCompanyId || undefined,
                client_id: scopeClientId || undefined,
                branch_id: scopeBranchId || undefined,
            });
            return response.data;
        },
        enabled: !!session && canReadIntegrations,
        refetchInterval: 60000,
    });

    const {
        data: onboardingScorecard,
        error: scorecardError,
        refetch: refetchScorecard,
    } = useQuery({
        queryKey: ["company-workspace-scorecard", scopeBranchId],
        queryFn: async () => {
            const response = await onboardingApi.scorecard(scopeBranchId);
            return response.data;
        },
        enabled: !!session && !!scopeBranchId && canReadTenants,
    });

    useEffect(() => {
        if (integrationsError) {
            handleError(integrationsError);
        }
    }, [integrationsError, handleError]);

    useEffect(() => {
        if (scorecardError) {
            handleError(scorecardError);
        }
    }, [scorecardError, handleError]);

    useEffect(() => {
        if (!scopeClientId) {
            return;
        }
        if (clientOptions.some((client) => client.id === scopeClientId)) {
            return;
        }
        setScopeClientId("");
        setScopeBranchId("");
    }, [clientOptions, scopeClientId]);

    useEffect(() => {
        if (!scopeBranchId) {
            return;
        }
        if (branchOptions.some((branch) => branch.id === scopeBranchId)) {
            return;
        }
        setScopeBranchId("");
    }, [branchOptions, scopeBranchId]);

    const selectedBranch = useMemo(
        () => branchOptions.find((branch) => branch.id === scopeBranchId) ?? null,
        [branchOptions, scopeBranchId],
    );

    const selectedIntegration = useMemo(() => {
        const items = integrationsData?.items ?? [];
        if (!scopeBranchId) {
            return items[0] ?? null;
        }
        return items.find((item) => item.branch_id === scopeBranchId) ?? null;
    }, [integrationsData?.items, scopeBranchId]);

    useEffect(() => {
        setBranchPhone(selectedBranch?.phone ?? "");
        setBranchInstanceId(selectedBranch?.instance_id ?? "");
    }, [selectedBranch?.id, selectedBranch?.phone, selectedBranch?.instance_id]);

    useEffect(() => {
        setWebhookSecret("");
        setWebhookUrl(selectedIntegration?.webhook_url ?? "");
        setActionSummary("");
    }, [selectedIntegration?.branch_id, selectedIntegration?.webhook_url]);

    useEffect(() => {
        const recommendation = readWorkspaceRecommendedActionContext();
        if (!recommendation) {
            setRecommendedActionContext(null);
            return;
        }
        if (!scopeBranchId) {
            setRecommendedActionContext(recommendation);
            return;
        }
        if (recommendation.branch_id !== scopeBranchId) {
            setRecommendedActionContext(null);
            return;
        }
        setRecommendedActionContext(recommendation);
    }, [scopeBranchId, selectedIntegration?.branch_id]);

    const createBranchConfirmation = async (
        branchId: string,
        reason: string,
        action: "integration_reconcile" | "provider_ops_execute",
    ): Promise<string> => {
        const confirmation = await confirmationsApi.create({
            action,
            target_type: "branch",
            target_id: branchId,
            reason,
        });
        return confirmation.data.confirmation_id;
    };

    const runBranchAction = async (
        branchId: string,
        action: ProviderOpsAction,
        mode: "dry_run" | "execute",
        payload: Partial<IntegrationBranchActionRequest> = {},
        confirmationReason?: string,
    ) => {
        setRunningAction({ branchId, mode, action });
        try {
            const confirmationAction = action === "integration_reconcile" ? "integration_reconcile" : "provider_ops_execute";
            const runAction = async (confirmationId?: string) =>
                adminApi.reconcileIntegrationBranch(branchId, {
                    action,
                    mode,
                    confirmation_id: confirmationId,
                    ...payload,
                });

            let response;
            try {
                response = await runAction();
            } catch (error: unknown) {
                const apiCode = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
                if (mode !== "execute" || apiCode !== "CONFIRMATION_REQUIRED") {
                    throw error;
                }
                const normalizedReason = confirmationReason?.trim();
                if (!normalizedReason) {
                    toast.error("Укажите причину выполнения");
                    return;
                }
                const confirmationId = await createBranchConfirmation(branchId, normalizedReason, confirmationAction);
                response = await runAction(confirmationId);
            }

            const result = response.data.result ?? {};
            setActionSummary(`${providerOpsActionLabel(action)}: ${JSON.stringify(result)}`);
            toast.success(mode === "dry_run" ? "Проверка завершена (без записи)" : "Операция выполнена");
            if (mode === "execute") {
                setLocalStorageValue(WORKSPACE_RECOMMENDED_ACTION_KEY, null);
                setRecommendedActionContext(null);
            }
            await refetchIntegrations();
            await refetchScorecard();
        } catch (error) {
            const parsed = parseApiError(error);
            if (
                parsed.code === "INVALID_PARAM"
                && /limit must be between 1 and 100/i.test(parsed.message)
            ) {
                toast.error("API вернул limit вне диапазона 1..100. Обновите страницу и повторите.");
                return;
            }
            handleError(error);
        } finally {
            setRunningAction(null);
        }
    };

    const openProviderActionDialog = (action: ProviderOpsAction, mode: "dry_run" | "execute" = "execute") => {
        if (!selectedIntegration) {
            toast.error("Сначала выберите филиал");
            return;
        }
        setProviderActionDialog({
            action,
            mode,
            reason: defaultExecuteReason(action),
            notes: `${providerOpsActionLabel(action)} для ${selectedIntegration.branch_slug}`,
            paidUntil: selectedIntegration.provider_binding_paid_until ?? "",
            nextRenewalAt: selectedIntegration.provider_binding_next_renewal_at ?? "",
            instanceId: branchInstanceId || selectedIntegration.instance_id || "",
        });
    };

    const closeProviderActionDialog = () => {
        if (runningAction) {
            return;
        }
        setProviderActionDialog(null);
    };

    const buildDialogPayload = (dialog: ProviderActionDialogState): Partial<IntegrationBranchActionRequest> | null => {
        if (dialog.mode === "execute" && !dialog.reason.trim()) {
            toast.error("Причина обязательна");
            return null;
        }
        if (dialog.action === "provider_renewal_confirmed") {
            const paidUntil = dialog.paidUntil.trim();
            const nextRenewalAt = dialog.nextRenewalAt.trim();
            if (!paidUntil && !nextRenewalAt) {
                toast.error("Укажите paid_until или next_renewal_at");
                return null;
            }
            return {
                paid_until: paidUntil || undefined,
                next_renewal_at: nextRenewalAt || undefined,
                notes: dialog.notes.trim() || undefined,
            };
        }
        if (dialog.action === "provider_webhook_updated" || dialog.action === "provider_complete_rebind") {
            return {
                instance_id: dialog.instanceId.trim() || undefined,
                notes: dialog.notes.trim() || undefined,
            };
        }
        if (dialog.action === "provider_start_rebind" || dialog.action === "provider_send_reminder") {
            return {
                notes: dialog.notes.trim() || undefined,
            };
        }
        if (dialog.action === "integration_reconcile") {
            return {};
        }
        return null;
    };

    const submitProviderActionDialog = async () => {
        if (!providerActionDialog || !selectedIntegration) {
            return;
        }
        const payload = buildDialogPayload(providerActionDialog);
        if (payload === null) {
            return;
        }
        await runBranchAction(
            selectedIntegration.branch_id,
            providerActionDialog.action,
            providerActionDialog.mode,
            payload,
            providerActionDialog.reason,
        );
        setProviderActionDialog(null);
    };

    const saveBranchWhatsappIdentity = async () => {
        if (!scopeBranchId) {
            toast.error("Выберите филиал");
            return;
        }
        const normalizedPhone = branchPhone.trim();
        const normalizedInstanceId = branchInstanceId.trim();
        if (!normalizedPhone || !normalizedInstanceId) {
            toast.error("Телефон и instance_id обязательны");
            return;
        }
        setBranchSaving(true);
        try {
            await adminApi.patchBranch(scopeBranchId, {
                phone: normalizedPhone,
                instance_id: normalizedInstanceId,
                is_active: true,
            });
            toast.success("WhatsApp-идентичность филиала сохранена");
            await refetchIntegrations();
        } catch (error) {
            handleError(error);
        } finally {
            setBranchSaving(false);
        }
    };

    const refreshWebhookSecret = async () => {
        if (!scopeBranchId) {
            toast.error("Выберите филиал");
            return;
        }
        try {
            const response = await adminApi.getWebhookSecret({
                branch_id: scopeBranchId,
                clientId: scopeClientId || undefined,
            });
            setWebhookSecret(response.data.webhook_secret ?? "");
            setWebhookUrl(response.data.webhook_url ?? "");
            toast.success("Webhook-контракт обновлен");
        } catch (error) {
            handleError(error);
        }
    };

    const approveGoLive = async () => {
        if (!scopeBranchId) {
            toast.error("Выберите филиал");
            return;
        }
        const reason = goLiveReason.trim();
        if (!reason) {
            toast.error("Причина для go-live обязательна");
            return;
        }
        setGoLiveSaving("approve");
        try {
            await adminApi.approveBranchGoLive(scopeBranchId, { reason });
            toast.success("Go-live подтвержден");
            await refetchIntegrations();
            await refetchScorecard();
        } catch (error) {
            handleError(error);
        } finally {
            setGoLiveSaving(null);
        }
    };

    const rejectGoLive = async () => {
        if (!scopeBranchId) {
            toast.error("Выберите филиал");
            return;
        }
        const reason = goLiveReason.trim();
        if (!reason) {
            toast.error("Причина отклонения обязательна");
            return;
        }
        setGoLiveSaving("reject");
        try {
            await adminApi.rejectBranchGoLive(scopeBranchId, { reason });
            toast.success("Go-live отклонен");
            await refetchIntegrations();
            await refetchScorecard();
        } catch (error) {
            handleError(error);
        } finally {
            setGoLiveSaving(null);
        }
    };

    const waiveGoLive = async () => {
        if (!scopeBranchId) {
            toast.error("Выберите филиал");
            return;
        }
        const reason = goLiveReason.trim();
        if (!reason) {
            toast.error("Причина waiver обязательна");
            return;
        }
        setGoLiveSaving("waive");
        try {
            await adminApi.waiveBranchGoLive(scopeBranchId, { reason, ttl_hours: 24 });
            toast.success("Отсрочка go-live применена на 24 часа");
            await refetchIntegrations();
            await refetchScorecard();
        } catch (error) {
            handleError(error);
        } finally {
            setGoLiveSaving(null);
        }
    };

    const selectedCompanyName = useMemo(() => {
        return (
            (meData?.companies ?? []).find((company) => company.id === scopeCompanyId)?.name
            ?? shortId(scopeCompanyId)
        );
    }, [meData?.companies, scopeCompanyId]);

    const selectedClientName = useMemo(() => {
        return (
            clientOptions.find((client) => client.id === scopeClientId)?.name
            ?? shortId(scopeClientId)
        );
    }, [clientOptions, scopeClientId]);

    const selectedBranchName = useMemo(() => {
        return (
            branchOptions.find((branch) => branch.id === scopeBranchId)?.name
            ?? shortId(scopeBranchId)
        );
    }, [branchOptions, scopeBranchId]);

    const hasContext = Boolean(scopeCompanyId && scopeClientId && scopeBranchId);
    const hasIdentity = Boolean((selectedBranch?.phone ?? "").trim() && (selectedBranch?.instance_id ?? "").trim());
    const webhookConfigured = Boolean(
        selectedIntegration?.webhook_url_valid
        && selectedIntegration?.provider_binding_webhook_status === "configured",
    );
    const renewalTracked = Boolean(
        selectedIntegration
        && (
            (selectedIntegration.provider_binding_paid_until ?? "").trim()
            || (selectedIntegration.provider_binding_next_renewal_at ?? "").trim()
        )
        && (selectedIntegration.provider_binding_owner ?? "").trim(),
    );
    const scorecardReady = Boolean(onboardingScorecard?.ready);

    const wizardSteps = useMemo<WizardStep[]>(() => {
        return [
            {
                id: "context",
                title: "Шаг 1: Выберите компанию/клиента/филиал",
                passed: hasContext,
                detail: hasContext ? "Контекст выбран" : "Компания, клиент и филиал обязательны",
                fix: "Заполните Scope и нажмите «Применить контекст»",
            },
            {
                id: "identity",
                title: "Шаг 2: Запишите WhatsApp-идентичность",
                passed: hasIdentity,
                detail: hasIdentity ? "Телефон и instance_id заполнены" : "Телефон филиала и instance_id обязательны",
                fix: "Сохраните WA-идентичность филиала (телефон + instance_id)",
            },
            {
                id: "webhook",
                title: "Шаг 3: Проверьте webhook и связь с provider",
                passed: webhookConfigured,
                detail: webhookConfigured ? "Webhook настроен" : "Webhook должен быть валидным и webhook_status=configured",
                fix: "Обновите webhook и отметьте «Webhook обновлен» или «Завершить перепривязку»",
            },
            {
                id: "renewal",
                title: "Шаг 4: Зафиксируйте продление и владельца",
                passed: renewalTracked,
                detail: renewalTracked ? "Данные продления заполнены" : "Нужны владелец и paid_until/next_renewal_at",
                fix: "Выполните действие «Подтвердить продление»",
            },
            {
                id: "go-live",
                title: "Шаг 5: Готовность и допуск go-live",
                passed: scorecardReady,
                detail: scorecardReady ? "Проверка готовности пройдена" : "Проверка готовности не пройдена",
                fix: "Закройте незаполненные проверки до подтверждения go-live",
            },
        ];
    }, [hasContext, hasIdentity, renewalTracked, scorecardReady, webhookConfigured]);

    const firstFailedStepIndex = wizardSteps.findIndex((step) => !step.passed);
    const hardStopActive = firstFailedStepIndex !== -1;
    const currentBlocker = hardStopActive ? wizardSteps[firstFailedStepIndex] : null;

    const recommendedPlaybook = useMemo(() => {
        const reasons = recommendedActionContext?.reasons ?? [];
        const steps: string[] = [];
        for (const reason of reasons) {
            if (reason === "provider_binding_rebind_required" || reason === "instance_id_mismatch") {
                steps.push("Проверьте instance_id и нажмите «Старт перепривязки», затем «Завершить перепривязку».");
                continue;
            }
            if (reason === "provider_binding_expired" || reason === "provider_binding_expiring_soon") {
                steps.push("Уточните оплату у provider и выполните «Подтвердить продление» с актуальной датой.");
                continue;
            }
            if (reason === "invalid_webhook_url") {
                steps.push("Получите новый webhook-контракт и подтвердите действие «Webhook обновлен».");
                continue;
            }
            if (reason === "no_recent_inbound" || reason === "integration_degraded") {
                steps.push("Запустите «Проверить без записи», затем «Применить сверку» при подтверждении проблемы.");
                continue;
            }
            if (reason === "provider_binding_alert_critical" || reason === "provider_binding_alert_warn") {
                steps.push("Проверьте карточку provider и отправьте напоминание/перепривяжите по регламенту.");
                continue;
            }
        }
        return [...new Set(steps)];
    }, [recommendedActionContext?.reasons]);

    if (!session) {
        return <div className="p-8 text-center text-muted-foreground">Войдите в систему, чтобы открыть центр компании.</div>;
    }

    if (meLoading) {
        return <div className="p-8 text-center text-muted-foreground">Загрузка роли и контекста...</div>;
    }

    if (!canReadTenants && !canReadIntegrations) {
        return <AccessDenied message="Нет доступа к центру компании." />;
    }

    return (
        <div className="mx-auto max-w-[1320px] p-4 sm:p-6" data-testid="company-workspace-page">
            <div className="rounded-lg border border-border/60 bg-card p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h1 className="text-2xl font-bold">Центр управления компанией</h1>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Один экран для подключения, перепривязки, продления и допуска go-live по филиалу.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <Link href="/tenants" className="btn-ghost">Тенанты</Link>
                        <Link href="/integrations" className="btn-ghost">Интеграции</Link>
                        <Link href="/ops" className="btn-ghost">Операции</Link>
                    </div>
                </div>
            </div>

            <section className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5" data-testid="company-workspace-status-cards">
                <div className={`rounded-lg border p-3 text-xs ${statusCardClass(hasContext)}`}>
                    <div className="font-semibold uppercase tracking-[0.15em]">Контекст</div>
                    <div className="mt-1 text-sm">{hasContext ? "Выбран" : "Не выбран"}</div>
                </div>
                <div className={`rounded-lg border p-3 text-xs ${statusCardClass(hasIdentity)}`}>
                    <div className="font-semibold uppercase tracking-[0.15em]">WA-идентичность</div>
                    <div className="mt-1 text-sm">{hasIdentity ? "Заполнена" : "Нет телефона/instance_id"}</div>
                </div>
                <div className={`rounded-lg border p-3 text-xs ${statusCardClass(webhookConfigured)}`}>
                    <div className="font-semibold uppercase tracking-[0.15em]">Webhook</div>
                    <div className="mt-1 text-sm">{webhookConfigured ? "Настроен" : "Требует проверки"}</div>
                </div>
                <div className={`rounded-lg border p-3 text-xs ${statusCardClass(renewalTracked)}`}>
                    <div className="font-semibold uppercase tracking-[0.15em]">Продление</div>
                    <div className="mt-1 text-sm">{renewalTracked ? "Зафиксировано" : "Нужен владелец + даты"}</div>
                </div>
                <div className={`rounded-lg border p-3 text-xs ${statusCardClass(scorecardReady)}`}>
                    <div className="font-semibold uppercase tracking-[0.15em]">Go-live</div>
                    <div className="mt-1 text-sm">{scorecardReady ? "Допуск возможен" : "Есть блокеры"}</div>
                </div>
            </section>

            <section className="mt-4 rounded-lg border border-border/60 bg-card p-4" data-testid="company-workspace-recommended-action">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h2 className="text-lg font-semibold">Следующее рекомендуемое действие</h2>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Авто-подсказка из Integrations Queue/Matrix. Ничего не выполняется автоматически.
                        </p>
                    </div>
                    <span className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
                        source: {recommendedActionContext?.source ?? "-"}
                    </span>
                </div>

                {recommendedActionContext && (!scopeBranchId || recommendedActionContext.branch_id === scopeBranchId) ? (
                    <div className="mt-3 space-y-3">
                        <div className="rounded-lg border border-amber-300/60 bg-amber-50 p-3 text-sm text-amber-900">
                            <span className="font-semibold">Рекомендуется:</span>{" "}
                            {providerOpsActionLabel(recommendedActionContext.action)}
                        </div>

                        <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs">
                            <div className="font-semibold uppercase tracking-[0.12em] text-muted-foreground">Причины</div>
                            <div className="mt-2 flex flex-wrap gap-1">
                                {(recommendedActionContext.reasons ?? []).length ? (
                                    recommendedActionContext.reasons.map((reason) => (
                                        <span key={reason} className="rounded bg-red-100 px-2 py-0.5 text-[11px] font-medium text-red-800">
                                            {providerOpsReasonLabel(reason)}
                                        </span>
                                    ))
                                ) : (
                                    <span className="text-muted-foreground">нет</span>
                                )}
                            </div>
                        </div>

                        {recommendedPlaybook.length ? (
                            <div className="rounded-lg border border-border/60 bg-background p-3 text-xs">
                                <div className="font-semibold uppercase tracking-[0.12em] text-muted-foreground">Playbook</div>
                                <ol className="mt-2 list-decimal space-y-1 pl-4 text-muted-foreground">
                                    {recommendedPlaybook.map((step) => (
                                        <li key={step}>{step}</li>
                                    ))}
                                </ol>
                            </div>
                        ) : null}

                        <div className="flex flex-wrap gap-2">
                            <button
                                className="btn-primary"
                                onClick={() => openProviderActionDialog(recommendedActionContext.action, "execute")}
                                disabled={!scopeBranchId || !selectedIntegration || !!runningAction}
                                data-testid="workspace-recommended-open-execute"
                            >
                                Открыть форму действия
                            </button>
                            <button
                                className="btn-ghost"
                                onClick={() => openProviderActionDialog("integration_reconcile", "dry_run")}
                                disabled={!scopeBranchId || !selectedIntegration || !!runningAction}
                                data-testid="workspace-recommended-open-dryrun"
                            >
                                Сначала проверить без записи
                            </button>
                            <button
                                className="btn-ghost"
                                onClick={() => {
                                    setLocalStorageValue(WORKSPACE_RECOMMENDED_ACTION_KEY, null);
                                    setRecommendedActionContext(null);
                                }}
                                disabled={!!runningAction}
                                data-testid="workspace-recommended-clear"
                            >
                                Скрыть подсказку
                            </button>
                        </div>
                    </div>
                ) : (
                    <div className="mt-3 rounded-lg border border-emerald-300/60 bg-emerald-50 p-3 text-xs text-emerald-800">
                        Для текущего контекста нет активной подсказки. Используйте Integrations Queue/Matrix для выбора филиала с проблемой.
                    </div>
                )}
            </section>

            <section className="mt-4 rounded-lg border border-border/60 bg-card p-4" data-testid="company-workspace-scope">
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Контекст</div>
                <div className="mt-1 text-xs text-muted-foreground">Шаг 1. Выберите компанию, клиента и филиал, затем нажмите «Применить контекст».</div>
                <div className="mt-3 grid gap-3 md:grid-cols-4">
                    <label className="text-xs text-muted-foreground">
                        компания
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={scopeCompanyId}
                            onChange={(event) => {
                                setScopeCompanyId(event.target.value);
                                setScopeClientId("");
                                setScopeBranchId("");
                            }}
                            data-testid="workspace-scope-company"
                        >
                            <option value="">выберите</option>
                            {(meData?.companies ?? []).map((company) => (
                                <option key={company.id} value={company.id ?? ""}>
                                    {company.name ?? company.id}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="text-xs text-muted-foreground">
                        клиент
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={scopeClientId}
                            onChange={(event) => {
                                setScopeClientId(event.target.value);
                                setScopeBranchId("");
                            }}
                            data-testid="workspace-scope-client"
                        >
                            <option value="">выберите</option>
                            {clientOptions.map((client) => (
                                <option key={client.id} value={client.id ?? ""}>
                                    {client.name ?? client.slug ?? client.id}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="text-xs text-muted-foreground">
                        филиал
                        <select
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            value={scopeBranchId}
                            onChange={(event) => setScopeBranchId(event.target.value)}
                            disabled={!scopeClientId}
                            data-testid="workspace-scope-branch"
                        >
                            <option value="">выберите</option>
                            {branchOptions.map((branch) => (
                                <option key={branch.id} value={branch.id ?? ""}>
                                    {branch.name ?? branch.slug ?? branch.id}
                                </option>
                            ))}
                        </select>
                    </label>
                    <div className="flex flex-wrap items-end gap-2">
                        <button className="btn-ghost" onClick={syncScopeFromContext}>Из контекста</button>
                        <button className="btn-primary" onClick={persistScopeAsContext}>Применить контекст</button>
                    </div>
                </div>
                <div className="mt-2 rounded-md border border-border/60 bg-muted/20 p-2 text-xs text-muted-foreground">
                    активный контекст:{" "}
                    компания <span className="font-semibold text-foreground">{selectedCompanyName}</span>
                    {" "}(<span className="font-mono">{shortId(scopeCompanyId)}</span>)
                    {" "}· клиент <span className="font-semibold text-foreground">{selectedClientName}</span>
                    {" "}(<span className="font-mono">{shortId(scopeClientId)}</span>)
                    {" "}· филиал <span className="font-semibold text-foreground">{selectedBranchName}</span>
                    {" "}(<span className="font-mono">{shortId(scopeBranchId)}</span>)
                </div>
            </section>

            <section className="mt-4 rounded-lg border border-border/60 bg-card p-4" data-testid="company-workspace-whatsapp-panel">
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h2 className="text-lg font-semibold">Панель WhatsApp / ChatFlow</h2>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Шаги 2-4: идентичность канала, webhook-контракт, перепривязка и продление.
                        </p>
                    </div>
                    <button
                        className="btn-ghost"
                        onClick={() => refetchIntegrations()}
                        disabled={integrationsLoading}
                    >
                        {integrationsLoading ? "Обновляю..." : "Обновить"}
                    </button>
                </div>

                <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <label className="text-xs text-muted-foreground">
                        телефон филиала
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono"
                            value={branchPhone}
                            onChange={(event) => setBranchPhone(event.target.value)}
                            placeholder="+77000000000"
                        />
                    </label>
                    <label className="text-xs text-muted-foreground">
                        instance_id ChatFlow
                        <input
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm font-mono"
                            value={branchInstanceId}
                            onChange={(event) => setBranchInstanceId(event.target.value)}
                            placeholder="instance-xxxxxxxx"
                        />
                    </label>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button
                        className="btn-primary"
                        onClick={() => void saveBranchWhatsappIdentity()}
                        disabled={!scopeBranchId || branchSaving}
                    >
                        {branchSaving ? "Сохраняю..." : "Сохранить WA-идентичность"}
                    </button>
                    <button className="btn-ghost" onClick={() => void refreshWebhookSecret()} disabled={!scopeBranchId}>
                        Получить webhook-контракт
                    </button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("integration_reconcile", "dry_run")} disabled={!scopeBranchId || !!runningAction}>
                        Проверить без записи
                    </button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("integration_reconcile", "execute")} disabled={!scopeBranchId || !!runningAction}>
                        Применить сверку
                    </button>
                </div>

                <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs">
                        <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold">instance_id филиала</span>
                            <button className="btn-ghost px-2 py-1 text-[11px]" onClick={() => void copyToClipboard("instance_id", branchInstanceId || selectedIntegration?.instance_id)}>Копировать</button>
                        </div>
                        <div className="mt-1 overflow-x-auto rounded bg-background/60 px-2 py-1">
                            <span className="font-mono text-[11px] whitespace-nowrap">{branchInstanceId || selectedIntegration?.instance_id || "-"}</span>
                        </div>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs">
                        <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold">Webhook URL</span>
                            <button className="btn-ghost px-2 py-1 text-[11px]" onClick={() => void copyToClipboard("Webhook URL", webhookUrl || selectedIntegration?.webhook_url)}>Копировать</button>
                        </div>
                        <div className="mt-1 overflow-x-auto rounded bg-background/60 px-2 py-1">
                            <span className="font-mono text-[11px] whitespace-nowrap">{webhookUrl || selectedIntegration?.webhook_url || "-"}</span>
                        </div>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs">
                        <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold">Webhook secret</span>
                            <button className="btn-ghost px-2 py-1 text-[11px]" onClick={() => void copyToClipboard("Webhook secret", webhookSecret)}>Копировать</button>
                        </div>
                        <div className="mt-1 overflow-x-auto rounded bg-background/60 px-2 py-1">
                            <span className="font-mono text-[11px] whitespace-nowrap">{webhookSecret || "-"}</span>
                        </div>
                    </div>
                    <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs">
                        <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold">Владелец provider</span>
                            <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusPill(selectedIntegration?.status ?? "ok")}`}>
                                {selectedIntegration?.status ?? "-"}
                            </span>
                        </div>
                        <div className="mt-1 font-mono text-[11px] break-all">{selectedIntegration?.provider_binding_owner || "-"}</div>
                        <div className="mt-1 text-[11px] text-muted-foreground">
                            paid_until: <span className="font-mono break-all">{selectedIntegration?.provider_binding_paid_until || "-"}</span>
                            {" "}· next_renewal_at: <span className="font-mono break-all">{selectedIntegration?.provider_binding_next_renewal_at || "-"}</span>
                        </div>
                        <div className="mt-1 text-[11px] text-muted-foreground">
                            webhook_status: <span className="font-mono">{selectedIntegration?.provider_binding_webhook_status || "-"}</span>
                            {" "}· last inbound: <span className="font-mono">{formatDateLabel(selectedIntegration?.last_inbound_at)}</span>
                        </div>
                    </div>
                </div>

                <div className="mt-2 rounded-lg border border-border/60 bg-muted/10 p-2 text-xs text-muted-foreground">
                    последнее действие: <span className="font-mono break-all">{actionSummary || "-"}</span>
                </div>

                <div className="mt-3 flex flex-wrap gap-2" data-testid="company-workspace-provider-actions">
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_start_rebind")} disabled={!scopeBranchId || !!runningAction}>Старт перепривязки</button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_complete_rebind")} disabled={!scopeBranchId || !!runningAction}>Завершить перепривязку</button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_webhook_updated")} disabled={!scopeBranchId || !!runningAction}>Webhook обновлен</button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_renewal_confirmed")} disabled={!scopeBranchId || !!runningAction}>Подтвердить продление</button>
                    <button className="btn-ghost" onClick={() => openProviderActionDialog("provider_send_reminder")} disabled={!scopeBranchId || !!runningAction}>Отправить напоминание</button>
                </div>
            </section>

            <section className="mt-4 rounded-lg border border-border/60 bg-card p-4" data-testid="company-workspace-hardstop-wizard">
                <h2 className="text-lg font-semibold">Линейный hard-stop онбординга</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                    Поток: контекст -&gt; WA-идентичность -&gt; webhook -&gt; продление -&gt; go-live.
                </p>

                {currentBlocker ? (
                    <div className="mt-3 rounded-lg border border-red-300/70 bg-red-50 p-3 text-xs text-red-800">
                        <div className="font-semibold">Текущий блокер: {currentBlocker.title}</div>
                        <div className="mt-1">Что исправить: {currentBlocker.fix}</div>
                    </div>
                ) : (
                    <div className="mt-3 rounded-lg border border-emerald-300/70 bg-emerald-50 p-3 text-xs text-emerald-800">
                        Все обязательные шаги пройдены, можно принимать go-live.
                    </div>
                )}

                <div className="mt-3 space-y-2">
                    {wizardSteps.map((step, index) => {
                        const isCurrentBlocker = !step.passed && firstFailedStepIndex === index;
                        return (
                            <div key={step.id} className="rounded-lg border border-border/60 bg-background p-3">
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                    <div className="text-sm font-medium">{step.title}</div>
                                    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${step.passed ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                                        {wizardStatusLabel(step.passed)}
                                    </span>
                                </div>
                                <div className="mt-1 text-xs text-muted-foreground">{step.detail}</div>
                                {!step.passed ? (
                                    <div className={`mt-1 text-xs ${isCurrentBlocker ? "text-red-700" : "text-muted-foreground"}`}>
                                        fix: {step.fix}{isCurrentBlocker ? " (текущий блокер)" : ""}
                                    </div>
                                ) : null}
                            </div>
                        );
                    })}
                </div>

                <div className="mt-4 rounded-lg border border-border/60 bg-background p-3">
                    <div className="text-sm font-medium">Решение по go-live</div>
                    <label className="mt-2 block text-xs text-muted-foreground">
                        причина
                        <textarea
                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                            rows={2}
                            value={goLiveReason}
                            onChange={(event) => setGoLiveReason(event.target.value)}
                            placeholder="укажите причину решения"
                        />
                    </label>
                    <div className="mt-3 flex flex-wrap gap-2">
                        <button
                            className="btn-primary"
                            onClick={() => void approveGoLive()}
                            disabled={!scopeBranchId || !canWriteTenants || hardStopActive || goLiveSaving !== null}
                        >
                            {goLiveSaving === "approve" ? "Подтверждаю..." : "Подтвердить go-live"}
                        </button>
                        <button
                            className="btn-ghost"
                            onClick={() => void rejectGoLive()}
                            disabled={!scopeBranchId || !canWriteTenants || goLiveSaving !== null}
                        >
                            {goLiveSaving === "reject" ? "Отклоняю..." : "Отклонить"}
                        </button>
                        <button
                            className="btn-ghost"
                            onClick={() => void waiveGoLive()}
                            disabled={!scopeBranchId || !canWriteTenants || hardStopActive || goLiveSaving !== null}
                        >
                            {goLiveSaving === "waive" ? "Применяю..." : "Отложить 24ч"}
                        </button>
                    </div>
                    <div className="mt-2 text-xs text-muted-foreground">
                        hard-stop: {hardStopActive ? "активен" : "снят"} · готовность: {onboardingScorecard?.status ?? "-"}
                    </div>
                </div>
            </section>

            {providerActionDialog && selectedIntegration ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" data-testid="workspace-action-modal-overlay">
                    <div className="w-full max-w-xl rounded-xl border border-border/60 bg-card p-5 shadow-xl" role="dialog" aria-modal="true" data-testid="workspace-action-modal">
                        <div className="flex items-start justify-between gap-3">
                            <div>
                                <h2 className="text-lg font-semibold">{providerOpsActionLabel(providerActionDialog.action)}</h2>
                                <p className="text-xs text-muted-foreground mt-1">
                                    {selectedIntegration.client_slug} / {selectedIntegration.branch_name} · режим: {providerActionDialog.mode === "execute" ? "выполнить" : "проверить"}
                                </p>
                            </div>
                            <button type="button" className="btn-ghost" onClick={closeProviderActionDialog} disabled={!!runningAction}>Закрыть</button>
                        </div>

                        <div className="mt-4 space-y-3">
                            {providerActionDialog.mode === "execute" ? (
                                <label className="text-xs text-muted-foreground">
                                    причина (обязательно)
                                    <textarea
                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        rows={2}
                                        value={providerActionDialog.reason}
                                        onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, reason: event.target.value } : prev))}
                                        placeholder="почему выполняем операцию"
                                    />
                                </label>
                            ) : null}

                            <label className="text-xs text-muted-foreground">
                                заметки
                                <textarea
                                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                    rows={2}
                                    value={providerActionDialog.notes}
                                    onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, notes: event.target.value } : prev))}
                                    placeholder="комментарий для операции"
                                />
                            </label>

                            {providerActionDialog.action === "provider_complete_rebind" || providerActionDialog.action === "provider_webhook_updated" ? (
                                <label className="text-xs text-muted-foreground">
                                    instance_id
                                    <input
                                        className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                        value={providerActionDialog.instanceId}
                                        onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, instanceId: event.target.value } : prev))}
                                        placeholder="instance-xxxxxxxx"
                                    />
                                </label>
                            ) : null}

                            {providerActionDialog.action === "provider_renewal_confirmed" ? (
                                <div className="grid gap-3 sm:grid-cols-2">
                                    <label className="text-xs text-muted-foreground">
                                        paid_until
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={providerActionDialog.paidUntil}
                                            onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, paidUntil: event.target.value } : prev))}
                                            placeholder="2026-12-31"
                                        />
                                    </label>
                                    <label className="text-xs text-muted-foreground">
                                        next_renewal_at
                                        <input
                                            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                                            value={providerActionDialog.nextRenewalAt}
                                            onChange={(event) => setProviderActionDialog((prev) => (prev ? { ...prev, nextRenewalAt: event.target.value } : prev))}
                                            placeholder="2026-12-31"
                                        />
                                    </label>
                                </div>
                            ) : null}
                        </div>

                        <div className="mt-4 flex items-center justify-end gap-2">
                            <button type="button" className="btn-ghost" onClick={closeProviderActionDialog} disabled={!!runningAction}>Отмена</button>
                            <button type="button" className="btn-primary" onClick={() => void submitProviderActionDialog()} disabled={!!runningAction}>
                                {runningAction ? "Выполняю..." : providerActionDialog.mode === "execute" ? "Выполнить" : "Проверить"}
                            </button>
                        </div>
                    </div>
                </div>
            ) : null}
        </div>
    );
}
