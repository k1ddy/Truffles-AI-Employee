-- Wave1 guard: one visit fact per appointment to keep status transitions idempotent.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_visits_appointment_id'
    ) THEN
        ALTER TABLE visits
            ADD CONSTRAINT uq_visits_appointment_id UNIQUE (appointment_id);
    END IF;
END $$;
