CREATE TABLE IF NOT EXISTS console_ops_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE SET NULL,
    actor_agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE RESTRICT,
    job_type TEXT NOT NULL,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_payload JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    CONSTRAINT check_console_ops_jobs_mode CHECK (mode IN ('dry_run', 'execute')),
    CONSTRAINT check_console_ops_jobs_status CHECK (status IN ('success', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_console_ops_jobs_client_created
    ON console_ops_jobs(client_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_console_ops_jobs_type_created
    ON console_ops_jobs(job_type, created_at DESC);
