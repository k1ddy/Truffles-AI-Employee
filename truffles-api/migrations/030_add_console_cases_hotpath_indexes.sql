-- Console Plane /cases hot-path indexes (P0 DB wave)
-- Note: CONCURRENTLY avoids long write locks on production tables.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_client_conversation_created_desc
    ON messages (client_id, conversation_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_client_role_conversation_created_desc
    ON messages (client_id, role, conversation_id, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_outbox_messages_client_conversation_status
    ON outbox_messages (client_id, conversation_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_handovers_client_status_created_desc
    ON handovers (client_id, status, created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_client_branch
    ON conversations (client_id, branch_id);
