"use client";

import Link from "next/link";

interface AccessDeniedProps {
    message?: string;
}

export default function AccessDenied({ message }: AccessDeniedProps) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
                <div className="text-6xl mb-4">🚫</div>
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                    Нет доступа
                </h1>
                <p className="text-gray-600 mb-6">
                    {message || "У вас нет доступа к этой системе. Обратитесь к администратору для получения доступа."}
                </p>
                <div className="flex flex-col gap-3">
                    <Link
                        href="/"
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        На главную
                    </Link>
                    <a
                        href="mailto:support@truffles.kz"
                        className="text-sm text-gray-500 hover:text-blue-600"
                    >
                        Связаться с поддержкой
                    </a>
                </div>
            </div>
        </div>
    );
}
