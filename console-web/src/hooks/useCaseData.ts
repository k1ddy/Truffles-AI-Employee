"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import type { Case, Message } from "@/types";

async function fetchCase(caseId: string): Promise<Case> {
    const response = await api.get(`/cases/${caseId}`);
    return response.data;
}

async function fetchMessages(caseId: string): Promise<{ items: Message[] }> {
    const response = await api.get(`/cases/${caseId}/messages`);
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

    const messagesQuery = useQuery({
        queryKey: ["messages", caseId],
        queryFn: () => fetchMessages(caseId as string),
        enabled,
        refetchInterval: 5000,
        refetchIntervalInBackground: true,
        refetchOnWindowFocus: true,
    });

    return {
        caseDetail: caseQuery.data,
        caseLoading: caseQuery.isLoading,
        caseError: caseQuery.error,
        refetchCase: caseQuery.refetch,
        messages: messagesQuery.data?.items ?? [],
        messagesLoading: messagesQuery.isLoading,
    };
}
