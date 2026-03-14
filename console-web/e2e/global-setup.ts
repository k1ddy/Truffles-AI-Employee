import { chromium, type FullConfig } from "@playwright/test";
import {
    loginThroughKeycloak,
    shouldStayOnBaseOrigin,
    waitForAuthenticatedConsole,
} from "./support/keycloak-auth";

const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;

function escapeRegex(value: string) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function buildConsoleHostPattern(baseURL: string) {
    const host = new URL(baseURL).host;
    return new RegExp(
        `${escapeRegex(host)}|localhost(?::\\d+)?|127\\.0\\.0\\.1(?::\\d+)?|192\\.168\\.5\\.27:3000|console\\.truffles\\.kz`,
    );
}

async function waitForConsoleApp(
    page: import("@playwright/test").Page,
    consoleHostPattern: RegExp,
) {
    if (consoleHostPattern.test(page.url()) && !page.url().includes("/api/auth")) {
        return;
    }
    await page.waitForURL(
        (url) => consoleHostPattern.test(url.toString()) && !url.toString().includes("/api/auth"),
        { timeout: 30000 }
    );
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
    const consoleHostPattern = buildConsoleHostPattern(baseURL);
    const browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    const stayOnBaseOrigin = shouldStayOnBaseOrigin(baseURL);
    const logoutButton = page.getByTestId("logout-button");
    await page.goto(baseURL, { waitUntil: "domcontentloaded" });
    await loginThroughKeycloak(page, {
        baseURL,
        consoleHostPattern,
        keycloakHostPattern,
        stayOnBaseOrigin,
        allowLocalSessionBridge: false,
        loginUser: username,
        loginPassword: password,
        authWaitTimeoutMs: Number.parseInt(process.env.E2E_LOGIN_TRANSITION_TIMEOUT_MS ?? "60000", 10),
        onNoCredentialsVisible: async () => {
            await waitForConsoleApp(page, consoleHostPattern);
        },
        onPostLogin: async () => {
            if (!consoleHostPattern.test(page.url())) {
                await waitForConsoleApp(page, consoleHostPattern);
            }
            await page.goto(baseURL, { waitUntil: "domcontentloaded" });
        },
    });

    await page.waitForLoadState("domcontentloaded");
    await waitForAuthenticatedConsole(page, 30000);
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

    await context.storageState({ path: "e2e/.auth/state.json" });
    await browser.close();
}
