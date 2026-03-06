"use client";

import { useEffect, useMemo, useRef, useState, type MouseEvent, type ReactNode } from "react";
import { signOut, useSession } from "next-auth/react";
import { usePathname, useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Image from "next/image";
import Link from "next/link";
import toast from "react-hot-toast";

import LoginButton from "@/components/LoginButton";
import {
    adminApi,
    authApi,
    businessApi,
    canAccessConsole,
    opsApi,
    parseApiError,
    type ConsoleAction,
    type ConsoleRole,
    type ConsoleSection,
    type HealthResponse,
    type IncidentItem,
    type IncidentListResponse,
} from "@/lib/api-client";
import {
    clearConsoleContextScope,
    readConsoleContextScopeFromStorage,
    setConsoleBranchContext,
    setConsoleClientContext,
    setConsoleCompanyContext,
    writeConsoleContextScopeToStorage,
} from "@/lib/console-context-storage";
import { readBrowserStorage, writeBrowserStorage } from "@/lib/browser-storage";
import { QUERY_PROFILE_CONTEXT } from "@/lib/query-profiles";

const NAV_COLLAPSED_STORAGE_KEY = "console:nav_collapsed";
const OWNER_ADMIN_ADVANCED_NAV_STORAGE_KEY = "console:owner_admin_advanced_nav";
const AUTH_ERROR_CODES = new Set(["AUTH_REQUIRED", "TOKEN_EXPIRED", "TOKEN_INVALID"]);
const HEALTH_INCIDENT_UI_STORAGE_KEY = "console:health_incident_ui";
const HEALTH_INCIDENT_CRITICAL_BACKLOG = 1000;
const HEALTH_INCIDENT_WARN_BACKLOG = 500;
const HEALTH_INCIDENT_STALE_WARN_MINUTES = 3;
const HEALTH_INCIDENT_HIDE_MS = 30 * 60 * 1000;
const HEALTH_INCIDENT_REFRESH_TIMEOUT_MS = 1500;
const OWNER_ADMIN_PRIMARY_NAV_TEST_IDS = new Set<string>([
    "nav-cases",
    "nav-calendar",
    "nav-marketing",
    "nav-ops",
    "nav-business",
    "nav-data-trust",
    "nav-team-performance",
    "nav-subscription",
    "nav-settings",
]);

type SessionAuth = {
    accessToken?: string;
    error?: string;
};

type ClientSummary = {
    id?: string;
    name?: string;
    company_id?: string | null;
    company_name?: string | null;
};

type CompanySummary = {
    id?: string;
    name?: string;
};

type BranchSummary = {
    id?: string;
    name?: string;
};

type ConsoleMe = {
    agent?: { role?: ConsoleRole | null };
    client?: ClientSummary | null;
    clients?: ClientSummary[];
    companies?: CompanySummary[];
    company_selection_required?: boolean;
    branches?: BranchSummary[];
    selection_required?: boolean;
    branch_selection_required?: boolean;
    selected_company_id?: string | null;
    selected_branch_id?: string | null;
};

type NavItem = {
    label: string;
    href: string;
    section: ConsoleSection;
    action?: ConsoleAction;
    testId: string;
};

const NAV_ITEMS: NavItem[] = [
    { label: "Тенанты", href: "/tenants", section: "tenants", action: "read", testId: "nav-tenants" },
    { label: "Компании", href: "/company-workspace", section: "tenants", action: "read", testId: "nav-company-workspace" },
    { label: "Интеграции", href: "/integrations", section: "integrations", action: "read", testId: "nav-integrations" },
    { label: "Заявки", href: "/", section: "inbox", action: "read", testId: "nav-cases" },
    { label: "Записи", href: "/calendar", section: "calendar", action: "read", testId: "nav-calendar" },
    { label: "Маркетинг", href: "/marketing", section: "marketing", action: "read", testId: "nav-marketing" },
    { label: "Знания", href: "/knowledge", section: "knowledge", action: "read", testId: "nav-knowledge" },
    { label: "Команда", href: "/team", section: "team", action: "read", testId: "nav-team" },
    { label: "Статус", href: "/ops", section: "ops", action: "read", testId: "nav-ops" },
    { label: "Журнал", href: "/audit", section: "audit", action: "read", testId: "nav-audit" },
    { label: "Аналитика", href: "/insights", section: "insights", action: "read", testId: "nav-insights" },
    { label: "Бизнес", href: "/business", section: "business", action: "read", testId: "nav-business" },
    { label: "Данные", href: "/business/data-trust", section: "business", action: "read", testId: "nav-data-trust" },
    { label: "Команда KPI", href: "/business/team-performance", section: "business", action: "read", testId: "nav-team-performance" },
    { label: "Подписка", href: "/subscription", section: "subscription", action: "read", testId: "nav-subscription" },
    { label: "Настройки", href: "/settings", section: "settings", action: "read", testId: "nav-settings" },
];

const CONTEXT_AWARE_QUERY_KEY_PREFIXES = [
    "admin-",
    "agents",
    "audit",
    "bookings",
    "business-",
    "calendar-",
    "case",
    "cases",
    "company-workspace-",
    "console-health-banner",
    "console-health-incident-feed",
    "console-me",
    "health",
    "inbox-macros",
    "insights-",
    "integrations-",
    "knowledge-",
    "marketing-",
    "learning-candidates",
    "membership-",
    "messages",
    "metrics-daily",
    "onboarding-",
    "ops-",
    "provider-lifecycle",
    "settings",
    "slots",
    "specialists",
    "subscription-",
    "team-",
    "telegram-health",
    "tenants-",
] as const;

function isContextAwareQueryKey(queryKey: readonly unknown[]): boolean {
    const head = queryKey[0];
    if (typeof head !== "string") {
        return false;
    }
    return CONTEXT_AWARE_QUERY_KEY_PREFIXES.some((prefix) =>
        head === prefix || head.startsWith(prefix)
    );
}

const ROLE_LABELS: Record<ConsoleRole, string> = {
    platform_admin: "Платформа: админ",
    owner: "Owner",
    admin: "Админ",
    manager: "Менеджер",
    support: "Поддержка",
    specialist: "Специалист",
    viewer: "Наблюдатель",
};

function NavIcon({ children, className }: { children: ReactNode; className?: string }) {
    return (
        <svg
            className={className ?? "h-5 w-5"}
            width={20}
            height={20}
            style={{ width: 20, height: 20, maxWidth: 20, maxHeight: 20 }}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.8}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
        >
            {children}
        </svg>
    );
}

const NAV_ICONS: Partial<Record<ConsoleSection, ReactNode>> = {
    tenants: (
        <NavIcon>
            <path d="M4 20h16" />
            <rect x="6" y="6" width="12" height="14" rx="2" />
            <path d="M9 10h2M13 10h2M9 14h2M13 14h2" />
        </NavIcon>
    ),
    provisioning: (
        <NavIcon>
            <rect x="3" y="5" width="6" height="6" rx="1.5" />
            <rect x="15" y="5" width="6" height="6" rx="1.5" />
            <rect x="9" y="13" width="6" height="6" rx="1.5" />
            <path d="M9 8h6M12 11v2" />
        </NavIcon>
    ),
    inbox: (
        <NavIcon>
            <path d="M4 4h16v10H4z" />
            <path d="M4 14h4l2 3h4l2-3h4" />
        </NavIcon>
    ),
    calendar: (
        <NavIcon>
            <rect x="4" y="5" width="16" height="15" rx="2" />
            <path d="M8 3v4M16 3v4M4 9h16" />
        </NavIcon>
    ),
    marketing: (
        <NavIcon>
            <path d="M4 11l13-6v14L4 13z" />
            <path d="M17 10h3" />
            <path d="M8 14v4" />
            <path d="M6 18h4" />
        </NavIcon>
    ),
    knowledge: (
        <NavIcon>
            <rect x="4" y="4" width="16" height="16" rx="2" />
            <path d="M8 8h8M8 12h8M8 16h5" />
        </NavIcon>
    ),
    team: (
        <NavIcon>
            <path d="M4 19c0-3 3-5 6-5s6 2 6 5" />
            <circle cx="10" cy="9" r="3" />
            <path d="M16 19c0-2 2-4 4-4" />
            <circle cx="18" cy="10" r="2" />
        </NavIcon>
    ),
    ops: (
        <NavIcon>
            <path d="M3 12h4l2-4 4 8 2-4h6" />
        </NavIcon>
    ),
    audit: (
        <NavIcon>
            <path d="M4 6h1M4 12h1M4 18h1" />
            <path d="M8 6h12M8 12h12M8 18h12" />
        </NavIcon>
    ),
    insights: (
        <NavIcon>
            <path d="M4 19h16" />
            <path d="M7 16v-6" />
            <path d="M12 16v-10" />
            <path d="M17 16v-3" />
        </NavIcon>
    ),
    business: (
        <NavIcon>
            <path d="M4 20h16" />
            <rect x="5" y="11" width="4" height="7" rx="1" />
            <rect x="10" y="8" width="4" height="10" rx="1" />
            <rect x="15" y="5" width="4" height="13" rx="1" />
        </NavIcon>
    ),
    subscription: (
        <NavIcon>
            <circle cx="12" cy="12" r="8" />
            <path d="M9.5 9.5c.4-1 1.4-1.6 2.6-1.6 1.5 0 2.7.9 2.7 2.1 0 1.1-.9 1.7-2.2 2.1l-1 .3c-1.1.3-1.6.7-1.6 1.5 0 1 1 1.8 2.5 1.8 1.3 0 2.2-.5 2.8-1.4" />
            <path d="M12 6.5v11" />
        </NavIcon>
    ),
    settings: (
        <NavIcon>
            <circle cx="12" cy="12" r="3" />
            <path d="M12 3v2M12 19v2M4.5 4.5l1.4 1.4M18.1 18.1l1.4 1.4M3 12h2M19 12h2M4.5 19.5l1.4-1.4M18.1 5.9l1.4-1.4" />
        </NavIcon>
    ),
};

function formatCompanyLabel(companyName?: string | null, companyId?: string | null): string {
    if (companyName) {
        return companyName;
    }
    if (companyId) {
        return companyId.slice(0, 8);
    }
    return "—";
}

function formatContextLabel(name?: string | null, fallbackId?: string | null): string {
    if (name && name !== "—") {
        return name;
    }
    if (fallbackId) {
        return fallbackId;
    }
    return "—";
}

function findClientName(
    clients: ClientSummary[] | undefined,
    clientId: string | null | undefined,
    fallbackName: string | null | undefined,
): string {
    if (clientId && clients?.length) {
        const match = clients.find((client) => client.id === clientId);
        if (match?.name) {
            return match.name;
        }
    }
    if (fallbackName) {
        return fallbackName;
    }
    if (clients?.length === 1) {
        return clients[0].name ?? clients[0].id ?? "—";
    }
    return clients?.length ? "Выберите клиента" : "Нет активных клиентов";
}

function findBranchName(
    branches: BranchSummary[] | undefined,
    branchId: string | null | undefined,
    allowAllBranches = false,
): string {
    if (!branches?.length) {
        return "Нет активных филиалов";
    }
    if (branchId) {
        const match = branches.find((branch) => branch.id === branchId);
        if (match?.name) {
            return match.name;
        }
    }
    if (branches.length === 1) {
        return branches[0].name ?? branches[0].id ?? "—";
    }
    if (allowAllBranches) {
        return "Все филиалы";
    }
    return "Выберите филиал";
}

function isNavItemCurrent(pathname: string, href: string): boolean {
    if (href === "/") {
        return pathname === "/";
    }
    return pathname === href || pathname.startsWith(`${href}/`);
}

type HealthIncident = {
    severity: "critical" | "warn";
    status: string;
    backlog: number;
    reasonCode: IncidentItem["reason_code"] | "redis_mandatory";
    title: string;
    summary: string;
    reasons: string[];
    runbook: string[];
    updatedAtLabel: string;
};

type HealthIncidentUiState = {
    hiddenUntilTs: number;
};

type ContextHealthTone = "ok" | "info" | "warn";

type ContextHealthMessage = {
    id: string;
    tone: ContextHealthTone;
    text: string;
};

function formatRelativeAgeLabel(timestampMs: number): string {
    if (!Number.isFinite(timestampMs) || timestampMs <= 0) {
        return "время обновления неизвестно";
    }
    const elapsedMs = Date.now() - timestampMs;
    if (!Number.isFinite(elapsedMs) || elapsedMs < 0) {
        return "обновлено только что";
    }
    const elapsedMinutes = Math.floor(elapsedMs / 60000);
    if (elapsedMinutes <= 0) {
        return "обновлено только что";
    }
    if (elapsedMinutes === 1) {
        return "обновлено 1 минуту назад";
    }
    return `обновлено ${elapsedMinutes} минут назад`;
}

function readHealthIncidentUiState(): HealthIncidentUiState {
    const raw = readBrowserStorage(HEALTH_INCIDENT_UI_STORAGE_KEY);
    if (!raw) {
        return {
            hiddenUntilTs: 0,
        };
    }
    try {
        const parsed = JSON.parse(raw) as Partial<HealthIncidentUiState> & { hiddenUntilByFingerprint?: Record<string, unknown> };
        let hiddenUntilTs = Number.isFinite(parsed.hiddenUntilTs) ? Number(parsed.hiddenUntilTs) : 0;
        // Backward compatibility with older per-fingerprint storage.
        if (!hiddenUntilTs && parsed.hiddenUntilByFingerprint && typeof parsed.hiddenUntilByFingerprint === "object") {
            const values = Object.values(parsed.hiddenUntilByFingerprint)
                .map((value) => (Number.isFinite(value) ? Number(value) : 0))
                .filter((value) => value > 0);
            if (values.length > 0) {
                hiddenUntilTs = Math.max(...values);
            }
        }
        return {
            hiddenUntilTs,
        };
    } catch {
        return {
            hiddenUntilTs: 0,
        };
    }
}

function pickTopIncident(incidentList?: IncidentListResponse | null): IncidentItem | null {
    const items = incidentList?.items ?? [];
    if (items.length === 0) {
        return null;
    }
    const severityWeight: Record<IncidentItem["severity"], number> = {
        critical: 3,
        warn: 2,
        info: 1,
    };
    return [...items].sort((left, right) => {
        const bySeverity = severityWeight[right.severity] - severityWeight[left.severity];
        if (bySeverity !== 0) {
            return bySeverity;
        }
        return new Date(right.detected_at).getTime() - new Date(left.detected_at).getTime();
    })[0] ?? null;
}

function incidentHref(basePath: string, incident?: IncidentItem | null): string {
    if (!incident) {
        return basePath;
    }
    const params = new URLSearchParams();
    params.set("incident_id", incident.id);
    params.set("reason", incident.reason_code);
    params.set("severity", incident.severity);
    if (incident.client_id) {
        params.set("client_id", incident.client_id);
    }
    if (incident.branch_id) {
        params.set("branch_id", incident.branch_id);
    }
    return `${basePath}?${params.toString()}`;
}

function incidentRunbook(reasonCode: IncidentItem["reason_code"] | "redis_mandatory", ownerAdminView: boolean): string[] {
    if (reasonCode === "redis_mandatory") {
        return ownerAdminView
            ? [
                "Откройте «Статус» и проверьте, что Redis в состоянии connected.",
                "Если Redis error, проверьте REDIS_URL и сетевой доступ до инстанса Redis.",
                "После восстановления нажмите «Обновить health» и убедитесь, что риск снят.",
            ]
            : [
                "Откройте OPS и проверьте карточку компонента Redis.",
                "Если Redis недоступен, проверьте REDIS_URL/credentials и сетевую связность контейнера API.",
                "После фикса обновите health и зафиксируйте remediation в журнале.",
            ];
    }

    if (reasonCode === "integration_degraded") {
        return ownerAdminView
            ? [
                "Откройте Workspace и проверьте branch-лидеры с интеграционной деградацией.",
                "Для проблемного филиала выполните dry-run сверки интеграции.",
                "После подтверждения примените execute и проверьте стабилизацию failed_24h.",
            ]
            : [
                "Откройте OPS и посмотрите failed_24h + последний error.",
                "Откройте Workspace и выполните integration_reconcile в dry-run для проблемного филиала.",
                "Если dry-run чистый, выполните execute и перепроверьте тренд ошибок.",
            ];
    }

    if (reasonCode === "outbox_backlog") {
        return ownerAdminView
            ? [
                "Откройте «Статус» и проверьте рост pending/failed за последние минуты.",
                "Запустите dry-run outbox_process и оцените готовность к execute.",
                "Если backlog растет, эскалируйте инцидент до P0.",
            ]
            : [
                "Откройте OPS и разберите outbox failed/pending.",
                "Запустите outbox_process dry-run, затем execute при безопасном результате.",
                "Проверьте, что после выполнения backlog идет вниз.",
            ];
    }

    if (reasonCode === "provider_billing_blocked" || reasonCode === "provider_unavailable" || reasonCode === "provider_auth" || reasonCode === "provider_rate_limited") {
        return ownerAdminView
            ? [
                "Откройте Workspace и проверьте связку provider по проблемному филиалу.",
                "Сделайте dry-run remedation действия из карточки инцидента.",
                "После execute убедитесь, что нет роста failed_24h и интеграция стабилизирована.",
            ]
            : [
                "Откройте OPS и зафиксируйте тип provider-деградации.",
                "В Workspace выполните рекомендуемое действие сначала в dry-run.",
                "После execute проверьте, что риск снят и ошибки больше не растут.",
            ];
    }

    if (reasonCode === "handover_backlog") {
        return ownerAdminView
            ? [
                "Откройте «Заявки» и проверьте объем неразобранных handoff.",
                "Увеличьте покрытие менеджеров и перераспределите SLA-очередь.",
                "Если старение заявок растет, поднимите приоритет инцидента.",
            ]
            : [
                "Откройте очередь handoff в Inbox и проверьте oldest age.",
                "Разгрузите backlog приоритетными ответами.",
                "Проверьте, что новые handoff закрываются в SLA.",
            ];
    }

    return ownerAdminView
        ? [
            "Откройте «Статус» и проверьте фактическую динамику сигналов риска.",
            "Перейдите в Workspace по проблемному филиалу и выполните dry-run remediation.",
            "Если причина не ясна, зафиксируйте инцидент в журнале и эскалируйте до platform admin.",
        ]
        : [
            "Откройте OPS и проверьте детальные метрики инцидента.",
            "Перейдите в Workspace и выполните безопасную диагностику по филиалу.",
            "При отсутствии эффекта эскалируйте с trace/job evidence.",
        ];
}

function contextHealthToneClass(tone: ContextHealthTone): string {
    if (tone === "warn") {
        return "border-amber-300/80 bg-amber-50 text-amber-900";
    }
    if (tone === "info") {
        return "border-sky-300/80 bg-sky-50 text-sky-900";
    }
    return "border-emerald-300/80 bg-emerald-50 text-emerald-900";
}

function deriveHealthIncident(
    health?: HealthResponse | null,
    updatedAtMs?: number,
    options?: { ownerAdminView?: boolean; topIncident?: IncidentItem | null },
): HealthIncident | null {
    if (!health) {
        return null;
    }

    const ownerAdminView = options?.ownerAdminView ?? false;
    const topIncident = options?.topIncident ?? null;
    const statusRaw = health.status ?? "healthy";
    const status = statusRaw === "healthy" ? "ok" : statusRaw;
    const backlog = health.outbox_backlog ?? 0;
    const redisStatus = health.redis ?? "unknown";
    const reasons: string[] = [];
    let severity: "critical" | "warn" | null = null;

    if (statusRaw === "unhealthy" || backlog >= HEALTH_INCIDENT_CRITICAL_BACKLOG) {
        severity = "critical";
    }

    if (!severity && (statusRaw === "degraded" || backlog >= HEALTH_INCIDENT_WARN_BACKLOG)) {
        severity = "warn";
    }

    const redisDegraded = redisStatus !== "connected";
    if (!severity && redisDegraded) {
        severity = "warn";
    }

    if (statusRaw === "unhealthy" || statusRaw === "degraded") {
        reasons.push(ownerAdminView ? `Статус сервиса: ${status}` : `health.status=${status}`);
    }
    if (redisDegraded) {
        reasons.push(
            ownerAdminView
                ? `Redis обязателен: состояние ${redisStatus}`
                : `redis.status=${redisStatus} (mandatory)`,
        );
    }
    if (backlog >= HEALTH_INCIDENT_CRITICAL_BACKLOG) {
        reasons.push(
            ownerAdminView
                ? `Очередь отправки: ${backlog} (критично)`
                : `outbox_backlog=${backlog} (>= ${HEALTH_INCIDENT_CRITICAL_BACKLOG})`,
        );
    } else if (backlog >= HEALTH_INCIDENT_WARN_BACKLOG) {
        reasons.push(
            ownerAdminView
                ? `Очередь отправки: ${backlog} (повышенный риск)`
                : `outbox_backlog=${backlog} (>= ${HEALTH_INCIDENT_WARN_BACKLOG})`,
        );
    }

    const updatedAgeLabel = formatRelativeAgeLabel(updatedAtMs ?? 0);
    const staleMinutes = Number.isFinite(updatedAtMs) && (updatedAtMs ?? 0) > 0
        ? Math.floor((Date.now() - (updatedAtMs ?? 0)) / 60000)
        : null;
    if (staleMinutes !== null && staleMinutes >= HEALTH_INCIDENT_STALE_WARN_MINUTES) {
        reasons.push(
            ownerAdminView
                ? `Данные обновлялись давно: ${staleMinutes} мин назад`
                : `telemetry stale=${staleMinutes}m`,
        );
        if (!severity) {
            severity = "warn";
        }
    }

    if (!severity) {
        return null;
    }

    const reasonCode: IncidentItem["reason_code"] | "redis_mandatory" = redisDegraded
        ? "redis_mandatory"
        : (topIncident?.reason_code ?? "unknown");
    const runbook = incidentRunbook(reasonCode, ownerAdminView);

    if (topIncident) {
        reasons.push(ownerAdminView ? `Причина: ${topIncident.reason_label}` : `incident.reason_code=${topIncident.reason_code}`);
        reasons.push(ownerAdminView ? `Деталь: ${topIncident.summary}` : `incident.summary=${topIncident.summary}`);
        if (topIncident.severity === "critical") {
            severity = "critical";
        } else if (!severity) {
            severity = "warn";
        }
    }

    const uniqueReasons = Array.from(new Set(reasons));

    if (reasons.length === 0) {
        uniqueReasons.push(`status=${status}, outbox_backlog=${backlog}`);
    }

    return {
        severity,
        status,
        backlog,
        reasonCode,
        title: severity === "critical"
            ? ownerAdminView
                ? "Критичный риск для клиентских сообщений (P0)"
                : "Критичный инцидент платформы (P0)"
            : ownerAdminView
                ? "Повышенный риск задержек сообщений (P1)"
                : "Риск деградации платформы (P1)",
        summary: ownerAdminView
            ? `Статус сервиса: ${status} · очередь отправки: ${backlog}`
            : `status=${status}, outbox_backlog=${backlog}`,
        reasons: uniqueReasons,
        runbook,
        updatedAtLabel: updatedAgeLabel,
    };
}

function SelectionGate({
    me,
    clients,
    onConfirmCompany,
    onConfirmClient,
    onConfirmBranch,
    isSubmitting,
}: {
    me: ConsoleMe;
    clients: ClientSummary[];
    onConfirmCompany: (companyId: string) => void;
    onConfirmClient: (clientId: string) => void;
    onConfirmBranch: (branchId: string) => void;
    isSubmitting: boolean;
}) {
    const [companyId, setCompanyId] = useState(() => me.selected_company_id ?? "");
    const [clientId, setClientId] = useState(() => me.client?.id ?? "");
    const [branchId, setBranchId] = useState(() => me.selected_branch_id ?? "");

    useEffect(() => {
        setCompanyId(me.selected_company_id ?? "");
    }, [me.selected_company_id]);

    useEffect(() => {
        setClientId(me.client?.id ?? "");
    }, [me.client?.id]);

    useEffect(() => {
        setBranchId(me.selected_branch_id ?? "");
    }, [me.selected_branch_id]);

    if (me.company_selection_required) {
        return (
            <div className="card-surface p-8 max-w-xl">
                <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Требуется выбор</p>
                <h2 className="text-2xl font-semibold mt-3 mb-4">Выберите компанию</h2>
                <p className="text-sm text-muted-foreground mb-6">
                    Доступно несколько компаний. Выберите контекст, чтобы загрузить данные.
                </p>
                <select
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    value={companyId}
                    onChange={(event) => setCompanyId(event.target.value)}
                    data-testid="company-select"
                >
                    <option value="">Выберите компанию</option>
                    {(me.companies ?? []).map((company) => (
                        <option key={company.id} value={company.id}>
                            {company.name ?? company.id}
                        </option>
                    ))}
                </select>
                <p className="mt-2 text-xs text-muted-foreground">
                    Доступно компаний: {(me.companies ?? []).length}
                </p>
                <div className="mt-6 flex justify-end">
                    <button
                        className="btn-primary"
                        onClick={() => onConfirmCompany(companyId)}
                        disabled={!companyId || isSubmitting}
                        data-testid="company-select-confirm"
                    >
                        {isSubmitting ? "Загрузка..." : "Продолжить"}
                    </button>
                </div>
            </div>
        );
    }

    if (me.selection_required) {
        return (
            <div className="card-surface p-8 max-w-xl">
                <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Требуется выбор</p>
                <h2 className="text-2xl font-semibold mt-3 mb-4">Выберите клиента</h2>
                <p className="text-sm text-muted-foreground mb-6">
                    Доступно несколько клиентов. Выберите контекст, чтобы загрузить данные.
                </p>
                <select
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    value={clientId}
                    onChange={(event) => setClientId(event.target.value)}
                    data-testid="client-select"
                >
                    <option value="">Выберите клиента</option>
                    {clients.map((client) => (
                        <option key={client.id} value={client.id}>
                            {client.name ?? client.id}
                        </option>
                    ))}
                </select>
                <p className="mt-2 text-xs text-muted-foreground">
                    Доступно клиентов: {clients.length}
                </p>
                <div className="mt-6 flex justify-end">
                    <button
                        className="btn-primary"
                        onClick={() => onConfirmClient(clientId)}
                        disabled={!clientId || isSubmitting}
                        data-testid="client-select-confirm"
                    >
                        {isSubmitting ? "Загрузка..." : "Продолжить"}
                    </button>
                </div>
            </div>
        );
    }

    if (me.branch_selection_required) {
        return (
            <div className="card-surface p-8 max-w-xl">
                <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">Требуется выбор</p>
                <h2 className="text-2xl font-semibold mt-3 mb-4">Выберите филиал</h2>
                <p className="text-sm text-muted-foreground mb-6">
                    Для вашей роли нужен филиал. Выберите, чтобы продолжить работу.
                </p>
                <select
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    value={branchId}
                    onChange={(event) => setBranchId(event.target.value)}
                    data-testid="branch-select"
                >
                    <option value="">Выберите филиал</option>
                    {(me.branches ?? []).map((branch) => (
                        <option key={branch.id} value={branch.id}>
                            {branch.name ?? branch.id}
                        </option>
                    ))}
                </select>
                <p className="mt-2 text-xs text-muted-foreground">
                    Доступно филиалов: {(me.branches ?? []).length}
                </p>
                <div className="mt-6 flex justify-end">
                    <button
                        className="btn-primary"
                        onClick={() => onConfirmBranch(branchId)}
                        disabled={!branchId || isSubmitting}
                        data-testid="branch-select-confirm"
                    >
                        {isSubmitting ? "Загрузка..." : "Продолжить"}
                    </button>
                </div>
            </div>
        );
    }

    return null;
}

function ContextBar({
    me,
    companyId,
    clients,
    onSelectCompany,
    onSelectClient,
    onSelectBranch,
    showActiveScopeHint,
    isBusy,
}: {
    me: ConsoleMe;
    companyId: string;
    clients: ClientSummary[];
    onSelectCompany: (companyId: string) => void;
    onSelectClient: (clientId: string) => void;
    onSelectBranch: (branchId: string | null) => void;
    showActiveScopeHint: boolean;
    isBusy: boolean;
}) {
    const companies = me.companies ?? [];
    const branches = me.branches ?? [];
    const clientId = me.client?.id ?? "";
    const branchId = me.selected_branch_id ?? "";
    const allowAllBranches = !me.branch_selection_required;
    const companyName = companies.find((company) => company.id === companyId)?.name ?? me.client?.company_name;
    const clientName = findClientName(clients, clientId, me.client?.name);
    const branchName = findBranchName(branches, branchId, allowAllBranches);

    return (
        <div className="flex flex-wrap items-start gap-x-5 gap-y-2 text-sm" data-testid="context-bar">
            <div className="flex flex-col gap-1 min-w-[140px]">
                <span className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Компания</span>
                {companies.length > 1 ? (
                    <select
                        className="rounded-lg border border-border bg-background px-2 py-1 text-sm"
                        value={companyId}
                        onChange={(event) => onSelectCompany(event.target.value)}
                        disabled={isBusy}
                        data-testid="context-company-select"
                    >
                        <option value="">Выберите компанию</option>
                        {companies.map((company) => (
                            <option key={company.id} value={company.id}>
                                {company.name ?? company.id}
                            </option>
                        ))}
                    </select>
                ) : (
                    <span className="text-sm font-semibold" data-testid="context-company-value">
                        {formatCompanyLabel(companyName, companyId)}
                    </span>
                )}
            </div>
            <div className="flex flex-col gap-1 min-w-[180px]">
                <span className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Клиент</span>
                {clients.length > 1 ? (
                    <select
                        className="rounded-lg border border-border bg-background px-2 py-1 text-sm"
                        value={clientId}
                        onChange={(event) => onSelectClient(event.target.value)}
                        disabled={isBusy}
                        data-testid="context-client-select"
                    >
                        {clients.map((client) => (
                            <option key={client.id} value={client.id}>
                                {client.name ?? client.id}
                            </option>
                        ))}
                    </select>
                ) : (
                    <span className="text-sm font-semibold" data-testid="context-client-value">{clientName}</span>
                )}
            </div>
            <div className="flex flex-col gap-1 min-w-[180px]">
                <span className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">Филиал</span>
                {branches.length > 1 ? (
                    <select
                        className="rounded-lg border border-border bg-background px-2 py-1 text-sm"
                        value={branchId}
                        onChange={(event) => onSelectBranch(event.target.value || null)}
                        disabled={isBusy}
                        data-testid="context-branch-select"
                    >
                        {allowAllBranches && <option value="">Все филиалы</option>}
                        {branches.map((branch) => (
                            <option key={branch.id} value={branch.id}>
                                {branch.name ?? branch.id}
                            </option>
                        ))}
                    </select>
                ) : (
                    <span className="text-sm font-semibold" data-testid="context-branch-value">
                        {branchName}
                    </span>
                )}
            </div>
            {showActiveScopeHint && (
                <div className="flex min-w-[200px] items-end">
                    <span
                        className="inline-flex w-fit rounded-full border border-sky-300/80 bg-sky-50 px-2 py-1 text-[11px] font-medium text-sky-900"
                        data-testid="context-active-scope-hint"
                        title="Архив и деактивированные в Тенантах."
                        aria-label="Режим данных: Активные"
                    >
                        Режим данных: Активные
                    </span>
                </div>
            )}
        </div>
    );
}

function ContextHealthStrip({
    me,
    companyId,
    visibleClients,
    canReadOps,
    canReadTenants,
    onOpenOps,
    onOpenTenants,
}: {
    me: ConsoleMe;
    companyId: string;
    visibleClients: ClientSummary[];
    canReadOps: boolean;
    canReadTenants: boolean;
    onOpenOps: () => void;
    onOpenTenants: () => void;
}) {
    const companies = me.companies ?? [];
    const clients = me.clients ?? [];
    const branches = me.branches ?? [];
    const warningMessages: ContextHealthMessage[] = [];
    const infoMessages: ContextHealthMessage[] = [];

    if (companies.length > 1 && !companyId) {
        warningMessages.push({
            id: "company_missing",
            tone: "warn",
            text: "Контекст компании не выбран. Данные могут выглядеть неполными.",
        });
    }
    if (companyId && clients.length > 0 && visibleClients.length === 0) {
        warningMessages.push({
            id: "no_clients_for_company",
            tone: "warn",
            text: "Для выбранной компании нет активных клиентов.",
        });
    }
    if (branches.length === 0) {
        warningMessages.push({
            id: "no_active_branches",
            tone: "warn",
            text: "В текущем контексте нет активных филиалов.",
        });
    } else if (!me.branch_selection_required && !me.selected_branch_id && branches.length > 1) {
        infoMessages.push({
            id: "all_branches_mode",
            tone: "info",
            text: "Все активные филиалы в текущем контексте.",
        });
    }
    const messages = warningMessages.length > 0 ? warningMessages : infoMessages;
    const showHealthBadges = messages.length > 0;
    const showMobileActions = canReadOps || canReadTenants;

    return (
        <>
            {showHealthBadges && (
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[12px]" data-testid="context-health-strip">
                    {messages.map((message) => (
                        <span
                            key={message.id}
                            className={`rounded-full border px-2 py-1 ${contextHealthToneClass(message.tone)}`}
                            data-testid={`context-health-${message.id}`}
                        >
                            {message.text}
                        </span>
                    ))}
                </div>
            )}
            {showMobileActions && (
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px] md:hidden">
                    {canReadOps && (
                        <button
                            type="button"
                            className="btn-ghost text-[12px]"
                            data-testid="context-health-open-ops"
                            onClick={onOpenOps}
                        >
                            Открыть Ops
                        </button>
                    )}
                    {canReadTenants && (
                        <button
                            type="button"
                            className="btn-ghost text-[12px]"
                            data-testid="context-health-open-tenants"
                            onClick={onOpenTenants}
                        >
                            Открыть Тенанты
                        </button>
                    )}
                </div>
            )}
        </>
    );
}

function PublicLanding() {
    return (
        <div className="min-h-screen bg-background">
            <header className="border-b border-border/60 bg-background/80 backdrop-blur">
                <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
                    <div className="flex items-center gap-3">
                        <Image
                            src="/brand/truffles-logo.png"
                            alt="Truffles"
                            width={140}
                            height={40}
                            className="h-7 w-auto"
                            priority
                        />
                        <span className="hidden text-xs uppercase tracking-[0.3em] text-muted-foreground sm:inline">
                            Truffles Console
                        </span>
                    </div>
                    <LoginButton />
                </div>
            </header>
            <main className="mx-auto flex max-w-3xl flex-col items-center px-6 py-20 text-center">
                <span className="badge mb-6">Control Plane</span>
                <h1 className="text-3xl font-semibold md:text-4xl">Панель управления AI‑ассистентом</h1>
                <p className="mt-4 text-base text-muted-foreground">
                    Войдите в систему, чтобы управлять заявками, расписанием и настройками.
                </p>
            </main>
        </div>
    );
}

export default function ConsoleShell({ children }: { children: React.ReactNode }) {
    const { status, data: session } = useSession();
    const pathname = usePathname();
    const router = useRouter();
    const e2eBypassAuth =
        process.env.NEXT_PUBLIC_E2E_BYPASS_AUTH === "1" &&
        typeof window !== "undefined" &&
        /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname);
    const sessionAuth = session as SessionAuth | null;
    const sessionError = sessionAuth?.error;
    const accessToken = sessionAuth?.accessToken;
    const hasSession = (status === "authenticated" && !!accessToken && !sessionError) || e2eBypassAuth;
    const queryClient = useQueryClient();
    const isInboxPage = pathname === "/" || pathname.startsWith("/cases") || pathname.startsWith("/calendar");
    const isTenantsPage = pathname === "/tenants" || pathname.startsWith("/tenants/");
    const contentWidthClass = isInboxPage ? "max-w-[1440px]" : "max-w-6xl";
    const contentFrameClass = isInboxPage ? "h-full min-h-0" : "";
    const signOutTriggered = useRef(false);

    const { data, isLoading, isFetching, error, refetch } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data as ConsoleMe;
        },
        enabled: hasSession,
        ...QUERY_PROFILE_CONTEXT,
    });

    useEffect(() => {
        if (signOutTriggered.current || status !== "authenticated") {
            return;
        }

        if (sessionError || !accessToken) {
            signOutTriggered.current = true;
            clearConsoleContextScope();
            toast.error("Сессия истекла. Войдите снова.");
            signOut({ callbackUrl: "/" });
            return;
        }

        if (error) {
            const parsed = parseApiError(error);
            if (AUTH_ERROR_CODES.has(parsed.code)) {
                signOutTriggered.current = true;
                clearConsoleContextScope();
                toast.error("Сессия истекла. Войдите снова.");
                signOut({ callbackUrl: "/" });
            }
        }
    }, [accessToken, error, sessionError, status]);

    const role = data?.agent?.role ?? "manager";
    const canReadOps = canAccessConsole(role, "ops", "read");
    const canReadTenants = canAccessConsole(role, "tenants", "read");
    const isPlatformAdmin = role === "platform_admin";
    const ownerAdminView = role === "owner" || role === "admin";
    const [ownerAdminAdvancedNav, setOwnerAdminAdvancedNav] = useState(
        () => readBrowserStorage(OWNER_ADMIN_ADVANCED_NAV_STORAGE_KEY) === "1"
    );
    const navItems = useMemo(
        () => {
            const allowedItems = NAV_ITEMS.filter((item) => {
                if (item.section === "settings") {
                    return (
                        canAccessConsole(role, "settings", item.action ?? "read")
                        || canAccessConsole(role, "provisioning", "read")
                    );
                }
                return canAccessConsole(role, item.section, item.action ?? "read");
            });

            if (!ownerAdminView || ownerAdminAdvancedNav) {
                return allowedItems;
            }

            return allowedItems.filter((item) => {
                if (OWNER_ADMIN_PRIMARY_NAV_TEST_IDS.has(item.testId)) {
                    return true;
                }
                return isNavItemCurrent(pathname, item.href);
            });
        },
        [ownerAdminAdvancedNav, ownerAdminView, pathname, role]
    );
    const { data: healthData, dataUpdatedAt: healthDataUpdatedAt, refetch: refetchHealth } = useQuery({
        queryKey: ["console-health-banner"],
        queryFn: async () => {
            const response = await opsApi.getHealth();
            return response.data;
        },
        enabled: hasSession && canReadOps,
        refetchInterval: 30000,
        staleTime: 10000,
    });
    const { data: incidentFeed, refetch: refetchIncidentFeed } = useQuery({
        queryKey: ["console-health-incident-feed", role],
        queryFn: async () => {
            if (isPlatformAdmin) {
                const response = await adminApi.listIncidents({ limit: 20 });
                return response.data;
            }
            if (ownerAdminView) {
                const response = await businessApi.getIncidents();
                return response.data;
            }
            return null;
        },
        enabled: hasSession && canReadOps && (isPlatformAdmin || ownerAdminView),
        refetchInterval: 30000,
        staleTime: 10000,
    });
    const topIncident = useMemo(() => pickTopIncident(incidentFeed ?? null), [incidentFeed]);
    const healthIncident = useMemo(
        () => deriveHealthIncident(healthData ?? null, healthDataUpdatedAt, { ownerAdminView, topIncident }),
        [healthData, healthDataUpdatedAt, ownerAdminView, topIncident],
    );
    const healthIncidentClass = healthIncident?.severity === "critical"
        ? "border-red-300/80 bg-red-50 text-red-900"
        : "border-amber-300/80 bg-amber-50 text-amber-900";
    const healthIncidentOpsHref = useMemo(() => incidentHref("/ops", topIncident), [topIncident]);
    const healthIncidentWorkspaceHref = useMemo(
        () => (canReadTenants ? incidentHref("/company-workspace", topIncident) : null),
        [canReadTenants, topIncident],
    );

    const [isSubmitting, setIsSubmitting] = useState(false);
    const [contextNotice, setContextNotice] = useState<string | null>(null);
    const [navTransitioning, setNavTransitioning] = useState(false);
    const navFallbackTimeoutRef = useRef<number | null>(null);
    const healthRefreshTimeoutRef = useRef<number | null>(null);
    const [manualHealthRefreshing, setManualHealthRefreshing] = useState(false);
    const [navCollapsed, setNavCollapsed] = useState(
        () => readBrowserStorage(NAV_COLLAPSED_STORAGE_KEY) === "1"
    );
    const [healthIncidentUiState, setHealthIncidentUiState] = useState<HealthIncidentUiState>(
        () => readHealthIncidentUiState()
    );
    const navToggleLabel = navCollapsed ? "Развернуть меню" : "Свернуть меню";
    const healthIncidentHiddenUntil = Number.isFinite(healthIncidentUiState.hiddenUntilTs)
        ? healthIncidentUiState.hiddenUntilTs
        : 0;

    const markContextAwareQueriesStale = async () => {
        await queryClient.cancelQueries({
            predicate: (query) => isContextAwareQueryKey(query.queryKey),
        });
        await queryClient.invalidateQueries({
            predicate: (query) => isContextAwareQueryKey(query.queryKey),
            refetchType: "none",
        });
    };
    const refetchActiveContextAwareQueries = () => {
        void queryClient.refetchQueries({
            predicate: (query) => isContextAwareQueryKey(query.queryKey),
            type: "active",
        });
    };
    const healthIncidentHidden = !!healthIncident && healthIncidentHiddenUntil > Date.now();
    const navigateToRoute = (href: string) => {
        if (typeof window === "undefined") {
            return;
        }
        const currentPathWithQuery = `${window.location.pathname}${window.location.search}`;
        if (href === currentPathWithQuery) {
            return;
        }
        const previousPathWithQuery = currentPathWithQuery;
        setNavTransitioning(true);
        router.push(href);
        // Guard against rare App Router no-op transitions: fall back to hard navigation.
        if (navFallbackTimeoutRef.current !== null) {
            window.clearTimeout(navFallbackTimeoutRef.current);
            navFallbackTimeoutRef.current = null;
        }
        navFallbackTimeoutRef.current = window.setTimeout(() => {
            navFallbackTimeoutRef.current = null;
            const currentAfterPush = `${window.location.pathname}${window.location.search}`;
            if (currentAfterPush === previousPathWithQuery && href.startsWith("/")) {
                window.location.assign(href);
            }
        }, 800);
    };

    const navigateFromNav = (event: MouseEvent<HTMLAnchorElement>, href: string) => {
        if (
            event.defaultPrevented
            || event.button !== 0
            || event.metaKey
            || event.ctrlKey
            || event.shiftKey
            || event.altKey
            || event.currentTarget.target === "_blank"
            || event.currentTarget.hasAttribute("download")
        ) {
            return;
        }
        event.preventDefault();
        navigateToRoute(href);
    };

    const refreshHealthBanner = () => {
        if (manualHealthRefreshing) {
            return;
        }
        setManualHealthRefreshing(true);
        if (healthRefreshTimeoutRef.current !== null) {
            window.clearTimeout(healthRefreshTimeoutRef.current);
            healthRefreshTimeoutRef.current = null;
        }
        healthRefreshTimeoutRef.current = window.setTimeout(() => {
            healthRefreshTimeoutRef.current = null;
            setManualHealthRefreshing(false);
        }, HEALTH_INCIDENT_REFRESH_TIMEOUT_MS);
        void Promise.all([
            refetchHealth(),
            (isPlatformAdmin || ownerAdminView) ? refetchIncidentFeed() : Promise.resolve(null),
        ]).finally(() => {
            if (healthRefreshTimeoutRef.current !== null) {
                window.clearTimeout(healthRefreshTimeoutRef.current);
                healthRefreshTimeoutRef.current = null;
            }
            setManualHealthRefreshing(false);
        });
    };

    useEffect(() => {
        if (!contextNotice) {
            return undefined;
        }
        const timeout = window.setTimeout(() => setContextNotice(null), 2500);
        return () => window.clearTimeout(timeout);
    }, [contextNotice]);

    useEffect(() => {
        setNavTransitioning(false);
        if (navFallbackTimeoutRef.current !== null) {
            window.clearTimeout(navFallbackTimeoutRef.current);
            navFallbackTimeoutRef.current = null;
        }
    }, [pathname]);

    useEffect(() => {
        return () => {
            if (healthRefreshTimeoutRef.current !== null) {
                window.clearTimeout(healthRefreshTimeoutRef.current);
                healthRefreshTimeoutRef.current = null;
            }
        };
    }, []);

    useEffect(() => {
        writeBrowserStorage(NAV_COLLAPSED_STORAGE_KEY, navCollapsed ? "1" : null);
    }, [navCollapsed]);

    useEffect(() => {
        if (!ownerAdminView) {
            writeBrowserStorage(OWNER_ADMIN_ADVANCED_NAV_STORAGE_KEY, null);
            return;
        }
        writeBrowserStorage(OWNER_ADMIN_ADVANCED_NAV_STORAGE_KEY, ownerAdminAdvancedNav ? "1" : null);
    }, [ownerAdminAdvancedNav, ownerAdminView]);

    useEffect(() => {
        if (healthIncidentUiState.hiddenUntilTs <= Date.now()) {
            writeBrowserStorage(HEALTH_INCIDENT_UI_STORAGE_KEY, null);
            return;
        }
        writeBrowserStorage(
            HEALTH_INCIDENT_UI_STORAGE_KEY,
            JSON.stringify({ hiddenUntilTs: healthIncidentUiState.hiddenUntilTs }),
        );
    }, [healthIncidentUiState.hiddenUntilTs]);

    const snoozeHealthIncident = () => {
        if (!healthIncident) {
            return;
        }
        setHealthIncidentUiState({ hiddenUntilTs: Date.now() + HEALTH_INCIDENT_HIDE_MS });
    };

    const companies = data?.companies ?? [];
    const companySelectionRequired = !!data?.company_selection_required;
    const selectionRequired = !!data?.selection_required;
    const branchSelectionRequired = !!data?.branch_selection_required;
    const showGate = companySelectionRequired || selectionRequired || branchSelectionRequired;
    const contextBusy = isSubmitting || (showGate && isFetching);

    const storedScope = readConsoleContextScopeFromStorage();
    const storedCompanyId = storedScope.companyId;
    const fallbackCompanyId = !companySelectionRequired ? (data?.client?.company_id ?? "") : "";
    const resolvedCompanyId = data?.selected_company_id ?? storedCompanyId ?? fallbackCompanyId;
    const companyId = companies.some((company) => company.id === resolvedCompanyId)
        ? resolvedCompanyId ?? ""
        : "";
    const visibleClients = companyId
        ? (data?.clients ?? []).filter((client) => client.company_id === companyId)
        : (data?.clients ?? []);

    const handleSelectCompany = async (companyId: string) => {
        if (!companyId) {
            return;
        }
        setIsSubmitting(true);
        try {
            const companyName = companies.find((company) => company.id === companyId)?.name;
            setConsoleCompanyContext(companyId);
            await refetch();
            await markContextAwareQueriesStale();
            refetchActiveContextAwareQueries();
            setContextNotice(`Контекст: компания ${formatContextLabel(companyName, companyId)}`);
        } catch {
            toast.error("Не удалось обновить контекст");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleSelectClient = async (clientId: string) => {
        if (!clientId) {
            return;
        }
        setIsSubmitting(true);
        try {
            const clientName = visibleClients.find((client) => client.id === clientId)?.name;
            const selectedClientCompanyId = visibleClients.find((client) => client.id === clientId)?.company_id;
            setConsoleClientContext(clientId, selectedClientCompanyId ?? companyId ?? null);
            await refetch();
            await markContextAwareQueriesStale();
            refetchActiveContextAwareQueries();
            setContextNotice(`Контекст: клиент ${formatContextLabel(clientName, clientId)}`);
        } catch {
            toast.error("Не удалось обновить контекст");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleSelectBranch = async (branchId: string) => {
        if (!branchId) {
            return;
        }
        setIsSubmitting(true);
        try {
            const branchName = (data?.branches ?? []).find((branch) => branch.id === branchId)?.name;
            setConsoleBranchContext(branchId);
            await refetch();
            await markContextAwareQueriesStale();
            refetchActiveContextAwareQueries();
            setContextNotice(`Контекст: филиал ${formatContextLabel(branchName, branchId)}`);
        } catch {
            toast.error("Не удалось обновить контекст");
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleContextClientChange = async (clientId: string) => {
        if (!clientId || clientId === readConsoleContextScopeFromStorage().clientId) {
            return;
        }
        await handleSelectClient(clientId);
    };

    const handleContextCompanyChange = async (companyId: string) => {
        if (!companyId || companyId === readConsoleContextScopeFromStorage().companyId) {
            return;
        }
        await handleSelectCompany(companyId);
    };

    const handleContextBranchChange = async (branchId: string | null) => {
        const nextBranchId = branchId ?? "";
        if (nextBranchId === readConsoleContextScopeFromStorage().branchId) {
            return;
        }
        setIsSubmitting(true);
        try {
            setConsoleBranchContext(nextBranchId);
            await refetch();
            await markContextAwareQueriesStale();
            refetchActiveContextAwareQueries();
            if (!nextBranchId) {
                setContextNotice("Контекст: все филиалы");
            } else {
                const nextBranchName = findBranchName(data?.branches, nextBranchId);
                setContextNotice(`Контекст: филиал ${formatContextLabel(nextBranchName, nextBranchId)}`);
            }
        } catch {
            toast.error("Не удалось обновить контекст");
        } finally {
            setIsSubmitting(false);
        }
    };

    useEffect(() => {
        if (!data) {
            return;
        }

        const stored = readConsoleContextScopeFromStorage();
        const nextCompanyId = data.company_selection_required
            ? ""
            : data.selected_company_id ?? data.client?.company_id ?? stored.companyId;
        const nextClientId = data.selection_required ? "" : data.client?.id ?? stored.clientId;
        const nextBranchId = data.branch_selection_required
            ? ""
            // Preserve stored branch when /me does not provide a concrete branch selection.
            // /me branch lists can be scope-limited, and dropping branch here causes silent scope drift.
            : data.selected_branch_id ?? stored.branchId;
        if (
            nextCompanyId !== stored.companyId
            || nextClientId !== stored.clientId
            || nextBranchId !== stored.branchId
        ) {
            writeConsoleContextScopeToStorage({
                companyId: nextCompanyId,
                clientId: nextClientId,
                branchId: nextBranchId,
            });
        }
    }, [data]);

    if (!hasSession && status !== "loading") {
        return <PublicLanding />;
    }

    return (
        <div className="min-h-screen bg-background">
            <div className="flex min-h-screen">
                <aside
                    className={`hidden ${navCollapsed ? "w-16" : "w-52"} flex-col border-r border-border/60 bg-card/40 px-2 py-2 transition-[width] duration-200 md:flex`}
                >
                    <div
                        className={`flex px-2 ${
                            navCollapsed ? "flex-col items-center gap-3" : "items-center justify-between"
                        }`}
                    >
                        {navCollapsed ? (
                            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-foreground text-xs font-semibold text-background">
                                T
                            </div>
                        ) : (
                            <Image
                                src="/brand/truffles-logo.png"
                                alt="Truffles"
                                width={120}
                                height={32}
                                className="h-6 w-auto"
                            />
                        )}
                        <button
                            type="button"
                            onClick={() => setNavCollapsed((prev) => !prev)}
                            className={`inline-flex items-center gap-2 rounded-full border border-border/60 text-xs font-semibold text-muted-foreground transition hover:bg-muted hover:text-foreground ${
                                navCollapsed ? "h-9 w-9 justify-center" : "px-3 py-2"
                            }`}
                            aria-label={navToggleLabel}
                            title={navToggleLabel}
                            data-testid="nav-toggle"
                        >
                            {navCollapsed ? (
                                <NavIcon className="h-4 w-4">
                                    <path d="M10 6l6 6-6 6" />
                                </NavIcon>
                            ) : (
                                <>
                                    <NavIcon className="h-4 w-4">
                                        <path d="M14 6l-6 6 6 6" />
                                    </NavIcon>
                                    <span>Свернуть</span>
                                </>
                            )}
                        </button>
                    </div>
                    {!navCollapsed && (
                        <div className="mt-1 px-2 text-[10px] uppercase tracking-[0.16em] leading-tight text-muted-foreground">
                            {ROLE_LABELS[role]}
                        </div>
                    )}
                    {ownerAdminView && !navCollapsed && (
                        <div className="mt-2 px-2">
                            <button
                                type="button"
                                onClick={() => setOwnerAdminAdvancedNav((prev) => !prev)}
                                className={`w-full rounded-lg border px-3 py-2 text-left text-xs font-semibold transition ${
                                    ownerAdminAdvancedNav
                                        ? "border-primary/40 bg-primary/5 text-primary"
                                        : "border-border/60 text-muted-foreground hover:bg-muted"
                                }`}
                                data-testid="nav-owner-admin-toggle"
                            >
                                {ownerAdminAdvancedNav ? "Скрыть расширенное меню" : "Показать расширенное меню"}
                            </button>
                            <p className="mt-2 text-[11px] text-muted-foreground">
                                {ownerAdminAdvancedNav
                                    ? "Видны технические и редкие разделы."
                                    : "Сейчас показаны только ключевые разделы для бизнеса."}
                            </p>
                        </div>
                    )}
                    <nav className={`mt-1 flex flex-col gap-1.5 text-sm font-medium ${navCollapsed ? "items-center" : ""}`}>
                        {navItems.map((item) => {
                            const isActive = isNavItemCurrent(pathname, item.href);
                            return (
                                <a
                                    key={item.href}
                                    href={item.href}
                                    onClick={(event) => navigateFromNav(event, item.href)}
                                    className={`flex items-center rounded-lg transition ${
                                        navCollapsed ? "justify-center px-2 py-2" : "gap-3 px-3 py-2"
                                    } ${isActive ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-muted"}`}
                                    data-testid={item.testId}
                                    title={navCollapsed ? item.label : undefined}
                                    aria-current={isActive ? "page" : undefined}
                                >
                                    <span
                                        className={`flex h-5 w-5 items-center justify-center ${
                                            isActive ? "text-primary-foreground" : "text-muted-foreground"
                                        }`}
                                    >
                                        {NAV_ICONS[item.section] ?? (
                                            <NavIcon>
                                                <circle cx="12" cy="12" r="4" />
                                            </NavIcon>
                                        )}
                                    </span>
                                    {navCollapsed ? <span className="sr-only">{item.label}</span> : item.label}
                                </a>
                            );
                        })}
                    </nav>
                </aside>
                <div className="flex flex-1 flex-col">
                    <header
                        className="sticky top-0 z-20 border-b border-border/60 bg-background/80 backdrop-blur"
                        data-testid="console-header"
                    >
                        <div className="flex flex-col gap-3 px-5 py-3 lg:flex-row lg:items-center lg:justify-between">
                            <div className="flex items-center gap-3 md:hidden">
                                <Image
                                    src="/brand/truffles-logo.png"
                                    alt="Truffles"
                                    width={120}
                                    height={32}
                                    className="h-6 w-auto"
                                />
                                <span className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
                                    Truffles Console
                                </span>
                            </div>
                            {data && (
                                <div className="w-full lg:w-auto lg:flex-1">
                                    <div className="rounded-lg border border-border/60 bg-muted/20 px-3 py-1.5 text-xs text-foreground/80 md:hidden">
                                        {isTenantsPage ? (
                                            <>
                                                Контекст управляется в блоке «Рабочий контур» на странице «Тенанты».
                                                <Link href="/tenants" className="ml-2 font-medium text-primary underline underline-offset-2">
                                                    открыть
                                                </Link>
                                            </>
                                        ) : (
                                            <>
                                                Контекст:{" "}
                                                <span className="font-semibold text-foreground">
                                                    {data.client?.company_name ?? "Компания"}
                                                </span>
                                                {" "}·{" "}
                                                <span className="font-semibold text-foreground">
                                                    {data.client?.name ?? "Клиент"}
                                                </span>
                                                {" "}·{" "}
                                                <span className="font-semibold text-foreground">
                                                    {findBranchName(data.branches, data.selected_branch_id, !data.branch_selection_required)}
                                                </span>
                                                <Link href="/company-workspace" className="ml-2 font-medium text-primary underline underline-offset-2">
                                                    изменить
                                                </Link>
                                                {role === "platform_admin" && (
                                                    <span
                                                        className="ml-2 inline-flex rounded-full border border-sky-300/80 bg-sky-50 px-2 py-0.5 text-[10px] text-sky-900"
                                                        data-testid="context-active-scope-hint-mobile"
                                                        title="Архив и деактивированные в Тенантах."
                                                        aria-label="Режим данных: Активные"
                                                    >
                                                        Режим данных: Активные
                                                    </span>
                                                )}
                                            </>
                                        )}
                                    </div>
                                    <div className="hidden md:block">
                                        {isTenantsPage ? (
                                            <div
                                                className="rounded-lg border border-border/60 bg-muted/20 px-3 py-2 text-xs text-foreground/80"
                                                data-testid="context-managed-in-tenants"
                                            >
                                                Контекст на странице «Тенанты» управляется в блоке «Рабочий контур», чтобы избежать конфликтов с фильтрами страницы.
                                            </div>
                                        ) : (
                                            <ContextBar
                                                me={data}
                                                companyId={companyId}
                                                clients={visibleClients}
                                                onSelectCompany={handleContextCompanyChange}
                                                onSelectClient={handleContextClientChange}
                                                onSelectBranch={handleContextBranchChange}
                                                showActiveScopeHint={role === "platform_admin"}
                                                isBusy={contextBusy}
                                            />
                                        )}
                                    </div>
                                    <ContextHealthStrip
                                        me={data}
                                        companyId={companyId}
                                        visibleClients={visibleClients}
                                        canReadOps={canReadOps}
                                        canReadTenants={canReadTenants}
                                        onOpenOps={() => navigateToRoute("/ops")}
                                        onOpenTenants={() => navigateToRoute("/tenants")}
                                    />
                                </div>
                            )}
                            <div className="flex items-center justify-between gap-4">
                                {navTransitioning && (
                                    <span
                                        className="rounded-full bg-sky-50 px-3 py-1 text-xs text-sky-700"
                                        data-testid="nav-transitioning"
                                    >
                                        Переход...
                                    </span>
                                )}
                                {contextBusy && (
                                    <span
                                        className="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground"
                                        data-testid="context-loading"
                                    >
                                        Обновление контекста...
                                    </span>
                                )}
                                {!contextBusy && contextNotice && (
                                    <span
                                        className="rounded-full bg-emerald-50 px-3 py-1 text-xs text-emerald-700"
                                        data-testid="context-notice"
                                    >
                                        {contextNotice}
                                    </span>
                                )}
                                <LoginButton />
                            </div>
                        </div>
                        {healthIncident && !healthIncidentHidden && (
                            <div
                                className={`mx-6 mb-4 flex flex-wrap items-start justify-between gap-3 rounded-lg border px-4 py-3 text-xs ${healthIncidentClass}`}
                                data-testid="global-health-incident-banner"
                            >
                                <div className="min-w-[280px] flex-1">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span
                                            className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                                healthIncident.severity === "critical"
                                                    ? "bg-red-200/80 text-red-900"
                                                    : "bg-amber-200/80 text-amber-900"
                                            }`}
                                            data-testid="global-health-incident-severity"
                                        >
                                            {healthIncident.severity === "critical" ? "P0" : "P1"}
                                        </span>
                                        <p className="text-sm font-semibold">{healthIncident.title}</p>
                                        <span className="rounded-full border border-current/30 px-2 py-0.5 font-mono text-[10px]">
                                            {healthIncident.reasonCode}
                                        </span>
                                    </div>
                                    <p className="mt-1 font-mono" data-testid="global-health-incident-summary">
                                        {healthIncident.summary}
                                    </p>
                                    <p className="mt-1 text-[11px] text-current/80" data-testid="global-health-incident-updated">
                                        {healthIncident.updatedAtLabel}
                                    </p>
                                    <ul className="mt-2 list-disc space-y-1 pl-4 text-[11px]" data-testid="global-health-incident-reasons">
                                        {healthIncident.reasons.map((reason) => (
                                            <li key={reason}>{reason}</li>
                                        ))}
                                    </ul>
                                    <ol className="mt-2 space-y-1 text-[11px]" data-testid="global-health-incident-runbook">
                                        {healthIncident.runbook.map((step, index) => (
                                            <li key={step}>{index + 1}. {step}</li>
                                        ))}
                                    </ol>
                                </div>
                                <div className="flex flex-wrap items-center gap-2">
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={snoozeHealthIncident}
                                        data-testid="global-health-incident-snooze"
                                    >
                                        Скрыть на 30м
                                    </button>
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={refreshHealthBanner}
                                        disabled={manualHealthRefreshing}
                                        data-testid="global-health-incident-refresh"
                                    >
                                        {manualHealthRefreshing ? "Обновляю..." : "Обновить health"}
                                    </button>
                                    <button
                                        type="button"
                                        className="btn-ghost"
                                        onClick={() => navigateToRoute(healthIncidentOpsHref)}
                                        data-testid="global-health-incident-open-ops"
                                    >
                                        Открыть OPS
                                    </button>
                                    {healthIncidentWorkspaceHref && (
                                        <button
                                            type="button"
                                            className="btn-ghost"
                                            onClick={() => navigateToRoute(healthIncidentWorkspaceHref)}
                                            data-testid="global-health-incident-open-workspace"
                                        >
                                            Открыть Workspace
                                        </button>
                                    )}
                                </div>
                            </div>
                        )}
                        <nav className="flex gap-2 overflow-x-auto px-4 pb-3 text-xs font-medium md:hidden">
                            {navItems.map((item) => {
                                const isActive = item.href === "/"
                                    ? pathname === "/"
                                    : pathname.startsWith(item.href);
                                return (
                                    <a
                                        key={item.href}
                                        href={item.href}
                                        onClick={(event) => navigateFromNav(event, item.href)}
                                        className={`shrink-0 rounded-full px-4 py-2 transition ${
                                            isActive ? "bg-primary text-primary-foreground" : "bg-muted"
                                        }`}
                                        data-testid={`mobile-${item.testId}`}
                                    >
                                        {item.label}
                                    </a>
                                );
                            })}
                        </nav>
                    </header>

                    <main className="flex-1 min-h-0 px-6 py-6">
                        <div className={`mx-auto w-full ${contentWidthClass} ${contentFrameClass}`}>
                            {status === "loading" && (
                                <div className="card-surface p-8">
                                    <p className="text-sm text-muted-foreground">Загрузка профиля...</p>
                                </div>
                            )}
                            {error && (
                                <div className="card-surface p-8">
                                    <p className="text-sm text-destructive">
                                        Не удалось загрузить данные профиля.
                                    </p>
                                    <button
                                        onClick={() => refetch()}
                                        className="btn-ghost mt-4"
                                        data-testid="me-retry"
                                    >
                                        Повторить
                                    </button>
                                </div>
                            )}
                            {!isLoading && !error && data && showGate && (
                                <div
                                    className="fixed inset-0 z-[10000] flex items-center justify-center bg-background/80 p-6 backdrop-blur-sm"
                                    data-testid="selection-gate-overlay"
                                >
                                    <div className="pointer-events-auto max-w-xl w-full">
                                        <SelectionGate
                                            me={data}
                                            clients={visibleClients}
                                            onConfirmCompany={handleSelectCompany}
                                            onConfirmClient={handleSelectClient}
                                            onConfirmBranch={handleSelectBranch}
                                            isSubmitting={isSubmitting || isFetching}
                                        />
                                    </div>
                                </div>
                            )}
                            {!isLoading && !error && data && !showGate && (
                                <div className={isInboxPage ? "flex h-full min-h-0 flex-col" : undefined}>
                                    {children}
                                </div>
                            )}
                        </div>
                    </main>
                </div>
            </div>
        </div>
    );
}
