"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
    bookingNeedsAttention,
    fetchBookings,
    getBookingAttentionLabel,
    getVisitActionOptions,
    registerNoShowFollowUp,
    updateBookingStatus,
    type Booking,
} from "@/lib/calendar-bookings";
import { getBookingStatusColor, getBookingStatusLabel } from "@/utils/labels";

function formatTimeRange(startAt: string, endAt: string) {
    return `${new Date(startAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })} - ${new Date(endAt).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}`;
}

function formatDateLabel(startAt: string) {
    return new Date(startAt).toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "long",
    });
}

interface CaseBookingsPanelProps {
    caseId: string;
    conversationId?: string | null;
    canWriteCalendar?: boolean;
    fullCalendarHref: string;
}

export default function CaseBookingsPanel({
    caseId,
    conversationId,
    canWriteCalendar = false,
    fullCalendarHref,
}: CaseBookingsPanelProps) {
    const queryClient = useQueryClient();
    const queryKey = ["bookings", "case-panel", caseId, conversationId || ""] as const;

    const bookingsQuery = useQuery({
        queryKey: [...queryKey],
        queryFn: () =>
            fetchBookings({
                caseId,
                conversationId: conversationId || undefined,
                lane: "all",
            }),
        enabled: Boolean(caseId),
    });

    const statusMutation = useMutation({
        mutationFn: async (payload: { bookingId: string; status: "COMPLETED" | "NO_SHOW" }) =>
            updateBookingStatus(payload.bookingId, { status: payload.status }),
        onSuccess: (response) => {
            queryClient.invalidateQueries({ queryKey: ["bookings"] });
            toast.success(`Статус записи обновлен: ${getBookingStatusLabel(response.booking.status)}`);
        },
        onError: () => {
            toast.error("Не удалось обновить статус записи");
        },
    });

    const followUpMutation = useMutation({
        mutationFn: async (payload: { bookingId: string; result: "contacted" | "rebooked" }) =>
            registerNoShowFollowUp(payload.bookingId, { result: payload.result }),
        onSuccess: (response) => {
            queryClient.invalidateQueries({ queryKey: ["bookings"] });
            const label = response.booking.no_show_followup_result === "rebooked" ? "перезапись сохранена" : "контакт отмечен";
            toast.success(`После неявки: ${label}`);
        },
        onError: () => {
            toast.error("Не удалось сохранить результат после неявки");
        },
    });

    const bookings = bookingsQuery.data?.items ?? [];
    const attentionCount = bookings.filter((booking) => bookingNeedsAttention(booking)).length;

    return (
        <div className="card-surface p-4 flex flex-col gap-4" data-testid="case-bookings-panel">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Записи по заявке</p>
                    <h2 className="text-lg font-semibold">Связанные визиты</h2>
                    <p className="text-sm text-muted-foreground">
                        Держите контекст заявки и визитов на одном экране. Полный календарь открывайте только когда нужен общий обзор.
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full bg-muted px-2.5 py-1 font-semibold text-muted-foreground" data-testid="case-bookings-count">
                        Всего: {bookings.length}
                    </span>
                    <span className="rounded-full bg-amber-100 px-2.5 py-1 font-semibold text-amber-900" data-testid="case-bookings-attention">
                        Требуют внимания: {attentionCount}
                    </span>
                </div>
            </div>

            <div className="flex flex-wrap gap-2">
                <Link
                    href={fullCalendarHref}
                    className="rounded border border-border/60 px-3 py-2 text-xs font-semibold text-foreground hover:bg-background"
                    data-testid="case-bookings-open-full-calendar"
                >
                    Открыть полный календарь
                </Link>
            </div>

            {bookingsQuery.isLoading ? (
                <div className="space-y-3" data-testid="case-bookings-loading">
                    {[0, 1].map((item) => (
                        <div key={item} className="h-24 animate-pulse rounded-lg border border-border/60 bg-muted/50" />
                    ))}
                </div>
            ) : bookingsQuery.isError ? (
                <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4" data-testid="case-bookings-error">
                    <p className="text-sm font-semibold text-destructive">Не удалось загрузить записи по заявке</p>
                    <p className="mt-1 text-xs text-muted-foreground">Обновите блок или откройте полный календарь.</p>
                    <button
                        type="button"
                        onClick={() => bookingsQuery.refetch()}
                        className="mt-3 rounded border border-border/60 px-3 py-2 text-xs font-semibold text-foreground hover:bg-background"
                        data-testid="case-bookings-retry"
                    >
                        Повторить
                    </button>
                </div>
            ) : bookings.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border/60 p-4 text-sm text-muted-foreground" data-testid="case-bookings-empty">
                    По этой заявке пока нет связанных записей.
                </div>
            ) : (
                <div className="space-y-3">
                    {bookings.map((booking) => {
                        const attentionLabel = getBookingAttentionLabel(booking);
                        const statusPending = statusMutation.isPending && statusMutation.variables?.bookingId === booking.id;
                        const followUpPending = followUpMutation.isPending && followUpMutation.variables?.bookingId === booking.id;
                        return (
                            <BookingCard
                                key={booking.id}
                                booking={booking}
                                attentionLabel={attentionLabel}
                                canWriteCalendar={canWriteCalendar}
                                statusPending={statusPending}
                                followUpPending={followUpPending}
                                onUpdateStatus={(status) => statusMutation.mutate({ bookingId: booking.id, status })}
                                onCloseNoShow={(result) => followUpMutation.mutate({ bookingId: booking.id, result })}
                            />
                        );
                    })}
                </div>
            )}
        </div>
    );
}

function BookingCard({
    booking,
    attentionLabel,
    canWriteCalendar,
    statusPending,
    followUpPending,
    onUpdateStatus,
    onCloseNoShow,
}: {
    booking: Booking;
    attentionLabel: string | null;
    canWriteCalendar: boolean;
    statusPending: boolean;
    followUpPending: boolean;
    onUpdateStatus: (status: "COMPLETED" | "NO_SHOW") => void;
    onCloseNoShow: (result: "contacted" | "rebooked") => void;
}) {
    return (
        <div className="rounded-lg border border-border/60 p-3" data-testid="case-booking-card">
            <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                    <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">{formatDateLabel(booking.start_at)}</p>
                    <p className="text-sm font-semibold">{formatTimeRange(booking.start_at, booking.end_at)}</p>
                </div>
                <span className={`rounded px-2 py-0.5 text-xs font-medium ${getBookingStatusColor(booking.status)}`}>
                    {getBookingStatusLabel(booking.status)}
                </span>
            </div>
            <div className="mt-2 space-y-1 text-sm">
                <p className="text-foreground/90">{booking.specialist_name}</p>
                {booking.customer_name ? (
                    <p className="text-muted-foreground">
                        {booking.customer_name}
                        {booking.customer_phone ? ` • ${booking.customer_phone}` : ""}
                    </p>
                ) : null}
                {booking.service_type ? <p className="text-xs text-muted-foreground">{booking.service_type}</p> : null}
            </div>
            {attentionLabel ? (
                <div className="mt-2">
                    <span className="rounded bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-900">
                        {attentionLabel}
                    </span>
                </div>
            ) : null}
            {canWriteCalendar && getVisitActionOptions(booking.status).length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                    {getVisitActionOptions(booking.status).map((action) => (
                        <button
                            key={`${booking.id}-${action.status}`}
                            type="button"
                            onClick={() => onUpdateStatus(action.status)}
                            disabled={statusPending}
                            className="rounded border border-border/70 px-2.5 py-1.5 text-xs font-medium hover:bg-background disabled:opacity-50"
                        >
                            {statusPending ? "Обновляем..." : action.label}
                        </button>
                    ))}
                </div>
            ) : null}
            {canWriteCalendar && booking.status.toUpperCase() === "NO_SHOW" ? (
                <div className="mt-2 flex flex-wrap gap-2">
                    {booking.no_show_followup_done ? (
                        <>
                            <span className="rounded-md bg-green-100 px-2.5 py-1.5 text-xs font-medium text-green-800">
                                {booking.no_show_followup_result === "rebooked" ? "После неявки: перезаписан" : "После неявки: связались"}
                            </span>
                            {booking.no_show_followup_rebooked_appointment_id ? (
                                <span className="rounded-md bg-muted px-2.5 py-1.5 text-xs font-medium text-muted-foreground">
                                    Новая запись: {booking.no_show_followup_rebooked_appointment_id.slice(0, 8)}
                                </span>
                            ) : null}
                        </>
                    ) : (
                        <>
                            <button
                                type="button"
                                onClick={() => onCloseNoShow("contacted")}
                                disabled={followUpPending}
                                className="rounded-md border border-border/70 px-2.5 py-1.5 text-xs font-medium hover:bg-background disabled:opacity-50"
                            >
                                {followUpPending ? "Фиксируем..." : "Связались"}
                            </button>
                            <button
                                type="button"
                                onClick={() => onCloseNoShow("rebooked")}
                                disabled={followUpPending}
                                className="rounded-md border border-border/70 px-2.5 py-1.5 text-xs font-medium hover:bg-background disabled:opacity-50"
                            >
                                Перезаписали
                            </button>
                        </>
                    )}
                </div>
            ) : null}
        </div>
    );
}
