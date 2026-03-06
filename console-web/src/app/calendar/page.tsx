"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import toast from "react-hot-toast";
import {
    bookingNeedsAttention,
    createBooking,
    fetchBookings,
    getBookingAttentionLabel,
    getVisitActionOptions,
    registerNoShowFollowUp,
    type BookingQueueLane,
    type BookingStatusFilter,
    type BookingStatusUpdateRequest,
    updateBookingStatus,
} from "@/lib/calendar-bookings";
import { getBookingStatusLabel, getBookingStatusColor } from "@/utils/labels";
import AccessDenied from "@/components/AccessDenied";
import { authApi, canAccessConsole } from "@/lib/api-client";

interface Specialist {
    id: string;
    name: string;
    branch_id: string | null;
    branch_name: string | null;
    services: Array<{ name: string; duration_min: number; price: number }>;
    is_active: boolean;
}

interface TimeSlot {
    start: string;
    end: string;
    start_time: string;
    end_time: string;
    available: boolean;
}

async function fetchSpecialists(): Promise<{ items: Specialist[] }> {
    const response = await api.get("/calendar/specialists");
    return response.data;
}

async function fetchSlots(specialistId: string, date: string, duration: number): Promise<{ slots: TimeSlot[] }> {
    const response = await api.get(`/calendar/slots?specialist_id=${specialistId}&date=${date}&duration=${duration}`);
    return response.data;
}

function formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

export default function CalendarPage() {
    const { data: session } = useSession();
    const searchParams = useSearchParams();
    const queryClient = useQueryClient();
    const today = formatDate(new Date());
    const focusedConversationId = searchParams.get("conversation_id") || "";
    const focusedCaseId = searchParams.get("case_id") || "";

    const { data: meData } = useQuery({
        queryKey: ["console-me"],
        queryFn: async () => {
            const response = await authApi.getMe();
            return response.data;
        },
        enabled: !!session,
    });

    const role = meData?.agent?.role ?? "manager";
    const canReadCalendar = canAccessConsole(role, "calendar", "read");
    const canWriteCalendar = canAccessConsole(role, "calendar", "write");

    // Form state
    const [selectedSpecialist, setSelectedSpecialist] = useState<string>("");
    const [selectedDate, setSelectedDate] = useState<string>(today);
    const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
    const [selectedService, setSelectedService] = useState<{ name: string; duration_min: number; price: number } | null>(null);
    const [customerName, setCustomerName] = useState("");
    const [customerPhone, setCustomerPhone] = useState("");
    const [notes, setNotes] = useState("");
    const [showForm, setShowForm] = useState(false);
    const [showPastDates, setShowPastDates] = useState(false);
    const [statusUpdateBookingId, setStatusUpdateBookingId] = useState<string | null>(null);
    const [followUpBookingId, setFollowUpBookingId] = useState<string | null>(null);
    const [queueLane, setQueueLane] = useState<BookingQueueLane>(focusedConversationId ? "all" : "attention");
    const [queueStatusFilter, setQueueStatusFilter] = useState<BookingStatusFilter>("all");
    const [queueSearch, setQueueSearch] = useState("");

    // Queries
    const { data: specialistsData, isError: specialistsError, error: specialistsErrorData } = useQuery({
        queryKey: ["specialists"],
        queryFn: fetchSpecialists,
        enabled: !!session && canReadCalendar,
        retry: 1,
    });

    const specialists = specialistsData?.items ?? [];
    const currentSpecialist = specialists.find(s => s.id === selectedSpecialist);
    const duration = selectedService?.duration_min || 60;

    const { data: slotsData, isLoading: slotsLoading } = useQuery({
        queryKey: ["slots", selectedSpecialist, selectedDate, duration],
        queryFn: () => fetchSlots(selectedSpecialist, selectedDate, duration),
        enabled: !!session && canReadCalendar && !!selectedSpecialist && !!selectedDate,
    });

    const slots = slotsData?.slots ?? [];

    const { data: bookingsData, isLoading: bookingsLoading } = useQuery({
        queryKey: ["bookings", selectedDate, focusedConversationId, focusedCaseId, queueLane, queueStatusFilter],
        queryFn: () =>
            fetchBookings({
                date: selectedDate,
                conversationId: focusedConversationId || undefined,
                caseId: focusedCaseId || undefined,
                lane: queueLane,
                status: queueStatusFilter,
            }),
        enabled: !!session && canReadCalendar,
    });

    const bookings = useMemo(() => bookingsData?.items ?? [], [bookingsData?.items]);
    const bookingsSorted = useMemo(() => {
        return [...bookings].sort((left, right) => {
            const leftPriority = bookingNeedsAttention(left) ? 1 : 0;
            const rightPriority = bookingNeedsAttention(right) ? 1 : 0;
            if (leftPriority !== rightPriority) {
                return rightPriority - leftPriority;
            }
            return new Date(left.start_at).getTime() - new Date(right.start_at).getTime();
        });
    }, [bookings]);
    const attentionCount = bookingsSorted.filter((booking) => bookingNeedsAttention(booking)).length;
    const noShowAttentionCount = bookingsSorted.filter(
        (booking) => booking.status.toUpperCase() === "NO_SHOW" && !booking.no_show_followup_done
    ).length;
    const queueSearchNormalized = queueSearch.trim().toLowerCase();
    const bookingsVisible = useMemo(() => {
        return bookingsSorted.filter((booking) => {
            if (!queueSearchNormalized) {
                return true;
            }
            const haystack = [
                booking.customer_name || "",
                booking.customer_phone || "",
                booking.service_type || "",
                booking.specialist_name || "",
                booking.id || "",
            ]
                .join(" ")
                .toLowerCase();
            return haystack.includes(queueSearchNormalized);
        });
    }, [bookingsSorted, queueSearchNormalized]);

    // Create booking mutation
    const createMutation = useMutation({
        mutationFn: createBooking,
        onSuccess: () => {
            toast.success("Запись создана!");
            queryClient.invalidateQueries({ queryKey: ["slots"] });
            queryClient.invalidateQueries({ queryKey: ["bookings"] });
            resetForm();
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "BOOKING_CONFLICT") {
                toast.error("Это время уже занято. Выберите другой слот.");
            } else {
                toast.error("Не удалось создать запись");
            }
        },
    });

    const statusMutation = useMutation({
        mutationFn: async (payload: { bookingId: string; status: BookingStatusUpdateRequest["status"] }) => {
            setStatusUpdateBookingId(payload.bookingId);
            return updateBookingStatus(payload.bookingId, { status: payload.status });
        },
        onSuccess: (_data, variables) => {
            const labels: Record<BookingStatusUpdateRequest["status"], string> = {
                COMPLETED: "Статус: клиент пришел",
                NO_SHOW: "Статус: клиент не пришел",
            };
            toast.success(labels[variables.status]);
            queryClient.invalidateQueries({ queryKey: ["bookings"] });
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "BOOKING_STATUS_TRANSITION_DENIED") {
                toast.error("Недопустимый переход статуса для этой записи");
            } else if (code === "INVALID_STATUS") {
                toast.error("Некорректный статус визита");
            } else {
                toast.error("Не удалось обновить статус визита");
            }
        },
        onSettled: () => {
            setStatusUpdateBookingId(null);
        },
    });

    const followUpMutation = useMutation({
        mutationFn: async (payload: {
            bookingId: string;
            result: "contacted" | "rebooked";
            rebookedAppointmentId?: string;
        }) => {
            setFollowUpBookingId(payload.bookingId);
            return registerNoShowFollowUp(payload.bookingId, {
                result: payload.result,
                rebooked_appointment_id: payload.rebookedAppointmentId,
            });
        },
        onSuccess: (_data, variables) => {
            if (variables.result === "rebooked") {
                toast.success("Follow-up закрыт: клиент перезаписан");
            } else {
                toast.success("Follow-up закрыт: с клиентом связались");
            }
            queryClient.invalidateQueries({ queryKey: ["bookings"] });
        },
        onError: (error: unknown) => {
            const code = (error as { response?: { data?: { error?: { code?: string } } } })?.response?.data?.error?.code;
            if (code === "BOOKING_STATUS_REQUIRED") {
                toast.error("Follow-up доступен только для статуса 'Не пришел'");
            } else {
                toast.error("Не удалось зафиксировать follow-up");
            }
        },
        onSettled: () => {
            setFollowUpBookingId(null);
        },
    });

    const resetForm = () => {
        setSelectedSlot(null);
        setCustomerName("");
        setCustomerPhone("");
        setNotes("");
        setShowForm(false);
    };

    const handleSlotClick = (slot: TimeSlot) => {
        if (!slot.available || !canWriteCalendar) return;
        setSelectedSlot(slot);
        setShowForm(true);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedSlot || !selectedSpecialist || !canWriteCalendar) return;

        const startAt = new Date(selectedSlot.start);
        const endAt = new Date(selectedSlot.end);

        createMutation.mutate({
            specialist_id: selectedSpecialist,
            start_at: startAt.toISOString(),
            end_at: endAt.toISOString(),
            customer_name: customerName || undefined,
            customer_phone: customerPhone || undefined,
            service_type: selectedService?.name || undefined,
            notes: notes || undefined,
            conversation_id: focusedConversationId || undefined,
            case_id: focusedCaseId || undefined,
        });
    };

    if (!session) {
        return (
            <div className="p-8 text-center text-muted-foreground">
                Войдите в систему для просмотра календаря.
            </div>
        );
    }

    if (!canReadCalendar) {
        return (
            <AccessDenied message="Эта роль не имеет доступа к календарю." />
        );
    }

    return (
        <div className="space-y-6" data-testid="calendar-page">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <div className="badge mb-3">Calendar</div>
                    <h1 className="text-2xl font-semibold">Записи</h1>
                    <p className="mt-2 text-sm text-muted-foreground">
                        Управляйте очередью визитов, подтверждайте статусы и возвращайтесь к нужной заявке без потери контекста.
                    </p>
                    {!canWriteCalendar && (
                        <p className="mt-2 text-xs text-muted-foreground">
                            Read-only доступ: создание и отмена записей недоступны.
                        </p>
                    )}
                </div>
                <Link
                    href={focusedCaseId ? `/cases/${encodeURIComponent(focusedCaseId)}` : "/"}
                    className="btn-ghost"
                    data-testid="calendar-back-to-cases"
                >
                    ← {focusedCaseId ? "Вернуться в заявку" : "Назад к заявкам"}
                </Link>
            </div>

            {focusedConversationId && (
                <div
                    className="card-surface border border-primary/30 bg-primary/5 p-4"
                    data-testid="calendar-case-context-banner"
                >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <p className="text-sm font-semibold">Режим по заявке включен</p>
                            <p className="text-xs text-muted-foreground">
                                Показываются записи, связанные с выбранной заявкой.
                            </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {focusedCaseId && (
                                <Link
                                    href={`/cases/${encodeURIComponent(focusedCaseId)}`}
                                    className="rounded border border-border/60 px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-background"
                                    data-testid="calendar-open-linked-case"
                                >
                                    Открыть заявку
                                </Link>
                            )}
                            <Link
                                href="/calendar"
                                className="rounded border border-border/60 px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground hover:bg-background"
                                data-testid="calendar-clear-case-context"
                            >
                                Показать все записи
                            </Link>
                        </div>
                    </div>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left: Filters & Slots */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Debug/Error info */}
                    {specialistsError && (
                        <div className="card-surface p-4 text-destructive">
                            <h3 className="font-semibold mb-1">Не удалось загрузить список мастеров</h3>
                            <p className="text-sm text-muted-foreground">
                                Проверьте соединение и попробуйте обновить страницу.
                            </p>
                            <details className="mt-2 text-xs text-muted-foreground">
                                <summary className="cursor-pointer">Технические детали</summary>
                                <pre className="mt-2 overflow-auto whitespace-pre-wrap">
                                    {JSON.stringify(specialistsErrorData, null, 2)}
                                </pre>
                            </details>
                        </div>
                    )}

                    {/* Filters */}
                    <div className="card-surface p-4 space-y-4">
                        <h2 className="font-semibold text-lg">Выберите мастера и дату</h2>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Specialist */}
                            <div>
                                <label className="block text-sm font-medium text-muted-foreground mb-1">
                                    Мастер
                                </label>
                                <select
                                    value={selectedSpecialist}
                                    onChange={(e) => {
                                        setSelectedSpecialist(e.target.value);
                                        setSelectedSlot(null);
                                        setSelectedService(null);
                                    }}
                                    className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                >
                                    <option value="">Выберите мастера</option>
                                    {specialists.map((s) => (
                                        <option key={s.id} value={s.id}>
                                            {s.name} {s.branch_name ? `(${s.branch_name})` : ""}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Service */}
                            {currentSpecialist && currentSpecialist.services.length > 0 && (
                                <div>
                                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                                        Услуга
                                    </label>
                                    <select
                                        value={selectedService?.name || ""}
                                        onChange={(e) => {
                                            const service = currentSpecialist.services.find(s => s.name === e.target.value);
                                            setSelectedService(service || null);
                                            setSelectedSlot(null);
                                        }}
                                        className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    >
                                        <option value="">Любая услуга</option>
                                        {currentSpecialist.services.map((s, i) => (
                                            <option key={i} value={s.name}>
                                                {s.name} ({s.duration_min} мин, {s.price}₸)
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            )}

                            {/* Date */}
                            <div>
                                <label
                                    className="block text-sm font-medium text-muted-foreground mb-1"
                                    htmlFor="calendar-date"
                                >
                                    Дата
                                </label>
                                <input
                                    id="calendar-date"
                                    type="date"
                                    value={selectedDate}
                                    onChange={(e) => {
                                        setSelectedDate(e.target.value);
                                        setSelectedSlot(null);
                                    }}
                                    min={showPastDates ? undefined : today}
                                    className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                />
                                <label className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                                    <input
                                        type="checkbox"
                                        checked={showPastDates}
                                        onChange={(event) => {
                                            const enabled = event.target.checked;
                                            setShowPastDates(enabled);
                                            if (!enabled && selectedDate < today) {
                                                setSelectedDate(today);
                                                setSelectedSlot(null);
                                            }
                                        }}
                                        className="w-4 h-4 rounded border-border/60 text-primary focus:ring-primary/40"
                                        data-testid="calendar-show-past-dates"
                                    />
                                    Показывать прошлые даты
                                </label>
                            </div>
                        </div>
                    </div>

                    {/* Slots Grid */}
                    {selectedSpecialist && (
                        <div className="card-surface p-4">
                            <h2 className="font-semibold text-lg mb-4">
                                Доступные слоты на {new Date(selectedDate).toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
                            </h2>

                            {slotsLoading ? (
                                <div className="animate-pulse grid grid-cols-4 md:grid-cols-6 gap-2">
                                    {[...Array(12)].map((_, i) => (
                                        <div key={i} className="h-12 bg-muted/70 rounded"></div>
                                    ))}
                                </div>
                            ) : slots.length === 0 ? (
                                <p className="text-muted-foreground text-center py-8">
                                    Нет доступных слотов на выбранную дату. Возможно, это выходной день.
                                </p>
                            ) : (
                                <div className="grid grid-cols-4 md:grid-cols-6 gap-2">
                                    {slots.map((slot, i) => (
                                        <button
                                            key={i}
                                            onClick={() => handleSlotClick(slot)}
                                            disabled={!slot.available}
                                            className={`
                                                py-3 px-2 rounded-lg text-sm font-medium transition-colors
                                                ${slot.available
                                                    ? selectedSlot?.start === slot.start
                                                        ? "bg-primary text-primary-foreground"
                                                        : "bg-green-50 text-green-800 hover:bg-green-100 border border-green-200"
                                                    : "bg-muted text-muted-foreground cursor-not-allowed"
                                                }
                                            `}
                                        >
                                            {slot.start_time}
                                        </button>
                                    ))}
                                </div>
                            )}

                            <div className="mt-4 flex gap-4 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 bg-green-100 border border-green-200 rounded"></span>
                                    Свободно
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 bg-muted rounded"></span>
                                    Занято
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 bg-primary rounded"></span>
                                    Выбрано
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Booking Form */}
                    {showForm && selectedSlot && (
                        <div className="card-surface p-4">
                            <h2 className="font-semibold text-lg mb-4">Данные клиента</h2>

                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div className="bg-muted p-3 rounded-lg text-sm">
                                    <strong>Мастер:</strong> {currentSpecialist?.name}<br />
                                    <strong>Время:</strong> {selectedSlot.start_time} - {selectedSlot.end_time}<br />
                                    {selectedService && (
                                        <>
                                            <strong>Услуга:</strong> {selectedService.name} ({selectedService.price}₸)
                                        </>
                                    )}
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-muted-foreground mb-1">
                                            Имя клиента
                                        </label>
                                        <input
                                            type="text"
                                            value={customerName}
                                            onChange={(e) => setCustomerName(e.target.value)}
                                            placeholder="Иван Иванов"
                                            className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-muted-foreground mb-1">
                                            Телефон
                                        </label>
                                        <input
                                            type="tel"
                                            value={customerPhone}
                                            onChange={(e) => setCustomerPhone(e.target.value)}
                                            placeholder="+7 777 123 4567"
                                            className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-muted-foreground mb-1">
                                        Примечания
                                    </label>
                                    <textarea
                                        value={notes}
                                        onChange={(e) => setNotes(e.target.value)}
                                        placeholder="Дополнительная информация..."
                                        rows={2}
                                        className="w-full px-3 py-2 border border-border/60 rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    />
                                </div>

                                <div className="flex gap-3">
                                    <button
                                        type="submit"
                                        disabled={createMutation.isPending}
                                        className="btn-primary disabled:opacity-50"
                                    >
                                        {createMutation.isPending ? "Создаём..." : "Записать клиента"}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={resetForm}
                                        className="btn-ghost"
                                    >
                                        Отмена
                                    </button>
                                </div>
                            </form>
                        </div>
                    )}
                </div>

                {/* Right: Today's Bookings */}
                <div className="space-y-6">
                    <div className="card-surface p-4">
                        <h2 className="font-semibold text-lg mb-4">
                            Записи на {new Date(selectedDate).toLocaleDateString("ru-RU", { day: "numeric", month: "short" })}
                        </h2>
                        <div className="mb-3 flex flex-wrap gap-2 text-xs">
                            <span className="rounded bg-muted px-2.5 py-1 text-muted-foreground">
                                Всего: <span className="font-semibold text-foreground">{bookingsSorted.length}</span>
                            </span>
                            <span className="rounded bg-amber-100 px-2.5 py-1 text-amber-900">
                                Требуют внимания: <span className="font-semibold">{attentionCount}</span>
                            </span>
                            <span className="rounded bg-red-100 px-2.5 py-1 text-red-900">
                                Неявки без связи: <span className="font-semibold">{noShowAttentionCount}</span>
                            </span>
                            {bookingsData?.has_more && (
                                <span className="rounded bg-primary/10 px-2.5 py-1 text-primary">
                                    Показаны первые {bookingsSorted.length}
                                </span>
                            )}
                        </div>
                        <div className="mb-4 space-y-2" data-testid="calendar-queue-controls">
                            <div className="flex flex-wrap items-center gap-2">
                                <button
                                    type="button"
                                    onClick={() => setQueueLane("attention")}
                                    className={`rounded border px-2.5 py-1 text-xs font-semibold ${
                                        queueLane === "attention"
                                            ? "border-amber-300 bg-amber-100 text-amber-900"
                                            : "border-border/60 text-muted-foreground hover:text-foreground"
                                    }`}
                                    data-testid="calendar-queue-lane-attention"
                                >
                                    Только действия
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setQueueLane("all")}
                                    className={`rounded border px-2.5 py-1 text-xs font-semibold ${
                                        queueLane === "all"
                                            ? "border-primary/40 bg-primary/10 text-primary"
                                            : "border-border/60 text-muted-foreground hover:text-foreground"
                                    }`}
                                    data-testid="calendar-queue-lane-all"
                                >
                                    Все записи
                                </button>
                            </div>
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto]">
                                <input
                                    type="text"
                                    value={queueSearch}
                                    onChange={(event) => setQueueSearch(event.target.value)}
                                    placeholder="Поиск по клиенту, телефону, услуге или ID записи"
                                    className="w-full rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    data-testid="calendar-queue-search"
                                />
                                <select
                                    value={queueStatusFilter}
                                    onChange={(event) => setQueueStatusFilter(event.target.value as BookingStatusFilter)}
                                    className="rounded border border-border/60 bg-background px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-primary/40"
                                    data-testid="calendar-queue-status-filter"
                                >
                                    <option value="all">Все статусы</option>
                                    <option value="scheduled">Запланированные</option>
                                    <option value="completed">Пришёл</option>
                                    <option value="no_show">Не пришёл</option>
                                    <option value="cancelled">Отменённые</option>
                                </select>
                            </div>
                        </div>

                        {bookingsLoading ? (
                            <div className="animate-pulse space-y-3">
                                {[...Array(3)].map((_, i) => (
                                    <div key={i} className="h-16 bg-muted/70 rounded"></div>
                                ))}
                            </div>
                        ) : bookingsVisible.length === 0 ? (
                            <p className="text-muted-foreground text-center py-4">
                                {focusedConversationId
                                    ? "По этой заявке нет записей под выбранные фильтры"
                                    : "Нет записей под выбранные фильтры"}
                            </p>
                        ) : (
                            <div className="space-y-3">
                                {bookingsVisible.map((booking) => {
                                    const attentionLabel = getBookingAttentionLabel(booking);
                                    return (
                                        <div
                                            key={booking.id}
                                            className="p-3 border border-border/60 rounded-lg hover:bg-muted/60"
                                            data-testid="calendar-booking-card"
                                        >
                                        <div className="flex justify-between items-start mb-1">
                                            <span className="font-medium text-sm">
                                                {new Date(booking.start_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                                {" - "}
                                                {new Date(booking.end_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                            </span>
                                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getBookingStatusColor(booking.status)}`}>
                                                {getBookingStatusLabel(booking.status)}
                                            </span>
                                        </div>
                                        <div className="text-sm text-muted-foreground">
                                            {booking.specialist_name}
                                        </div>
                                        {booking.customer_name && (
                                            <div className="text-sm">
                                                {booking.customer_name}
                                                {booking.customer_phone && (
                                                    <span className="text-muted-foreground"> • {booking.customer_phone}</span>
                                                )}
                                            </div>
                                        )}
                                        {booking.service_type && (
                                            <div className="text-xs text-muted-foreground mt-1">
                                                {booking.service_type}
                                            </div>
                                        )}
                                        {attentionLabel && (
                                            <div className="mt-2">
                                                <span className="rounded bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                                                    {attentionLabel}
                                                </span>
                                            </div>
                                        )}
                                        {booking.case_id && (
                                            <div className="mt-2 flex items-center gap-2">
                                                <Link
                                                    href={`/cases/${encodeURIComponent(booking.case_id)}`}
                                                    className="rounded border border-border/60 px-2.5 py-1 text-xs font-semibold text-foreground hover:bg-background"
                                                    data-testid="calendar-booking-open-case"
                                                >
                                                    Открыть чат заявки
                                                </Link>
                                                {focusedCaseId && booking.case_id === focusedCaseId && (
                                                    <span className="rounded bg-primary/10 px-2 py-0.5 text-[11px] font-semibold text-primary">
                                                        Текущая заявка
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                        {canWriteCalendar && getVisitActionOptions(booking.status).length > 0 && (
                                            <div className="mt-3 flex flex-wrap gap-2">
                                                {getVisitActionOptions(booking.status).map((action) => {
                                                    const isPending = statusMutation.isPending && statusUpdateBookingId === booking.id;
                                                    return (
                                                        <button
                                                            key={`${booking.id}-${action.status}`}
                                                            type="button"
                                                            onClick={() => statusMutation.mutate({ bookingId: booking.id, status: action.status })}
                                                            disabled={isPending}
                                                            className="px-2.5 py-1.5 rounded-md border border-border/70 text-xs font-medium hover:bg-background disabled:opacity-50"
                                                        >
                                                            {isPending ? "Обновляем..." : action.label}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        )}
                                        {canWriteCalendar && booking.status.toUpperCase() === "NO_SHOW" && (
                                            <div className="mt-2 flex flex-wrap gap-2">
                                                {booking.no_show_followup_done ? (
                                                    <>
                                                        <span className="px-2.5 py-1.5 rounded-md bg-green-100 text-green-800 text-xs font-medium">
                                                            {booking.no_show_followup_result === "rebooked"
                                                                ? "После неявки: перезаписан"
                                                                : "После неявки: связались"}
                                                        </span>
                                                        {booking.no_show_followup_rebooked_appointment_id && (
                                                            <span className="px-2.5 py-1.5 rounded-md bg-muted text-muted-foreground text-xs font-medium">
                                                                Новая запись: {booking.no_show_followup_rebooked_appointment_id.slice(0, 8)}
                                                            </span>
                                                        )}
                                                    </>
                                                ) : (
                                                    <>
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                followUpMutation.mutate({
                                                                    bookingId: booking.id,
                                                                    result: "contacted",
                                                                })
                                                            }
                                                            disabled={followUpMutation.isPending && followUpBookingId === booking.id}
                                                            className="px-2.5 py-1.5 rounded-md border border-border/70 text-xs font-medium hover:bg-background disabled:opacity-50"
                                                        >
                                                            {followUpMutation.isPending && followUpBookingId === booking.id
                                                                ? "Фиксируем..."
                                                                : "Связались"}
                                                        </button>
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                followUpMutation.mutate({
                                                                    bookingId: booking.id,
                                                                    result: "rebooked",
                                                                })
                                                            }
                                                            disabled={followUpMutation.isPending && followUpBookingId === booking.id}
                                                            className="px-2.5 py-1.5 rounded-md border border-border/70 text-xs font-medium hover:bg-background disabled:opacity-50"
                                                        >
                                                            Перезаписали
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        )}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
