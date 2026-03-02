-- Compliance lifecycle run ledger and execution records (retention/export/destruction previews).

CREATE TABLE IF NOT EXISTS compliance_lifecycle_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope TEXT NOT NULL,
    data_class TEXT NOT NULL,
    operation TEXT NOT NULL,
    run_mode TEXT NOT NULL DEFAULT 'preview',
    status TEXT NOT NULL DEFAULT 'completed',
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    domain_key TEXT,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    policy_version_id UUID REFERENCES compliance_policy_versions(id) ON DELETE SET NULL,
    policy_scope TEXT,
    policy_schema_version TEXT,
    policy_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    triggered_by UUID REFERENCES agents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_compliance_lifecycle_runs_scope
        CHECK (scope IN ('client', 'branch')),
    CONSTRAINT check_compliance_lifecycle_runs_operation
        CHECK (operation IN ('retention_scan', 'export_preview', 'destruction_preview')),
    CONSTRAINT check_compliance_lifecycle_runs_mode
        CHECK (run_mode IN ('preview', 'manual')),
    CONSTRAINT check_compliance_lifecycle_runs_status
        CHECK (status IN ('running', 'completed', 'failed')),
    CONSTRAINT check_compliance_lifecycle_runs_data_class
        CHECK (data_class ~ '^[a-z][a-z0-9_.-]{1,63}$'),
    CONSTRAINT check_compliance_lifecycle_runs_scope_target
        CHECK (
            (scope = 'client' AND client_id IS NOT NULL AND branch_id IS NULL) OR
            (scope = 'branch' AND client_id IS NOT NULL AND branch_id IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_compliance_lifecycle_runs_lookup
    ON compliance_lifecycle_runs(client_id, branch_id, data_class, operation, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_compliance_lifecycle_runs_policy_version
    ON compliance_lifecycle_runs(policy_version_id);

CREATE TABLE IF NOT EXISTS compliance_lifecycle_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES compliance_lifecycle_runs(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    action TEXT NOT NULL,
    result TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_compliance_lifecycle_records_result
        CHECK (result IN ('candidate', 'skipped', 'error'))
);

CREATE INDEX IF NOT EXISTS idx_compliance_lifecycle_records_run_id
    ON compliance_lifecycle_records(run_id, occurred_at DESC);
