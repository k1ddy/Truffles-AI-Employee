CREATE TABLE IF NOT EXISTS marketing_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    created_by UUID REFERENCES agents(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    message_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    audience_mode TEXT NOT NULL DEFAULT 'branch_active_conversations',
    audience_filter JSONB NOT NULL DEFAULT '{}'::jsonb,
    preview_total INTEGER NOT NULL DEFAULT 0,
    last_preview_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_marketing_campaign_status
        CHECK (status IN ('draft', 'ready', 'executed', 'paused')),
    CONSTRAINT check_marketing_campaign_audience_mode
        CHECK (audience_mode IN ('branch_active_conversations'))
);

CREATE INDEX IF NOT EXISTS idx_marketing_campaigns_client_created
    ON marketing_campaigns(client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_marketing_campaigns_branch_created
    ON marketing_campaigns(branch_id, created_at DESC);

CREATE TABLE IF NOT EXISTS marketing_campaign_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    recipient_jid TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    outbox_id UUID REFERENCES outbox_messages(id) ON DELETE SET NULL,
    error_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_marketing_delivery_status
        CHECK (status IN ('queued', 'sent', 'failed', 'replied'))
);

CREATE INDEX IF NOT EXISTS idx_marketing_deliveries_campaign_created
    ON marketing_campaign_deliveries(campaign_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_marketing_deliveries_branch_status
    ON marketing_campaign_deliveries(branch_id, status, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_marketing_delivery_campaign_conversation
    ON marketing_campaign_deliveries(campaign_id, conversation_id)
    WHERE conversation_id IS NOT NULL;
