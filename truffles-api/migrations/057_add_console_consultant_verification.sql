CREATE TABLE IF NOT EXISTS console_consultant_verification_sessions (
    id UUID PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id),
    branch_id UUID NULL REFERENCES branches(id),
    actor_agent_id UUID NOT NULL REFERENCES agents(id),
    actor_role TEXT NOT NULL,
    source_mode TEXT NOT NULL,
    challenge_mode TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    title TEXT NULL,
    remote_jid TEXT NOT NULL,
    runtime_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    latest_preview JSONB NOT NULL DEFAULT '{}'::jsonb,
    latest_outcome TEXT NULL,
    latest_business_verdict TEXT NULL,
    turns_total INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_console_consultant_verification_sessions_remote_jid
    ON console_consultant_verification_sessions (remote_jid);

CREATE INDEX IF NOT EXISTS ix_console_consultant_verification_sessions_client_id
    ON console_consultant_verification_sessions (client_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS ix_console_consultant_verification_sessions_branch_id
    ON console_consultant_verification_sessions (branch_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS console_consultant_verification_turns (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES console_consultant_verification_sessions(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    message_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    decision_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    decision_trace JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    preview JSONB NOT NULL DEFAULT '{}'::jsonb,
    outcome TEXT NULL,
    business_verdict TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_console_consultant_verification_turns_session_turn_index
    ON console_consultant_verification_turns (session_id, turn_index);

CREATE INDEX IF NOT EXISTS ix_console_consultant_verification_turns_session_id
    ON console_consultant_verification_turns (session_id, created_at ASC);
