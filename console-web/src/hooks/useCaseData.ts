"use client";

import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Case, Message } from "@/types";

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

export function useCaseData(caseId?: string | null) {
    const enabled = Boolean(caseId);

    const caseQuery = useQuery({
        queryKey: ["case", caseId],
        queryFn: () => fetchCase(caseId as string),
        enabled,
        refetchInterval: 10000,
        refetchIntervalInBackground: true,
        refetchOnWindowFocus: true,
    });

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
        refetchInterval: 5000,
        refetchIntervalInBackground: true,
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
        loadMoreMessages: () => {
            if (!messagesQuery.hasNextPage || messagesQuery.isFetchingNextPage) {
                return Promise.resolve();
            }
            return messagesQuery.fetchNextPage();
        },
    };
}
