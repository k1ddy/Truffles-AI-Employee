"use client";

import React from "react";

interface Props {
    children: React.ReactNode;
    fallback?: React.ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: React.ErrorInfo | null;
}

export default class ErrorBoundary extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error("ErrorBoundary caught an error:", error, errorInfo);
        this.setState({ errorInfo });

        // Optional: Send to error tracking service
        // if (typeof window !== 'undefined' && window.Sentry) {
        //   window.Sentry.captureException(error, { extra: errorInfo });
        // }
    }

    handleRetry = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
    };

    handleReload = () => {
        if (typeof window !== 'undefined') {
            window.location.reload();
        }
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="flex flex-col items-center justify-center min-h-[400px] p-8 bg-destructive/10 rounded-lg border border-destructive/30">
                    <div className="text-destructive text-6xl mb-4">⚠️</div>
                    <h2 className="text-xl font-bold text-destructive mb-2">Что-то пошло не так</h2>
                    <p className="text-destructive/80 mb-4 text-center max-w-md">
                        {this.state.error?.message || "Произошла непредвиденная ошибка"}
                    </p>

                    <div className="flex gap-3">
                        <button
                            onClick={this.handleRetry}
                            className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                        >
                            Повторить
                        </button>
                        <button
                            onClick={this.handleReload}
                            className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
                        >
                            Обновить страницу
                        </button>
                    </div>

                    {/* Debug info for development */}
                    {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
                        <details className="mt-4 w-full max-w-lg">
                            <summary className="text-sm text-muted-foreground cursor-pointer hover:text-foreground">
                                Технические детали
                            </summary>
                            <pre className="mt-2 p-3 bg-card rounded text-xs overflow-auto max-h-32 border border-border/60">
                                {this.state.errorInfo.componentStack}
                            </pre>
                        </details>
                    )}
                </div>
            );
        }

        return this.props.children;
    }
}
