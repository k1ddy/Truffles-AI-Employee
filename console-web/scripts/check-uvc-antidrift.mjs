#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const consoleRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(consoleRoot, "..");

function readUtf8(relativePath) {
    const fullPath = path.resolve(repoRoot, relativePath);
    return fs.readFileSync(fullPath, "utf8");
}

function fail(message, details = []) {
    console.error(`UVC anti-drift check failed: ${message}`);
    for (const detail of details) {
        console.error(`- ${detail}`);
    }
    process.exit(1);
}

function ensureIncludes(content, needle, label) {
    if (!content.includes(needle)) {
        fail(`missing required token: ${needle}`, [label]);
    }
}

function normalizeText(value) {
    return value.replace(/\r\n/g, "\n").trimEnd();
}

function runOpenApiTypescriptSnapshot() {
    const npxCommand = process.platform === "win32" ? "npx.cmd" : "npx";
    return execFileSync(
        npxCommand,
        ["openapi-typescript", "../contracts/console_api/openapi.v1.yaml"],
        {
            cwd: consoleRoot,
            encoding: "utf8",
            stdio: ["ignore", "pipe", "pipe"],
        },
    );
}

const openApiSpec = readUtf8("contracts/console_api/openapi.v1.yaml");
const generatedTypes = readUtf8("console-web/src/types/api.generated.ts");
const apiClient = readUtf8("console-web/src/lib/api-client.ts");
const e2eSpec = readUtf8("console-web/e2e/platform-admin.spec.ts");
const integrationsPage = readUtf8("console-web/src/app/integrations/page.tsx");
const workspacePage = readUtf8("console-web/src/app/company-workspace/page.tsx");
const tenantsPage = readUtf8("console-web/src/app/tenants/tenants-page-view.tsx");
const opsPage = readUtf8("console-web/src/components/OpsPage.tsx");

const freshGeneratedSnapshot = normalizeText(runOpenApiTypescriptSnapshot());
if (normalizeText(generatedTypes) !== freshGeneratedSnapshot) {
    fail("console-web/src/types/api.generated.ts is out of date with OpenAPI.", [
        "Run: cd console-web && npm run generate:api",
        "Commit the regenerated file before merge.",
    ]);
}

const requiredControlTowerPaths = [
    "/console/v1/admin/control-tower/overview",
    "/console/v1/admin/control-tower/readiness-board",
    "/console/v1/admin/control-tower/drift-board",
    "/console/v1/admin/control-tower/action-center",
    "/console/v1/admin/control-tower/migration-program",
    "/console/v1/admin/control-tower/migration-program/{wave}",
];

for (const endpointPath of requiredControlTowerPaths) {
    ensureIncludes(openApiSpec, endpointPath, "contracts/console_api/openapi.v1.yaml");
    ensureIncludes(generatedTypes, endpointPath, "console-web/src/types/api.generated.ts");
}

const requiredApiClientMethods = [
    "getControlTowerOverview",
    "getControlTowerReadinessBoard",
    "getControlTowerDriftBoard",
    "getControlTowerActionCenter",
    "getControlTowerMigrationProgram",
    "getControlTowerMigrationWave",
];

for (const methodName of requiredApiClientMethods) {
    ensureIncludes(apiClient, `${methodName}:`, "console-web/src/lib/api-client.ts");
}

const requiredUiSelectors = [
    "integrations-open-workspace-scope",
    "integrations-workspace-guidance",
    "workspace-next-step-ops",
    "workspace-empty-next-steps",
    "workspace-return-tenants",
    "workspace-return-integrations",
    "tenants-onboarding-loop-hint",
    "tenants-onboarding-open-ops",
    "ops-back-workspace",
    "ops-back-tenants",
];

for (const selector of requiredUiSelectors) {
    const selectorToken = `data-testid="${selector}"`;
    const selectorExistsInUi =
        integrationsPage.includes(selectorToken)
        || workspacePage.includes(selectorToken)
        || tenantsPage.includes(selectorToken)
        || opsPage.includes(selectorToken);
    if (!selectorExistsInUi) {
        fail(`required selector missing in UI sources: ${selector}`, [
            "Checked files: integrations/page.tsx, company-workspace/page.tsx, tenants-page-view.tsx, OpsPage.tsx",
        ]);
    }
    ensureIncludes(e2eSpec, selector, "console-web/e2e/platform-admin.spec.ts");
}

const requiredE2ESuites = [
    "Platform Admin Navigation",
    "Platform Admin Tenants",
    "Platform Admin Integrations",
];

for (const suiteName of requiredE2ESuites) {
    ensureIncludes(e2eSpec, suiteName, "console-web/e2e/platform-admin.spec.ts");
}

if (integrationsPage.includes("reconcileIntegrationBranch(")) {
    fail("Integrations page contains execute-level reconcile action call.", [
        "Integrations must stay fact-only and hand off execution to Company Workspace.",
    ]);
}

console.log("UVC anti-drift check passed");
