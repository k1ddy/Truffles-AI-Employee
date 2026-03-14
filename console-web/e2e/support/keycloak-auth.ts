import { expect, type Page } from '@playwright/test';

export const DEFAULT_CONSOLE_HOST_PATTERN = /localhost(?::\d+)?|127\.0\.0\.1(?::\d+)?|192\.168\.5\.27:3000|console\.truffles\.kz/;
export const DEFAULT_KEYCLOAK_HOST_PATTERN = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;

type WaitForConsoleApp = (page: Page) => Promise<void>;

export type KeycloakAuthOptions = {
    baseURL: string;
    consoleHostPattern?: RegExp;
    keycloakHostPattern?: RegExp;
    stayOnBaseOrigin?: boolean;
    allowLocalSessionBridge?: boolean;
    localSessionBridgeBaseURL?: string;
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

export function shouldAllowLocalSessionBridge(baseURL: string) {
    try {
        const url = new URL(baseURL);
        const isLocalHost = /^(localhost|127\.0\.0\.1)$/.test(url.hostname);
        return !(isLocalHost && (url.port === '3000' || (!url.port && url.protocol === 'http:')));
    } catch {
        return true;
    }
}

function resolveLocalSessionBridgeBaseURL(options: KeycloakAuthOptions) {
    if (options.localSessionBridgeBaseURL) {
        return options.localSessionBridgeBaseURL;
    }
    return process.env.E2E_REMOTE_AUTH_BASE_URL ?? 'https://console.truffles.kz';
}

function resolvePreferredOrigin(baseURL: string, actionOrigin: string, stayOnBaseOrigin: boolean) {
    return stayOnBaseOrigin ? baseURL : actionOrigin;
}

function isConsoleAppUrl(urlString: string, consoleHostPattern: RegExp) {
    return consoleHostPattern.test(urlString) && !urlString.includes('/api/auth');
}

type ConsoleAuthState = {
    ok: boolean;
    sessionStatus: number | null;
    meStatus: number | null;
    sessionError?: string | null;
    hasAccessToken?: boolean;
};

async function readAuthenticatedConsoleState(page: Page): Promise<ConsoleAuthState> {
    return page.evaluate(async () => {
        try {
            const sessionResponse = await fetch("/api/auth/session", {
                credentials: "include",
                cache: "no-store",
            });
            if (!sessionResponse.ok) {
                return { ok: false, sessionStatus: sessionResponse.status, meStatus: null };
            }
            const session = await sessionResponse.json().catch(() => null) as
                | { accessToken?: string; error?: string }
                | null;
            if (!session?.accessToken || session.error) {
                return {
                    ok: false,
                    sessionStatus: sessionResponse.status,
                    meStatus: null,
                    sessionError: session?.error ?? null,
                    hasAccessToken: Boolean(session?.accessToken),
                };
            }

            const meResponse = await fetch("/api/proxy/me", {
                credentials: "include",
                cache: "no-store",
            }).catch(() => null);
            return {
                ok: Boolean(meResponse?.ok),
                sessionStatus: sessionResponse.status,
                meStatus: meResponse?.status ?? null,
            };
        } catch {
            return { ok: false, sessionStatus: null, meStatus: null };
        }
    });
}

async function resolveNoCredentialsState(page: Page, options: KeycloakLoginOptions) {
    await options.onNoCredentialsVisible?.(page);
    return readAuthenticatedConsoleState(page);
}

async function waitForAuthTransition(page: Page, options: KeycloakAuthOptions) {
    const keycloakHostPattern = options.keycloakHostPattern ?? DEFAULT_KEYCLOAK_HOST_PATTERN;
    const consoleHostPattern = options.consoleHostPattern ?? DEFAULT_CONSOLE_HOST_PATTERN;
    const authWaitTimeoutMs = options.authWaitTimeoutMs ?? 20000;
    const waitForConsoleApp = options.waitForConsoleApp;

    await Promise.race([
        page.waitForURL(keycloakHostPattern, { timeout: authWaitTimeoutMs, waitUntil: 'domcontentloaded' }),
        waitForConsoleApp
            ? waitForConsoleApp(page)
            : page.waitForURL((url) => isConsoleAppUrl(url.toString(), consoleHostPattern), {
                timeout: authWaitTimeoutMs,
                waitUntil: 'domcontentloaded',
            }),
    ]);
}

function findSessionCookieName(cookies: Array<{ name: string }>) {
    return cookies.find((cookie) =>
        cookie.name === '__Secure-next-auth.session-token'
        || cookie.name === 'next-auth.session-token'
        || cookie.name === '__Secure-authjs.session-token'
        || cookie.name === 'authjs.session-token'
    )?.name;
}

function toLocalCookieName(name: string) {
    return name.replace(/^__Secure-/, '').replace(/^__Host-/, '');
}

async function bridgeRemoteConsoleSessionToLocalBase(page: Page, options: KeycloakLoginOptions) {
    const baseURL = options.baseURL;
    if (!(options.allowLocalSessionBridge ?? true) || !shouldStayOnBaseOrigin(baseURL)) {
        return false;
    }

    const remoteConsoleBaseURL = resolveLocalSessionBridgeBaseURL(options);
    if (!remoteConsoleBaseURL || new URL(remoteConsoleBaseURL).origin === new URL(baseURL).origin) {
        return false;
    }

    const remotePage = await page.context().newPage();
    try {
        await loginThroughKeycloak(remotePage, {
            ...options,
            baseURL: remoteConsoleBaseURL,
            stayOnBaseOrigin: false,
            allowLocalSessionBridge: false,
            onResolvedOrigin: undefined,
            onNoCredentialsVisible: undefined,
            onPostLogin: undefined,
        });

        const cookies = await page.context().cookies(remoteConsoleBaseURL);
        const sessionCookieName = findSessionCookieName(cookies);
        if (!sessionCookieName) {
            throw new Error(`Remote console session cookie not found for ${remoteConsoleBaseURL}`);
        }

        const sessionCookie = cookies.find((cookie) => cookie.name === sessionCookieName);
        if (!sessionCookie) {
            throw new Error(`Remote console session cookie payload missing for ${remoteConsoleBaseURL}`);
        }

        const localOrigin = new URL(baseURL).origin;
        const localCookieName = toLocalCookieName(sessionCookie.name);
        await page.context().addCookies([
            {
                name: localCookieName,
                value: sessionCookie.value,
                url: localOrigin,
                httpOnly: true,
                secure: localOrigin.startsWith('https://'),
                sameSite: 'Lax',
                expires: sessionCookie.expires,
            },
        ]);
        await page.goto(baseURL, { waitUntil: 'domcontentloaded' });
        return true;
    } finally {
        await remotePage.close().catch(() => undefined);
    }
}

export async function startKeycloakLogin(page: Page, options: KeycloakAuthOptions) {
    const baseURL = options.baseURL;
    const stayOnBaseOrigin = options.stayOnBaseOrigin ?? shouldStayOnBaseOrigin(baseURL);
    const providerWaitTimeoutMs = options.providerWaitTimeoutMs ?? 15000;
    const baseOrigin = new URL(baseURL).origin;

    await page.goto(buildSignInUrl(baseURL), { waitUntil: 'domcontentloaded' });
    const providerForm = page.locator('form[action*="keycloak"]').first();
    const action = await providerForm.getAttribute('action');
    const actionOrigin = action ? new URL(action).origin : baseURL;
    const preferredOrigin = resolvePreferredOrigin(baseURL, actionOrigin, stayOnBaseOrigin);
    options.onResolvedOrigin?.(preferredOrigin);

    if (stayOnBaseOrigin && action) {
        const actionUrl = new URL(action);
        if (actionUrl.origin !== baseOrigin) {
            const normalizedAction = `${baseOrigin}${actionUrl.pathname}${actionUrl.search}`;
            await providerForm.evaluate((form, nextAction) => {
                form.setAttribute('action', nextAction);
            }, normalizedAction);
        }
    }

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
    const bridged = await bridgeRemoteConsoleSessionToLocalBase(page, options);
    if (bridged) {
        await options.onPostLogin?.(page);
        return true;
    }

    const started = await startKeycloakLogin(page, options);
    if (!started) {
        return false;
    }

    const usernameInput = page.locator('#username');
    await usernameInput.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null);
    if (!(await usernameInput.isVisible().catch(() => false))) {
        const initialState = await resolveNoCredentialsState(page, options);
        if (initialState.ok) {
            await options.onPostLogin?.(page);
            return true;
        }

        const retried = await startKeycloakLogin(page, options);
        if (!retried) {
            return false;
        }
        await usernameInput.waitFor({ state: 'visible', timeout: 5000 }).catch(() => null);
        if (!(await usernameInput.isVisible().catch(() => false))) {
            const retryState = await resolveNoCredentialsState(page, options);
            if (retryState.ok) {
                await options.onPostLogin?.(page);
                return true;
            }
            return false;
        }
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

export async function waitForAuthenticatedConsole(page: Page, timeoutMs = 20000) {
    await expect
        .poll(
            async () => readAuthenticatedConsoleState(page),
            { timeout: timeoutMs }
        )
        .toEqual(
            expect.objectContaining({ ok: true }),
        );
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
