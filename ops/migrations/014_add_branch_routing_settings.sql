-- Migration 014: branch routing + auto-approve settings
-- Run: psql -U n8n -d chatbot -f ops/migrations/014_add_branch_routing_settings.sql

ALTER TABLE client_settings
  ADD COLUMN IF NOT EXISTS branch_resolution_mode TEXT DEFAULT 'hybrid',
  ADD COLUMN IF NOT EXISTS remember_branch_preference BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS manager_scope TEXT DEFAULT 'branch',
  ADD COLUMN IF NOT EXISTS require_branch_for_pricing BOOLEAN DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS auto_approve_roles TEXT DEFAULT 'owner,admin';

-- Verify
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'client_settings'
  AND column_name IN (
    'branch_resolution_mode',
    'remember_branch_preference',
    'manager_scope',
    'require_branch_for_pricing',
    'auto_approve_roles'
  )
ORDER BY ordinal_position;
