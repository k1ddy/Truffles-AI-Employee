-- Expand allowed handover trigger types to match runtime usage.

ALTER TABLE handovers
  DROP CONSTRAINT IF EXISTS handovers_trigger_type_check;

ALTER TABLE handovers
  ADD CONSTRAINT handovers_trigger_type_check
  CHECK (trigger_type = ANY (ARRAY[
    'intent',
    'keyword',
    'manual',
    'timeout',
    'media',
    'shield',
    'knowledge_safe_mode',
    'minimum_data_contract'
  ]));
