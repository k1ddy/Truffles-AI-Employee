"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";
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

interface Booking {
    id: string;
    specialist_id: string;
    specialist_name: string;
    start_at: string;
    end_at: string;
    customer_name: string | null;
    customer_phone: string | null;
    service_type: string | null;
    status: string;
    created_at: string;
}

interface BookingCreateRequest {
    specialist_id: string;
    start_at: string;
    end_at: string;
    customer_name?: string;
    customer_phone?: string;
    service_type?: string;
    notes?: string;
    conversation_id?: string;
}

interface BookingStatusUpdateRequest {
    status: "COMPLETED" | "NO_SHOW";
    reason?: string;
}

interface BookingActionResponse {
    success: boolean;
    booking: Booking;
}

async function fetchSpecialists(): Promise<{ items: Specialist[] }> {
    const response = await api.get("/calendar/specialists");
    return response.data;
}

async function fetchSlots(specialistId: string, date: string, duration: number): Promise<{ slots: TimeSlot[] }> {
    const response = await api.get(`/calendar/slots?specialist_id=${specialistId}&date=${date}&duration=${duration}`);
    return response.data;
}

async function fetchBookings(date?: string): Promise<{ items: Booking[] }> {
    const params = date ? `?date_from=${date}&date_to=${date}` : "";
    const response = await api.get(`/calendar/bookings${params}`);
    return response.data;
}

async function createBooking(data: BookingCreateRequest): Promise<BookingActionResponse> {
    const response = await api.post("/calendar/bookings", data);
    return response.data;
}

async function updateBookingStatus(bookingId: string, data: BookingStatusUpdateRequest): Promise<BookingActionResponse> {
    const response = await api.post(`/calendar/bookings/${bookingId}/status`, data);
    return response.data;
}

function getVisitActionOptions(status: string): Array<{ status: BookingStatusUpdateRequest["status"]; label: string }> {
    const normalized = status.toUpperCase();
    if (["HOLD", "PENDING_CONFIRMATION", "CONFIRMED", "RESCHEDULE_REQUESTED", "CHECKED_IN"].includes(normalized)) {
        return [
            { status: "COMPLETED", label: "Пришел" },
            { status: "NO_SHOW", label: "Не пришел" },
        ];
    }
    return [];
}

function formatDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

export default function CalendarPage() {
    const { data: session } = useSession();
    const queryClient = useQueryClient();
    const today = formatDate(new Date());

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
        queryKey: ["bookings", selectedDate],
        queryFn: () => fetchBookings(selectedDate),
        enabled: !!session && canReadCalendar,
    });

    const bookings = bookingsData?.items ?? [];

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
                        Подберите слот, подтвердите услугу и создайте запись вручную при необходимости.
                    </p>
                    {!canWriteCalendar && (
                        <p className="mt-2 text-xs text-muted-foreground">
                            Read-only доступ: создание и отмена записей недоступны.
                        </p>
                    )}
                </div>
                <Link href="/" className="btn-ghost">
                    ← Назад к заявкам
                </Link>
            </div>

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

                        {bookingsLoading ? (
                            <div className="animate-pulse space-y-3">
                                {[...Array(3)].map((_, i) => (
                                    <div key={i} className="h-16 bg-muted/70 rounded"></div>
                                ))}
                            </div>
                        ) : bookings.length === 0 ? (
                            <p className="text-muted-foreground text-center py-4">
                                Нет записей на эту дату
                            </p>
                        ) : (
                            <div className="space-y-3">
                                {bookings.map((booking) => (
                                    <div
                                        key={booking.id}
                                        className="p-3 border border-border/60 rounded-lg hover:bg-muted/60"
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
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
