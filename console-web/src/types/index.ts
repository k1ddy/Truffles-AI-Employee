export interface DecisionTraceEntry {
    stage: string;
    decision?: string;
    recorded_at?: string;
    meta?: Record<string, unknown>;
    [key: string]: unknown;
}

export interface TelegramTrail {
    message_id?: number | null;
    topic_id?: number | null;
    chat_id?: string | null;
    telegram_link?: string | null;
    telegram_desktop_link?: string | null;
    delivery_status?: string | null;  // sent, failed, pending
    delivered_at?: string | null;
}

export interface Case {
    id: string;
    conversation_id: string;
    branch_id?: string;
    status: string;
    trigger_type: string;
    trigger_value?: string;
    context_summary?: string;
    decision_trace?: DecisionTraceEntry[];
    user_message: string | null;
    created_at: string;
    assigned_to_id?: string | null;
    assigned_to_name: string | null;
    first_response_at?: string | null;
    resolved_at?: string | null;
    resolution_time_seconds?: number | null;
    channel: string;
    sla_status?: string;
    sla_action_state?: string | null;
    sla_overdue_minutes?: number | null;
    priority_tier?: "low" | "normal" | "high" | "urgent" | string;
    attention_reason?: string | null;
    target_response_at?: string | null;
    // Customer info
    customer_name?: string | null;
    customer_phone?: string | null;
    customer_remote_jid?: string | null;
    // Telegram trail (TG-01)
    telegram_trail?: TelegramTrail | null;
    // Inbox health
    last_inbound_at?: string | null;
    last_outbound_at?: string | null;
    last_activity_at?: string | null;
    last_activity_channel?: string | null;
    last_message_preview?: string | null;
    needs_reply?: boolean | null;
    has_delivery_error?: boolean | null;
    has_pending_outbox?: boolean | null;
    human_lock_active?: boolean | null;
    human_lock_until?: string | null;
    human_lock_remaining_seconds?: number | null;
    human_lock_source?: string | null;
    human_lock_reason?: string | null;
    human_lock_by?: string | null;
    snoozed_until?: string | null;
    snoozed_reason?: string | null;
    snoozed_by?: string | null;
}

export interface Message {
    id: string;
    role: string;
    content: string;
    created_at: string;
    metadata?: Record<string, unknown> | null;
}
