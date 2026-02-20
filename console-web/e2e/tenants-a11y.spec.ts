import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const REPORT_ARTIFACTS_DIR = path.resolve(
    __dirname,
    "..",
    "..",
    "docs",
    "REPORTS",
    "artifacts",
    "2026-02-20-tenants-a11y",
);
const consoleHostPattern = /localhost:3000|192\.168\.5\.27:3000|console\.truffles\.kz/;
const keycloakHostPattern = /localhost:8080|192\.168\.5\.27:8080|auth\.truffles\.kz/;
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const stayOnBaseOrigin = /localhost|127\.0\.0\.1/.test(baseURL);
const loginUser = process.env.E2E_USERNAME ?? "admin";
const loginPassword = process.env.E2E_PASSWORD ?? "admin";
const failOnThresholds = process.env.A11Y_FAIL_ON_THRESHOLDS === "1";
let resolvedBaseURL = baseURL;

type AxeImpact = "minor" | "moderate" | "serious" | "critical";

type AxeSummary = {
    url: string;
    timestamp: string;
    violations_total: number;
    impacts: Record<AxeImpact, number>;
    violations: Array<{
        id: string;
        impact: AxeImpact | null;
        description: string;
        help: string;
        nodes: number;
        targets: string[];
    }>;
};

function buildSignInUrl(origin: string, callbackOrigin = origin) {
    return `${origin}/api/auth/signin?callbackUrl=${encodeURIComponent(callbackOrigin)}`;
}

function resolvePreferredOrigin(actionOrigin: string) {
    return stayOnBaseOrigin ? baseURL : actionOrigin;
}

function urlPathPattern(pathValue: string) {
    return new RegExp(`${pathValue.replace(/\//g, "\\/")}(\\?|$)`);
}

async function selectOptionIfNeeded(selector: import("@playwright/test").Locator) {
    if (!(await selector.isVisible().catch(() => false))) {
        return false;
    }
    const currentValue = await selector.inputValue();
    if (currentValue) {
        return true;
    }
    const options = selector.locator("option");
    const optionCount = await options.count();
    if (optionCount < 2) {
        return false;
    }
    const value = await options.nth(1).getAttribute("value");
    if (value) {
        await selector.selectOption(value);
    } else {
        await selector.selectOption({ index: 1 });
    }
    await expect(selector).not.toHaveValue("");
    return true;
}

async function selectFromGate(
    page: import("@playwright/test").Page,
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

async function resolveSelectionGate(page: import("@playwright/test").Page) {
    if (await selectFromGate(page, "company-select", "company-select-confirm")) {
        await page.waitForLoadState("domcontentloaded");
    }
    if (await selectFromGate(page, "client-select", "client-select-confirm")) {
        await page.waitForLoadState("domcontentloaded");
    }
    if (await selectFromGate(page, "branch-select", "branch-select-confirm")) {
        await page.waitForLoadState("domcontentloaded");
    }

    await selectOptionIfNeeded(page.getByTestId("context-company-select"));
    await selectOptionIfNeeded(page.getByTestId("context-client-select"));
    await selectOptionIfNeeded(page.getByTestId("context-branch-select"));
}

async function startKeycloakLogin(page: import("@playwright/test").Page) {
    await page.goto(buildSignInUrl(baseURL), { waitUntil: "domcontentloaded" });
    let providerForm = page.locator('form[action*="keycloak"]').first();
    const action = await providerForm.getAttribute("action");
    const actionOrigin = action ? new URL(action).origin : baseURL;
    if (actionOrigin !== baseURL) {
        const callbackOrigin = stayOnBaseOrigin ? baseURL : actionOrigin;
        await page.goto(buildSignInUrl(actionOrigin, callbackOrigin), { waitUntil: "domcontentloaded" });
        providerForm = page.locator('form[action*="keycloak"]').first();
    }
    resolvedBaseURL = resolvePreferredOrigin(actionOrigin);
    const providerButton = page.getByRole("button", { name: /sign in with keycloak/i });
    if (await providerButton.isVisible().catch(() => false)) {
        await providerButton.click();
    } else if (await providerForm.isVisible().catch(() => false)) {
        await providerForm.waitFor({ state: "visible", timeout: 15000 });
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

async function loginThroughKeycloak(page: import("@playwright/test").Page) {
    const started = await startKeycloakLogin(page);
    if (!started) {
        return;
    }
    if (!(await page.locator("#username").isVisible().catch(() => false))) {
        return;
    }
    await page.fill("#username", loginUser);
    await page.fill("#password", loginPassword);
    await page.click("#kc-login");
    await page.waitForURL(consoleHostPattern);
}

async function gotoConsoleRoot(page: import("@playwright/test").Page) {
    await page.goto(resolvedBaseURL, { waitUntil: "domcontentloaded" });
}

async function ensureLoggedIn(page: import("@playwright/test").Page) {
    await gotoConsoleRoot(page);
    const loginButton = page.getByTestId("login-button");
    const logoutButton = page.getByTestId("logout-button");
    await page.waitForSelector('[data-testid="login-button"], [data-testid="logout-button"]', { timeout: 15000 });
    if (!(await logoutButton.isVisible().catch(() => false)) && (await loginButton.isVisible().catch(() => false))) {
        await loginThroughKeycloak(page);
        await gotoConsoleRoot(page);
    }
    await resolveSelectionGate(page);
}

async function openTenants(page: import("@playwright/test").Page) {
    await page.goto(`${resolvedBaseURL}/tenants`, { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(urlPathPattern("/tenants"));
    await expect(page.getByTestId("tenants-title")).toBeVisible();
}

function summarizeAxe(result: Awaited<ReturnType<AxeBuilder["analyze"]>>, url: string): AxeSummary {
    const impacts: Record<AxeImpact, number> = {
        minor: 0,
        moderate: 0,
        serious: 0,
        critical: 0,
    };
    for (const violation of result.violations) {
        if (violation.impact && violation.impact in impacts) {
            impacts[violation.impact as AxeImpact] += 1;
        }
    }
    return {
        url,
        timestamp: new Date().toISOString(),
        violations_total: result.violations.length,
        impacts,
        violations: result.violations.map((violation) => ({
            id: violation.id,
            impact: violation.impact as AxeImpact | null,
            description: violation.description,
            help: violation.help,
            nodes: violation.nodes.length,
            targets: violation.nodes.map((node) => JSON.stringify(node.target)),
        })),
    };
}

async function captureTenantsArtifacts(
    page: import("@playwright/test").Page,
    variant: "desktop" | "mobile",
): Promise<AxeSummary> {
    fs.mkdirSync(REPORT_ARTIFACTS_DIR, { recursive: true });
    await page.waitForTimeout(400);

    const screenshotPath = path.join(REPORT_ARTIFACTS_DIR, `tenants-${variant}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const axeResult = await new AxeBuilder({ page }).analyze();
    const summary = summarizeAxe(axeResult, page.url());
    const summaryPath = path.join(REPORT_ARTIFACTS_DIR, `tenants-${variant}-axe.json`);
    fs.writeFileSync(summaryPath, `${JSON.stringify(summary, null, 2)}\n`, "utf-8");

    if (failOnThresholds) {
        expect(summary.impacts.critical, `${variant} critical axe violations`).toBe(0);
        expect(summary.impacts.serious, `${variant} serious axe violations`).toBe(0);
    }
    return summary;
}

test.describe("Tenants a11y evidence", () => {
    test.describe.configure({ timeout: 120000 });

    test.beforeEach(async ({ page }) => {
        await ensureLoggedIn(page);
        await gotoConsoleRoot(page);
        await openTenants(page);
    });

    test("desktop snapshot + axe @smoke", async ({ page }) => {
        await expect(page.getByTestId("tenants-workspace-guide")).toBeVisible();
        const summary = await captureTenantsArtifacts(page, "desktop");
        test.info().annotations.push({
            type: "a11y-desktop",
            description: `critical=${summary.impacts.critical}, serious=${summary.impacts.serious}`,
        });
    });

    test.describe("mobile", () => {
        test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

        test("mobile snapshot + axe @smoke", async ({ page }) => {
            await expect(page.getByTestId("tenants-workspace-guide")).toBeVisible();
            const summary = await captureTenantsArtifacts(page, "mobile");
            test.info().annotations.push({
                type: "a11y-mobile",
                description: `critical=${summary.impacts.critical}, serious=${summary.impacts.serious}`,
            });
        });
    });
});
