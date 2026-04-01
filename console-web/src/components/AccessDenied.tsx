"use client";

import Link from "next/link";

interface AccessDeniedProps {
    message?: string;
}

export default function AccessDenied({ message }: AccessDeniedProps) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <div className="max-w-md w-full bg-card rounded-lg shadow-lg p-8 text-center border border-border/60">
                <div className="text-6xl mb-4">🚫</div>
                <h1 className="text-2xl font-bold text-foreground mb-2">
                    Нет доступа
                </h1>
                <p className="text-muted-foreground mb-6">
                    {message || "У вас нет доступа к этой системе. Обратитесь к администратору для получения доступа."}
                </p>
                <div className="flex flex-col gap-3">
                    <Link
                        href="/"
                        className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
                    >
                        На главную
                    </Link>
                    <a
                        href="mailto:support@truffles.kz"
                        className="text-sm text-muted-foreground hover:text-foreground"
                    >
                        Связаться с поддержкой
                    </a>
                </div>
            </div>
        </div>
    );
}
