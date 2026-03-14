import { mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from '@playwright/test';
import {
    buildSignInUrl,
    loginThroughKeycloak,
    shouldAllowLocalSessionBridge,
    shouldStayOnBaseOrigin,
    waitForAuthenticatedConsole,
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
    await waitForAuthenticatedConsole(page, 30000);
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
    test.beforeEach(async ({ page }) => {
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
