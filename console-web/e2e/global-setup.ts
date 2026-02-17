import { chromium, type FullConfig } from "@playwright/test";

const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;

function buildSignInUrl(baseUrl: string, basePath: string) {
    return `${baseUrl}${basePath}/signin?callbackUrl=${encodeURIComponent(baseUrl)}`;
}

async function resolveNextAuthBase(page: import("@playwright/test").Page, fallbackBaseURL: string) {
    const nextAuth = await page
        .waitForFunction(() => {
            return (window as typeof window & { __NEXTAUTH?: { baseUrl?: string; basePath?: string } }).__NEXTAUTH ?? null;
        }, { timeout: 5000 })
        .then((handle) => handle.jsonValue() as { baseUrl?: string; basePath?: string })
        .catch(() => null);
    const baseUrl = typeof nextAuth?.baseUrl === "string" ? nextAuth.baseUrl : fallbackBaseURL;
    const basePath = typeof nextAuth?.basePath === "string" ? nextAuth.basePath : "/api/auth";
    return { baseUrl, basePath };
}

async function waitForConsoleApp(page: import("@playwright/test").Page) {
    await page.waitForURL(
        (url) => consoleHostPattern.test(url.toString()) && !url.toString().includes("/api/auth"),
        { timeout: 30000 }
    );
}

async function startKeycloakLogin(page: import("@playwright/test").Page, baseURL: string) {
    await page.goto(baseURL, { waitUntil: "domcontentloaded" });

    const logoutButton = page.getByTestId("logout-button");
    if (await logoutButton.isVisible().catch(() => false)) {
        return "logged-in";
    }

    const loginButton = page.getByTestId("login-button");
    if (await loginButton.waitFor({ state: "visible", timeout: 10000 }).catch(() => false)) {
        await loginButton.click();
        return "started";
    }

    if (keycloakHostPattern.test(page.url())) {
        return "started";
    }

    const { baseUrl: authBaseUrl, basePath: authBasePath } = await resolveNextAuthBase(page, baseURL);
    const signInUrl = buildSignInUrl(authBaseUrl, authBasePath);
    const signInResponse = await page.goto(signInUrl, { waitUntil: "domcontentloaded" });
    const providerForm = page.locator('form[action*="keycloak"]').first();
    const providerButton = page.getByRole("button", { name: /sign in with keycloak/i });

    if (await providerButton.isVisible().catch(() => false)) {
        await providerButton.click();
        return "started";
    }

    if (await providerForm.isVisible().catch(() => false)) {
        await providerForm.waitFor({ state: "visible", timeout: 15000 });
        const submitButton = providerForm
            .locator('button[type="submit"], input[type="submit"]')
            .first();
        await submitButton.click();
        return "started";
    }

    throw new Error(`Keycloak sign-in not reachable (status ${signInResponse?.status() ?? "unknown"})`);
}

export default async function globalSetup(config: FullConfig) {
    if (process.env.E2E_USE_STORAGE_STATE !== "1") {
        return;
    }

    const username = process.env.E2E_USERNAME;
    const password = process.env.E2E_PASSWORD;
    if (!username || !password) {
        throw new Error("E2E_USERNAME and E2E_PASSWORD are required for storageState");
    }

    const projectBaseURL = config.projects[0]?.use?.baseURL;
    const baseURL = process.env.PLAYWRIGHT_BASE_URL
        ?? (typeof projectBaseURL === "string" ? projectBaseURL : undefined)
        ?? "http://localhost:3000";
    const loginTransitionTimeoutMs = Number.parseInt(
        process.env.E2E_LOGIN_TRANSITION_TIMEOUT_MS ?? "60000",
        10,
    );
    const browser = await chromium.launch();
    const page = await browser.newPage();

    const loginState = await startKeycloakLogin(page, baseURL);
    const logoutButton = page.getByTestId("logout-button");

    if (loginState !== "logged-in") {
        await Promise.any([
            page.waitForURL(keycloakHostPattern, { timeout: loginTransitionTimeoutMs }),
            logoutButton.waitFor({ state: "visible", timeout: loginTransitionTimeoutMs }),
        ]);

        if (keycloakHostPattern.test(page.url())) {
            await page.waitForSelector("#username", { timeout: loginTransitionTimeoutMs });
            await page.fill("#username", username);
            await page.fill("#password", password);
            await page.click("#kc-login");
        }

        await waitForConsoleApp(page);
    }

    await page.waitForLoadState("domcontentloaded");
    await logoutButton.waitFor({ state: "visible", timeout: 20000 });

    const envClientId = process.env.E2E_CLIENT_ID;
    const envBranchId = process.env.E2E_BRANCH_ID;
    const meData = await page.evaluate(async () => {
        const response = await fetch("/api/proxy/me");
        if (!response.ok) {
            return null;
        }
        return response.json();
    });
    const accessibleClients: string[] = [];
    if (meData?.clients?.length) {
        accessibleClients.push(...meData.clients.map((client: { id?: string }) => client.id).filter(Boolean));
    } else if (meData?.client?.id) {
        accessibleClients.push(meData.client.id as string);
    }

    let selectedClientId = envClientId ?? null;
    if (!selectedClientId || (accessibleClients.length && !accessibleClients.includes(selectedClientId))) {
        selectedClientId = accessibleClients[0] ?? null;
    }
    if (selectedClientId) {
        await page.evaluate((id) => {
            window.localStorage.setItem("console:client_id", id);
            window.localStorage.removeItem("console:branch_id");
        }, selectedClientId);
    }

    let selectedBranchId = envBranchId ?? null;
    if (selectedClientId) {
        const resolvedBranch = await page.evaluate(async (clientId) => {
            const response = await fetch("/api/proxy/me", {
                headers: { "X-Client-Id": clientId },
            });
            if (!response.ok) {
                return { required: false, ids: [] as string[] };
            }
            const data = await response.json();
            const ids = Array.isArray(data?.branches)
                ? data.branches.map((branch: { id?: string }) => branch.id).filter(Boolean)
                : [];
            return { required: !!data?.branch_selection_required, ids };
        }, selectedClientId);
        if (selectedBranchId && !resolvedBranch.ids.includes(selectedBranchId)) {
            selectedBranchId = null;
        }
        if (!selectedBranchId && resolvedBranch.required) {
            selectedBranchId = resolvedBranch.ids[0] ?? null;
        }
    }
    if (selectedBranchId) {
        await page.evaluate((id) => {
            window.localStorage.setItem("console:branch_id", id);
        }, selectedBranchId);
    }

    await page.context().storageState({ path: "e2e/.auth/state.json" });
    await browser.close();
}
