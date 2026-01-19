"use client";

import { Toaster } from "react-hot-toast";

export default function ToastProvider() {
    return (
        <Toaster
            position="top-right"
            toastOptions={{
                duration: 4000,
                style: {
                    background: "#333",
                    color: "#fff",
                },
                success: {
                    duration: 3000,
                    iconTheme: {
                        primary: "#22c55e",
                        secondary: "#fff",
                    },
                },
                error: {
                    duration: 5000,
                    iconTheme: {
                        primary: "#ef4444",
                        secondary: "#fff",
                    },
                },
            }}
        />
    );
}
