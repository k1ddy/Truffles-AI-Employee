import { expect, type Page } from '@playwright/test';

export const DEFAULT_CONSOLE_HOST_PATTERN = /localhost:3000|localhost:3100|192\.168\.5\.27:3000|console\.truffles\.kz/;
export const DEFAULT_KEYCLOAK_HOST_PATTERN = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;

type WaitForConsoleApp = (page: Page) => Promise<void>;

export type KeycloakAuthOptions = {
    baseURL: string;
    consoleHostPattern?: RegExp;
    keycloakHostPattern?: RegExp;
    stayOnBaseOrigin?: boolean;
    authWaitTimeoutMs?: number;
    providerWaitTimeoutMs?: number;
    waitForConsoleApp?: WaitForConsoleApp;
    onResolvedOrigin?: (origin: string) => void;
};

export type KeycloakLoginOptions = KeycloakAuthOptions & {
    loginUser: string;
    loginPassword: string;
    onNoCredentialsVisible?: (page: Page) => Promise<void>;
    onPostLogin?: (page: Page) => Promise<void>;
};

export type AuthGateOptions = {
    logoutTestId?: string;
    ssoButtonName?: RegExp;
    loadingProfileText?: RegExp;
};

export function buildSignInUrl(origin: string, callbackOrigin = origin) {
    return `${origin}/api/auth/signin?callbackUrl=${encodeURIComponent(callbackOrigin)}`;
}

export function shouldStayOnBaseOrigin(baseURL: string) {
    return /localhost|127\.0\.0\.1/.test(baseURL);
}

function resolvePreferredOrigin(baseURL: string, actionOrigin: string, stayOnBaseOrigin: boolean) {
    return stayOnBaseOrigin ? baseURL : actionOrigin;
}

function isConsoleAppUrl(urlString: string, consoleHostPattern: RegExp) {
    return consoleHostPattern.test(urlString) && !urlString.includes('/api/auth');
}

async function waitForAuthTransition(page: Page, options: KeycloakAuthOptions) {
    const keycloakHostPattern = options.keycloakHostPattern ?? DEFAULT_KEYCLOAK_HOST_PATTERN;
    const consoleHostPattern = options.consoleHostPattern ?? DEFAULT_CONSOLE_HOST_PATTERN;
    const authWaitTimeoutMs = options.authWaitTimeoutMs ?? 20000;
    const waitForConsoleApp = options.waitForConsoleApp;

    await Promise.race([
        page.waitForURL(keycloakHostPattern, { timeout: authWaitTimeoutMs }),
        waitForConsoleApp
            ? waitForConsoleApp(page)
            : page.waitForURL((url) => isConsoleAppUrl(url.toString(), consoleHostPattern), { timeout: authWaitTimeoutMs }),
    ]);
}

export async function startKeycloakLogin(page: Page, options: KeycloakAuthOptions) {
    const baseURL = options.baseURL;
    const stayOnBaseOrigin = options.stayOnBaseOrigin ?? shouldStayOnBaseOrigin(baseURL);
    const providerWaitTimeoutMs = options.providerWaitTimeoutMs ?? 15000;

    await page.goto(buildSignInUrl(baseURL), { waitUntil: 'domcontentloaded' });
    const providerForm = page.locator('form[action*="keycloak"]').first();
    const action = await providerForm.getAttribute('action');
    const actionOrigin = action ? new URL(action).origin : baseURL;
    const preferredOrigin = resolvePreferredOrigin(baseURL, actionOrigin, stayOnBaseOrigin);
    options.onResolvedOrigin?.(preferredOrigin);

    const providerButton = page.getByRole('button', { name: /sign in with keycloak|войти через sso/i });
    await Promise.race([
        providerButton.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
        providerForm.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null),
    ]);
    if (await providerButton.isVisible().catch(() => false)) {
        await providerButton.click();
    } else if (await providerForm.isVisible().catch(() => false)) {
        await providerForm.waitFor({ state: 'visible', timeout: providerWaitTimeoutMs });
        const submitButton = providerForm
            .locator('button[type="submit"], input[type="submit"]')
            .first();
        await submitButton.click();
    } else {
        return false;
    }

    await waitForAuthTransition(page, options);
    return true;
}

export async function loginThroughKeycloak(page: Page, options: KeycloakLoginOptions) {
    const started = await startKeycloakLogin(page, options);
    if (!started) {
        return false;
    }

    const usernameInput = page.locator('#username');
    if (!(await usernameInput.isVisible().catch(() => false))) {
        await options.onNoCredentialsVisible?.(page);
        return true;
    }

    await expect(usernameInput).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await page.fill('#username', options.loginUser);
    await page.fill('#password', options.loginPassword);
    await page.click('#kc-login');

    const waitForConsoleApp = options.waitForConsoleApp;
    if (waitForConsoleApp) {
        await waitForConsoleApp(page);
    } else {
        const consoleHostPattern = options.consoleHostPattern ?? DEFAULT_CONSOLE_HOST_PATTERN;
        await page.waitForURL((url) => isConsoleAppUrl(url.toString(), consoleHostPattern), {
            timeout: options.authWaitTimeoutMs ?? 20000,
        });
    }

    await options.onPostLogin?.(page);
    return true;
}

export async function isAuthGateVisible(page: Page, options: AuthGateOptions = {}) {
    const logoutTestId = options.logoutTestId ?? 'logout-button';
    const ssoButtonName = options.ssoButtonName ?? /войти через sso/i;
    const loadingProfileText = options.loadingProfileText ?? /загрузка профиля/i;

    const logoutButton = page.getByTestId(logoutTestId).first();
    if (await logoutButton.isVisible().catch(() => false)) {
        return false;
    }

    const ssoButton = page.getByRole('button', { name: ssoButtonName }).first();
    const loadingProfile = page.getByText(loadingProfileText).first();
    return Boolean(
        (await ssoButton.isVisible().catch(() => false))
        || (await loadingProfile.isVisible().catch(() => false)),
    );
}
