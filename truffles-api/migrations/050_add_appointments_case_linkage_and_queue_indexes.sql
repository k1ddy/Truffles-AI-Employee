-- Wave3: explicit appointment->case linkage + queue query indexes.

ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS case_id UUID REFERENCES handovers(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_appointments_case_id ON appointments(case_id);
CREATE INDEX IF NOT EXISTS idx_appointments_client_conversation_start_at
    ON appointments(client_id, conversation_id, start_at DESC);
CREATE INDEX IF NOT EXISTS idx_appointments_client_case_start_at
    ON appointments(client_id, case_id, start_at DESC);
CREATE INDEX IF NOT EXISTS idx_appointments_client_status_start_at
    ON appointments(client_id, status, start_at DESC);

-- Backfill historical rows by latest case in conversation (idempotent).
WITH latest_case_per_conversation AS (
    SELECT DISTINCT ON (h.client_id, h.conversation_id)
        h.client_id,
        h.conversation_id,
        h.id AS case_id
    FROM handovers h
    WHERE h.conversation_id IS NOT NULL
    ORDER BY h.client_id, h.conversation_id, h.created_at DESC
)
UPDATE appointments a
SET case_id = latest_case_per_conversation.case_id
FROM latest_case_per_conversation
WHERE a.case_id IS NULL
  AND a.client_id = latest_case_per_conversation.client_id
  AND a.conversation_id = latest_case_per_conversation.conversation_id;
