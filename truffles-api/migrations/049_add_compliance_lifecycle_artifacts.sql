-- Immutable compliance lifecycle evidence artifacts (external audit publication).

CREATE TABLE IF NOT EXISTS compliance_lifecycle_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL UNIQUE REFERENCES compliance_lifecycle_runs(id) ON DELETE CASCADE,
    scope TEXT NOT NULL,
    data_class TEXT NOT NULL,
    operation TEXT NOT NULL,
    run_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL DEFAULT 'compliance_lifecycle_evidence',
    artifact_digest TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    records_count INTEGER NOT NULL DEFAULT 0,
    evidence_record_count INTEGER NOT NULL DEFAULT 0,
    published_by UUID REFERENCES agents(id) ON DELETE SET NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_compliance_lifecycle_artifacts_scope
        CHECK (scope IN ('client', 'branch')),
    CONSTRAINT check_compliance_lifecycle_artifacts_operation
        CHECK (operation IN ('retention_scan', 'export_preview', 'destruction_preview')),
    CONSTRAINT check_compliance_lifecycle_artifacts_mode
        CHECK (run_mode IN ('preview', 'manual')),
    CONSTRAINT check_compliance_lifecycle_artifacts_status
        CHECK (status IN ('running', 'completed', 'failed')),
    CONSTRAINT check_compliance_lifecycle_artifacts_type
        CHECK (artifact_type = 'compliance_lifecycle_evidence'),
    CONSTRAINT check_compliance_lifecycle_artifacts_records_count
        CHECK (records_count >= 0),
    CONSTRAINT check_compliance_lifecycle_artifacts_evidence_count
        CHECK (evidence_record_count >= 0),
    CONSTRAINT check_compliance_lifecycle_artifacts_scope_target
        CHECK (
            (scope = 'client' AND branch_id IS NULL) OR
            (scope = 'branch' AND branch_id IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_compliance_lifecycle_artifacts_client_lookup
    ON compliance_lifecycle_artifacts(client_id, branch_id, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_compliance_lifecycle_artifacts_digest
    ON compliance_lifecycle_artifacts(artifact_digest);
