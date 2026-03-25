-- Emergency reset: close all open handovers and вернуть бота в bot_active.
-- Использовать только когда "бот молчит" из-за зависших заявок.

BEGIN;

-- 1) Починить channel_ref у открытых заявок (защита от отправки ответа не тому клиенту)
UPDATE handovers h
SET channel_ref = u.remote_jid
FROM conversations c
JOIN users u ON u.id = c.user_id
WHERE h.conversation_id = c.id
  AND h.status IN ('pending', 'active')
  AND u.remote_jid IS NOT NULL
  AND h.channel_ref IS DISTINCT FROM u.remote_jid;

-- 2) Закрыть все открытые заявки
UPDATE handovers
SET
  status = 'resolved',
  resolved_at = NOW(),
  resolved_by_id = 'system',
  resolved_by_name = 'system',
  resolution_notes = 'Bulk reset: close all open handovers',
  resolution_time_seconds = CASE
    WHEN created_at IS NOT NULL THEN EXTRACT(EPOCH FROM (NOW() - created_at))::INT
    ELSE resolution_time_seconds
  END
WHERE status IN ('pending', 'active');

-- 3) Вернуть диалоги в bot_active (и сбросить мьют/счётчики)
UPDATE conversations
SET
  state = 'bot_active',
  bot_status = 'active',
  bot_muted_until = NULL,
  no_count = 0,
  retry_offered_at = NULL,
  context = '{}'::jsonb
WHERE state IN ('pending', 'manager_active');

COMMIT;
