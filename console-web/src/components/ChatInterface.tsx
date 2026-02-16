"use client";

import { useState, useRef, useEffect, type ReactNode } from "react";
import { Message } from "@/types";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import toast from "react-hot-toast";

interface ChatInterfaceProps {
    messages: Message[];
    conversationId: string;
    caseId: string;  // For query invalidation (handover ID)
    isLoading?: boolean;
    hasMoreMessages?: boolean;
    loadingMoreMessages?: boolean;
    onLoadMoreMessages?: () => void;
    canSend?: boolean; // Allow sending messages (case must be active)
    draft?: string;
    onDraftChange?: (value: string) => void;
    composerBefore?: ReactNode;
    frame?: "card" | "plain";
}

type LocalMessageStatus = "sending" | "failed";
type LocalMessageKind = "text" | "media";
type LocalMessage = Message & {
    localId: string;
    localStatus: LocalMessageStatus;
    localKind: LocalMessageKind;
};

const isLocalMessage = (message: Message | LocalMessage): message is LocalMessage =>
    "localStatus" in message;

interface SendManagerMessageResponse {
    success?: boolean;
    message?: Message;
}

async function sendMessage(conversationId: string, content: string) {
    const response = await api.post(`/conversations/${conversationId}/messages`, {
        content,
    });
    return response.data as SendManagerMessageResponse;
}

async function sendMediaMessage(conversationId: string, file: File, caption?: string) {
    const formData = new FormData();
    formData.append("file", file);
    if (caption && caption.trim()) {
        formData.append("caption", caption.trim());
    }
    const response = await api.post(`/conversations/${conversationId}/messages/media`, formData);
    return response.data as SendManagerMessageResponse;
}

const VIDEO_EXTENSIONS = new Set([".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"]);
const IMAGE_EXTENSIONS = new Set([".jpg", ".jpeg", ".png", ".gif", ".webp"]);
const AUDIO_EXTENSIONS = new Set([".ogg", ".mp3", ".wav", ".m4a", ".aac", ".opus"]);
const MEDIA_LABELS: Record<string, string> = {
    photo: "Фото",
    audio: "Аудио",
    document: "Документ",
};

function formatBytes(bytes?: number) {
    if (!bytes || bytes <= 0) {
        return null;
    }
    if (bytes < 1024) {
        return `${bytes} B`;
    }
    const kb = bytes / 1024;
    if (kb < 1024) {
        return `${kb.toFixed(1)} KB`;
    }
    const mb = kb / 1024;
    return `${mb.toFixed(1)} MB`;
}

function resolveMediaType(file: File) {
    const extension = file.name.includes(".")
        ? `.${file.name.split(".").pop()?.toLowerCase()}`
        : "";
    if (file.type.startsWith("image/") || IMAGE_EXTENSIONS.has(extension)) {
        return "photo";
    }
    if (file.type.startsWith("audio/") || AUDIO_EXTENSIONS.has(extension)) {
        return "audio";
    }
    return "document";
}

export default function ChatInterface({
    messages,
    conversationId,
    caseId,
    isLoading,
    hasMoreMessages = false,
    loadingMoreMessages = false,
    onLoadMoreMessages,
    canSend = true,
    draft,
    onDraftChange,
    composerBefore,
    frame = "card",
}: ChatInterfaceProps) {
    const isControlled = typeof onDraftChange === "function";
    const [internalDraft, setInternalDraft] = useState("");
    const [attachedFile, setAttachedFile] = useState<File | null>(null);
    const [localMessages, setLocalMessages] = useState<LocalMessage[]>([]);
    const inputValue = isControlled ? draft ?? "" : internalDraft;
    const setInputValue = isControlled ? onDraftChange : setInternalDraft;
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const lastMessageIdRef = useRef<string | null>(null);
    const prependAnchorRef = useRef<{ scrollHeight: number; scrollTop: number; baseCount: number } | null>(null);
    const shouldStickToBottomRef = useRef(true);
    const queryClient = useQueryClient();
    const isPlain = frame === "plain";
    const maxTextareaHeight = 220;
    const minTextareaHeight = 44;

    const createLocalId = (prefix: string) =>
        `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
    const addLocalMessage = (message: LocalMessage) => {
        setLocalMessages((prev) => [message, ...prev]);
    };
    const updateLocalMessageStatus = (localId: string, status: LocalMessageStatus) => {
        setLocalMessages((prev) =>
            prev.map((message) =>
                message.localId === localId
                    ? {
                        ...message,
                        localStatus: status,
                    }
                    : message
            )
        );
    };
    const removeLocalMessage = (localId: string) => {
        setLocalMessages((prev) => prev.filter((message) => message.localId !== localId));
    };
    const retryLocalMessage = (message: LocalMessage) => {
        if (message.localKind !== "text") {
            return;
        }
        const content = message.content?.trim();
        if (!content) {
            return;
        }
        removeLocalMessage(message.localId);
        sendMutation.mutate(content);
    };

    const displayMessages = localMessages.length ? [...localMessages, ...messages] : messages;
    const sortedMessages = [...displayMessages].reverse();
    const isNearBottom = (node: HTMLDivElement, threshold = 120) =>
        node.scrollHeight - node.scrollTop - node.clientHeight <= threshold;
    const scrollToBottom = () => {
        if (!scrollContainerRef.current) {
            return;
        }
        scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    };

    // Scroll to bottom on new messages
    useEffect(() => {
        const latestId = messages[0]?.id || null;
        if (latestId && latestId !== lastMessageIdRef.current) {
            lastMessageIdRef.current = latestId;
            if (scrollContainerRef.current && shouldStickToBottomRef.current) {
                scrollToBottom();
            }
        }
    }, [messages]);

    useEffect(() => {
        const anchor = prependAnchorRef.current;
        if (!anchor || !scrollContainerRef.current) {
            return;
        }
        if (sortedMessages.length > anchor.baseCount) {
            const container = scrollContainerRef.current;
            const delta = container.scrollHeight - anchor.scrollHeight;
            container.scrollTop = anchor.scrollTop + delta;
            prependAnchorRef.current = null;
        }
    }, [sortedMessages.length]);

    useEffect(() => {
        if (loadingMoreMessages) {
            return;
        }
        const anchor = prependAnchorRef.current;
        if (!anchor) {
            return;
        }
        if (sortedMessages.length <= anchor.baseCount) {
            prependAnchorRef.current = null;
        }
    }, [loadingMoreMessages, sortedMessages.length]);

    useEffect(() => {
        setLocalMessages([]);
        lastMessageIdRef.current = null;
        prependAnchorRef.current = null;
        shouldStickToBottomRef.current = true;
    }, [caseId]);

    useEffect(() => {
        const textarea = textareaRef.current;
        if (!textarea) {
            return;
        }
        textarea.style.height = "auto";
        const nextHeight = Math.min(textarea.scrollHeight, maxTextareaHeight);
        textarea.style.height = `${Math.max(nextHeight, minTextareaHeight)}px`;
        textarea.style.overflowY = textarea.scrollHeight > maxTextareaHeight ? "auto" : "hidden";
    }, [inputValue, maxTextareaHeight, minTextareaHeight]);

    // Send message mutation with optimistic updates
    const sendMutation = useMutation({
        mutationFn: (content: string) => sendMessage(conversationId, content),
        onMutate: async (content) => {
            await queryClient.cancelQueries({ queryKey: ["messages", caseId] });
            const localId = createLocalId("temp");
            const optimisticMessage: LocalMessage = {
                id: localId,
                localId,
                localStatus: "sending",
                localKind: "text",
                role: "manager",
                content,
                created_at: new Date().toISOString(),
            };
            addLocalMessage(optimisticMessage);

            // Scroll to bottom on optimistic update
            shouldStickToBottomRef.current = true;
            scrollToBottom();

            return { localId, content };
        },
        onSuccess: (response, _, context) => {
            if (response?.success === false) {
                if (context?.localId) {
                    updateLocalMessageStatus(context.localId, "failed");
                }
                if (context?.content) {
                    setInputValue(context.content);
                }
                toast.error("Не удалось отправить сообщение");
                return;
            }
            if (context?.localId) {
                removeLocalMessage(context.localId);
            }
            setInputValue("");
            queryClient.invalidateQueries({ queryKey: ["messages", caseId] });
            toast.success("Сообщение отправлено");
        },
        onError: (error: unknown, _, context) => {
            if (context?.localId) {
                updateLocalMessageStatus(context.localId, "failed");
            }
            if (context?.content) {
                setInputValue(context.content);
            }
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "NOT_ASSIGNED") {
                toast.error("Вы не назначены на эту заявку");
            } else if (code === "CASE_NOT_ACTIVE") {
                toast.error("Заявка должна быть активной для отправки сообщений");
            } else {
                toast.error("Не удалось отправить сообщение");
            }
        },
    });

    const mediaMutation = useMutation({
        mutationFn: ({ file, caption }: { file: File; caption?: string }) =>
            sendMediaMessage(conversationId, file, caption),
        onMutate: async ({ file, caption }) => {
            const mediaType = resolveMediaType(file);
            const localId = createLocalId("temp-media");
            const optimisticMessage: LocalMessage = {
                id: localId,
                localId,
                localStatus: "sending",
                localKind: "media",
                role: "manager",
                content: caption?.trim() || `[${mediaType}]`,
                created_at: new Date().toISOString(),
                metadata: {
                    media: {
                        type: mediaType,
                        file_name: file.name,
                        mime: file.type,
                        size_bytes: file.size,
                        source: "console",
                    },
                    source: "console",
                },
            };
            addLocalMessage(optimisticMessage);

            shouldStickToBottomRef.current = true;
            scrollToBottom();

            return { localId, caption: caption?.trim() || "" };
        },
        onSuccess: (data, _, context) => {
            if (data?.success === false) {
                if (context?.localId) {
                    updateLocalMessageStatus(context.localId, "failed");
                }
                if (context?.caption) {
                    setInputValue(context.caption);
                }
                toast.error("Не удалось отправить медиа");
                return;
            }
            if (context?.localId) {
                removeLocalMessage(context.localId);
            }
            setInputValue("");
            clearAttachment();
            queryClient.invalidateQueries({ queryKey: ["messages", caseId] });
            toast.success("Медиа отправлено");
        },
        onError: (error: unknown, _, context) => {
            if (context?.localId) {
                updateLocalMessageStatus(context.localId, "failed");
            }
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "NOT_ASSIGNED") {
                toast.error("Вы не назначены на эту заявку");
            } else if (code === "CASE_NOT_ACTIVE") {
                toast.error("Заявка должна быть активной для отправки сообщений");
            } else if (code === "MEDIA_TOO_LARGE") {
                toast.error("Файл слишком большой");
            } else if (code === "MEDIA_TYPE_FORBIDDEN") {
                toast.error("Видео из консоли не поддерживается");
            } else if (code === "MEDIA_EMPTY") {
                toast.error("Файл пустой");
            } else {
                toast.error("Не удалось отправить медиа");
            }
        },
    });

    const isSending = sendMutation.isPending || mediaMutation.isPending;
    const handleMessagesScroll = () => {
        if (!scrollContainerRef.current) {
            return;
        }
        shouldStickToBottomRef.current = isNearBottom(scrollContainerRef.current);
    };
    const handleLoadMoreMessages = () => {
        if (!onLoadMoreMessages || loadingMoreMessages) {
            return;
        }
        if (scrollContainerRef.current) {
            prependAnchorRef.current = {
                scrollHeight: scrollContainerRef.current.scrollHeight,
                scrollTop: scrollContainerRef.current.scrollTop,
                baseCount: sortedMessages.length,
            };
        }
        onLoadMoreMessages();
    };

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }
        const extension = file.name.includes(".")
            ? `.${file.name.split(".").pop()?.toLowerCase()}`
            : "";
        if (file.type.startsWith("video/") || VIDEO_EXTENSIONS.has(extension)) {
            toast.error("Видео из консоли не поддерживается");
            event.target.value = "";
            return;
        }
        setAttachedFile(file);
    };

    const clearAttachment = () => {
        setAttachedFile(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (attachedFile) {
            mediaMutation.mutate({ file: attachedFile, caption: inputValue });
            return;
        }
        const content = inputValue.trim();
        if (!content) return;
        setInputValue(""); // Clear immediately for better UX
        sendMutation.mutate(content);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        // Enter (without shift) or Ctrl+Enter to send
        if ((e.key === "Enter" && !e.shiftKey) || (e.key === "Enter" && e.ctrlKey)) {
            e.preventDefault();
            handleSubmit(e);
        }
        // Escape to clear input
        if (e.key === "Escape") {
            setInputValue("");
            clearAttachment();
        }
    };

    if (isLoading) {
        return (
            <div
                className={`flex flex-col gap-4 p-4 h-full min-h-0 overflow-y-auto ${
                    isPlain ? "" : "bg-muted/60 rounded-xl"
                }`}
            >
                <div className="animate-pulse space-y-4">
                    <div className="h-16 bg-muted/70 rounded-lg w-3/4"></div>
                    <div className="h-16 bg-muted/70 rounded-lg w-2/3 self-end ml-auto"></div>
                    <div className="h-16 bg-muted/70 rounded-lg w-3/4"></div>
                </div>
            </div>
        );
    }

    return (
        <div
            className={`flex flex-col h-full min-h-0 ${
                isPlain ? "" : "bg-muted/60 rounded-xl overflow-hidden"
            }`}
        >
            {/* Messages area */}
            <div
                ref={scrollContainerRef}
                onScroll={handleMessagesScroll}
                className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4"
            >
                {hasMoreMessages && (
                    <div className="flex justify-center pb-2">
                        <button
                            type="button"
                            onClick={handleLoadMoreMessages}
                            disabled={loadingMoreMessages}
                            className="rounded-full border border-border/60 px-3 py-1 text-xs font-semibold text-muted-foreground hover:text-foreground disabled:opacity-60 disabled:cursor-not-allowed"
                            data-testid="chat-load-more"
                        >
                            {loadingMoreMessages ? "Загрузка..." : "Загрузить более ранние"}
                        </button>
                    </div>
                )}
                {sortedMessages.length === 0 ? (
                    <div className="text-center text-muted-foreground my-auto">
                        Нет сообщений
                    </div>
                ) : (
                    sortedMessages.map((msg) => {
                        const isLocal = isLocalMessage(msg);
                        const localStatus = isLocal ? msg.localStatus : null;
                        const isSending = localStatus === "sending";
                        const isFailed = localStatus === "failed";
                        const statusSuffix = isSending ? " (отправка...)" : isFailed ? " (не доставлено)" : "";
                        const mediaMeta = (msg.metadata as { media?: Record<string, unknown> } | null)?.media;
                        const mediaType = typeof mediaMeta?.type === "string" ? mediaMeta.type : null;
                        const mediaLabel = mediaType ? (MEDIA_LABELS[mediaType] ?? "Файл") : null;
                        const fileName = typeof mediaMeta?.file_name === "string" ? mediaMeta.file_name : null;
                        const publicUrl = typeof mediaMeta?.public_url === "string" ? mediaMeta.public_url : null;
                        const originUrl = typeof mediaMeta?.url === "string" ? mediaMeta.url : null;
                        const mediaUrl = publicUrl ?? (mediaLabel ? originUrl : null);
                        const sizeRaw = mediaMeta?.size_bytes;
                        const sizeBytes = typeof sizeRaw === "number" ? sizeRaw : Number(sizeRaw);
                        const sizeLabel = Number.isFinite(sizeBytes) ? formatBytes(sizeBytes) : null;
                        const contentValue = msg.content?.trim();
                        const isPlaceholder = Boolean(
                            mediaType && contentValue && /^\[.+\]$/.test(contentValue)
                        );
                        return (
                            <div
                                key={msg.id}
                                className={`flex flex-col max-w-[92%] ${msg.role === "user" ? "self-start" : "self-end items-end"} ${isSending ? "opacity-70" : ""}`}
                            >
                                <div className={`text-xs mb-1 ${isFailed ? "text-amber-700" : "text-muted-foreground"}`}>
                                    {msg.role === "user" ? "Клиент" :
                                        msg.role === "manager" ? "Менеджер" : "Бот"}
                                    {statusSuffix}
                                </div>
                                <div
                                    className={`p-3 rounded-lg ${msg.role === "user"
                                        ? "bg-card border border-border/60"
                                        : msg.role === "manager"
                                            ? "bg-primary text-primary-foreground"
                                            : "bg-foreground text-background"
                                        }`}
                                >
                                    {!isPlaceholder && (
                                        <p className="whitespace-pre-wrap">{msg.content}</p>
                                    )}
                                    {mediaType && (
                                        <div className="mt-2 rounded-md border border-border/60 bg-background/70 px-2 py-1 text-xs text-foreground">
                                            <div className="font-semibold">{mediaLabel}</div>
                                            <div className="text-muted-foreground">
                                                {fileName ?? "Файл"}
                                                {sizeLabel ? ` · ${sizeLabel}` : ""}
                                            </div>
                                            {mediaUrl && mediaType === "photo" && (
                                                <a
                                                    href={mediaUrl}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="mt-2 block"
                                                >
                                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                                    <img
                                                        src={mediaUrl}
                                                        alt={fileName ?? mediaLabel ?? "Фото"}
                                                        loading="lazy"
                                                        className="w-full max-w-[320px] rounded-md border border-border/40 object-cover"
                                                    />
                                                </a>
                                            )}
                                            {mediaUrl && mediaType === "audio" && (
                                                <audio
                                                    controls
                                                    preload="metadata"
                                                    className="mt-2 w-full"
                                                    src={mediaUrl}
                                                />
                                            )}
                                            {mediaUrl && (
                                                <a
                                                    href={mediaUrl}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="mt-1 inline-flex text-primary underline-offset-2 hover:underline"
                                                >
                                                    Открыть
                                                </a>
                                            )}
                                        </div>
                                    )}
                                </div>
                                <span className="text-xs text-muted-foreground mt-1">
                                    {isSending ? "..." : isFailed ? "Не доставлено" : new Date(msg.created_at).toLocaleString("ru-RU")}
                                </span>
                                {isFailed && isLocal && msg.localKind === "text" && (
                                    <button
                                        type="button"
                                        onClick={() => retryLocalMessage(msg)}
                                        className="mt-1 text-xs text-amber-700 hover:text-amber-800 underline underline-offset-4"
                                    >
                                        Повторить
                                    </button>
                                )}
                            </div>
                        );
                    })
                )}
            </div>

            {/* Input area */}
            {canSend && (
                <div className="border-t border-border/60 p-3 bg-card">
                    {composerBefore && (
                        <div className="mb-2">
                            {composerBefore}
                        </div>
                    )}
                    <form onSubmit={handleSubmit} className="space-y-2">
                        {attachedFile && (
                            <div className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/40 px-3 py-2 text-xs">
                                <div className="min-w-0">
                                    <div className="font-semibold text-foreground">
                                        {MEDIA_LABELS[resolveMediaType(attachedFile)] ?? "Файл"}
                                    </div>
                                    <div className="truncate text-muted-foreground">
                                        {attachedFile.name}
                                        {formatBytes(attachedFile.size) ? ` · ${formatBytes(attachedFile.size)}` : ""}
                                    </div>
                                </div>
                                <button
                                    type="button"
                                    onClick={clearAttachment}
                                    className="text-muted-foreground hover:text-foreground"
                                >
                                    Убрать
                                </button>
                            </div>
                        )}
                        <div className="flex gap-2">
                            <label className="flex h-[44px] w-[44px] items-center justify-center rounded-lg border border-border/60 bg-background text-lg text-muted-foreground transition hover:text-foreground">
                                <span aria-hidden="true">📎</span>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    onChange={handleFileChange}
                                    accept="image/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.txt"
                                    className="hidden"
                                    disabled={isSending}
                                    aria-label="Прикрепить файл"
                                />
                            </label>
                            <textarea
                                ref={textareaRef}
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                onKeyDown={handleKeyDown}
                                placeholder="Введите сообщение или подпись к файлу. Enter — отправить."
                                rows={2}
                                disabled={isSending}
                                className="flex-1 px-3 py-2 border border-border/60 rounded-lg text-sm resize-none bg-background focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:bg-muted min-h-[44px]"
                            />
                            <button
                                type="submit"
                                disabled={isSending || (!attachedFile && !inputValue.trim())}
                                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors"
                            >
                                {isSending ? (
                                    <span className="flex items-center gap-1">
                                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                        </svg>
                                    </span>
                                ) : (
                                    "Отправить"
                                )}
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {!canSend && (
                <div className="border-t border-border/60 p-3 bg-muted text-center text-sm text-muted-foreground">
                    Возьмите заявку, чтобы отвечать клиенту
                </div>
            )}
        </div>
    );
}
