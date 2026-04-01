"use client";

import { Toaster } from "react-hot-toast";

export default function ToastProvider() {
    return (
        <Toaster
            position="top-right"
            toastOptions={{
                duration: 4000,
                style: {
                    background: "hsl(var(--foreground))",
                    color: "hsl(var(--background))",
                    borderRadius: "12px",
                },
                success: {
                    duration: 3000,
                    iconTheme: {
                        primary: "#22c55e",
                        secondary: "hsl(var(--background))",
                    },
                },
                error: {
                    duration: 5000,
                    iconTheme: {
                        primary: "hsl(var(--destructive))",
                        secondary: "hsl(var(--background))",
                    },
                },
            }}
        />
    );
}
