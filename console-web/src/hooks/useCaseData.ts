"use client";

import { useEffect, useState } from "react";
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Case, Message } from "@/types";
import { readConsoleContextScopeFromStorage } from "@/lib/console-context-storage";

async function fetchCase(caseId: string): Promise<Case> {
    const response = await api.get(`/cases/${caseId}`);
    return response.data;
}

async function fetchMessagesPage(
    caseId: string,
    cursor?: string,
): Promise<{ items: Message[]; cursor?: string | null; has_more?: boolean }> {
    const response = await api.get(`/cases/${caseId}/messages`, {
        params: {
            cursor,
            limit: 50,
        },
    });
    return response.data;
}

function useDocumentVisible(): boolean {
    const [visible, setVisible] = useState(true);

    useEffect(() => {
        if (typeof document === "undefined") {
            return;
        }
        const update = () => {
            setVisible(!document.hidden);
        };
        update();
        document.addEventListener("visibilitychange", update);
        return () => {
            document.removeEventListener("visibilitychange", update);
        };
    }, []);

    return visible;
}

export function useCaseData(caseId?: string | null) {
    const enabled = Boolean(caseId);
    const documentVisible = useDocumentVisible();
    const queryClient = useQueryClient();
    const sseEnabled = process.env.NEXT_PUBLIC_CASE_SSE_ENABLED !== "0";
    const [syncMode, setSyncMode] = useState<"sse" | "polling">("polling");
    const [syncReasonCode, setSyncReasonCode] = useState<string | null>("stream_not_initialized");
    const casePollMs = syncMode === "sse" ? 120000 : 30000;

    useEffect(() => {
        if (!enabled || !documentVisible || !caseId) {
            setSyncMode("polling");
            setSyncReasonCode("stream_inactive");
            return;
        }

        if (typeof window === "undefined" || typeof EventSource === "undefined") {
            setSyncMode("polling");
            setSyncReasonCode("event_source_unsupported");
            return;
        }
        if (!sseEnabled) {
            setSyncMode("polling");
            setSyncReasonCode("sse_disabled_by_flag");
            return;
        }

        const scope = readConsoleContextScopeFromStorage();
        const params = new URLSearchParams();
        if (scope.companyId) {
            params.set("company_id", scope.companyId);
        }
        if (scope.clientId) {
            params.set("client_id", scope.clientId);
        }
        if (scope.branchId) {
            params.set("branch_id", scope.branchId);
        }

        const streamPath = `/api/proxy/cases/${encodeURIComponent(caseId)}/stream`;
        const streamUrl = params.toString() ? `${streamPath}?${params.toString()}` : streamPath;
        const stream = new EventSource(streamUrl);
        let stopped = false;

        const switchToPolling = (reasonCode: string) => {
            if (stopped) {
                return;
            }
            setSyncMode("polling");
            setSyncReasonCode(reasonCode);
        };

        stream.addEventListener("open", () => {
            setSyncMode("sse");
            setSyncReasonCode(null);
        });

        stream.addEventListener("case.refresh", () => {
            queryClient.invalidateQueries({ queryKey: ["case", caseId] });
            queryClient.invalidateQueries({ queryKey: ["messages", caseId] });
        });

        stream.addEventListener("closed", (event: MessageEvent<string>) => {
            let reasonCode = "stream_closed";
            try {
                const payload = JSON.parse(event.data || "{}");
                if (typeof payload.reason_code === "string" && payload.reason_code.trim()) {
                    reasonCode = payload.reason_code;
                }
            } catch {
                // Keep default reason code on malformed payload.
            }
            switchToPolling(reasonCode);
            stream.close();
        });

        stream.onerror = () => {
            if (stream.readyState === EventSource.CLOSED) {
                switchToPolling("stream_error_closed");
            }
        };

        return () => {
            stopped = true;
            stream.close();
        };
    }, [caseId, documentVisible, enabled, queryClient, sseEnabled]);

    const caseQuery = useQuery({
        queryKey: ["case", caseId],
        queryFn: () => fetchCase(caseId as string),
        enabled,
        refetchInterval: documentVisible ? casePollMs : false,
        refetchIntervalInBackground: false,
        refetchOnWindowFocus: true,
    });

    const messagesPollMs = syncMode === "sse"
        ? 45000
        : caseQuery.data?.status === "active"
            ? 8000
            : 15000;
    const messagesQuery = useInfiniteQuery({
        queryKey: ["messages", caseId],
        queryFn: ({ pageParam }) =>
            fetchMessagesPage(
                caseId as string,
                typeof pageParam === "string" ? pageParam : undefined,
            ),
        enabled,
        initialPageParam: undefined as string | undefined,
        getNextPageParam: (lastPage) =>
            lastPage.has_more ? (lastPage.cursor ?? undefined) : undefined,
        refetchInterval: documentVisible ? messagesPollMs : false,
        refetchIntervalInBackground: false,
        refetchOnWindowFocus: true,
    });
    const messages = (() => {
        const seen = new Set<string>();
        const merged: Message[] = [];
        for (const page of messagesQuery.data?.pages ?? []) {
            for (const item of page.items ?? []) {
                if (!item?.id || seen.has(item.id)) {
                    continue;
                }
                seen.add(item.id);
                merged.push(item);
            }
        }
        return merged;
    })();

    return {
        caseDetail: caseQuery.data,
        caseLoading: caseQuery.isLoading,
        caseError: caseQuery.error,
        refetchCase: caseQuery.refetch,
        messages,
        messagesLoading: messagesQuery.isLoading,
        messagesHasMore: Boolean(messagesQuery.hasNextPage),
        messagesLoadingMore: messagesQuery.isFetchingNextPage,
        liveSync: {
            mode: syncMode,
            reason_code: syncReasonCode,
        },
        loadMoreMessages: () => {
            if (!messagesQuery.hasNextPage || messagesQuery.isFetchingNextPage) {
                return Promise.resolve();
            }
            return messagesQuery.fetchNextPage();
        },
    };
}
