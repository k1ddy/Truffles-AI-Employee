import { test, expect } from '@playwright/test';
import path from 'path';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const consoleHostPattern = /localhost:3000|localhost:3100|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const useRouteMocks = process.env.INSPECT_CASE_USE_MOCKS !== '0';
const COMPANY_ID = '11111111-1111-4111-8111-111111111111';
const CLIENT_ID = '22222222-2222-4222-8222-222222222222';
const BRANCH_ID = '33333333-3333-4333-8333-333333333333';
const AGENT_ID = '44444444-4444-4444-8444-444444444444';
const CASE_ID = '55555555-5555-4555-8555-555555555555';
const LIVE_CASE_ID = process.env.INSPECT_CASE_LIVE_CASE_ID ?? CASE_ID;
const CONVERSATION_ID = '66666666-6666-4666-8666-666666666666';
const SPECIALIST_ID = '77777777-7777-4777-8777-777777777777';

function toJsonResponse(route: import('@playwright/test').Route, payload: unknown) {
    return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
    });
}

async function installConsoleMocks(page: import('@playwright/test').Page) {
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
                role: 'manager',
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
    await page.route('**/api/proxy/cases**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        const url = new URL(route.request().url());
        if (url.pathname !== '/api/proxy/cases' && url.pathname !== '/api/proxy/cases/') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [
                {
                    id: CASE_ID,
                    conversation_id: CONVERSATION_ID,
                    branch_id: BRANCH_ID,
                    status: 'active',
                    trigger_type: 'message',
                    trigger_value: null,
                    context_summary: 'Клиент хочет маникюр и уточняет свободное время.',
                    user_message: 'Здравствуйте, можно записаться на завтра?',
                    created_at: '2026-03-05T09:00:00+05:00',
                    assigned_to_name: 'Manager',
                    channel: 'whatsapp',
                    sla_status: 'warning',
                    customer_name: 'Айгуль',
                    customer_phone: '+77001234567',
                    last_inbound_at: '2026-03-05T09:10:00+05:00',
                    last_activity_at: '2026-03-05T09:10:00+05:00',
                    last_message_preview: 'Здравствуйте, можно записаться на завтра?',
                    needs_reply: true,
                    has_delivery_error: false,
                    has_pending_outbox: false,
                    human_lock_active: false,
                },
            ],
            cursor: null,
            has_more: false,
            total: 1,
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
        await toJsonResponse(route, {
            id: CASE_ID,
            conversation_id: CONVERSATION_ID,
            branch_id: BRANCH_ID,
            status: 'active',
            trigger_type: 'message',
            trigger_value: null,
            context_summary: 'Клиент хочет маникюр и уточняет свободное время.',
            user_message: 'Здравствуйте, можно записаться на завтра?',
            created_at: '2026-03-05T09:00:00+05:00',
            assigned_to_name: 'Manager',
            channel: 'whatsapp',
            sla_status: 'warning',
            customer_name: 'Айгуль',
            customer_phone: '+77001234567',
            last_inbound_at: '2026-03-05T09:10:00+05:00',
            last_activity_at: '2026-03-05T09:10:00+05:00',
            last_message_preview: 'Здравствуйте, можно записаться на завтра?',
            needs_reply: true,
            has_delivery_error: false,
            has_pending_outbox: false,
            human_lock_active: false,
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
            items: [
                {
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
                },
            ],
            cursor: null,
            has_more: false,
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
    await gotoWithRetry(page, caseUrl);
    const casePane = page
        .getByTestId('case-conversation')
        .or(page.getByTestId('case-details'))
        .or(page.getByTestId('case-view'));
    if (await casePane.first().isVisible().catch(() => false)) {
        return true;
    }
    return false;
}

async function isLiveAuthGateVisible(page: import('@playwright/test').Page): Promise<boolean> {
    const ssoButton = page.getByRole('button', { name: /войти через sso/i }).first();
    const loadingProfile = page.getByText(/загрузка профиля/i).first();
    return Boolean(
        (await ssoButton.isVisible().catch(() => false))
        || (await loadingProfile.isVisible().catch(() => false)),
    );
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
        const startUrl = page.url();
        let clicked = false;
        for (let attempt = 1; attempt <= 3; attempt += 1) {
            try {
                await loginButtonLocator.click({ timeout: 5000 });
                clicked = true;
                break;
            } catch {
                if (await casesTitle.isVisible().catch(() => false)) {
                    return;
                }
                await page.waitForTimeout(400 * attempt);
            }
        }
        if (!clicked && !(await casesTitle.isVisible().catch(() => false))) {
            throw new Error('Failed to click login button after retries');
        }

        await Promise.race([
            page.waitForURL(keycloakHostPattern, { timeout: 15000 }).catch(() => null),
            page.waitForURL((url) => {
                return consoleHostPattern.test(url.toString()) && url.toString() !== startUrl;
            }, { timeout: 15000 }).catch(() => null),
            casesTitle.waitFor({ state: 'visible', timeout: 15000 }).catch(() => null),
            page.locator('#username').waitFor({ state: 'visible', timeout: 15000 }).catch(() => null),
        ]);

        if (
            !(await page.locator('#username').isVisible().catch(() => false))
            && !(await casesTitle.isVisible().catch(() => false))
            && await loginButtonLocator.isVisible().catch(() => false)
        ) {
            await gotoWithRetry(page, `${baseURL}/api/auth/signin/keycloak`);
            await Promise.race([
                page.waitForURL(keycloakHostPattern, { timeout: 15000 }).catch(() => null),
                page.locator('#username').waitFor({ state: 'visible', timeout: 15000 }).catch(() => null),
            ]);
        }

        if (await page.locator('#username').isVisible().catch(() => false)) {
            await page.fill('#username', loginUser);
            await page.fill('#password', loginPassword);
            await page.click('#kc-login');
            await page.waitForURL(consoleHostPattern, { timeout: 20000 });
        }
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
        const opened = await openCaseDirectly(page, LIVE_CASE_ID);
        if (!opened) {
            if (await isLiveAuthGateVisible(page)) {
                test.skip(true, 'Live mode blocked: auth gate visible (SSO/login not established).');
            }
            throw new Error(
                `Live mode: cases workspace unavailable and direct case fallback failed for case_id=${LIVE_CASE_ID}.`,
            );
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
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(`Debug screenshot saved to: ${screenshotPath}`);
        if (useRouteMocks) {
            await gotoWithRetry(page, `${baseURL}/cases/${CASE_ID}`);
            openedFixtureCaseDirectly = true;
        } else {
            console.log('Live mode: queue is empty, trying direct case fallback.');
            openedFixtureCaseDirectly = await openCaseDirectly(page, LIVE_CASE_ID);
            if (!openedFixtureCaseDirectly) {
                if (await isLiveAuthGateVisible(page)) {
                    test.skip(true, 'Live mode blocked: auth gate visible (SSO/login not established).');
                }
                throw new Error(
                    `Live mode: queue is empty and direct case fallback failed for case_id=${LIVE_CASE_ID}.`,
                );
            }
        }
    }

    if (!openedFixtureCaseDirectly) {
        const firstRow = page.getByTestId('cases-row').first();
        if (await firstRow.isVisible().catch(() => false)) {
            await firstRow.click({ force: true });
        } else if (!useRouteMocks) {
            console.log('Live mode: queue row unavailable, trying direct case fallback.');
            const opened = await openCaseDirectly(page, LIVE_CASE_ID);
            if (!opened) {
                if (await isLiveAuthGateVisible(page)) {
                    test.skip(true, 'Live mode blocked: auth gate visible (SSO/login not established).');
                }
                throw new Error(
                    `Live mode: queue row unavailable and direct case fallback failed for case_id=${LIVE_CASE_ID}.`,
                );
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
            const opened = await openCaseDirectly(page, LIVE_CASE_ID);
            if (!opened) {
                if (await isLiveAuthGateVisible(page)) {
                    test.skip(true, 'Live mode blocked: auth gate visible (SSO/login not established).');
                }
                throw new Error(
                    `Live mode: case pane unavailable after fallback for case_id=${LIVE_CASE_ID}.`,
                );
            }
        }
        await expect(casePane.first()).toBeVisible({ timeout: 15000 });
    }
    console.log(`Current URL: ${page.url()}`);

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
        const calendarHref = await openCalendarButton.getAttribute('href');
        if (!calendarHref) {
            throw new Error('case-open-calendar link does not contain href');
        }
        await gotoWithRetry(page, `${baseURL}${calendarHref}`);
        await expect(page.getByTestId('calendar-page')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-queue-controls')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-queue-lane-attention')).toBeVisible({ timeout: 20000 });
        await expect(page.getByTestId('calendar-queue-lane-all')).toBeVisible({ timeout: 20000 });

        await page.getByTestId('calendar-queue-lane-all').click();
        await expect(page.getByTestId('calendar-queue-status-filter')).toBeVisible({ timeout: 20000 });

        const calendarScreenshotPath = path.resolve('calendar_case_context.png');
        await page.screenshot({ path: calendarScreenshotPath, fullPage: true });
        console.log(`Calendar screenshot saved to: ${calendarScreenshotPath}`);

        const openLinkedCase = page.getByTestId('calendar-open-linked-case');
        if (await openLinkedCase.isVisible().catch(() => false)) {
            await openLinkedCase.click();
            await expect(page.getByTestId('case-conversation')).toBeVisible({ timeout: 20000 });
        }
    } else {
        console.log('case-open-calendar button is not visible for this case.');
    }
});
