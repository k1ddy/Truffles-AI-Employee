-- Add index to speed up branch-scoped queries on conversations
CREATE INDEX IF NOT EXISTS ix_conversations_branch_id ON conversations (branch_id);
