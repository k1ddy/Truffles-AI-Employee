-- Add agent_link_tokens for Telegram linking
CREATE TABLE IF NOT EXISTS agent_link_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    channel TEXT NOT NULL DEFAULT 'telegram',
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    created_by_id UUID REFERENCES agents(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_link_tokens_hash ON agent_link_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_agent_link_tokens_agent_id ON agent_link_tokens(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_link_tokens_client_id ON agent_link_tokens(client_id);
