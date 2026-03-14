import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';
import {
    buildSignInUrl,
    loginThroughKeycloak,
    shouldAllowLocalSessionBridge,
    shouldStayOnBaseOrigin,
} from './support/keycloak-auth';

const consoleHostPattern = /localhost(?::\d+)?|127\.0\.0\.1(?::\d+)?|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const stayOnBaseOrigin = shouldStayOnBaseOrigin(baseURL);
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const isLocalBaseURL = /localhost|127\.0\.0\.1/.test(baseURL);
const quarantineLocal = !!process.env.CI && isLocalBaseURL;
const consultantVerificationScreenshotDir = process.env.E2E_CONSULTANT_VERIFICATION_SCREENSHOT_DIR;

let resolvedBaseURL = baseURL;

test.skip(quarantineLocal, 'Quarantine local CI owner/admin suite while stabilizing console-e2e.');

function urlPathPattern(path: string) {
    return new RegExp(`${path.replace(/\//g, '\\/')}(\\?|$)`);
}

function toJsonResponse(route: import('@playwright/test').Route, payload: unknown, status = 200) {
    return route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(payload),
    });
}

async function mockKnowledgeWorkspace(
    page: import('@playwright/test').Page,
    {
        current,
        readiness,
        validateResponse,
    }: {
        current: Record<string, unknown>;
        readiness?: Record<string, unknown>;
        validateResponse?: Record<string, unknown>;
    },
) {
    const companyId = '11111111-1111-4111-8111-111111111111';
    const clientId = '22222222-2222-4222-8222-222222222222';
    const branchId = '33333333-3333-4333-8333-333333333333';
    const agentId = '44444444-4444-4444-8444-444444444444';

    await page.route(/.*\/api\/auth\/session(?:\?.*)?$/, async (route) => {
        await toJsonResponse(route, {
            user: {
                name: 'Owner',
                email: 'owner@example.com',
            },
            accessToken: 'e2e-owner-token',
            expires: '2030-01-01T00:00:00.000Z',
        });
    });
    await page.route('**/api/proxy/me', async (route) => {
        await toJsonResponse(route, {
            agent: {
                id: agentId,
                role: 'owner',
                name: 'Owner',
            },
            client: {
                id: clientId,
                company_id: companyId,
                name: 'Demo Salon',
                slug: 'demo_salon',
            },
            selected_company_id: companyId,
            selected_branch_id: branchId,
            branches: [
                {
                    id: branchId,
                    client_id: clientId,
                    company_id: companyId,
                    name: 'Almaty Downtown',
                    knowledge_tag: 'demo_salon',
                    working_hours: {
                        days: 'Пн-Вс',
                        open: '10:00',
                        close: '21:00',
                    },
                },
            ],
        });
    });
    await page.route(/.*\/api\/proxy\/knowledge\/current(?:\?.*)?$/, async (route) => {
        await toJsonResponse(route, current);
    });
    await page.route(/.*\/api\/proxy\/knowledge\/history(?:\?.*)?$/, async (route) => {
        await toJsonResponse(route, { items: [] });
    });
    await page.route(/.*\/api\/proxy\/learning\/candidates(?:\?.*)?$/, async (route) => {
        await toJsonResponse(route, { items: [] });
    });
    await page.route(/.*\/api\/proxy\/calendar\/specialists(?:\?.*)?$/, async (route) => {
        await toJsonResponse(route, { items: [] });
    });
    await page.route(/.*\/api\/proxy\/business\/consultant-verification\/readiness(?:\?.*)?$/, async (route) => {
        await toJsonResponse(route, readiness ?? {
            readiness: {
                status: 'ready',
                status_label: 'Сравнение не требуется',
                summary: 'Для текущего branch compare не нужен.',
                compare_required: false,
            },
        });
    });
    if (validateResponse) {
        await page.route(/.*\/api\/proxy\/knowledge\/validate(?:\?.*)?$/, async (route) => {
            await toJsonResponse(route, validateResponse);
        });
    }
}

function isMockedKnowledgeWorkspaceTest(title: string) {
    return title.includes('knowledge saved draft provenance')
        || title.includes('knowledge structured draft preservation')
        || title.includes('knowledge remediation')
        || title.includes('knowledge lossy rewrite');
}

async function resolveAuthOrigin(page: import('@playwright/test').Page) {
    await page.goto(buildSignInUrl(baseURL), { waitUntil: 'domcontentloaded' });
    const providerForm = page.locator('form[action*="keycloak"]').first();
    const action = await providerForm.getAttribute('action');
    const actionOrigin = action ? new URL(action).origin : baseURL;
    resolvedBaseURL = stayOnBaseOrigin ? baseURL : actionOrigin;
}

async function gotoConsoleRoot(page: import('@playwright/test').Page) {
    await page.goto(resolvedBaseURL, { waitUntil: 'domcontentloaded' });
}

function keycloakAuthOptions() {
    return {
        baseURL,
        consoleHostPattern,
        keycloakHostPattern,
        stayOnBaseOrigin,
        allowLocalSessionBridge: shouldAllowLocalSessionBridge(baseURL),
        authWaitTimeoutMs: 15000,
        onResolvedOrigin: (origin: string) => {
            resolvedBaseURL = origin;
        },
    };
}

async function loginWithSharedHelper(page: import('@playwright/test').Page) {
    await loginThroughKeycloak(page, {
        ...keycloakAuthOptions(),
        loginUser,
        loginPassword,
    });
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

async function ensureLoggedIn(page: import('@playwright/test').Page) {
    await resolveAuthOrigin(page);
    await gotoConsoleRoot(page);
    const loginButton = page.getByTestId('login-button');
    const logoutButton = page.getByTestId('logout-button');
    await page.waitForSelector('[data-testid="login-button"], [data-testid="logout-button"]', { timeout: 15000 });
    if (!(await logoutButton.isVisible().catch(() => false)) && (await loginButton.isVisible().catch(() => false))) {
        await loginWithSharedHelper(page);
        await gotoConsoleRoot(page);
    }
    await resolveSelectionGate(page);
}

async function resolveConsoleRole(page: import('@playwright/test').Page) {
    return page.evaluate(async () => {
        const response = await fetch('/api/proxy/me', { credentials: 'include' }).catch(() => null);
        if (!response?.ok) {
            return null;
        }
        const payload = await response.json().catch(() => null) as { agent?: { role?: string } } | null;
        return payload?.agent?.role ?? null;
    });
}

async function requireOwnerAdminRoleOrSkip(page: import('@playwright/test').Page) {
    const role = await resolveConsoleRole(page);
    if (role && role !== 'owner' && role !== 'admin' && role !== 'platform_admin') {
        test.skip(true, `owner/admin/platform_admin credentials required for this lane; current role=${role}`);
    }
}

async function captureConsultantVerificationScreenshots(page: import('@playwright/test').Page) {
    if (!consultantVerificationScreenshotDir) {
        return;
    }

    mkdirSync(consultantVerificationScreenshotDir, { recursive: true });
    const originalViewport = page.viewportSize();
    const viewports = [
        { width: 390, height: 1400 },
        { width: 1024, height: 1600 },
        { width: 1280, height: 1600 },
        { width: 1440, height: 1600 },
    ];

    await page.evaluate(() => window.scrollTo(0, 0));
    for (const viewport of viewports) {
        await page.setViewportSize(viewport);
        await page.waitForTimeout(750);
        await page.screenshot({
            path: join(consultantVerificationScreenshotDir, `consultant-verification-${viewport.width}.png`),
            fullPage: true,
        });
    }

    if (originalViewport) {
        await page.setViewportSize(originalViewport);
    }
}

test.describe('Owner/Admin Business Control', () => {
    test.beforeEach(async ({ page }, testInfo) => {
        if (isMockedKnowledgeWorkspaceTest(testInfo.title)) {
            return;
        }
        await ensureLoggedIn(page);
        await gotoConsoleRoot(page);
    });

    test('should expose owner/admin control navigation and business summary', async ({ page }) => {
        await requireOwnerAdminRoleOrSkip(page);
        const navModeToggle = page.getByTestId('nav-owner-admin-toggle');
        if (!(await navModeToggle.isVisible().catch(() => false))) {
            await page.getByTestId('nav-toggle').click();
        }
        await expect(navModeToggle).toBeVisible();
        await expect(navModeToggle).toContainText('Показать расширенное меню');
        await navModeToggle.click();
        await expect(navModeToggle).toContainText('Скрыть расширенное меню');
        await navModeToggle.click();
        await expect(navModeToggle).toContainText('Показать расширенное меню');

        await expect(page.getByTestId('nav-business')).toBeVisible();
        await expect(page.getByTestId('nav-data-trust')).toBeVisible();
        await expect(page.getByTestId('nav-team-performance')).toBeVisible();
        await expect(page.getByTestId('nav-subscription')).toBeVisible();

        await page.getByTestId('nav-business').click();
        await expect(page).toHaveURL(urlPathPattern('/business'));
        await expect(page.getByTestId('business-title')).toBeVisible();
        await expect(page.getByTestId('business-status-card')).toBeVisible();
        await expect(page.getByTestId('business-today-plan')).toBeVisible();
        await expect(page.getByTestId('business-kpi-grid')).toBeVisible();
        await expect(page.getByTestId('business-actions')).toBeVisible();

        await expect(page.getByTestId('business-wave2-shortcuts')).toBeVisible();
        await page.getByRole('link', { name: 'Проверить качество данных' }).click();
        await expect(page).toHaveURL(urlPathPattern('/business/data-trust'));
        await expect(page.getByTestId('data-trust-title')).toBeVisible();
    });

    test('should render data-trust and team-performance operational surfaces', async ({ page }) => {
        await requireOwnerAdminRoleOrSkip(page);
        await page.getByTestId('nav-data-trust').click();
        await expect(page).toHaveURL(urlPathPattern('/business/data-trust'));
        await expect(page.getByTestId('data-trust-title')).toBeVisible();
        await expect(page.getByTestId('data-trust-status-card')).toBeVisible();
        await expect(page.getByTestId('data-trust-kpi-grid')).toBeVisible();
        await expect(page.getByTestId('data-trust-actions')).toBeVisible();

        await page.getByTestId('nav-team-performance').click();
        await expect(page).toHaveURL(urlPathPattern('/business/team-performance'));
        await expect(page.getByTestId('team-performance-title')).toBeVisible();
        await expect(page.getByTestId('team-performance-status-card')).toBeVisible();
        await expect(page.getByTestId('team-performance-kpi-grid')).toBeVisible();
        await expect(page.getByTestId('team-performance-actions')).toBeVisible();
        const quickProfile = page.getByTestId('team-performance-quick-profile');
        if (await quickProfile.isVisible().catch(() => false)) {
            await expect(page.getByTestId('team-performance-quick-profile-apply')).toBeVisible();
            await expect(page.getByTestId('team-performance-remediation-guide')).toBeVisible();
            await expect(page.getByTestId('team-performance-quick-profile-rollback-card')).toBeVisible();
            const operationState = page
                .getByTestId('team-performance-quick-profile-rollback-empty')
                .or(page.getByTestId('team-performance-operation-impact'));
            await expect(operationState).toBeVisible();
        }
        const teamTable = page.getByTestId('team-performance-table');
        const teamEmpty = page.getByText('Нет открытых заявок в текущем scope.');
        await expect(teamTable.or(teamEmpty)).toBeVisible();

        await page.getByTestId('nav-subscription').click();
        await expect(page).toHaveURL(urlPathPattern('/subscription'));
        await expect(page.getByTestId('subscription-title')).toBeVisible();
        await expect(page.getByTestId('subscription-contract')).toBeVisible();
        await expect(page.getByTestId('subscription-contract-health')).toBeVisible();
        await expect(page.getByTestId('subscription-reference-plan')).toBeVisible();
        await expect(page.getByTestId('subscription-meters')).toBeVisible();
        await expect(page.getByTestId('subscription-alert')).toBeVisible();
        await expect(page.getByTestId('subscription-forecast-v2')).toBeVisible();
        await expect(page.getByTestId('subscription-actions')).toBeVisible();
    });

    test('should render consultant verification overview foundation consultant verification', async ({ page }) => {
        await requireOwnerAdminRoleOrSkip(page);
        await expect(page.getByTestId('nav-consultant-verification')).toBeVisible();

        await page.getByTestId('nav-consultant-verification').click();
        await expect(page).toHaveURL(urlPathPattern('/business/consultant-verification'));
        await expect(page.getByTestId('consultant-verification-page')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-title')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-status-card')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-readiness-grid')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-examples')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-actions')).toBeVisible();
    });

    test('should render consultant verification chat workspace, scenario tools, compare, and findings when rollout is enabled consultant verification chat consultant verification scenarios consultant verification findings consultant verification compare', async ({ page }) => {
        test.slow();
        await requireOwnerAdminRoleOrSkip(page);
        await page.getByTestId('nav-consultant-verification').click();
        await expect(page).toHaveURL(urlPathPattern('/business/consultant-verification'));
        const featureGate = page.getByTestId('consultant-verification-feature-gate');
        if (await featureGate.isVisible().catch(() => false)) {
            test.skip(true, 'consultant verification rollout disabled for current client');
        }

        await expect(page.getByTestId('consultant-verification-workspace')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-session-list')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-explainer')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-composer')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-scenario-library')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-session-summary')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-compare')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-findings')).toBeVisible();

        await page.getByTestId('consultant-verification-mode-stress').click();
        await page.getByTestId('consultant-verification-start-session').click();
        await page.getByTestId('consultant-verification-composer-input').fill('Какие услуги у вас есть и что вы не можете сделать без менеджера?');
        await page.getByTestId('consultant-verification-send').click();

        await expect(page.getByTestId('consultant-verification-turn-1')).toBeVisible({ timeout: 30000 });
        await expect(page.getByTestId('consultant-verification-turn-2')).toBeVisible({ timeout: 30000 });
        await expect(page.getByTestId('consultant-verification-turn-verdict').first()).toBeVisible();
        await expect(page.getByTestId('consultant-verification-advanced-details')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-summary-answered')).toBeVisible();
        await expect(page.getByTestId('consultant-verification-summary-gap')).toBeVisible();

        await page.getByTestId('consultant-verification-finding-note').fill('Этот ответ нужно сохранить на разбор.');
        await page.getByTestId('consultant-verification-create-finding').click();
        await expect(page.getByTestId('consultant-verification-findings')).toContainText('Найденные слабые места');
        await expect(page.getByTestId('consultant-verification-compare-last-prompt')).toBeVisible();
        await captureConsultantVerificationScreenshots(page);
    });

    test('should restore saved draft provenance in knowledge workspace knowledge saved draft provenance', async ({ page }) => {
        await mockKnowledgeWorkspace(page, {
            current: {
                version_id: '55555555-5555-4555-8555-555555555555',
                payload: {
                    client_pack: {
                        salon: { name: 'Published Salon' },
                    },
                },
                content: JSON.stringify({
                    client_pack: {
                        salon: { name: 'Published Salon' },
                    },
                }, null, 2),
                updated_at: '2026-03-14T10:00:00Z',
                draft_version_id: '66666666-6666-4666-8666-666666666666',
                draft_payload: {
                    client_pack: {
                        salon: { name: 'Draft Salon' },
                    },
                },
                draft_content: JSON.stringify({
                    client_pack: {
                        salon: { name: 'Draft Salon' },
                    },
                }, null, 2),
                draft_updated_at: '2026-03-14T11:00:00Z',
                edit_base_source: 'draft',
                edit_base_version_id: '66666666-6666-4666-8666-666666666666',
                edit_base_payload: {
                    client_pack: {
                        salon: { name: 'Draft Salon' },
                    },
                },
                edit_base_content: JSON.stringify({
                    client_pack: {
                        salon: { name: 'Draft Salon' },
                    },
                }, null, 2),
                edit_base_updated_at: '2026-03-14T11:00:00Z',
            },
        });

        await page.goto(`${resolvedBaseURL}/knowledge`, { waitUntil: 'domcontentloaded' });
        await expect(page).toHaveURL(urlPathPattern('/knowledge'));
        await expect(page.getByTestId('knowledge-studio')).toBeVisible();
        await expect(page.getByTestId('knowledge-edit-base-card')).toContainText('сохраненный draft');
        await expect(page.getByTestId('knowledge-draft-textarea')).toHaveValue(/Draft Salon/);

        await page.getByTestId('knowledge-load-published').click();
        await expect(page.getByTestId('knowledge-draft-textarea')).toHaveValue(/Published Salon/);

        await page.getByTestId('knowledge-load-saved-draft').click();
        await expect(page.getByTestId('knowledge-draft-textarea')).toHaveValue(/Draft Salon/);
    });

    test('should preserve structured policy objects when building structured draft knowledge structured draft preservation', async ({ page }) => {
        const structuredPayload = {
            client_pack: {
                salon: {
                    name: 'Structured Salon',
                    city: 'Алматы',
                    address: { full: 'ул. Пример, 10' },
                    services_summary: 'Стрижки и окрашивание',
                    communication: { languages: ['ru', 'kk'] },
                    hours: {
                        days: 'Пн-Вс',
                        open: '10:00',
                        close: '21:00',
                    },
                },
                guest_policy: {
                    allow_new_clients: true,
                    deposit_required: false,
                },
                booking: {
                    collect_fields: ['service', 'date', 'time', 'name', 'phone'],
                    bot_can_confirm: true,
                },
                policy: {
                    payment_info: {
                        methods: ['card', 'cash'],
                    },
                    reschedule: {
                        notice_hours: 3,
                    },
                    cancel: {
                        notice_hours: 6,
                    },
                    discounts: {
                        rules: ['student'],
                    },
                },
                services_catalog: {
                    services: [{ name: 'Стрижка' }],
                },
            },
        };

        await mockKnowledgeWorkspace(page, {
            current: {
                version_id: '77777777-7777-4777-8777-777777777777',
                payload: structuredPayload,
                content: JSON.stringify(structuredPayload, null, 2),
                updated_at: '2026-03-14T10:00:00Z',
                edit_base_source: 'published',
                edit_base_version_id: '77777777-7777-4777-8777-777777777777',
                edit_base_payload: structuredPayload,
                edit_base_content: JSON.stringify(structuredPayload, null, 2),
                edit_base_updated_at: '2026-03-14T10:00:00Z',
            },
        });

        await page.goto(`${resolvedBaseURL}/knowledge`, { waitUntil: 'domcontentloaded' });
        await expect(page.getByTestId('knowledge-structured-warning')).toContainText('policy.payment_info');
        await expect(page.getByTestId('knowledge-structured-warning')).toContainText('guest_policy');

        await page.getByTestId('knowledge-build-structured-draft').click();
        const draftValue = await page.getByTestId('knowledge-draft-textarea').inputValue();
        const parsed = JSON.parse(draftValue);
        expect(parsed.client_pack.guest_policy).toEqual(structuredPayload.client_pack.guest_policy);
        expect(parsed.client_pack.policy.payment_info).toEqual(structuredPayload.client_pack.policy.payment_info);
        expect(parsed.client_pack.policy.reschedule).toEqual(structuredPayload.client_pack.policy.reschedule);
        expect(parsed.client_pack.policy.cancel).toEqual(structuredPayload.client_pack.policy.cancel);
        expect(parsed.client_pack.policy.discounts).toEqual(structuredPayload.client_pack.policy.discounts);
    });

    test('should show owner-readable remediation messages on validate knowledge remediation', async ({ page }) => {
        await mockKnowledgeWorkspace(page, {
            current: {
                version_id: '88888888-8888-4888-8888-888888888888',
                payload: {
                    client_pack: {
                        salon: { name: 'Needs Policy' },
                    },
                },
                content: JSON.stringify({
                    client_pack: {
                        salon: { name: 'Needs Policy' },
                    },
                }, null, 2),
                updated_at: '2026-03-14T10:00:00Z',
                edit_base_source: 'published',
                edit_base_version_id: '88888888-8888-4888-8888-888888888888',
                edit_base_payload: {
                    client_pack: {
                        salon: { name: 'Needs Policy' },
                    },
                },
                edit_base_content: JSON.stringify({
                    client_pack: {
                        salon: { name: 'Needs Policy' },
                    },
                }, null, 2),
                edit_base_updated_at: '2026-03-14T10:00:00Z',
            },
            validateResponse: {
                valid: false,
                errors: [
                    'Missing required field: client_pack.policy.payment_info',
                    'Missing required field: client_pack.policy.cancel',
                ],
                warnings: [],
                draft_hash: 'draft-hash-1',
                diff: '',
            },
        });

        await page.goto(`${resolvedBaseURL}/knowledge`, { waitUntil: 'domcontentloaded' });
        await page.getByTestId('knowledge-step-validate').click();
        await page.getByTestId('knowledge-validate-button').click();
        await expect(page.getByTestId('knowledge-validation-errors')).toContainText('Не заполнено: Политика: оплата');
        await expect(page.getByTestId('knowledge-validation-errors')).toContainText('Не заполнено: Политика: отмена');
        await expect(page.getByTestId('knowledge-validation-errors')).toContainText('Добавьте понятное объяснение оплаты');
        await expect(page.getByTestId('knowledge-validation-errors')).not.toContainText('Missing required field: client_pack.policy.payment_info');
    });

    test('should block saving lossy structured rewrites in knowledge validate flow knowledge lossy rewrite', async ({ page }) => {
        await mockKnowledgeWorkspace(page, {
            current: {
                version_id: '99999999-9999-4999-8999-999999999999',
                payload: {
                    client_pack: {
                        salon: { name: 'Structured Policy Salon' },
                        policy: {
                            payment_info: {
                                methods: ['card'],
                            },
                        },
                    },
                },
                content: JSON.stringify({
                    client_pack: {
                        salon: { name: 'Structured Policy Salon' },
                        policy: {
                            payment_info: {
                                methods: ['card'],
                            },
                        },
                    },
                }, null, 2),
                updated_at: '2026-03-14T10:00:00Z',
                edit_base_source: 'published',
                edit_base_version_id: '99999999-9999-4999-8999-999999999999',
                edit_base_payload: {
                    client_pack: {
                        salon: { name: 'Structured Policy Salon' },
                        policy: {
                            payment_info: {
                                methods: ['card'],
                            },
                        },
                    },
                },
                edit_base_content: JSON.stringify({
                    client_pack: {
                        salon: { name: 'Structured Policy Salon' },
                        policy: {
                            payment_info: {
                                methods: ['card'],
                            },
                        },
                    },
                }, null, 2),
                edit_base_updated_at: '2026-03-14T10:00:00Z',
            },
            validateResponse: {
                valid: false,
                errors: [
                    'Lossy structured field rewrite blocked: client_pack.policy.payment_info',
                ],
                warnings: [],
                draft_hash: 'draft-hash-structured-loss',
                draft_saved: false,
                diff: '',
            },
        });

        await page.goto(`${resolvedBaseURL}/knowledge`, { waitUntil: 'domcontentloaded' });
        await page.getByTestId('knowledge-step-validate').click();
        await page.getByTestId('knowledge-validate-button').click();
        await expect(page.getByTestId('knowledge-validation-errors')).toContainText('Нельзя упростить structured поле: Политика: оплата');
        await expect(page.getByTestId('knowledge-validation-draft-save-blocked')).toContainText('Черновик не сохранён на сервере');
        await expect(page.getByTestId('knowledge-validation-errors')).not.toContainText('Lossy structured field rewrite blocked: client_pack.policy.payment_info');
    });

    test('should render simple owner settings and explainability surface', async ({ page }) => {
        await requireOwnerAdminRoleOrSkip(page);
        await page.getByTestId('nav-settings').click();
        await expect(page).toHaveURL(urlPathPattern('/settings'));
        await expect(page.getByTestId('settings-simple-card')).toBeVisible();
        await expect(page.getByTestId('settings-after-save')).toBeVisible();
        await expect(page.getByTestId('settings-telegram-connector')).toBeVisible();
        await expect(page.getByTestId('settings-subscription-snapshot')).toBeVisible();
        await expect(page.getByTestId('settings-goal-mode')).toBeVisible();
        await expect(page.getByTestId('settings-goal-capture_leads')).toBeVisible();
        await expect(page.getByTestId('settings-goal-stable_quality')).toBeVisible();
        await expect(page.getByTestId('settings-goal-team_protection')).toBeVisible();
        await expect(page.getByTestId('settings-owner-operation')).toBeVisible();
        await expect(page.getByTestId('settings-input-reminder1')).toBeVisible();
        await expect(page.getByTestId('settings-input-reminder2')).toBeVisible();
        await expect(page.getByTestId('settings-input-escalation')).toBeVisible();
        await expect(page.getByTestId('settings-save-simple')).toBeVisible();

        await page.getByTestId('settings-preset-fast').click();
        await expect(page.getByTestId('settings-input-reminder1')).toHaveValue('5');
        await expect(page.getByTestId('settings-input-reminder2')).toHaveValue('30');
        await expect(page.getByTestId('settings-input-escalation')).toHaveValue('60');

        await page.getByTestId('settings-advanced-toggle').click();
        await expect(page.getByTestId('settings-branches')).toBeVisible();
    });
});
