"use client";

import { useEffect, useState } from "react";
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
    const casePollMs = 30000;

    const caseQuery = useQuery({
        queryKey: ["case", caseId],
        queryFn: () => fetchCase(caseId as string),
        enabled,
        refetchInterval: documentVisible ? casePollMs : false,
        refetchIntervalInBackground: false,
        refetchOnWindowFocus: true,
    });

    const messagesPollMs = caseQuery.data?.status === "active" ? 8000 : 15000;
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
        loadMoreMessages: () => {
            if (!messagesQuery.hasNextPage || messagesQuery.isFetchingNextPage) {
                return Promise.resolve();
            }
            return messagesQuery.fetchNextPage();
        },
    };
}
