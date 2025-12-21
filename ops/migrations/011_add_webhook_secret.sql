-- Add webhook secret per tenant for inbound /webhook auth
ALTER TABLE client_settings
ADD COLUMN IF NOT EXISTS webhook_secret TEXT;
