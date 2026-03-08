ALTER TABLE console_saved_views
    ADD COLUMN IF NOT EXISTS scope TEXT NOT NULL DEFAULT 'personal',
    ADD COLUMN IF NOT EXISTS created_by_agent_id UUID REFERENCES agents(id),
    ADD COLUMN IF NOT EXISTS target_branch_id UUID REFERENCES branches(id),
    ADD COLUMN IF NOT EXISTS target_role TEXT;

ALTER TABLE console_saved_views
    ALTER COLUMN agent_id DROP NOT NULL;

UPDATE console_saved_views
SET created_by_agent_id = agent_id
WHERE created_by_agent_id IS NULL;

ALTER TABLE console_saved_views
    ALTER COLUMN created_by_agent_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_console_saved_views_scope_surface_updated_at
    ON console_saved_views (scope, surface, updated_at);

CREATE UNIQUE INDEX IF NOT EXISTS ux_console_saved_views_team_name
    ON console_saved_views (
        client_id,
        surface,
        COALESCE(target_branch_id, '00000000-0000-0000-0000-000000000000'::uuid),
        COALESCE(target_role, ''),
        name
    )
    WHERE scope = 'team';

CREATE UNIQUE INDEX IF NOT EXISTS ux_console_saved_views_team_default_target
    ON console_saved_views (
        client_id,
        surface,
        COALESCE(target_branch_id, '00000000-0000-0000-0000-000000000000'::uuid),
        COALESCE(target_role, '')
    )
    WHERE scope = 'team' AND is_default IS TRUE;
