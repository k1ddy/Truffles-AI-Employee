import type { ConsultantVerificationScenarioItem } from "@/lib/api-client";

import {
    getChallengeModeLabel,
    getScenarioCategoryLabel,
} from "../_lib/presentation";

type ScenarioLibraryProps = {
    scenarios: ConsultantVerificationScenarioItem[];
    isBusy: boolean;
    onFillPrompt: (prompt: string) => void;
    onRunScenario: (scenario: ConsultantVerificationScenarioItem) => void;
};

export default function ConsultantVerificationScenarioLibrary({
    scenarios,
    isBusy,
    onFillPrompt,
    onRunScenario,
}: ScenarioLibraryProps) {
    const scenarioItems = scenarios ?? [];

    return (
        <article
            className="rounded-xl border border-border/60 bg-card p-4"
            data-testid="consultant-verification-scenario-library"
        >
            <div className="flex items-center justify-between gap-2">
                <div>
                    <p className="text-sm font-semibold text-foreground">Сценарии для быстрой проверки</p>
                    <p className="mt-1 text-sm text-muted-foreground">
                        Готовые сложные вопросы строятся от домена, reference pack и capabilities текущего бизнеса.
                    </p>
                </div>
                <span className="text-xs text-muted-foreground">{scenarioItems.length}</span>
            </div>

            {scenarioItems.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">
                    Сценарии пока не собраны. Можно проверять вручную через обычный чат.
                </p>
            ) : null}

            <div className="mt-3 space-y-3">
                {scenarioItems.map((scenario) => (
                    <article
                        key={scenario.id}
                        className="rounded-xl border border-border/60 bg-muted/10 p-3"
                        data-testid={`consultant-verification-scenario-${scenario.id}`}
                    >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                                <p className="text-sm font-semibold text-foreground">{scenario.title}</p>
                                <p className="mt-1 text-xs text-muted-foreground">{scenario.description}</p>
                            </div>
                            <div className="flex flex-wrap gap-1 text-[11px] text-muted-foreground">
                                <span className="rounded-full border border-border px-2 py-0.5">
                                    {getScenarioCategoryLabel(scenario.category)}
                                </span>
                                <span className="rounded-full border border-border px-2 py-0.5">
                                    {getChallengeModeLabel(scenario.recommended_challenge_mode)}
                                </span>
                            </div>
                        </div>

                        <p className="mt-3 rounded-lg border border-border/60 bg-background/80 px-3 py-2 text-sm text-foreground">
                            {scenario.prompt}
                        </p>

                        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                            <p className="text-xs text-muted-foreground">
                                Источник: {scenario.source_label}
                            </p>
                            <div className="flex flex-wrap gap-2">
                                <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={() => {
                                        onFillPrompt(scenario.prompt);
                                    }}
                                    disabled={isBusy}
                                    data-testid={`consultant-verification-scenario-fill-${scenario.id}`}
                                >
                                    Вставить в поле
                                </button>
                                <button
                                    type="button"
                                    className="btn-ghost"
                                    onClick={() => {
                                        onRunScenario(scenario);
                                    }}
                                    disabled={isBusy}
                                    data-testid={`consultant-verification-scenario-launch-${scenario.id}`}
                                >
                                    Запустить отдельно
                                </button>
                            </div>
                        </div>
                    </article>
                ))}
            </div>
        </article>
    );
}
