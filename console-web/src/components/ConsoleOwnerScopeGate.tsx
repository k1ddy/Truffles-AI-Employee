import Link from "next/link";

type BranchOption = {
    id?: string | null;
    name?: string | null;
    slug?: string | null;
};

type ScopeGateLink = {
    href: string;
    label: string;
};

function formatBranchLabel(branch: BranchOption): string {
    return `${branch.name ?? branch.slug ?? branch.id} · ${branch.slug ?? String(branch.id).slice(0, 8)}`;
}

export default function ConsoleOwnerScopeGate({
    rootTestId,
    selectTestId,
    applyTestId,
    title,
    description,
    branchOptions,
    selectedBranchId,
    onSelectedBranchChange,
    onApply,
    applyLabel,
    applyPendingLabel = "Загрузка...",
    isApplying = false,
    disabled = false,
    emptyStateTitle,
    emptyStateDescription,
    links = [],
    className = "",
}: {
    rootTestId: string;
    selectTestId: string;
    applyTestId: string;
    title: string;
    description: string;
    branchOptions: BranchOption[];
    selectedBranchId: string;
    onSelectedBranchChange: (value: string) => void;
    onApply: () => void | Promise<void>;
    applyLabel: string;
    applyPendingLabel?: string;
    isApplying?: boolean;
    disabled?: boolean;
    emptyStateTitle?: string;
    emptyStateDescription?: string;
    links?: ScopeGateLink[];
    className?: string;
}) {
    return (
        <section
            className={`rounded-xl border border-amber-300/70 bg-amber-50 p-4 ${className}`.trim()}
            data-testid={rootTestId}
        >
            <p className="text-xs uppercase tracking-[0.16em] text-amber-800">Требуется выбор</p>
            <h2 className="mt-1 text-lg font-semibold text-foreground">{title}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{description}</p>
            {branchOptions.length > 0 ? (
                <div className="mt-4 flex flex-col gap-3 sm:flex-row">
                    <select
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                        value={selectedBranchId}
                        onChange={(event) => onSelectedBranchChange(event.target.value)}
                        data-testid={selectTestId}
                    >
                        <option value="">Выберите филиал</option>
                        {branchOptions.map((branch) => (
                            <option key={branch.id ?? branch.slug ?? "branch-option"} value={branch.id ?? ""}>
                                {formatBranchLabel(branch)}
                            </option>
                        ))}
                    </select>
                    <button
                        type="button"
                        className="btn-primary"
                        onClick={() => {
                            void onApply();
                        }}
                        disabled={disabled || isApplying || !selectedBranchId}
                        data-testid={applyTestId}
                    >
                        {isApplying ? applyPendingLabel : applyLabel}
                    </button>
                </div>
            ) : (
                <div className="mt-4 rounded-lg border border-border/60 bg-background px-3 py-3 text-sm text-muted-foreground">
                    <p>{emptyStateTitle ?? "Нет доступных филиалов в текущем контексте."}</p>
                    {emptyStateDescription ? <p className="mt-2 text-xs">{emptyStateDescription}</p> : null}
                </div>
            )}
            {links.length > 0 ? (
                <div className="mt-4 flex flex-wrap gap-3 text-sm">
                    {links.map((link) => (
                        <Link key={`${link.href}:${link.label}`} href={link.href} className="btn-ghost">
                            {link.label}
                        </Link>
                    ))}
                </div>
            ) : null}
        </section>
    );
}
