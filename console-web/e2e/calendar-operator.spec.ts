import { test, expect, type Page, type Route } from '@playwright/test';
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
const CONVERSATION_ID = '66666666-6666-4666-8666-666666666666';
const SPECIALIST_ID = '77777777-7777-4777-8777-777777777777';
const SECOND_SPECIALIST_ID = '88888888-8888-4888-8888-888888888888';
const MANAGER_TWO_AGENT_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const COORDINATOR_AGENT_ID = 'abababab-1111-4bab-8bab-ababababab11';
const TECHNICAL_ADMIN_AGENT_ID = '99999999-aaaa-4999-8aaa-999999999999';
const TECHNICAL_CI_AGENT_ID = '99999999-bbbb-4999-8bbb-999999999999';
const NO_SHOW_BOOKING_ID = '98989898-9898-4989-8989-989898989898';
const LINKED_REBOOK_BOOKING_ID = '97979797-9797-4979-8979-979797979797';

type MockViewerRole = 'admin' | 'manager' | 'owner';

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
    created_at: string;
};

type CalendarOperatorMockOptions = {
    viewerRole?: MockViewerRole;
    emptySlotDates?: string[];
    slotErrorDates?: string[];
};

function deepClone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value)) as T;
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
    const digits = String(value ?? '').replace(/\D/g, '');
    if (digits.length === 10) {
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

async function installCalendarOperatorMocks(page: Page, options: CalendarOperatorMockOptions = {}) {
    const viewerRole = options.viewerRole ?? 'owner';
    const today = formatMockDate(new Date());
    const emptySlotDates = new Set(options.emptySlotDates ?? []);
    const slotFailuresRemaining = new Map<string, number>((options.slotErrorDates ?? []).map((date) => [date, 2]));
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
            created_at: '2026-03-05T09:30:00+05:00',
        },
    ];

    await page.route('**/api/auth/session**', async (route) => {
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
    await page.route('**/api/auth/csrf**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, { csrfToken: 'calendar-operator-csrf' });
    });
    await page.route('**/api/auth/providers**', async (route) => {
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
    await page.route('**/api/proxy/me**', async (route) => {
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
    await page.route('**/api/proxy/agents**', async (route) => {
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
    await page.route('**/api/proxy/queue-state/current**', async (route) => {
        const method = route.request().method();
        if (method === 'GET') {
            await toJsonResponse(route, {
                found: false,
                surface: 'calendar',
                query_state: null,
                updated_at: null,
                version: 1,
            });
            return;
        }
        if (method === 'PUT') {
            const payload = route.request().postDataJSON() as Record<string, unknown> | null;
            await toJsonResponse(route, {
                success: true,
                found: true,
                surface: 'calendar',
                query_state: deepClone(payload?.query_state ?? null),
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
    await page.route(new RegExp(`.*/api/proxy/cases/${CASE_ID}(?:\\?.*)?$`), async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, caseState);
    });
    await page.route('**/api/proxy/calendar/specialists**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, { items: specialists });
    });
    await page.route('**/api/proxy/calendar/slots**', async (route) => {
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
    await page.route('**/api/proxy/calendar/bookings**', async (route) => {
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
            await toJsonResponse(route, { items: deepClone(items) });
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
                created_at: '2026-03-08T15:30:00+05:00',
            };
            bookingStore.unshift(newBooking);
            await toJsonResponse(route, { success: true, booking: deepClone(newBooking), case_effects: [] });
            return;
        }
        const statusMatch = pathname.match(/\/calendar\/bookings\/([^/]+)\/status$/);
        if (method === 'POST' && statusMatch) {
            const booking = bookingStore.find((item) => item.id === statusMatch[1]);
            if (!booking) {
                await toErrorResponse(route, 404, 'NOT_FOUND', 'Booking not found');
                return;
            }
            const payload = route.request().postDataJSON() as { status?: 'COMPLETED' | 'NO_SHOW' } | null;
            booking.status = payload?.status ?? booking.status;
            booking.needs_action = booking.status === 'NO_SHOW';
            booking.attention_reason = booking.status === 'NO_SHOW' ? 'Связаться после неявки' : null;
            await toJsonResponse(route, { success: true, booking: deepClone(booking), case_effects: [] });
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
            } | null;
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
            await toJsonResponse(route, {
                success: true,
                booking: deepClone(booking),
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
            const payload = route.request().postDataJSON() as { owner_agent_id?: string | null; due_at?: string | null } | null;
            booking.follow_up_owner_id = payload?.owner_agent_id ?? null;
            booking.follow_up_owner_name = getAgentDisplayName(payload?.owner_agent_id ?? null);
            booking.follow_up_due_at = payload?.due_at ?? null;
            booking.follow_up_overdue = Boolean(booking.follow_up_due_at && booking.follow_up_due_at < '2026-03-08T16:30:00+05:00');
            await toJsonResponse(route, { success: true, booking: deepClone(booking), case_effects: [] });
            return;
        }
        await route.fallback();
    });
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
        await panel.getByTestId('calendar-follow-up-rebooked-select').selectOption(LINKED_REBOOK_BOOKING_ID);
        await expect(panel.getByTestId('calendar-follow-up-submit')).toBeEnabled({ timeout: 15000 });
        await panel.getByTestId('calendar-follow-up-submit').click({ force: true });
        await expect(panel).toContainText('Клиента переписали', { timeout: 15000 });
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
    });
});
