"use client";

import type { components } from "@/types/api.generated";
import { formatMissingRequirement } from "@/components/provisioning-wizard-domain";
import type { OnboardingTimelineItem } from "@/components/provisioning-wizard-derived";
import {
    onboardingStepStatusClass,
    onboardingStepStatusLabel,
} from "@/components/provisioning-wizard-utils";

type OnboardingScorecardCheck = components["schemas"]["ConsoleOnboardingScorecardCheck"];
type OnboardingDocumentIngestion = components["schemas"]["ConsoleOnboardingDocumentIngestion"];

type ProvisioningWizardReadinessPanelProps = {
    onboardingUpdatedAt?: string | null;
    onboardingTimeline: OnboardingTimelineItem[];
    scorecardFailed: boolean;
    scorecardStatus?: string | null;
    scorecardGeneratedAt?: string | null;
    scorecardMissing: string[];
    scorecardFailedChecks: OnboardingScorecardCheck[];
    documentIngestionGate?: OnboardingDocumentIngestion | null;
    documentIngestionMissing: string[];
    documentIngestionCriticalMissing: string[];
};

export function ProvisioningWizardReadinessPanel({
    onboardingUpdatedAt,
    onboardingTimeline,
    scorecardFailed,
    scorecardStatus,
    scorecardGeneratedAt,
    scorecardMissing,
    scorecardFailedChecks,
    documentIngestionGate,
    documentIngestionMissing,
    documentIngestionCriticalMissing,
}: ProvisioningWizardReadinessPanelProps) {
    return (
        <>
            <div className="rounded-lg border border-border/60 bg-background p-3 space-y-2" data-testid="onboarding-readiness-timeline">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                        Readiness Timeline
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                        updated_at: {onboardingUpdatedAt ? new Date(onboardingUpdatedAt).toLocaleString("ru-RU") : "—"}
                    </div>
                </div>
                <div className="space-y-2">
                    {onboardingTimeline.map((item) => (
                        <div
                            key={item.id}
                            className={`rounded-lg border px-3 py-2 text-xs ${onboardingStepStatusClass(item.status)}`}
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="font-medium">
                                    {item.index}. {item.label}
                                </div>
                                <div>{onboardingStepStatusLabel(item.status)}</div>
                            </div>
                            <div className="mt-1 text-[11px]">
                                hint: {item.hint} · required: {item.required ? "yes" : "no"}
                            </div>
                            {item.missing.length > 0 ? (
                                <div className="mt-1 text-[11px]">
                                    missing: {item.missing.map((code) => formatMissingRequirement(code)).join(", ")}
                                </div>
                            ) : null}
                        </div>
                    ))}
                </div>
            </div>
            <div
                className={`rounded-lg border px-3 py-3 text-xs ${
                    scorecardFailed
                        ? "border-destructive/30 bg-destructive/10 text-destructive"
                        : "border-green-200 bg-green-50 text-green-800"
                }`}
                data-testid="onboarding-scorecard"
            >
                <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold">Server Scorecard</span>
                    <span className="font-mono">{scorecardStatus ?? "—"}</span>
                </div>
                <div className="mt-1">
                    generated_at: {scorecardGeneratedAt ? new Date(scorecardGeneratedAt).toLocaleString("ru-RU") : "—"}
                </div>
                {scorecardMissing.length > 0 && (
                    <div className="mt-2">
                        missing: {scorecardMissing.map((item) => formatMissingRequirement(item)).join(", ")}
                    </div>
                )}
                {scorecardFailedChecks.length > 0 && (
                    <div className="mt-2">
                        failed checks: {scorecardFailedChecks.map((item) => item.id).join(", ")}
                    </div>
                )}
                {documentIngestionGate && (
                    <div
                        className={`mt-2 rounded-md border px-2 py-2 ${
                            documentIngestionGate.status === "pass"
                                ? "border-green-200 bg-green-50 text-green-800"
                                : documentIngestionGate.status === "fail"
                                    ? "border-destructive/30 bg-destructive/10 text-destructive"
                                    : "border-border/60 bg-muted/40 text-muted-foreground"
                        }`}
                        data-testid="onboarding-document-ingestion"
                    >
                        <div className="font-semibold">
                            Document ingestion: {documentIngestionGate.status}
                        </div>
                        <div className="mt-1 text-[11px]">
                            source: <span className="font-mono">{documentIngestionGate.source}</span> · valid:{" "}
                            <span className="font-mono">{documentIngestionGate.valid ? "true" : "false"}</span>
                        </div>
                        {documentIngestionMissing.length > 0 && (
                            <div className="mt-1 text-[11px]">
                                missing_fields: {documentIngestionMissing.map((item) => formatMissingRequirement(item)).join(", ")}
                            </div>
                        )}
                        {documentIngestionCriticalMissing.length > 0 && (
                            <div className="mt-1 text-[11px] font-semibold">
                                critical_missing: {documentIngestionCriticalMissing.map((item) => formatMissingRequirement(item)).join(", ")}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </>
    );
}
