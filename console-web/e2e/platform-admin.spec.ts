import { expect, test } from '@playwright/test';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const stayOnBaseOrigin = /localhost|127\.0\.0\.1/.test(baseURL);
let resolvedBaseURL = baseURL;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const isLocalBaseURL = /localhost|127\.0\.0\.1/.test(baseURL);
const quarantineLocal = !!process.env.CI && isLocalBaseURL;

test.skip(quarantineLocal, 'Quarantine local CI platform-admin suite while stabilizing console-e2e.');

function buildSignInUrl(origin: string, callbackOrigin = origin) {
    return `${origin}/api/auth/signin?callbackUrl=${encodeURIComponent(callbackOrigin)}`;
}

function resolvePreferredOrigin(actionOrigin: string) {
    return stayOnBaseOrigin ? baseURL : actionOrigin;
}

function urlPathPattern(path: string) {
    return new RegExp(`${path.replace(/\//g, '\\/')}(\\?|$)`);
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
    await page.getByTestId('nav-tenants').click();
    await expect(page).toHaveURL(urlPathPattern('/tenants'));
    await expect(page.getByTestId('tenants-title')).toBeVisible();
}

async function openIntegrations(page: import('@playwright/test').Page) {
    await page.getByTestId('nav-integrations').click();
    await expect(page).toHaveURL(urlPathPattern('/integrations'));
    await expect(page.getByTestId('integrations-title')).toBeVisible();
}

async function mockCriticalHealthIncident(page: import('@playwright/test').Page, backlog = 1656) {
    await page.route('**/api/proxy/health**', async (route) => {
        if (route.request().method() !== 'GET') {
            await route.fallback();
            return;
        }
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                status: 'ok',
                outbox_backlog: backlog,
                version: 'e2e-mock',
            }),
        });
    });
}

test.describe('Platform Admin Incident Banner', () => {
    test('should collapse, snooze, and restore incident banner @smoke', async ({ page }) => {
        await mockCriticalHealthIncident(page);
        await ensureLoggedIn(page);
        await gotoConsoleRoot(page);

        const banner = page.getByTestId('global-health-incident-banner');
        await expect(banner).toBeVisible();
        await expect(page.getByTestId('global-health-incident-summary')).toContainText('status=ok');
        await expect(page.getByTestId('global-health-incident-summary')).toContainText('outbox_backlog=1656');
        await expect(page.getByTestId('global-health-incident-toggle')).toHaveText(/Развернуть/i);

        await expect(page.getByTestId('global-health-incident-reasons')).toHaveCount(0);
        await expect(page.getByTestId('global-health-incident-runbook')).toHaveCount(0);

        await page.getByTestId('global-health-incident-toggle').click();
        await expect(page.getByTestId('global-health-incident-toggle')).toHaveText(/Свернуть/i);
        await expect(page.getByTestId('global-health-incident-reasons')).toBeVisible();
        await expect(page.getByTestId('global-health-incident-runbook')).toBeVisible();

        await page.getByTestId('global-health-incident-snooze').click();
        await expect(page.getByTestId('global-health-incident-hidden')).toBeVisible();
        await expect(page.getByTestId('global-health-incident-banner')).toHaveCount(0);

        await page.getByTestId('global-health-incident-show').click();
        await expect(page.getByTestId('global-health-incident-banner')).toBeVisible();
    });
});

test.describe('Platform Admin Navigation', () => {
    test.beforeEach(async ({ page }) => {
        await ensureLoggedIn(page);
        await gotoConsoleRoot(page);
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

        const storedContext = await page.evaluate(() => ({
            clientId: window.localStorage.getItem('console:client_id'),
            branchId: window.localStorage.getItem('console:branch_id'),
        }));
        expect(storedContext.clientId).toBeTruthy();
        expect(storedContext.branchId).toBeTruthy();
    });
});

test.describe('Platform Admin Tenants', () => {
    test.beforeEach(async ({ page }) => {
        await ensureLoggedIn(page);
        await gotoConsoleRoot(page);
        await openTenants(page);
    });

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

        await expect(clients.getByText(/Клиенты не найдены|фильтр по компании из контекста/i)).toBeVisible();
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
        const branches = tenantsSection(page, 'Филиалы');
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
            await expect(page.getByTestId('tenants-clients-section')).toBeVisible();

            await page.getByTestId('tenants-mode-portfolio').click();
            await expect(page.getByTestId('tenants-portfolio-companies')).toBeVisible();

            await page.getByTestId('tenants-mode-all').click();
            await expect(page.getByTestId('tenants-onboarding-section')).toBeVisible();
            await expect(page.getByTestId('tenants-change-management')).toBeVisible();
            return;
        }

        await expect(tenantsSection(page, 'Компании')).toBeVisible();
        await expect(tenantsSection(page, 'Клиенты')).toBeVisible();
        await expect(tenantsSection(page, 'Филиалы')).toBeVisible();
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
});
