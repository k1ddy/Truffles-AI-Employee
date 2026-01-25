"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import CaseList from "@/components/CaseList";
import CaseConversation from "@/components/CaseConversation";
import CaseDetailsPanel from "@/components/CaseDetailsPanel";
import InboxMacros from "@/components/InboxMacros";
import { useCaseData } from "@/hooks/useCaseData";

interface InboxViewProps {
    initialCaseId?: string | null;
}

export default function InboxView({ initialCaseId }: InboxViewProps) {
    const router = useRouter();
    const [selectedCaseId, setSelectedCaseId] = useState(initialCaseId ?? "");
    const [draft, setDraft] = useState("");

    useEffect(() => {
        if (initialCaseId) {
            setSelectedCaseId(initialCaseId);
        }
    }, [initialCaseId]);

    useEffect(() => {
        setDraft("");
    }, [selectedCaseId]);

    const {
        caseDetail,
        caseLoading,
        caseError,
        refetchCase,
        messages,
        messagesLoading,
    } = useCaseData(selectedCaseId);

    const canSend = Boolean(caseDetail && caseDetail.status === "active");

    const handleSelectCase = (caseId: string) => {
        setSelectedCaseId(caseId);
        router.push(`/cases/${caseId}`);
    };

    const handleMacroSelect = (text: string) => {
        setDraft((prev) => (prev.trim() ? `${prev}\n${text}` : text));
    };

    const renderEmptyPane = (title: string, subtitle: string) => (
        <div className="card-surface p-6 text-center text-sm text-muted-foreground">
            <p className="font-semibold text-foreground mb-2">{title}</p>
            <p>{subtitle}</p>
        </div>
    );

    const renderErrorPane = () => (
        <div className="card-surface p-6 text-center text-sm text-destructive">
            <p className="mb-4">Не удалось загрузить заявку</p>
            <button
                onClick={() => refetchCase()}
                className="btn-ghost"
                data-testid="case-retry"
            >
                Повторить
            </button>
        </div>
    );

    const renderLoadingPane = () => (
        <div className="card-surface p-6 animate-pulse text-sm text-muted-foreground">
            Загрузка...
        </div>
    );

    return (
        <div className="space-y-6" data-testid="inbox-view">
            <div>
                <h1 className="text-2xl font-semibold">Inbox</h1>
                <p className="text-sm text-muted-foreground">
                    Рабочий экран менеджера: список → диалог → детали.
                </p>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_minmax(0,1fr)_320px]">
                <section className="card-surface p-4 flex flex-col min-h-[620px]" data-testid="inbox-list">
                    <CaseList
                        variant="compact"
                        selectedCaseId={selectedCaseId}
                        onSelectCase={handleSelectCase}
                    />
                </section>

                <section className="flex flex-col gap-4 min-h-[620px]" data-testid="inbox-conversation">
                    {!selectedCaseId && renderEmptyPane("Выберите заявку", "Кликните по карточке слева, чтобы открыть диалог.")}
                    {selectedCaseId && caseLoading && renderLoadingPane()}
                    {selectedCaseId && caseError && renderErrorPane()}
                    {selectedCaseId && !caseLoading && !caseError && caseDetail && (
                        <div className="card-surface p-5 flex flex-col">
                            <CaseConversation
                                caseDetail={caseDetail}
                                caseId={selectedCaseId}
                                messages={messages}
                                messagesLoading={messagesLoading}
                                canSend={canSend}
                                draft={draft}
                                onDraftChange={setDraft}
                            />
                        </div>
                    )}
                    {selectedCaseId && !caseLoading && !caseError && !caseDetail && (
                        <div className="card-surface p-6 text-center text-muted-foreground">
                            Заявка не найдена
                        </div>
                    )}
                    <InboxMacros onSelect={handleMacroSelect} disabled={!selectedCaseId || !canSend} />
                </section>

                <section className="flex flex-col gap-4 min-h-[620px]" data-testid="inbox-details">
                    {!selectedCaseId && renderEmptyPane("Детали", "Выберите заявку, чтобы увидеть контекст и trace.")}
                    {selectedCaseId && caseLoading && renderLoadingPane()}
                    {selectedCaseId && caseError && renderErrorPane()}
                    {selectedCaseId && !caseLoading && !caseError && caseDetail && (
                        <CaseDetailsPanel caseDetail={caseDetail} />
                    )}
                    {selectedCaseId && !caseLoading && !caseError && !caseDetail && (
                        <div className="card-surface p-6 text-center text-muted-foreground">
                            Детали недоступны
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
}
