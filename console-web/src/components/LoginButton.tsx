"use client"

import { signIn, signOut, useSession } from "next-auth/react"

import { clearConsoleContextScope } from "@/lib/console-context-storage"

export default function LoginButton() {
    const { data: session } = useSession()

    if (session) {
        return (
            <div className="flex gap-4 items-center">
                <p className="text-sm text-muted-foreground">Вы вошли</p>
                <button
                    onClick={() => {
                        if (typeof window !== "undefined") {
                            clearConsoleContextScope()
                            const inboxWorkspacePrefixes = [
                                "console:inbox:case-list:v1:",
                                "console:inbox:selected-case:v1:",
                            ]
                            const keysToRemove: string[] = []
                            for (let index = 0; index < window.localStorage.length; index += 1) {
                                const key = window.localStorage.key(index)
                                if (!key) {
                                    continue
                                }
                                if (inboxWorkspacePrefixes.some((prefix) => key.startsWith(prefix))) {
                                    keysToRemove.push(key)
                                }
                            }
                            keysToRemove.forEach((key) => window.localStorage.removeItem(key))
                        }
                        signOut()
                    }}
                    className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                    data-testid="logout-button"
                >
                    Выйти
                </button>
            </div>
        )
    }
    return (
        <button
            onClick={() => signIn("keycloak")}
            className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
            data-testid="login-button"
        >
            Войти через SSO
        </button>
    )
}
