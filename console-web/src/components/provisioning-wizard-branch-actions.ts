import type { components } from "@/types/api.generated";
import {
    buildBookingSettingsJsonFromFields,
    buildWorkingHoursJsonFromFields,
    type ProvisioningBranchBootstrapState,
} from "@/components/provisioning-wizard-state";
import { parseOptionalJson } from "@/components/provisioning-wizard-utils";

type BranchBootstrapAccount = components["schemas"]["ConsoleBranchBootstrapAccountTemplate"];
type BranchCreateRequest = components["schemas"]["ConsoleBranchCreateRequest"];
type BranchGoLiveDecisionRequest = components["schemas"]["ConsoleBranchGoLiveDecisionRequest"];
type BranchGoLiveWaiverRequest = components["schemas"]["ConsoleBranchGoLiveWaiverRequest"];
type BranchUpdateRequest = components["schemas"]["ConsoleBranchUpdateRequest"];

type ActionResult<T> = {
    error?: string;
    payload?: T;
};

type GoLiveMutationInput<TPayload> = {
    result: ActionResult<TPayload>;
    fallbackError: string;
    reportValidationError: (message: string) => void;
    mutate: (payload: TPayload, options: { onSuccess: () => void }) => void;
    clearReason: () => void;
};

type BranchMutationInput<TPayload> = {
    result: ActionResult<TPayload>;
    fallbackError: string;
    reportValidationError: (message: string) => void;
    mutate: (payload: TPayload, options?: { onSuccess: (data: unknown) => void }) => void;
    onSuccess?: (data: unknown) => void;
};

type GoLiveDecisionMutationInput = {
    branchId: string | null | undefined;
    reason: string;
    decisionLabel: "approve" | "reject";
    enforceScorecard: boolean;
    scorecardMissingLabels: string[];
    reportValidationError: (message: string) => void;
    mutate: (payload: BranchGoLiveDecisionRequest, options: { onSuccess: () => void }) => void;
    clearReason: () => void;
};

type GoLiveWaiverMutationInput = {
    branchId: string | null | undefined;
    reason: string;
    ttlHoursInput: string;
    enforceScorecard: boolean;
    scorecardMissingLabels: string[];
    reportValidationError: (message: string) => void;
    mutate: (payload: BranchGoLiveWaiverRequest, options: { onSuccess: () => void }) => void;
    clearReason: () => void;
};

type SaveBookingResult = ActionResult<BranchUpdateRequest> & {
    nextWorkingHoursJson?: string;
    nextBookingSettingsJson?: string;
};

type BranchMutationSuccessInput<TBranch> = {
    data: TBranch;
    toastMessage: string;
    setBranchData: (value: TBranch) => void;
    refetchOnboarding: () => void;
    refetchOnboardingScorecard: () => void;
    notifySuccess: (message: string) => void;
};

type BranchMutationErrorInput = {
    error: unknown;
    action: string;
    endpoint: string;
    reportValidationError: (message: string) => void;
    reportProvisioningError: (error: unknown, action: string, endpoint: string) => void;
    branchRequiredMessage?: string;
};

export function syncBranchMutationSuccess<TBranch>(input: BranchMutationSuccessInput<TBranch>): void {
    input.setBranchData(input.data);
    input.refetchOnboarding();
    input.refetchOnboardingScorecard();
    input.notifySuccess(input.toastMessage);
}

export function handleBranchMutationError(input: BranchMutationErrorInput): void {
    const branchRequiredMessage = input.branchRequiredMessage ?? "Сначала создайте филиал";
    if (input.error instanceof Error && input.error.message === "BRANCH_REQUIRED") {
        input.reportValidationError(branchRequiredMessage);
        return;
    }
    input.reportProvisioningError(input.error, input.action, input.endpoint);
}

function buildGoLiveScorecardError(scorecardMissingLabels: string[]): string {
    return `Go-live заблокирован scorecard: ${scorecardMissingLabels.join(", ") || "есть незавершенные проверки"}`;
}

export function buildGoLiveDecisionPayload(input: {
    branchId: string | null | undefined;
    reason: string;
    decisionLabel: "approve" | "reject";
    enforceScorecard: boolean;
    scorecardMissingLabels: string[];
}): ActionResult<BranchGoLiveDecisionRequest> {
    if (!input.branchId) {
        return { error: "Сначала создайте филиал" };
    }
    if (input.enforceScorecard && input.scorecardMissingLabels.length > 0) {
        return { error: buildGoLiveScorecardError(input.scorecardMissingLabels) };
    }
    const reason = input.reason.trim();
    if (!reason) {
        return { error: `Укажите reason для ${input.decisionLabel}` };
    }
    return { payload: { reason } };
}

export function buildGoLiveWaiverPayload(input: {
    branchId: string | null | undefined;
    reason: string;
    ttlHoursInput: string;
    enforceScorecard: boolean;
    scorecardMissingLabels: string[];
}): ActionResult<BranchGoLiveWaiverRequest> {
    if (!input.branchId) {
        return { error: "Сначала создайте филиал" };
    }
    if (input.enforceScorecard && input.scorecardMissingLabels.length > 0) {
        return { error: buildGoLiveScorecardError(input.scorecardMissingLabels) };
    }
    const reason = input.reason.trim();
    if (!reason) {
        return { error: "Укажите reason для waiver" };
    }
    const ttlHours = Number.parseInt(input.ttlHoursInput, 10);
    if (!Number.isFinite(ttlHours) || ttlHours <= 0) {
        return { error: "ttl_hours должен быть положительным числом" };
    }
    return {
        payload: {
            reason,
            ttl_hours: ttlHours,
        },
    };
}

export function submitGoLiveMutation<TPayload>(input: GoLiveMutationInput<TPayload>): void {
    if (input.result.error || !input.result.payload) {
        input.reportValidationError(input.result.error ?? input.fallbackError);
        return;
    }
    input.mutate(input.result.payload, {
        onSuccess: () => {
            input.clearReason();
        },
    });
}

export function submitBranchMutation<TPayload>(input: BranchMutationInput<TPayload>): void {
    if (input.result.error || !input.result.payload) {
        input.reportValidationError(input.result.error ?? input.fallbackError);
        return;
    }
    const options = input.onSuccess ? { onSuccess: input.onSuccess } : undefined;
    input.mutate(input.result.payload, options);
}

export function submitGoLiveDecisionMutation(input: GoLiveDecisionMutationInput): void {
    submitGoLiveMutation({
        result: buildGoLiveDecisionPayload({
            branchId: input.branchId,
            reason: input.reason,
            decisionLabel: input.decisionLabel,
            enforceScorecard: input.enforceScorecard,
            scorecardMissingLabels: input.scorecardMissingLabels,
        }),
        fallbackError: `Ошибка валидации ${input.decisionLabel}`,
        reportValidationError: input.reportValidationError,
        mutate: input.mutate,
        clearReason: input.clearReason,
    });
}

export function submitGoLiveWaiverMutation(input: GoLiveWaiverMutationInput): void {
    submitGoLiveMutation({
        result: buildGoLiveWaiverPayload({
            branchId: input.branchId,
            reason: input.reason,
            ttlHoursInput: input.ttlHoursInput,
            enforceScorecard: input.enforceScorecard,
            scorecardMissingLabels: input.scorecardMissingLabels,
        }),
        fallbackError: "Ошибка валидации waiver",
        reportValidationError: input.reportValidationError,
        mutate: input.mutate,
        clearReason: input.clearReason,
    });
}

export function buildBranchBootstrapAccounts(input: {
    bootstrap: ProvisioningBranchBootstrapState;
    branchName: string;
}): BranchBootstrapAccount[] {
    if (!input.bootstrap.enabled) {
        return [];
    }
    const branchLabel = input.branchName.trim() || "Branch";
    const accounts: BranchBootstrapAccount[] = [];

    if (input.bootstrap.createOwner) {
        accounts.push({
            role: "owner",
            name: input.bootstrap.ownerName.trim() || `${branchLabel} Owner`,
            oidc_subject: input.bootstrap.ownerOidcSubject.trim() || undefined,
            is_active: true,
        });
    }
    if (input.bootstrap.createAdmin) {
        accounts.push({
            role: "admin",
            name: input.bootstrap.adminName.trim() || `${branchLabel} Admin`,
            oidc_subject: input.bootstrap.adminOidcSubject.trim() || undefined,
            is_active: true,
        });
    }
    if (input.bootstrap.createManager) {
        accounts.push({
            role: "manager",
            name: input.bootstrap.managerName.trim() || `${branchLabel} Manager`,
            oidc_subject: input.bootstrap.managerOidcSubject.trim() || undefined,
            is_active: true,
        });
    }
    return accounts;
}

export function buildCreateBranchPayload(input: {
    clientId: string;
    branchName: string;
    branchSlug: string;
    timezone: string;
    phone: string;
    bootstrap: ProvisioningBranchBootstrapState;
}): ActionResult<BranchCreateRequest> {
    if (!input.clientId) {
        return { error: "Укажите client_id" };
    }
    const name = input.branchName.trim();
    const slug = input.branchSlug.trim();
    if (!name || !slug) {
        return { error: "Заполните название и slug" };
    }
    return {
        payload: {
            client_id: input.clientId,
            name,
            slug,
            timezone: input.timezone.trim() || undefined,
            phone: input.phone.trim() || undefined,
            is_active: false,
            bootstrap_accounts: buildBranchBootstrapAccounts({
                bootstrap: input.bootstrap,
                branchName: name,
            }),
        },
    };
}

export function buildUpdateBranchDraftPayload(input: {
    branchId: string | null | undefined;
    branchName: string;
    branchSlug: string;
    timezone: string;
    phone: string;
}): ActionResult<BranchUpdateRequest> {
    if (!input.branchId) {
        return { error: "Сначала создайте филиал" };
    }
    const name = input.branchName.trim();
    const slug = input.branchSlug.trim();
    if (!name || !slug) {
        return { error: "Заполните название и slug" };
    }
    return {
        payload: {
            name,
            slug,
            timezone: input.timezone.trim() || undefined,
            phone: input.phone.trim() || undefined,
        },
    };
}

export function buildSaveInstancePayload(input: {
    branchId: string | null | undefined;
    instanceId: string;
    phone: string;
    activateOnSave: boolean;
}): ActionResult<BranchUpdateRequest> {
    if (!input.branchId) {
        return { error: "Сначала создайте филиал" };
    }
    const instanceId = input.instanceId.trim();
    if (!instanceId) {
        return { error: "Укажите instance_id" };
    }
    const phone = input.phone.trim();
    if (!phone) {
        return { error: "Укажите phone филиала" };
    }
    return {
        payload: {
            phone,
            instance_id: instanceId,
            is_active: input.activateOnSave,
        },
    };
}

export function buildSaveTelegramPayload(input: {
    branchId: string | null | undefined;
    chatId: string;
}): ActionResult<BranchUpdateRequest> {
    if (!input.branchId) {
        return { error: "Сначала создайте филиал" };
    }
    const chatId = input.chatId.trim();
    if (!chatId) {
        return { error: "Укажите telegram_chat_id" };
    }
    return {
        payload: {
            telegram_chat_id: chatId,
        },
    };
}

export function buildSaveKnowledgePayload(input: {
    branchId: string | null | undefined;
    knowledgeTag: string;
}): ActionResult<BranchUpdateRequest> {
    if (!input.branchId) {
        return { error: "Сначала создайте филиал" };
    }
    const knowledgeTag = input.knowledgeTag.trim();
    if (!knowledgeTag) {
        return { error: "Укажите knowledge_tag" };
    }
    return {
        payload: {
            knowledge_tag: knowledgeTag,
        },
    };
}

export function buildSaveBookingPayload(input: {
    branchId: string | null | undefined;
    workingHoursJson: string;
    bookingSettingsJson: string;
    workingHoursDays: string[];
    workingHoursStart: string;
    workingHoursEnd: string;
    bookingDefaultDuration: string;
    bookingBufferMin: string;
}): SaveBookingResult {
    if (!input.branchId) {
        return { error: "Сначала создайте филиал" };
    }
    const workingHours = parseOptionalJson(input.workingHoursJson, "working_hours");
    if (workingHours.error) {
        return { error: workingHours.error };
    }
    const bookingSettings = parseOptionalJson(input.bookingSettingsJson, "booking_settings");
    if (bookingSettings.error) {
        return { error: bookingSettings.error };
    }

    let workingPayload = workingHours.value;
    let bookingPayload = bookingSettings.value;
    let nextWorkingHoursJson: string | undefined;
    let nextBookingSettingsJson: string | undefined;

    if (!workingPayload) {
        const built = buildWorkingHoursJsonFromFields({
            selectedDays: input.workingHoursDays,
            start: input.workingHoursStart,
            end: input.workingHoursEnd,
        });
        if (built.error) {
            return { error: built.error };
        }
        if (built.json) {
            const parsed = parseOptionalJson(built.json, "working_hours");
            if (parsed.error) {
                return { error: parsed.error };
            }
            workingPayload = parsed.value;
            nextWorkingHoursJson = built.json;
        }
    }

    if (!bookingPayload) {
        const built = buildBookingSettingsJsonFromFields({
            defaultDuration: input.bookingDefaultDuration,
            bufferMin: input.bookingBufferMin,
        });
        if (built.error) {
            return { error: built.error };
        }
        if (built.json) {
            const parsed = parseOptionalJson(built.json, "booking_settings");
            if (parsed.error) {
                return { error: parsed.error };
            }
            bookingPayload = parsed.value;
            nextBookingSettingsJson = built.json;
        }
    }

    if (!workingPayload && !bookingPayload) {
        return { error: "Заполните working_hours или booking_settings" };
    }

    const payload: BranchUpdateRequest = {
        working_hours: (workingPayload as Record<string, never> | undefined) ?? undefined,
        booking_settings: (bookingPayload as Record<string, never> | undefined) ?? undefined,
    };
    return { payload, nextWorkingHoursJson, nextBookingSettingsJson };
}
