"use client"

import { signIn, signOut, useSession } from "next-auth/react"

export default function LoginButton() {
    const { data: session } = useSession()

    if (session) {
        return (
            <div className="flex gap-4 items-center">
                <p className="text-sm text-gray-600">Вы вошли</p>
                <button
                    onClick={() => {
                        if (typeof window !== "undefined") {
                            window.localStorage.removeItem("console:client_id")
                        }
                        signOut()
                    }}
                    className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                >
                    Выйти
                </button>
            </div>
        )
    }
    return (
        <button onClick={() => signIn("keycloak")} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
            Войти через SSO
        </button>
    )
}
