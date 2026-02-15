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

type ParsedErrorShape = {
    code?: string;
    message?: string;
    trace_id?: string;
} | undefined;

export function useInlineErrorSummary(limit = 8) {
    const { handleError } = useErrorHandler();
    const handleErrorRef = useRef(handleError);
    const [errors, setErrors] = useState<InlineErrorSummaryItem[]>([]);

    useEffect(() => {
        handleErrorRef.current = handleError;
    }, [handleError]);

    const reportError = useCallback((error: unknown): ParsedErrorShape => {
        const parsed = handleErrorRef.current(error) as ParsedErrorShape;
        const capturedAt = new Date().toISOString();
        const next: InlineErrorSummaryItem = {
            id: `${capturedAt}:${Math.random().toString(36).slice(2, 8)}`,
            code: parsed?.code ?? "UNKNOWN_ERROR",
            message: parsed?.message ?? "Unexpected error",
            traceId: parsed?.trace_id ?? "",
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
        return parsed;
    }, [limit]);

    const clearErrors = useCallback(() => {
        setErrors([]);
    }, []);

    return {
        errors,
        reportError,
        clearErrors,
    };
}
