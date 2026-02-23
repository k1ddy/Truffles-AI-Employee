ALTER TABLE tenants_fleet_cache
    ADD COLUMN IF NOT EXISTS scope_company_id UUID;

ALTER TABLE tenants_fleet_cache
    ADD COLUMN IF NOT EXISTS scope_client_id UUID;

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_cache_scope_company
    ON tenants_fleet_cache(cache_type, scope_company_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_cache_scope_client
    ON tenants_fleet_cache(cache_type, scope_client_id, updated_at DESC);
