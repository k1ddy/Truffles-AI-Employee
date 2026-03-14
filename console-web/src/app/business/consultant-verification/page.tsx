"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";

import AccessDenied from "@/components/AccessDenied";
import { ConsolePageError, ConsolePageSkeleton } from "@/components/PageStates";
import { authApi, businessApi, canAccessConsole } from "@/lib/api-client";
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
                data-testid="consultant-verification-status-card"
            >
                <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <p className="text-sm text-muted-foreground">Статус контура проверки</p>
                        <p className="mt-1 text-base font-semibold text-foreground">{data.status_label}</p>
                        <p className="mt-2 text-sm text-muted-foreground" data-testid="consultant-verification-summary">
                            {data.summary}
                        </p>
                    </div>
                    <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${statusChipClass(data.status)}`}
                        data-testid="consultant-verification-status-chip"
                    >
                        {data.status}
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
                ) : null}
            </section>

            <section
                className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3"
                data-testid="consultant-verification-readiness-grid"
            >
                {data.readiness_cards.map((card) => (
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

            {data.feature_enabled ? <ConsultantVerificationWorkspace overview={data} /> : null}

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
                        {data.stress_test_examples.map((example, index) => (
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
                    <span className="text-xs text-muted-foreground">{data.actions.length} шага</span>
                </div>
                <div className="space-y-3">
                    {data.actions.map((action) => (
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
