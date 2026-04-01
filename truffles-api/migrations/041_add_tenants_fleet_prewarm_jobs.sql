-- Durable queue for tenants fleet prewarm dispatch.
-- Stores incremental prewarm tasks so scheduling survives process restarts.

CREATE TABLE IF NOT EXISTS tenants_fleet_prewarm_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    global_required BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NULL,
    locked_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_prewarm_jobs_status_created_at
    ON tenants_fleet_prewarm_jobs(status, created_at);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_prewarm_jobs_status_locked_at
    ON tenants_fleet_prewarm_jobs(status, locked_at);
