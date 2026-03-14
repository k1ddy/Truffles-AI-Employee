import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { test, expect, type Page, type Route } from '@playwright/test';
import { isAuthGateVisible, loginThroughKeycloak, shouldAllowLocalSessionBridge } from './support/keycloak-auth';
import {
    CALENDAR_BOOKING_ACTION_SCENARIO_MATRIX,
    buildCalendarBookingActionAvailabilityMap,
    getCalendarActorClassForRole,
    getCalendarActionPermissionsForActor,
    type CalendarBlockedReasonCode,
    type CalendarBookingActionId,
} from '../src/lib/calendar-action-registry';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const consoleHostPattern = /localhost:3000|localhost:3100|192\.168\.5\.27:3000|console\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const useRouteMocks = process.env.INSPECT_CASE_USE_MOCKS !== '0';
const captureDir = process.env.CALENDAR_OPERATOR_CAPTURE_DIR?.trim() || '';

const COMPANY_ID = '11111111-1111-4111-8111-111111111111';
const CLIENT_ID = '22222222-2222-4222-8222-222222222222';
const BRANCH_ID = '33333333-3333-4333-8333-333333333333';
const AGENT_ID = '44444444-4444-4444-8444-444444444444';
const CASE_ID = '55555555-5555-4555-8555-555555555555';
const CONVERSATION_ID = '66666666-6666-4666-8666-666666666666';
const SPECIALIST_ID = '77777777-7777-4777-8777-777777777777';
const SECOND_SPECIALIST_ID = '88888888-8888-4888-8888-888888888888';
const MANAGER_TWO_AGENT_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const COORDINATOR_AGENT_ID = 'abababab-1111-4bab-8bab-ababababab11';
const TECHNICAL_ADMIN_AGENT_ID = '99999999-aaaa-4999-8aaa-999999999999';
const TECHNICAL_CI_AGENT_ID = '99999999-bbbb-4999-8bbb-999999999999';
const NO_SHOW_BOOKING_ID = '98989898-9898-4989-8989-989898989898';
const LINKED_REBOOK_BOOKING_ID = '97979797-9797-4979-8979-979797979797';
const COMPLETED_BOOKING_ID = '96969696-9696-4969-8969-969696969696';
const CANCELLED_BOOKING_ID = '95959595-9595-4959-8959-959595959595';

type MockViewerRole = 'admin' | 'manager' | 'owner' | 'consultant_bot';

type MockSpecialist = {
    id: string;
    name: string;
    branch_id: string;
    branch_name: string;
    services: Array<{ name: string; duration_min: number; price: number }>;
    is_active: boolean;
};

type MockBooking = {
    id: string;
    specialist_id: string;
    specialist_name: string;
    start_at: string;
    end_at: string;
    customer_name: string | null;
    customer_phone: string | null;
    service_type: string | null;
    notes?: string | null;
    status: string;
    no_show_followup_done?: boolean;
    no_show_followup_result?: 'contacted' | 'rebooked' | null;
    no_show_followup_closed_at?: string | null;
    no_show_followup_closed_by?: string | null;
    no_show_followup_rebooked_appointment_id?: string | null;
    follow_up_owner_id?: string | null;
    follow_up_owner_name?: string | null;
    follow_up_due_at?: string | null;
    follow_up_overdue?: boolean;
    conversation_id?: string | null;
    case_id?: string | null;
    needs_action?: boolean;
    attention_reason?: string | null;
    version: number;
    created_at: string;
    last_actor_type?: string | null;
};

type CalendarOperatorMockOptions = {
    viewerRole?: MockViewerRole;
    emptySlotDates?: string[];
    slotErrorDates?: string[];
    includeHistoricalStatuses?: boolean;
    slowCreateMs?: number;
    slowCancelMs?: number;
};

function deepClone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
}

function sortActionIds(actionIds: string[]) {
    return [...actionIds].sort((left, right) => left.localeCompare(right));
}

function toJsonResponse(route: Route, payload: unknown) {
    return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
    });
}

function toErrorResponse(route: Route, status: number, code: string, message: string) {
    return route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify({
            error: {
                code,
                message,
            },
        }),
    });
}

function formatMockDate(value: Date) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function shiftDate(date: string, days: number) {
    return formatMockDate(new Date(new Date(`${date}T00:00:00+05:00`).getTime() + days * 24 * 60 * 60 * 1000));
}

function buildMockDateTime(date: string, hours: number, minutes: number) {
    const paddedHours = String(hours).padStart(2, '0');
    const paddedMinutes = String(minutes).padStart(2, '0');
    return `${date}T${paddedHours}:${paddedMinutes}:00+05:00`;
}

function normalizeMockCalendarPhone(value: unknown): string | null {
    const rawValue = String(value ?? '').trim();
    const digits = rawValue.replace(/\D/g, '');
    if (digits.length === 10) {
        if (rawValue.startsWith('+') || /^7(?:[\s().-]|$)/.test(rawValue) || /^8(?:[\s().-]|$)/.test(rawValue)) {
            return null;
        }
        return `+7${digits}`;
    }
    if (digits.length === 11 && digits.startsWith('7')) {
        return `+${digits}`;
    }
    if (digits.length === 11 && digits.startsWith('8')) {
        return `+7${digits.slice(1)}`;
    }
    return null;
}

function formatPhoneForUi(value: string | null | undefined) {
    const digits = String(value ?? '').replace(/\D/g, '');
    if (!digits) {
        return '';
    }
    const normalized = digits.length === 10
        ? `7${digits}`
        : digits.length >= 11 && digits.startsWith('8')
            ? `7${digits.slice(1)}`
            : digits.length >= 11 && !digits.startsWith('7')
                ? `7${digits.slice(-10)}`
                : digits;
    const limited = normalized.slice(0, 11);
    const country = limited.slice(0, 1);
    const area = limited.slice(1, 4);
    const first = limited.slice(4, 7);
    const second = limited.slice(7, 9);
    const third = limited.slice(9, 11);
    return [`+${country}`, area, first, second, third].filter(Boolean).join(' ');
}

function mockBookingNeedsAttention(booking: MockBooking) {
    if (typeof booking.needs_action === 'boolean') {
        return booking.needs_action;
    }
    const normalizedStatus = String(booking.status || '').toUpperCase();
    if (normalizedStatus === 'NO_SHOW' && !booking.no_show_followup_done) {
        return true;
    }
    return ['PENDING_CONFIRMATION', 'RESCHEDULE_REQUESTED', 'NO_SHOW', 'HOLD'].includes(normalizedStatus);
}

function getAgentDisplayName(agentId: string | null | undefined) {
    if (!agentId) {
        return null;
    }
    if (agentId === AGENT_ID) {
        return 'Manager';
    }
    if (agentId === MANAGER_TWO_AGENT_ID) {
        return 'Manager Two';
    }
    if (agentId === COORDINATOR_AGENT_ID) {
        return 'Coordinator Dana';
    }
    if (agentId === TECHNICAL_ADMIN_AGENT_ID) {
        return 'admin console';
    }
    if (agentId === TECHNICAL_CI_AGENT_ID) {
        return 'ci-console';
    }
    return null;
}

function matchesStatusFilter(booking: MockBooking, status: string | null) {
    if (!status || status === 'all') {
        return true;
    }
    const normalized = booking.status.toUpperCase();
    if (status === 'no_show') {
        return normalized === 'NO_SHOW';
    }
    if (status === 'completed') {
        return normalized === 'COMPLETED';
    }
    if (status === 'cancelled') {
        return normalized === 'CANCELLED';
    }
    if (status === 'scheduled') {
        return !['COMPLETED', 'NO_SHOW', 'CANCELLED'].includes(normalized);
    }
    return true;
}

function buildSlotsForRequest(date: string, specialistId: string) {
    if (specialistId === SPECIALIST_ID) {
        return [
            {
                start: buildMockDateTime(date, 10, 0),
                end: buildMockDateTime(date, 11, 0),
                start_time: '10:00',
                end_time: '11:00',
                available: true,
            },
            {
                start: buildMockDateTime(date, 11, 30),
                end: buildMockDateTime(date, 12, 30),
                start_time: '11:30',
                end_time: '12:30',
                available: true,
            },
        ];
    }
    return [
        {
            start: buildMockDateTime(date, 14, 0),
            end: buildMockDateTime(date, 15, 0),
            start_time: '14:00',
            end_time: '15:00',
            available: true,
        },
    ];
}

async function maybeCapture(page: Page, name: string) {
    if (!captureDir) {
        return;
    }
    mkdirSync(captureDir, { recursive: true });
    await page.screenshot({
        path: join(captureDir, `${name}.png`),
        fullPage: true,
    });
}

function buildMockServerActionContract(booking: MockBooking, viewerRole: MockViewerRole) {
    const actorClass = getCalendarActorClassForRole(viewerRole);
    const permissions = getCalendarActionPermissionsForActor(actorClass);
    const availabilityMap = buildCalendarBookingActionAvailabilityMap(
        {
            status: booking.status,
            no_show_followup_done: booking.no_show_followup_done,
            case_id: booking.case_id,
        },
        permissions,
        actorClass,
    );
    const allowedActions = Object.values(availabilityMap)
        .filter((action) => action.state === 'enabled')
        .map((action) => action.id);
    const blockedActions = Object.values(availabilityMap)
        .filter((action) => Boolean(action.blockedReasonCode))
        .map((action) => ({
            action_id: action.id as CalendarBookingActionId,
            reason_code: action.blockedReasonCode as CalendarBlockedReasonCode,
        }));
    return {
        allowed_actions: allowedActions,
        blocked_actions: blockedActions,
    };
}

function serializeBookingForViewer(booking: MockBooking, viewerRole: MockViewerRole) {
    return {
        ...deepClone(booking),
        ...buildMockServerActionContract(booking, viewerRole),
        last_actor_type: booking.last_actor_type ?? 'agent',
    };
}

async function installCalendarOperatorMocks(page: Page, options: CalendarOperatorMockOptions = {}) {
    const viewerRole = options.viewerRole ?? 'owner';
    const today = formatMockDate(new Date());
    const emptySlotDates = new Set(options.emptySlotDates ?? []);
    const slotFailuresRemaining = new Map<string, number>((options.slotErrorDates ?? []).map((date) => [date, 2]));
    const slowCreateMs = Math.max(0, options.slowCreateMs ?? 0);
    const slowCancelMs = Math.max(0, options.slowCancelMs ?? 0);
    const specialists: MockSpecialist[] = [
        {
            id: SPECIALIST_ID,
            name: 'Мастер Айжан',
            branch_id: BRANCH_ID,
            branch_name: 'Almaty Downtown',
            services: [
                { name: 'Маникюр', duration_min: 60, price: 7000 },
                { name: 'Педикюр', duration_min: 90, price: 9000 },
            ],
            is_active: true,
        },
        {
            id: SECOND_SPECIALIST_ID,
            name: 'Мастер Алина',
            branch_id: BRANCH_ID,
            branch_name: 'Almaty Downtown',
            services: [
                { name: 'Маникюр', duration_min: 60, price: 7000 },
            ],
            is_active: true,
        },
    ];
    const caseState = {
        id: CASE_ID,
        conversation_id: CONVERSATION_ID,
        branch_id: BRANCH_ID,
        status: 'active',
        business_status_code: 'needs_reply',
        business_status_label: 'Нужен ответ',
        context_summary: 'Клиент хочет записаться на ближайшее свободное время.',
        user_message: 'Можно записаться на этой неделе?',
        created_at: '2026-03-05T09:00:00+05:00',
        assigned_to_id: AGENT_ID,
        assigned_to_name: 'Manager',
        customer_name: 'Айгуль',
        customer_phone: '+77001234567',
        last_inbound_at: '2026-03-05T09:10:00+05:00',
        last_activity_at: '2026-03-05T09:10:00+05:00',
        booking_summary: null,
    };
    const bookingStore: MockBooking[] = [
        {
            id: '99999999-9999-4999-8999-999999999999',
            specialist_id: SPECIALIST_ID,
            specialist_name: 'Мастер Айжан',
            start_at: buildMockDateTime(today, 10, 0),
            end_at: buildMockDateTime(today, 11, 0),
            customer_name: 'Айгуль',
            customer_phone: '+77001234567',
            service_type: 'Маникюр',
            notes: 'Позвонить за час',
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
            version: 1,
            created_at: '2026-03-05T09:20:00+05:00',
        },
        {
            id: NO_SHOW_BOOKING_ID,
            specialist_id: SPECIALIST_ID,
            specialist_name: 'Мастер Айжан',
            start_at: buildMockDateTime(today, 12, 30),
            end_at: buildMockDateTime(today, 13, 30),
            customer_name: 'Динара',
            customer_phone: '+77015554433',
            service_type: 'Педикюр',
            notes: null,
            status: 'NO_SHOW',
            no_show_followup_done: false,
            no_show_followup_result: null,
            no_show_followup_closed_at: null,
            no_show_followup_closed_by: null,
            no_show_followup_rebooked_appointment_id: null,
            follow_up_owner_id: TECHNICAL_ADMIN_AGENT_ID,
            follow_up_owner_name: 'admin console',
            follow_up_due_at: buildMockDateTime(today, 14, 0),
            follow_up_overdue: true,
            conversation_id: CONVERSATION_ID,
            case_id: CASE_ID,
            needs_action: true,
            attention_reason: 'Связаться после неявки',
            version: 3,
            created_at: '2026-03-05T09:25:00+05:00',
        },
        {
            id: LINKED_REBOOK_BOOKING_ID,
            specialist_id: SECOND_SPECIALIST_ID,
            specialist_name: 'Мастер Алина',
            start_at: buildMockDateTime(today, 15, 0),
            end_at: buildMockDateTime(today, 16, 0),
            customer_name: 'Динара',
            customer_phone: '+77015554433',
            service_type: 'Педикюр',
            notes: null,
            status: 'CONFIRMED',
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
            needs_action: false,
            attention_reason: null,
            version: 2,
            created_at: '2026-03-05T09:30:00+05:00',
        },
    ];
    if (options.includeHistoricalStatuses) {
        bookingStore.push(
            {
                id: COMPLETED_BOOKING_ID,
                specialist_id: SECOND_SPECIALIST_ID,
                specialist_name: 'Мастер Алина',
                start_at: buildMockDateTime(today, 16, 30),
                end_at: buildMockDateTime(today, 17, 30),
                customer_name: 'Ляззат',
                customer_phone: '+77017770011',
                service_type: 'Маникюр',
                notes: 'Визит закрыт',
                status: 'COMPLETED',
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
                needs_action: false,
                attention_reason: null,
                version: 4,
                created_at: '2026-03-05T09:35:00+05:00',
            },
            {
                id: CANCELLED_BOOKING_ID,
                specialist_id: SPECIALIST_ID,
                specialist_name: 'Мастер Айжан',
                start_at: buildMockDateTime(today, 18, 0),
                end_at: buildMockDateTime(today, 19, 0),
                customer_name: 'Назерке',
                customer_phone: '+77018889900',
                service_type: 'Педикюр',
                notes: 'Отмена подтверждена',
                status: 'CANCELLED',
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
                needs_action: false,
                attention_reason: null,
                version: 5,
                created_at: '2026-03-05T09:40:00+05:00',
            },
        );
    }
    let currentQueueState: Record<string, unknown> | null = null;
    let cancelRequestCount = 0;
    const operatorEvents: Array<{
        event_type: 'filter_apply' | 'filter_reset' | 'double_submit_blocked';
        action_id: string;
        surface: string;
        booking_id?: string;
    }> = [];

    await page.route(/.*\/api\/auth\/session(?:\?.*)?$/, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            user: { name: 'Manager', email: 'manager@truffles.local' },
            expires: '2099-01-01T00:00:00.000Z',
            accessToken: 'calendar-operator-token',
        });
    });
    await page.route(/.*\/api\/auth\/csrf(?:\?.*)?$/, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, { csrfToken: 'calendar-operator-csrf' });
    });
    await page.route(/.*\/api\/auth\/providers(?:\?.*)?$/, async (route) => {
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
    await page.route(/.*\/api\/proxy\/me(?:\?.*)?$/, async (route) => {
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
    await page.route(/.*\/api\/proxy\/agents(?:\?.*)?$/, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [
                { id: AGENT_ID, name: 'Manager', role: 'manager', branch_id: BRANCH_ID, is_active: true },
                { id: MANAGER_TWO_AGENT_ID, name: 'Manager Two', role: 'manager', branch_id: BRANCH_ID, is_active: true },
                { id: COORDINATOR_AGENT_ID, name: 'Coordinator Dana', role: 'manager', branch_id: BRANCH_ID, is_active: true },
                { id: TECHNICAL_ADMIN_AGENT_ID, name: 'admin console', role: 'manager', branch_id: BRANCH_ID, is_active: true },
                { id: TECHNICAL_CI_AGENT_ID, name: 'ci-console', role: 'manager', branch_id: BRANCH_ID, is_active: true },
            ],
        });
    });
    await page.route(/.*\/api\/proxy\/queue-state\/current(?:\?.*)?$/, async (route) => {
        const method = route.request().method();
        if (method === 'GET') {
            await toJsonResponse(route, {
                found: currentQueueState !== null,
                surface: 'calendar',
                query_state: deepClone(currentQueueState),
                updated_at: currentQueueState ? '2026-03-08T15:05:00+05:00' : null,
                version: 1,
            });
            return;
        }
        if (method === 'PUT') {
            const payload = route.request().postDataJSON() as Record<string, unknown> | null;
            currentQueueState = deepClone(payload?.query_state ?? null);
            await toJsonResponse(route, {
                success: true,
                found: true,
                surface: 'calendar',
                query_state: deepClone(currentQueueState),
                updated_at: '2026-03-08T15:05:00+05:00',
                version: Number(payload?.version ?? 1),
            });
            return;
        }
        await route.fallback();
    });
    await page.route(/.*\/api\/proxy\/queue-state\/views(?:\?.*)?$/, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, { items: [] });
    });
    await page.route(/.*\/api\/proxy\/calendar\/operator-events(?:\?.*)?$/, async (route) => {
        if (route.request().method() !== 'POST') {
            await route.fallback();
            return;
        }
        const payload = route.request().postDataJSON() as {
            event_type: 'filter_apply' | 'filter_reset' | 'double_submit_blocked';
            action_id: string;
            surface: string;
            booking_id?: string;
        } | null;
        if (!payload?.event_type || !payload?.action_id || !payload?.surface) {
            await toErrorResponse(route, 400, 'INVALID_PARAM', 'Operator event payload is invalid.');
            return;
        }
        operatorEvents.push({
            event_type: payload.event_type,
            action_id: payload.action_id,
            surface: payload.surface,
            booking_id: payload.booking_id,
        });
        await toJsonResponse(route, { success: true });
    });
    await page.route(new RegExp(`.*/api/proxy/cases/${CASE_ID}(?:\\?.*)?$`), async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, caseState);
    });
    await page.route(/.*\/api\/proxy\/calendar\/specialists(?:\?.*)?$/, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, { items: specialists });
    });
    await page.route(/.*\/api\/proxy\/calendar\/slots(?:\?.*)?$/, async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        const url = new URL(route.request().url());
        const date = url.searchParams.get('date') || today;
        const specialistId = url.searchParams.get('specialist_id') || SPECIALIST_ID;
        const remainingFailures = slotFailuresRemaining.get(date) ?? 0;
        if (remainingFailures > 0) {
            slotFailuresRemaining.set(date, remainingFailures - 1);
            await toErrorResponse(route, 503, 'SLOT_LOOKUP_FAILED', 'Не удалось получить свободное время. Повторите попытку.');
            return;
        }
        if (emptySlotDates.has(date)) {
            await toJsonResponse(route, { slots: [] });
            return;
        }
        await toJsonResponse(route, { slots: buildSlotsForRequest(date, specialistId) });
    });
    await page.route(/.*\/api\/proxy\/calendar\/bookings(?:\/[^?]+)?(?:\?.*)?$/, async (route) => {
        const method = route.request().method();
        const url = new URL(route.request().url());
        const pathname = url.pathname;
        if (method === 'GET' && pathname.endsWith('/calendar/bookings')) {
            const dateFrom = url.searchParams.get('date_from');
            const dateTo = url.searchParams.get('date_to');
            const lane = url.searchParams.get('lane');
            const status = url.searchParams.get('status');
            const followUpOwnerId = url.searchParams.get('follow_up_owner_id');
            const followUpOverdue = url.searchParams.get('follow_up_overdue') === 'true';
            const caseId = url.searchParams.get('case_id');
            const conversationId = url.searchParams.get('conversation_id');
            const items = bookingStore.filter((booking) => {
                const bookingDatePart = String(booking.start_at || '').slice(0, 10);
                if (dateFrom && bookingDatePart < dateFrom) {
                    return false;
                }
                if (dateTo && bookingDatePart > dateTo) {
                    return false;
                }
                if (caseId && booking.case_id !== caseId) {
                    return false;
                }
                if (conversationId && booking.conversation_id !== conversationId) {
                    return false;
                }
                if (followUpOwnerId && booking.follow_up_owner_id !== followUpOwnerId) {
                    return false;
                }
                if (followUpOverdue && !booking.follow_up_overdue) {
                    return false;
                }
                if (!matchesStatusFilter(booking, status)) {
                    return false;
                }
                if (lane === 'attention' && !mockBookingNeedsAttention(booking)) {
                    return false;
                }
                return true;
            });
            await toJsonResponse(route, { items: items.map((booking) => serializeBookingForViewer(booking, viewerRole)) });
            return;
        }
        if (method === 'POST' && pathname.endsWith('/calendar/bookings')) {
            const payload = route.request().postDataJSON() as {
                specialist_id?: string;
                start_at?: string;
                end_at?: string;
                customer_name?: string;
                customer_phone?: string;
                service_type?: string;
                notes?: string;
                case_id?: string;
                conversation_id?: string;
            } | null;
            const customerName = String(payload?.customer_name ?? '').trim();
            const normalizedPhone = normalizeMockCalendarPhone(payload?.customer_phone);
            const serviceType = String(payload?.service_type ?? '').trim();
            const specialist = specialists.find((item) => item.id === payload?.specialist_id);
            if (!specialist || !payload?.start_at || !payload?.end_at || customerName.length < 2 || !normalizedPhone || !serviceType) {
                await toErrorResponse(route, 400, 'VALIDATION_ERROR', 'Проверьте услугу, время и данные клиента.');
                return;
            }
            const newBooking: MockBooking = {
                id: `created-booking-${bookingStore.length + 1}`,
                specialist_id: specialist.id,
                specialist_name: specialist.name,
                start_at: payload.start_at,
                end_at: payload.end_at,
                customer_name: customerName,
                customer_phone: normalizedPhone,
                service_type: serviceType,
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
                conversation_id: payload?.conversation_id ?? null,
                case_id: payload?.case_id ?? null,
                needs_action: true,
                attention_reason: 'Нужно подтвердить визит',
                version: 1,
                created_at: '2026-03-08T15:30:00+05:00',
            };
            if (slowCreateMs > 0) {
                await new Promise((resolve) => setTimeout(resolve, slowCreateMs));
            }
            bookingStore.unshift(newBooking);
            await toJsonResponse(route, { success: true, booking: serializeBookingForViewer(newBooking, viewerRole), case_effects: [] });
            return;
        }
        const updateMatch = pathname.match(/\/calendar\/bookings\/([^/]+)$/);
        if (method === 'PATCH' && updateMatch) {
            const booking = bookingStore.find((item) => item.id === updateMatch[1]);
            if (!booking) {
                await toErrorResponse(route, 404, 'BOOKING_NOT_FOUND', 'Booking not found');
                return;
            }
            const payload = route.request().postDataJSON() as {
                specialist_id?: string;
                start_at?: string;
                end_at?: string;
                customer_name?: string;
                customer_phone?: string;
                service_type?: string;
                notes?: string;
                version?: number;
            } | null;
            if (Number(payload?.version ?? 0) !== booking.version) {
                await toErrorResponse(route, 409, 'BOOKING_VERSION_CONFLICT', 'Booking was changed by another action.');
                return;
            }
            if (!['HOLD', 'PENDING_CONFIRMATION', 'CONFIRMED', 'RESCHEDULE_REQUESTED', 'CHECKED_IN'].includes(String(booking.status || '').toUpperCase())) {
                await toErrorResponse(route, 409, 'BOOKING_UPDATE_DENIED', 'Booking edit is not allowed');
                return;
            }
            const customerName = String(payload?.customer_name ?? '').trim();
            const normalizedPhone = normalizeMockCalendarPhone(payload?.customer_phone);
            const serviceType = String(payload?.service_type ?? '').trim();
            const specialist = specialists.find((item) => item.id === payload?.specialist_id);
            if (!specialist || !payload?.start_at || !payload?.end_at || customerName.length < 2 || !normalizedPhone || !serviceType) {
                await toErrorResponse(route, 400, 'VALIDATION_ERROR', 'Проверьте услугу, время и данные клиента.');
                return;
            }
            booking.specialist_id = specialist.id;
            booking.specialist_name = specialist.name;
            booking.start_at = payload.start_at;
            booking.end_at = payload.end_at;
            booking.customer_name = customerName;
            booking.customer_phone = normalizedPhone;
            booking.service_type = serviceType;
            booking.notes = String(payload?.notes ?? '').trim() || null;
            booking.status = 'PENDING_CONFIRMATION';
            booking.needs_action = true;
            booking.attention_reason = 'Нужно подтвердить визит';
            booking.version += 1;
            await toJsonResponse(route, {
                success: true,
                booking: serializeBookingForViewer(booking, viewerRole),
                case_effects: [],
            });
            return;
        }
        const cancelMatch = pathname.match(/\/calendar\/bookings\/([^/]+)\/cancel$/);
        if (method === 'POST' && cancelMatch) {
            const booking = bookingStore.find((item) => item.id === cancelMatch[1]);
            if (!booking) {
                await toErrorResponse(route, 404, 'BOOKING_NOT_FOUND', 'Booking not found');
                return;
            }
            const payload = route.request().postDataJSON() as { version?: number } | null;
            if (Number(payload?.version ?? 0) !== booking.version) {
                await toErrorResponse(route, 409, 'BOOKING_VERSION_CONFLICT', 'Booking was changed by another action.');
                return;
            }
            if (!['HOLD', 'PENDING_CONFIRMATION', 'CONFIRMED', 'RESCHEDULE_REQUESTED', 'CHECKED_IN'].includes(String(booking.status || '').toUpperCase())) {
                await toErrorResponse(route, 409, 'BOOKING_CANCEL_DENIED', 'Booking cancellation is not allowed');
                return;
            }
            cancelRequestCount += 1;
            if (slowCancelMs > 0) {
                await new Promise((resolve) => setTimeout(resolve, slowCancelMs));
            }
            booking.status = 'CANCELLED';
            booking.needs_action = false;
            booking.attention_reason = null;
            booking.version += 1;
            await toJsonResponse(route, { success: true, booking: serializeBookingForViewer(booking, viewerRole), case_effects: [] });
            return;
        }
        const statusMatch = pathname.match(/\/calendar\/bookings\/([^/]+)\/status$/);
        if (method === 'POST' && statusMatch) {
            const booking = bookingStore.find((item) => item.id === statusMatch[1]);
            if (!booking) {
                await toErrorResponse(route, 404, 'NOT_FOUND', 'Booking not found');
                return;
            }
            const payload = route.request().postDataJSON() as { status?: 'COMPLETED' | 'NO_SHOW'; version?: number } | null;
            if (Number(payload?.version ?? 0) !== booking.version) {
                await toErrorResponse(route, 409, 'BOOKING_VERSION_CONFLICT', 'Booking was changed by another action.');
                return;
            }
            booking.status = payload?.status ?? booking.status;
            booking.needs_action = booking.status === 'NO_SHOW';
            booking.attention_reason = booking.status === 'NO_SHOW' ? 'Связаться после неявки' : null;
            booking.version += 1;
            await toJsonResponse(route, { success: true, booking: serializeBookingForViewer(booking, viewerRole), case_effects: [] });
            return;
        }
        const followUpMatch = pathname.match(/\/calendar\/bookings\/([^/]+)\/no-show-followup$/);
        if (method === 'POST' && followUpMatch) {
            const booking = bookingStore.find((item) => item.id === followUpMatch[1]);
            if (!booking) {
                await toErrorResponse(route, 404, 'NOT_FOUND', 'Booking not found');
                return;
            }
            const payload = route.request().postDataJSON() as {
                result?: 'contacted' | 'rebooked';
                rebooked_appointment_id?: string;
                note?: string;
                version?: number;
            } | null;
            if (Number(payload?.version ?? 0) !== booking.version) {
                await toErrorResponse(route, 409, 'BOOKING_VERSION_CONFLICT', 'Booking was changed by another action.');
                return;
            }
            if (payload?.result === 'rebooked' && !payload?.rebooked_appointment_id) {
                await toErrorResponse(route, 400, 'FOLLOW_UP_REBOOK_REQUIRES_LINKED_BOOKING', 'Выберите новую запись, чтобы закрыть неявку как переписанную.');
                return;
            }
            booking.no_show_followup_done = true;
            booking.no_show_followup_result = payload?.result ?? 'contacted';
            booking.no_show_followup_closed_at = '2026-03-08T16:00:00+05:00';
            booking.no_show_followup_closed_by = 'Manager';
            booking.no_show_followup_rebooked_appointment_id = payload?.rebooked_appointment_id ?? null;
            booking.needs_action = false;
            booking.attention_reason = null;
            booking.version += 1;
            await toJsonResponse(route, {
                success: true,
                booking: serializeBookingForViewer(booking, viewerRole),
                case_effects: payload?.result === 'rebooked'
                    ? [{ case_id: CASE_ID, action: 'linked_rebooked_booking', message: 'Новая запись привязана к заявке.' }]
                    : [{ case_id: CASE_ID, action: 'reopened_for_booking_attention', message: 'После неявки клиенту нужно ответить.' }],
            });
            return;
        }
        const governanceMatch = pathname.match(/\/calendar\/bookings\/([^/]+)\/follow-up-governance$/);
        if (method === 'POST' && governanceMatch) {
            const booking = bookingStore.find((item) => item.id === governanceMatch[1]);
            if (!booking) {
                await toErrorResponse(route, 404, 'NOT_FOUND', 'Booking not found');
                return;
            }
            const payload = route.request().postDataJSON() as { owner_agent_id?: string | null; due_at?: string | null; version?: number } | null;
            if (Number(payload?.version ?? 0) !== booking.version) {
                await toErrorResponse(route, 409, 'BOOKING_VERSION_CONFLICT', 'Booking was changed by another action.');
                return;
            }
            booking.follow_up_owner_id = payload?.owner_agent_id ?? null;
            booking.follow_up_owner_name = getAgentDisplayName(payload?.owner_agent_id ?? null);
            booking.follow_up_due_at = payload?.due_at ?? null;
            booking.follow_up_overdue = Boolean(booking.follow_up_due_at && booking.follow_up_due_at < '2026-03-08T16:30:00+05:00');
            booking.version += 1;
            await toJsonResponse(route, { success: true, booking: serializeBookingForViewer(booking, viewerRole), case_effects: [] });
            return;
        }
        await route.fallback();
    });

    return {
        getCurrentQueueState: () => deepClone(currentQueueState),
        getCancelRequestCount: () => cancelRequestCount,
        getOperatorEvents: () => deepClone(operatorEvents),
    };
}

async function gotoWithRetry(page: Page, url: string, attempts = 3) {
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

async function selectOptionIfNeeded(selector: ReturnType<Page['getByTestId']>) {
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

async function resolveTenantSelection(page: Page) {
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

async function ensureCalendarReady(page: Page, url: string) {
    await gotoWithRetry(page, url);
    const calendarPage = page.getByTestId('calendar-page');
    if (await calendarPage.isVisible().catch(() => false)) {
        return;
    }

    if (useRouteMocks) {
        const retryButton = page.getByRole('button', { name: /повторить/i });
        const loginButton = page.getByTestId('login-button').or(page.getByRole('button', { name: /войти через sso/i })).first();
        const loadingProfile = page.getByText('Загрузка профиля...');
        for (let cycle = 0; cycle < 3; cycle += 1) {
            await resolveTenantSelection(page);
            for (let attempt = 0; attempt < 3; attempt += 1) {
                if (await retryButton.isVisible().catch(() => false)) {
                    await retryButton.click();
                    await page.waitForTimeout(250);
                }
            }
            if (await calendarPage.isVisible().catch(() => false)) {
                return;
            }
            const shouldReload = await loginButton.isVisible().catch(() => false)
                || await loadingProfile.isVisible().catch(() => false)
                || await isAuthGateVisible(page).catch(() => false);
            if (shouldReload) {
                await gotoWithRetry(page, url);
            }
        }
        await expect(calendarPage).toBeVisible({ timeout: 20000 });
        return;
    }

    const loginButton = page.getByTestId('login-button').or(page.getByRole('button', { name: /войти/i })).first();
    if (await loginButton.isVisible().catch(() => false)) {
        await loginThroughKeycloak(page, {
            baseURL,
            consoleHostPattern,
            allowLocalSessionBridge: shouldAllowLocalSessionBridge(baseURL),
            loginUser,
            loginPassword,
            authWaitTimeoutMs: 20000,
        });
        await gotoWithRetry(page, url);
    }
    await resolveTenantSelection(page);
    await expect(calendarPage).toBeVisible({ timeout: 20000 });
}

async function openCalendarSecondaryPanel(page: Page, section: 'filters' | 'saved_views' | 'scheduling') {
    if (section === 'scheduling') {
        const composer = page.getByTestId('calendar-booking-composer');
        if (!(await composer.isVisible().catch(() => false))) {
            await page.getByTestId('calendar-scheduling-panel-toggle').click({ force: true });
            await expect(composer).toBeVisible({ timeout: 15000 });
        }
        return;
    }
    const panel = page.getByTestId('calendar-secondary-panel');
    if (!(await panel.isVisible().catch(() => false))) {
        const toggleBySection = {
            filters: 'calendar-secondary-panel-toggle',
            saved_views: 'calendar-saved-views-panel-toggle',
        } as const;
        await page.getByTestId(toggleBySection[section]).click({ force: true });
        await expect(panel).toBeVisible({ timeout: 15000 });
    }
    await page.getByTestId(`calendar-secondary-tab-${section}`).click({ force: true });
}

async function closeCalendarSecondaryPanel(page: Page) {
    const panel = page.getByTestId('calendar-secondary-panel');
    if (await panel.isVisible().catch(() => false)) {
        await page.getByTestId('calendar-secondary-panel-close').click({ force: true });
        await expect(panel).toHaveCount(0);
    }
}

async function openCalendarBookingActionsByText(page: Page, text: string) {
    const card = page.getByTestId('calendar-booking-card').filter({ hasText: text }).first();
    await expect(card).toBeVisible({ timeout: 15000 });
    await card.getByTestId('calendar-booking-open-actions').click({ force: true });
    const panel = page.getByTestId('calendar-booking-panel');
    await expect(panel).toBeVisible({ timeout: 15000 });
    return panel;
}

test.describe('calendar operator workflow', () => {
    test.describe.configure({ mode: 'serial' });

    test('calendar action registry stays aligned with actor and status matrix', () => {
        for (const scenario of CALENDAR_BOOKING_ACTION_SCENARIO_MATRIX) {
            const actionMap = buildCalendarBookingActionAvailabilityMap(
                {
                    status: scenario.booking.status,
                    no_show_followup_done: scenario.booking.no_show_followup_done,
                    case_id: scenario.booking.case_id,
                },
                getCalendarActionPermissionsForActor(scenario.actorClass),
                scenario.actorClass,
            );
            const enabled = sortActionIds(
                Object.values(actionMap)
                    .filter((action) => action.state === 'enabled')
                    .map((action) => action.id),
            );
            const disabled = sortActionIds(
                Object.values(actionMap)
                    .filter((action) => action.state === 'disabled')
                    .map((action) => action.id),
            );
            const hidden = sortActionIds(
                Object.values(actionMap)
                    .filter((action) => action.state === 'hidden')
                    .map((action) => action.id),
            );

            expect(enabled, `${scenario.id} enabled`).toEqual(sortActionIds([...scenario.expectedEnabled]));
            expect(disabled, `${scenario.id} disabled`).toEqual(sortActionIds([...scenario.expectedDisabled]));
            expect(hidden, `${scenario.id} hidden`).toEqual(sortActionIds([...scenario.expectedHidden]));

            if (scenario.expectedDisabled.includes('edit_booking')) {
                expect(actionMap.edit_booking.blockedReasonCode, `${scenario.id} edit reason`).toBe('active_status_only');
            }
            if (scenario.expectedDisabled.includes('cancel_booking')) {
                expect(actionMap.cancel_booking.blockedReasonCode, `${scenario.id} cancel reason`).toBe('active_status_only');
            }
            if (scenario.actorClass === 'consultant_bot') {
                expect(actionMap.edit_booking.blockedReasonCode, `${scenario.id} permission reason`).toBeUndefined();
            }
            if (scenario.booking.case_id === null) {
                expect(actionMap.open_case_from_booking.blockedReasonCode, `${scenario.id} case-link reason`).toBe('case_link_required');
            }
        }
    });

    test('calendar filters stay in draft until apply and reset back to the applied state', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        const today = formatMockDate(new Date());
        const mocks = await installCalendarOperatorMocks(page);
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.setViewportSize({ width: 1280, height: 1180 });
        const visibleCards = page.getByTestId('calendar-booking-card');
        await expect(visibleCards).toHaveCount(2, { timeout: 15000 });
        await expect.poll(() => mocks.getCurrentQueueState()).toBeNull();
        await maybeCapture(page, 'wave39-queue-default-1280');
        await page.setViewportSize({ width: 1440, height: 1180 });
        await maybeCapture(page, 'wave39-queue-default-1440');
        await page.setViewportSize({ width: 1280, height: 1180 });

        await openCalendarSecondaryPanel(page, 'filters');
        const searchInput = page.getByTestId('calendar-queue-search');
        const statusSelect = page.getByTestId('calendar-queue-status-filter');

        await searchInput.fill('Динара');
        await statusSelect.selectOption('no_show');
        await expect(page.getByTestId('calendar-filter-draft-banner')).toBeVisible({ timeout: 15000 });
        await maybeCapture(page, 'wave39-filters-draft-1280');
        await expect(page).not.toHaveURL(/q=/);
        await expect(page.getByText('Найти: Динара')).toHaveCount(0);
        await expect(visibleCards).toHaveCount(2);
        await page.waitForTimeout(400);
        await expect.poll(() => mocks.getCurrentQueueState()).toBeNull();

        await page.getByTestId('calendar-filters-reset').click({ force: true });
        await expect(searchInput).toHaveValue('');
        await expect(statusSelect).toHaveValue('all');
        await expect(page.getByTestId('calendar-filter-draft-banner')).toHaveCount(0);

        await searchInput.fill('Динара');
        await statusSelect.selectOption('no_show');
        await page.getByTestId('calendar-filters-apply').click({ force: true });
        await expect.poll(() => new URL(page.url()).searchParams.get('q')).toBe('Динара');
        await expect.poll(() => new URL(page.url()).searchParams.get('status')).toBe('no_show');
        await expect.poll(() => mocks.getCurrentQueueState()).toEqual({
            follow_up_overdue_only: false,
            follow_up_owner_id: null,
            query: 'Динара',
            queue_lane: 'attention',
            queue_mode: 'ops',
            selected_date: today,
            status_filter: 'no_show',
        });

        await closeCalendarSecondaryPanel(page);
        await expect(page.getByText('Найти: Динара')).toBeVisible({ timeout: 15000 });
        await expect(page.getByText('Статус: Не пришёл')).toBeVisible({ timeout: 15000 });
        await expect(visibleCards).toHaveCount(1);
        await maybeCapture(page, 'wave39-filters-applied-1280');

        await openCalendarSecondaryPanel(page, 'filters');
        await searchInput.fill('Айгуль');
        await expect(page.getByTestId('calendar-filter-draft-banner')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('calendar-filters-reset').click({ force: true });
        await expect(searchInput).toHaveValue('Динара');
        await expect(statusSelect).toHaveValue('no_show');
        await expect(page.getByTestId('calendar-filter-draft-banner')).toHaveCount(0);
        await expect(visibleCards).toHaveCount(1);
    });

    test('phone field keeps raw typing and deletion natural while still showing normalized preview', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page);
        await ensureCalendarReady(page, `${baseURL}/calendar`);

        await openCalendarSecondaryPanel(page, 'scheduling');
        await page.getByTestId('calendar-schedule-service').selectOption('Маникюр');
        await page.getByTestId('calendar-schedule-specialist').selectOption(SPECIALIST_ID);
        await page.getByTestId('calendar-booking-date').fill(formatMockDate(new Date()));
        await expect(page.getByTestId('calendar-slot-10-00')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('calendar-slot-10-00').click({ force: true });

        const phoneInput = page.getByTestId('calendar-booking-customer-phone');
        await phoneInput.fill('8 (701) 555-44-33');
        await expect(phoneInput).toHaveValue('8 (701) 555-44-33');
        await expect(page.getByText(`Сохраним номер как ${formatPhoneForUi('+77015554433')}.`)).toBeVisible({ timeout: 15000 });

        await phoneInput.press('Backspace');
        await expect(phoneInput).toHaveValue('8 (701) 555-44-3');
        await expect(page.getByText('Можно писать как удобно: +7, 8, со скобками или без. Сохраним номер, когда он станет полным.')).toBeVisible({ timeout: 15000 });
        await maybeCapture(page, 'wave39-phone-invalid-1280');

        await phoneInput.press('Control+A');
        await phoneInput.press('Backspace');
        await expect(phoneInput).toHaveValue('');
        await expect(page.getByText('Можно ввести +7 700 123 45 67, 8 700 123 45 67 или вставить номер как есть.')).toBeVisible({ timeout: 15000 });

        await phoneInput.fill('+7 701 555 44 33');
        await expect(phoneInput).toHaveValue('+7 701 555 44 33');
        await expect(page.getByText(`Сохраним номер как ${formatPhoneForUi('+77015554433')}.`)).toBeVisible({ timeout: 15000 });
        await maybeCapture(page, 'wave39-phone-valid-1280');
    });

    test('operator can recover from dependent resets, clear the draft, and create a booking again', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page);
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await expect(page.getByTestId('calendar-booking-card')).toHaveCount(2, { timeout: 15000 });

        await openCalendarSecondaryPanel(page, 'scheduling');
        await expect(page.getByTestId('calendar-booking-next-step')).toContainText('1. Выберите услугу', { timeout: 15000 });

        await page.getByTestId('calendar-schedule-service').selectOption('Маникюр');
        await page.getByTestId('calendar-schedule-specialist').selectOption(SECOND_SPECIALIST_ID);
        await page.getByTestId('calendar-booking-date').fill(formatMockDate(new Date()));
        await expect(page.getByTestId('calendar-slot-14-00')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('calendar-slot-14-00').click({ force: true });
        await expect(page.getByTestId('calendar-booking-summary')).toContainText('14:00 - 15:00', { timeout: 15000 });

        await page.getByTestId('calendar-schedule-service').selectOption('Педикюр');
        await expect(page.getByTestId('calendar-schedule-specialist')).toHaveValue('');
        await expect(page.getByTestId('calendar-booking-next-step')).toContainText('2. Выберите мастера', { timeout: 15000 });
        await expect(page.getByTestId('calendar-booking-summary')).toContainText('Время: Не выбрано', { timeout: 15000 });

        await page.getByTestId('calendar-booking-reset').click({ force: true });
        await expect(page.getByTestId('calendar-schedule-service')).toHaveValue('');
        await expect(page.getByTestId('calendar-booking-next-step')).toContainText('1. Выберите услугу', { timeout: 15000 });

        await page.getByTestId('calendar-schedule-service').selectOption('Маникюр');
        await page.getByTestId('calendar-schedule-specialist').selectOption(SPECIALIST_ID);
        await page.getByTestId('calendar-booking-date').fill(formatMockDate(new Date()));
        await expect(page.getByTestId('calendar-slot-10-00')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('calendar-slot-10-00').click({ force: true });
        await page.getByTestId('calendar-booking-customer-name').fill('Мадина С.');
        await page.getByTestId('calendar-booking-customer-phone').fill('8 (701) 555-44-33');
        await expect(page.getByText(`Сохраним номер как ${formatPhoneForUi('+77015554433')}.`)).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('calendar-booking-submit')).toBeEnabled({ timeout: 15000 });
        await page.getByTestId('calendar-booking-submit').click({ force: true });

        await expect(page.getByText('Запись создана!')).toBeVisible({ timeout: 15000 });
        const createdCard = page.getByTestId('calendar-booking-card').filter({ hasText: 'Мадина С.' }).first();
        await expect(createdCard).toContainText('Маникюр', { timeout: 15000 });
        await expect(createdCard).toContainText('+7 701 555 44 33', { timeout: 15000 });
    });

    test('operator gets case prefill, sees empty-day guidance, and can move to the next day', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        const today = formatMockDate(new Date());
        const emptyDay = shiftDate(today, 1);
        await installCalendarOperatorMocks(page, { emptySlotDates: [emptyDay] });
        await ensureCalendarReady(page, `${baseURL}/calendar?case_id=${CASE_ID}&conversation_id=${CONVERSATION_ID}`);
        await expect(page.getByTestId('calendar-case-context-banner')).toBeVisible({ timeout: 15000 });

        await openCalendarSecondaryPanel(page, 'scheduling');
        await page.getByTestId('calendar-booking-prefill-case').click({ force: true });
        await expect(page.getByTestId('calendar-booking-customer-name')).toHaveValue('Айгуль');
        await expect(page.getByTestId('calendar-booking-customer-phone')).toHaveValue('+7 700 123 45 67');

        await page.getByTestId('calendar-schedule-service').selectOption('Маникюр');
        await page.getByTestId('calendar-schedule-specialist').selectOption(SPECIALIST_ID);
        await page.getByTestId('calendar-booking-date').fill(emptyDay);
        await expect(page.getByTestId('calendar-slot-state')).toContainText('свободного времени нет', { timeout: 15000 });
        await expect(page.getByTestId('calendar-booking-next-step')).toContainText('Выберите другой день', { timeout: 15000 });

        await page.getByTestId('calendar-booking-next-day').click({ force: true });
        await expect(page.getByTestId('calendar-slot-state')).toContainText('Свободное время на', { timeout: 15000 });
        await expect(page.getByTestId('calendar-slot-10-00')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('calendar-slot-10-00').click({ force: true });
        await expect(page.getByTestId('calendar-booking-submit')).toBeEnabled({ timeout: 15000 });
    });

    test('operator sees slot-load errors explicitly and can retry without losing the flow', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        const today = formatMockDate(new Date());
        await installCalendarOperatorMocks(page, { slotErrorDates: [today] });
        await ensureCalendarReady(page, `${baseURL}/calendar`);

        await openCalendarSecondaryPanel(page, 'scheduling');
        await page.getByTestId('calendar-schedule-service').selectOption('Маникюр');
        await page.getByTestId('calendar-schedule-specialist').selectOption(SPECIALIST_ID);
        await page.getByTestId('calendar-booking-date').fill(today);
        await expect(page.getByTestId('calendar-slot-state')).toContainText('Не удалось загрузить свободное время', { timeout: 15000 });
        await expect(page.getByTestId('calendar-booking-next-step')).toContainText('Повторите поиск времени', { timeout: 15000 });

        await page.getByTestId('calendar-booking-retry-slots').click({ force: true });
        await expect(page.getByTestId('calendar-slot-10-00')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('calendar-slot-state')).toContainText('Свободное время на', { timeout: 15000 });
    });

    test('operator gets guarded follow-up actions and never sees technical owners as normal choices', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page, { viewerRole: 'owner' });
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.getByTestId('calendar-queue-lane-all').click({ force: true });
        await expect(page.getByTestId('calendar-booking-card')).toHaveCount(3, { timeout: 15000 });

        await openCalendarSecondaryPanel(page, 'filters');
        const ownerFilter = page.getByTestId('calendar-follow-up-owner-filter');
        const ownerOptions = await ownerFilter.locator('option').allTextContents();
        expect(ownerOptions).toEqual(expect.arrayContaining(['Все, кто звонит клиентам', 'Manager', 'Manager Two', 'Coordinator Dana']));
        expect(ownerOptions).not.toContain('admin console');
        expect(ownerOptions).not.toContain('ci-console');
        await expect(page.getByText('Служебные учётные записи не показываем оператору: 2')).toBeVisible({ timeout: 15000 });
        await closeCalendarSecondaryPanel(page);

        const panel = await openCalendarBookingActionsByText(page, 'Динара');
        await expect(panel).toContainText('За звонок отвечает: Служебный аккаунт', { timeout: 15000 });
        await panel.getByTestId('calendar-follow-up-result-rebooked').click({ force: true });
        await expect(panel.getByTestId('calendar-follow-up-submit')).toBeDisabled();
        await expect(panel.getByText('Выберите новую запись, чтобы закрыть неявку как переписанную.')).toBeVisible({ timeout: 15000 });
        await maybeCapture(page, 'wave39-follow-up-guarded-1280');
        await panel.getByTestId('calendar-follow-up-rebooked-select').selectOption(LINKED_REBOOK_BOOKING_ID);
        await expect(panel.getByTestId('calendar-follow-up-submit')).toBeEnabled({ timeout: 15000 });
        await panel.getByTestId('calendar-follow-up-submit').click({ force: true });
        await expect(panel).toContainText('Клиента переписали', { timeout: 15000 });
    });

    test('operator can edit an active booking, change the slot, and save coherent client data', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page);
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.getByTestId('calendar-queue-lane-all').click({ force: true });

        const panel = await openCalendarBookingActionsByText(page, 'Айгуль');
        await panel.getByTestId('calendar-booking-edit').click({ force: true });
        const composer = page.getByTestId('calendar-booking-composer');
        await expect(composer).toBeVisible({ timeout: 15000 });
        await expect(composer).toContainText('Изменить запись');
        await expect(page.getByTestId('calendar-booking-customer-name')).toHaveValue('Айгуль');
        await expect(page.getByTestId('calendar-booking-customer-phone')).toHaveValue('+7 700 123 45 67');
        await maybeCapture(page, 'wave39-edit-open-1280');

        await page.getByTestId('calendar-schedule-specialist').selectOption(SECOND_SPECIALIST_ID);
        await expect(page.getByTestId('calendar-booking-summary')).toContainText('Время: Не выбрано', { timeout: 15000 });
        await expect(page.getByTestId('calendar-booking-next-step')).toContainText('4. Выберите время', { timeout: 15000 });
        await expect(page.getByTestId('calendar-slot-14-00')).toBeVisible({ timeout: 15000 });
        await page.getByTestId('calendar-slot-14-00').click({ force: true });
        await page.getByTestId('calendar-booking-customer-name').fill('Айгуль Ж.');
        await page.getByTestId('calendar-booking-customer-phone').fill('8 (702) 111-22-33');
        await page.getByLabel('Примечания').fill('Перенесли по просьбе клиента');
        await page.getByTestId('calendar-booking-submit').click({ force: true });

        await expect(page.getByText('Запись обновлена')).toBeVisible({ timeout: 15000 });
        const updatedCard = page.getByTestId('calendar-booking-card').filter({ hasText: 'Айгуль Ж.' }).first();
        await expect(updatedCard).toContainText('14:00 - 15:00', { timeout: 15000 });
        await expect(updatedCard).toContainText('Мастер Алина');
        await expect(updatedCard).toContainText('+7 702 111 22 33');
    });

    test('operator must confirm before discarding composer changes, and edit reset restores the original booking payload', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page);
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.getByTestId('calendar-queue-lane-all').click({ force: true });

        const panel = await openCalendarBookingActionsByText(page, 'Айгуль');
        await panel.getByTestId('calendar-booking-edit').click({ force: true });
        const composer = page.getByTestId('calendar-booking-composer');
        await expect(composer).toBeVisible({ timeout: 15000 });

        await page.getByTestId('calendar-schedule-specialist').selectOption(SECOND_SPECIALIST_ID);
        await page.getByTestId('calendar-booking-customer-name').fill('Айгуль Черновик');
        await page.getByTestId('calendar-booking-reset').click({ force: true });

        await expect(composer).toContainText('Изменить запись');
        await expect(page.getByTestId('calendar-schedule-specialist')).toHaveValue(SPECIALIST_ID);
        await expect(page.getByTestId('calendar-booking-customer-name')).toHaveValue('Айгуль');

        await page.getByTestId('calendar-booking-customer-name').fill('Айгуль Черновик');
        page.once('dialog', (dialog) => dialog.dismiss());
        await page.getByTestId('calendar-booking-composer-close').click({ force: true });
        await expect(composer).toBeVisible({ timeout: 15000 });

        page.once('dialog', (dialog) => dialog.accept());
        await page.getByTestId('calendar-booking-composer-close').click({ force: true });
        await expect(composer).toHaveCount(0);
    });

    test('operator can cancel an active booking with reason and still find it in the queue', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page);
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.getByTestId('calendar-queue-lane-all').click({ force: true });

        const panel = await openCalendarBookingActionsByText(page, 'Мастер Алина');
        await panel.getByTestId('calendar-booking-cancel-reason').fill('Клиент отменил визит');
        await maybeCapture(page, 'wave39-cancel-panel-1280');
        await panel.getByTestId('calendar-booking-cancel-submit').click({ force: true });

        await expect(page.getByText('Запись отменена')).toBeVisible({ timeout: 15000 });
        const cancelledCard = page.getByTestId('calendar-booking-card').filter({ hasText: 'Мастер Алина' }).first();
        await expect(cancelledCard).toContainText('отменена', { timeout: 15000 });
    });

    test('stale booking actions fail closed on version conflict and force the operator to refresh', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page);
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.getByTestId('calendar-queue-lane-all').click({ force: true });

        const panel = await openCalendarBookingActionsByText(page, 'Мастер Алина');

        const backgroundCancel = await page.evaluate(async (bookingId) => {
            const response = await fetch(`/api/proxy/calendar/bookings/${bookingId}/cancel`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    reason: 'Фоновая отмена',
                    version: 2,
                }),
            });
            return {
                status: response.status,
                body: await response.json(),
            };
        }, LINKED_REBOOK_BOOKING_ID);
        expect(backgroundCancel.status).toBe(200);

        await panel.getByTestId('calendar-booking-cancel-reason').fill('Оператор пытается отменить устаревшую запись');
        await panel.getByTestId('calendar-booking-cancel-submit').click({ force: true });

        await expect(page.getByText('Запись уже изменилась. Обновите список и проверьте текущий статус.')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('calendar-booking-panel')).toHaveCount(0);
        await expect(page.getByTestId('calendar-booking-card').filter({ hasText: 'Мастер Алина' }).first()).toContainText('отменена', { timeout: 15000 });
    });

    test('operator must confirm before discarding no-show follow-up drafts from the action panel', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page, { viewerRole: 'owner' });
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.getByTestId('calendar-queue-lane-all').click({ force: true });

        const panel = await openCalendarBookingActionsByText(page, 'Динара');
        await panel.getByTestId('calendar-follow-up-result-rebooked').click({ force: true });
        await panel.getByTestId('calendar-follow-up-note').fill('Черновик по клиенту');

        page.once('dialog', (dialog) => dialog.dismiss());
        await panel.getByTestId('calendar-booking-panel-close').click({ force: true });
        await expect(panel).toBeVisible({ timeout: 15000 });

        page.once('dialog', (dialog) => dialog.accept());
        await panel.getByTestId('calendar-booking-panel-close').click({ force: true });
        await expect(page.getByTestId('calendar-booking-panel')).toHaveCount(0);

        const reopenedPanel = await openCalendarBookingActionsByText(page, 'Динара');
        await expect(reopenedPanel.getByTestId('calendar-follow-up-rebooked-select')).toHaveCount(0);
        await expect(reopenedPanel.getByTestId('calendar-follow-up-note')).toHaveValue('');
    });

    test('operator sees edit and cancel explicitly blocked for non-active bookings', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page);
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.getByTestId('calendar-queue-lane-all').click({ force: true });

        const panel = await openCalendarBookingActionsByText(page, 'Динара');
        await expect(panel.getByTestId('calendar-booking-edit-disabled')).toBeVisible({ timeout: 15000 });
        await expect(panel.getByTestId('calendar-booking-cancel-disabled')).toBeVisible({ timeout: 15000 });
        await expect(panel.getByTestId('calendar-booking-edit')).toHaveCount(0);
        await expect(panel.getByTestId('calendar-booking-cancel-submit')).toHaveCount(0);
        await maybeCapture(page, 'wave39-no-show-disabled-1280');
    });

    test('completed and cancelled bookings keep history visible but block lifecycle mutations', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        await installCalendarOperatorMocks(page, { includeHistoricalStatuses: true });
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.getByTestId('calendar-queue-lane-all').click({ force: true });
        await expect(page.getByTestId('calendar-booking-card')).toHaveCount(5, { timeout: 15000 });

        const completedPanel = await openCalendarBookingActionsByText(page, 'Ляззат');
        await expect(completedPanel.getByTestId('calendar-booking-edit-disabled')).toBeVisible({ timeout: 15000 });
        await expect(completedPanel.getByTestId('calendar-booking-cancel-disabled')).toBeVisible({ timeout: 15000 });
        await expect(completedPanel.getByTestId('calendar-booking-open-case')).toBeVisible({ timeout: 15000 });
        await expect(completedPanel.getByTestId('calendar-follow-up-submit')).toHaveCount(0);
        await maybeCapture(page, 'wave39-completed-blocked-1280');
        await completedPanel.getByTestId('calendar-booking-panel-close').click({ force: true });
        await expect(page.getByTestId('calendar-booking-panel')).toHaveCount(0);

        const cancelledPanel = await openCalendarBookingActionsByText(page, 'Назерке');
        await expect(cancelledPanel.getByTestId('calendar-booking-edit-disabled')).toBeVisible({ timeout: 15000 });
        await expect(cancelledPanel.getByTestId('calendar-booking-cancel-disabled')).toBeVisible({ timeout: 15000 });
        await expect(cancelledPanel.getByTestId('calendar-booking-open-case')).toBeVisible({ timeout: 15000 });
        await expect(cancelledPanel.getByTestId('calendar-follow-up-submit')).toHaveCount(0);
        await maybeCapture(page, 'wave39-cancelled-blocked-1280');
    });

    test('server-backed consultant bot contract never exposes lifecycle or case actions', () => {
        const booking = {
            status: 'CONFIRMED',
            no_show_followup_done: false,
            case_id: 'case-1',
        };
        const actorClass = getCalendarActorClassForRole('consultant_bot');
        const actionMap = buildCalendarBookingActionAvailabilityMap(
            {
                ...booking,
                ...buildMockServerActionContract(
                    {
                        id: 'bot-booking',
                        specialist_id: SPECIALIST_ID,
                        specialist_name: 'Мастер Айжан',
                        start_at: buildMockDateTime(formatMockDate(new Date()), 10, 0),
                        end_at: buildMockDateTime(formatMockDate(new Date()), 11, 0),
                        customer_name: 'Айгуль',
                        customer_phone: '+77001234567',
                        service_type: 'Маникюр',
                        status: 'CONFIRMED',
                        version: 1,
                        created_at: '2026-03-05T09:20:00+05:00',
                        no_show_followup_done: false,
                        case_id: 'case-1',
                    },
                    'consultant_bot',
                ),
            },
            getCalendarActionPermissionsForActor(actorClass),
            actorClass,
        );

        const enabled = Object.values(actionMap)
            .filter((action) => action.state === 'enabled')
            .map((action) => action.id);
        expect(enabled).toEqual([]);
        expect(actionMap.open_case_from_booking.state).toBe('hidden');
        expect(actionMap.edit_booking.state).toBe('hidden');
        expect(actionMap.cancel_booking.state).toBe('hidden');
    });

    test('pending cancel submit disables the destructive action and only sends one mutation', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        const mocks = await installCalendarOperatorMocks(page, { slowCancelMs: 800 });
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await page.getByTestId('calendar-queue-lane-all').click({ force: true });

        const panel = await openCalendarBookingActionsByText(page, 'Мастер Алина');
        const submitButton = panel.getByTestId('calendar-booking-cancel-submit');
        await panel.getByTestId('calendar-booking-cancel-reason').fill('Защита от двойного клика');

        const submitPromise = submitButton.click({ force: true });
        await expect(submitButton).toBeDisabled({ timeout: 15000 });
        await expect.poll(() => mocks.getCancelRequestCount()).toBe(1);
        await submitPromise;

        await expect(page.getByText('Запись отменена')).toBeVisible({ timeout: 15000 });
        await expect.poll(() => mocks.getCancelRequestCount()).toBe(1);
    });

    test('operator telemetry records filter apply/reset and double-submit replay families', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');

        const mocks = await installCalendarOperatorMocks(page, { slowCreateMs: 800 });
        await ensureCalendarReady(page, `${baseURL}/calendar`);

        await openCalendarSecondaryPanel(page, 'filters');
        await page.getByTestId('calendar-queue-search').fill('айгуль');
        await page.getByTestId('calendar-filters-apply').click({ force: true });
        await expect.poll(() => mocks.getOperatorEvents().map((event) => event.event_type)).toContain('filter_apply');

        await page.getByTestId('calendar-queue-search').fill('черновик');
        await page.getByTestId('calendar-filters-reset').click({ force: true });
        await expect.poll(() => mocks.getOperatorEvents().map((event) => event.event_type)).toContain('filter_reset');
        await closeCalendarSecondaryPanel(page);
        await openCalendarSecondaryPanel(page, 'scheduling');
        await page.getByTestId('calendar-schedule-service').selectOption('Маникюр');
        await page.getByTestId('calendar-schedule-specialist').selectOption(SPECIALIST_ID);
        await page.getByTestId('calendar-booking-date').fill(formatMockDate(new Date()));
        await page.getByTestId('calendar-slot-10-00').click({ force: true });
        await page.getByTestId('calendar-booking-customer-name').fill('Нуржан');
        await page.getByTestId('calendar-booking-customer-phone').fill('8 (700) 555-11-22');

        const submitButton = page.getByTestId('calendar-booking-submit');
        const submitPromise = submitButton.click({ force: true });
        await expect(submitButton).toBeDisabled({ timeout: 15000 });
        await page.getByTestId('calendar-booking-form').dispatchEvent('submit');

        await expect.poll(() =>
            mocks.getOperatorEvents().some(
                (event) =>
                    event.event_type === 'double_submit_blocked'
                    && event.action_id === 'create_booking'
                    && event.surface === 'composer',
            ),
        ).toBe(true);

        await submitPromise;
        await expect(page.getByText('Запись создана!')).toBeVisible({ timeout: 15000 });
    });

    test('medium-width calendar keeps filters and booking composer inside the screen bounds', async ({ page }) => {
        test.skip(!useRouteMocks, 'calendar operator lane is deterministic only');
        await page.setViewportSize({ width: 1024, height: 1180 });

        await installCalendarOperatorMocks(page);
        await ensureCalendarReady(page, `${baseURL}/calendar`);
        await expect(page.getByTestId('calendar-queue-controls')).toBeVisible({ timeout: 15000 });

        await openCalendarSecondaryPanel(page, 'filters');
        const secondaryPanel = page.getByTestId('calendar-secondary-panel');
        const overdueFilter = page.getByTestId('calendar-follow-up-overdue-filter');
        const panelBox = await secondaryPanel.boundingBox();
        const overdueBox = await overdueFilter.boundingBox();
        expect(panelBox).not.toBeNull();
        expect(overdueBox).not.toBeNull();
        expect((overdueBox?.x ?? 0) + (overdueBox?.width ?? 0)).toBeLessThanOrEqual((panelBox?.x ?? 0) + (panelBox?.width ?? 0) + 1);
        await closeCalendarSecondaryPanel(page);

        await openCalendarSecondaryPanel(page, 'scheduling');
        await page.getByTestId('calendar-schedule-service').selectOption('Маникюр');
        await page.getByTestId('calendar-schedule-specialist').selectOption(SPECIALIST_ID);
        await page.getByTestId('calendar-booking-date').fill(formatMockDate(new Date()));
        await expect(page.getByTestId('calendar-slot-10-00')).toBeVisible({ timeout: 15000 });
        await expect(page.getByTestId('calendar-booking-summary')).toBeVisible({ timeout: 15000 });
        const composer = page.getByTestId('calendar-booking-composer');
        const composerBox = await composer.boundingBox();
        expect(composerBox).not.toBeNull();
        expect((composerBox?.x ?? 0) + (composerBox?.width ?? 0)).toBeLessThanOrEqual(1024);
        await maybeCapture(page, 'wave39-medium-width-1024');
    });
});
