"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import toast from "react-hot-toast";

import AccessDenied from "@/components/AccessDenied";
import ConsoleOwnerScopeGate from "@/components/ConsoleOwnerScopeGate";
import { ConsolePageError, ConsolePageSkeleton } from "@/components/PageStates";
import { authApi, businessApi, canAccessConsole } from "@/lib/api-client";
import { applyConsoleScopeContext } from "@/lib/console-scope-gate";
import ConsultantVerificationWorkspace from "./_components/ConsultantVerificationWorkspace";
import { QUERY_PROFILE_CONTEXT, QUERY_PROFILE_DASHBOARD, keepPreviousData } from "@/lib/query-profiles";

function statusChipClass(status?: string | null): string {
    if (status === "ready") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (status === "needs_attention") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-slate-100 text-slate-700";
}

function cardStateClass(state?: string | null): string {
    if (state === "ready") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (state === "needs_attention") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-slate-100 text-slate-700";
}

function actionChipClass(severity: "critical" | "warn" | "info"): string {
    if (severity === "critical") {
        return "bg-red-100 text-red-800";
    }
    if (severity === "warn") {
        return "bg-amber-100 text-amber-800";
    }
    return "bg-slate-100 text-slate-700";
}

function syncChipClass(status?: string | null): string {
    if (status === "ready") {
        return "bg-emerald-100 text-emerald-800";
    }
    if (status === "failed") {
        return "bg-red-100 text-red-800";
    }
    return "bg-slate-100 text-slate-700";
}

function formatHours(value?: number | null): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return "—";
    }
    if (value < 24) {
        return `${Math.round(value)} ч`;
    }
    return `${(value / 24).toFixed(1)} д`;
}

const EXPECTATION_POINTS = [
    "Владелец бизнеса здесь пишет как клиент, а не как QA-инженер.",
    "Сильная проверка — это неудобные и смешанные вопросы, а не только простые happy-path сценарии.",
    "Доверие строится на честной границе: где консультант отвечает сам, а где должен передать человека.",
] as const;

export default function BusinessConsultantVerificationPage() {
    const { data: session } = useSession();
    const queryClient = useQueryClient();
    const [branchDraftId, setBranchDraftId] = useState("");

    const { data: meData, isLoading: meLoading } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
        ...QUERY_PROFILE_CONTEXT,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadBusiness = canAccessConsole(role, "business", "read");
    const selectedClientId = meData?.client?.id ?? "";
    const selectedCompanyId = meData?.selected_company_id ?? meData?.client?.company_id ?? "";
    const branchOptions = useMemo(() => meData?.branches ?? [], [meData?.branches]);

    const { data, isLoading, error, refetch, isFetching } = useQuery({
        queryKey: ["business-consultant-verification-overview"],
        queryFn: async () => {
            const response = await businessApi.getConsultantVerificationOverview();
            return response.data;
        },
        enabled: !!session && canReadBusiness,
        refetchInterval: 45000,
        placeholderData: keepPreviousData,
        ...QUERY_PROFILE_DASHBOARD,
    });

    useEffect(() => {
        if (!branchDraftId) {
            if (data?.selected_branch_id) {
                setBranchDraftId(data.selected_branch_id);
                return;
            }
            if (branchOptions.length === 1) {
                setBranchDraftId(branchOptions[0]?.id ?? "");
            }
        }
    }, [branchDraftId, branchOptions, data?.selected_branch_id]);

    const selectedBranchContext = useMemo(() => {
        const targetId = data?.selected_branch_id ?? meData?.selected_branch_id ?? "";
        return branchOptions.find((branch) => branch.id === targetId) ?? null;
    }, [branchOptions, data?.selected_branch_id, meData?.selected_branch_id]);
    const branchSelectionRequired = Boolean(meData) && Boolean(data?.branch_selection_required);
    const canApplyBranchContext = Boolean(branchDraftId && selectedClientId);
    const previewStatus = data?.preview_status ?? data?.status ?? "needs_attention";
    const previewStatusLabel = data?.preview_status_label ?? data?.status_label ?? "Нужно внимание";
    const previewSummary = data?.preview_summary ?? data?.summary ?? "";
    const liveActivationStatus = data?.live_activation_status ?? data?.knowledge_sync_status ?? "not_started";
    const liveActivationLabel = data?.live_activation_status_label ?? data?.knowledge_sync_status_label ?? "Обновление не запускалось";
    const liveActivationSummary = data?.live_activation_summary ?? null;
    const previewTruthSource = data?.preview_truth_source ?? null;
    const blockers = data?.blockers ?? [];
    const workspaceReady = Boolean(data?.feature_enabled) && !branchSelectionRequired && Boolean(data?.can_verify_now ?? (previewStatus === "ready"));
    const readinessCards = data?.readiness_cards ?? [];
    const stressTestExamples = data?.stress_test_examples ?? [];
    const actions = data?.actions ?? [];

    async function applyBranchContext() {
        if (!canApplyBranchContext) {
            toast.error("Сначала выберите филиал.");
            return;
        }
        await applyConsoleScopeContext({
            queryClient,
            companyId: selectedCompanyId || null,
            clientId: selectedClientId || null,
            branchId: branchDraftId,
            invalidateKeys: [
                ["business-consultant-verification-overview"],
                ["business-consultant-verification-sessions"],
                ["business-consultant-verification-findings"],
                ["business-consultant-verification-readiness"],
            ],
        });
        toast.success("Контекст филиала применен.");
    }

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Пожалуйста, войдите для просмотра проверки консультанта.
            </div>
        );
    }

    if (meLoading) {
        return <div className="p-8 text-center text-muted-foreground">Загрузка роли...</div>;
    }

    if (!canReadBusiness) {
        return <AccessDenied message="Эта роль не имеет доступа к разделу проверки консультанта." />;
    }

    if (isLoading) {
        return (
            <ConsolePageSkeleton
                pageTestId="consultant-verification-page"
                title="Проверка консультанта"
                titleTestId="consultant-verification-title"
                columns={3}
                cardCount={4}
            />
        );
    }

    if (error || !data) {
        return (
            <ConsolePageError
                pageTestId="consultant-verification-page"
                title="Проверка консультанта"
                titleTestId="consultant-verification-title"
                errorTestId="consultant-verification-error"
                retryTestId="consultant-verification-retry"
                errorMessage="Не удалось загрузить обзор проверки консультанта"
                onRetry={() => {
                    refetch();
                }}
            />
        );
    }

    return (
        <div className="mx-auto max-w-6xl p-6" data-testid="consultant-verification-page">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold" data-testid="consultant-verification-title">
                        Проверка консультанта
                    </h1>
                    <p className="mt-1 text-sm text-muted-foreground" data-testid="consultant-verification-generated-at">
                        Обновлено: {new Date(data.generated_at).toLocaleString("ru-RU")}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => {
                            refetch();
                        }}
                        className="btn-ghost"
                        disabled={isFetching}
                        data-testid="consultant-verification-refresh"
                    >
                        {isFetching ? "Обновляю..." : "Обновить"}
                    </button>
                    <Link href="/business" className="btn-ghost">
                        Назад в Бизнес
                    </Link>
                </div>
            </div>

            <section
                className="rounded-xl border border-border/60 bg-card p-4"
                data-testid="consultant-verification-scope-card"
            >
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <p className="text-sm text-muted-foreground">Текущий контекст проверки</p>
                        <p className="mt-1 text-base font-semibold text-foreground">
                            {meData?.client?.name ?? "Клиент не выбран"} · {data.selected_branch_name ?? selectedBranchContext?.name ?? "Филиал не выбран"}
                        </p>
                        <p className="mt-2 text-sm text-muted-foreground">
                            Preview использует только знания выбранного филиала и pinned snapshot выбранного источника.
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs">
                        <span className={`rounded-full px-3 py-1 font-semibold ${statusChipClass(previewStatus)}`}>
                            {previewStatusLabel}
                        </span>
                        <span className={`rounded-full px-3 py-1 font-semibold ${syncChipClass(liveActivationStatus)}`}>
                            {liveActivationLabel}
                        </span>
                    </div>
                </div>
                <div className="mt-4 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        Клиент: {meData?.client?.name ?? "не выбран"}
                    </div>
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        Branch: {data.selected_branch_name ?? selectedBranchContext?.name ?? "не выбран"}
                    </div>
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        Preview:{" "}
                        {previewTruthSource === "draft"
                            ? "черновик"
                            : previewTruthSource === "published"
                              ? "опубликованный кандидат"
                              : previewTruthSource === "live"
                                ? "live версия"
                                : "не готов"}
                    </div>
                    <div className="rounded-lg border border-border/60 px-3 py-2">
                        Обновление для клиентов: {liveActivationLabel ?? "—"}
                    </div>
                </div>
                {liveActivationSummary && !branchSelectionRequired ? (
                    <p
                        className={`mt-3 rounded-lg px-3 py-2 text-sm ${liveActivationStatus === "failed" ? "border border-red-200 bg-red-50 text-red-800" : "border border-slate-300/70 bg-slate-50 text-slate-800"}`}
                        data-testid="consultant-verification-live-activation"
                    >
                        {liveActivationSummary}
                    </p>
                ) : null}
                {blockers.length > 0 ? (
                    <ul className="mt-3 space-y-2" data-testid="consultant-verification-blockers">
                        {blockers.map((blocker) => (
                            <li key={blocker} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                                {blocker}
                            </li>
                        ))}
                    </ul>
                ) : null}
            </section>

            {branchSelectionRequired ? (
                <ConsoleOwnerScopeGate
                    rootTestId="consultant-verification-branch-gate"
                    selectTestId="consultant-verification-branch-select"
                    applyTestId="consultant-verification-apply-branch"
                    title="Выберите филиал прямо здесь"
                    description="Выберите филиал здесь и продолжайте проверку без переходов между вкладками."
                    branchOptions={branchOptions}
                    selectedBranchId={branchDraftId}
                    onSelectedBranchChange={setBranchDraftId}
                    onApply={applyBranchContext}
                    applyLabel="Применить контекст"
                    applyPendingLabel="Применяю..."
                    isApplying={isFetching}
                    disabled={!canApplyBranchContext}
                    emptyStateDescription="Нет доступных филиалов в текущем контексте. Сначала выберите клиента или откройте Workspace."
                    links={[
                        { href: "/knowledge", label: "Открыть Знания" },
                        { href: "/company-workspace", label: "Открыть Workspace" },
                    ]}
                    className="mt-4"
                />
            ) : null}

            <section
                className="rounded-xl border border-border/60 bg-card p-4"
                data-testid="consultant-verification-status-card"
            >
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-sm text-muted-foreground">Статус контура проверки</p>
                        <p className="mt-1 text-base font-semibold text-foreground">{previewStatusLabel}</p>
                        <p className="mt-2 text-sm text-muted-foreground" data-testid="consultant-verification-summary">
                            {previewSummary}
                        </p>
                    </div>
                    <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${statusChipClass(previewStatus)}`}
                        data-testid="consultant-verification-status-chip"
                    >
                        {previewStatus}
                    </span>
                </div>
                <div className="mt-4 rounded-lg border border-border/60 bg-muted/20 p-3">
                    <p className="text-sm font-semibold text-foreground">Следующий блок</p>
                    <p
                        className="mt-1 text-sm text-muted-foreground"
                        data-testid="consultant-verification-next-wave-summary"
                    >
                        {data.next_wave_summary}
                    </p>
                </div>
                {!data.feature_enabled ? (
                    <p
                        className="mt-4 rounded-lg border border-slate-300/60 bg-slate-50 px-3 py-2 text-xs text-slate-700"
                        data-testid="consultant-verification-feature-gate"
                    >
                        Для этого клиента пока включен только обзор готовности. Интерактивная проверка откроется после
                        следующей волны rollout.
                    </p>
                ) : !(data?.can_verify_now ?? (previewStatus === "ready")) ? (
                    <p
                        className="mt-4 rounded-lg border border-slate-300/60 bg-slate-50 px-3 py-2 text-xs text-slate-700"
                        data-testid="consultant-verification-preview-gate"
                    >
                        Preview пока не готов. Подготовьте источник данных выше и затем запускайте проверку.
                    </p>
                ) : null}
            </section>

            <section
                className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3"
                data-testid="consultant-verification-readiness-grid"
            >
                {readinessCards.map((card) => (
                    <article
                        key={card.id}
                        className="rounded-xl border border-border/60 bg-card p-4"
                        data-testid={`consultant-verification-card-${card.id}`}
                    >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                            <h2 className="text-base font-semibold text-foreground">{card.title}</h2>
                            <span
                                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${cardStateClass(card.state)}`}
                            >
                                {card.state_label}
                            </span>
                        </div>
                        <p className="mt-2 text-sm text-muted-foreground">{card.summary}</p>
                        {card.evidence_label ? (
                            <p className="mt-3 text-xs text-muted-foreground">{card.evidence_label}</p>
                        ) : null}
                        {card.id === "knowledge_readiness" ? (
                            <p className="mt-1 text-xs text-muted-foreground">
                                Свежесть знаний: {formatHours(data.knowledge_stale_hours)}
                            </p>
                        ) : null}
                        {card.href ? (
                            <div className="mt-3">
                                <Link href={card.href} className="btn-ghost">
                                    Перейти
                                </Link>
                            </div>
                        ) : null}
                    </article>
                ))}
            </section>

            {workspaceReady ? <ConsultantVerificationWorkspace overview={data} role={role} /> : null}

            <section className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1.2fr_0.8fr]">
                <article
                    className="rounded-xl border border-border/60 bg-card p-4"
                    data-testid="consultant-verification-expectations"
                >
                    <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Как этим пользоваться</p>
                    <h2 className="mt-1 text-lg font-semibold">Проверяйте систему так, как проверит ее владелец бизнеса</h2>
                    <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                        {EXPECTATION_POINTS.map((item) => (
                            <li key={item} className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2">
                                {item}
                            </li>
                        ))}
                    </ul>
                </article>

                <article
                    className="rounded-xl border border-border/60 bg-card p-4"
                    data-testid="consultant-verification-examples"
                >
                    <p className="text-xs uppercase tracking-[0.16em] text-muted-foreground">Что спросить</p>
                    <h2 className="mt-1 text-lg font-semibold">Примеры неудобных проверок</h2>
                    <ol className="mt-3 space-y-2 text-sm text-muted-foreground">
                        {stressTestExamples.map((example, index) => (
                            <li key={example} className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2">
                                {index + 1}. {example}
                            </li>
                        ))}
                    </ol>
                </article>
            </section>

            <section
                className="mt-6 rounded-xl border border-border/60 bg-card p-4"
                data-testid="consultant-verification-actions"
            >
                <div className="mb-3 flex items-center justify-between">
                    <h2 className="text-lg font-semibold">Что сделать сейчас</h2>
                    <span className="text-xs text-muted-foreground">{actions.length} шага</span>
                </div>
                <div className="space-y-3">
                    {actions.map((action) => (
                        <article
                            key={action.id}
                            className="rounded-lg border border-border/60 bg-muted/20 p-3"
                            data-testid={`consultant-verification-action-${action.id}`}
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="text-sm font-semibold text-foreground">{action.title}</p>
                                <span
                                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${actionChipClass(action.severity)}`}
                                >
                                    {action.severity}
                                </span>
                            </div>
                            <p className="mt-1 text-sm text-muted-foreground">{action.description}</p>
                            <div className="mt-3">
                                <Link href={action.href} className="btn-ghost">
                                    Перейти
                                </Link>
                            </div>
                        </article>
                    ))}
                </div>
            </section>
        </div>
    );
}
