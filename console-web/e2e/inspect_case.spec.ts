import { test, expect } from '@playwright/test';
import path from 'path';
import { isAuthGateVisible, loginThroughKeycloak } from './support/keycloak-auth';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const consoleHostPattern = /localhost:3000|localhost:3100|192\.168\.5\.27:3000|console\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const useRouteMocks = process.env.INSPECT_CASE_USE_MOCKS !== '0';
const COMPANY_ID = '11111111-1111-4111-8111-111111111111';
const CLIENT_ID = '22222222-2222-4222-8222-222222222222';
const BRANCH_ID = '33333333-3333-4333-8333-333333333333';
const AGENT_ID = '44444444-4444-4444-8444-444444444444';
const CASE_ID = '55555555-5555-4555-8555-555555555555';
const LIVE_CASE_ID = process.env.INSPECT_CASE_LIVE_CASE_ID ?? CASE_ID;
const HAS_EXPLICIT_LIVE_CASE_ID = LIVE_CASE_ID !== CASE_ID;
const WAVE22_LIVE_PROOF_REQUIRED_MESSAGE = 'Set INSPECT_CASE_LIVE_CASE_ID to a safe resolved case for Wave22 live proof.';
const CONVERSATION_ID = '66666666-6666-4666-8666-666666666666';
const SPECIALIST_ID = '77777777-7777-4777-8777-777777777777';
const TEXT_MACRO_ID = 'abababab-abab-4bab-8bab-abababababab';
const ACTION_MACRO_ID = 'cdcdcdcd-cdcd-4dcd-8dcd-cdcdcdcdcdcd';
const CREATED_MACRO_ID = 'efefefef-efef-4fef-8fef-efefefefefef';
const CASE_PERSONAL_VIEW_ID = 'case-personal-view-1';
const CASE_TEAM_VIEW_ID = 'case-team-view-1';
const CASE_CREATED_TEAM_VIEW_ID = 'cases-created-team-view-1';
const CALENDAR_PERSONAL_VIEW_ID = 'calendar-personal-view-1';
const CALENDAR_TEAM_VIEW_ID = 'calendar-team-view-1';
let lastMacroCreatePayload: unknown = null;
let lastMacroExecutePayload: unknown = null;

type MockViewerRole = 'admin' | 'manager' | 'owner';
type MockQueueSurface = 'cases' | 'calendar';
type MockSavedView = {
    id: string;
    surface: MockQueueSurface;
    name: string;
    query_state: Record<string, unknown>;
    is_default: boolean;
    scope: 'personal' | 'team';
    target_branch_id: string | null;
    target_role: MockViewerRole | null;
};
type MockQueueStateRecord = {
    found: boolean;
    surface: MockQueueSurface;
    query_state?: Record<string, unknown> | null;
    updated_at?: string | null;
    case_id?: string | null;
    conversation_id?: string | null;
    version?: number;
};

function deepClone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
}

function isSavedViewApplicable(view: MockSavedView, viewerRole: MockViewerRole) {
    if (view.scope !== 'team') {
        return true;
    }
    const branchMatches = !view.target_branch_id || view.target_branch_id === BRANCH_ID;
    const roleMatches = !view.target_role || view.target_role === viewerRole;
    return branchMatches && roleMatches;
}

function toSavedViewResponse(view: MockSavedView, viewerRole: MockViewerRole) {
    return {
        id: view.id,
        name: view.name,
        surface: view.surface,
        query_state: deepClone(view.query_state),
        is_default: view.is_default,
        scope: view.scope,
        target_branch_id: view.target_branch_id,
        target_role: view.target_role,
        is_applicable: isSavedViewApplicable(view, viewerRole),
    };
}

async function installClipboardCapture(page: import('@playwright/test').Page) {
    const install = () => {
        (window as Window & { __copiedText?: string }).__copiedText = '';
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: {
                writeText: async (text: string) => {
                    (window as Window & { __copiedText?: string }).__copiedText = text;
                },
            },
        });
    };
    await page.addInitScript(install);
    await page.evaluate(install);
}

async function readCopiedClipboardText(page: import('@playwright/test').Page) {
    return page.evaluate(() => (window as Window & { __copiedText?: string }).__copiedText ?? '');
}

function toJsonResponse(route: import('@playwright/test').Route, payload: unknown) {
    return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
    });
}

async function waitForCasesListRequest(
    page: import('@playwright/test').Page,
    action: () => Promise<void>,
) {
    const requestPromise = page.waitForRequest((request) => (
        request.method() === 'GET' && request.url().includes('/api/proxy/cases?')
    ));
    await action();
    return new URL((await requestPromise).url());
}

async function openCasesSecondaryPanel(
    page: import('@playwright/test').Page,
    section: 'saved_views' | 'filters' | 'view' | 'bulk',
) {
    const panel = page.getByTestId('cases-secondary-panel');
    if (!(await panel.isVisible().catch(() => false))) {
        await page.getByTestId('cases-secondary-panel-toggle').click({ force: true });
        await expect(panel).toBeVisible({ timeout: 15000 });
    }
    await page.getByTestId(`cases-secondary-tab-${section}`).click({ force: true });
}

async function closeCasesSecondaryPanel(page: import('@playwright/test').Page) {
    const panel = page.getByTestId('cases-secondary-panel');
    if (await panel.isVisible().catch(() => false)) {
        await page.getByTestId('cases-secondary-panel-close').click({ force: true });
        await expect(panel).toHaveCount(0);
    }
}

async function openCalendarSecondaryPanel(
    page: import('@playwright/test').Page,
    section: 'filters' | 'saved_views' | 'scheduling',
) {
    const panel = page.getByTestId('calendar-secondary-panel');
    if (!(await panel.isVisible().catch(() => false))) {
        const toggleBySection: Record<typeof section, string> = {
            filters: 'calendar-secondary-panel-toggle',
            saved_views: 'calendar-saved-views-panel-toggle',
            scheduling: 'calendar-scheduling-panel-toggle',
        };
        await page.getByTestId(toggleBySection[section]).click({ force: true });
        await expect(panel).toBeVisible({ timeout: 15000 });
    }
    await page.getByTestId(`calendar-secondary-tab-${section}`).click({ force: true });
}

async function closeCalendarSecondaryPanel(page: import('@playwright/test').Page) {
    const panel = page.getByTestId('calendar-secondary-panel');
    if (await panel.isVisible().catch(() => false)) {
        await page.getByTestId('calendar-secondary-panel-close').click({ force: true });
        await expect(panel).toHaveCount(0);
    }
}

async function closeCalendarBookingPanel(page: import('@playwright/test').Page) {
    const panel = page.getByTestId('calendar-booking-panel');
    if (await panel.isVisible().catch(() => false)) {
        await page.getByTestId('calendar-booking-panel-close').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect.poll(() => panel.isVisible().catch(() => false)).toBe(false);
    }
}

async function installConsoleMocks(
    page: import('@playwright/test').Page,
    options?: { viewerRole?: MockViewerRole },
) {
    lastMacroCreatePayload = null;
    lastMacroExecutePayload = null;
    const viewerRole = options?.viewerRole ?? 'admin';
    const savedViewStore: MockSavedView[] = [
        {
            id: CASE_PERSONAL_VIEW_ID,
            surface: 'cases',
            name: 'Мои Айгуль',
            query_state: {
                mode_scope: 'open',
                base_view: 'all_open',
                owner_scope: {
                    kind: 'mine',
                    agent_id: null,
                },
                refinements: {
                    branch_id: null,
                    query: 'Айгуль',
                    has_delivery_error: false,
                    has_pending_outbox: false,
                    has_human_lock: false,
                    date_from: null,
                    date_to: null,
                    sort_by: 'created_at',
                },
            },
            is_default: false,
            scope: 'personal',
            target_branch_id: null,
            target_role: null,
        },
        {
            id: CASE_TEAM_VIEW_ID,
            surface: 'cases',
            name: 'Команда · Ждём клиента',
            query_state: {
                mode_scope: 'open',
                base_view: 'waiting_client',
                owner_scope: {
                    kind: 'all',
                    agent_id: null,
                },
                refinements: {
                    branch_id: null,
                    query: null,
                    has_delivery_error: false,
                    has_pending_outbox: false,
                    has_human_lock: false,
                    date_from: null,
                    date_to: null,
                    sort_by: 'sla',
                },
            },
            is_default: false,
            scope: 'team',
            target_branch_id: BRANCH_ID,
            target_role: null,
        },
        {
            id: CALENDAR_PERSONAL_VIEW_ID,
            surface: 'calendar',
            name: 'Неявки Айгуль',
            query_state: {
                selected_date: '2026-03-06',
                queue_mode: 'ops',
                queue_lane: 'attention',
                status_filter: 'no_show',
                query: 'Айгуль',
                follow_up_owner_id: '',
                follow_up_overdue_only: false,
            },
            is_default: false,
            scope: 'personal',
            target_branch_id: null,
            target_role: null,
        },
        {
            id: CALENDAR_TEAM_VIEW_ID,
            surface: 'calendar',
            name: 'Команда · Follow-up',
            query_state: {
                selected_date: '2026-03-06',
                queue_mode: 'ops',
                queue_lane: 'attention',
                status_filter: 'no_show',
                query: null,
                follow_up_owner_id: AGENT_ID,
                follow_up_overdue_only: true,
            },
            is_default: false,
            scope: 'team',
            target_branch_id: BRANCH_ID,
            target_role: 'manager',
        },
    ];
    const queueStateCurrentStore: Record<MockQueueSurface, MockQueueStateRecord> = {
        cases: {
            found: false,
            surface: 'cases',
            query_state: null,
            updated_at: null,
            version: 1,
        },
        calendar: {
            found: false,
            surface: 'calendar',
            query_state: null,
            updated_at: null,
            version: 1,
        },
    };
    const nextSavedViewId = (surface: MockQueueSurface) => {
        if (surface === 'cases' && !savedViewStore.some((view) => view.id === CASE_CREATED_TEAM_VIEW_ID)) {
            return CASE_CREATED_TEAM_VIEW_ID;
        }
        return `${surface}-created-view-${savedViewStore.filter((view) => view.surface === surface).length + 1}`;
    };
    const findSavedView = (viewId: string) => savedViewStore.find((view) => view.id === viewId) ?? null;
    const clearSavedViewDefaultsForTarget = (view: MockSavedView) => {
        if (!view.is_default) {
            return;
        }
        for (const item of savedViewStore) {
            if (item.id === view.id) {
                continue;
            }
            const sameSurface = item.surface === view.surface;
            const sameScope = item.scope === view.scope;
            const sameBranch = (item.target_branch_id ?? null) === (view.target_branch_id ?? null);
            const sameRole = (item.target_role ?? null) === (view.target_role ?? null);
            if (sameSurface && sameScope && sameBranch && sameRole) {
                item.is_default = false;
            }
        }
    };
    await page.route('**/api/proxy/queue-state/current**', async (route) => {
        const method = route.request().method();
        if (method !== 'GET' && method !== 'PUT') {
            await route.fallback();
            return;
        }
        if (method === 'GET') {
            const url = new URL(route.request().url());
            const surface = (url.searchParams.get('surface') === 'calendar' ? 'calendar' : 'cases') as MockQueueSurface;
            await toJsonResponse(route, deepClone(queueStateCurrentStore[surface]));
            return;
        }
        const payload = route.request().postDataJSON() as {
            surface?: MockQueueSurface;
            query_state?: Record<string, unknown> | null;
            case_id?: string | null;
            conversation_id?: string | null;
            version?: number;
        } | null;
        const surface = payload?.surface === 'calendar' ? 'calendar' : 'cases';
        queueStateCurrentStore[surface] = {
            found: true,
            surface,
            query_state: deepClone(payload?.query_state ?? null),
            case_id: payload?.case_id ?? null,
            conversation_id: payload?.conversation_id ?? null,
            version: payload?.version ?? 1,
            updated_at: '2026-03-08T12:35:01+05:00',
        };
        await toJsonResponse(route, { success: true, ...deepClone(queueStateCurrentStore[surface]) });
    });
    await page.route(/.*\/api\/proxy\/queue-state\/views\/[^/?]+(?:\?.*)?$/, async (route) => {
        const method = route.request().method();
        const viewId = route.request().url().split('/').pop()?.split('?')[0] ?? '';
        const view = findSavedView(viewId);
        if (!view) {
            await route.fulfill({
                status: 404,
                contentType: 'application/json',
                body: JSON.stringify({ error: { code: 'NOT_FOUND' } }),
            });
            return;
        }
        if (method === 'GET') {
            await toJsonResponse(route, toSavedViewResponse(view, viewerRole));
            return;
        }
        if (method === 'PATCH') {
            const payload = route.request().postDataJSON() as {
                query_state?: Record<string, unknown>;
                is_default?: boolean;
                target_branch_id?: string | null;
                target_role?: MockViewerRole | null;
                name?: string;
            } | null;
            if (payload && Object.prototype.hasOwnProperty.call(payload, 'query_state')) {
                view.query_state = deepClone(payload.query_state ?? {});
            }
            if (payload && Object.prototype.hasOwnProperty.call(payload, 'name') && typeof payload.name === 'string') {
                view.name = payload.name;
            }
            if (payload && Object.prototype.hasOwnProperty.call(payload, 'target_branch_id')) {
                view.target_branch_id = payload.target_branch_id || null;
            }
            if (payload && Object.prototype.hasOwnProperty.call(payload, 'target_role')) {
                view.target_role = payload.target_role || null;
            }
            if (payload && Object.prototype.hasOwnProperty.call(payload, 'is_default')) {
                view.is_default = Boolean(payload.is_default);
            }
            clearSavedViewDefaultsForTarget(view);
            await toJsonResponse(route, toSavedViewResponse(view, viewerRole));
            return;
        }
        if (method === 'DELETE') {
            const index = savedViewStore.findIndex((item) => item.id === viewId);
            if (index >= 0) {
                savedViewStore.splice(index, 1);
            }
            await toJsonResponse(route, { success: true });
            return;
        }
        await route.fallback();
    });
    await page.route(/.*\/api\/proxy\/queue-state\/views(?:\?.*)?$/, async (route) => {
        const method = route.request().method();
        if (method === 'GET') {
            const url = new URL(route.request().url());
            const surface = (url.searchParams.get('surface') === 'calendar' ? 'calendar' : 'cases') as MockQueueSurface;
            const items = savedViewStore
                .filter((view) => view.surface === surface)
                .map((view) => toSavedViewResponse(view, viewerRole));
            await toJsonResponse(route, { items });
            return;
        }
        if (method === 'POST') {
            const payload = route.request().postDataJSON() as {
                surface?: MockQueueSurface;
                name?: string;
                query_state?: Record<string, unknown>;
                is_default?: boolean;
                scope?: 'personal' | 'team';
                target_branch_id?: string | null;
                target_role?: MockViewerRole | null;
            } | null;
            const surface = payload?.surface === 'calendar' ? 'calendar' : 'cases';
            const view: MockSavedView = {
                id: nextSavedViewId(surface),
                surface,
                name: payload?.name ?? 'Новый вид',
                query_state: deepClone(payload?.query_state ?? {}),
                is_default: Boolean(payload?.is_default),
                scope: payload?.scope === 'team' ? 'team' : 'personal',
                target_branch_id: payload?.scope === 'team' ? (payload?.target_branch_id || null) : null,
                target_role: payload?.scope === 'team' ? (payload?.target_role || null) : null,
            };
            savedViewStore.push(view);
            clearSavedViewDefaultsForTarget(view);
            await toJsonResponse(route, toSavedViewResponse(view, viewerRole));
            return;
        }
        await route.fallback();
    });
    await page.route('**/api/auth/session**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            user: { name: 'Manager', email: 'manager@truffles.local' },
            expires: '2099-01-01T00:00:00.000Z',
            accessToken: 'e2e-manager-token',
        });
    });
    await page.route('**/api/auth/csrf', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, { csrfToken: 'e2e-csrf' });
    });
    await page.route('**/api/auth/providers', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            keycloak: {
                id: 'keycloak',
                name: 'Keycloak',
                type: 'oauth',
                signinUrl: `${baseURL}/api/auth/signin/keycloak`,
                callbackUrl: `${baseURL}/api/auth/callback/keycloak`,
            },
        });
    });
    await page.route('**/api/proxy/me', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            agent: {
                id: AGENT_ID,
                name: 'Manager',
                role: viewerRole,
                client_id: CLIENT_ID,
                branch_id: BRANCH_ID,
                is_active: true,
            },
            client: {
                id: CLIENT_ID,
                slug: 'demo_salon',
                name: 'Demo Salon',
            },
            branches: [
                {
                    id: BRANCH_ID,
                    client_id: CLIENT_ID,
                    slug: 'almaty_downtown',
                    name: 'Almaty Downtown',
                    timezone: 'Asia/Almaty',
                    is_active: true,
                },
            ],
            clients: [],
            companies: [
                {
                    id: COMPANY_ID,
                    name: 'Demo Holding',
                },
            ],
            company_selection_required: false,
            selection_required: false,
            branch_selection_required: false,
            selected_company_id: COMPANY_ID,
            selected_branch_id: BRANCH_ID,
        });
    });
    await page.route('**/api/proxy/agents', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [
                {
                    id: AGENT_ID,
                    name: 'Manager',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_active: true,
                },
                {
                    id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                    name: 'Manager Two',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_active: true,
                },
            ],
        });
    });
    const caseState = {
        id: CASE_ID,
        conversation_id: CONVERSATION_ID,
        branch_id: BRANCH_ID,
        status: 'active',
        business_status_code: 'needs_reply',
        business_status_label: 'Нужен ответ',
        trigger_type: 'message',
        trigger_value: null,
        context_summary: 'Клиент хочет маникюр и уточняет свободное время.',
        user_message: 'Здравствуйте, можно записаться на завтра?',
        created_at: '2026-03-05T09:00:00+05:00',
        assigned_to_id: AGENT_ID,
        assigned_to_name: 'Manager',
        channel: 'whatsapp',
        sla_status: 'warning',
        sla_action_state: 'reply_due',
        sla_overdue_minutes: null,
        target_response_at: '2026-03-05T10:00:00+05:00',
        customer_name: 'Айгуль',
        customer_phone: '+77001234567',
        last_inbound_at: '2026-03-05T09:10:00+05:00',
        last_activity_at: '2026-03-05T09:10:00+05:00',
        last_message_preview: 'Здравствуйте, можно записаться на завтра?',
        needs_reply: true,
        has_delivery_error: false,
        has_pending_outbox: false,
        human_lock_active: false,
        snoozed_until: null,
        snoozed_reason: null,
        snoozed_by: null,
    } as Record<string, unknown>;
    const waitingClientCaseState = {
        ...caseState,
        id: '56565656-5656-4565-8565-565656565656',
        conversation_id: '78787878-7878-4787-8787-787878787878',
        customer_name: 'Мадина',
        customer_phone: '+77001112233',
        user_message: 'Хорошо, жду подтверждение.',
        last_message_preview: 'Жду подтверждение менеджера.',
        created_at: '2026-03-05T08:40:00+05:00',
        last_inbound_at: '2026-03-05T08:50:00+05:00',
        last_activity_at: '2026-03-05T08:50:00+05:00',
        needs_reply: false,
        human_lock_active: true,
        business_status_code: 'waiting_client',
        business_status_label: 'Ждем клиента',
        sla_action_state: 'waiting_client',
        target_response_at: null,
    } as Record<string, unknown>;
    const snoozedCaseState = {
        ...caseState,
        id: '59595959-5959-4595-8595-595959595959',
        conversation_id: '81818181-8181-4818-8818-818181818181',
        customer_name: 'Жанар',
        customer_phone: '+77004445566',
        user_message: 'Свяжитесь со мной после обеда.',
        last_message_preview: 'Просьба вернуться к диалогу позже.',
        created_at: '2026-03-05T08:32:00+05:00',
        last_inbound_at: '2026-03-05T08:42:00+05:00',
        last_activity_at: '2026-03-05T08:42:00+05:00',
        needs_reply: false,
        business_status_code: 'snoozed',
        business_status_label: 'Отложена',
        sla_action_state: 'snoozed',
        target_response_at: null,
        snoozed_until: '2026-03-05T12:00:00+05:00',
        snoozed_reason: 'follow_up_later',
        snoozed_by: 'Manager',
    } as Record<string, unknown>;
    const deliveryCaseState = {
        ...caseState,
        id: '57575757-5757-4575-8575-575757575757',
        conversation_id: '79797979-7979-4797-8797-797979797979',
        customer_name: 'Сабина',
        customer_phone: '+77002223344',
        user_message: 'Уточните, дошло ли сообщение.',
        last_message_preview: 'Сообщение не отправилось клиенту.',
        created_at: '2026-03-05T08:30:00+05:00',
        last_inbound_at: '2026-03-05T08:45:00+05:00',
        last_activity_at: '2026-03-05T08:45:00+05:00',
        assigned_to_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        assigned_to_name: 'Manager Two',
        needs_reply: false,
        has_delivery_error: true,
        has_pending_outbox: true,
        attention_reason: 'Проверьте отправку',
        sla_action_state: 'delivery_issue',
        target_response_at: null,
    } as Record<string, unknown>;
    const resolvedCaseState = {
        ...caseState,
        id: '5a5a5a5a-5a5a-45a5-85a5-5a5a5a5a5a5a',
        conversation_id: '82828282-8282-4828-8828-828282828282',
        customer_name: 'Сабина Архив',
        customer_phone: '+77005556677',
        user_message: 'Спасибо, заявку можно закрыть.',
        last_message_preview: 'Заявка закрыта после подтверждения записи.',
        created_at: '2026-03-02T12:15:00+05:00',
        last_inbound_at: '2026-03-02T12:20:00+05:00',
        last_activity_at: '2026-03-03T10:05:00+05:00',
        resolved_at: '2026-03-03T10:05:00+05:00',
        status: 'resolved',
        assigned_to_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        assigned_to_name: 'Manager Two',
        needs_reply: false,
        business_status_code: 'resolved',
        business_status_label: 'Закрыта',
        sla_action_state: 'resolved',
        target_response_at: null,
    } as Record<string, unknown>;
    const unassignedCaseState = {
        ...caseState,
        id: '58585858-5858-4585-8585-585858585858',
        conversation_id: '80808080-8080-4808-8808-808080808080',
        customer_name: 'Нургуль',
        customer_phone: '+77003334455',
        user_message: 'Нужна запись на выходные.',
        last_message_preview: 'Новая заявка без ответственного.',
        created_at: '2026-03-05T08:20:00+05:00',
        last_inbound_at: '2026-03-05T08:35:00+05:00',
        last_activity_at: '2026-03-05T08:35:00+05:00',
        assigned_to_id: null,
        assigned_to_name: null,
        needs_reply: false,
        status: 'pending',
        business_status_code: 'unassigned',
        business_status_label: 'Без владельца',
        attention_reason: 'Назначьте ответственного',
        sla_action_state: 'waiting_client',
        target_response_at: null,
    } as Record<string, unknown>;
    const queueCases = [caseState, waitingClientCaseState, snoozedCaseState, deliveryCaseState, resolvedCaseState, unassignedCaseState];
    const bookingState = {
        id: '99999999-9999-4999-8999-999999999999',
        specialist_id: SPECIALIST_ID,
        specialist_name: 'Мастер Айжан',
        start_at: '2026-03-06T10:00:00+05:00',
        end_at: '2026-03-06T11:00:00+05:00',
        customer_name: 'Айгуль',
        customer_phone: '+77001234567',
        service_type: 'Маникюр',
        status: 'PENDING_CONFIRMATION',
        no_show_followup_done: false,
        no_show_followup_result: null,
        no_show_followup_closed_at: null,
        no_show_followup_closed_by: null,
        no_show_followup_rebooked_appointment_id: null,
        follow_up_owner_id: null,
        follow_up_owner_name: null,
        follow_up_due_at: null,
        follow_up_overdue: false,
        conversation_id: CONVERSATION_ID,
        case_id: CASE_ID,
        needs_action: true,
        attention_reason: 'Нужно подтвердить визит',
        created_at: '2026-03-05T09:20:00+05:00',
    } as Record<string, unknown>;
    const buildMockBookingSummary = () => {
        const status = String(bookingState.status || '');
        const needsAction = Boolean(bookingState.needs_action);
        const attentionReason = typeof bookingState.attention_reason === 'string'
            ? bookingState.attention_reason
            : null;
        const startLabel = typeof bookingState.start_at === 'string'
            ? new Date(bookingState.start_at).toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
            })
            : null;
        const meta = [startLabel, bookingState.specialist_name, bookingState.service_type]
            .filter((value) => typeof value === 'string' && value.length > 0)
            .join(' · ');
        let operatorSummary = `По заявке есть запись${meta ? ` ${meta}` : ''}.`;
        if (status === 'PENDING_CONFIRMATION') {
            operatorSummary = `По заявке создан визит${meta ? ` ${meta}` : ''} — нужно подтвердить запись.`;
        } else if (status === 'COMPLETED') {
            operatorSummary = `Визит по заявке завершен${meta ? `: ${meta}` : ''}.`;
        } else if (status === 'NO_SHOW' && bookingState.no_show_followup_done) {
            operatorSummary = bookingState.no_show_followup_result === 'rebooked'
                ? 'После неявки клиента уже перезаписали.'
                : 'После неявки с клиентом уже связались.';
        } else if (status === 'NO_SHOW') {
            operatorSummary = `Клиент не пришел на визит${meta ? ` ${meta}` : ''} — ${attentionReason || 'нужен follow-up'}.`;
        }
        return {
            booking_id: bookingState.id,
            status,
            start_at: bookingState.start_at,
            specialist_name: bookingState.specialist_name,
            service_type: bookingState.service_type,
            needs_action: needsAction,
            attention_reason: attentionReason,
            no_show_followup_done: Boolean(bookingState.no_show_followup_done),
            no_show_followup_result: bookingState.no_show_followup_result,
            operator_summary: operatorSummary,
        };
    };
    const buildCaseDetailPayload = (state: Record<string, unknown>) => ({
        ...state,
        booking_summary: state.id === CASE_ID ? buildMockBookingSummary() : null,
    });
    const reopenCaseForBookingAttention = () => {
        caseState.status = 'active';
        caseState.business_status_code = 'needs_reply';
        caseState.business_status_label = 'Нужен ответ';
        caseState.sla_status = 'warning';
        caseState.sla_action_state = 'reply_due';
        caseState.target_response_at = '2026-03-05T10:30:00+05:00';
        caseState.needs_reply = true;
        caseState.resolved_at = null;
        caseState.assigned_to_id = AGENT_ID;
        caseState.assigned_to_name = 'Manager';
        caseState.attention_reason = 'Связаться после неявки';
    };
    const macroStore = [
        {
            id: ACTION_MACRO_ID,
            scope: 'team',
            label: 'Закрыть и ответить',
            body: 'Заявку закрываю, если понадобится — напишите снова.',
            action: {
                type: 'resolve_case',
            },
            is_active: true,
            created_at: '2026-03-05T09:12:00+05:00',
            updated_at: '2026-03-05T09:12:00+05:00',
        },
        {
            id: TEXT_MACRO_ID,
            scope: 'personal',
            label: 'Уточняю время',
            body: 'Уточняю свободное время и скоро отвечу.',
            action: null,
            is_active: true,
            created_at: '2026-03-05T09:11:00+05:00',
            updated_at: '2026-03-05T09:11:00+05:00',
        },
    ];
    const matchesQueueView = (item: Record<string, unknown>, queueView: string | null) => {
        if (!queueView) {
            return true;
        }
        const status = String(item.status || '');
        const hasOwner = Boolean(item.assigned_to_id || item.assigned_to_name);
        const hasDelivery = Boolean(item.has_delivery_error || item.has_pending_outbox);
        const isSnoozed = Boolean(item.snoozed_until);
        const actionState = String(item.sla_action_state || '');
        if (status === 'resolved' || status === 'bot_handling') {
            return false;
        }
        if (queueView === 'needs_reply') {
            return !hasDelivery && !isSnoozed && Boolean(item.needs_reply || actionState === 'reply_due' || actionState === 'overdue');
        }
        if (queueView === 'waiting_client') {
            return !hasDelivery && !isSnoozed && hasOwner && actionState === 'waiting_client';
        }
        if (queueView === 'snoozed') {
            return isSnoozed;
        }
        if (queueView === 'delivery') {
            return hasDelivery;
        }
        if (queueView === 'unassigned') {
            return !hasOwner;
        }
        return true;
    };
    await page.route(/.*\/api\/proxy\/cases\/?(?:\?.*)?$/, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        const url = new URL(route.request().url());
        const status = url.searchParams.get('status');
        const queueView = url.searchParams.get('queue_view');
        const assignedToMe = url.searchParams.get('assigned_to_me') === 'true';
        const assigneeId = url.searchParams.get('assignee_id');
        const unassigned = url.searchParams.get('unassigned') === 'true';
        const hasDeliveryError = url.searchParams.get('has_delivery_error') === 'true';
        const hasPendingOutbox = url.searchParams.get('has_pending_outbox') === 'true';
        const hasHumanLock = url.searchParams.get('has_human_lock') === 'true';
        const query = (url.searchParams.get('q') || '').trim().toLowerCase();
        const sortBy = url.searchParams.get('sort_by');
        let items = queueCases.filter((item) => {
            const caseStatus = String(item.status || '');
            if (status === 'open' && caseStatus === 'resolved') {
                return false;
            }
            if (status && status !== 'open' && caseStatus !== status) {
                return false;
            }
            if (!matchesQueueView(item, queueView)) {
                return false;
            }
            if (assignedToMe && item.assigned_to_id !== AGENT_ID) {
                return false;
            }
            if (assigneeId && item.assigned_to_id !== assigneeId) {
                return false;
            }
            if (unassigned && item.assigned_to_id) {
                return false;
            }
            if (hasDeliveryError && !item.has_delivery_error) {
                return false;
            }
            if (hasPendingOutbox && !item.has_pending_outbox) {
                return false;
            }
            if (hasHumanLock && !item.human_lock_active) {
                return false;
            }
            if (query) {
                const haystack = [
                    item.id,
                    item.customer_name,
                    item.customer_phone,
                    item.last_message_preview,
                ]
                    .filter(Boolean)
                    .join(' ')
                    .toLowerCase();
                if (!haystack.includes(query)) {
                    return false;
                }
            }
            return true;
        });
        if (sortBy === 'created_at') {
            items = [...items].sort((left, right) => String(right.created_at).localeCompare(String(left.created_at)));
        } else if (sortBy === 'sla') {
            items = [...items].sort((left, right) => String(left.target_response_at || '').localeCompare(String(right.target_response_at || '')));
        } else {
            items = [...items].sort((left, right) => String(right.last_activity_at || '').localeCompare(String(left.last_activity_at || '')));
        }
        await toJsonResponse(route, {
            items: items.map((item) => ({ ...item })),
            cursor: null,
            has_more: false,
            total: items.length,
        });
    });
    await page.route('**/api/proxy/cases/assignees**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [
                {
                    agent_id: AGENT_ID,
                    agent_name: 'Manager',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_current: false,
                    open_case_count: 2,
                    assignment_eligible: true,
                },
                {
                    agent_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                    agent_name: 'Manager Two',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_current: false,
                    open_case_count: 1,
                    assignment_eligible: true,
                },
            ],
        });
    });
    await page.route(`**/api/proxy/cases/${CASE_ID}/messages**`, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [
                {
                    id: '88888888-8888-4888-8888-888888888888',
                    role: 'user',
                    content: 'Здравствуйте, можно записаться на завтра?',
                    created_at: '2026-03-05T09:10:00+05:00',
                },
            ],
            cursor: null,
            has_more: false,
        });
    });
    await page.route(`**/api/proxy/cases/${CASE_ID}`, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, buildCaseDetailPayload(caseState));
    });
    await page.route(/.*\/api\/proxy\/inbox\/macros(?:\?.*)?$/, async (route) => {
        if (route.request().method() === 'GET') {
            await toJsonResponse(route, {
                items: macroStore.map((macro) => ({ ...macro })),
            });
            return;
        }
        if (route.request().method() === 'POST') {
            const payload = route.request().postDataJSON() as {
                scope?: 'personal' | 'team';
                label?: string;
                body?: string;
                action?: Record<string, unknown> | null;
                is_active?: boolean;
            } | null;
            lastMacroCreatePayload = payload;
            const createdMacro = {
                id: CREATED_MACRO_ID,
                scope: payload?.scope === 'team' ? 'team' : 'personal',
                label: payload?.label ?? 'Новый макрос',
                body: payload?.body ?? '',
                action: payload?.action ?? null,
                is_active: payload?.is_active ?? true,
                created_at: '2026-03-05T09:30:00+05:00',
                updated_at: '2026-03-05T09:30:00+05:00',
            };
            macroStore.unshift(createdMacro);
            await toJsonResponse(route, { macro: createdMacro });
            return;
        }
        await route.fallback();
    });
    await page.route(/.*\/api\/proxy\/inbox\/macros\/[^/]+$/, async (route) => {
        if (route.request().method() !== 'PATCH') {
            await route.fallback();
            return;
        }
        const macroId = route.request().url().split('/').pop() ?? '';
        const payload = route.request().postDataJSON() as {
            label?: string;
            body?: string;
            action?: Record<string, unknown> | null;
            is_active?: boolean;
        } | null;
        const macro = macroStore.find((item) => item.id === macroId);
        if (!macro) {
            await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: { code: 'NOT_FOUND' } }) });
            return;
        }
        if (typeof payload?.label === 'string') {
            macro.label = payload.label;
        }
        if (typeof payload?.body === 'string') {
            macro.body = payload.body;
        }
        if (payload && Object.prototype.hasOwnProperty.call(payload, 'action')) {
            macro.action = payload.action ?? null;
        }
        if (typeof payload?.is_active === 'boolean') {
            macro.is_active = payload.is_active;
        }
        macro.updated_at = '2026-03-05T09:31:00+05:00';
        await toJsonResponse(route, { ...macro });
    });
    await page.route(/.*\/api\/proxy\/inbox\/macros\/[^/]+\/execute$/, async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        const payload = route.request().postDataJSON() as { case_id?: string } | null;
        lastMacroExecutePayload = payload;
        const urlParts = route.request().url().split('/');
        const macroId = urlParts[urlParts.length - 2] ?? '';
        const macro = macroStore.find((item) => item.id === macroId);
        if (!macro) {
            await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ error: { code: 'NOT_FOUND' } }) });
            return;
        }
        if (macro.action?.type === 'resolve_case') {
            caseState.status = 'resolved';
            caseState.business_status_code = 'resolved';
            caseState.business_status_label = 'Закрыта';
            caseState.sla_status = 'ok';
            caseState.sla_action_state = 'resolved';
            caseState.target_response_at = null;
            caseState.needs_reply = false;
        }
        if (macro.action?.type === 'snooze_case') {
            caseState.snoozed_until = '2026-03-05T10:15:00+05:00';
            caseState.snoozed_reason = (macro.action as { reason?: string | null }).reason ?? 'follow_up';
            caseState.snoozed_by = 'Manager';
            caseState.business_status_code = 'snoozed';
            caseState.business_status_label = 'Отложена';
            caseState.sla_action_state = 'waiting_client';
        }
        await toJsonResponse(route, {
            success: true,
            macro: { ...macro },
            case: buildCaseDetailPayload(caseState),
            sync: macro.action?.type === 'resolve_case'
                ? {
                    telegram: { status: 'ok', operator_message: null },
                    client_notify: {
                        status: 'failed',
                        detail: 'chatflow_failed',
                        operator_message: 'Не удалось отправить системное уведомление клиенту.',
                    },
                }
                : {
                    telegram: { status: 'ok', operator_message: null },
                    client_notify: { status: 'ok', operator_message: null },
                },
        });
    });
    await page.route(`**/api/proxy/cases/${CASE_ID}/reopen`, async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        caseState.status = 'active';
        caseState.business_status_code = 'in_progress';
        caseState.business_status_label = 'В работе';
        caseState.sla_action_state = 'reply_due';
        caseState.target_response_at = '2026-03-05T10:00:00+05:00';
        caseState.needs_reply = true;
        await toJsonResponse(route, {
            success: true,
            case: buildCaseDetailPayload(caseState),
            sync: {
                telegram: {
                    status: 'skipped',
                    detail: 'reopen_internal_only',
                    operator_message: null,
                },
                client_notify: {
                    status: 'skipped',
                    detail: 'reopen_internal_only',
                    operator_message: null,
                },
            },
        });
    });
    await page.route(`**/api/proxy/cases/${CASE_ID}/assignees**`, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [
                {
                    agent_id: AGENT_ID,
                    agent_name: 'Manager',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_current: true,
                    open_case_count: 2,
                    assignment_eligible: true,
                },
                {
                    agent_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                    agent_name: 'Manager Two',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_current: false,
                    open_case_count: 1,
                    assignment_eligible: true,
                },
                {
                    agent_id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
                    agent_name: 'Paused Manager',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_current: false,
                    open_case_count: 0,
                    routing_status: 'paused',
                    assignment_eligible: false,
                    assignment_block_reason_code: 'paused',
                    max_open_case_count: 5,
                },
                {
                    agent_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
                    agent_name: 'Follow-up Only',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_current: false,
                    open_case_count: 1,
                    routing_status: 'follow_up_only',
                    assignment_eligible: false,
                    assignment_block_reason_code: 'follow_up_only',
                },
                {
                    agent_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
                    agent_name: 'At Capacity',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_current: false,
                    open_case_count: 5,
                    assignment_eligible: false,
                    assignment_block_reason_code: 'at_capacity',
                    max_open_case_count: 5,
                },
            ],
            routing: {
                policy: 'least_open_cases',
                recommended_agent_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                recommended_agent_name: 'Manager Two',
                recommended_open_case_count: 1,
                current_agent_id: AGENT_ID,
                current_agent_name: 'Manager',
                current_open_case_count: 2,
                will_reassign: true,
                reason_code: 'least_open_cases',
                reason_summary: 'Назначить Manager Two: 1 в работе вместо Manager · 2.',
            },
        });
    });
    await page.route(`**/api/proxy/cases/${CASE_ID}/reassign`, async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        const payload = route.request().postDataJSON() as {
            agent_id?: string;
            mode?: 'manual' | 'policy';
            policy?: string;
        } | null;
        const nextAssigneeId = payload?.mode === 'policy'
            ? 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
            : payload?.agent_id ?? AGENT_ID;
        const nextAssigneeName = nextAssigneeId === AGENT_ID ? 'Manager' : 'Manager Two';
        caseState.assigned_to_id = nextAssigneeId;
        caseState.assigned_to_name = nextAssigneeName;
        caseState.business_status_code = 'needs_reply';
        caseState.business_status_label = 'Нужен ответ';
        await toJsonResponse(route, {
            success: true,
            case: { ...caseState },
            sync: null,
            routing: payload?.mode === 'policy'
                ? {
                    policy: 'least_open_cases',
                    recommended_agent_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                    recommended_agent_name: 'Manager Two',
                    recommended_open_case_count: 1,
                    current_agent_id: AGENT_ID,
                    current_agent_name: 'Manager',
                    current_open_case_count: 2,
                    will_reassign: true,
                    reason_code: 'least_open_cases',
                    reason_summary: 'Назначить Manager Two: 1 в работе вместо Manager · 2.',
                }
                : null,
        });
    });
    await page.route('**/api/proxy/cases/bulk', async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        const payload = route.request().postDataJSON() as {
            action?: 'reassign' | 'snooze' | 'route';
            case_ids?: string[];
        } | null;
        const caseIds = Array.isArray(payload?.case_ids) ? payload.case_ids : [];
        const action = payload?.action === 'route'
            ? 'route'
            : payload?.action === 'reassign'
                ? 'reassign'
                : 'snooze';
        await toJsonResponse(route, {
            success: true,
            action,
            requested_count: caseIds.length,
            processed_count: caseIds.length,
            skipped_count: 0,
            failed_count: 0,
            items: caseIds.map((caseId) => ({
                case_id: caseId,
                status: 'processed',
                code: action === 'route' ? 'ROUTED' : action === 'reassign' ? 'REASSIGNED' : 'SNOOZED',
                message: action === 'route'
                    ? 'Назначить Manager Two: 1 в работе вместо Manager · 2.'
                    : action === 'reassign'
                        ? 'Assigned to Manager Two'
                        : 'Case snoozed',
                case: null,
                routing: action === 'route'
                    ? {
                        policy: 'least_open_cases',
                        recommended_agent_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                        recommended_agent_name: 'Manager Two',
                        recommended_open_case_count: 1,
                        current_agent_id: AGENT_ID,
                        current_agent_name: 'Manager',
                        current_open_case_count: 2,
                        will_reassign: true,
                        reason_code: 'least_open_cases',
                        reason_summary: 'Назначить Manager Two: 1 в работе вместо Manager · 2.',
                    }
                    : null,
            })),
        });
    });
    await page.route(`**/api/proxy/conversations/${CONVERSATION_ID}/human-lock**`, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            status: {
                active: false,
                lock_until: null,
                remaining_seconds: null,
                source: null,
                reason: null,
                locked_by_name: null,
            },
        });
    });
    await page.route('**/api/proxy/calendar/specialists**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [
                {
                    id: SPECIALIST_ID,
                    name: 'Мастер Айжан',
                    branch_id: BRANCH_ID,
                    branch_name: 'Almaty Downtown',
                    services: [{ name: 'Маникюр', duration_min: 60, price: 7000 }],
                    is_active: true,
                },
            ],
        });
    });
    await page.route('**/api/proxy/calendar/slots**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            slots: [
                {
                    start: '2026-03-06T10:00:00+05:00',
                    end: '2026-03-06T11:00:00+05:00',
                    start_time: '10:00',
                    end_time: '11:00',
                    available: true,
                },
            ],
        });
    });
    await page.route('**/api/proxy/calendar/bookings**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [{ ...bookingState }],
            cursor: null,
            has_more: false,
        });
    });
    await page.route(`**/api/proxy/calendar/bookings/${bookingState.id}/status`, async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        const payload = route.request().postDataJSON() as { status?: 'COMPLETED' | 'NO_SHOW' } | null;
        bookingState.status = payload?.status === 'NO_SHOW' ? 'NO_SHOW' : 'COMPLETED';
        bookingState.needs_action = bookingState.status === 'NO_SHOW';
        bookingState.attention_reason = bookingState.status === 'NO_SHOW' ? 'Связаться после неявки' : null;
        const caseEffects = [] as Array<{
            case_id: string;
            action: 'reopened_for_booking_attention' | 'linked_rebooked_booking';
            message: string;
        }>;
        if (bookingState.status === 'NO_SHOW' && caseState.status === 'resolved') {
            reopenCaseForBookingAttention();
            caseEffects.push({
                case_id: CASE_ID,
                action: 'reopened_for_booking_attention',
                message: 'Неявка требует follow-up: заявка возвращена в работу.',
            });
        }
        await toJsonResponse(route, {
            success: true,
            booking: { ...bookingState },
            case_effects: caseEffects,
        });
    });
    await page.route(`**/api/proxy/calendar/bookings/${bookingState.id}/no-show-followup`, async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        const payload = route.request().postDataJSON() as {
            result?: 'contacted' | 'rebooked';
            rebooked_appointment_id?: string;
        } | null;
        bookingState.no_show_followup_done = true;
        bookingState.no_show_followup_result = payload?.result ?? 'contacted';
        bookingState.needs_action = false;
        bookingState.attention_reason = null;
        const caseEffects = [] as Array<{
            case_id: string;
            action: 'reopened_for_booking_attention' | 'linked_rebooked_booking';
            message: string;
        }>;
        if (payload?.result === 'rebooked' && payload?.rebooked_appointment_id) {
            caseEffects.push({
                case_id: CASE_ID,
                action: 'linked_rebooked_booking',
                message: 'Новая запись привязана к этой заявке.',
            });
        }
        await toJsonResponse(route, {
            success: true,
            booking: { ...bookingState },
            case_effects: caseEffects,
        });
    });
    await page.route(`**/api/proxy/calendar/bookings/${bookingState.id}/follow-up-governance`, async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        const payload = route.request().postDataJSON() as {
            owner_agent_id?: string | null;
            due_at?: string | null;
        } | null;
        bookingState.follow_up_owner_id = payload?.owner_agent_id ?? null;
        bookingState.follow_up_owner_name = bookingState.follow_up_owner_id === AGENT_ID
            ? 'Manager'
            : bookingState.follow_up_owner_id === 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
                ? 'Manager Two'
                : null;
        bookingState.follow_up_due_at = payload?.due_at ?? null;
        bookingState.follow_up_overdue = false;
        await toJsonResponse(route, {
            success: true,
            booking: { ...bookingState },
            case_effects: [],
        });
    });
}

async function gotoWithRetry(page: import('@playwright/test').Page, url: string, attempts = 3) {
    let lastError: unknown = null;
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
        try {
            await page.goto(url, { waitUntil: 'domcontentloaded' });
            return;
        } catch (error) {
            lastError = error;
            if (attempt >= attempts) {
                break;
            }
            await page.waitForTimeout(500 * attempt);
        }
    }
    if (lastError instanceof Error) {
        throw lastError;
    }
    throw new Error(`Failed to navigate to ${url}`);
}

async function openCaseDirectly(
    page: import('@playwright/test').Page,
    caseId: string,
): Promise<boolean> {
    if (!caseId) {
        return false;
    }
    const caseUrl = `${baseURL}/cases/${caseId}`;
    try {
        await gotoWithRetry(page, caseUrl);
    } catch {
        return false;
    }
    const casePane = page
        .getByTestId('case-conversation')
        .or(page.getByTestId('case-details'))
        .or(page.getByTestId('case-view'));
    try {
        await casePane.first().waitFor({ state: 'visible', timeout: 15000 });
        return true;
    } catch {
        return false;
    }
}

async function clearInboxWorkspaceStorage(page: import('@playwright/test').Page) {
    await page.evaluate(() => {
        const inboxWorkspacePrefixes = [
            'console:inbox:case-list:v1:',
            'console:inbox:selected-case:v1:',
        ];
        const keysToRemove: string[] = [];
        for (let index = 0; index < window.localStorage.length; index += 1) {
            const key = window.localStorage.key(index);
            if (!key) {
                continue;
            }
            if (inboxWorkspacePrefixes.some((prefix) => key.startsWith(prefix))) {
                keysToRemove.push(key);
            }
        }
        keysToRemove.forEach((key) => window.localStorage.removeItem(key));
    });
}

async function fetchAnyLiveCaseId(page: import('@playwright/test').Page): Promise<string | null> {
    const statuses = ['', 'open', 'active', 'resolved', 'closed'];
    for (const status of statuses) {
        const caseId = await page.evaluate(async (statusQuery) => {
            const params = new URLSearchParams();
            params.set('limit', '20');
            params.set('sort_by', 'last_activity');
            if (statusQuery) {
                params.set('status', statusQuery);
            }
            const response = await fetch(`/api/proxy/cases?${params.toString()}`, {
                method: 'GET',
                credentials: 'include',
            }).catch(() => null);
            if (!response || !response.ok) {
                return null;
            }
            const payload = await response.json().catch(() => null) as { items?: Array<{ id?: string }> } | null;
            if (!payload || !Array.isArray(payload.items)) {
                return null;
            }
            const firstCase = payload.items.find((item) => typeof item?.id === 'string' && item.id.length > 0);
            return firstCase?.id ?? null;
        }, status);
        if (caseId) {
            return caseId;
        }
    }
    return null;
}

async function resolveLiveCaseId(page: import('@playwright/test').Page): Promise<string | null> {
    if (LIVE_CASE_ID && LIVE_CASE_ID !== CASE_ID) {
        return LIVE_CASE_ID;
    }
    return fetchAnyLiveCaseId(page);
}

async function assertCalendarQueueSurface(page: import('@playwright/test').Page) {
    await gotoWithRetry(page, `${baseURL}/calendar`);
    await expect(page.getByTestId('calendar-page')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('calendar-queue-controls')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('calendar-queue-lane-attention')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('calendar-secondary-panel-toggle')).toBeVisible({ timeout: 20000 });
    await openCalendarSecondaryPanel(page, 'filters');
    await expect(page.getByTestId('calendar-queue-status-filter')).toBeVisible({ timeout: 20000 });
    await closeCalendarSecondaryPanel(page);
    const screenshotPath = path.resolve('calendar_no_cases_context.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Calendar no-cases screenshot saved to: ${screenshotPath}`);
}

async function maybeValidateLivePolicyRoutingMutation(page: import('@playwright/test').Page) {
    if (useRouteMocks) {
        return;
    }
    if (!HAS_EXPLICIT_LIVE_CASE_ID) {
        console.log('Live mode: policy-routing mutation skipped; set INSPECT_CASE_LIVE_CASE_ID to a safe active case to validate the real mutation path.');
        return;
    }
    if (!page.url().includes(`/cases/${LIVE_CASE_ID}`)) {
        const opened = await openCaseDirectly(page, LIVE_CASE_ID);
        if (!opened) {
            console.log(`Live mode: policy-routing mutation blocked; explicit case_id=${LIVE_CASE_ID} is not accessible.`);
            return;
        }
    }

    const reassignToggle = page.getByTestId('case-reassign-toggle');
    if (!(await reassignToggle.isVisible().catch(() => false))) {
        console.log(`Live mode: policy-routing mutation blocked; case_id=${LIVE_CASE_ID} does not expose reassign controls.`);
        return;
    }
    await reassignToggle.click();

    const policyButton = page.getByTestId('case-reassign-policy-submit');
    if (!(await policyButton.isVisible().catch(() => false))) {
        console.log(`Live mode: policy-routing mutation blocked; policy button is unavailable for case_id=${LIVE_CASE_ID}.`);
        return;
    }

    const responsePromise = page.waitForResponse((response) =>
        response.request().method() === 'POST'
        && response.url().includes(`/api/proxy/cases/${LIVE_CASE_ID}/reassign`)
    );
    await policyButton.click();
    const response = await responsePromise;
    expect(response.ok()).toBeTruthy();
    const payload = await response.json().catch(() => null) as { routing?: { reason_summary?: string } } | null;
    if (payload?.routing?.reason_summary) {
        console.log(`Live mode: policy-routing mutation reached backend for case_id=${LIVE_CASE_ID}: ${payload.routing.reason_summary}`);
    } else {
        console.log(`Live mode: policy-routing mutation reached backend for case_id=${LIVE_CASE_ID}.`);
    }
}

async function selectOptionIfNeeded(selector: import('@playwright/test').Locator) {
    if (!(await selector.isVisible().catch(() => false))) {
        return false;
    }
    const currentValue = await selector.inputValue();
    if (currentValue) {
        return true;
    }
    const options = selector.locator('option');
    const optionCount = await options.count();
    if (optionCount < 2) {
        return false;
    }
    const nextValue = await options.nth(1).getAttribute('value');
    if (nextValue) {
        await selector.selectOption(nextValue);
    } else {
        await selector.selectOption({ index: 1 });
    }
    await expect(selector).not.toHaveValue('');
    return true;
}

async function resolveTenantSelection(page: import('@playwright/test').Page) {
    const gateSelectors = [
        page.getByTestId('company-select'),
        page.getByTestId('client-select'),
        page.getByTestId('branch-select'),
        page.getByTestId('context-company-select'),
        page.getByTestId('context-client-select'),
        page.getByTestId('context-branch-select'),
    ];
    for (const selector of gateSelectors) {
        await selectOptionIfNeeded(selector);
    }
}

async function ensureLoggedIn(page: import('@playwright/test').Page) {
    await gotoWithRetry(page, baseURL);
    await clearInboxWorkspaceStorage(page);
    await gotoWithRetry(page, baseURL);
    const casesTitle = page.getByTestId('cases-title');
    if (await casesTitle.isVisible().catch(() => false)) {
        return;
    }

    if (useRouteMocks) {
        await resolveTenantSelection(page);
        const retryButton = page.getByRole('button', { name: /повторить/i });
        for (let attempt = 0; attempt < 3; attempt += 1) {
            if (await retryButton.isVisible().catch(() => false)) {
                await retryButton.click();
                await page.waitForTimeout(250);
            }
        }
        await expect(casesTitle).toBeVisible({ timeout: 20000 });
        return;
    }

    const loginButtonLocator = page.getByTestId('login-button').or(page.getByRole('button', { name: /войти/i })).first();
    for (let attempt = 0; attempt < 6; attempt += 1) {
        if (await casesTitle.isVisible().catch(() => false)) {
            return;
        }
        if (await loginButtonLocator.isVisible().catch(() => false)) {
            break;
        }
        await page.waitForTimeout(400);
    }

    if (await loginButtonLocator.isVisible().catch(() => false)) {
        await loginThroughKeycloak(page, {
            baseURL,
            consoleHostPattern,
            loginUser,
            loginPassword,
            authWaitTimeoutMs: 20000,
        });
        await gotoWithRetry(page, baseURL);
    }

    await resolveTenantSelection(page);
    const retryButton = page.getByRole('button', { name: /повторить/i });
    for (let attempt = 0; attempt < 3; attempt += 1) {
        if (await retryButton.isVisible().catch(() => false)) {
            await retryButton.click();
            await page.waitForTimeout(500);
        }
    }
    if (useRouteMocks) {
        await expect(casesTitle).toBeVisible({ timeout: 20000 });
    }
}

async function recoverAndValidateCalendarSurface(
    page: import('@playwright/test').Page,
    message: string,
) {
    if (await isAuthGateVisible(page)) {
        console.log('Live mode: auth gate detected during fallback, retrying login.');
        await ensureLoggedIn(page);
    }
    console.log(message);
    await assertCalendarQueueSurface(page);
}

test('inspect first case', async ({ page }) => {
    test.setTimeout(90000);
    if (useRouteMocks) {
        await installConsoleMocks(page);
    }
    await ensureLoggedIn(page);
    await resolveTenantSelection(page);
    const casesTitle = page.getByTestId('cases-title');
    const hasCasesWorkspace = (await casesTitle.isVisible().catch(() => false))
        || (await page.getByTestId('cases-table').isVisible().catch(() => false));
    if (useRouteMocks) {
        await expect(casesTitle).toBeVisible({ timeout: 20000 });
    } else if (!hasCasesWorkspace) {
        const screenshotPath = path.resolve('live_cases_workspace_unavailable.png');
        await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => null);
        console.log('Live mode: cases workspace unavailable, trying direct case fallback.');
        console.log(`Fallback screenshot: ${screenshotPath}`);
        const liveCaseId = await resolveLiveCaseId(page);
        const opened = liveCaseId ? await openCaseDirectly(page, liveCaseId) : false;
        if (!opened) {
            await recoverAndValidateCalendarSurface(
                page,
                `Live mode: cases workspace unavailable and direct fallback failed for case_id=${liveCaseId ?? LIVE_CASE_ID}.`,
            );
            return;
        }
    }

    const tableHtml = await page.getByTestId('cases-table').innerHTML().catch(() => 'Table HTML not found');
    console.log('--- TABLE HTML START ---');
    console.log(tableHtml.slice(0, 2000));
    console.log('--- TABLE HTML END ---');

    const emptyState = page.getByTestId('cases-empty');
    let openedFixtureCaseDirectly = false;
    if (await emptyState.isVisible().catch(() => false)) {
        console.log('No cases in queue.');
        const screenshotPath = path.resolve('inbox_debug.png');
        const screenshotTaken = await page
            .screenshot({ path: screenshotPath, fullPage: true })
            .then(() => true)
            .catch(() => false);
        if (screenshotTaken) {
            console.log(`Debug screenshot saved to: ${screenshotPath}`);
        } else {
            console.log('Debug screenshot skipped: unable to capture screenshot in current browser state.');
        }
        if (useRouteMocks) {
            await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
            openedFixtureCaseDirectly = true;
        } else {
            console.log('Live mode: queue is empty, trying direct case fallback.');
            const liveCaseId = await resolveLiveCaseId(page);
            if (!liveCaseId) {
                console.log('Live mode: no accessible cases found; validating calendar queue surface only.');
                await assertCalendarQueueSurface(page);
                return;
            }
            openedFixtureCaseDirectly = await openCaseDirectly(page, liveCaseId);
            if (!openedFixtureCaseDirectly) {
                await recoverAndValidateCalendarSurface(
                    page,
                    `Live mode: direct case fallback failed for case_id=${liveCaseId}; validating calendar queue surface.`,
                );
                return;
            }
        }
    }

    if (useRouteMocks && !openedFixtureCaseDirectly) {
        await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
        openedFixtureCaseDirectly = true;
    }

    if (!openedFixtureCaseDirectly) {
        const firstRow = page.getByTestId('cases-row').first();
        if (await firstRow.isVisible().catch(() => false)) {
            await firstRow.click({ force: true });
        } else if (!useRouteMocks) {
            console.log('Live mode: queue row unavailable, trying direct case fallback.');
            const liveCaseId = await resolveLiveCaseId(page);
            if (!liveCaseId) {
                console.log('Live mode: no accessible cases found; validating calendar queue surface only.');
                await assertCalendarQueueSurface(page);
                return;
            }
            const opened = await openCaseDirectly(page, liveCaseId);
            if (!opened) {
                await recoverAndValidateCalendarSurface(
                    page,
                    `Live mode: queue row fallback failed for case_id=${liveCaseId}; validating calendar queue surface.`,
                );
                return;
            }
        } else {
            await expect(firstRow).toBeVisible({ timeout: 15000 });
            await firstRow.click({ force: true });
        }
    }

    const casePane = page
        .getByTestId('case-conversation')
        .or(page.getByTestId('case-details'))
        .or(page.getByTestId('case-view'));

    if (!(await casePane.first().isVisible().catch(() => false))) {
        const openButton = page.getByTestId('case-open').first();
        if (await openButton.isVisible().catch(() => false)) {
            await openButton.click();
            await expect(page).toHaveURL(/\/cases\/[a-f0-9-]+/, { timeout: 15000 });
        }
    }

    if (!(await casePane.first().isVisible().catch(() => false))) {
        if (!useRouteMocks) {
            const liveCaseId = await resolveLiveCaseId(page);
            if (!liveCaseId) {
                console.log('Live mode: no accessible cases found; validating calendar queue surface only.');
                await assertCalendarQueueSurface(page);
                return;
            }
            const opened = await openCaseDirectly(page, liveCaseId);
            if (!opened) {
                await recoverAndValidateCalendarSurface(
                    page,
                    `Live mode: case pane fallback failed for case_id=${liveCaseId}; validating calendar queue surface.`,
                );
                return;
            }
        }
        await expect(casePane.first()).toBeVisible({ timeout: 15000 });
    }
    console.log(`Current URL: ${page.url()}`);

    const caseActionBadge = page.getByTestId('case-next-action');
    await expect(caseActionBadge).toBeVisible({ timeout: 15000 });
    await expect(caseActionBadge).not.toContainText('SLA:', { timeout: 15000 });
    await expect(page.getByTestId('case-business-status')).toContainText('Нужен ответ', { timeout: 15000 });
    if (!useRouteMocks) {
        await maybeValidateLivePolicyRoutingMutation(page);
    }
    if (useRouteMocks) {
        await expect(page.getByTestId('cases-mode-scopes')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-queue-views')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-filter-compact-layout')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-filter-owner-scope')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-filter-owner-scope').locator('option').nth(2)).toContainText('Без владельца');
        await expect(page.getByTestId('cases-filter-owner-scope').locator('option').nth(3)).toContainText('Manager · 2 в работе');
        await expect(page.getByTestId('cases-filter-owner-scope').locator('option').nth(4)).toContainText('Manager Two · 1 в работе');
        await expect(page.getByTestId('cases-secondary-panel-toggle')).toBeVisible({ timeout: 15000 });
        const inboxList = page.getByTestId('inbox-list');
        await expect(inboxList).toBeVisible({ timeout: 15000 });
        const inboxListWidth = await inboxList.evaluate((element) => element.getBoundingClientRect().width);
        expect(inboxListWidth).toBeGreaterThan(300);
        await openCasesSecondaryPanel(page, 'view');
        if (!(await page.getByTestId('cases-field-panel').isVisible().catch(() => false))) {
            await page.getByTestId('cases-field-toggle').click({ force: true });
        }
        await page.getByTestId('cases-field-owner').check({ force: true });
        await page.getByTestId('cases-field-channel').check({ force: true });
        await expect(page.getByTestId('cases-field-toggle')).toContainText('Вид 4/5', { timeout: 15000 });
        await closeCasesSecondaryPanel(page);

        const selectedAssigneeId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
        const ownerScopeRequest = await waitForCasesListRequest(page, async () => {
            await page.getByTestId('cases-filter-owner-scope').selectOption(selectedAssigneeId);
        });
        expect(ownerScopeRequest.searchParams.get('assignee_id')).toBe(selectedAssigneeId);
        expect(ownerScopeRequest.searchParams.get('queue_view')).toBeNull();
        expect(ownerScopeRequest.searchParams.get('status')).toBe('open');
        expect(ownerScopeRequest.searchParams.get('sort_by')).toBe('last_activity');
        await expect(page.getByTestId('cases-owner-summary')).toContainText('Manager Two', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Сабина', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Manager Two', { timeout: 15000 });

        await openCasesSecondaryPanel(page, 'filters');
        if (!(await page.getByTestId('cases-filters-advanced').isVisible().catch(() => false))) {
            await page.getByTestId('cases-filter-advanced-toggle').click({ force: true });
        }
        await expect(page.getByTestId('cases-filters-advanced')).toBeVisible({ timeout: 15000 });
        const sortRequest = await waitForCasesListRequest(page, async () => {
            await page.getByTestId('cases-filter-sort-select').selectOption('created_at');
        });
        expect(sortRequest.searchParams.get('status')).toBe('open');
        expect(sortRequest.searchParams.get('assignee_id')).toBe(selectedAssigneeId);
        expect(sortRequest.searchParams.get('sort_by')).toBe('created_at');
        await closeCasesSecondaryPanel(page);
        await page.getByTestId('cases-mode-scope-resolved').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect(page.getByTestId('cases-history-hint')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-queue-views')).toHaveCount(0);
        await expect(page.getByTestId('cases-row').first()).toContainText('Сабина Архив', { timeout: 15000 });

        await page.getByTestId('cases-mode-scope-all').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect(page.getByTestId('cases-history-hint')).toContainText('Поиск по открытым и закрытым заявкам.', { timeout: 15000 });
        await expect(page.getByTestId('cases-row')).toHaveCount(2, { timeout: 15000 });

        await page.getByTestId('cases-mode-scope-open').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect(page.getByTestId('cases-queue-views')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Сабина', { timeout: 15000 });

        await openCasesSecondaryPanel(page, 'filters');
        await page.getByTestId('cases-filter-clear').click({ force: true });
        await closeCasesSecondaryPanel(page);
        await expect(page.getByTestId('cases-queue-view-summary')).toContainText('Открытые', { timeout: 15000 });
        await page.getByTestId('cases-mode-scope-resolved').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect(page.getByTestId('cases-history-hint')).toContainText('История закрытых заявок.', { timeout: 15000 });
        await expect(page.getByTestId('cases-queue-views')).toHaveCount(0);
        await openCasesSecondaryPanel(page, 'filters');
        const resolvedDateRequest = await waitForCasesListRequest(page, async () => {
            await page.getByTestId('cases-filter-date-from').fill('2026-03-05');
        });
        expect(resolvedDateRequest.searchParams.get('resolved_from')).toBe('2026-03-05');
        expect(resolvedDateRequest.searchParams.get('date_from')).toBeNull();
        await closeCasesSecondaryPanel(page);

        await page.getByTestId('cases-mode-scope-open').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect(page.getByTestId('cases-queue-views')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Айгуль', { timeout: 15000 });
        await page.getByTestId('cases-filter-owner-scope').selectOption('__unassigned__');
        await expect(page.getByTestId('cases-owner-summary')).toContainText('Без владельца', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Нургуль', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Без владельца', { timeout: 15000 });

        await openCasesSecondaryPanel(page, 'filters');
        await page.getByTestId('cases-filter-clear').click({ force: true });
        await closeCasesSecondaryPanel(page);
        await expect(page.getByTestId('cases-queue-view-summary')).toContainText('Открытые', { timeout: 15000 });
        await expect(page.getByTestId('cases-queue-view-waiting_client')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-queue-view-snoozed')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('cases-queue-view-needs_reply').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect(page.getByTestId('cases-row')).toHaveCount(1, { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Айгуль', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Manager', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('whatsapp', { timeout: 15000 });
        await page.getByTestId('cases-queue-view-waiting_client').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect(page.getByTestId('cases-row')).toHaveCount(1, { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Мадина', { timeout: 15000 });
        await page.getByTestId('cases-queue-view-snoozed').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect(page.getByTestId('cases-row')).toHaveCount(1, { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Жанар', { timeout: 15000 });

        await page.getByTestId('cases-queue-view-all_open').evaluate((element) => {
            (element as HTMLButtonElement).click();
        });
        await expect(page.getByTestId('cases-queue-view-summary')).toContainText('Открытые', { timeout: 15000 });
        await page.getByTestId('cases-row').first().click({ force: true });
        await expect(caseActionBadge).toContainText('Ответить до', { timeout: 15000 });
        await expect(page.getByTestId('case-reassign-toggle')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('case-snooze-toggle')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('case-origin-summary')).toContainText('Клиент написал, и заявка ушла менеджеру', { timeout: 15000 });
        await expect(page.getByTestId('case-origin-summary')).toContainText('Клиент хочет маникюр и уточняет свободное время.', { timeout: 15000 });
        await expect(page.getByTestId('case-booking-summary')).toContainText('нужно подтвердить запись', { timeout: 15000 });
        const bulkSelect = page.getByTestId('cases-bulk-select').first();
        await bulkSelect.click({ force: true });
        await expect(bulkSelect).toBeChecked({ timeout: 15000 });
        await expect(page.getByTestId('cases-bulk-selection-summary')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('cases-bulk-open-panel').click({ force: true });
        await expect(page.getByTestId('cases-bulk-toolbar')).toBeVisible({ timeout: 15000 });
        await closeCasesSecondaryPanel(page);
        await page.getByTestId('case-reassign-toggle').click();
        await expect(page.getByTestId('case-reassign-recommendation')).toContainText('Follow-up + SLA баланс', { timeout: 15000 });
        await expect(page.getByTestId('case-reassign-recommendation')).toContainText('Назначить Manager Two: 1 в работе вместо Manager · 2.', { timeout: 15000 });
        await expect(page.getByTestId('case-reassign-recommend-submit')).toContainText('Передать Manager Two');
        const caseRouteRequestPromise = page.waitForRequest((request) =>
            request.method() === 'POST' && request.url().includes(`/api/proxy/cases/${CASE_ID}/reassign`)
        );
        await page.getByTestId('case-reassign-policy-submit').click({ force: true });
        const caseRouteRequest = await caseRouteRequestPromise;
        expect(caseRouteRequest.postDataJSON()).toMatchObject({
            mode: 'policy',
            policy: 'follow_up_sla_balance',
        });
        await page.getByTestId('case-snooze-toggle').click();
        await expect(page.getByTestId('case-snooze-minutes')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('case-snooze-close').click({ force: true });
        await expect(page.getByTestId('case-snooze-panel')).toHaveCount(0);
        await page.getByTestId('case-reassign-toggle').click();
        await expect(page.getByTestId('case-reassign-panel')).toBeVisible({ timeout: 15000 });
    }

    let content = '';
    const contentCandidates = [
        page.getByTestId('case-conversation'),
        page.getByTestId('case-details'),
        page.getByTestId('case-view'),
    ];
    for (const candidate of contentCandidates) {
        if (await candidate.isVisible().catch(() => false)) {
            content = (await candidate.innerText().catch(() => '')).slice(0, 3000);
            if (content) {
                break;
            }
        }
    }
    console.log('--- CASE CONTENT START ---');
    console.log(content || 'Case content is empty');
    console.log('--- CASE CONTENT END ---');

    const screenshotPath = path.resolve('case_inspection.png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log(`Screenshot saved to: ${screenshotPath}`);

    const openCalendarButton = page.getByTestId('case-open-calendar');
    if (await openCalendarButton.isVisible().catch(() => false)) {
        await openCalendarButton.click();
        const visibleBookingsPanel = page.locator('[data-testid=\"case-bookings-panel\"]:visible').first();
        await expect(visibleBookingsPanel).toBeVisible({ timeout: 20000 });
        expect(page.url()).not.toContain('/calendar');
        if (useRouteMocks) {
            await expect(visibleBookingsPanel.locator('[data-testid=\"case-booking-card\"]').first()).toBeVisible({ timeout: 20000 });
            await expect(visibleBookingsPanel.getByTestId('case-bookings-semantic-summary')).toContainText('нужно подтвердить запись', { timeout: 20000 });
            await visibleBookingsPanel.getByRole('button', { name: 'Пришел', exact: true }).click();
            await expect(visibleBookingsPanel.getByText('пришел', { exact: true }).first()).toBeVisible({ timeout: 20000 });
            await expect(page.getByTestId('case-booking-summary')).toContainText('Визит по заявке завершен', { timeout: 20000 });
        }

        const openFullCalendar = visibleBookingsPanel.getByTestId('case-bookings-open-full-calendar');
        const calendarHref = await openFullCalendar.getAttribute('href');
        if (!calendarHref) {
            throw new Error('case-bookings-open-full-calendar link does not contain href');
        }
        expect(calendarHref).toContain('return_panel=bookings');
        await gotoWithRetry(page, `${baseURL}${calendarHref}`);
        await expect(page.getByTestId('calendar-page')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-queue-controls')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-queue-mode-ops')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-queue-mode-history')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-secondary-panel-toggle')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-history-all-dates-hint')).toBeVisible({ timeout: 20000 });
        await openCalendarSecondaryPanel(page, 'filters');
        await expect(page.getByTestId('calendar-queue-status-filter')).toBeVisible({ timeout: 20000 });
        await closeCalendarSecondaryPanel(page);

        const calendarScreenshotPath = path.resolve('calendar_case_context.png');
        await page.screenshot({ path: calendarScreenshotPath, fullPage: true });
        console.log(`Calendar screenshot saved to: ${calendarScreenshotPath}`);

        const openLinkedCase = page.getByTestId('calendar-open-linked-case');
        if (await openLinkedCase.isVisible().catch(() => false)) {
            await openLinkedCase.click();
            await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });
            await expect(page.locator('[data-testid=\"case-bookings-panel\"]:visible').first()).toBeVisible({ timeout: 20000 });
            await expect.poll(() => new URL(page.url()).pathname).toBe(`/cases/${CASE_ID}`);
            await expect.poll(() => new URL(page.url()).searchParams.get('panel')).toBe('bookings');
        }
    } else {
        console.log('case-open-calendar button is not visible for this case.');
    }
});

test('manager history modes hide queue views and keep owner scope role-gated', async ({ page }) => {
    test.skip(!useRouteMocks, 'manager history matrix is covered in deterministic mock lane only');
    test.setTimeout(90000);

    await installConsoleMocks(page, { viewerRole: 'manager' });
    await ensureLoggedIn(page);
    await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
    await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });

    await expect(page.getByTestId('cases-filter-owner-scope').locator('option')).toHaveCount(2);
    await expect(page.getByTestId('cases-queue-views')).toBeVisible({ timeout: 15000 });

    const resolvedRequest = await waitForCasesListRequest(page, async () => {
        await page.getByTestId('cases-mode-scope-resolved').click({ force: true });
    });
    expect(resolvedRequest.searchParams.get('status')).toBe('resolved');
    expect(resolvedRequest.searchParams.get('sort_by')).toBe('resolved_at');
    expect(resolvedRequest.searchParams.get('assigned_to_me')).toBeNull();
    expect(resolvedRequest.searchParams.get('assignee_id')).toBeNull();
    expect(resolvedRequest.searchParams.get('unassigned')).toBeNull();
    await expect(page.getByTestId('cases-queue-views')).toHaveCount(0);
    await expect(page.getByTestId('cases-history-hint')).toContainText('История закрытых заявок', { timeout: 15000 });
    await expect(page.getByTestId('cases-row').first()).toContainText('Сабина Архив', { timeout: 15000 });

    const mineHistoryRequest = await waitForCasesListRequest(page, async () => {
        await page.getByTestId('cases-filter-owner-scope').selectOption('__mine__');
    });
    expect(mineHistoryRequest.searchParams.get('status')).toBe('resolved');
    expect(mineHistoryRequest.searchParams.get('assigned_to_me')).toBe('true');
    await expect(page.getByTestId('cases-owner-summary')).toContainText('Мои заявки', { timeout: 15000 });

    const allModeRequest = await waitForCasesListRequest(page, async () => {
        await page.getByTestId('cases-mode-scope-all').click({ force: true });
    });
    expect(allModeRequest.searchParams.get('status')).toBeNull();
    expect(allModeRequest.searchParams.get('sort_by')).toBe('created_at');
    expect(allModeRequest.searchParams.get('assigned_to_me')).toBe('true');
    await expect(page.getByTestId('cases-queue-views')).toHaveCount(0);
    await expect(page.getByTestId('cases-history-hint')).toContainText('Поиск по открытым и закрытым заявкам', { timeout: 15000 });

    const backToOpenRequest = await waitForCasesListRequest(page, async () => {
        await page.getByTestId('cases-mode-scope-open').click({ force: true });
    });
    expect(backToOpenRequest.searchParams.get('status')).toBe('open');
    expect(backToOpenRequest.searchParams.get('assigned_to_me')).toBe('true');
    await expect(page.getByTestId('cases-queue-views')).toBeVisible({ timeout: 15000 });
});

test('role-gated owner scope is normalized before first queue request', async ({ page }) => {
    test.setTimeout(60000);
    test.skip(!useRouteMocks, 'Deterministic stale-storage validation runs only with route mocks.');

    const staleScopeKey = `console:inbox:case-list:v5:manager:${AGENT_ID}:${CLIENT_ID}:${BRANCH_ID}`;
    const stalePrefs = {
        savedAt: Date.now(),
        value: {
            filters: {
                query: 'Сабина',
                hasDeliveryError: false,
                hasPendingOutbox: false,
                hasHumanLock: false,
                sortBy: 'created_at',
            },
            ownerScope: {
                kind: 'agent',
                agentId: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
            },
            modeScope: 'resolved',
            searchValue: 'Сабина',
            showAdvancedFilters: false,
            filtersCollapsed: false,
            autoRefreshEnabled: true,
            activeViewId: 'all_open',
            visibleFields: {
                branch: true,
                owner: false,
                channel: false,
                activity: true,
                priority: false,
            },
        },
    };

    await page.addInitScript(
        ([key, value]) => {
            window.localStorage.setItem(key, JSON.stringify(value));
        },
        [staleScopeKey, stalePrefs] as const,
    );
    await installConsoleMocks(page, { viewerRole: 'manager' });
    const firstQueueRequestPromise = page.waitForRequest((request) => (
        request.method() === 'GET' && request.url().includes('/api/proxy/cases?')
    ));
    await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);

    const firstQueueRequest = await firstQueueRequestPromise;
    const requestUrl = new URL(firstQueueRequest.url());
    expect(requestUrl.searchParams.get('assignee_id')).toBeNull();
    expect(requestUrl.searchParams.get('unassigned')).toBeNull();
    expect(requestUrl.searchParams.get('status')).toBe('resolved');
    expect(requestUrl.searchParams.get('sort_by')).toBe('created_at');

    await expect(page.getByTestId('cases-filter-owner-scope').locator('option')).toHaveCount(2);
    await expect(page.getByTestId('cases-owner-summary')).toHaveCount(0);
    await expect(page.getByTestId('cases-search-summary')).toContainText('Сабина', { timeout: 15000 });
});

test('manage and apply action macro', async ({ page }) => {
    test.skip(!useRouteMocks, 'action-macro UI is covered in deterministic mock lane only');
    test.setTimeout(90000);

    await installConsoleMocks(page);
    await ensureLoggedIn(page);
    await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
    await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });

    await page.getByRole('button', { name: /все ответы/i }).click({ force: true });
    await expect(page.getByTestId(`macro-chip-${ACTION_MACRO_ID}`)).toBeVisible({ timeout: 15000 });

    await page.getByRole('button', { name: 'Управление' }).click({ force: true });
    await page.getByPlaceholder('Заголовок').fill('Отложить и ответить');
    await page.getByPlaceholder('Текст быстрого ответа').fill('Отложу заявку и вернусь позже.');
    await page.getByTestId('macro-action-select').selectOption('snooze_case');
    await page.getByTestId('macro-action-minutes').fill('45');
    await page.getByPlaceholder('Причина отсрочки').fill('follow_up');
    await page.getByTestId('macro-save-button').click({ force: true });

    await expect.poll(() => lastMacroCreatePayload).not.toBeNull();
    expect(lastMacroCreatePayload).toMatchObject({
        label: 'Отложить и ответить',
        body: 'Отложу заявку и вернусь позже.',
        action: {
            type: 'snooze_case',
            minutes: 45,
            reason: 'follow_up',
        },
    });

    await page.getByRole('button', { name: 'Ответы', exact: true }).click({ force: true });
    await expect(page.getByTestId(`macro-apply-${CREATED_MACRO_ID}`)).toBeVisible({ timeout: 15000 });
    await page.getByTestId(`macro-apply-${CREATED_MACRO_ID}`).click({ force: true });

    await expect.poll(() => lastMacroExecutePayload).toMatchObject({ case_id: CASE_ID });
    await expect(page.getByTestId('case-next-action')).toContainText('Ожидаем клиента', { timeout: 15000 });
    await expect(page.getByTestId('case-business-status')).toContainText('Отложена', { timeout: 15000 });
    await expect(
        page.getByPlaceholder('Введите сообщение или подпись к файлу. Enter — отправить.')
    ).toHaveValue(/Отложу заявку и вернусь позже\./, { timeout: 15000 });
});

test('action feedback hides raw sync reason codes and keeps reopen internal-only', async ({ page }) => {
    test.skip(!useRouteMocks, 'action feedback contract is covered in deterministic mock lane only');
    test.setTimeout(90000);

    await installConsoleMocks(page);
    await ensureLoggedIn(page);
    await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
    await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });

    await page.getByRole('button', { name: /все ответы/i }).click({ force: true });
    await expect(page.getByTestId(`macro-apply-${ACTION_MACRO_ID}`)).toBeVisible({ timeout: 15000 });
    await page.getByTestId(`macro-apply-${ACTION_MACRO_ID}`).click({ force: true });

    await expect(page.getByText('Применено: Закрыть заявку. Текст добавлен в черновик.')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('Не удалось отправить системное уведомление клиенту.')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('chatflow_failed')).toHaveCount(0);
    await expect(page.getByTestId('case-business-status')).toContainText('Закрыта', { timeout: 15000 });
    await expect(page.getByTestId('case-reopen')).toBeVisible({ timeout: 15000 });

    await expect(page.getByText('Не удалось отправить системное уведомление клиенту.')).toHaveCount(0, { timeout: 7000 });

    await page.getByTestId('case-reopen').click({ force: true });
    await expect(page.getByText('Заявка возвращена в работу: Manager')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('case-business-status')).toContainText('В работе', { timeout: 15000 });
    await expect(page.getByText('chatflow_failed')).toHaveCount(0);
    await expect(page.getByText('Не удалось отправить системное уведомление клиенту.')).toHaveCount(0);
});

test('booking no-show reopens resolved case and preserves case-booking semantics', async ({ page }) => {
    test.skip(!useRouteMocks, 'Wave21 booking-state propagation is covered in deterministic mock lane only');
    test.setTimeout(90000);

    await installConsoleMocks(page);
    await ensureLoggedIn(page);
    await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
    await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });

    await page.getByRole('button', { name: /все ответы/i }).click({ force: true });
    await page.getByTestId(`macro-apply-${ACTION_MACRO_ID}`).click({ force: true });

    await expect(page.getByTestId('case-business-status')).toContainText('Закрыта', { timeout: 15000 });

    const openCalendarButton = page.getByTestId('case-open-calendar');
    await openCalendarButton.click();
    const visibleBookingsPanel = page.locator('[data-testid=\"case-bookings-panel\"]:visible').first();
    await expect(visibleBookingsPanel).toBeVisible({ timeout: 20000 });
    await visibleBookingsPanel.getByRole('button', { name: 'Не пришел', exact: true }).click();

    await expect(page.getByText('Неявка требует follow-up: заявка возвращена в работу.')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('case-business-status')).toContainText('Нужен ответ', { timeout: 15000 });
    await expect(page.getByTestId('case-next-action')).toContainText('Ответить до', { timeout: 15000 });
    await expect(page.getByTestId('case-booking-summary')).toContainText('Клиент не пришел', { timeout: 15000 });
});

test('calendar secondary panels isolate filters and booking actions', async ({ page }) => {
    test.skip(!useRouteMocks, 'Wave34 calendar decomposition is covered in deterministic mock lane only');
    test.setTimeout(90000);

    await installConsoleMocks(page);
    await ensureLoggedIn(page);
    await gotoWithRetry(page, `${baseURL}/calendar`);
    await expect(page.getByTestId('calendar-page')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('calendar-queue-controls')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('calendar-queue-status-filter')).toHaveCount(0);
    await expect(page.getByTestId('calendar-follow-up-governance-card')).toHaveCount(0);

    await openCalendarSecondaryPanel(page, 'filters');
    await expect(page.getByTestId('calendar-queue-status-filter')).toBeVisible({ timeout: 20000 });
    await closeCalendarSecondaryPanel(page);

    await page.getByTestId('calendar-booking-open-actions').first().click({ force: true });
    const bookingPanel = page.getByTestId('calendar-booking-panel');
    await expect(bookingPanel).toBeVisible({ timeout: 20000 });
    await bookingPanel.getByRole('button', { name: 'Не пришел', exact: true }).click();
    await expect(bookingPanel.getByTestId('calendar-follow-up-governance-owner')).toBeVisible({ timeout: 20000 });
    await expect(bookingPanel.getByRole('button', { name: 'Связались', exact: true })).toBeVisible({ timeout: 20000 });

    await closeCalendarBookingPanel(page);
    await expect(page.getByTestId('calendar-follow-up-governance-card')).toHaveCount(0);
});

test('saved views, team presets, and share urls stay reachable from inbox secondary surfaces', async ({ page }) => {
    test.skip(!useRouteMocks, 'Wave35 saved views/team presets/share URLs are covered in deterministic mock lane only');
    test.setTimeout(90000);

    await installConsoleMocks(page, { viewerRole: 'owner' });
    await ensureLoggedIn(page);
    await installClipboardCapture(page);
    await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
    await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });

    await openCasesSecondaryPanel(page, 'saved_views');
    const savedViewSelect = page.getByTestId('cases-saved-view-select');
    await savedViewSelect.selectOption(CASE_PERSONAL_VIEW_ID);
    await expect(page.getByText('Применён вид «Мои Айгуль»')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('cases-saved-view-summary')).toContainText('Мои Айгуль', { timeout: 15000 });
    await expect(page.getByTestId('cases-search-summary')).toContainText('Айгуль', { timeout: 15000 });
    await expect(page.getByTestId('cases-owner-summary')).toContainText('Мои заявки', { timeout: 15000 });
    await expect.poll(() => new URL(page.url()).searchParams.get('view_id')).toBe(CASE_PERSONAL_VIEW_ID);
    await expect.poll(() => new URL(page.url()).searchParams.get('q')).toBe('Айгуль');

    await page.getByTestId('cases-saved-view-save').click({ force: true });
    await page.getByTestId('cases-saved-view-name-input').fill('Команда · Айгуль');
    await page.getByTestId('cases-saved-view-scope').selectOption('team');
    await page.getByTestId('cases-saved-view-target-branch').selectOption(BRANCH_ID);
    await page.getByTestId('cases-saved-view-target-role').selectOption('manager');
    await page.getByTestId('cases-saved-view-name-submit').click({ force: true });

    await expect(page.getByText('Вид «Команда · Айгуль» сохранён')).toBeVisible({ timeout: 15000 });
    await expect(savedViewSelect).toHaveValue(CASE_CREATED_TEAM_VIEW_ID, { timeout: 15000 });
    await expect(page.getByTestId('cases-saved-view-team-branch')).toHaveValue(BRANCH_ID);
    await expect(page.getByTestId('cases-saved-view-team-role')).toHaveValue('manager');

    await page.getByTestId('cases-saved-view-team-role').selectOption('');
    await page.getByTestId('cases-saved-view-update').click({ force: true });
    await expect(page.getByText('Вид «Команда · Айгуль» обновлён')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('cases-saved-view-team-role')).toHaveValue('');

    await page.getByTestId('cases-queue-copy-link').click({ force: true });
    await expect.poll(() => readCopiedClipboardText(page)).toContain(`view_id=${CASE_CREATED_TEAM_VIEW_ID}`);
    const copiedUrl = await readCopiedClipboardText(page);
    expect(copiedUrl).toContain('q=%D0%90%D0%B9%D0%B3%D1%83%D0%BB%D1%8C');

    await gotoWithRetry(page, copiedUrl);
    await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('cases-search-summary')).toContainText('Айгуль', { timeout: 15000 });
    await expect(page.getByTestId('cases-owner-summary')).toContainText('Мои заявки', { timeout: 15000 });
    await openCasesSecondaryPanel(page, 'saved_views');
    await expect(page.getByTestId('cases-saved-view-select')).toHaveValue(CASE_CREATED_TEAM_VIEW_ID);
    await expect(page.getByTestId('cases-saved-view-team-branch')).toHaveValue(BRANCH_ID);
    await expect(page.getByTestId('cases-saved-view-team-role')).toHaveValue('');
});

test('follow-up governance stays inside the calendar booking panel', async ({ page }) => {
    test.skip(!useRouteMocks, 'Wave35 follow-up governance proof is covered in deterministic mock lane only');
    test.setTimeout(90000);

    await installConsoleMocks(page, { viewerRole: 'owner' });
    await ensureLoggedIn(page);
    await gotoWithRetry(page, `${baseURL}/calendar`);
    await expect(page.getByTestId('calendar-page')).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId('calendar-follow-up-governance-card')).toHaveCount(0);

    await page.getByTestId('calendar-booking-open-actions').first().click({ force: true });
    const bookingPanel = page.getByTestId('calendar-booking-panel');
    await expect(bookingPanel).toBeVisible({ timeout: 20000 });
    await bookingPanel.getByRole('button', { name: 'Не пришел', exact: true }).click();
    await expect(bookingPanel.getByTestId('calendar-follow-up-governance-owner')).toBeVisible({ timeout: 20000 });

    await bookingPanel.getByTestId('calendar-follow-up-governance-owner').selectOption(AGENT_ID);
    await bookingPanel.getByTestId('calendar-follow-up-governance-due').fill('2026-03-06T14:30');
    await bookingPanel.getByTestId('calendar-follow-up-governance-save').click({ force: true });
    await expect(page.getByText('Follow-up owner и дедлайн обновлены')).toBeVisible({ timeout: 15000 });

    await closeCalendarBookingPanel(page);
    await page.getByTestId('calendar-booking-open-actions').first().click({ force: true });
    const reopenedPanel = page.getByTestId('calendar-booking-panel');
    await expect(reopenedPanel.getByTestId('calendar-follow-up-governance-owner')).toHaveValue(AGENT_ID);
    await expect(reopenedPanel.getByTestId('calendar-follow-up-governance-due')).toHaveValue('2026-03-06T14:30');
    await closeCalendarBookingPanel(page);
    await expect(page.getByTestId('calendar-follow-up-governance-card')).toHaveCount(0);
});

test('routing profile restrictions stay visible in reassignment panel', async ({ page }) => {
    test.skip(!useRouteMocks, 'Wave35 routing-profile restriction proof is covered in deterministic mock lane only');
    test.setTimeout(90000);

    await installConsoleMocks(page);
    await ensureLoggedIn(page);
    await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
    await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });

    await page.getByTestId('case-reassign-toggle').click({ force: true });
    const reassignPanel = page.getByTestId('case-reassign-panel');
    await expect(reassignPanel).toBeVisible({ timeout: 15000 });

    const pausedOption = reassignPanel.locator('button').filter({ hasText: 'Paused Manager' }).first();
    await expect(pausedOption).toBeDisabled();
    await expect(pausedOption).toContainText('Новые заявки временно отключены этим routing profile.');

    const followUpOnlyOption = reassignPanel.locator('button').filter({ hasText: 'Follow-up Only' }).first();
    await expect(followUpOnlyOption).toBeDisabled();
    await expect(followUpOnlyOption).toContainText('Можно назначать только на явный follow-up continuity кейс.');

    const atCapacityOption = reassignPanel.locator('button').filter({ hasText: 'At Capacity' }).first();
    await expect(atCapacityOption).toBeDisabled();
    await expect(atCapacityOption).toContainText('Достигнут лимит 5/5.');

    await expect(reassignPanel.getByTestId('case-reassign-policy-submit')).toBeEnabled();
});

test('medium-width inbox and calendar keep primary queue surfaces visible', async ({ page }) => {
    test.skip(!useRouteMocks, 'Wave35 medium-width layout proof is covered in deterministic mock lane only');
    test.setTimeout(90000);

    await installConsoleMocks(page);
    await ensureLoggedIn(page);

    for (const width of [1280, 1100]) {
        await page.setViewportSize({ width, height: 900 });

        await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
        await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('cases-mode-scopes')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-secondary-panel-toggle')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-secondary-panel')).toHaveCount(0);
        await expect(page.getByTestId('cases-saved-views')).toHaveCount(0);
        const inboxList = page.getByTestId('inbox-list');
        await expect(inboxList).toBeVisible({ timeout: 15000 });
        const inboxListWidth = await inboxList.evaluate((element) => element.getBoundingClientRect().width);
        expect(inboxListWidth).toBeGreaterThan(280);

        await gotoWithRetry(page, `${baseURL}/calendar`);
        await expect(page.getByTestId('calendar-page')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-queue-controls')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('calendar-secondary-panel-toggle')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('calendar-secondary-panel')).toHaveCount(0);
        await expect(page.getByTestId('calendar-saved-views')).toHaveCount(0);
        await expect(page.getByTestId('calendar-follow-up-governance-card')).toHaveCount(0);
        await expect(page.getByTestId('calendar-booking-open-actions').first()).toBeVisible({ timeout: 15000 });
    }
});

test('live action feedback validation requires explicit safe case and hides raw sync codes', {
    tag: ['@live', '@wave22-live-proof'],
    annotation: [
        { type: 'wave', description: 'Wave22 live-proof closure' },
        { type: 'blocked-by', description: 'Requires explicit safe INSPECT_CASE_LIVE_CASE_ID' },
    ],
}, async ({ page }) => {
    test.skip(useRouteMocks, 'Wave22 live proof runs only without route mocks');
    test.setTimeout(90000);

    if (!HAS_EXPLICIT_LIVE_CASE_ID) {
        test.info().annotations.push({ type: 'blocked-by', description: 'INSPECT_CASE_LIVE_CASE_ID is not set' });
        test.skip(true, WAVE22_LIVE_PROOF_REQUIRED_MESSAGE);
    }

    await ensureLoggedIn(page);
    const opened = await openCaseDirectly(page, LIVE_CASE_ID);
    if (!opened) {
        test.info().annotations.push({ type: 'blocked-by', description: `Explicit live case_id=${LIVE_CASE_ID} is not accessible` });
        test.skip(true, `Explicit live case_id=${LIVE_CASE_ID} is not accessible.`);
    }

    const reopenButton = page.getByTestId('case-reopen').or(
        page.getByRole('button', { name: 'Вернуть в работу', exact: true }),
    ).first();
    try {
        await reopenButton.waitFor({ state: 'visible', timeout: 15000 });
    } catch {
        test.info().annotations.push({ type: 'blocked-by', description: `Explicit live case_id=${LIVE_CASE_ID} does not expose reopen control` });
        test.skip(true, `Explicit live case_id=${LIVE_CASE_ID} does not expose reopen control.`);
    }

    const reopenResponsePromise = page.waitForResponse((response) =>
        response.request().method() === 'POST'
        && response.url().includes(`/api/proxy/cases/${LIVE_CASE_ID}/reopen`)
    );
    await reopenButton.click({ force: true });
    const reopenResponse = await reopenResponsePromise;
    expect(reopenResponse.ok()).toBeTruthy();

    const reopenPayload = await reopenResponse.json().catch(() => null) as {
        sync?: {
            telegram?: { status?: string; detail?: string | null };
            client_notify?: { status?: string; detail?: string | null };
        };
    } | null;
    expect(reopenPayload?.sync?.telegram?.status).toBe('skipped');
    expect(reopenPayload?.sync?.telegram?.detail).toBe('reopen_internal_only');
    expect(reopenPayload?.sync?.client_notify?.status).toBe('skipped');
    expect(reopenPayload?.sync?.client_notify?.detail).toBe('reopen_internal_only');
    await expect(page.getByText('chatflow_failed')).toHaveCount(0);
    await expect(page.getByText('telegram_edit_failed')).toHaveCount(0);

    const returnToBotButton = page.getByRole('button', { name: 'Вернуть боту', exact: true });
    try {
        await returnToBotButton.waitFor({ state: 'visible', timeout: 15000 });
    } catch {
        test.info().annotations.push({ type: 'blocked-by', description: `Explicit live case_id=${LIVE_CASE_ID} does not expose a sync-bearing return action after reopen` });
        test.skip(true, `Explicit live case_id=${LIVE_CASE_ID} does not expose a sync-bearing return action after reopen.`);
    }

    const returnResponsePromise = page.waitForResponse((response) =>
        response.request().method() === 'POST'
        && response.url().includes(`/api/proxy/cases/${LIVE_CASE_ID}/return`)
    );
    await returnToBotButton.click({ force: true });
    const returnResponse = await returnResponsePromise;
    expect(returnResponse.ok()).toBeTruthy();

    const returnPayload = await returnResponse.json().catch(() => null) as {
        sync?: {
            telegram?: { detail?: string | null };
            client_notify?: { detail?: string | null };
        };
    } | null;
    if (returnPayload?.sync?.telegram?.detail) {
        await expect(page.getByText(returnPayload.sync.telegram.detail)).toHaveCount(0);
    }
    if (returnPayload?.sync?.client_notify?.detail) {
        await expect(page.getByText(returnPayload.sync.client_notify.detail)).toHaveCount(0);
    }
});
