CREATE TABLE IF NOT EXISTS tenants_weekly_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    week_key TEXT NOT NULL,
    snapshot JSONB NOT NULL,
    snapshot_schema_version TEXT NOT NULL DEFAULT 'v1',
    actor_id UUID,
    actor_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenants_weekly_snapshots_client_week UNIQUE (client_id, week_key)
);

CREATE INDEX IF NOT EXISTS idx_tenants_weekly_snapshots_client_updated_at
    ON tenants_weekly_snapshots(client_id, updated_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_tenants_weekly_snapshots_week_key
    ON tenants_weekly_snapshots(week_key);

DO $$
DECLARE
    actor_expr TEXT := 'NULL::uuid';
    order_id_expr TEXT := 'audit.created_at';
BEGIN
    -- Backfill must work across legacy and current audit_events schemas.
    -- Some runtimes still use actor_agent_id/event_id physical column names.
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'audit_events'
          AND column_name = 'actor_agent_id'
    ) THEN
        actor_expr := 'audit.actor_agent_id';
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'audit_events'
          AND column_name = 'actor_id'
    ) THEN
        actor_expr := 'audit.actor_id';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'audit_events'
          AND column_name = 'event_id'
    ) THEN
        order_id_expr := 'audit.event_id';
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'audit_events'
          AND column_name = 'id'
    ) THEN
        order_id_expr := 'audit.id';
    END IF;

    EXECUTE REPLACE(
        REPLACE(
            $sql$
        INSERT INTO tenants_weekly_snapshots (
            client_id,
            week_key,
            snapshot,
            snapshot_schema_version,
            actor_id,
            actor_name,
            created_at,
            updated_at
        )
        SELECT DISTINCT ON (audit.client_id, audit.payload ->> 'week_key')
            audit.client_id,
            audit.payload ->> 'week_key' AS week_key,
            audit.payload -> 'snapshot' AS snapshot,
            COALESCE(audit.payload ->> 'snapshot_schema_version', 'v1') AS snapshot_schema_version,
            __ACTOR_EXPR__ AS actor_id,
            audit.actor_name,
            audit.created_at,
            audit.created_at
        FROM audit_events AS audit
        WHERE audit.client_id IS NOT NULL
          AND audit.event_type = 'tenants_weekly_snapshot_saved'
          AND audit.entity_type = 'tenant_snapshot'
          AND jsonb_typeof(audit.payload) = 'object'
          AND jsonb_typeof(audit.payload -> 'snapshot') = 'object'
          AND (audit.payload ->> 'week_key') ~ '^\\d{4}-W\\d{2}$'
        ORDER BY audit.client_id, audit.payload ->> 'week_key', audit.created_at DESC, __ORDER_ID_EXPR__ DESC
        ON CONFLICT (client_id, week_key) DO UPDATE
        SET snapshot = EXCLUDED.snapshot,
            snapshot_schema_version = EXCLUDED.snapshot_schema_version,
            actor_id = EXCLUDED.actor_id,
            actor_name = EXCLUDED.actor_name,
            updated_at = EXCLUDED.updated_at
        WHERE EXCLUDED.updated_at >= tenants_weekly_snapshots.updated_at
            $sql$,
            '__ACTOR_EXPR__',
            actor_expr
        ),
        '__ORDER_ID_EXPR__',
        order_id_expr
    );
END
$$;
