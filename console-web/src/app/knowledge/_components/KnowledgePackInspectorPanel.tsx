"use client";

type KnowledgePackInspectorItem = {
    path: string;
    preview: string;
};

type KnowledgePackInspectorSummary = {
    flattenedFieldsCount: number;
    servicesCount: number;
    priceRowsCount: number;
    collectFieldsCount: number;
    policyFilledCount: number;
};

type KnowledgePackInspectorPanelProps = {
    summary: KnowledgePackInspectorSummary;
    query: string;
    onQueryChange: (value: string) => void;
    items: KnowledgePackInspectorItem[];
};

export default function KnowledgePackInspectorPanel({
    summary,
    query,
    onQueryChange,
    items,
}: KnowledgePackInspectorPanelProps) {
    return (
        <div className="rounded-lg border border-border/60 bg-background p-3" data-testid="knowledge-pack-inspector">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">Client Pack Inspector</p>
                <span className="text-xs text-muted-foreground">полей {summary.flattenedFieldsCount}</span>
            </div>
            <div className="mt-2 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-lg border border-border/60 px-2 py-1">services_catalog: {summary.servicesCount}</div>
                <div className="rounded-lg border border-border/60 px-2 py-1">price_list: {summary.priceRowsCount}</div>
                <div className="rounded-lg border border-border/60 px-2 py-1">booking.collect_fields: {summary.collectFieldsCount}</div>
                <div className="rounded-lg border border-border/60 px-2 py-1">policy заполнено: {summary.policyFilledCount}/4</div>
            </div>
            <label className="mt-3 block text-xs text-muted-foreground">
                Поиск по ключам Client_Pack
                <input
                    className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    value={query}
                    onChange={(event) => onQueryChange(event.target.value)}
                    placeholder="Например: client_pack.booking.collect_fields"
                />
            </label>
            <div className="mt-2 max-h-44 overflow-auto rounded-lg border border-border/60 bg-muted/30 p-2 text-xs">
                {items.length === 0 ? <div className="text-muted-foreground">Совпадений не найдено.</div> : null}
                {items.map((item) => (
                    <div key={`${item.path}-${item.preview}`} className="mb-1">
                        <span className="font-mono text-foreground">{item.path}</span>
                        <span className="text-muted-foreground"> = {item.preview}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
