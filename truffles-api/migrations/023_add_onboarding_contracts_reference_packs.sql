CREATE TABLE IF NOT EXISTS reference_packs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'active',
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_reference_packs_status CHECK (status IN ('active', 'disabled'))
);

CREATE INDEX IF NOT EXISTS idx_reference_packs_domain_slug ON reference_packs(domain_slug);

CREATE TABLE IF NOT EXISTS client_onboarding_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    branch_id UUID REFERENCES branches(id) ON DELETE CASCADE,
    scope TEXT NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'active',
    payment_status TEXT NOT NULL DEFAULT 'pending',
    payment_confirmed_at TIMESTAMPTZ,
    payment_confirmed_by UUID REFERENCES agents(id),
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_client_onboarding_contracts_scope CHECK (scope IN ('client', 'branch')),
    CONSTRAINT check_client_onboarding_contracts_status CHECK (status IN ('active', 'disabled')),
    CONSTRAINT check_client_onboarding_contracts_payment_status CHECK (payment_status IN ('pending', 'confirmed', 'rejected')),
    CONSTRAINT check_client_onboarding_contracts_branch_scope CHECK (
        (scope = 'client' AND branch_id IS NULL) OR
        (scope = 'branch' AND branch_id IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_client_onboarding_contracts_client_id ON client_onboarding_contracts(client_id);
CREATE INDEX IF NOT EXISTS idx_client_onboarding_contracts_branch_id ON client_onboarding_contracts(branch_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_client_onboarding_contracts_unique_client
    ON client_onboarding_contracts(client_id)
    WHERE scope = 'client' AND branch_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_client_onboarding_contracts_unique_branch
    ON client_onboarding_contracts(client_id, branch_id)
    WHERE scope = 'branch' AND branch_id IS NOT NULL;
