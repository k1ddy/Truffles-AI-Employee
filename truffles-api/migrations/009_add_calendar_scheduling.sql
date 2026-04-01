-- Calendar scheduling core tables + pgcrypto tokens

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS timezone TEXT DEFAULT 'Asia/Almaty';
ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS working_hours JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS booking_settings JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE google_calendar_tokens
    ADD COLUMN IF NOT EXISTS access_token_enc BYTEA;
ALTER TABLE google_calendar_tokens
    ADD COLUMN IF NOT EXISTS refresh_token_enc BYTEA;
ALTER TABLE google_calendar_tokens
    ADD COLUMN IF NOT EXISTS encryption_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE google_calendar_tokens
    ADD COLUMN IF NOT EXISTS encrypted_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    duration_min INTEGER,
    price INTEGER,
    buffer_before_min INTEGER NOT NULL DEFAULT 0,
    buffer_after_min INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_services_client_id ON services(client_id);
CREATE INDEX IF NOT EXISTS idx_services_branch_id ON services(branch_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_services_unique_name ON services(client_id, branch_id, name);

CREATE TABLE IF NOT EXISTS specialist_services (
    specialist_id UUID NOT NULL REFERENCES specialists(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    duration_min INTEGER,
    price INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (specialist_id, service_id)
);

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    specialist_id UUID REFERENCES specialists(id),
    user_id UUID REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    status TEXT NOT NULL,
    source TEXT NOT NULL,
    confirmation_policy TEXT NOT NULL DEFAULT 'manager',
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    hold_expires_at TIMESTAMPTZ,
    customer_name TEXT,
    customer_phone TEXT,
    notes TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_appointments_time_order CHECK (start_at < end_at),
    CONSTRAINT check_appointments_status CHECK (status IN (
        'DRAFT',
        'HOLD',
        'PENDING_CONFIRMATION',
        'CONFIRMED',
        'CANCELLED',
        'RESCHEDULE_REQUESTED',
        'CHECKED_IN',
        'COMPLETED',
        'NO_SHOW'
    )),
    CONSTRAINT check_appointments_source CHECK (source IN (
        'bot',
        'console',
        'telegram',
        'google_import',
        'system'
    )),
    CONSTRAINT check_appointments_confirmation_policy CHECK (confirmation_policy IN (
        'manager',
        'client',
        'mixed'
    ))
);

CREATE INDEX IF NOT EXISTS idx_appointments_client_id ON appointments(client_id);
CREATE INDEX IF NOT EXISTS idx_appointments_branch_id ON appointments(branch_id);
CREATE INDEX IF NOT EXISTS idx_appointments_specialist_id ON appointments(specialist_id);
CREATE INDEX IF NOT EXISTS idx_appointments_start_at ON appointments(start_at);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);

ALTER TABLE appointments
    ADD CONSTRAINT appointments_no_overlap EXCLUDE USING gist (
        branch_id WITH =,
        specialist_id WITH =,
        tstzrange(start_at, end_at, '[)') WITH &&
    )
    WHERE (
        specialist_id IS NOT NULL
        AND status IN (
            'HOLD',
            'PENDING_CONFIRMATION',
            'CONFIRMED',
            'RESCHEDULE_REQUESTED',
            'CHECKED_IN'
        )
    );

CREATE TABLE IF NOT EXISTS appointment_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    service_id UUID REFERENCES services(id),
    service_name TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    price INTEGER,
    buffer_before_min INTEGER NOT NULL DEFAULT 0,
    buffer_after_min INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_appointment_services_appointment_id ON appointment_services(appointment_id);

CREATE TABLE IF NOT EXISTS appointment_sync_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    external_id TEXT,
    external_etag TEXT,
    state TEXT NOT NULL DEFAULT 'PENDING',
    last_synced_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT check_appointment_sync_state CHECK (state IN (
        'PENDING',
        'OK',
        'FAILED',
        'CONFLICT',
        'DISABLED'
    ))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_appointment_sync_unique ON appointment_sync_states(appointment_id, provider);

CREATE TABLE IF NOT EXISTS calendar_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    specialist_id UUID REFERENCES specialists(id),
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    provider TEXT,
    external_id TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT check_calendar_blocks_time_order CHECK (start_at < end_at),
    CONSTRAINT check_calendar_blocks_source CHECK (source IN (
        'google_import',
        'manual',
        'system'
    )),
    CONSTRAINT check_calendar_blocks_status CHECK (status IN (
        'ACTIVE',
        'CANCELLED'
    ))
);

CREATE INDEX IF NOT EXISTS idx_calendar_blocks_branch_id ON calendar_blocks(branch_id);
CREATE INDEX IF NOT EXISTS idx_calendar_blocks_specialist_id ON calendar_blocks(specialist_id);
CREATE INDEX IF NOT EXISTS idx_calendar_blocks_start_at ON calendar_blocks(start_at);

CREATE TABLE IF NOT EXISTS calendar_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    calendar_id TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT check_calendar_connections_status CHECK (status IN (
        'ACTIVE',
        'DISABLED',
        'FAILED',
        'PENDING'
    ))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_calendar_connections_unique ON calendar_connections(branch_id, provider);
CREATE INDEX IF NOT EXISTS idx_calendar_connections_client_id ON calendar_connections(client_id);

CREATE TABLE IF NOT EXISTS calendar_sync_cursors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES calendar_connections(id) ON DELETE CASCADE,
    cursor TEXT,
    channel_id TEXT,
    channel_expiration TIMESTAMPTZ,
    last_synced_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_calendar_sync_cursors_connection_id ON calendar_sync_cursors(connection_id);

CREATE TABLE IF NOT EXISTS reminder_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    template TEXT NOT NULL,
    run_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    next_attempt_at TIMESTAMPTZ,
    last_error TEXT,
    dedupe_key TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT check_reminder_jobs_status CHECK (status IN (
        'PENDING',
        'SENT',
        'FAILED'
    ))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_reminder_jobs_dedupe ON reminder_jobs(dedupe_key);
CREATE INDEX IF NOT EXISTS idx_reminder_jobs_run_at ON reminder_jobs(run_at);

CREATE TABLE IF NOT EXISTS visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    specialist_id UUID REFERENCES specialists(id),
    user_id UUID REFERENCES users(id),
    status TEXT NOT NULL,
    arrived_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT check_visits_status CHECK (status IN (
        'CHECKED_IN',
        'COMPLETED',
        'NO_SHOW'
    ))
);

CREATE INDEX IF NOT EXISTS idx_visits_branch_id ON visits(branch_id);
CREATE INDEX IF NOT EXISTS idx_visits_appointment_id ON visits(appointment_id);

CREATE TABLE IF NOT EXISTS appointment_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    actor_type TEXT NOT NULL,
    actor_id UUID,
    channel TEXT NOT NULL,
    action TEXT NOT NULL,
    prev_status TEXT,
    new_status TEXT,
    prev_version INTEGER,
    new_version INTEGER,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    trace_id TEXT,
    correlation_id TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT check_appointment_audit_actor_type CHECK (actor_type IN (
        'bot',
        'agent',
        'system',
        'google_sync'
    ))
);

CREATE INDEX IF NOT EXISTS idx_appointment_audit_appointment_id ON appointment_audit(appointment_id);
CREATE INDEX IF NOT EXISTS idx_appointment_audit_created_at ON appointment_audit(created_at);
