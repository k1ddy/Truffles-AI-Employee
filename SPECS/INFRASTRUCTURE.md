# ИНФРАСТРУКТУРА И КАЧЕСТВО

**Статус:** CANON  
**Owner:** Top Architect  
**Обновлено:** 2026-01-15  
**Scope:** инфраструктура, безопасность, тесты, CI/CD, мониторинг.  
**Out of scope:** продуктовые обещания, бизнес‑политики.  
**Links:** `SPECS/ARCHITECTURE.md`, `SPECS/SYSTEM_REFERENCE.md`, `TECH.md`, `STATE.md`.

**Источник правды по требованиям инфраструктуры/качества. Статус и evidence — только в `STATE.md` (см. `docs/TECH_STATUS.md`).**  
**Создано:** 2025-12-11

---

## СТАТУС (DERIVED, НЕ ИСТОЧНИК ИСТИНЫ)

_Исторический снимок. Актуальный статус и evidence — в `STATE.md`/`docs/TECH_STATUS.md`._

| Область | Статус |
|---------|--------|
| Секреты | ✅ В .env (2025-12-12) |
| Бэкапы БД | ✅ Cron ежедневно 3:00 (2025-12-12) |
| Бэкапы Qdrant | ✅ Cron воскресенье 4:00 (2025-12-12) |
| Алерты | ✅ Telegram сервис готов (2025-12-12) |
| Тесты | ❌ НЕТ |
| CI/CD | ❌ НЕТ |
| Логирование | ⚠️ print() |
| Мониторинг | ❌ НЕТ |

---

# ЧАСТЬ 1: ТЕКУЩЕЕ СОСТОЯНИЕ (DERIVED)

_Раздел‑снимок. Канон требований — ниже; статус и evidence — в `STATE.md`._

## Что хорошо

- ✅ Архитектура правильная (разделение ответственности)
- ✅ State machine есть
- ✅ Спеки документированы
- ✅ Git используется
- ✅ HTTPS через Traefik
- ✅ Docker для деплоя

## Что плохо (технический долг)

| Проблема | Риск | Приоритет |
|----------|------|-----------|
| API ключи в коде | Утечка при push | P0 |
| Нет бэкапов | Потеря всех данных | P0 |
| Нет тестов | Сломать и не заметить | P1 |
| Деплой руками (SCP) | Ошибки, забыть шаг | P1 |
| Логи через print() | Не найти проблему | P1 |
| Нет алертов | Узнать от клиента | P1 |

---

# ЧАСТЬ 2: БЕЗОПАСНОСТЬ

## Секреты [P0 — КРИТИЧНО]

### Текущее состояние

```python
# ai_service.py — ПЛОХО!
OPENAI_API_KEY = "sk-proj-..."  # В коде!
```

### Целевое состояние

```python
# ai_service.py — ХОРОШО
import os
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
```

```bash
# .env (НЕ в git!)
OPENAI_API_KEY=sk-proj-...
TELEGRAM_BOT_TOKEN=...
QDRANT_API_KEY=...
DATABASE_URL=postgresql://...
```

### Шаги реализации

1. Создать `.env` файл на сервере
2. Добавить `.env` в `.gitignore`
3. Заменить хардкод на `os.environ`
4. Обновить `/home/zhan/infrastructure/docker-compose.truffles.yml` — `env_file: .env`
5. Проверить что в git нет секретов: `git log -p | grep -i "sk-proj\|password\|token"`

### Список секретов для выноса

| Секрет | Где сейчас | Файл |
|--------|------------|------|
| OPENAI_API_KEY | В коде | ai_service.py |
| TELEGRAM_BOT_TOKEN | В БД (ок) | client_settings |
| QDRANT_API_KEY | В коде | knowledge_service.py |
| DATABASE_URL | docker-compose | /home/zhan/infrastructure/docker-compose.truffles.yml |
| BGE_M3_URL | В коде | knowledge_service.py |

---

# ЧАСТЬ 3: БЭКАПЫ [P0 — КРИТИЧНО]

## Что бэкапить

| Данные | Где | Критичность |
|--------|-----|-------------|
| PostgreSQL | Сервер | КРИТИЧНО — все данные |
| Qdrant | Сервер | ВЫСОКО — база знаний |
| .env | Сервер | ВЫСОКО — секреты |
| Код | GitHub | ОК — уже есть |

## PostgreSQL бэкап

### Скрипт

```bash
#!/bin/bash
# /home/zhan/scripts/backup_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/zhan/backups/postgres"
CONTAINER="truffles_postgres_1"

mkdir -p $BACKUP_DIR

# Создать бэкап
docker exec $CONTAINER pg_dump -U "$DB_USER" chatbot | gzip > "$BACKUP_DIR/chatbot_$DATE.sql.gz"

# Удалить старые (оставить 7 дней)
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup created: chatbot_$DATE.sql.gz"
```

### Cron

```bash
# crontab -e
0 3 * * * /home/zhan/scripts/backup_db.sh >> /home/zhan/logs/backup.log 2>&1
```

### Восстановление

```bash
gunzip -c chatbot_20251211.sql.gz | docker exec -i truffles_postgres_1 psql -U "$DB_USER" -d chatbot
```

## Qdrant бэкап

```bash
# Создать snapshot
curl -X POST "http://localhost:6333/collections/truffles_knowledge/snapshots"

# Скопировать
cp /var/lib/qdrant/snapshots/truffles_knowledge/* /home/zhan/backups/qdrant/
```

---

# ЧАСТЬ 4: ТЕСТИРОВАНИЕ [P1]

## Уровни тестов

| Уровень | Что тестирует | Нужно сейчас |
|---------|---------------|--------------|
| Unit | Отдельные функции | ✅ Да |
| Integration | Сервисы вместе | ⚠️ Частично |
| E2E | Весь путь сообщения | ❌ Позже |

## Минимальный набор тестов

### Unit тесты (первые)

```python
# tests/test_state_machine.py

def test_bot_active_to_pending():
    assert can_transition(BOT_ACTIVE, PENDING) == True

def test_bot_active_to_manager_active():
    assert can_transition(BOT_ACTIVE, MANAGER_ACTIVE) == False

def test_invalid_transition_raises():
    with pytest.raises(InvalidTransitionError):
        transition(BOT_ACTIVE, MANAGER_ACTIVE)
```

```python
# tests/test_intent_service.py

def test_greeting_intent():
    assert classify_intent("привет") == Intent.GREETING

def test_human_request_intent():
    assert classify_intent("позовите менеджера") == Intent.HUMAN_REQUEST
```

```python
# tests/test_result.py

def test_result_success():
    r = Result.success(42)
    assert r.ok == True
    assert r.value == 42

def test_result_failure():
    r = Result.failure("error", "test_error")
    assert r.ok == False
    assert r.error == "error"

def test_unwrap_or():
    r = Result.failure("error")
    assert r.unwrap_or(0) == 0
```

### Integration тесты (потом)

```python
# tests/test_message_flow.py

def test_message_creates_response(db_session, mock_llm):
    # Arrange
    client = create_test_client(db_session)
    user = create_test_user(db_session)
    
    # Act
    response = process_message(db_session, client.id, user.id, "привет")
    
    # Assert
    assert response is not None
    assert "помочь" in response.lower()
```

### Запуск тестов

```bash
# Локально
cd truffles-api
pytest tests/ -v

# В CI
pytest tests/ --cov=app --cov-report=html
```

---

# ЧАСТЬ 5: CI/CD [P1]

## GitHub Actions

### Файл workflow

```yaml
# .github/workflows/ci.yml

name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  IMAGE_NAME: ghcr.io/k1ddy/truffles-ai-employee

permissions:
  contents: read
  packages: write

jobs:
  lint-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: truffles-api
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: truffles-api/requirements.txt
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov ruff
      
      - name: Lint
        run: ruff check app tests
      
      - name: Run tests
        run: pytest tests/ -q

  build-push:
    if: github.ref == 'refs/heads/main'
    needs: lint-test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.repository_owner }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build metadata
        id: meta
        run: echo "build_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$GITHUB_OUTPUT"
      
      - name: Build and push image
        uses: docker/build-push-action@v6
        with:
          context: ./truffles-api
          file: ./truffles-api/Dockerfile
          push: true
          tags: |
            ${{ env.IMAGE_NAME }}:main
            ${{ env.IMAGE_NAME }}:sha-${{ github.sha }}
          build-args: |
            APP_VERSION=main
            GIT_COMMIT=${{ github.sha }}
            BUILD_TIME=${{ steps.meta.outputs.build_time }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    if: github.ref == 'refs/heads/main' && secrets.SSH_PRIVATE_KEY != '' && secrets.SERVER_HOST != '' && secrets.SERVER_USER != '' && secrets.SERVER_PORT != ''
    needs: build-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          port: ${{ secrets.SERVER_PORT }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            IMAGE_NAME=${{ env.IMAGE_NAME }}:main PULL_IMAGE=1 bash ~/restart_api.sh
```

### Секреты в GitHub

Для CI тестов секреты не нужны. Для deploy через SSH:
- `SERVER_HOST`
- `SERVER_USER`
- `SERVER_PORT`
- `SSH_PRIVATE_KEY`

---

# ЧАСТЬ 6: ЛОГИРОВАНИЕ [P1]

## Текущее (плохо)

```python
print(f"Knowledge search error: {e}")  # Теряется, нет контекста
```

## Целевое (хорошо)

```python
import logging

logger = logging.getLogger(__name__)

logger.error(
    "Knowledge search failed",
    extra={
        "client_id": str(client_id),
        "query": query[:50],
        "error": str(e)
    },
    exc_info=True
)
```

### Конфигурация

```python
# app/logging_config.py

import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": "truffles-api",
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
```

---

# ЧАСТЬ 7: АЛЕРТЫ [P1]

## Что алертить

| Событие | Уровень | Куда |
|---------|---------|------|
| Ошибка LLM | ERROR | Telegram |
| Ошибка БД | CRITICAL | Telegram + SMS |
| Много эскалаций (>10/час) | WARNING | Telegram |
| Сервис недоступен | CRITICAL | Telegram + SMS |
| Self-healing сработал | WARNING | Telegram |

## Простой алерт в Telegram

```python
# app/services/alert_service.py

import httpx

ALERT_BOT_TOKEN = os.environ["ALERT_BOT_TOKEN"]
ALERT_CHAT_ID = os.environ["ALERT_CHAT_ID"]  # ID чата для алертов

def send_alert(level: str, message: str, context: dict = None):
    """Отправить алерт в Telegram."""
    emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🔥"}
    
    text = f"{emoji.get(level, '📢')} *{level}*\n\n{message}"
    if context:
        text += f"\n\n```\n{json.dumps(context, indent=2)}\n```"
    
    try:
        httpx.post(
            f"https://api.telegram.org/bot{ALERT_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": ALERT_CHAT_ID,
                "text": text,
                "parse_mode": "Markdown"
            },
            timeout=10
        )
    except Exception as e:
        print(f"Failed to send alert: {e}")  # Fallback to print
```

### Использование

```python
# В коде
try:
    response = llm.generate(...)
except Exception as e:
    send_alert("ERROR", f"LLM failed: {e}", {"client_id": str(client_id)})
    raise
```

---

# ЧАСТЬ 8: ROADMAP

## Неделя 1: Критичное [P0]

| # | Задача | Время | Результат |
|---|--------|-------|-----------|
| 1 | Секреты → .env | 1ч | Ключи не в git |
| 2 | Бэкап PostgreSQL | 2ч | Ежедневный бэкап |
| 3 | Бэкап Qdrant | 1ч | Еженедельный бэкап |
| 4 | Алерты в Telegram | 2ч | Узнаём о проблемах |

## Неделя 2: Качество [P1]

| # | Задача | Время | Результат |
|---|--------|-------|-----------|
| 5 | Базовые тесты | 4ч | 10-15 тестов |
| 6 | Логирование | 2ч | JSON логи |
| 7 | CI/CD | 4ч | Автодеплой |
| 8 | Линтер (ruff) | 1ч | Единый стиль |

## Неделя 3+: Функционал

После инфраструктуры — функционал из STATE.md:
- Result pattern
- Эскалация при низком RAG
- Active Learning

## При масштабе (позже)

| Когда | Что добавить |
|-------|--------------|
| >1 разработчика | Staging среда, code review |
| >100 клиентов | Мониторинг (Prometheus), трейсинг |
| >1000 сообщений/час | Масштабирование, очереди |

---

# ЧАСТЬ 9: ЧЕКЛИСТ ПЕРЕД РЕЛИЗОМ

## Обязательно (P0)

- [ ] Секреты не в коде
- [ ] Бэкапы настроены и проверены
- [ ] Алерты работают (тест отправки)
- [ ] Восстановление из бэкапа проверено

## Желательно (P1)

- [ ] Тесты проходят
- [ ] CI/CD настроен
- [ ] Логи пишутся в файл/сервис
- [ ] README актуален

## Хорошо бы (P2)

- [ ] Staging среда
- [ ] Мониторинг
- [ ] Runbook для типичных проблем

---

## СВЯЗЬ С ДРУГИМИ ДОКУМЕНТАМИ

| Документ | Что там |
|----------|---------|
| `SPECS/ARCHITECTURE.md` | Архитектура кода, Error Handling |
| `TECH.md` | Доступы, команды |
| `STATE.md` | Текущий план |

---

*Создано: 2025-12-11*
