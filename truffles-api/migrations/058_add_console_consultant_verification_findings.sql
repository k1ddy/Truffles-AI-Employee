-- 058_add_console_consultant_verification_findings.sql
-- Owner/Admin consultant verification findings with failure-family clustering.

CREATE TABLE IF NOT EXISTS console_consultant_verification_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    actor_agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    actor_role TEXT NOT NULL,
    session_id UUID NOT NULL REFERENCES console_consultant_verification_sessions(id) ON DELETE CASCADE,
    owner_turn_id UUID REFERENCES console_consultant_verification_turns(id) ON DELETE SET NULL,
    assistant_turn_id UUID NOT NULL REFERENCES console_consultant_verification_turns(id) ON DELETE CASCADE,
    source_mode TEXT NOT NULL,
    challenge_mode TEXT NOT NULL,
    family_key TEXT NOT NULL,
    family_kind TEXT NOT NULL,
    family_label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    owner_prompt TEXT NOT NULL,
    assistant_excerpt TEXT NOT NULL,
    owner_note TEXT,
    resolution_note TEXT,
    outcome TEXT,
    business_verdict TEXT,
    decision_reason_code TEXT,
    source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    latest_preview JSONB NOT NULL DEFAULT '{}'::jsonb,
    linked_knowledge_backlog_id UUID,
    linked_learning_candidate_id UUID REFERENCES learned_responses(id) ON DELETE SET NULL,
    repeat_count INTEGER NOT NULL DEFAULT 1,
    first_captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS console_consultant_verification_findings_client_idx
    ON console_consultant_verification_findings (client_id, last_captured_at DESC);

CREATE INDEX IF NOT EXISTS console_consultant_verification_findings_status_idx
    ON console_consultant_verification_findings (client_id, status, last_captured_at DESC);

CREATE INDEX IF NOT EXISTS console_consultant_verification_findings_family_idx
    ON console_consultant_verification_findings (client_id, family_key);

CREATE INDEX IF NOT EXISTS console_consultant_verification_findings_session_idx
    ON console_consultant_verification_findings (session_id, last_captured_at DESC);
