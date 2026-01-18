-- Truffles Console - Test Data Seed Script
-- Purpose: Create test data for E2E testing of Console platform
-- Run: psql -h localhost -U postgres -d truffles -f seed-test-data.sql

-- ============================================
-- CLEANUP (optional - uncomment if needed)
-- ============================================
-- DELETE FROM audit_events WHERE client_id IN (SELECT id FROM clients WHERE name = 'test_client');
-- DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE client_id IN (SELECT id FROM clients WHERE name = 'test_client'));
-- DELETE FROM handovers WHERE client_id IN (SELECT id FROM clients WHERE name = 'test_client');
-- DELETE FROM conversations WHERE client_id IN (SELECT id FROM clients WHERE name = 'test_client');
-- DELETE FROM agent_identities WHERE agent_id IN (SELECT id FROM agents WHERE client_id IN (SELECT id FROM clients WHERE name = 'test_client'));
-- DELETE FROM agents WHERE client_id IN (SELECT id FROM clients WHERE name = 'test_client');
-- DELETE FROM branches WHERE client_id IN (SELECT id FROM clients WHERE name = 'test_client');
-- DELETE FROM client_settings WHERE client_id IN (SELECT id FROM clients WHERE name = 'test_client');
-- DELETE FROM clients WHERE name = 'test_client';

-- ============================================
-- 1. CLIENT
-- ============================================
INSERT INTO clients (id, name, is_active, created_at)
VALUES (
    'c0000001-0000-0000-0000-000000000001',
    'test_client',
    true,
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 2. CLIENT SETTINGS
-- ============================================
INSERT INTO client_settings (id, client_id, reminder_1_minutes, reminder_2_minutes, escalation_timeout_minutes, created_at)
VALUES (
    'cs000001-0000-0000-0000-000000000001',
    'c0000001-0000-0000-0000-000000000001',
    15,
    30,
    60,
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 3. BRANCHES
-- ============================================
INSERT INTO branches (id, client_id, slug, name, is_active, created_at)
VALUES 
    ('b0000001-0000-0000-0000-000000000001', 'c0000001-0000-0000-0000-000000000001', 'almaty', 'Алматы', true, NOW()),
    ('b0000002-0000-0000-0000-000000000002', 'c0000001-0000-0000-0000-000000000001', 'astana', 'Астана', true, NOW()),
    ('b0000003-0000-0000-0000-000000000003', 'c0000001-0000-0000-0000-000000000001', 'shymkent', 'Шымкент', true, NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 4. AGENTS (users who can access Console)
-- ============================================
INSERT INTO agents (id, client_id, branch_id, name, role, is_active, created_at)
VALUES 
    -- Admin (all branches access)
    ('a0000001-0000-0000-0000-000000000001', 'c0000001-0000-0000-0000-000000000001', NULL, 'Admin User', 'admin', true, NOW()),
    -- Manager Almaty
    ('a0000002-0000-0000-0000-000000000002', 'c0000001-0000-0000-0000-000000000001', 'b0000001-0000-0000-0000-000000000001', 'Manager Almaty', 'manager', true, NOW()),
    -- Manager Astana
    ('a0000003-0000-0000-0000-000000000003', 'c0000001-0000-0000-0000-000000000001', 'b0000002-0000-0000-0000-000000000002', 'Manager Astana', 'manager', true, NOW()),
    -- Support
    ('a0000004-0000-0000-0000-000000000004', 'c0000001-0000-0000-0000-000000000001', NULL, 'Support Agent', 'support', true, NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 5. AGENT IDENTITIES (link to Keycloak)
-- Replace <keycloak-user-id> with actual Keycloak user ID (sub claim)
-- You can find it in Keycloak Admin Console > Users > <user> > ID
-- ============================================
-- For testing with 'admin' user in Keycloak:
INSERT INTO agent_identities (id, agent_id, provider, provider_user_id, created_at)
VALUES (
    'ai000001-0000-0000-0000-000000000001',
    'a0000001-0000-0000-0000-000000000001',
    'keycloak',
    '00000000-0000-0000-0000-000000000000', -- 👈 REPLACE with actual Keycloak user ID
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 6. TEST USERS (customers)
-- ============================================
INSERT INTO users (id, client_id, remote_jid, phone, name, created_at)
VALUES 
    ('u0000001-0000-0000-0000-000000000001', 'c0000001-0000-0000-0000-000000000001', '77011234567@s.whatsapp.net', '+77011234567', 'Test Customer 1', NOW()),
    ('u0000002-0000-0000-0000-000000000002', 'c0000001-0000-0000-0000-000000000001', '77021234567@s.whatsapp.net', '+77021234567', 'Test Customer 2', NOW()),
    ('u0000003-0000-0000-0000-000000000003', 'c0000001-0000-0000-0000-000000000001', '77031234567@s.whatsapp.net', '+77031234567', 'Test Customer 3', NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 7. TEST CONVERSATIONS
-- ============================================
INSERT INTO conversations (id, client_id, branch_id, user_id, channel, state, created_at, updated_at)
VALUES 
    ('cv000001-0000-0000-0000-000000000001', 'c0000001-0000-0000-0000-000000000001', 'b0000001-0000-0000-0000-000000000001', 'u0000001-0000-0000-0000-000000000001', 'whatsapp', 'human_active', NOW() - INTERVAL '2 hours', NOW()),
    ('cv000002-0000-0000-0000-000000000002', 'c0000001-0000-0000-0000-000000000001', 'b0000002-0000-0000-0000-000000000002', 'u0000002-0000-0000-0000-000000000002', 'whatsapp', 'human_active', NOW() - INTERVAL '1 hour', NOW()),
    ('cv000003-0000-0000-0000-000000000003', 'c0000001-0000-0000-0000-000000000001', 'b0000001-0000-0000-0000-000000000001', 'u0000003-0000-0000-0000-000000000003', 'whatsapp', 'bot_active', NOW() - INTERVAL '30 minutes', NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 8. TEST HANDOVERS (Cases)
-- ============================================
INSERT INTO handovers (id, client_id, branch_id, conversation_id, status, trigger_type, trigger_value, user_message, context_summary, assigned_to, assigned_to_name, created_at, updated_at)
VALUES 
    -- Pending case (no one took yet) - SLA critical (2 hours old)
    ('h0000001-0000-0000-0000-000000000001', 'c0000001-0000-0000-0000-000000000001', 'b0000001-0000-0000-0000-000000000001', 'cv000001-0000-0000-0000-000000000001', 
     'pending', 'human_request', 'Хочу поговорить с менеджером', 'Здравствуйте, у меня вопрос по записи на следующую неделю', 
     'Клиент интересуется записью на маникюр', NULL, NULL, 
     NOW() - INTERVAL '2 hours', NOW() - INTERVAL '2 hours'),
    
    -- Active case (taken by manager) - 1 hour old
    ('h0000002-0000-0000-0000-000000000002', 'c0000001-0000-0000-0000-000000000001', 'b0000002-0000-0000-0000-000000000002', 'cv000002-0000-0000-0000-000000000002', 
     'active', 'complaint', 'Недовольство обслуживанием', 'Мне не понравилось как сделали в прошлый раз', 
     'Жалоба на качество услуги', 'a0000003-0000-0000-0000-000000000003', 'Manager Astana', 
     NOW() - INTERVAL '1 hour', NOW() - INTERVAL '30 minutes'),
    
    -- Resolved case
    ('h0000003-0000-0000-0000-000000000003', 'c0000001-0000-0000-0000-000000000001', 'b0000001-0000-0000-0000-000000000001', 'cv000003-0000-0000-0000-000000000003', 
     'resolved', 'question', 'Вопрос о ценах', 'Сколько стоит педикюр?', 
     'Вопрос о стоимости услуг', 'a0000002-0000-0000-0000-000000000002', 'Manager Almaty', 
     NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours')
ON CONFLICT (id) DO NOTHING;

-- Set resolved_at for resolved case
UPDATE handovers SET resolved_at = NOW() - INTERVAL '2 hours' WHERE id = 'h0000003-0000-0000-0000-000000000003';

-- ============================================
-- 9. TEST MESSAGES
-- ============================================
INSERT INTO messages (id, conversation_id, role, content, created_at)
VALUES 
    -- Conversation 1 (pending handover)
    ('m0000001-0000-0000-0000-000000000001', 'cv000001-0000-0000-0000-000000000001', 'user', 'Здравствуйте!', NOW() - INTERVAL '2 hours' - INTERVAL '5 minutes'),
    ('m0000002-0000-0000-0000-000000000002', 'cv000001-0000-0000-0000-000000000001', 'assistant', 'Здравствуйте! Чем могу помочь?', NOW() - INTERVAL '2 hours' - INTERVAL '4 minutes'),
    ('m0000003-0000-0000-0000-000000000003', 'cv000001-0000-0000-0000-000000000001', 'user', 'Хочу поговорить с менеджером', NOW() - INTERVAL '2 hours' - INTERVAL '3 minutes'),
    ('m0000004-0000-0000-0000-000000000004', 'cv000001-0000-0000-0000-000000000001', 'assistant', 'Конечно, сейчас переключу вас на менеджера. Пожалуйста, подождите.', NOW() - INTERVAL '2 hours' - INTERVAL '2 minutes'),
    ('m0000005-0000-0000-0000-000000000005', 'cv000001-0000-0000-0000-000000000001', 'user', 'У меня вопрос по записи на следующую неделю', NOW() - INTERVAL '2 hours'),
    
    -- Conversation 2 (active handover)
    ('m0000006-0000-0000-0000-000000000006', 'cv000002-0000-0000-0000-000000000002', 'user', 'Добрый день', NOW() - INTERVAL '1 hour' - INTERVAL '10 minutes'),
    ('m0000007-0000-0000-0000-000000000007', 'cv000002-0000-0000-0000-000000000002', 'assistant', 'Добрый день! Рады вас видеть снова!', NOW() - INTERVAL '1 hour' - INTERVAL '9 minutes'),
    ('m0000008-0000-0000-0000-000000000008', 'cv000002-0000-0000-0000-000000000002', 'user', 'Мне не понравилось как сделали в прошлый раз', NOW() - INTERVAL '1 hour' - INTERVAL '8 minutes'),
    ('m0000009-0000-0000-0000-000000000009', 'cv000002-0000-0000-0000-000000000002', 'assistant', 'Очень жаль это слышать. Переключаю вас на менеджера.', NOW() - INTERVAL '1 hour' - INTERVAL '7 minutes'),
    ('m0000010-0000-0000-0000-000000000010', 'cv000002-0000-0000-0000-000000000002', 'manager', 'Здравствуйте! Расскажите подробнее, что именно вас не устроило?', NOW() - INTERVAL '30 minutes'),
    
    -- Conversation 3 (resolved handover)
    ('m0000011-0000-0000-0000-000000000011', 'cv000003-0000-0000-0000-000000000003', 'user', 'Сколько стоит педикюр?', NOW() - INTERVAL '3 hours'),
    ('m0000012-0000-0000-0000-000000000012', 'cv000003-0000-0000-0000-000000000003', 'assistant', 'Педикюр стоит от 5000 тенге. Хотите записаться?', NOW() - INTERVAL '3 hours' + INTERVAL '1 minute'),
    ('m0000013-0000-0000-0000-000000000013', 'cv000003-0000-0000-0000-000000000003', 'user', 'Да, но мне нужна консультация по типу покрытия', NOW() - INTERVAL '2 hours' - INTERVAL '30 minutes'),
    ('m0000014-0000-0000-0000-000000000014', 'cv000003-0000-0000-0000-000000000003', 'manager', 'Мы предлагаем несколько видов покрытия: обычный лак, гель-лак и шеллак. Какой вас интересует?', NOW() - INTERVAL '2 hours' - INTERVAL '20 minutes'),
    ('m0000015-0000-0000-0000-000000000015', 'cv000003-0000-0000-0000-000000000003', 'user', 'Гель-лак. Запишите меня на завтра', NOW() - INTERVAL '2 hours' - INTERVAL '10 minutes'),
    ('m0000016-0000-0000-0000-000000000016', 'cv000003-0000-0000-0000-000000000003', 'manager', 'Отлично! Записала вас на завтра в 14:00. До встречи!', NOW() - INTERVAL '2 hours')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 10. TEST AUDIT EVENTS
-- ============================================
INSERT INTO audit_events (id, client_id, actor_id, actor_name, event_type, entity_type, entity_id, payload, created_at)
VALUES 
    ('ae000001-0000-0000-0000-000000000001', 'c0000001-0000-0000-0000-000000000001', 'a0000003-0000-0000-0000-000000000003', 'Manager Astana', 'case_taken', 'handover', 'h0000002-0000-0000-0000-000000000002', '{"previous_status": "pending"}', NOW() - INTERVAL '30 minutes'),
    ('ae000002-0000-0000-0000-000000000002', 'c0000001-0000-0000-0000-000000000001', 'a0000003-0000-0000-0000-000000000003', 'Manager Astana', 'message_sent', 'conversation', 'cv000002-0000-0000-0000-000000000002', '{"message_id": "m0000010-0000-0000-0000-000000000010"}', NOW() - INTERVAL '30 minutes'),
    ('ae000003-0000-0000-0000-000000000003', 'c0000001-0000-0000-0000-000000000001', 'a0000002-0000-0000-0000-000000000002', 'Manager Almaty', 'case_taken', 'handover', 'h0000003-0000-0000-0000-000000000003', '{"previous_status": "pending"}', NOW() - INTERVAL '2 hours' - INTERVAL '25 minutes'),
    ('ae000004-0000-0000-0000-000000000004', 'c0000001-0000-0000-0000-000000000001', 'a0000002-0000-0000-0000-000000000002', 'Manager Almaty', 'case_resolved', 'handover', 'h0000003-0000-0000-0000-000000000003', '{"resolution_time_minutes": 25}', NOW() - INTERVAL '2 hours')
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- VERIFY DATA
-- ============================================
SELECT 'Clients:' AS entity, COUNT(*) AS count FROM clients WHERE name = 'test_client'
UNION ALL
SELECT 'Branches:', COUNT(*) FROM branches WHERE client_id = 'c0000001-0000-0000-0000-000000000001'
UNION ALL
SELECT 'Agents:', COUNT(*) FROM agents WHERE client_id = 'c0000001-0000-0000-0000-000000000001'
UNION ALL
SELECT 'Handovers:', COUNT(*) FROM handovers WHERE client_id = 'c0000001-0000-0000-0000-000000000001'
UNION ALL
SELECT 'Messages:', COUNT(*) FROM messages WHERE conversation_id LIKE 'cv00000%'
UNION ALL
SELECT 'Audit Events:', COUNT(*) FROM audit_events WHERE client_id = 'c0000001-0000-0000-0000-000000000001';

-- ============================================
-- IMPORTANT: Get Keycloak User ID
-- ============================================
-- To link the 'admin' Keycloak user to the test agent:
-- 1. Go to Keycloak Admin Console: http://localhost:8080/admin
-- 2. Navigate to: Realm > Users > admin
-- 3. Copy the ID (UUID format)
-- 4. Update agent_identities:
--    UPDATE agent_identities SET provider_user_id = '<your-keycloak-user-id>' 
--    WHERE agent_id = 'a0000001-0000-0000-0000-000000000001';
