"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useErrorHandler } from "@/lib/api-hooks";

export type InlineErrorSummaryItem = {
    id: string;
    code: string;
    message: string;
    traceId: string;
    capturedAt: string;
};

export type InlineErrorInput = {
    code?: string;
    message: string;
    traceId?: string;
};

type ParsedErrorShape = {
    code?: string;
    message?: string;
    trace_id?: string;
} | undefined;

type InlineErrorReportOptions = {
    includeProvisioningGuidance?: boolean;
    operation?: string;
    endpoint?: string;
};

const PROVISIONING_SERVER_ERROR_CODES = new Set([
    "SERVER_ERROR",
    "DATABASE_ERROR",
    "UPSTREAM_ERROR",
    "UPSTREAM_INVALID_RESPONSE",
    "PROXY_ERROR",
    "UNKNOWN_ERROR",
]);

function buildProvisioningGuidanceMessage(
    parsed: ParsedErrorShape,
    options?: InlineErrorReportOptions,
): string {
    const operation = options?.operation?.trim() || "операция provisioning";
    const endpoint = options?.endpoint?.trim() ? ` (${options.endpoint?.trim()})` : "";
    const traceValue = parsed?.trace_id?.trim() || "n/a";
    return [
        `Что делать сейчас для «${operation}»${endpoint}:`,
        "1) Проверьте контекст компании/клиента/филиала и обязательные поля.",
        "2) Повторите действие один раз после обновления страницы.",
        `3) Если ошибка повторяется: передайте в OPS trace=${traceValue} и время ошибки.`,
    ].join(" ");
}

export function useInlineErrorSummary(limit = 8) {
    const { handleError } = useErrorHandler();
    const handleErrorRef = useRef(handleError);
    const [errors, setErrors] = useState<InlineErrorSummaryItem[]>([]);

    useEffect(() => {
        handleErrorRef.current = handleError;
    }, [handleError]);

    const appendError = useCallback((input: InlineErrorInput): InlineErrorSummaryItem => {
        const capturedAt = new Date().toISOString();
        const next: InlineErrorSummaryItem = {
            id: `${capturedAt}:${Math.random().toString(36).slice(2, 8)}`,
            code: input.code ?? "UNKNOWN_ERROR",
            message: input.message,
            traceId: input.traceId ?? "",
            capturedAt,
        };
        setErrors((previous) => {
            const deduped = previous.filter(
                (item) =>
                    item.code !== next.code
                    || item.message !== next.message
                    || item.traceId !== next.traceId,
            );
            return [next, ...deduped].slice(0, limit);
        });
        return next;
    }, [limit]);

    const reportError = useCallback((error: unknown, options?: InlineErrorReportOptions): ParsedErrorShape => {
        const parsed = handleErrorRef.current(error) as ParsedErrorShape;
        appendError({
            code: parsed?.code ?? "UNKNOWN_ERROR",
            message: parsed?.message ?? "Unexpected error",
            traceId: parsed?.trace_id ?? "",
        });
        if (
            options?.includeProvisioningGuidance
            && parsed?.code
            && PROVISIONING_SERVER_ERROR_CODES.has(parsed.code)
        ) {
            appendError({
                code: "PROVISIONING_NEXT_STEP",
                message: buildProvisioningGuidanceMessage(parsed, options),
                traceId: parsed?.trace_id ?? "",
            });
        }
        return parsed;
    }, [appendError]);

    const reportInlineError = useCallback((input: InlineErrorInput) => {
        appendError({
            code: input.code ?? "VALIDATION_ERROR",
            message: input.message,
            traceId: input.traceId ?? "",
        });
    }, [appendError]);

    const clearErrors = useCallback(() => {
        setErrors([]);
    }, []);

    return {
        errors,
        reportError,
        reportInlineError,
        clearErrors,
    };
}
