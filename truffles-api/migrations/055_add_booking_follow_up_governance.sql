ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS follow_up_owner_id UUID REFERENCES agents(id),
    ADD COLUMN IF NOT EXISTS follow_up_due_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_appointments_follow_up_owner_id
    ON appointments (follow_up_owner_id);

CREATE INDEX IF NOT EXISTS ix_appointments_follow_up_due_at
    ON appointments (follow_up_due_at);
