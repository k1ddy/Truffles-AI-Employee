"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast";

export type TenantsSensitiveAction = "reveal" | "copy";

type TenantsSensitiveIdCellProps = {
    branchId?: string | null;
    instanceId: string | null | undefined;
    contextScope?: string;
    onAudit?: (input: {
        branchId: string;
        field: "instance_id";
        action: TenantsSensitiveAction;
        contextScope?: string;
    }) => Promise<void>;
};

function formatMaskedInstanceId(value: string | null | undefined): string {
    const normalized = (value ?? "").trim();
    if (!normalized) {
        return "instance_id: —";
    }
    if (normalized.length <= 4) {
        return `instance_id: ${"*".repeat(normalized.length)}`;
    }
    const visibleHead = normalized.slice(0, 2);
    const visibleTail = normalized.slice(-2);
    return `instance_id: ${visibleHead}***${visibleTail}`;
}

export default function TenantsSensitiveIdCell({
    branchId,
    instanceId,
    contextScope,
    onAudit,
}: TenantsSensitiveIdCellProps) {
    const [revealed, setRevealed] = useState(false);
    const hasValue = Boolean((instanceId ?? "").trim());
    const normalizedValue = (instanceId ?? "").trim();

    useEffect(() => {
        if (!revealed) {
            return;
        }
        const timeout = window.setTimeout(() => setRevealed(false), 20000);
        return () => window.clearTimeout(timeout);
    }, [revealed]);

    const trackAudit = async (action: TenantsSensitiveAction) => {
        if (!onAudit || !branchId || !hasValue) {
            return;
        }
        try {
            await onAudit({
                branchId,
                field: "instance_id",
                action,
                contextScope,
            });
        } catch {
            // Access action already happened in UI; keep UX non-blocking and report concise signal.
            toast.error("Не удалось записать audit по доступу к instance_id");
        }
    };

    const handleToggleReveal = async () => {
        if (!hasValue) {
            return;
        }
        if (revealed) {
            setRevealed(false);
            return;
        }
        setRevealed(true);
        await trackAudit("reveal");
    };

    const handleCopy = async () => {
        if (!hasValue) {
            return;
        }
        try {
            await navigator.clipboard.writeText(normalizedValue);
            toast.success("instance_id скопирован");
        } catch {
            toast.error("Не удалось скопировать instance_id");
            return;
        }
        await trackAudit("copy");
    };

    return (
        <div className="text-xs text-muted-foreground" data-testid="tenants-sensitive-id-cell">
            <span>{revealed ? `instance_id: ${normalizedValue}` : formatMaskedInstanceId(normalizedValue)}</span>
            {hasValue ? (
                <span className="ml-2 inline-flex items-center gap-1">
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={handleToggleReveal}
                        aria-label={revealed ? "Скрыть instance_id" : "Показать instance_id"}
                        data-testid="tenants-instance-id-reveal"
                    >
                        {revealed ? "Скрыть" : "Показать"}
                    </button>
                    <button
                        type="button"
                        className="btn-ghost"
                        onClick={handleCopy}
                        aria-label="Скопировать instance_id"
                        data-testid="tenants-instance-id-copy"
                    >
                        Копировать
                    </button>
                </span>
            ) : null}
        </div>
    );
}
