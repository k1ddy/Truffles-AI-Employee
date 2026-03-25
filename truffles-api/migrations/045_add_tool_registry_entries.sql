-- Tool registry certification catalog.
-- Enables platform-admin governance for tool certification/health/scope rules.

CREATE TABLE IF NOT EXISTS tool_registry_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_action TEXT NOT NULL UNIQUE,
    tool_group TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    schema_version TEXT NOT NULL DEFAULT 'v1',
    status TEXT NOT NULL DEFAULT 'active',
    certification_status TEXT NOT NULL DEFAULT 'certified',
    health_status TEXT NOT NULL DEFAULT 'healthy',
    allowed_scopes_json JSONB NOT NULL DEFAULT '["client","branch"]'::jsonb,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES agents(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT check_tool_registry_entries_status
        CHECK (status IN ('active', 'disabled')),
    CONSTRAINT check_tool_registry_entries_certification
        CHECK (certification_status IN ('certified', 'uncertified')),
    CONSTRAINT check_tool_registry_entries_health
        CHECK (health_status IN ('healthy', 'degraded', 'down'))
);

CREATE INDEX IF NOT EXISTS idx_tool_registry_entries_status
    ON tool_registry_entries(status);

CREATE INDEX IF NOT EXISTS idx_tool_registry_entries_certification
    ON tool_registry_entries(certification_status);

INSERT INTO tool_registry_entries (
    tool_action,
    tool_group,
    title,
    summary,
    schema_version,
    status,
    certification_status,
    health_status,
    allowed_scopes_json,
    metadata_json
)
VALUES
    (
        'calendar.list_slots',
        'calendar',
        'List Slots',
        'Lookup available booking slots',
        'v1',
        'active',
        'certified',
        'healthy',
        '["client","branch"]'::jsonb,
        '{}'::jsonb
    ),
    (
        'calendar.book_slot',
        'calendar',
        'Book Slot',
        'Create booking in provider calendar',
        'v1',
        'active',
        'certified',
        'healthy',
        '["client","branch"]'::jsonb,
        '{}'::jsonb
    ),
    (
        'calendar.get_booking',
        'calendar',
        'Get Booking',
        'Read booking by appointment id',
        'v1',
        'active',
        'certified',
        'healthy',
        '["client","branch"]'::jsonb,
        '{}'::jsonb
    ),
    (
        'calendar.reschedule',
        'calendar',
        'Reschedule Booking',
        'Move booking to another slot',
        'v1',
        'active',
        'certified',
        'healthy',
        '["client","branch"]'::jsonb,
        '{}'::jsonb
    ),
    (
        'calendar.cancel',
        'calendar',
        'Cancel Booking',
        'Cancel booking in provider calendar',
        'v1',
        'active',
        'certified',
        'healthy',
        '["client","branch"]'::jsonb,
        '{}'::jsonb
    ),
    (
        'catalog.service_query',
        'catalog',
        'Service Query',
        'Resolve service info/duration/price',
        'v1',
        'active',
        'certified',
        'healthy',
        '["client","branch"]'::jsonb,
        '{}'::jsonb
    ),
    (
        'catalog.location',
        'catalog',
        'Catalog Location',
        'Resolve branch location/address',
        'v1',
        'active',
        'certified',
        'healthy',
        '["client","branch"]'::jsonb,
        '{}'::jsonb
    ),
    (
        'catalog.portfolio',
        'catalog',
        'Catalog Portfolio',
        'Resolve portfolio/reference media',
        'v1',
        'active',
        'certified',
        'healthy',
        '["client","branch"]'::jsonb,
        '{}'::jsonb
    )
ON CONFLICT (tool_action) DO NOTHING;
