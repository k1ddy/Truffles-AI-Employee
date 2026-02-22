ALTER TABLE marketing_campaigns
    ADD COLUMN IF NOT EXISTS segment_code TEXT NOT NULL DEFAULT 'reactivation_30_120',
    ADD COLUMN IF NOT EXISTS preflight_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS preflight_valid BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES agents(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS requested_review_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS run_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS run_completed_at TIMESTAMPTZ;

ALTER TABLE marketing_campaigns
    DROP CONSTRAINT IF EXISTS check_marketing_campaign_status;

ALTER TABLE marketing_campaigns
    ADD CONSTRAINT check_marketing_campaign_status
    CHECK (
        status IN (
            'draft',
            'ready',
            'executed',
            'paused',
            'in_review',
            'approved',
            'scheduled',
            'running',
            'completed',
            'cancelled',
            'failed'
        )
    );

CREATE INDEX IF NOT EXISTS idx_marketing_campaigns_status_created
    ON marketing_campaigns(status, created_at DESC);

CREATE TABLE IF NOT EXISTS marketing_campaign_recipients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    recipient_jid TEXT NOT NULL,
    segment_code TEXT NOT NULL,
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    suppressed BOOLEAN NOT NULL DEFAULT FALSE,
    suppression_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_marketing_campaign_recipients_campaign_jid
    ON marketing_campaign_recipients(campaign_id, recipient_jid);

CREATE INDEX IF NOT EXISTS idx_marketing_campaign_recipients_campaign_suppressed
    ON marketing_campaign_recipients(campaign_id, suppressed, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_marketing_campaign_recipients_client_branch
    ON marketing_campaign_recipients(client_id, branch_id, created_at DESC);

CREATE TABLE IF NOT EXISTS marketing_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    recipient_jid TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'opt_in',
    source TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_marketing_consents_status CHECK (status IN ('opt_in', 'opt_out'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_marketing_consents_client_jid
    ON marketing_consents(client_id, recipient_jid);

CREATE INDEX IF NOT EXISTS idx_marketing_consents_active
    ON marketing_consents(client_id, active, changed_at DESC);

CREATE TABLE IF NOT EXISTS marketing_suppressions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    recipient_jid TEXT NOT NULL,
    reason TEXT NOT NULL,
    source TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_marketing_suppressions_lookup
    ON marketing_suppressions(client_id, recipient_jid, active, expires_at);

CREATE TABLE IF NOT EXISTS marketing_delivery_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    delivery_id UUID REFERENCES marketing_campaign_deliveries(id) ON DELETE SET NULL,
    outbox_id UUID REFERENCES outbox_messages(id) ON DELETE SET NULL,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    recipient_jid TEXT,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_marketing_delivery_events_campaign_created
    ON marketing_delivery_events(campaign_id, created_at DESC);
