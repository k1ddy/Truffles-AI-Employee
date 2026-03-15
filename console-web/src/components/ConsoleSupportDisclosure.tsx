import type { ReactNode } from "react";

type ConsoleSupportDisclosureProps = {
    rootTestId: string;
    title: string;
    description?: string;
    defaultOpen?: boolean;
    className?: string;
    children: ReactNode;
};

export default function ConsoleSupportDisclosure({
    rootTestId,
    title,
    description,
    defaultOpen = false,
    className = "",
    children,
}: ConsoleSupportDisclosureProps) {
    return (
        <details
            open={defaultOpen}
            className={`rounded-xl border border-border/60 bg-muted/10 p-3 ${className}`.trim()}
            data-testid={rootTestId}
        >
            <summary className="cursor-pointer list-none">
                <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                        <p className="text-sm font-semibold text-foreground">{title}</p>
                        {description ? <p className="mt-1 text-xs text-muted-foreground">{description}</p> : null}
                    </div>
                    <span className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Вторично</span>
                </div>
            </summary>
            <div className="mt-3">{children}</div>
        </details>
    );
}
