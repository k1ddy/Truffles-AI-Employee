CREATE TABLE IF NOT EXISTS conversation_human_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    remote_jid TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'console',
    reason TEXT,
    locked_by_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    locked_by_name TEXT,
    lock_until TIMESTAMPTZ NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    released_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_conversation_human_locks_client_remote
    ON conversation_human_locks(client_id, remote_jid);

CREATE INDEX IF NOT EXISTS idx_conversation_human_locks_active_until
    ON conversation_human_locks(client_id, active, lock_until DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_human_locks_conversation
    ON conversation_human_locks(conversation_id, active, lock_until DESC)
    WHERE conversation_id IS NOT NULL;
