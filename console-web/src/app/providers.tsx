"use client"

import { SessionProvider } from "next-auth/react"
import ToastProvider from "@/components/ToastProvider"
import ErrorBoundary from "@/components/ErrorBoundary"
import QueryProvider from "@/components/QueryProvider"

export default function Providers({ children }: { children: React.ReactNode }) {
    return (
        <SessionProvider>
            <QueryProvider>
                <ErrorBoundary>
                    {children}
                    <ToastProvider />
                </ErrorBoundary>
            </QueryProvider>
        </SessionProvider>
    )
}
