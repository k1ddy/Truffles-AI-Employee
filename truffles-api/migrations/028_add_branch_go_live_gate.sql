ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS go_live_state TEXT;

UPDATE branches
SET go_live_state = CASE WHEN is_active THEN 'approved' ELSE 'pending' END
WHERE go_live_state IS NULL;

ALTER TABLE branches
    ALTER COLUMN go_live_state SET DEFAULT 'pending';

ALTER TABLE branches
    ALTER COLUMN go_live_state SET NOT NULL;

ALTER TABLE branches
    DROP CONSTRAINT IF EXISTS check_branches_go_live_state;

ALTER TABLE branches
    ADD CONSTRAINT check_branches_go_live_state
        CHECK (go_live_state IN ('pending', 'approved', 'rejected'));

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS go_live_reason TEXT;

UPDATE branches
SET go_live_reason = 'backfill_existing_active_branch'
WHERE go_live_state = 'approved'
  AND (go_live_reason IS NULL OR btrim(go_live_reason) = '');

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS go_live_reviewed_at TIMESTAMPTZ;

UPDATE branches
SET go_live_reviewed_at = now()
WHERE go_live_state = 'approved'
  AND go_live_reviewed_at IS NULL;

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS go_live_reviewed_by UUID REFERENCES agents(id);

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS go_live_waiver_until TIMESTAMPTZ;

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS go_live_waiver_reason TEXT;

ALTER TABLE branches
    ADD COLUMN IF NOT EXISTS go_live_waiver_by UUID REFERENCES agents(id);
