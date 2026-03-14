import { expect, test } from '@playwright/test';
import {
    buildSignInUrl,
    loginThroughKeycloak,
    shouldAllowLocalSessionBridge,
    shouldStayOnBaseOrigin,
} from './support/keycloak-auth';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const stayOnBaseOrigin = shouldStayOnBaseOrigin(baseURL);
let resolvedBaseURL = baseURL;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const runMutations = process.env.E2E_ALLOW_MUTATIONS === '1';

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

test.describe('Marketing Page', () => {
    test.beforeEach(async ({ page }) => {
        await ensureLoggedIn(page);
        await gotoConsoleRoot(page);
    });

    test('should open marketing page and render lifecycle blocks @smoke', async ({ page }) => {
        const marketingNav = page.getByTestId('nav-marketing');
        if (!(await marketingNav.isVisible().catch(() => false))) {
            return;
        }

        await marketingNav.click();
        await expect(page).toHaveURL(urlPathPattern('/marketing'));
        await expect(page.getByRole('heading', { name: 'Маркетинг' })).toBeVisible();
        await expect(page.getByText('Понятный поток для владельца')).toBeVisible();
        await expect(page.getByRole('button', { name: 'Проверить аудиторию' })).toBeVisible();
        await expect(page.getByText('Готовность к отправке')).toBeVisible();
        await expect(page.getByText('Клиенты для рассылки')).toBeVisible();
        await expect(page.getByText('Результаты отправки')).toBeVisible();
    });
});

test.describe('Marketing lifecycle @mutating', () => {
    test.skip(!runMutations, 'Mutating tests are disabled');

    test.beforeEach(async ({ page }) => {
        await ensureLoggedIn(page);
        await gotoConsoleRoot(page);
    });

    test('should create campaign and open execute modal @mutating', async ({ page }) => {
        const marketingNav = page.getByTestId('nav-marketing');
        if (!(await marketingNav.isVisible().catch(() => false))) {
            return;
        }

        await marketingNav.click();
        await expect(page).toHaveURL(urlPathPattern('/marketing'));

        const campaignName = `E2E MK ${Date.now()}`;
        await page.getByPlaceholder('Название').fill(campaignName);
        await page
            .getByPlaceholder('Текст WhatsApp сообщения')
            .fill('Напоминаем о визите. Ответьте, если хотите подобрать удобное время.');
        await page.getByRole('button', { name: 'Создать кампанию' }).click();

        const campaignButton = page.getByRole('button', { name: new RegExp(campaignName) }).first();
        await expect(campaignButton).toBeVisible({ timeout: 15000 });
        await campaignButton.click();

        await page.getByRole('button', { name: 'Проверить аудиторию' }).click();
        await page.getByRole('button', { name: 'На ревью' }).click();

        const approveButton = page.getByRole('button', { name: 'Подтвердить' });
        await expect(approveButton).toBeEnabled({ timeout: 10000 });
        await approveButton.click();

        await page.getByRole('button', { name: 'Проверить готовность' }).click();
        const executeModalButton = page.getByRole('button', { name: 'Проверить и отправить' });
        await expect(executeModalButton).toBeVisible();
        await executeModalButton.click();

        await expect(page.getByRole('heading', { name: 'Подтверждение отправки' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Подтвердить отправку' })).toBeVisible();
        await page.getByRole('button', { name: 'Закрыть' }).click();
    });
});
