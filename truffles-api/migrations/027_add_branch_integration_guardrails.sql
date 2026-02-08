ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS integration_state TEXT;

UPDATE branches
SET integration_state = 'ok'
WHERE integration_state IS NULL;

ALTER TABLE branches
    ALTER COLUMN integration_state SET DEFAULT 'ok';

ALTER TABLE branches
    ALTER COLUMN integration_state SET NOT NULL;

ALTER TABLE branches
    DROP CONSTRAINT IF EXISTS check_branches_integration_state;

ALTER TABLE branches
    ADD CONSTRAINT check_branches_integration_state
        CHECK (integration_state IN ('ok', 'degraded'));

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS integration_reason TEXT;

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS integration_checked_at TIMESTAMPTZ;

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS integration_degraded_at TIMESTAMPTZ;

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS integration_recovered_at TIMESTAMPTZ;

DO $$
DECLARE
    duplicate_instances TEXT;
BEGIN
    SELECT string_agg(instance_id, ', ' ORDER BY instance_id)
      INTO duplicate_instances
    FROM (
        SELECT instance_id
        FROM branches
        WHERE instance_id IS NOT NULL
        GROUP BY instance_id
        HAVING COUNT(*) > 1
    ) duplicates;

    IF duplicate_instances IS NOT NULL THEN
        RAISE EXCEPTION 'Cannot enforce global unique branches.instance_id, duplicates: %', duplicate_instances;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ux_branches_instance_id_global
    ON branches (instance_id)
    WHERE instance_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_branches_integration_state
    ON branches (integration_state);

CREATE INDEX IF NOT EXISTS idx_branches_integration_checked_at
    ON branches (integration_checked_at);
