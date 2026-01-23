"use client"

import { useEffect, useMemo, useState } from "react"
import { SessionProvider, useSession } from "next-auth/react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import ToastProvider from "@/components/ToastProvider"
import ErrorBoundary from "@/components/ErrorBoundary"
import QueryProvider from "@/components/QueryProvider"
import { authApi } from "@/lib/api-client"

const CLIENT_ID_STORAGE_KEY = "console:client_id"
const BRANCH_ID_STORAGE_KEY = "console:branch_id"

function readSelectedClientId(): string {
    if (typeof window === "undefined") {
        return ""
    }
    return window.localStorage.getItem(CLIENT_ID_STORAGE_KEY) ?? ""
}

function persistSelectedClientId(value: string) {
    if (typeof window === "undefined") {
        return
    }
    if (value) {
        window.localStorage.setItem(CLIENT_ID_STORAGE_KEY, value)
    } else {
        window.localStorage.removeItem(CLIENT_ID_STORAGE_KEY)
    }
}

function readSelectedBranchId(): string {
    if (typeof window === "undefined") {
        return ""
    }
    return window.localStorage.getItem(BRANCH_ID_STORAGE_KEY) ?? ""
}

function persistSelectedBranchId(value: string) {
    if (typeof window === "undefined") {
        return
    }
    if (value) {
        window.localStorage.setItem(BRANCH_ID_STORAGE_KEY, value)
    } else {
        window.localStorage.removeItem(BRANCH_ID_STORAGE_KEY)
    }
}

function ClientSelectorGate() {
    const { status } = useSession()
    const queryClient = useQueryClient()
    const [selectedClientId, setSelectedClientId] = useState(() => readSelectedClientId())
    const [selectedBranchId, setSelectedBranchId] = useState(() => readSelectedBranchId())

    const { data: meData } = useQuery({
        queryKey: ["me", "client-selector"],
        queryFn: async () => {
            const { data } = await authApi.getMe()
            return data
        },
        enabled: status === "authenticated",
        staleTime: 5 * 60 * 1000,
        retry: false,
    })

    const clients = useMemo(() => {
        if (meData?.clients && meData.clients.length > 0) {
            return meData.clients
        }
        return meData?.client ? [meData.client] : []
    }, [meData])
    const branches = useMemo(() => meData?.branches ?? [], [meData])

    const hasMultipleClients = clients.length > 1
    const selectionRequired = Boolean(meData?.selection_required)
    const resolvedClientId = useMemo(() => {
        if (clients.length <= 1) {
            return clients[0]?.id ?? ""
        }
        if (selectedClientId && clients.some((client) => client.id === selectedClientId)) {
            return selectedClientId
        }
        return ""
    }, [clients, selectedClientId])
    const hasMultipleBranches = branches.length > 1
    const branchSelectionRequired = Boolean(meData?.branch_selection_required)
    const resolvedBranchId = useMemo(() => {
        if (branches.length <= 1) {
            return branches[0]?.id ?? ""
        }
        if (selectedBranchId && branches.some((branch) => branch.id === selectedBranchId)) {
            return selectedBranchId
        }
        return ""
    }, [branches, selectedBranchId])

    useEffect(() => {
        if (status !== "authenticated") {
            persistSelectedClientId("")
            persistSelectedBranchId("")
            return
        }
        persistSelectedClientId(resolvedClientId)
    }, [status, resolvedClientId])
    useEffect(() => {
        if (status !== "authenticated") {
            persistSelectedBranchId("")
            return
        }
        persistSelectedBranchId(resolvedBranchId)
    }, [status, resolvedBranchId])

    if (status !== "authenticated" || (!hasMultipleClients && !hasMultipleBranches)) {
        return null
    }

    const selectionMissing = !resolvedClientId
    const branchSelectionMissing = !resolvedBranchId

    return (
        <div className={`border-b ${selectionMissing ? "bg-amber-50 border-amber-200" : "bg-gray-50 border-gray-200"}`}>
            <div className="max-w-6xl mx-auto px-6 py-3 flex flex-wrap items-center gap-3">
                {hasMultipleClients && (
                    <>
                        <span className="text-sm font-medium text-gray-700">Клиент</span>
                        <select
                            data-testid="client-selector"
                            value={resolvedClientId}
                            onChange={(event) => {
                                const nextValue = event.target.value
                                setSelectedClientId(nextValue)
                                persistSelectedClientId(nextValue)
                                setSelectedBranchId("")
                                persistSelectedBranchId("")
                                queryClient.invalidateQueries()
                            }}
                            className="px-3 py-2 border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Выберите клиента</option>
                            {clients.map((client, index) => {
                                const clientId = client.id ?? ""
                                const label = client.name || client.slug || clientId || `Client ${index + 1}`
                                const key = clientId || client.slug || client.name || `${index}`
                                return (
                                    <option key={key} value={clientId}>
                                        {label}
                                    </option>
                                )
                            })}
                        </select>
                        {selectionMissing && selectionRequired && (
                            <span className="text-xs text-amber-700">
                                Выберите клиента, чтобы загрузить данные.
                            </span>
                        )}
                    </>
                )}
                {hasMultipleBranches && (
                    <>
                        <span className="text-sm font-medium text-gray-700">Филиал</span>
                        <select
                            data-testid="branch-selector"
                            value={resolvedBranchId}
                            onChange={(event) => {
                                const nextValue = event.target.value
                                setSelectedBranchId(nextValue)
                                persistSelectedBranchId(nextValue)
                                queryClient.invalidateQueries()
                            }}
                            className="px-3 py-2 border rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Выберите филиал</option>
                            {branches.map((branch) => {
                                const branchId = branch.id ?? ""
                                const label = branch.name || branch.slug || branchId
                                const key = branchId || branch.slug || branch.name
                                return (
                                    <option key={key} value={branchId}>
                                        {label}
                                    </option>
                                )
                            })}
                        </select>
                        {branchSelectionMissing && branchSelectionRequired && (
                            <span className="text-xs text-amber-700">
                                Выберите филиал, чтобы загрузить данные.
                            </span>
                        )}
                    </>
                )}
            </div>
        </div>
    )
}

export default function Providers({ children }: { children: React.ReactNode }) {
    return (
        <SessionProvider>
            <QueryProvider>
                <ErrorBoundary>
                    <ClientSelectorGate />
                    {children}
                    <ToastProvider />
                </ErrorBoundary>
            </QueryProvider>
        </SessionProvider>
    )
}
