import { expect, test } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const stayOnBaseOrigin = /localhost|127\.0\.0\.1/.test(baseURL);
let resolvedBaseURL = baseURL;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const deterministicAuthEnabled = process.env.E2E_DETERMINISTIC_AUTH !== '0';
const TENANTS_FIXTURE_COMPANY_ID = '11111111-1111-4111-8111-111111111111';
const TENANTS_FIXTURE_CLIENT_ID = '22222222-2222-4222-8222-222222222222';
const TENANTS_FIXTURE_BRANCH_ID = '33333333-3333-4333-8333-333333333333';
const TENANTS_FIXTURE_AGENT_ID = '44444444-4444-4444-8444-444444444444';
const TENANTS_FIXTURE_NOW = '2026-02-22T12:00:00.000Z';

function buildSignInUrl(origin: string, callbackOrigin = origin) {
    return `${origin}/api/auth/signin?callbackUrl=${encodeURIComponent(callbackOrigin)}`;
}

function resolvePreferredOrigin(actionOrigin: string) {
    return stayOnBaseOrigin ? baseURL : actionOrigin;
}

function urlPathPattern(path: string) {
    return new RegExp(`${path.replace(/\//g, '\\/')}(\\?|$)`);
}

function toJsonResponse(route: import('@playwright/test').Route, payload: unknown) {
    return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
    });
}

function buildTenantsFixtureBundle() {
    const company = {
        id: TENANTS_FIXTURE_COMPANY_ID,
        name: 'Demo Holding',
        billing_info: {},
    };
    const client = {
        id: TENANTS_FIXTURE_CLIENT_ID,
        slug: 'demo_salon',
        name: 'Demo Salon',
        status: 'active',
        company_id: TENANTS_FIXTURE_COMPANY_ID,
        company_name: 'Demo Holding',
        lifecycle_state: 'active',
        payment_status: 'confirmed',
        commercial_state: 'payment_confirmed',
        service_state: 'ok',
        owner_name: 'Owner',
        next_action: 'monitor_sla_and_quality',
        total_branches: 1,
        active_branches: 1,
        degraded_branches: 0,
        go_live_ready_branches: 1,
        reference_branch_ids: [TENANTS_FIXTURE_BRANCH_ID],
        reference_branch_reason: 'active_live_signals',
    };
    const branch = {
        id: TENANTS_FIXTURE_BRANCH_ID,
        client_id: TENANTS_FIXTURE_CLIENT_ID,
        company_id: TENANTS_FIXTURE_COMPANY_ID,
        slug: 'almaty_downtown',
        name: 'Almaty Downtown',
        is_active: true,
        instance_id: 'instance-demo-01',
        telegram_chat_id: '-100100200300',
        phone: '+77001234567',
        knowledge_tag: 'demo_salon',
        timezone: 'Asia/Almaty',
        go_live_state: 'approved',
        go_live_waiver_active: false,
        go_live_allowed: true,
    };
    const fleetSummary = {
        total_companies: 1,
        total_clients: 1,
        active_clients: 1,
        onboarding_clients: 0,
        archived_clients: 0,
        paused_clients: 0,
        go_live_ready_clients: 0,
        degraded_clients: 0,
        payment_pending_clients: 0,
        payment_confirmed_clients: 1,
        lifecycle_counts: {
            lead: 0,
            contracting: 0,
            onboarding: 0,
            go_live_ready: 0,
            active: 1,
            paused: 0,
            archived: 0,
        },
        payment_counts: {
            pending: 0,
            confirmed: 1,
            rejected: 0,
            unknown: 0,
        },
        service_counts: {
            ok: 1,
            degraded: 0,
            attention: 0,
        },
        onboarding_throughput: {
            window_hours: 720,
            approved_branches_total: 1,
            first_pass_approved_branches: 1,
            time_to_go_live_median_hours: 12.0,
            blocker_age_p95_hours: 4.0,
            first_pass_go_live_rate_pct: 100.0,
            incident_reopen_rate_24h_pct: 0.0,
        },
    };
    const attention = {
        generated_at: TENANTS_FIXTURE_NOW,
        stale_after_minutes: 60,
        summary: {
            active_clients_total: 1,
            clients_with_attention: 0,
            high_risk_clients: 0,
            medium_risk_clients: 0,
            low_risk_clients: 0,
            stale_branches_total: 0,
            integration_error_branches_total: 0,
            integration_warn_branches_total: 0,
            outbox_failed_24h_total: 0,
            pending_handovers_total: 0,
        },
        items: [],
    };
    return {
        company,
        client,
        branch,
        fleetSummary,
        attention,
    };
}

function buildDeterministicSessionPayload() {
    return {
        user: {
            name: 'Platform Admin',
            email: 'platform-admin@truffles.local',
        },
        expires: '2099-01-01T00:00:00.000Z',
        accessToken: 'e2e-platform-admin-token',
    };
}

async function mockDeterministicAuthSession(page: import('@playwright/test').Page) {
    await page.route('**/api/auth/session**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, buildDeterministicSessionPayload());
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
}

async function mockPlatformAdminCoreApis(page: import('@playwright/test').Page) {
    const fixture = buildTenantsFixtureBundle();
    await page.route('**/api/proxy/me', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            agent: {
                id: TENANTS_FIXTURE_AGENT_ID,
                name: 'Platform Admin',
                role: 'platform_admin',
                client_id: fixture.client.id,
                branch_id: null,
                is_active: true,
            },
            client: null,
            branches: [fixture.branch],
            clients: [fixture.client],
            companies: [fixture.company],
            company_selection_required: false,
            selection_required: false,
            branch_selection_required: false,
            selected_company_id: null,
            selected_branch_id: null,
        });
    });
}

async function mockIntegrationsDeterministicApis(page: import('@playwright/test').Page) {
    await mockPlatformAdminCoreApis(page);
    await page.route('**/api/proxy/admin/integrations**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            stale_after_minutes: 60,
            cursor: null,
            has_more: false,
            total_in_scope: 0,
            items: [],
            provider_ops_queue: [],
        });
    });
    await page.route('**/api/proxy/admin/provider-lifecycle**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            stale_after_minutes: 60,
            cursor: null,
            has_more: false,
            total_in_scope: 0,
            items: [],
        });
    });
}

async function mockTenantsDeterministicApis(
    page: import('@playwright/test').Page,
    counters?: { portfolioCalls?: number; cockpitCalls?: number },
) {
    const fixture = buildTenantsFixtureBundle();
    const integrationRow = {
        branch_id: fixture.branch.id,
        branch_slug: fixture.branch.slug,
        branch_name: fixture.branch.name,
        client_id: fixture.client.id,
        client_slug: fixture.client.slug,
        status: 'warn',
        whatsapp_status: 'warn',
        telegram_status: 'ok',
        webhook_url: 'https://hooks.example.com/demo',
        webhook_url_valid: true,
        webhook_secret_valid: true,
        instance_id: fixture.branch.instance_id,
        last_inbound_at: TENANTS_FIXTURE_NOW,
        provider_binding_owner: 'provider-owner',
        provider_binding_paid_until: '2026-12-31',
        provider_binding_next_renewal_at: '2026-12-20T00:00:00.000Z',
        provider_binding_instance_id: fixture.branch.instance_id,
        provider_binding_expiry_status: 'expiring_soon',
        provider_binding_rebind_required: true,
        provider_binding_alert_state: 'warn',
        provider_binding_webhook_status: 'configured',
    };
    const controlTowerActionCenter = {
        generated_at: TENANTS_FIXTURE_NOW,
        stale_after_minutes: 60,
        limit: 24,
        include_p2: true,
        summary: {
            total_actions: 2,
            p0_actions: 1,
            p1_actions: 1,
            p2_actions: 0,
            incident_actions: 0,
            provider_ops_actions: 1,
            readiness_actions: 1,
        },
        top_reasons: [{ code: 'provider_binding_rebind_required', count: 1 }],
        items: [
            {
                id: `provider:${fixture.branch.id}:provider_start_rebind`,
                priority: 'p0',
                source: 'provider_ops',
                kind: 'provider_action',
                title: 'Начать перепривязку канала',
                description: 'Филиал требует перепривязки канала для стабильной отправки.',
                reasons: ['provider_binding_rebind_required'],
                href: '/integrations',
                incident_id: null,
                client_id: fixture.client.id,
                client_slug: fixture.client.slug,
                branch_id: fixture.branch.id,
                branch_slug: fixture.branch.slug,
                branch_name: fixture.branch.name,
                job_type: null,
                mode: 'execute',
                params: {
                    branch_id: fixture.branch.id,
                    action: 'provider_start_rebind',
                    mode: 'execute',
                },
                provider_action: 'provider_start_rebind',
                requires_confirmation: false,
                evidence_links: ['/admin/control-tower/action-center'],
            },
            {
                id: `readiness:${fixture.branch.id}`,
                priority: 'p1',
                source: 'readiness',
                kind: 'navigate',
                title: 'Закрыть блокеры запуска филиала',
                description: 'Проверьте onboarding-чеклист перед go-live.',
                reasons: ['readiness_blocked'],
                href: '/tenants',
                incident_id: null,
                client_id: fixture.client.id,
                client_slug: fixture.client.slug,
                branch_id: fixture.branch.id,
                branch_slug: fixture.branch.slug,
                branch_name: fixture.branch.name,
                job_type: null,
                mode: null,
                params: null,
                provider_action: null,
                requires_confirmation: false,
                evidence_links: ['/admin/control-tower/readiness-board'],
            },
        ],
    };
    const controlTowerMigrationProgram = {
        generated_at: TENANTS_FIXTURE_NOW,
        stale_after_minutes: 60,
        limit: 24,
        include_p2: true,
        summary: {
            active_clients_total: 1,
            total_branches: 1,
            ready_branches: 0,
            blocked_branches: 1,
            p0_actions: 1,
            p1_actions: 1,
            p2_actions: 0,
            waves_go: 0,
            waves_hold: 1,
        },
        waves: [
            {
                wave: 'canary',
                gate: 'hold',
                reason: 'hard_blockers_present',
                candidate_clients_total: 1,
                candidate_branches_total: 1,
                blockers_total: 1,
                rollback_triggers: ['hard_blockers_present'],
                top_blockers: [{ code: 'provider_binding_rebind_required', count: 1 }],
            },
            {
                wave: 'cohort',
                gate: 'hold',
                reason: 'hard_blockers_present',
                candidate_clients_total: 1,
                candidate_branches_total: 1,
                blockers_total: 1,
                rollback_triggers: ['hard_blockers_present'],
                top_blockers: [{ code: 'provider_binding_rebind_required', count: 1 }],
            },
            {
                wave: 'fleet',
                gate: 'hold',
                reason: 'hard_blockers_present',
                candidate_clients_total: 1,
                candidate_branches_total: 1,
                blockers_total: 1,
                rollback_triggers: ['hard_blockers_present'],
                top_blockers: [{ code: 'provider_binding_rebind_required', count: 1 }],
            },
        ],
        signals: [
            {
                code: 'hard_blockers',
                status: 'fail',
                value: 1,
                threshold: 0,
                note: 'p0 blockers must be zero',
            },
        ],
        promotion_actions: [],
    };
    await page.route('**/api/proxy/me', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        const headers = route.request().headers();
        const selectedCompanyId = headers['x-company-id'] || '';
        const selectedClientId = headers['x-client-id'] || '';
        const selectedBranchId = headers['x-branch-id'] || '';
        const selectedClient = selectedClientId === fixture.client.id ? fixture.client : null;
        const selectedCompany = selectedCompanyId === fixture.company.id ? fixture.company.id : null;
        const selectedBranch = selectedBranchId === fixture.branch.id ? fixture.branch.id : null;
        await toJsonResponse(route, {
            agent: {
                id: TENANTS_FIXTURE_AGENT_ID,
                name: 'Platform Admin',
                role: 'platform_admin',
                client_id: fixture.client.id,
                branch_id: null,
                is_active: true,
            },
            client: selectedClient,
            branches: [fixture.branch],
            clients: [fixture.client],
            companies: [fixture.company],
            company_selection_required: false,
            selection_required: false,
            branch_selection_required: false,
            selected_company_id: selectedCompany,
            selected_branch_id: selectedBranch,
        });
    });
    await page.route('**/api/proxy/admin/companies**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [fixture.company],
            cursor: null,
            has_more: false,
        });
    });
    await page.route('**/api/proxy/admin/clients**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [fixture.client],
            cursor: null,
            has_more: false,
            summary: fixture.fleetSummary,
        });
    });
    await page.route('**/api/proxy/admin/branches**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            items: [fixture.branch],
            cursor: null,
            has_more: false,
        });
    });
    await page.route('**/api/proxy/admin/tenants/portfolio**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        if (counters) {
            counters.portfolioCalls = (counters.portfolioCalls ?? 0) + 1;
        }
        await toJsonResponse(route, {
            generated_at: TENANTS_FIXTURE_NOW,
            clients: {
                items: [fixture.client],
                cursor: null,
                has_more: false,
                summary: fixture.fleetSummary,
            },
            fleet_attention: fixture.attention,
        });
    });
    await page.route('**/api/proxy/admin/tenants/company-cockpit**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        if (counters) {
            counters.cockpitCalls = (counters.cockpitCalls ?? 0) + 1;
        }
        const url = new URL(route.request().url());
        const selectedClientId = url.searchParams.get('client_id');
        await toJsonResponse(route, {
            generated_at: TENANTS_FIXTURE_NOW,
            company_id: fixture.company.id,
            selected_client_id: selectedClientId || null,
            clients: {
                items: [fixture.client],
                cursor: null,
                has_more: false,
                summary: null,
            },
            branches: {
                items: [fixture.branch],
                cursor: null,
                has_more: false,
            },
        });
    });
    await page.route('**/api/proxy/admin/control-tower/action-center**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, controlTowerActionCenter);
    });
    await page.route('**/api/proxy/admin/control-tower/migration-program**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, controlTowerMigrationProgram);
    });
    await page.route('**/api/proxy/admin/integrations**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            stale_after_minutes: 60,
            cursor: null,
            has_more: false,
            total_in_scope: 1,
            items: [integrationRow],
            provider_ops_queue: [
                {
                    branch_id: fixture.branch.id,
                    client_id: fixture.client.id,
                    client_slug: fixture.client.slug,
                    branch_slug: fixture.branch.slug,
                    branch_name: fixture.branch.name,
                    priority: 'p0',
                    recommended_action: 'provider_start_rebind',
                    reasons: ['provider_binding_rebind_required'],
                    requires_confirmation: false,
                },
            ],
        });
    });
    await page.route('**/api/proxy/admin/provider-lifecycle**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            stale_after_minutes: 60,
            cursor: null,
            has_more: false,
            total_in_scope: 1,
            items: [
                {
                    company_id: fixture.company.id,
                    client_id: fixture.client.id,
                    client_slug: fixture.client.slug,
                    branch_id: fixture.branch.id,
                    branch_slug: fixture.branch.slug,
                    branch_name: fixture.branch.name,
                    sla_state: 'due_soon',
                    next_action: 'provider_start_rebind',
                    sla_deadline_at: '2026-03-03T12:00:00.000Z',
                    blockers: ['provider_binding_rebind_required'],
                    provider_binding_owner: 'provider-owner',
                    provider_binding_paid_until: '2026-12-31',
                    instance_id: fixture.branch.instance_id,
                    provider_binding_instance_id: fixture.branch.instance_id,
                },
            ],
        });
    });
    await page.route('**/api/proxy/onboarding/scorecard**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            status: 'warn',
            ready: false,
        });
    });
    await page.route('**/api/proxy/admin/incidents**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await toJsonResponse(route, {
            generated_at: TENANTS_FIXTURE_NOW,
            summary: {
                total: 0,
                critical: 0,
                warn: 0,
                info: 0,
            },
            items: [],
        });
    });
}

function tenantsSection(page: import('@playwright/test').Page, title: string) {
    return page.locator('section').filter({ has: page.getByRole('heading', { name: title }) }).first();
}

async function resolveAuthOrigin(page: import('@playwright/test').Page) {
    await page.goto(buildSignInUrl(baseURL), { waitUntil: 'domcontentloaded' });
    const providerForm = page.locator('form[action*="keycloak"]').first();
    const action = await providerForm.getAttribute('action');
    const actionOrigin = action ? new URL(action).origin : baseURL;
    resolvedBaseURL = resolvePreferredOrigin(actionOrigin);
}

async function gotoConsoleRoot(page: import('@playwright/test').Page) {
    await page.goto(resolvedBaseURL, { waitUntil: 'domcontentloaded' });
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
    const value = await options.nth(1).getAttribute('value');
    if (value) {
        await selector.selectOption(value);
    } else {
        await selector.selectOption({ index: 1 });
    }
    await expect(selector).not.toHaveValue('');
    return true;
}

async function selectFromGate(
    page: import('@playwright/test').Page,
    selectTestId: string,
    confirmTestId: string,
) {
    const select = page.getByTestId(selectTestId);
    if (!(await selectOptionIfNeeded(select))) {
        return false;
    }
    const confirm = page.getByTestId(confirmTestId);
    if (await confirm.isVisible().catch(() => false)) {
        await confirm.click();
    }
    return true;
}

async function resolveSelectionGate(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'company-select', 'company-select-confirm')) {
        await page.waitForLoadState('domcontentloaded');
    }
    if (await selectFromGate(page, 'client-select', 'client-select-confirm')) {
        await page.waitForLoadState('domcontentloaded');
    }
    if (await selectFromGate(page, 'branch-select', 'branch-select-confirm')) {
        await page.waitForLoadState('domcontentloaded');
    }

    await selectOptionIfNeeded(page.getByTestId('context-company-select'));
    await selectOptionIfNeeded(page.getByTestId('context-client-select'));
    await selectOptionIfNeeded(page.getByTestId('context-branch-select'));
}

async function startKeycloakLogin(page: import('@playwright/test').Page) {
    await page.goto(buildSignInUrl(baseURL), { waitUntil: 'domcontentloaded' });
    let providerForm = page.locator('form[action*="keycloak"]').first();
    const action = await providerForm.getAttribute('action');
    const actionOrigin = action ? new URL(action).origin : baseURL;
    if (actionOrigin !== baseURL) {
        const callbackOrigin = stayOnBaseOrigin ? baseURL : actionOrigin;
        await page.goto(buildSignInUrl(actionOrigin, callbackOrigin), { waitUntil: 'domcontentloaded' });
        providerForm = page.locator('form[action*="keycloak"]').first();
    }
    resolvedBaseURL = resolvePreferredOrigin(actionOrigin);
    const providerButton = page.getByRole('button', { name: /sign in with keycloak/i });
    if (await providerButton.isVisible().catch(() => false)) {
        await providerButton.click();
    } else if (await providerForm.isVisible().catch(() => false)) {
        await providerForm.waitFor({ state: 'visible', timeout: 15000 });
        const submitButton = providerForm.locator('button[type="submit"], input[type="submit"]').first();
        await submitButton.click();
    } else {
        return false;
    }
    await Promise.race([
        page.waitForURL(keycloakHostPattern, { timeout: 15000 }),
        page.waitForURL(consoleHostPattern, { timeout: 15000 }),
    ]);
    return true;
}

async function loginThroughKeycloak(page: import('@playwright/test').Page) {
    const started = await startKeycloakLogin(page);
    if (!started) {
        return;
    }
    if (!(await page.locator('#username').isVisible().catch(() => false))) {
        return;
    }
    await page.fill('#username', loginUser);
    await page.fill('#password', loginPassword);
    await page.click('#kc-login');
    await page.waitForURL(consoleHostPattern);
}

async function ensureLoggedIn(page: import('@playwright/test').Page) {
    if (deterministicAuthEnabled) {
        await mockDeterministicAuthSession(page);
        resolvedBaseURL = baseURL;
        return;
    }

    await resolveAuthOrigin(page);
    await gotoConsoleRoot(page);
    const loginButton = page.getByTestId('login-button');
    const logoutButton = page.getByTestId('logout-button');
    await page.waitForSelector('[data-testid="login-button"], [data-testid="logout-button"]', { timeout: 15000 });
    if (!(await logoutButton.isVisible().catch(() => false)) && (await loginButton.isVisible().catch(() => false))) {
        await loginThroughKeycloak(page);
        await gotoConsoleRoot(page);
    }
    await resolveSelectionGate(page);
}

async function openTenants(page: import('@playwright/test').Page) {
    const navTenants = page.getByTestId('nav-tenants');
    if (await navTenants.isVisible().catch(() => false)) {
        await navTenants.click();
    } else {
        await page.goto(`${resolvedBaseURL}/tenants`, { waitUntil: 'domcontentloaded' });
    }
    await expect(page).toHaveURL(urlPathPattern('/tenants'));
    const tenantsMarkers = [
        page.getByTestId('tenants-page').first(),
        page.getByTestId('tenants-lifecycle-controls').first(),
        page.getByTestId('tenants-onboarding-section').first(),
        page.getByRole('heading', { name: /Тенанты/i }).first(),
    ];
    for (let attempt = 0; attempt < 25; attempt += 1) {
        for (const marker of tenantsMarkers) {
            if (await marker.isVisible().catch(() => false)) {
                return;
            }
        }
        await page.waitForTimeout(200);
    }
    throw new Error("Tenants page markers were not visible after navigation.");
}

async function openIntegrations(page: import('@playwright/test').Page) {
    const navIntegrations = page.getByTestId('nav-integrations');
    if (await navIntegrations.isVisible().catch(() => false)) {
        await navIntegrations.click();
    } else {
        await page.goto(`${resolvedBaseURL}/integrations`, { waitUntil: 'domcontentloaded' });
    }
    await expect(page).toHaveURL(urlPathPattern('/integrations'));
    await expect(page.getByTestId('integrations-title')).toBeVisible();
}

async function openSettings(page: import('@playwright/test').Page) {
    const navSettings = page.getByTestId('nav-settings');
    if (await navSettings.isVisible().catch(() => false)) {
        await navSettings.click();
    } else {
        await page.goto(`${resolvedBaseURL}/settings`, { waitUntil: 'domcontentloaded' });
    }
    await expect(page).toHaveURL(urlPathPattern('/settings'));
    await expect(page.getByTestId('settings-title')).toBeVisible();
}

async function openOps(page: import('@playwright/test').Page) {
    const navOps = page.getByTestId('nav-ops');
    if (await navOps.isVisible().catch(() => false)) {
        await navOps.click();
    } else {
        await page.goto(`${resolvedBaseURL}/ops`, { waitUntil: 'domcontentloaded' });
    }
    await expect(page).toHaveURL(urlPathPattern('/ops'));
    await expect(page.getByTestId('ops-title')).toBeVisible();
}

async function mockCriticalHealthIncident(page: import('@playwright/test').Page, backlog = 1656) {
    const payload = {
        status: 'ok',
        outbox_backlog: backlog,
        version: 'e2e-mock',
    };
    await page.route('**/api/proxy/health**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(payload),
        });
    });
    return {
        setBacklog(nextBacklog: number) {
            payload.outbox_backlog = nextBacklog;
        },
    };
}

test.describe('Platform Admin Incident Banner', () => {
    test('should render full incident details, allow 30m hide, and navigate via CTA @smoke', async ({ page }) => {
        await mockTenantsDeterministicApis(page);
        const healthMock = await mockCriticalHealthIncident(page);
        await ensureLoggedIn(page);
        await openTenants(page);
        await page.evaluate(() => {
            window.localStorage.removeItem('console:health_incident_ui');
        });
        await page.reload({ waitUntil: 'domcontentloaded' });
        await resolveSelectionGate(page);

        const banner = page.getByTestId('global-health-incident-banner');
        await expect(banner).toBeVisible();
        await expect(page.getByTestId('global-health-incident-summary')).toContainText('status=ok');
        await expect(page.getByTestId('global-health-incident-summary')).toContainText('outbox_backlog=1656');
        await expect(page.getByTestId('global-health-incident-reasons')).toBeVisible();
        await expect(page.getByTestId('global-health-incident-runbook')).toBeVisible();

        await page.getByTestId('global-health-incident-open-ops').click();
        await expect(page).toHaveURL(urlPathPattern('/ops'));

        await openTenants(page);
        await page.getByTestId('global-health-incident-snooze').click();
        await expect(page.getByTestId('global-health-incident-banner')).toHaveCount(0);

        // Snooze state must survive health changes and not re-open before 30m.
        healthMock.setBacklog(2200);
        await page.reload({ waitUntil: 'domcontentloaded' });
        await resolveSelectionGate(page);
        await expect(page.getByTestId('global-health-incident-banner')).toHaveCount(0);
    });
});

test.describe('Platform Admin Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await mockIntegrationsDeterministicApis(page);
        await ensureLoggedIn(page);
    });

    test('should navigate from Integrations row to Company Workspace @smoke', async ({ page }) => {
        const integrationsNav = page.getByTestId('nav-integrations');
        if (!(await integrationsNav.isVisible().catch(() => false))) {
            return;
        }

        await openIntegrations(page);
        await expect(page.getByTestId('integrations-workspace-cta')).toBeVisible();

        const emptyState = page.getByTestId('integrations-empty');
        if (await emptyState.isVisible().catch(() => false)) {
            await expect(emptyState).toBeVisible();
            return;
        }

        const openWorkspaceButton = page.getByTestId('integrations-row-open-workspace').first();
        await expect(openWorkspaceButton).toBeVisible();
        await openWorkspaceButton.click();

        await expect(page).toHaveURL(urlPathPattern('/company-workspace'));
        await expect(page.getByTestId('company-workspace-page')).toBeVisible();
        await expect(page.getByTestId('workspace-recommended-open-execute')).toBeVisible();

        const deepLinkParams = await page.evaluate(() => ({
            branchId: new URL(window.location.href).searchParams.get('branch_id'),
            recommendedAction: new URL(window.location.href).searchParams.get('recommended_action'),
            source: new URL(window.location.href).searchParams.get('action_source'),
        }));
        expect(deepLinkParams.branchId).toBeTruthy();
        expect(deepLinkParams.recommendedAction).toBe('provider_start_rebind');
        expect(deepLinkParams.source).toBe('matrix');

        const storedContext = await page.evaluate(() => ({
            clientId: window.localStorage.getItem('console:client_id'),
            branchId: window.localStorage.getItem('console:branch_id'),
        }));
        expect(storedContext.clientId).toBeTruthy();
        expect(storedContext.branchId).toBeTruthy();
    });

    test('should require explicit scope before opening Workspace from Integrations header @smoke', async ({ page }) => {
        await openIntegrations(page);
        await expect(page.getByTestId('integrations-workspace-guidance')).toBeVisible();

        const openWorkspaceFromScope = page.getByTestId('integrations-open-workspace-scope');
        await expect(openWorkspaceFromScope).toBeVisible();
        await expect(openWorkspaceFromScope).toBeDisabled();

        const companySelect = page.getByTestId('integrations-scope-company');
        await expect(companySelect).toBeVisible();
        await companySelect.selectOption({ index: 1 });
        await expect(companySelect).not.toHaveValue('');
        const selectedCompanyId = await companySelect.inputValue();

        await expect(openWorkspaceFromScope).toBeEnabled();
        await openWorkspaceFromScope.click();

        await expect(page).toHaveURL(urlPathPattern('/company-workspace'));
        await expect(page.getByTestId('company-workspace-page')).toBeVisible();

        const storedContext = await page.evaluate(() => ({
            companyId: window.localStorage.getItem('console:company_id'),
        }));
        expect(storedContext.companyId).toBe(selectedCompanyId);
    });

    test('should keep Settings labels plain-language and action-oriented @smoke', async ({ page }) => {
        await page.route('**/api/proxy/settings', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, {
                branches: [
                    {
                        id: TENANTS_FIXTURE_BRANCH_ID,
                        slug: 'almaty_downtown',
                        name: 'Almaty Downtown',
                        is_active: true,
                        instance_id: 'instance-demo-01',
                        telegram_chat_id: '-100100200300',
                    },
                ],
                bot_config: {
                    reminder_timeout_1: 10,
                    reminder_timeout_2: 45,
                    auto_close_timeout: 120,
                    quiet_hours_enabled: false,
                    quiet_hours_start: null,
                    quiet_hours_end: null,
                    tone: 'balanced',
                    autolearn_enabled: true,
                    booking_enabled: true,
                    enable_reminders: true,
                    enable_owner_escalation: true,
                    learning_consent_status: 'granted',
                    learning_anonymization_mode: 'partial',
                    learning_retention_days: 30,
                    data_sharing: 'enabled',
                },
            });
        });
        await page.route('**/api/proxy/subscription/summary', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, {
                plan_name: 'Pro',
                contract_label: 'B2B',
                billable_messages: 1200,
                monthly_quota: 5000,
                next_billing_date: '2026-03-10',
                quota_alert_message: 'Квота в норме.',
            });
        });
        await page.route('**/api/proxy/telegram/verify', async (route) => {
            if (route.request().method() !== 'POST') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, { success: true });
        });
        await page.route('**/api/proxy/telegram/test', async (route) => {
            if (route.request().method() !== 'POST') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, { success: true });
        });

        await openSettings(page);

        const settingsPage = page.getByTestId('settings-page');
        await expect(settingsPage).toBeVisible();
        const telegramCard = page.getByTestId('settings-telegram-connector');
        await expect(telegramCard).toContainText('для уровня компании');
        await expect(telegramCard).not.toContainText('client scope');
        await expect(page.getByTestId('settings-telegram-verify')).toContainText('Проверить связь');
        await expect(page.getByTestId('settings-telegram-test')).toContainText('Отправить тест');
        await expect(telegramCard).not.toContainText('Verify');
        await expect(telegramCard).not.toContainText('Send test');

        await page.getByTestId('settings-advanced-toggle').click();
        const workspaceHint = page.getByTestId('settings-onboarding-workspace-hint');
        await expect(workspaceHint).toContainText('Канонический рабочий поток');
        await expect(workspaceHint).not.toContainText('execution-flow');

        const branchRow = page.getByTestId('settings-branch-row').first();
        await expect(branchRow).toContainText('ID канала WhatsApp (instance_id):');
        await expect(branchRow).not.toContainText('instance_id: instance');
    });

    test('should keep Ops labels plain-language for primary operator actions @smoke', async ({ page }) => {
        const fixtureNow = '2026-03-03T12:00:00.000Z';

        await page.route('**/api/proxy/health', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, {
                status: 'ok',
                version: 'e2e',
                database: 'ok',
                redis: 'ok',
                outbox_backlog: 12,
            });
        });
        await page.route('**/api/proxy/metrics/daily**', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, {
                date: '2026-03-03',
                total_cases: 24,
                pending_cases: 5,
                active_cases: 8,
                resolved_cases: 11,
                avg_resolution_hours: 1.2,
            });
        });
        await page.route('**/api/proxy/telegram/health', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, {
                status: 'ok',
                webhook_alive: true,
                last_success_at: fixtureNow,
                last_error_at: null,
                last_error_message: null,
                error_rate_24h: 0.01,
                pending_messages: 1,
            });
        });
        await page.route('**/api/proxy/ops/outbox**', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, {
                items: [
                    {
                        id: 'outbox-1',
                        status: 'failed',
                        attempts: 2,
                        next_attempt_at: null,
                        last_error: 'provider timeout',
                        created_at: fixtureNow,
                        updated_at: fixtureNow,
                        conversation_id: null,
                        branch_id: TENANTS_FIXTURE_BRANCH_ID,
                        inbound_message_id: 'inbound-1',
                        channel: 'whatsapp',
                        message_type: 'text',
                        message_preview: 'Напоминание о записи',
                        remote_jid: '77700011122@s.whatsapp.net',
                        instance_id: 'instance-demo-01',
                        forwarded_to_telegram: false,
                    },
                ],
                cursor: null,
                has_more: false,
                counts: { pending: 1, processing: 2, failed: 3 },
            });
        });
        await page.route('**/api/proxy/ops/reminders**', async (route) => {
            if (route.request().method() === 'POST') {
                await toJsonResponse(route, { success: true, retried: 1, skipped: 0, matched: 1 });
                return;
            }
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, {
                items: [
                    {
                        id: 'reminder-1',
                        appointment_id: 'appt-1',
                        branch_id: TENANTS_FIXTURE_BRANCH_ID,
                        channel: 'whatsapp',
                        template: 'appointment_reminder',
                        run_at: fixtureNow,
                        status: 'failed',
                        attempt: 1,
                        max_attempts: 3,
                        next_attempt_at: null,
                        last_error: 'provider timeout',
                        dedupe_key: 'dedupe-1',
                        created_at: fixtureNow,
                        updated_at: fixtureNow,
                        outbox_id: 'outbox-1',
                        outbox_status: 'failed',
                        outbox_attempts: 2,
                        outbox_last_error: 'provider timeout',
                        outbox_updated_at: fixtureNow,
                    },
                ],
                cursor: null,
                has_more: false,
                counts: { pending: 2, sent: 10, failed: 1, due_now: 2, overdue_15m: 0 },
                error_buckets: [{ reason: 'provider_timeout', count: 1 }],
            });
        });
        await page.route('**/api/proxy/ops/jobs**', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, { items: [], cursor: null, has_more: false });
        });
        await page.route('**/api/proxy/ops/jobs/catalog', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, {
                items: [
                    {
                        job_type: 'outbox_process',
                        label: 'Обработать очередь',
                        description: 'Проверка и обработка очереди отправки.',
                        supports_dry_run: true,
                    },
                    {
                        job_type: 'integration_reconcile',
                        label: 'Сверка интеграций',
                        description: 'Проверка связки интеграций по филиалам.',
                        supports_dry_run: true,
                    },
                    {
                        job_type: 'heal',
                        label: 'Восстановление',
                        description: 'Безопасная проверка восстановительных действий.',
                        supports_dry_run: true,
                    },
                ],
            });
        });
        await page.route('**/api/proxy/admin/incidents', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            await toJsonResponse(route, {
                generated_at: fixtureNow,
                scope: 'fleet',
                summary: { total: 1, critical: 1, warn: 0, info: 0 },
                items: [
                    {
                        id: 'incident-1',
                        scope: 'branch',
                        severity: 'critical',
                        title: 'Задержка доставки',
                        summary: 'Очередь растет быстрее обычного.',
                        reason_code: 'outbox_backlog',
                        reason_label: 'Очередь отправки растет',
                        source: 'ops',
                        detected_at: fixtureNow,
                        client_id: TENANTS_FIXTURE_CLIENT_ID,
                        client_slug: 'demo_salon',
                        branch_id: TENANTS_FIXTURE_BRANCH_ID,
                        incident_state: 'open',
                        metrics: {
                            outbox_backlog: 120,
                            outbox_failed_24h: 5,
                            integration_degraded_branches: 1,
                            pending_handovers: 2,
                        },
                        actions: [],
                    },
                ],
            });
        });

        await openOps(page);

        const opsPage = page.getByTestId('ops-page');
        await expect(opsPage).toBeVisible();
        await expect(page.getByTestId('ops-telegram-verify')).toContainText('Проверить связь');
        await expect(page.getByTestId('ops-telegram-test')).toContainText('Отправить тест');

        const queueCard = page.getByTestId('ops-queue-card');
        await expect(queueCard).toContainText('С ошибкой');
        await expect(queueCard).toContainText('Ожидает');
        await expect(queueCard).toContainText('В обработке');
        await expect(queueCard).toContainText('Повторить ошибки');
        await expect(queueCard).not.toContainText('Failed');
        await expect(queueCard).not.toContainText('Pending');
        await expect(queueCard).not.toContainText('Processing');
        await expect(queueCard).not.toContainText('Retry failed');

        const remindersCard = page.getByTestId('ops-reminders-card');
        await expect(remindersCard).toContainText('Очередь напоминаний');
        await expect(remindersCard).toContainText('Шаблон');
        await expect(remindersCard).toContainText('Повторить по фильтру');
        await expect(remindersCard).not.toContainText('Reminder Queue');
        await expect(remindersCard).not.toContainText('Template');

        const incidentsCard = page.getByTestId('ops-incidents-card');
        await expect(incidentsCard).toContainText('Критичные');
        await expect(incidentsCard).toContainText('Предупреждения');
        await expect(incidentsCard).toContainText('Инфо');
        await expect(incidentsCard).not.toContainText('Critical');
        await expect(incidentsCard).not.toContainText('Warn');
    });
});

test.describe('Platform Admin Integrations', () => {
    test.beforeEach(async ({ page }) => {
        await mockIntegrationsDeterministicApis(page);
        await ensureLoggedIn(page);
    });

    test('should keep Integrations as fact-only handoff layer with explicit context gate @smoke', async ({ page }) => {
        await openIntegrations(page);
        await expect(page.getByTestId('integrations-workspace-guidance')).toBeVisible();

        const scopeCta = page.getByTestId('integrations-open-workspace-scope');
        await expect(scopeCta).toBeVisible();

        const rowCta = page.getByTestId('integrations-row-open-workspace').first();
        if (!(await rowCta.isVisible().catch(() => false))) {
            await expect(page.getByTestId('integrations-empty')).toBeVisible();
            return;
        }

        if (await scopeCta.isDisabled().catch(() => false)) {
            const companySelect = page.getByTestId('integrations-scope-company');
            await expect(companySelect).toBeVisible();
            await companySelect.selectOption({ index: 1 });
        }
        await expect(scopeCta).toBeEnabled();
        await rowCta.click();
        await expect(page).toHaveURL(urlPathPattern('/company-workspace'));
        await expect(page.getByTestId('workspace-recommended-open-execute')).toBeVisible();
    });
});

test.describe('Platform Admin Tenants', () => {
    test.beforeEach(async ({ page }) => {
        await mockTenantsDeterministicApis(page);
        await ensureLoggedIn(page);
        await openTenants(page);
    });

    async function clickFirstEnabledContextButton(container: import('@playwright/test').Locator) {
        const contextButtons = container.getByRole('button', { name: 'В контекст' });
        const count = await contextButtons.count();
        for (let index = 0; index < count; index += 1) {
            const candidate = contextButtons.nth(index);
            if (!(await candidate.isVisible().catch(() => false))) {
                continue;
            }
            if (await candidate.isDisabled().catch(() => true)) {
                continue;
            }
            await candidate.click();
            return true;
        }
        return false;
    }

    async function ensureFilterHasValue(select: import('@playwright/test').Locator) {
        if (!(await select.isVisible().catch(() => false))) {
            return false;
        }
        if (await select.inputValue()) {
            return true;
        }
        const options = select.locator('option');
        const optionCount = await options.count();
        if (optionCount < 2) {
            return false;
        }
        await select.selectOption({ index: 1 });
        await expect(select).not.toHaveValue('');
        return true;
    }

    test('should render lifecycle modal flow on Tenants @smoke', async ({ page }) => {
        const clients = tenantsSection(page, 'Клиенты');
        await expect(clients).toBeVisible();

        const lifecycleButton = page.getByTestId('tenants-client-lifecycle-open').first();
        if (await lifecycleButton.isVisible().catch(() => false)) {
            await lifecycleButton.click();
            const lifecycleModal = page.getByTestId('tenants-client-lifecycle-modal').first();
            await expect(lifecycleModal).toBeVisible();
            await expect(page.getByTestId('tenants-client-lifecycle-impact').first()).toBeVisible();
            await expect(page.getByTestId('tenants-client-lifecycle-checklist').first()).toBeVisible();
            await expect(page.getByTestId('tenants-client-lifecycle-reason').first()).toBeVisible();
            await expect(page.getByTestId('tenants-client-lifecycle-confirm').first()).toBeVisible();
            const submitButton = page.getByTestId('tenants-client-lifecycle-submit').first();
            await expect(submitButton).toBeDisabled();
            await page.getByTestId('tenants-client-lifecycle-reason').first().fill('platform-admin lifecycle validation');
            await page.getByTestId('tenants-client-lifecycle-check-context').first().check();
            await page.getByTestId('tenants-client-lifecycle-check-impact').first().check();
            await page.getByTestId('tenants-client-lifecycle-check-owner').first().check();
            await page.getByTestId('tenants-client-lifecycle-confirm').first().check();
            await expect(submitButton).toBeEnabled();
            await page.getByTestId('tenants-client-lifecycle-cancel').first().click();
            await expect(lifecycleModal).not.toBeVisible();
            return;
        }

        const legacyButton = clients.getByRole('button', { name: /Архивировать|Восстановить/i }).first();
        if (await legacyButton.isVisible().catch(() => false)) {
            let sawDialog = false;
            page.once('dialog', async (dialog) => {
                sawDialog = true;
                await dialog.dismiss();
            });
            await legacyButton.click();
            await expect.poll(() => sawDialog, { timeout: 5000 }).toBe(true);
            return;
        }

        await expect(clients.getByText(/Клиенты не найдены|page filter company_id/i)).toBeVisible();
    });

    test('should render operational KPI panel on Tenants @smoke', async ({ page }) => {
        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-portfolio').click();
        }

        const actionQueue = page.getByTestId('tenants-action-queue');
        if (await actionQueue.isVisible().catch(() => false)) {
            await expect(actionQueue).toBeVisible();
            await expect(page.getByTestId('tenants-action-queue-item').first()).toBeVisible();
        }

        const kpiPanel = page.getByTestId('tenants-operational-kpi');
        if (await kpiPanel.isVisible().catch(() => false)) {
            await expect(page.getByTestId('tenants-kpi-onboarding-coverage')).toBeVisible();
            await expect(page.getByTestId('tenants-kpi-go-live-readiness')).toBeVisible();
            await expect(page.getByTestId('tenants-kpi-service-stability')).toBeVisible();
            await expect(page.getByTestId('tenants-kpi-change-failure')).toBeVisible();
            await expect(page.getByTestId('tenants-kpi-rollback-share')).toBeVisible();
            const kpiDrilldown = page.getByTestId('tenants-kpi-drilldown');
            if (await kpiDrilldown.isVisible().catch(() => false)) {
                await expect(page.getByTestId('tenants-kpi-export-controls')).toBeVisible();
                await expect(page.getByTestId('tenants-kpi-export-json')).toBeVisible();
                await expect(page.getByTestId('tenants-kpi-export-csv')).toBeVisible();
                await expect(page.getByTestId('tenants-kpi-save-weekly-snapshot')).toBeVisible();
                await expect(page.getByTestId('tenants-kpi-alert-hooks')).toBeVisible();
                await expect(page.getByTestId('tenants-kpi-alert-severity')).toBeVisible();
            }
            return;
        }

        await expect(page.getByTestId('tenants-fleet-attention')).toBeVisible();
    });

    test('should expose branch change controls on Tenants @smoke', async ({ page }) => {
        const modeChanges = page.getByTestId('tenants-mode-changes');
        if (await modeChanges.isVisible().catch(() => false)) {
            await modeChanges.click();
        }

        const branches = page.getByTestId('tenants-change-management');
        await expect(branches).toBeVisible();

        let editButton = page.getByTestId('tenants-branch-edit').first();
        if (!(await editButton.isVisible().catch(() => false))) {
            editButton = branches.getByRole('button', { name: 'Редактировать' }).first();
        }
        if (!(await editButton.isVisible().catch(() => false))) {
            await expect(branches.getByText(/Филиалы не найдены|фильтр по клиенту из контекста/i)).toBeVisible();
            return;
        }

        await editButton.click();
        const previewButton = page.getByTestId('tenants-branch-change-preview').first();
        if (await previewButton.isVisible().catch(() => false)) {
            await expect(previewButton).toBeVisible();
            await expect(page.getByTestId('tenants-branch-change-publish').first()).toBeVisible();
            await expect(page.getByTestId('tenants-branch-change-rollback').first()).toBeVisible();
            return;
        }

        await expect(branches.getByRole('button', { name: /Черновик \+ проверка|Draft \+ Validate/i }).first()).toBeVisible();
        await expect(branches.getByRole('button', { name: /Применить|Publish/i }).first()).toBeVisible();
        await expect(branches.getByRole('button', { name: /Откат|Rollback/i }).first()).toBeVisible();
    });

    test('should switch Tenants workspace modes @smoke', async ({ page }) => {
        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await expect(page.getByTestId('tenants-context-lens')).toBeVisible();
            await expect(
                page.getByTestId('tenants-lifecycle-controls').getByRole('button', { name: /^Все$/ }),
            ).toHaveCount(0);
            const workspaceGuide = page.getByTestId('tenants-workspace-guide');
            if (await workspaceGuide.isVisible().catch(() => false)) {
                await expect(workspaceGuide).toBeVisible();
            }
            await page.getByTestId('tenants-mode-onboarding').click();
            await expect(page.getByTestId('tenants-onboarding-section')).toBeVisible();

            await page.getByTestId('tenants-mode-changes').click();
            await expect(page.getByTestId('tenants-change-management')).toBeVisible();

            await page.getByTestId('tenants-mode-decommission').click();
            await expect(page.getByTestId('tenants-decommission-center')).toBeVisible();
            await expect(
                page.getByTestId('tenants-decommission-lifecycle-controls').getByRole('button', { name: /^Все$/ }),
            ).toHaveCount(0);
            await expect(page.getByTestId('tenants-clients-section')).toBeVisible();

            await page.getByTestId('tenants-mode-portfolio').click();
            await expect(page.getByTestId('tenants-portfolio-companies')).toBeVisible();
            return;
        }

        await expect(tenantsSection(page, 'Компании')).toBeVisible();
        await expect(tenantsSection(page, 'Клиенты')).toBeVisible();
        await expect(tenantsSection(page, 'Филиалы')).toBeVisible();
    });

    test('should keep single editable context source on Tenants (Scenario F2)', async ({ page }) => {
        await expect(page.getByTestId('tenants-context-lens')).toBeVisible();
        await expect(page.getByTestId('context-managed-in-tenants')).toBeVisible();
        await expect(page.getByTestId('context-company-select')).toHaveCount(0);
        await expect(page.getByTestId('context-client-select')).toHaveCount(0);
        await expect(page.getByTestId('context-branch-select')).toHaveCount(0);
        const advancedClear = page.getByTestId('tenants-context-clear-advanced');
        await expect(advancedClear).toBeVisible();
        await expect(page.getByTestId('tenants-context-clear-branch')).not.toBeVisible();
        await expect(page.getByTestId('tenants-context-clear-client')).not.toBeVisible();
        await page.getByTestId('tenants-context-clear-advanced-toggle').click();
        await expect(page.getByTestId('tenants-context-clear-branch')).toBeVisible();
        await expect(page.getByTestId('tenants-context-clear-client')).toBeVisible();
    });

    test('should run onboarding action queue intent with visible section focus', async ({ page }) => {
        const actionQueue = page.getByTestId('tenants-action-queue');
        await expect(actionQueue).toBeVisible();
        const onboardingRun = actionQueue.getByRole('button', { name: /Открыть Онбординг|Открыть Onboarding|Проверить запуск/i }).first();
        await expect(onboardingRun).toBeVisible();
        await onboardingRun.click();
        await expect(page.getByTestId('tenants-onboarding-section')).toBeVisible();
        await expect(page.getByTestId('tenants-onboarding-loop-hint')).toBeVisible();
        await expect(page.getByTestId('tenants-onboarding-open-ops')).toBeVisible();
    });

    test('should deep-link from Tenants action queue to Workspace execute @smoke', async ({ page }) => {
        const actionQueue = page.getByTestId('tenants-action-queue');
        await expect(actionQueue).toBeVisible();

        const openWorkspaceButton = actionQueue.getByRole('button', { name: 'Открыть Workspace' }).first();
        await expect(openWorkspaceButton).toBeVisible();
        await openWorkspaceButton.click();

        await expect(page).toHaveURL(urlPathPattern('/company-workspace'));
        await expect(page.getByTestId('company-workspace-page')).toBeVisible();
        await expect(page.getByTestId('workspace-recommended-open-execute')).toBeVisible();

        const deepLinkParams = await page.evaluate(() => ({
            branchId: new URL(window.location.href).searchParams.get('branch_id'),
            recommendedAction: new URL(window.location.href).searchParams.get('recommended_action'),
            source: new URL(window.location.href).searchParams.get('action_source'),
        }));
        expect(deepLinkParams.branchId).toBeTruthy();
        expect(deepLinkParams.recommendedAction).toBe('provider_start_rebind');
        expect(deepLinkParams.source).toBeTruthy();

        const nextStepOps = page.getByTestId('workspace-next-step-ops');
        await expect(nextStepOps).toBeVisible();
        await nextStepOps.click();
        await expect(page).toHaveURL(urlPathPattern('/ops'));
        await expect(page.getByTestId('ops-back-workspace')).toBeVisible();
        const opsBackTenants = page.getByTestId('ops-back-tenants');
        await expect(opsBackTenants).toBeVisible();
        await expect(opsBackTenants).toHaveAttribute('href', '/tenants');
    });

    test('should keep provider copy plain-language in Tenants -> Workspace flow @smoke', async ({ page }) => {
        const actionQueue = page.getByTestId('tenants-action-queue');
        await expect(actionQueue).toBeVisible();

        await expect(actionQueue).not.toContainText('provider_start_rebind');
        await expect(actionQueue).not.toContainText('provider_binding_rebind_required');

        const openWorkspaceButton = actionQueue.getByRole('button', { name: 'Открыть Workspace' }).first();
        await expect(openWorkspaceButton).toBeVisible();
        await openWorkspaceButton.click();

        await expect(page).toHaveURL(urlPathPattern('/company-workspace'));
        await expect(page.getByTestId('company-workspace-page')).toBeVisible();
        const recommendationSection = page.getByTestId('company-workspace-recommended-action');
        await expect(recommendationSection).toBeVisible();

        await expect(recommendationSection).toContainText('Рекомендуется:');
        await expect(recommendationSection).toContainText('Старт перепривязки');
        await expect(recommendationSection).not.toContainText('provider_start_rebind');
        await expect(recommendationSection).not.toContainText('provider_binding_rebind_required');
        await expect(recommendationSection).toContainText('Что это значит:');
        await expect(recommendationSection).toContainText('Причины');
        await expect(recommendationSection).toContainText('нужна перепривязка канала');
        await expect(recommendationSection).toContainText('источник подсказки:');
        await expect(recommendationSection).not.toContainText('source:');
    });

    test('should keep Integrations and Workspace labels plain-language @smoke', async ({ page }) => {
        await openIntegrations(page);

        const integrationsPage = page.getByTestId('integrations-page');
        await expect(integrationsPage).not.toContainText('owner:');
        await expect(integrationsPage).not.toContainText('paid_until');
        await expect(integrationsPage).not.toContainText('next_renewal_at');

        const row = page.getByTestId('integrations-row').first();
        if (!(await row.isVisible().catch(() => false))) {
            await expect(page.getByTestId('integrations-empty')).toBeVisible();
            return;
        }

        await expect(row).toContainText('Ответственный:');
        await expect(row).toContainText('Оплачено до:');
        await expect(row).toContainText('ID канала');

        await page.getByTestId('integrations-row-open-workspace').first().click();
        await expect(page).toHaveURL(urlPathPattern('/company-workspace'));

        const workspacePage = page.getByTestId('company-workspace-page');
        await expect(workspacePage).toContainText('источник подсказки:');
        await expect(workspacePage).not.toContainText('source:');
        await expect(workspacePage).not.toContainText('owner:');
        await expect(workspacePage).not.toContainText('paid_until');
        await expect(workspacePage).not.toContainText('next_renewal_at');
    });

    test('should ignore legacy workspace recommendation storage without query context @smoke', async ({ page }) => {
        await page.evaluate((branchId) => {
            window.localStorage.setItem(
                'console:workspace_recommended_action',
                JSON.stringify({
                    branch_id: branchId,
                    action: 'provider_start_rebind',
                    reasons: ['provider_binding_rebind_required'],
                    source: 'legacy-storage',
                    captured_at: new Date().toISOString(),
                }),
            );
        }, TENANTS_FIXTURE_BRANCH_ID);

        await page.goto(`${resolvedBaseURL}/company-workspace?branch_id=${TENANTS_FIXTURE_BRANCH_ID}`, { waitUntil: 'domcontentloaded' });
        await expect(page).toHaveURL(urlPathPattern('/company-workspace'));
        await expect(page.getByRole('heading', { name: 'Центр управления компанией' })).toBeVisible();
        await expect(page.getByTestId('workspace-recommended-open-execute')).toHaveCount(0);
        await expect(page.getByText(/нет активной подсказки/i)).toBeVisible();
        await expect(page.getByTestId('workspace-empty-next-steps')).toBeVisible();
        const returnTenants = page.getByTestId('workspace-return-tenants');
        const returnIntegrations = page.getByTestId('workspace-return-integrations');
        await expect(returnTenants).toBeVisible();
        await expect(returnIntegrations).toBeVisible();
        await expect(returnTenants).toHaveAttribute('href', '/tenants');
        await expect(returnIntegrations).toHaveAttribute('href', '/integrations');
    });

    test('should show explicit field contracts in Tenants branch editor @smoke', async ({ page }) => {
        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-changes').click();
        }

        const editButton = page.getByTestId('tenants-branch-edit').first();
        if (await editButton.isVisible().catch(() => false)) {
            await editButton.click();
            const contractPanel = page.getByTestId('tenants-branch-input-contract');
            if (await contractPanel.isVisible().catch(() => false)) {
                await expect(contractPanel).toBeVisible();
            } else {
                await expect(page.getByText(/slug.*a-z0-9_-/i)).toBeVisible();
            }
            return;
        }

        await expect(page.getByTestId('tenants-change-management')).toBeVisible();
    });

    test('should expose schema-driven onboarding controls on Tenants @smoke', async ({ page }) => {
        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-onboarding').click();
        }

        const wizard = page.getByTestId('provisioning-wizard');
        await expect(wizard).toBeVisible();
        await page.getByRole('button', { name: /Ручной по шагам/i }).click();

        const branchDraftStep = page.getByRole('button', { name: /Филиал/i }).first();
        if (await branchDraftStep.isVisible().catch(() => false) && !(await branchDraftStep.isDisabled().catch(() => true))) {
            await branchDraftStep.click();
        }

        const billingContractField = page.getByTestId('onboarding-billing-contract');
        const billingCurrencyField = page.getByTestId('onboarding-billing-currency');
        if (await billingContractField.isVisible().catch(() => false)) {
            await expect(billingContractField).toBeVisible();
            await expect(billingCurrencyField).toBeVisible();
        } else {
            await expect(page.getByPlaceholder('B2B').first()).toBeVisible();
            await expect(page.getByPlaceholder('KZT').first()).toBeVisible();
        }

        const bookingStep = page.getByRole('button', { name: /Бронирование/i }).first();
        if (await bookingStep.isVisible().catch(() => false) && !(await bookingStep.isDisabled().catch(() => true))) {
            await bookingStep.click();
            const workingHoursForm = page.getByTestId('onboarding-working-hours-form');
            const bookingSettingsForm = page.getByTestId('onboarding-booking-settings-form');
            if (await workingHoursForm.isVisible().catch(() => false)) {
                await expect(workingHoursForm).toBeVisible();
                await expect(bookingSettingsForm).toBeVisible();
            } else {
                await expect(page.getByText(/Working hours/i)).toBeVisible();
                await expect(page.getByText(/Booking settings/i)).toBeVisible();
            }
        }

        const goNoGoStep = page.getByRole('button', { name: /Go\/No-Go/i }).first();
        if (await goNoGoStep.isVisible().catch(() => false) && !(await goNoGoStep.isDisabled().catch(() => true))) {
            await goNoGoStep.click();
            const readinessScore = page.getByTestId('onboarding-readiness-score');
            if (await readinessScore.isVisible().catch(() => false)) {
                await expect(readinessScore).toBeVisible();
                const timeline = page.getByTestId('onboarding-readiness-timeline');
                if (await timeline.isVisible().catch(() => false)) {
                    await expect(timeline).toBeVisible();
                }
            } else {
                await expect(page.getByRole('heading', { name: /Проверки Go\/No-Go/i })).toBeVisible();
            }
            const templateSelect = page.getByTestId('onboarding-domain-template-select');
            if (await templateSelect.isVisible().catch(() => false)) {
                await expect(templateSelect).toBeVisible();
                await page.getByTestId('onboarding-domain-template-select').selectOption('ecom');
                await page.getByTestId('onboarding-domain-template-apply').click();
            } else {
                await expect(page.getByRole('heading', { name: /Договор онбординга/i })).toBeVisible();
            }

            const purchasedForm = page.getByTestId('onboarding-purchased-form');
            if (await purchasedForm.isVisible().catch(() => false)) {
                await expect(purchasedForm).toBeVisible();
                await expect(page.getByTestId('onboarding-purchased-apply-json')).toBeVisible();
                const purchasedJson = page.getByTestId('onboarding-purchased-json');
                if (!(await purchasedJson.isVisible().catch(() => false))) {
                    const advancedJsonToggle = page.getByText(/Advanced JSON \(expert\)/i).first();
                    if (await advancedJsonToggle.isVisible().catch(() => false)) {
                        await advancedJsonToggle.click();
                    }
                }
                await expect(purchasedJson).toBeAttached();
            } else {
                const schemaLabel = page.getByText(/Purchased capabilities \(schema form\)/i);
                if (await schemaLabel.isVisible().catch(() => false)) {
                    await expect(schemaLabel).toBeVisible();
                    await expect(page.getByText(/Advanced JSON \(expert\)/i)).toBeVisible();
                } else {
                    await expect(page.getByText(/purchased \(JSON, договор\/возможности\)/i)).toBeVisible();
                }
            }
            return;
        }

        await expect(page.getByText(/booking_settings и working_hours нужны/i)).toBeVisible();
    });

    test('should keep branch page-filter after apply context (Scenario B)', async ({ page }) => {
        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-changes').click();
        }

        const branchesSection = page.getByTestId('tenants-change-management');
        await expect(branchesSection).toBeVisible();
        const hasContextButton = await clickFirstEnabledContextButton(branchesSection);
        expect(hasContextButton).toBe(true);

        const companyFilter = page.getByTestId('tenants-page-filter-company');
        const clientFilter = page.getByTestId('tenants-page-filter-client');
        const branchFilter = page.getByTestId('tenants-page-filter-branch');
        await expect(companyFilter).toBeVisible();
        await expect(clientFilter).toBeVisible();
        await expect(branchFilter).toBeVisible();
        await expect(companyFilter).not.toHaveValue('');
        await expect(clientFilter).not.toHaveValue('');
        await expect(branchFilter).not.toHaveValue('');
        const companyValueBefore = await companyFilter.inputValue();
        const clientValueBefore = await clientFilter.inputValue();
        const branchValueBefore = await branchFilter.inputValue();

        await page.getByTestId('tenants-page-filter-apply-context').click();
        await expect(companyFilter).toHaveValue(companyValueBefore);
        await expect(clientFilter).toHaveValue(clientValueBefore);
        await expect(branchFilter).toHaveValue(branchValueBefore);
    });

    test('should not mutate page filters when context has orphan branch scope (Scenario B2)', async ({ page }) => {
        const companyFilter = page.getByTestId('tenants-page-filter-company');
        const clientFilter = page.getByTestId('tenants-page-filter-client');
        const branchFilter = page.getByTestId('tenants-page-filter-branch');
        await expect(companyFilter).toBeVisible();
        await expect(clientFilter).toBeVisible();
        await expect(branchFilter).toBeVisible();
        const companyValueBefore = await companyFilter.inputValue();
        const clientValueBefore = await clientFilter.inputValue();
        const branchValueBefore = await branchFilter.inputValue();

        await page.evaluate(() => {
            window.localStorage.setItem('console:company_id', '');
            window.localStorage.setItem('console:client_id', '');
            window.localStorage.setItem('console:branch_id', 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
        });

        await page.getByTestId('tenants-page-filter-apply-context').click();
        await expect(companyFilter).toHaveValue(companyValueBefore);
        await expect(clientFilter).toHaveValue(clientValueBefore);
        await expect(branchFilter).toHaveValue(branchValueBefore);
    });

    test('should pass branch_id to branches API when branch page filter is selected (Scenario B3)', async ({ page }) => {
        const fixture = buildTenantsFixtureBundle();
        let capturedBranchParam: string | null = null;
        await page.route('**/api/proxy/admin/branches**', async (route) => {
            if (route.request().method() !== 'GET') {
                await route.fallback();
                return;
            }
            const url = new URL(route.request().url());
            capturedBranchParam = url.searchParams.get('branch_id');
            await toJsonResponse(route, {
                items: [fixture.branch],
                cursor: null,
                has_more: false,
            });
        });

        const branchFilter = page.getByTestId('tenants-page-filter-branch');
        await expect(branchFilter).toBeVisible();
        await branchFilter.selectOption(fixture.branch.id);
        await expect(branchFilter).toHaveValue(fixture.branch.id);
        await expect.poll(() => capturedBranchParam).toBe(fixture.branch.id);
    });

    test('should reset only page filters and keep context chips (Scenario C)', async ({ page }) => {
        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-changes').click();
        }

        const branchesSection = page.getByTestId('tenants-change-management');
        await expect(branchesSection).toBeVisible();
        const hasContextButton = await clickFirstEnabledContextButton(branchesSection);
        expect(hasContextButton).toBe(true);

        const branchChip = page.locator('[data-testid="tenants-context-lens"] span').filter({ hasText: /^филиал:/ }).first();
        await expect(branchChip).toBeVisible();
        await expect(branchChip).not.toContainText('все');

        await page.getByTestId('tenants-page-filter-clear-all').click();
        await expect(page.getByTestId('tenants-page-filter-company')).toHaveValue('');
        await expect(page.getByTestId('tenants-page-filter-client')).toHaveValue('');
        await expect(page.getByTestId('tenants-page-filter-branch')).toHaveValue('');
        await expect(branchChip).not.toContainText('все');
    });

    test('should reset only context and keep page filters (Scenario D)', async ({ page }) => {
        const companyFilter = page.getByTestId('tenants-page-filter-company');
        const hasCompanyFilter = await ensureFilterHasValue(companyFilter);
        expect(hasCompanyFilter).toBe(true);
        const companyFilterBeforeReset = await companyFilter.inputValue();

        await page.getByTestId('tenants-context-clear-all').click();

        const branchChip = page.locator('[data-testid="tenants-context-lens"] span').filter({ hasText: /^филиал:/ }).first();
        await expect(branchChip).toBeVisible();
        await expect(branchChip).toContainText('все');
        await expect(companyFilter).toHaveValue(companyFilterBeforeReset);
    });

    test('should call portfolio and cockpit endpoints on Tenants (Scenario E)', async ({ page }) => {
        const counters = { portfolioCalls: 0, cockpitCalls: 0 };
        await mockTenantsDeterministicApis(page, counters);
        await page.reload({ waitUntil: 'domcontentloaded' });
        await resolveSelectionGate(page);
        await openTenants(page);

        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-portfolio').click();
        }

        const refreshKpiButton = page.getByRole('button', { name: /Обновить сводку/i });
        if (await refreshKpiButton.isVisible().catch(() => false)) {
            await refreshKpiButton.click();
        }
        for (let attempt = 0; attempt < 30 && (counters.portfolioCalls ?? 0) === 0; attempt += 1) {
            await page.waitForTimeout(500);
        }
        expect(counters.portfolioCalls).toBeGreaterThan(0);

        const companyFilter = page.getByTestId('tenants-page-filter-company');
        const hasCompanyFilter = await ensureFilterHasValue(companyFilter);
        expect(hasCompanyFilter).toBe(true);
        for (let attempt = 0; attempt < 30 && (counters.cockpitCalls ?? 0) === 0; attempt += 1) {
            await page.waitForTimeout(500);
        }
        expect(counters.cockpitCalls).toBeGreaterThan(0);
    });

    test('should keep tenants copy business-oriented and isolate technical markers to security/debug zones @smoke', async ({ page }) => {
        await openTenants(page);
        const tenantsPage = page.getByTestId('tenants-page');
        await expect(tenantsPage).not.toContainText('TENANTS_V3_CONTROL_TOWER');
        await expect(tenantsPage).not.toContainText('trace_id:');
        await expect(tenantsPage).not.toContainText('slug =');
        await expect(tenantsPage).not.toContainText('telegram_chat_id');

        const quickCreatePanel = page.getByTestId('tenants-quick-create');
        await expect(quickCreatePanel).toContainText('Идентификатор WhatsApp (если есть)');
        await expect(quickCreatePanel).not.toContainText('Instance ID (если есть)');

        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-changes').click();
        }

        const changePanel = page.getByTestId('tenants-change-management');
        await expect(changePanel).toBeVisible();
        await changePanel.getByRole('button', { name: 'Редактировать' }).first().click();
        await expect(changePanel).toContainText('Идентификатор WhatsApp (опционально)');
        await expect(changePanel).toContainText('Чат Telegram (опционально)');
        await expect(changePanel).toContainText('Тег базы знаний (опционально)');
        await expect(changePanel).not.toContainText('WhatsApp instance ID');
        await expect(changePanel).not.toContainText('Telegram chat ID');
        await expect(changePanel).not.toContainText('knowledge_tag');
        await expect(changePanel).not.toContainText('branch_deactivate');

        const sensitiveCells = changePanel.getByTestId('tenants-sensitive-id-cell');
        await expect(sensitiveCells.first()).toBeVisible();
        await expect(sensitiveCells.first()).toContainText('instance_id');
        const changePanelText = (await changePanel.innerText()).toLowerCase();
        const sensitiveZoneTexts = (await sensitiveCells.allInnerTexts()).map((item) => item.toLowerCase());
        const operatorTextWithoutSensitiveZones = sensitiveZoneTexts.reduce(
            (acc, item) => acc.split(item).join(' '),
            changePanelText,
        );
        expect(operatorTextWithoutSensitiveZones).not.toContain('instance_id');
    });

    test('should audit instance_id reveal and copy actions on Tenants @smoke', async ({ page }) => {
        const auditRequests: Array<Record<string, unknown>> = [];
        await page.route('**/api/proxy/admin/tenants/sensitive-access', async (route) => {
            if (route.request().method() !== 'POST') {
                await route.fallback();
                return;
            }
            let payload: Record<string, unknown> = {};
            try {
                payload = route.request().postDataJSON() as Record<string, unknown>;
            } catch {
                payload = {};
            }
            auditRequests.push(payload);
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ ok: true }),
            });
        });
        await openTenants(page);

        const modes = page.getByTestId('tenants-workspace-modes');
        if (await modes.isVisible().catch(() => false)) {
            await page.getByTestId('tenants-mode-changes').click();
        }

        const branches = page.getByTestId('tenants-change-management');
        await expect(branches).toBeVisible();
        const revealButton = page
            .getByTestId('tenants-instance-id-reveal')
            .or(page.getByRole('button', { name: /Показать instance_id|Скрыть instance_id/i }))
            .first();
        const copyButton = page
            .getByTestId('tenants-instance-id-copy')
            .or(page.getByRole('button', { name: /Скопировать instance_id/i }))
            .first();
        await expect(revealButton).toBeVisible();
        await expect(copyButton).toBeVisible();

        await page.evaluate(() => {
            const existing = navigator.clipboard as Clipboard | undefined;
            if (!existing) {
                Object.defineProperty(navigator, 'clipboard', {
                    configurable: true,
                    value: { writeText: async () => undefined },
                });
                return;
            }
            Object.defineProperty(existing, 'writeText', {
                configurable: true,
                value: async () => undefined,
            });
        });

        await revealButton.click();
        await expect.poll(() => auditRequests.some((item) => item.action === 'reveal')).toBe(true);

        await copyButton.click();
        await expect.poll(() => auditRequests.some((item) => item.action === 'copy')).toBe(true);

        const revealPayload = auditRequests.find((item) => item.action === 'reveal');
        const copyPayload = auditRequests.find((item) => item.action === 'copy');
        expect(revealPayload?.field).toBe('instance_id');
        expect(copyPayload?.field).toBe('instance_id');
        expect(typeof revealPayload?.branch_id).toBe('string');
        expect(typeof copyPayload?.branch_id).toBe('string');
    });

    test('should show actionable provisioning guidance for quick-create server errors @smoke', async ({ page }) => {
        await page.route('**/api/proxy/admin/companies', async (route) => {
            if (route.request().method() !== 'POST') {
                await route.fallback();
                return;
            }
            await route.fulfill({
                status: 500,
                contentType: 'application/json',
                body: JSON.stringify({
                    error: {
                        code: 'SERVER_ERROR',
                        message: 'Synthetic create company failure',
                        trace_id: 'trace-e2e-quick-create-500',
                    },
                }),
            });
        });

        const quickCreateSection = page.getByTestId('tenants-quick-create');
        await expect(quickCreateSection).toBeVisible();

        await quickCreateSection.getByPlaceholder('Beauty Group').fill(`e2e-company-${Date.now()}`);
        await quickCreateSection.getByRole('button', { name: 'Создать компанию' }).click();

        const errorSummary = page.getByTestId('tenants-error-summary');
        await expect(errorSummary).toBeVisible();
        await expect(errorSummary).toContainText('SERVER_ERROR');
        await expect(errorSummary).toContainText('Synthetic create company failure');
        await expect(errorSummary).toContainText('PROVISIONING_NEXT_STEP');
        await expect(errorSummary).toContainText('создание компании');
        await expect(errorSummary).toContainText('POST /api/proxy/admin/companies');
        await expect(errorSummary).toContainText('trace-e2e-quick-create-500');
        await expect(errorSummary).toContainText('передайте в OPS');
    });
});
