-- ============================================================
-- МИГРАЦИЯ 001: Расширение существующих таблиц + новые
-- Дата: 2025-12-08
-- Автор: Droid
-- 
-- СУЩЕСТВУЮЩИЕ ТАБЛИЦЫ (не трогаем структуру, расширяем):
-- - clients — уже есть
-- - client_settings — уже есть с таймаутами и quiet_hours
-- - conversations — уже есть с escalated_at
-- - handovers — уже есть базовая эскалация
--
-- ЧТО ДЕЛАЕТ:
-- 1. Расширяет client_settings (booking, autolearn, telegram_chat_id)
-- 2. Расширяет conversations (bot_status, bot_muted_until, no_count)
-- 3. Расширяет handovers (manager_response, moderation, llm_check, learning)
-- 4. Создаёт branches (филиалы)
-- 5. Создаёт managers (кто может отвечать)
-- 6. Создаёт learned_responses (выученные ответы)
-- ============================================================

-- ============================================================
-- 1. РАСШИРЕНИЕ CLIENT_SETTINGS
-- ============================================================

-- Telegram chat для эскалаций
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS telegram_chat_id TEXT;
COMMENT ON COLUMN client_settings.telegram_chat_id IS 'ID Telegram группы для эскалаций';

-- Настройки автообучения
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS autolearn_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS autolearn_llm_check BOOLEAN DEFAULT TRUE;
COMMENT ON COLUMN client_settings.autolearn_enabled IS 'Включено ли автообучение';
COMMENT ON COLUMN client_settings.autolearn_llm_check IS 'Проверять ответы менеджеров через LLM';

-- Настройки записи клиентов
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS booking_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS booking_cancel_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS booking_change_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS booking_source TEXT;
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS booking_sheet_id TEXT;
COMMENT ON COLUMN client_settings.booking_enabled IS 'Включена ли запись клиентов';
COMMENT ON COLUMN client_settings.booking_source IS 'Источник расписания: google_sheets, api';

-- Настройки "нет значит нет"
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS silence_after_first_no_minutes INTEGER DEFAULT 30;
ALTER TABLE client_settings ADD COLUMN IF NOT EXISTS max_retry_offers INTEGER DEFAULT 1;
COMMENT ON COLUMN client_settings.silence_after_first_no_minutes IS 'Сколько минут молчать после первого отказа';
COMMENT ON COLUMN client_settings.max_retry_offers IS 'Сколько раз предложить помощь после молчания';

-- ============================================================
-- 2. BRANCHES (ФИЛИАЛЫ) — ПОДХОД Б
-- ============================================================

CREATE TABLE IF NOT EXISTS branches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  
  -- Идентификация
  slug TEXT NOT NULL,                    -- 'almaty', 'astana'
  name TEXT NOT NULL,                    -- 'Филиал Алматы'
  
  -- WhatsApp
  instance_id TEXT NOT NULL,             -- отдельный instance для филиала
  phone TEXT,                            -- номер филиала
  
  -- Telegram (опционально отдельная группа)
  telegram_chat_id TEXT,                 -- если null — используется общая группа клиента
  
  -- RAG фильтрация
  knowledge_tag TEXT,                    -- тег для фильтрации в Qdrant (metadata.branch)
  
  -- Статус
  is_active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(client_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_branches_client ON branches(client_id);
CREATE INDEX IF NOT EXISTS idx_branches_slug ON branches(client_id, slug);

COMMENT ON TABLE branches IS 'Филиалы клиента (для нескольких WhatsApp номеров)';

-- ============================================================
-- 3. РАСШИРЕНИЕ HANDOVERS (для автообучения)
-- ============================================================

-- Ответ менеджера (для автообучения)
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS user_message TEXT;
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS manager_response TEXT;
COMMENT ON COLUMN handovers.user_message IS 'Сообщение клиента которое вызвало эскалацию';
COMMENT ON COLUMN handovers.manager_response IS 'Ответ менеджера (для автообучения)';

-- Назначение (механизм "Беру" — менеджер отвечает сообщением)
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS assigned_to_name TEXT;
COMMENT ON COLUMN handovers.assigned_to_name IS 'Имя менеджера который взял эскалацию';

-- Время до ответа (метрика)
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS resolution_time_seconds INTEGER;
COMMENT ON COLUMN handovers.resolution_time_seconds IS 'Секунды от создания до ответа менеджера';

-- Проверка LLM (gpt-5-mini)
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS llm_check_result JSONB;
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS llm_checked_at TIMESTAMPTZ;
COMMENT ON COLUMN handovers.llm_check_result IS 'Результат проверки LLM: {ok: bool, issues: [string]}';

-- Модерация владельцем
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS moderation_status TEXT DEFAULT 'pending';
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS moderated_by TEXT;
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS moderated_by_name TEXT;
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS moderation_notes TEXT;
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMPTZ;
COMMENT ON COLUMN handovers.moderation_status IS 'Статус модерации: pending, approved, rejected, edited';

-- Обучение
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS added_to_knowledge BOOLEAN DEFAULT FALSE;
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS knowledge_doc_id TEXT;
COMMENT ON COLUMN handovers.added_to_knowledge IS 'Добавлен ли ответ в базу знаний';
COMMENT ON COLUMN handovers.knowledge_doc_id IS 'ID точки в Qdrant';

-- Филиал (если несколько номеров)
ALTER TABLE handovers ADD COLUMN IF NOT EXISTS branch_id UUID;
-- FK добавим после создания branches

-- ============================================================
-- 4. "НЕТ ЗНАЧИТ НЕТ" — ПОЛЯ В CONVERSATIONS
-- ============================================================

-- ПРИМЕЧАНИЕ: conversations.status уже имеет 'handover' как значение
-- Добавляем только поля для двухступенчатой схемы "нет значит нет"

-- Статус бота в диалоге (дополняет существующий status)
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS bot_status TEXT DEFAULT 'active';
-- active: бот отвечает нормально
-- muted: бот молчит (клиент отказался)
-- human_active: менеджер ведёт диалог

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS bot_muted_until TIMESTAMPTZ;
-- до какого времени бот молчит

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS human_operator_id TEXT;
-- telegram user_id менеджера который ведёт диалог

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS no_count INTEGER DEFAULT 0;
-- сколько раз клиент сказал "нет" на предложение помощи

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS retry_offered_at TIMESTAMPTZ;
-- когда бот предложил помощь после молчания (для отслеживания попыток)

COMMENT ON COLUMN conversations.bot_status IS 'Статус бота: active, muted, human_active';
COMMENT ON COLUMN conversations.bot_muted_until IS 'До какого времени бот молчит';
COMMENT ON COLUMN conversations.no_count IS 'Сколько раз клиент отказался от помощи бота';
COMMENT ON COLUMN conversations.retry_offered_at IS 'Когда бот предложил помощь после молчания';

-- ============================================================
-- 5. MANAGERS (КТО МОЖЕТ ОТВЕЧАТЬ НА ЭСКАЛАЦИИ)
-- ============================================================

CREATE TABLE IF NOT EXISTS managers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  
  -- Идентификация
  telegram_user_id TEXT NOT NULL,        -- ID в Telegram
  telegram_username TEXT,                -- @username
  name TEXT NOT NULL,                    -- Имя для отображения
  
  -- Роль
  role TEXT DEFAULT 'manager',           -- owner, admin, manager
  
  -- Права (для будущего)
  can_approve_learning BOOLEAN DEFAULT FALSE,  -- может одобрять обучение
  
  -- Статус
  is_active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(client_id, telegram_user_id)
);

CREATE INDEX IF NOT EXISTS idx_managers_client ON managers(client_id);
CREATE INDEX IF NOT EXISTS idx_managers_telegram ON managers(telegram_user_id);

COMMENT ON TABLE managers IS 'Менеджеры которые могут отвечать на эскалации';

-- ============================================================
-- 6. LEARNED_RESPONSES (ВЫУЧЕННЫЕ ОТВЕТЫ)
-- ============================================================

CREATE TABLE IF NOT EXISTS learned_responses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
  escalation_id UUID REFERENCES escalations(id) ON DELETE SET NULL,
  
  -- Вопрос
  question_text TEXT NOT NULL,           -- оригинальный вопрос
  question_normalized TEXT,              -- нормализованный (lowercase, без пунктуации)
  
  -- Ответ
  response_text TEXT NOT NULL,           -- одобренный ответ
  
  -- Источник
  source TEXT DEFAULT 'manager',         -- manager, owner, edited
  source_name TEXT,                      -- имя кто дал ответ
  
  -- Статистика использования
  use_count INTEGER DEFAULT 0,
  last_used_at TIMESTAMPTZ,
  
  -- Статус
  is_active BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learned_client ON learned_responses(client_id);
CREATE INDEX IF NOT EXISTS idx_learned_active ON learned_responses(client_id, is_active);

COMMENT ON TABLE learned_responses IS 'Выученные ответы из эскалаций (для RAG)';

-- ============================================================
-- 7. FOREIGN KEY ДЛЯ HANDOVERS.BRANCH_ID
-- ============================================================

-- Теперь можно добавить FK после создания branches
ALTER TABLE handovers 
  DROP CONSTRAINT IF EXISTS handovers_branch_id_fkey;
  
ALTER TABLE handovers 
  ADD CONSTRAINT handovers_branch_id_fkey 
  FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL;

-- Индекс для поиска по модерации
CREATE INDEX IF NOT EXISTS idx_handovers_moderation ON handovers(moderation_status);
CREATE INDEX IF NOT EXISTS idx_handovers_learning ON handovers(added_to_knowledge);

-- ============================================================
-- ГОТОВО
-- ============================================================

-- Проверка что всё создалось
DO $$
BEGIN
  RAISE NOTICE '===========================================';
  RAISE NOTICE 'Миграция 001 выполнена успешно';
  RAISE NOTICE '===========================================';
  RAISE NOTICE '';
  RAISE NOTICE 'РАСШИРЕНЫ СУЩЕСТВУЮЩИЕ ТАБЛИЦЫ:';
  RAISE NOTICE '  - client_settings: telegram_chat_id, autolearn, booking, silence';
  RAISE NOTICE '  - conversations: bot_status, bot_muted_until, no_count, retry_offered_at';
  RAISE NOTICE '  - handovers: manager_response, moderation, llm_check, learning';
  RAISE NOTICE '';
  RAISE NOTICE 'СОЗДАНЫ НОВЫЕ ТАБЛИЦЫ:';
  RAISE NOTICE '  - branches (филиалы)';
  RAISE NOTICE '  - managers (кто может отвечать)';
  RAISE NOTICE '  - learned_responses (выученные ответы)';
  RAISE NOTICE '';
  RAISE NOTICE 'Следующий шаг: обновить workflow для использования новых полей';
END $$;
