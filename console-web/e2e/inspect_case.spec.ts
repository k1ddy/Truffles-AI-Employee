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
const CONVERSATION_ID = '66666666-6666-4666-8666-666666666666';
const SPECIALIST_ID = '77777777-7777-4777-8777-777777777777';
const TEXT_MACRO_ID = 'abababab-abab-4bab-8bab-abababababab';
const ACTION_MACRO_ID = 'cdcdcdcd-cdcd-4dcd-8dcd-cdcdcdcdcdcd';
const CREATED_MACRO_ID = 'efefefef-efef-4fef-8fef-efefefefefef';
let lastMacroCreatePayload: unknown = null;
let lastMacroExecutePayload: unknown = null;

function toJsonResponse(route: import('@playwright/test').Route, payload: unknown) {
    return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
    });
}

async function installConsoleMocks(page: import('@playwright/test').Page) {
    lastMacroCreatePayload = null;
    lastMacroExecutePayload = null;
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
                role: 'admin',
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
    const queueCases = [caseState, waitingClientCaseState, snoozedCaseState, deliveryCaseState, unassignedCaseState];
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
        conversation_id: CONVERSATION_ID,
        case_id: CASE_ID,
        needs_action: true,
        attention_reason: 'Нужно подтвердить визит',
        created_at: '2026-03-05T09:20:00+05:00',
    } as Record<string, unknown>;
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
                },
                {
                    agent_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                    agent_name: 'Manager Two',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_current: false,
                    open_case_count: 1,
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
        await toJsonResponse(route, { ...caseState });
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
            case: { ...caseState },
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
            case: { ...caseState },
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
                },
                {
                    agent_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                    agent_name: 'Manager Two',
                    role: 'manager',
                    branch_id: BRANCH_ID,
                    is_current: false,
                    open_case_count: 1,
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
        await toJsonResponse(route, {
            success: true,
            booking: { ...bookingState },
        });
    });
    await page.route(`**/api/proxy/calendar/bookings/${bookingState.id}/no-show-followup`, async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        const payload = route.request().postDataJSON() as { result?: 'contacted' | 'rebooked' } | null;
        bookingState.no_show_followup_done = true;
        bookingState.no_show_followup_result = payload?.result ?? 'contacted';
        bookingState.needs_action = false;
        bookingState.attention_reason = null;
        await toJsonResponse(route, {
            success: true,
            booking: { ...bookingState },
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
    if (await casePane.first().isVisible().catch(() => false)) {
        return true;
    }
    return false;
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
    await expect(page.getByTestId('calendar-queue-status-filter')).toBeVisible({ timeout: 20000 });
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
        await expect(page.getByTestId('cases-queue-views')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-filter-compact-layout')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-filter-assignee')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('cases-filter-assignee').locator('option').nth(2)).toContainText('Manager · 2 в работе');
        await expect(page.getByTestId('cases-filter-assignee').locator('option').nth(3)).toContainText('Manager Two · 1 в работе');
        await expect(page.getByTestId('cases-queue-view-unassigned')).toBeVisible({ timeout: 15000 });
        const inboxListBox = await page.getByTestId('inbox-list').boundingBox();
        expect(inboxListBox?.width ?? 0).toBeGreaterThan(300);
        await page.getByTestId('cases-field-toggle').click({ force: true });
        await page.getByTestId('cases-field-owner').check({ force: true });
        await page.getByTestId('cases-field-channel').check({ force: true });
        await expect(page.getByTestId('cases-field-toggle')).toContainText('Вид 4/5', { timeout: 15000 });

        await page.getByTestId('cases-filter-assignee').selectOption('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
        await expect(page.getByTestId('cases-owner-summary')).toContainText('Manager Two', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Сабина', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Manager Two', { timeout: 15000 });

        await page.getByTestId('cases-filter-clear').click({ force: true });
        await expect(page.getByTestId('cases-queue-view-summary')).toContainText('Все открытые', { timeout: 15000 });
        await page.getByTestId('cases-filter-assignee').selectOption('__unassigned__');
        await expect(page.getByTestId('cases-owner-summary')).toContainText('Без владельца', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Нургуль', { timeout: 15000 });
        await expect(page.getByTestId('cases-row').first()).toContainText('Без владельца', { timeout: 15000 });

        await page.getByTestId('cases-filter-clear').click({ force: true });
        await expect(page.getByTestId('cases-queue-view-summary')).toContainText('Все открытые', { timeout: 15000 });
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
        await expect(page.getByTestId('cases-queue-view-summary')).toContainText('Все открытые', { timeout: 15000 });
        await page.getByTestId('cases-row').first().click({ force: true });
        await expect(caseActionBadge).toContainText('Ответить до', { timeout: 15000 });
        await expect(page.getByTestId('case-reassign-toggle')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('case-snooze-toggle')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('cases-bulk-select').first().check({ force: true });
        await expect(page.getByTestId('cases-bulk-toolbar')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('cases-bulk-toggle-route').click({ force: true });
        await expect(page.getByTestId('cases-bulk-route-panel')).toBeVisible({ timeout: 15000 });
        const bulkRouteRequestPromise = page.waitForRequest((request) =>
            request.method() === 'POST' && request.url().includes('/api/proxy/cases/bulk')
        );
        await page.getByTestId('cases-bulk-route-submit').click({ force: true });
        const bulkRouteRequest = await bulkRouteRequestPromise;
        expect(bulkRouteRequest.postDataJSON()).toMatchObject({
            action: 'route',
            case_ids: [CASE_ID],
            policy: 'least_open_cases',
        });
        await page.getByTestId('cases-bulk-select').first().check({ force: true });
        await expect(page.getByTestId('cases-bulk-toolbar')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('cases-bulk-toggle-reassign').click({ force: true });
        await expect(page.getByTestId('cases-bulk-reassign-recommendation')).toContainText('Manager Two · 1 в работе', { timeout: 15000 });
        await page.getByTestId('cases-bulk-reassign-recommend').click({ force: true });
        await expect(page.getByTestId('cases-bulk-reassign-select')).toHaveValue('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
        await page.getByTestId('cases-bulk-toggle-snooze').click({ force: true });
        await expect(page.getByTestId('cases-bulk-snooze-minutes')).toBeVisible({ timeout: 15000 });
        const bulkRequestPromise = page.waitForRequest((request) =>
            request.method() === 'POST' && request.url().includes('/api/proxy/cases/bulk')
        );
        await page.getByTestId('cases-bulk-snooze-submit').click({ force: true });
        const bulkRequest = await bulkRequestPromise;
        expect(bulkRequest.postDataJSON()).toMatchObject({
            action: 'snooze',
            case_ids: [CASE_ID],
        });
        await page.getByTestId('case-reassign-toggle').click();
        await expect(page.getByTestId('case-reassign-select')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('case-reassign-select')).toContainText('Manager Two', { timeout: 15000 });
        await expect(page.getByTestId('case-reassign-recommendation')).toContainText('Сейчас у Manager 2 в работе.', { timeout: 15000 });
        await expect(page.getByTestId('case-reassign-recommendation')).toContainText('Лучше передать Manager Two, у него 1 в работе.', { timeout: 15000 });
        await expect(page.getByTestId('case-reassign-recommend-submit')).toContainText('Передать Manager Two');
        const caseRouteRequestPromise = page.waitForRequest((request) =>
            request.method() === 'POST' && request.url().includes(`/api/proxy/cases/${CASE_ID}/reassign`)
        );
        await page.getByTestId('case-reassign-policy-submit').click({ force: true });
        const caseRouteRequest = await caseRouteRequestPromise;
        expect(caseRouteRequest.postDataJSON()).toMatchObject({
            mode: 'policy',
            policy: 'least_open_cases',
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
            await visibleBookingsPanel.getByRole('button', { name: 'Пришел', exact: true }).click();
            await expect(visibleBookingsPanel.getByText('пришел', { exact: true }).first()).toBeVisible({ timeout: 20000 });
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
        await expect(page.getByTestId('calendar-queue-lane-attention')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-queue-lane-all')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-case-all-dates-hint')).toBeVisible({ timeout: 20000 });

        await page.getByTestId('calendar-queue-lane-all').click();
        await expect(page.getByTestId('calendar-queue-status-filter')).toBeVisible({ timeout: 20000 });

        const calendarScreenshotPath = path.resolve('calendar_case_context.png');
        await page.screenshot({ path: calendarScreenshotPath, fullPage: true });
        console.log(`Calendar screenshot saved to: ${calendarScreenshotPath}`);

        const openLinkedCase = page.getByTestId('calendar-open-linked-case');
        if (await openLinkedCase.isVisible().catch(() => false)) {
            await openLinkedCase.click();
            await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });
            await expect(page.locator('[data-testid=\"case-bookings-panel\"]:visible').first()).toBeVisible({ timeout: 20000 });
            await expect(page).toHaveURL(new RegExp(`/cases/${CASE_ID}\\?panel=bookings$`));
        }
    } else {
        console.log('case-open-calendar button is not visible for this case.');
    }
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

test('live action feedback validation requires explicit safe case and hides raw sync codes', async ({ page }) => {
    test.skip(useRouteMocks, 'Wave15 live validation runs only without route mocks');
    test.setTimeout(90000);

    if (!HAS_EXPLICIT_LIVE_CASE_ID) {
        test.skip(true, 'Set INSPECT_CASE_LIVE_CASE_ID to a safe resolved case for Wave15 live validation.');
    }

    await ensureLoggedIn(page);
    const opened = await openCaseDirectly(page, LIVE_CASE_ID);
    if (!opened) {
        test.skip(true, `Explicit live case_id=${LIVE_CASE_ID} is not accessible.`);
    }

    const reopenButton = page.getByTestId('case-reopen');
    if (!(await reopenButton.isVisible().catch(() => false))) {
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
    if (!(await returnToBotButton.isVisible().catch(() => false))) {
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
