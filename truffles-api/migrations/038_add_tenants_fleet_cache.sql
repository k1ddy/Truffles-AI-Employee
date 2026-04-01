CREATE TABLE IF NOT EXISTS tenants_fleet_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_type TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenants_fleet_cache_scope UNIQUE (cache_type, scope_key)
);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_cache_expires_at
    ON tenants_fleet_cache(expires_at);

CREATE INDEX IF NOT EXISTS idx_tenants_fleet_cache_type_updated_at
    ON tenants_fleet_cache(cache_type, updated_at DESC);
