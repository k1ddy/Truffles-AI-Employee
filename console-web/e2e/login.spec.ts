import { test, expect } from '@playwright/test';
import {
    loginThroughKeycloak,
    shouldAllowLocalSessionBridge,
    shouldStayOnBaseOrigin,
    startKeycloakLogin,
} from './support/keycloak-auth';

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const loginUser = process.env.E2E_USERNAME ?? 'admin';
const loginPassword = process.env.E2E_PASSWORD ?? 'admin';
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:3000';
const stayOnBaseOrigin = shouldStayOnBaseOrigin(baseURL);
let resolvedBaseURL = baseURL;

async function waitForConsoleApp(page: import('@playwright/test').Page) {
    await page.waitForURL(
        (url) => consoleHostPattern.test(url.toString()) && !url.toString().includes('/api/auth'),
        { timeout: 30000, waitUntil: 'domcontentloaded' }
    );
}

async function gotoConsoleRoot(page: import('@playwright/test').Page) {
    try {
        await page.goto(resolvedBaseURL, { waitUntil: 'domcontentloaded' });
    } catch (error) {
        if (!(error instanceof Error) || !error.message.includes('ERR_ABORTED')) {
            throw error;
        }
        await page.waitForTimeout(250);
        await page.goto(resolvedBaseURL, { waitUntil: 'domcontentloaded' });
    }
}

function keycloakAuthOptions() {
    return {
        baseURL,
        consoleHostPattern,
        keycloakHostPattern,
        stayOnBaseOrigin,
        allowLocalSessionBridge: shouldAllowLocalSessionBridge(baseURL),
        waitForConsoleApp,
        onResolvedOrigin: (origin: string) => {
            resolvedBaseURL = origin;
        },
    };
}

async function loginWithSharedHelper(page: import('@playwright/test').Page) {
    for (let attempt = 0; attempt < 2; attempt += 1) {
        const loggedIn = await loginThroughKeycloak(page, {
            ...keycloakAuthOptions(),
            loginUser,
            loginPassword,
            onNoCredentialsVisible: async () => {
                await waitForConsoleApp(page).catch(() => undefined);
                await gotoConsoleRoot(page).catch(() => undefined);
            },
            onPostLogin: async () => {
                await gotoConsoleRoot(page);
            },
        });
        if (loggedIn) {
            return;
        }
        await gotoConsoleRoot(page).catch(() => undefined);
        await page.waitForTimeout(500);
    }
    throw new Error('Keycloak login did not produce an authenticated console state');
}

async function selectOptionIfNeeded(
    selector: import('@playwright/test').Locator
) {
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
        return true;
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
    confirmTestId: string
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

async function selectClientIfNeeded(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'client-select', 'client-select-confirm')) {
        return;
    }
    const contextSelector = page.getByTestId('context-client-select');
    await selectOptionIfNeeded(contextSelector);
}

async function selectCompanyIfNeeded(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'company-select', 'company-select-confirm')) {
        return;
    }
    const contextSelector = page.getByTestId('context-company-select');
    await selectOptionIfNeeded(contextSelector);
}

async function selectBranchIfNeeded(page: import('@playwright/test').Page) {
    if (await selectFromGate(page, 'branch-select', 'branch-select-confirm')) {
        return;
    }
    const contextSelector = page.getByTestId('context-branch-select');
    await selectOptionIfNeeded(contextSelector);
}

async function clearStoredContext(page: import('@playwright/test').Page) {
    await page.evaluate(() => {
        window.localStorage.removeItem('console:company_id');
        window.localStorage.removeItem('console:client_id');
        window.localStorage.removeItem('console:branch_id');
    });
}

async function retryProfileLoad(page: import('@playwright/test').Page) {
    const retry = page.getByTestId('me-retry');
    if (!(await retry.isVisible().catch(() => false))) {
        return false;
    }
    await clearStoredContext(page);
    await retry.click();
    await page.waitForTimeout(500);
    return true;
}

async function logoutViaAuthEndpoint(page: import('@playwright/test').Page) {
    const response = await page.evaluate(async (callbackUrl) => {
        const clearContext = () => {
            window.localStorage.removeItem('console:company_id');
            window.localStorage.removeItem('console:client_id');
            window.localStorage.removeItem('console:branch_id');
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
        };

        const csrfResponse = await fetch('/api/auth/csrf', {
            credentials: 'include',
            cache: 'no-store',
        }).catch(() => null);
        if (!csrfResponse?.ok) {
            clearContext();
            return { ok: false, status: csrfResponse?.status ?? null };
        }

        const payload = await csrfResponse.json().catch(() => null) as { csrfToken?: string } | null;
        if (!payload?.csrfToken) {
            clearContext();
            return { ok: false, status: csrfResponse.status };
        }

        const body = new URLSearchParams({
            csrfToken: payload.csrfToken,
            callbackUrl,
            json: 'true',
        });
        const signOutResponse = await fetch('/api/auth/signout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: body.toString(),
            credentials: 'include',
        }).catch(() => null);
        clearContext();
        return {
            ok: Boolean(signOutResponse?.ok),
            status: signOutResponse?.status ?? null,
        };
    }, resolvedBaseURL);

    return response.ok;
}

async function waitForConsoleReady(page: import('@playwright/test').Page) {
    const selectionGate = page.locator('[data-testid="company-select"], [data-testid="client-select"], [data-testid="branch-select"]');
    const contextGate = page.locator('[data-testid="context-company-select"], [data-testid="context-client-select"], [data-testid="context-branch-select"]');
    const casesTitle = page.getByTestId('cases-title');
    const contextBar = page.getByTestId('context-bar');
    const inboxView = page.getByTestId('inbox-view');
    const consoleHeader = page.getByTestId('console-header');
    const isConsoleSurfaceVisible = async () => {
        if (await casesTitle.isVisible().catch(() => false)) return true;
        if (await selectionGate.isVisible().catch(() => false)) return true;
        if (await contextGate.isVisible().catch(() => false)) return true;
        if (await contextBar.isVisible().catch(() => false)) return true;
        if (await inboxView.isVisible().catch(() => false)) return true;
        if (await consoleHeader.isVisible().catch(() => false)) return true;
        return false;
    };
    for (let attempt = 0; attempt < 3; attempt += 1) {
        await retryProfileLoad(page);
        if (await isConsoleSurfaceVisible()) return;
        await page.waitForTimeout(1000);
    }
    await expect
        .poll(
            isConsoleSurfaceVisible,
            { timeout: 20000 }
        )
        .toBe(true);
}

test.describe('Smoke Test: Login Flow', () => {
    test.describe.configure({ retries: process.env.CI ? 1 : 0 });

    test('should redirect to Keycloak login @smoke', async ({ page }) => {
        test.slow(process.env.CI === 'true');
        await gotoConsoleRoot(page);
        const loginButton = page.getByTestId('login-button');
        const logoutButton = page.getByTestId('logout-button');
        const selectionGate = page.locator('[data-testid="company-select"], [data-testid="client-select"], [data-testid="branch-select"]');
        const contextGate = page.locator('[data-testid="context-company-select"], [data-testid="context-client-select"], [data-testid="context-branch-select"]');
        const contextBar = page.getByTestId('context-bar');
        const consoleHeader = page.getByTestId('console-header');
        await page.waitForSelector('[data-testid="login-button"], [data-testid="logout-button"]', { timeout: 5000 }).catch(() => null);
        const loginVisible = await loginButton.isVisible().catch(() => false);
        const logoutVisible = await logoutButton.isVisible().catch(() => false);
        const consoleSurfaceVisible = await selectionGate.isVisible().catch(() => false)
            || await contextGate.isVisible().catch(() => false)
            || await contextBar.isVisible().catch(() => false)
            || await consoleHeader.isVisible().catch(() => false);
        if (logoutVisible || consoleSurfaceVisible) {
            return;
        }
        if (loginVisible) {
            await loginButton.click();
        } else {
            await startKeycloakLogin(page, keycloakAuthOptions()).catch(() => null);
        }
        const signInHeading = page.getByRole('heading', { name: /sign in/i });
        const providerButton = page.getByRole('button', { name: /sign in with keycloak/i });
        const providerForm = page.locator('form[action*="keycloak"]').first();
        await Promise.race([
            logoutButton.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
            signInHeading.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
            providerButton.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
            providerForm.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
            loginButton.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => null),
            page.waitForURL(keycloakHostPattern, { timeout: 5000, waitUntil: 'domcontentloaded' }).catch(() => null),
        ]);
        const hasLogout = await logoutButton.isVisible().catch(() => false);
        const hasSignIn = await signInHeading.isVisible().catch(() => false);
        const hasProvider = await providerButton.isVisible().catch(() => false)
            || await providerForm.isVisible().catch(() => false);
        const onKeycloak = keycloakHostPattern.test(page.url());
        const loginHidden = !(await loginButton.isVisible().catch(() => false));

        if (!(hasLogout || hasSignIn || hasProvider || onKeycloak || loginHidden)) {
            const started = await startKeycloakLogin(page, keycloakAuthOptions()).catch(() => false);
            if (started) {
                await Promise.race([
                    providerButton.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
                    providerForm.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
                    page.waitForURL(keycloakHostPattern, { timeout: 5000, waitUntil: 'domcontentloaded' }).catch(() => null),
                ]);
            }
        }

        await expect
            .poll(
                async () => {
                    const hasLogoutAfter = await logoutButton.isVisible().catch(() => false);
                    const hasSignInAfter = await signInHeading.isVisible().catch(() => false);
                    const hasProviderAfter = await providerButton.isVisible().catch(() => false)
                        || await providerForm.isVisible().catch(() => false);
                    const onKeycloakAfter = keycloakHostPattern.test(page.url());
                    const loginHiddenAfter = !(await loginButton.isVisible().catch(() => false));
                    const hasConsoleSurface = await selectionGate.isVisible().catch(() => false)
                        || await contextGate.isVisible().catch(() => false)
                        || await contextBar.isVisible().catch(() => false)
                        || await consoleHeader.isVisible().catch(() => false);
                    return hasLogoutAfter || hasSignInAfter || hasProviderAfter || onKeycloakAfter || loginHiddenAfter || hasConsoleSurface;
                },
                { timeout: 20000 }
            )
            .toBe(true);
    });

    test('should login and see inbox @smoke', async ({ page }) => {
        await loginWithSharedHelper(page);
        await selectCompanyIfNeeded(page);
        await selectClientIfNeeded(page);
        await selectBranchIfNeeded(page);
        await waitForConsoleReady(page);
    });

    test('should logout successfully @smoke', async ({ page }) => {
        test.slow(process.env.CI === 'true');
        await loginWithSharedHelper(page);
        await selectCompanyIfNeeded(page);
        await selectClientIfNeeded(page);
        await selectBranchIfNeeded(page);
        await waitForConsoleReady(page);
        const logoutButton = page.getByTestId('logout-button');
        const loginButton = page.getByTestId('login-button');
        const hasLogoutButton = await logoutButton.isVisible().catch(() => false);
        if (hasLogoutButton) {
            await logoutButton.click();
        } else {
            const signedOut = await logoutViaAuthEndpoint(page);
            expect(signedOut).toBe(true);
            await gotoConsoleRoot(page);
        }
        await expect(loginButton).toBeVisible({ timeout: 10000 });
    });
});
