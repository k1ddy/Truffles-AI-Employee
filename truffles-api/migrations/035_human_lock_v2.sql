ALTER TABLE conversation_human_locks
    ADD COLUMN IF NOT EXISTS lock_scope TEXT NOT NULL DEFAULT 'conversation';

UPDATE conversation_human_locks
SET lock_scope = CASE
    WHEN conversation_id IS NULL THEN 'remote_jid'
    ELSE 'conversation'
END
WHERE lock_scope IS NULL OR lock_scope = 'conversation';

DROP INDEX IF EXISTS uq_conversation_human_locks_client_remote;

CREATE UNIQUE INDEX IF NOT EXISTS uq_conversation_human_locks_client_conversation
    ON conversation_human_locks(client_id, conversation_id)
    WHERE conversation_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_conversation_human_locks_client_remote_scope
    ON conversation_human_locks(client_id, remote_jid)
    WHERE lock_scope = 'remote_jid';
