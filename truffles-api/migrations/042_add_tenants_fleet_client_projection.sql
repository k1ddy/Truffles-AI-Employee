-- Materialized projection for fleet client states used by tenants read paths.
-- Keeps per-client derived lifecycle/payment/service state and branch counters.

CREATE TABLE IF NOT EXISTS tenants_fleet_client_projection (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL UNIQUE,
    company_id UUID NULL,
    lifecycle_state TEXT NOT NULL,
    payment_status TEXT NOT NULL,
    commercial_state TEXT NOT NULL,
    service_state TEXT NOT NULL,
    owner_name TEXT NULL,
    next_action TEXT NOT NULL,
    total_branches INTEGER NOT NULL DEFAULT 0,
    active_branches INTEGER NOT NULL DEFAULT 0,
    degraded_branches INTEGER NOT NULL DEFAULT 0,
    go_live_ready_branches INTEGER NOT NULL DEFAULT 0,
    reference_branch_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    reference_branch_reason TEXT NOT NULL DEFAULT 'no_active_branches',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_client_projection_company
    ON tenants_fleet_client_projection(company_id);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_client_projection_lifecycle
    ON tenants_fleet_client_projection(lifecycle_state);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_client_projection_payment
    ON tenants_fleet_client_projection(payment_status);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_client_projection_service
    ON tenants_fleet_client_projection(service_state);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_client_projection_refreshed_at
    ON tenants_fleet_client_projection(refreshed_at);
