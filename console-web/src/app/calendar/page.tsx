"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { useSession } from "next-auth/react";
import Link from "next/link";
import toast from "react-hot-toast";

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

async function createBooking(data: any): Promise<any> {
    const response = await api.post("/calendar/bookings", data);
    return response.data;
}

function formatDate(date: Date): string {
    return date.toISOString().split("T")[0];
}

function getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
        pending: "ожидает",
        confirmed: "подтверждена",
        cancelled: "отменена",
        completed: "завершена",
        no_show: "не пришёл",
    };
    return labels[status] || status;
}

function getStatusColor(status: string): string {
    const colors: Record<string, string> = {
        pending: "bg-yellow-100 text-yellow-800",
        confirmed: "bg-green-100 text-green-800",
        cancelled: "bg-gray-100 text-gray-800",
        completed: "bg-blue-100 text-blue-800",
        no_show: "bg-red-100 text-red-800",
    };
    return colors[status] || "bg-gray-100 text-gray-800";
}

export default function CalendarPage() {
    const { data: session } = useSession();
    const queryClient = useQueryClient();

    // Form state
    const [selectedSpecialist, setSelectedSpecialist] = useState<string>("");
    const [selectedDate, setSelectedDate] = useState<string>(formatDate(new Date()));
    const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
    const [selectedService, setSelectedService] = useState<{ name: string; duration_min: number; price: number } | null>(null);
    const [customerName, setCustomerName] = useState("");
    const [customerPhone, setCustomerPhone] = useState("");
    const [notes, setNotes] = useState("");
    const [showForm, setShowForm] = useState(false);

    // Queries
    const { data: specialistsData, isLoading: specialistsLoading, isError: specialistsError, error: specialistsErrorData } = useQuery({
        queryKey: ["specialists"],
        queryFn: fetchSpecialists,
        enabled: !!session,
        retry: 1,
    });

    // Debug log for specialists loading
    useEffect(() => {
        if (specialistsError) {
            console.error("Specialists load error:", specialistsErrorData);
        }
        if (specialistsData) {
            console.log("Specialists loaded:", specialistsData);
        }
    }, [specialistsData, specialistsError, specialistsErrorData]);

    const specialists = specialistsData?.items ?? [];
    const currentSpecialist = specialists.find(s => s.id === selectedSpecialist);
    const duration = selectedService?.duration_min || 60;

    const { data: slotsData, isLoading: slotsLoading, refetch: refetchSlots } = useQuery({
        queryKey: ["slots", selectedSpecialist, selectedDate, duration],
        queryFn: () => fetchSlots(selectedSpecialist, selectedDate, duration),
        enabled: !!session && !!selectedSpecialist && !!selectedDate,
    });

    const slots = slotsData?.slots ?? [];

    const { data: bookingsData, isLoading: bookingsLoading } = useQuery({
        queryKey: ["bookings", selectedDate],
        queryFn: () => fetchBookings(selectedDate),
        enabled: !!session,
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
        onError: (error: any) => {
            const code = error?.response?.data?.error?.code;
            if (code === "BOOKING_CONFLICT") {
                toast.error("Это время уже занято. Выберите другой слот.");
            } else {
                toast.error("Не удалось создать запись");
            }
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
        if (!slot.available) return;
        setSelectedSlot(slot);
        setShowForm(true);
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedSlot || !selectedSpecialist) return;

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
            <div className="p-8 text-center text-gray-500">
                Войдите в систему для просмотра календаря.
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">Записи</h1>
                <Link href="/" className="text-blue-600 hover:underline">
                    ← Назад к заявкам
                </Link>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left: Filters & Slots */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Debug/Error info */}
                    {specialistsError && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
                            <h3 className="font-semibold mb-2">Ошибка загрузки мастеров</h3>
                            <pre className="text-xs overflow-auto">
                                {JSON.stringify(specialistsErrorData, null, 2)}
                            </pre>
                        </div>
                    )}

                    {/* Filters */}
                    <div className="bg-white border rounded-lg p-4 space-y-4">
                        <h2 className="font-semibold text-lg">Выберите мастера и дату</h2>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {/* Specialist */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Мастер
                                </label>
                                <select
                                    value={selectedSpecialist}
                                    onChange={(e) => {
                                        setSelectedSpecialist(e.target.value);
                                        setSelectedSlot(null);
                                        setSelectedService(null);
                                    }}
                                    className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Услуга
                                    </label>
                                    <select
                                        value={selectedService?.name || ""}
                                        onChange={(e) => {
                                            const service = currentSpecialist.services.find(s => s.name === e.target.value);
                                            setSelectedService(service || null);
                                            setSelectedSlot(null);
                                        }}
                                        className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Дата
                                </label>
                                <input
                                    type="date"
                                    value={selectedDate}
                                    onChange={(e) => {
                                        setSelectedDate(e.target.value);
                                        setSelectedSlot(null);
                                    }}
                                    min={formatDate(new Date())}
                                    className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Slots Grid */}
                    {selectedSpecialist && (
                        <div className="bg-white border rounded-lg p-4">
                            <h2 className="font-semibold text-lg mb-4">
                                Доступные слоты на {new Date(selectedDate).toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
                            </h2>

                            {slotsLoading ? (
                                <div className="animate-pulse grid grid-cols-4 md:grid-cols-6 gap-2">
                                    {[...Array(12)].map((_, i) => (
                                        <div key={i} className="h-12 bg-gray-200 rounded"></div>
                                    ))}
                                </div>
                            ) : slots.length === 0 ? (
                                <p className="text-gray-500 text-center py-8">
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
                                                        ? "bg-blue-600 text-white"
                                                        : "bg-green-50 text-green-800 hover:bg-green-100 border border-green-200"
                                                    : "bg-gray-100 text-gray-400 cursor-not-allowed"
                                                }
                                            `}
                                        >
                                            {slot.start_time}
                                        </button>
                                    ))}
                                </div>
                            )}

                            <div className="mt-4 flex gap-4 text-xs text-gray-500">
                                <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 bg-green-100 border border-green-200 rounded"></span>
                                    Свободно
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 bg-gray-100 rounded"></span>
                                    Занято
                                </span>
                                <span className="flex items-center gap-1">
                                    <span className="w-3 h-3 bg-blue-600 rounded"></span>
                                    Выбрано
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Booking Form */}
                    {showForm && selectedSlot && (
                        <div className="bg-white border rounded-lg p-4">
                            <h2 className="font-semibold text-lg mb-4">Данные клиента</h2>

                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div className="bg-blue-50 p-3 rounded-lg text-sm">
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
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Имя клиента
                                        </label>
                                        <input
                                            type="text"
                                            value={customerName}
                                            onChange={(e) => setCustomerName(e.target.value)}
                                            placeholder="Иван Иванов"
                                            className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Телефон
                                        </label>
                                        <input
                                            type="tel"
                                            value={customerPhone}
                                            onChange={(e) => setCustomerPhone(e.target.value)}
                                            placeholder="+7 777 123 4567"
                                            className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        Примечания
                                    </label>
                                    <textarea
                                        value={notes}
                                        onChange={(e) => setNotes(e.target.value)}
                                        placeholder="Дополнительная информация..."
                                        rows={2}
                                        className="w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>

                                <div className="flex gap-3">
                                    <button
                                        type="submit"
                                        disabled={createMutation.isPending}
                                        className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        {createMutation.isPending ? "Создаём..." : "Записать клиента"}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={resetForm}
                                        className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
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
                    <div className="bg-white border rounded-lg p-4">
                        <h2 className="font-semibold text-lg mb-4">
                            Записи на {new Date(selectedDate).toLocaleDateString("ru-RU", { day: "numeric", month: "short" })}
                        </h2>

                        {bookingsLoading ? (
                            <div className="animate-pulse space-y-3">
                                {[...Array(3)].map((_, i) => (
                                    <div key={i} className="h-16 bg-gray-200 rounded"></div>
                                ))}
                            </div>
                        ) : bookings.length === 0 ? (
                            <p className="text-gray-500 text-center py-4">
                                Нет записей на эту дату
                            </p>
                        ) : (
                            <div className="space-y-3">
                                {bookings.map((booking) => (
                                    <div
                                        key={booking.id}
                                        className="p-3 border rounded-lg hover:bg-gray-50"
                                    >
                                        <div className="flex justify-between items-start mb-1">
                                            <span className="font-medium text-sm">
                                                {new Date(booking.start_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                                {" - "}
                                                {new Date(booking.end_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                                            </span>
                                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(booking.status)}`}>
                                                {getStatusLabel(booking.status)}
                                            </span>
                                        </div>
                                        <div className="text-sm text-gray-600">
                                            {booking.specialist_name}
                                        </div>
                                        {booking.customer_name && (
                                            <div className="text-sm">
                                                {booking.customer_name}
                                                {booking.customer_phone && (
                                                    <span className="text-gray-500"> • {booking.customer_phone}</span>
                                                )}
                                            </div>
                                        )}
                                        {booking.service_type && (
                                            <div className="text-xs text-gray-500 mt-1">
                                                {booking.service_type}
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
