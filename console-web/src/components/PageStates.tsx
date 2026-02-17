"use client";

type ConsolePageSkeletonProps = {
    pageTestId: string;
    title: string;
    titleTestId: string;
    columns?: 1 | 2 | 3 | 4;
    cardCount?: number;
    cardHeightClass?: string;
    maxWidthClass?: string;
};

export function ConsolePageSkeleton({
    pageTestId,
    title,
    titleTestId,
    columns = 3,
    cardCount = 3,
    cardHeightClass = "h-24",
    maxWidthClass = "max-w-6xl",
}: ConsolePageSkeletonProps) {
    const gridClass = columns === 4
        ? "md:grid-cols-4"
        : columns === 3
            ? "md:grid-cols-3"
            : columns === 2
                ? "md:grid-cols-2"
                : "md:grid-cols-1";

    return (
        <div className={`mx-auto ${maxWidthClass} p-6`} data-testid={pageTestId}>
            <h1 className="mb-6 text-2xl font-bold" data-testid={titleTestId}>{title}</h1>
            <div className={`grid grid-cols-1 gap-4 ${gridClass}`}>
                {Array.from({ length: cardCount }).map((_, index) => (
                    <div key={index} className={`${cardHeightClass} animate-pulse rounded-lg bg-muted/70`} />
                ))}
            </div>
        </div>
    );
}

type ConsolePageErrorProps = {
    pageTestId: string;
    title: string;
    titleTestId: string;
    errorTestId: string;
    retryTestId: string;
    errorMessage: string;
    retryLabel?: string;
    maxWidthClass?: string;
    onRetry: () => void;
};

export function ConsolePageError({
    pageTestId,
    title,
    titleTestId,
    errorTestId,
    retryTestId,
    errorMessage,
    retryLabel = "Повторить",
    maxWidthClass = "max-w-6xl",
    onRetry,
}: ConsolePageErrorProps) {
    return (
        <div className={`mx-auto ${maxWidthClass} p-6`} data-testid={pageTestId}>
            <h1 className="mb-6 text-2xl font-bold" data-testid={titleTestId}>{title}</h1>
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-6 text-center" data-testid={errorTestId}>
                <p className="mb-4 text-destructive">{errorMessage}</p>
                <button
                    onClick={onRetry}
                    className="rounded-full bg-destructive px-4 py-2 text-sm font-semibold text-destructive-foreground transition hover:bg-destructive/90"
                    data-testid={retryTestId}
                >
                    {retryLabel}
                </button>
            </div>
        </div>
    );
}
