# НЕДЕЛЯ 3: Защита кода — Задачи для кодера

**Архитектор:** Готово к выполнению
**Приоритет:** P0
**Ссылка:** `SPECS/ARCHITECTURE.md` ЧАСТЬ 10

---

## КОНТЕКСТ

Неделя 2 завершена: тесты, логирование, CI/CD, линтер.

Неделя 3: защита от сбоев и багов на уровне архитектуры.

**Цель:** Клиент всегда получает ответ. Невалидные состояния невозможны.

**Текущее состояние:**
- `state_machine.py` — enum и валидация переходов (простая)
- Переходы состояний в `webhook.py` напрямую: `conversation.state = new_state.value`
- Нет транзакций — всё в одном `db.commit()` в конце
- Ad-hoc self-healing в webhook.py (строки 139-152)

---

## ЗАДАЧА 1: Result Pattern

**Время:** ~20 мин
**Спека:** SPECS/ARCHITECTURE.md → "Решение: Result Pattern"

### Создать `truffles-api/app/services/result.py`:

```python
from dataclasses import dataclass
from typing import Optional, TypeVar, Generic

T = TypeVar('T')


@dataclass
class Result(Generic[T]):
    ok: bool
    value: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    @staticmethod
    def success(value: T) -> 'Result[T]':
        return Result(ok=True, value=value)
    
    @staticmethod
    def failure(error: str, code: str = "unknown") -> 'Result[T]':
        return Result(ok=False, error=error, error_code=code)
    
    def unwrap_or(self, default: T) -> T:
        return self.value if self.ok else default
```

### Коды ошибок:

| Код | Описание | Fallback |
|-----|----------|----------|
| `ai_error` | LLM не ответил | "Ошибка, попробуйте позже" |
| `rag_error` | Qdrant недоступен | Ответить без RAG |
| `escalation_error` | Не удалось эскалировать | Ответить + лог |
| `db_error` | PostgreSQL | Ошибка, не сохранять |

### Критерии готовности:
- [ ] result.py создан
- [ ] Тест test_result.py создан (min 5 тестов)

---

## ЗАДАЧА 2: State Service с транзакциями

**Время:** ~40 мин
**Спека:** SPECS/ARCHITECTURE.md → "Транзакции при смене состояния"

### Создать `truffles-api/app/services/state_service.py`:

```python
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import Conversation, Handover
from app.services.result import Result
from app.services.state_machine import ConversationState
from app.services.telegram_service import TelegramService
from app.services.escalation_service import get_telegram_credentials
from app.logging_config import get_logger

logger = get_logger("state_service")


def escalate_to_pending(
    db: Session,
    conversation: Conversation,
    user_message: str,
    trigger_type: str,
    trigger_value: str = None
) -> Result[Handover]:
    """Атомарный переход bot_active → pending с созданием handover и topic."""
    
    # Проверка: можно ли эскалировать
    if conversation.state != ConversationState.BOT_ACTIVE.value:
        return Result.failure(
            f"Cannot escalate from state {conversation.state}",
            "invalid_state"
        )
    
    try:
        # Получить Telegram credentials
        bot_token, chat_id = get_telegram_credentials(db, conversation.client_id)
        if not bot_token or not chat_id:
            return Result.failure("No Telegram credentials", "no_telegram")
        
        # Создать topic
        telegram = TelegramService(bot_token)
        from app.models import User
        user = db.query(User).filter(User.id == conversation.user_id).first()
        user_name = user.name or user.phone if user else "Unknown"
        
        topic_result = telegram.create_topic(chat_id, f"💬 {user_name}")
        if not topic_result or not topic_result.get("ok"):
            return Result.failure("Failed to create topic", "topic_error")
        
        topic_id = topic_result["result"]["message_thread_id"]
        
        # Атомарная операция
        now = datetime.now(timezone.utc)
        
        # 1. Создать handover
        handover = Handover(
            conversation_id=conversation.id,
            client_id=conversation.client_id,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            user_message=user_message,
            status="pending",
            created_at=now,
            channel="telegram",
        )
        db.add(handover)
        
        # 2. Обновить conversation
        conversation.state = ConversationState.PENDING.value
        conversation.telegram_topic_id = topic_id
        conversation.escalated_at = now
        
        db.flush()  # проверить constraints
        
        logger.info(f"Escalated conversation {conversation.id} to pending, topic={topic_id}")
        return Result.success(handover)
        
    except Exception as e:
        logger.error(f"Escalation failed: {e}")
        return Result.failure(str(e), "escalation_error")


def manager_take(db: Session, conversation: Conversation, handover: Handover, manager_name: str) -> Result[bool]:
    """Атомарный переход pending → manager_active."""
    
    if conversation.state != ConversationState.PENDING.value:
        return Result.failure(f"Cannot take from state {conversation.state}", "invalid_state")
    
    if handover.status != "pending":
        return Result.failure(f"Handover status is {handover.status}", "invalid_handover")
    
    try:
        now = datetime.now(timezone.utc)
        
        conversation.state = ConversationState.MANAGER_ACTIVE.value
        handover.status = "active"
        handover.assigned_to_name = manager_name
        handover.first_response_at = now
        
        db.flush()
        
        logger.info(f"Manager {manager_name} took conversation {conversation.id}")
        return Result.success(True)
        
    except Exception as e:
        logger.error(f"Manager take failed: {e}")
        return Result.failure(str(e), "take_error")


def manager_resolve(db: Session, conversation: Conversation, handover: Handover, manager_name: str) -> Result[bool]:
    """Атомарный переход manager_active/pending → bot_active."""
    
    if conversation.state not in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
        return Result.failure(f"Cannot resolve from state {conversation.state}", "invalid_state")
    
    try:
        now = datetime.now(timezone.utc)
        
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.bot_muted_until = None
        conversation.no_count = 0
        
        handover.status = "resolved"
        handover.resolved_at = now
        handover.resolved_by_name = manager_name
        
        if handover.created_at:
            handover.resolution_time_seconds = int((now - handover.created_at).total_seconds())
        
        db.flush()
        
        logger.info(f"Manager {manager_name} resolved conversation {conversation.id}")
        return Result.success(True)
        
    except Exception as e:
        logger.error(f"Manager resolve failed: {e}")
        return Result.failure(str(e), "resolve_error")


def check_invariants(conversation: Conversation, handover: Handover = None) -> list[str]:
    """Проверить инварианты состояния. Возвращает список нарушений."""
    violations = []
    
    # Инвариант 1: manager_active должен иметь topic_id
    if conversation.state == ConversationState.MANAGER_ACTIVE.value:
        if not conversation.telegram_topic_id:
            violations.append("manager_active_no_topic")
    
    # Инвариант 2: pending должен иметь topic_id
    if conversation.state == ConversationState.PENDING.value:
        if not conversation.telegram_topic_id:
            violations.append("pending_no_topic")
    
    # Инвариант 3: pending/manager_active должен иметь active/pending handover
    if conversation.state in [ConversationState.PENDING.value, ConversationState.MANAGER_ACTIVE.value]:
        if handover is None or handover.status not in ["pending", "active"]:
            violations.append("no_active_handover")
    
    return violations
```

### Критерии готовности:
- [ ] state_service.py создан
- [ ] Тест test_state_service.py создан (min 8 тестов)
- [ ] Все переходы используют Result pattern

---

## ЗАДАЧА 3: Health Service (self-healing)

**Время:** ~30 мин
**Спека:** SPECS/ARCHITECTURE.md → "Self-healing"

### Создать `truffles-api/app/services/health_service.py`:

```python
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import Conversation, Handover
from app.services.state_machine import ConversationState
from app.logging_config import get_logger

logger = get_logger("health_service")


def check_and_heal_conversations(db: Session) -> dict:
    """Проверить инварианты и починить нарушения."""
    healed = []
    
    # Инвариант 1: manager_active/pending без topic_id → сбросить на bot_active
    broken_no_topic = db.query(Conversation).filter(
        Conversation.state.in_([
            ConversationState.MANAGER_ACTIVE.value,
            ConversationState.PENDING.value
        ]),
        Conversation.telegram_topic_id == None
    ).all()
    
    for conv in broken_no_topic:
        old_state = conv.state
        conv.state = ConversationState.BOT_ACTIVE.value
        
        # Закрыть открытые handovers
        open_handovers = db.query(Handover).filter(
            Handover.conversation_id == conv.id,
            Handover.status.in_(["pending", "active"])
        ).all()
        
        for h in open_handovers:
            h.status = "resolved"
            h.resolved_at = datetime.now(timezone.utc)
            h.resolution_notes = f"Auto-healed: {old_state} without topic"
        
        healed.append({
            "conversation_id": str(conv.id),
            "issue": f"{old_state}_no_topic",
            "action": "reset_to_bot_active"
        })
        logger.warning(f"Healed conversation {conv.id}: {old_state} without topic")
    
    # Инвариант 2: pending/manager_active без активного handover → сбросить
    conversations_with_state = db.query(Conversation).filter(
        Conversation.state.in_([
            ConversationState.MANAGER_ACTIVE.value,
            ConversationState.PENDING.value
        ])
    ).all()
    
    for conv in conversations_with_state:
        active_handover = db.query(Handover).filter(
            Handover.conversation_id == conv.id,
            Handover.status.in_(["pending", "active"])
        ).first()
        
        if not active_handover:
            old_state = conv.state
            conv.state = ConversationState.BOT_ACTIVE.value
            healed.append({
                "conversation_id": str(conv.id),
                "issue": f"{old_state}_no_handover",
                "action": "reset_to_bot_active"
            })
            logger.warning(f"Healed conversation {conv.id}: {old_state} without active handover")
    
    db.commit()
    
    return {
        "healed_count": len(healed),
        "details": healed,
        "checked_at": datetime.now(timezone.utc).isoformat()
    }


def get_system_health(db: Session) -> dict:
    """Получить общее состояние системы."""
    
    # Считаем состояния
    bot_active = db.query(Conversation).filter(
        Conversation.state == ConversationState.BOT_ACTIVE.value
    ).count()
    
    pending = db.query(Conversation).filter(
        Conversation.state == ConversationState.PENDING.value
    ).count()
    
    manager_active = db.query(Conversation).filter(
        Conversation.state == ConversationState.MANAGER_ACTIVE.value
    ).count()
    
    # Считаем handovers
    pending_handovers = db.query(Handover).filter(
        Handover.status == "pending"
    ).count()
    
    active_handovers = db.query(Handover).filter(
        Handover.status == "active"
    ).count()
    
    return {
        "conversations": {
            "bot_active": bot_active,
            "pending": pending,
            "manager_active": manager_active,
        },
        "handovers": {
            "pending": pending_handovers,
            "active": active_handovers,
        },
        "checked_at": datetime.now(timezone.utc).isoformat()
    }
```

### Критерии готовности:
- [ ] health_service.py создан
- [ ] Тест test_health_service.py создан (min 5 тестов)

---

## ЗАДАЧА 4: SQL Constraint (миграция)

**Время:** ~15 мин
**Спека:** SPECS/ARCHITECTURE.md → "SQL Constraints"

### Создать `truffles-api/migrations/003_add_state_constraint.sql`:

```sql
-- Инвариант: manager_active должен иметь telegram_topic_id
-- PostgreSQL НЕ поддерживает subqueries в CHECK, поэтому только простой constraint

ALTER TABLE conversations 
ADD CONSTRAINT chk_manager_active_has_topic
CHECK (state != 'manager_active' OR telegram_topic_id IS NOT NULL);

-- Комментарий: проверка на активный handover делается на уровне приложения
-- в state_service.py → check_invariants()
```

### Критерии готовности:
- [ ] Миграция создана
- [ ] Миграция выполнена на сервере (после деплоя)

---

## ЗАДАЧА 5: Рефакторинг webhook.py

**Время:** ~30 мин

### Что изменить:

1. Заменить прямые изменения `conversation.state` на вызовы `state_service`
2. Удалить ad-hoc self-healing (строки 139-152) — теперь это в health_service
3. Обработать Result от state_service

### Пример изменения:

**Было:**
```python
if should_escalate(intent):
    new_state = escalate(ConversationState(conversation.state))
    conversation.state = new_state.value
    conversation.escalated_at = now
    handover, telegram_sent = escalate_conversation(...)
```

**Стало:**
```python
from app.services.state_service import escalate_to_pending

if should_escalate(intent):
    result = escalate_to_pending(
        db=db,
        conversation=conversation,
        user_message=message_text,
        trigger_type="intent",
        trigger_value=intent.value
    )
    if result.ok:
        handover = result.value
        telegram_sent = True
    else:
        logger.error(f"Escalation failed: {result.error}")
        telegram_sent = False
```

### Критерии готовности:
- [ ] webhook.py использует state_service
- [ ] telegram_webhook.py использует state_service (manager_take, manager_resolve)
- [ ] Ad-hoc self-healing удалён из webhook.py
- [ ] Все тесты проходят

---

## ЗАДАЧА 6: Health endpoint

**Время:** ~15 мин

### Добавить в `truffles-api/app/routers/admin.py`:

```python
from app.services.health_service import check_and_heal_conversations, get_system_health

@router.get("/admin/health")
async def system_health(db: Session = Depends(get_db)):
    """Получить состояние системы."""
    return get_system_health(db)

@router.post("/admin/heal")
async def heal_system(db: Session = Depends(get_db)):
    """Проверить и починить нарушения инвариантов."""
    return check_and_heal_conversations(db)
```

### Критерии готовности:
- [ ] GET /admin/health работает
- [ ] POST /admin/heal работает

---

## ПОРЯДОК ВЫПОЛНЕНИЯ

1. **result.py** — базовый класс
2. **state_service.py** — транзакционные переходы
3. **health_service.py** — self-healing
4. **SQL миграция** — constraint
5. **Рефакторинг webhook.py и telegram_webhook.py**
6. **Health endpoints**

---

## ПРОВЕРКА ЗАВЕРШЕНИЯ

```bash
cd truffles-api

# 1. Тесты
pytest tests/ -v

# 2. Линтер
ruff check .

# 3. Health endpoint
curl http://localhost:8000/admin/health
```

---

## ПОСЛЕ ЗАВЕРШЕНИЯ

1. Запустить все проверки
2. Сообщить архитектору результат

---

*Создано: 2025-12-12*
*Архитектор: truffles-architect*
*Спека: SPECS/ARCHITECTURE.md ЧАСТЬ 10*
