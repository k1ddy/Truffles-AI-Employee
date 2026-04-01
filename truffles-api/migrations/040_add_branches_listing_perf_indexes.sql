-- Wave4 tenants branch-list performance indexes.
-- Supports /admin/branches hot path for company/client scopes and active lifecycle listing.

CREATE INDEX IF NOT EXISTS idx_branches_client_active_created_desc
    ON branches (client_id, is_active, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_branches_active_created_desc
    ON branches (is_active, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_clients_status_company_id
    ON clients (status, company_id, id);
