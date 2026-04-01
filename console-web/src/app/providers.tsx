"use client"

import { SessionProvider } from "next-auth/react"
import ToastProvider from "@/components/ToastProvider"
import ErrorBoundary from "@/components/ErrorBoundary"
import QueryProvider from "@/components/QueryProvider"

const SESSION_REFETCH_INTERVAL_SECONDS = Number(process.env.NEXT_PUBLIC_SESSION_KEEPALIVE_SECONDS ?? 5 * 60)

export default function Providers({ children }: { children: React.ReactNode }) {
    return (
        <SessionProvider
            refetchInterval={SESSION_REFETCH_INTERVAL_SECONDS}
            refetchOnWindowFocus={true}
        >
            <QueryProvider>
                <ErrorBoundary>
                    {children}
                    <ToastProvider />
                </ErrorBoundary>
            </QueryProvider>
        </SessionProvider>
    )
}
