import type {
    ConsultantVerificationCompareCaseRecord,
    ConsultantVerificationCompareReadiness,
    ConsultantVerificationFindingRecord,
    ConsultantVerificationBusinessVerdict,
    ConsultantVerificationChallengeMode,
    ConsultantVerificationOutcome,
    ConsultantVerificationScenarioItem,
    ConsultantVerificationSessionRecord,
    ConsultantVerificationSourceMode,
    ConsultantVerificationTurnRecord,
} from "@/lib/api-client";

type VerdictPresentation = {
    label: string;
    summary: string;
    chipClass: string;
    panelClass: string;
};

type FindingStatusPresentation = {
    label: string;
    chipClass: string;
};

type CompareDeltaPresentation = {
    label: string;
    chipClass: string;
};

type CompareReadinessPresentation = {
    label: string;
    chipClass: string;
    panelClass: string;
};

const VERDICT_PRESENTATION: Record<ConsultantVerificationBusinessVerdict, VerdictPresentation> = {
    answered: {
        label: "Ответил по данным",
        summary: "Консультант дал прямой ответ на основе доступных данных бизнеса.",
        chipClass: "bg-emerald-100 text-emerald-800",
        panelClass: "border-emerald-200 bg-emerald-50/80",
    },
    needs_clarification: {
        label: "Уточняет детали",
        summary: "Консультант собирает недостающие детали, чтобы не ошибиться со следующим шагом.",
        chipClass: "bg-sky-100 text-sky-800",
        panelClass: "border-sky-200 bg-sky-50/80",
    },
    handoff: {
        label: "Передаст человеку",
        summary: "Сценарий корректно уходит человеку: здесь нужен менеджер или дополнительная проверка.",
        chipClass: "bg-amber-100 text-amber-800",
        panelClass: "border-amber-200 bg-amber-50/80",
    },
    gap_detected: {
        label: "Найден пробел",
        summary: "Проверка показала, что системе не хватает данных или правила ответа сейчас слишком слабы.",
        chipClass: "bg-rose-100 text-rose-800",
        panelClass: "border-rose-200 bg-rose-50/80",
    },
};

const OUTCOME_LABELS: Record<ConsultantVerificationOutcome, string> = {
    fact: "FACT",
    collect: "COLLECT",
    handoff: "HANDOFF",
};

const SOURCE_MODE_LABELS: Record<ConsultantVerificationSourceMode, string> = {
    live: "Текущая версия",
    draft: "Черновик",
};

const CHALLENGE_MODE_LABELS: Record<ConsultantVerificationChallengeMode, string> = {
    as_client: "Проверить как клиент",
    stress: "Найти слабые места",
};
const SCENARIO_CATEGORY_LABELS: Record<ConsultantVerificationScenarioItem["category"], string> = {
    core_info: "База",
    pricing: "Цена",
    booking: "Запись",
    policy: "Правила",
    handoff: "Человек",
    stress: "Стресс",
};
const FINDING_STATUS_PRESENTATION: Record<
    ConsultantVerificationFindingRecord["status"],
    FindingStatusPresentation
> = {
    new: {
        label: "Новый",
        chipClass: "bg-rose-100 text-rose-800",
    },
    in_review: {
        label: "На разборе",
        chipClass: "bg-amber-100 text-amber-800",
    },
    needs_data: {
        label: "Нужны данные",
        chipClass: "bg-sky-100 text-sky-800",
    },
    fixed: {
        label: "Исправлено",
        chipClass: "bg-emerald-100 text-emerald-800",
    },
    retested: {
        label: "Перепроверено",
        chipClass: "bg-slate-100 text-slate-700",
    },
};
const COMPARE_DELTA_PRESENTATION: Record<
    ConsultantVerificationCompareCaseRecord["delta"],
    CompareDeltaPresentation
> = {
    improved: {
        label: "Стало лучше",
        chipClass: "bg-emerald-100 text-emerald-800",
    },
    unchanged: {
        label: "Без заметных изменений",
        chipClass: "bg-slate-100 text-slate-700",
    },
    regressed: {
        label: "Стало хуже",
        chipClass: "bg-rose-100 text-rose-800",
    },
    needs_review: {
        label: "Нужно проверить руками",
        chipClass: "bg-amber-100 text-amber-800",
    },
};
const COMPARE_READINESS_PRESENTATION: Record<
    ConsultantVerificationCompareReadiness["status"],
    CompareReadinessPresentation
> = {
    ready: {
        label: "Готово к публикации",
        chipClass: "bg-emerald-100 text-emerald-800",
        panelClass: "border-emerald-200 bg-emerald-50/80",
    },
    needs_attention: {
        label: "Нужно внимание",
        chipClass: "bg-amber-100 text-amber-800",
        panelClass: "border-amber-200 bg-amber-50/80",
    },
    blocked: {
        label: "Сравнение не готово",
        chipClass: "bg-slate-100 text-slate-700",
        panelClass: "border-slate-200 bg-slate-50/80",
    },
};

export type ExplanationBlock = {
    id: string;
    title: string;
    body: string;
};

export function getVerdictPresentation(
    verdict?: ConsultantVerificationBusinessVerdict | null,
): VerdictPresentation {
    if (!verdict) {
        return {
            label: "Ожидает ответ",
            summary: "Сначала отправьте сообщение, чтобы увидеть результат проверки.",
            chipClass: "bg-slate-100 text-slate-700",
            panelClass: "border-slate-200 bg-slate-50/80",
        };
    }
    return VERDICT_PRESENTATION[verdict];
}

export function getOutcomeLabel(outcome?: ConsultantVerificationOutcome | null): string {
    if (!outcome) {
        return "—";
    }
    return OUTCOME_LABELS[outcome];
}

export function getSourceModeLabel(mode: ConsultantVerificationSourceMode): string {
    return SOURCE_MODE_LABELS[mode];
}

export function getChallengeModeLabel(mode: ConsultantVerificationChallengeMode): string {
    return CHALLENGE_MODE_LABELS[mode];
}

export function getScenarioCategoryLabel(category: ConsultantVerificationScenarioItem["category"]): string {
    return SCENARIO_CATEGORY_LABELS[category];
}

export function getFindingStatusPresentation(
    status: ConsultantVerificationFindingRecord["status"],
): FindingStatusPresentation {
    return FINDING_STATUS_PRESENTATION[status];
}

export function getCompareDeltaPresentation(
    delta: ConsultantVerificationCompareCaseRecord["delta"],
): CompareDeltaPresentation {
    return COMPARE_DELTA_PRESENTATION[delta];
}

export function getCompareReadinessPresentation(
    status?: ConsultantVerificationCompareReadiness["status"] | null,
): CompareReadinessPresentation {
    if (!status) {
        return COMPARE_READINESS_PRESENTATION.blocked;
    }
    return COMPARE_READINESS_PRESENTATION[status];
}

export function buildSessionTitle(
    mode: ConsultantVerificationChallengeMode,
    sourceMode: ConsultantVerificationSourceMode,
): string {
    const modeLabel = mode === "stress" ? "Стресс-проверка" : "Проверка как клиент";
    const sourceLabel = sourceMode === "draft" ? "черновик" : "текущая версия";
    return `${modeLabel} • ${sourceLabel}`;
}

export function buildReplayTitle(
    label: string,
    sourceMode: ConsultantVerificationSourceMode,
    challengeMode: ConsultantVerificationChallengeMode,
): string {
    return `${label} • ${getChallengeModeLabel(challengeMode)} • ${getSourceModeLabel(sourceMode)}`;
}

export function formatSessionTitle(session: ConsultantVerificationSessionRecord, index: number): string {
    const title = session.title?.trim();
    if (title) {
        return title;
    }
    return `${getChallengeModeLabel(session.challenge_mode)} #${index + 1}`;
}

export function formatTimestamp(value?: string | null): string {
    if (!value) {
        return "—";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return "—";
    }
    return date.toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

export function describeSessionLatest(session: ConsultantVerificationSessionRecord): string {
    const verdict = getVerdictPresentation(session.latest_business_verdict);
    const turnCount = session.turns_total || 0;
    if (!turnCount) {
        return "Без сообщений";
    }
    return `${verdict.label} • ${turnCount} сообщений`;
}

export function buildExplanationBlocks(turn?: ConsultantVerificationTurnRecord | null): ExplanationBlock[] {
    if (!turn) {
        return [
            {
                id: "waiting",
                title: "Как читать результат",
                body: "После ответа консультанта здесь появится простое объяснение: ответил ли он по данным, уточняет ли детали, корректно ли передает человеку, или найден реальный пробел.",
            },
        ];
    }

    const blocks: ExplanationBlock[] = [];

    if (turn.business_verdict === "gap_detected") {
        blocks.push({
            id: "gap",
            title: "Что это значит",
            body: "Проверка обнаружила слабое место: в данных бизнеса не хватает фактов или текущие правила ответа не закрывают этот сценарий надежно.",
        });
    } else if (turn.business_verdict === "handoff") {
        blocks.push({
            id: "handoff",
            title: "Почему передаем человеку",
            body: "Для такого сценария безопаснее и честнее подключить менеджера. Это корректный исход продукта, а не ошибка консультанта.",
        });
    } else if (turn.business_verdict === "needs_clarification" || turn.outcome === "collect") {
        blocks.push({
            id: "collect",
            title: "Почему идет уточнение",
            body: "Консультант собирает детали, без которых нельзя корректно продолжить запись или дать точный ответ.",
        });
    } else {
        blocks.push({
            id: "fact",
            title: "Почему ответ считается нормальным",
            body: "Консультант дал прямой ответ на основе данных бизнеса и не ушел в домыслы или неподтвержденные обещания.",
        });
    }

    if (turn.source_refs.length > 0) {
        blocks.push({
            id: "sources",
            title: "На что опирался ответ",
            body: "Ответ опирается на опубликованные данные бизнеса. Ниже показаны источники, которые попали в этот turn.",
        });
    } else if (turn.business_verdict === "answered") {
        blocks.push({
            id: "sources-empty",
            title: "Что стоит проверить",
            body: "Ответ получился без явных source refs. Для важного коммерческого сценария это повод дополнительно перепроверить knowledge и упаковку фактов.",
        });
    }

    if (turn.would_book) {
        blocks.push({
            id: "booking-preview",
            title: "Что было бы в живом диалоге",
            body: "Если бы это был реальный клиентский чат, система дошла бы до подготовки записи. В этой проверке запись не создается по design.",
        });
    } else if (turn.would_handoff) {
        blocks.push({
            id: "handoff-preview",
            title: "Что было бы в живом диалоге",
            body: "Если бы это был реальный клиентский чат, система создала бы handoff менеджеру. В этом режиме мы показываем только preview без side effects.",
        });
    }

    return blocks;
}

export function buildTurnSignals(turn?: ConsultantVerificationTurnRecord | null): string[] {
    if (!turn) {
        return [];
    }
    const signals: string[] = [];
    if (turn.source_refs.length > 0) {
        signals.push(`Источники: ${turn.source_refs.length}`);
    }
    if (turn.would_book) {
        signals.push("Подготовил бы запись");
    }
    if (turn.would_handoff) {
        signals.push("Создал бы handoff");
    }
    if (turn.gap_detected) {
        signals.push("Пробел зафиксирован");
    }
    if (turn.decision_trace.length > 0) {
        signals.push(`Trace: ${turn.decision_trace.length}`);
    }
    return signals;
}

export function roleLabel(role: ConsultantVerificationTurnRecord["role"]): string {
    if (role === "owner") {
        return "Вы как клиент";
    }
    if (role === "system") {
        return "Система";
    }
    return "Консультант";
}
