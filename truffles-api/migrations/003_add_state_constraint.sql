-- Инвариант: manager_active должен иметь telegram_topic_id
-- PostgreSQL НЕ поддерживает subqueries в CHECK, поэтому только простой constraint

ALTER TABLE conversations 
ADD CONSTRAINT chk_manager_active_has_topic
CHECK (state != 'manager_active' OR telegram_topic_id IS NOT NULL);

-- Комментарий: проверка на активный handover делается на уровне приложения
-- в state_service.py → check_invariants()
