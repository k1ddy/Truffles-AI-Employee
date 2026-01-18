export interface DecisionTraceEntry {
    stage: string;
    decision?: string;
    recorded_at?: string;
    meta?: Record<string, unknown>;
    [key: string]: unknown;
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
    assigned_to_name: string | null;
    channel: string;
    sla_status?: string;
    // Customer info
    customer_name?: string | null;
    customer_phone?: string | null;
    customer_remote_jid?: string | null;
}

export interface Message {
    id: string;
    role: string;
    content: string;
    created_at: string;
    metadata?: any;
}

