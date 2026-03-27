"use client";

import type {
    ConsultantVerificationChallengeMode,
    ConsultantVerificationScenarioItem,
    ConsultantVerificationSessionResponse,
    ConsultantVerificationSourceMode,
} from "@/lib/api-client";

import ConsultantVerificationScenarioLibrary from "./ConsultantVerificationScenarioLibrary";
import { formatTimestamp, getChallengeModeLabel, getSourceModeLabel } from "../_lib/presentation";

function sourceModeButtonClass(active: boolean): string {
    return active
        ? "border-foreground bg-foreground text-background"
        : "border-border bg-background text-foreground hover:bg-muted/40";
}

function challengeModeButtonClass(active: boolean): string {
    return active
        ? "border-foreground bg-foreground text-background"
        : "border-border bg-background text-foreground hover:bg-muted/40";
}

type ConsultantVerificationOwnerSetupLaneProps = {
    selectedSourceMode: ConsultantVerificationSourceMode;
    availableSourceModes: ConsultantVerificationSourceMode[];
    selectedChallengeMode: ConsultantVerificationChallengeMode;
    selectedSessionSummary: ConsultantVerificationSessionResponse["session"] | null;
    isBusy: boolean;
    createSessionPending: boolean;
    onResetSelection: () => void;
    onSelectSourceMode: (mode: ConsultantVerificationSourceMode) => void;
    onSelectChallengeMode: (mode: ConsultantVerificationChallengeMode) => void;
    onStartSession: () => void;
    scenarios: ConsultantVerificationScenarioItem[];
    onFillPrompt: (prompt: string) => void;
    onRunScenario: (scenario: ConsultantVerificationScenarioItem) => void;
};

export default function ConsultantVerificationOwnerSetupLane({
    selectedSourceMode,
    availableSourceModes,
    selectedChallengeMode,
    selectedSessionSummary,
    isBusy,
    createSessionPending,
    onResetSelection,
    onSelectSourceMode,
    onSelectChallengeMode,
    onStartSession,
    scenarios,
    onFillPrompt,
    onRunScenario,
}: ConsultantVerificationOwnerSetupLaneProps) {
    return (
        <aside className="space-y-4">
            <article className="rounded-xl border border-border/60 bg-card p-4">
                <div className="flex items-start justify-between gap-3">
                    <div>
                        <p className="text-sm font-semibold text-foreground">Новая проверка</p>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Выберите, как именно хотите атаковать систему, и начните отдельную сессию.
                        </p>
                    </div>
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={onResetSelection}
                        data-testid="consultant-verification-reset-session"
                    >
                        Сбросить выбор
                    </button>
                </div>

                <div className="mt-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Версия данных</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                        {(["live", "published", "draft"] as const).map((mode) => {
                            const disabled = !availableSourceModes.includes(mode);
                            return (
                                <button
                                    key={mode}
                                    type="button"
                                    onClick={() => onSelectSourceMode(mode)}
                                    className={`rounded-full border px-3 py-1.5 text-sm font-medium ${sourceModeButtonClass(selectedSourceMode === mode)} ${disabled ? "cursor-not-allowed opacity-50" : ""}`}
                                    data-testid={`consultant-verification-source-${mode}`}
                                    disabled={disabled}
                                >
                                    {getSourceModeLabel(mode)}
                                </button>
                            );
                        })}
                    </div>
                    {availableSourceModes.length === 0 ? (
                        <p className="mt-2 text-xs text-muted-foreground">
                            Сначала сохраните draft, либо дождитесь live версии или published candidate для preview.
                        </p>
                    ) : null}
                </div>

                <div className="mt-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Способ проверки</p>
                    <div className="mt-2 space-y-2">
                        {(["as_client", "stress"] as const).map((mode) => (
                            <button
                                key={mode}
                                type="button"
                                onClick={() => onSelectChallengeMode(mode)}
                                className={`w-full rounded-xl border p-3 text-left ${challengeModeButtonClass(selectedChallengeMode === mode)}`}
                                data-testid={`consultant-verification-mode-${mode}`}
                            >
                                <p className="text-sm font-semibold">{getChallengeModeLabel(mode)}</p>
                                <p className="mt-1 text-xs opacity-80">
                                    {mode === "stress"
                                        ? "Провоцируйте сложные, смешанные и неудобные сценарии."
                                        : "Пишите так, как будто вы обычный клиент бизнеса."}
                                </p>
                            </button>
                        ))}
                    </div>
                </div>

                <button
                    type="button"
                    className="btn-ghost mt-4 w-full"
                    onClick={onStartSession}
                    disabled={isBusy}
                    data-testid="consultant-verification-start-session"
                >
                    {createSessionPending ? "Создаю сессию..." : "Начать новую проверку"}
                </button>

                {selectedSessionSummary ? (
                    <p className="mt-3 text-xs text-muted-foreground">
                        Последний ответ: {formatTimestamp(selectedSessionSummary.last_message_at)}
                    </p>
                ) : null}
            </article>

            <ConsultantVerificationScenarioLibrary
                scenarios={scenarios}
                isBusy={isBusy}
                onFillPrompt={onFillPrompt}
                onRunScenario={onRunScenario}
            />
        </aside>
    );
}
