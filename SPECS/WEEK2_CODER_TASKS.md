# НЕДЕЛЯ 2: Качество кода — Задачи для кодера

**Архитектор:** Готово к выполнению
**Приоритет:** P1
**Ссылка:** `SPECS/INFRASTRUCTURE.md`

---

## КОНТЕКСТ

Неделя 1 завершена: секреты в .env, бэкапы настроены, alert_service.py создан.

Неделя 2: улучшение качества кодовой базы для надёжности и масштабирования.

**Текущее состояние:**
- 46 `print()` в коде → нужно заменить на logging
- alert_service.py готов, но не интегрирован
- 7 тестовых файлов есть, нужно проверить и добавить
- CI/CD нет, линтера нет

---

## ЗАДАЧА 1: Линтер (ruff)

**Время:** ~15 мин

### Что сделать:
1. Создать `truffles-api/pyproject.toml`
2. Настроить ruff

### Конфиг pyproject.toml:
```toml
[project]
name = "truffles-api"
version = "1.0.0"
requires-python = ">=3.11"

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I"]
ignore = ["E501"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

### Проверка:
```bash
cd truffles-api
pip install ruff
ruff check .
ruff format . --check
```

### Критерии готовности:
- [ ] pyproject.toml создан
- [ ] `ruff check .` проходит без критических ошибок
- [ ] Код отформатирован

---

## ЗАДАЧА 2: Логирование (JSON)

**Время:** ~30 мин

### Что сделать:
1. Создать `truffles-api/app/logging_config.py`
2. Импортировать в `main.py`
3. Заменить все `print()` на `logging`

### Файл logging_config.py:
```python
import logging
import json
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "context"):
            log_obj["context"] = record.context
        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging(level: str = "INFO"):
    """Configure JSON logging for the application."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper()))
    root.handlers = [handler]
    
    # Suppress noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(f"truffles.{name}")
```

### В main.py добавить:
```python
from app.logging_config import setup_logging

setup_logging()
```

### Замена print() на logging:
| Тип | Когда | Пример |
|-----|-------|--------|
| `logger.debug()` | Отладка, подробности | LLM responses, Qdrant results |
| `logger.info()` | Нормальные события | "Webhook received", "Message saved" |
| `logger.warning()` | Проблемы без фейла | "No prompt found", "Topic not found" |
| `logger.error()` | Ошибки | Exceptions, API errors |

### Файлы для изменения:
- `app/services/ai_service.py` — 10 print()
- `app/services/escalation_service.py` — 6 print()
- `app/services/chatflow_service.py` — 5 print()
- `app/services/llm/openai_provider.py` — 7 print()
- `app/routers/webhook.py` — 9 print()
- `app/routers/telegram_webhook.py` — 3 print()
- И другие (см. grep "print(" в app/)

### Критерии готовности:
- [ ] logging_config.py создан
- [ ] main.py импортирует setup_logging()
- [ ] 0 `print()` в app/ (кроме alert_service.py fallback)
- [ ] Логи выводятся в JSON формате

---

## ЗАДАЧА 3: Интеграция alert_service.py

**Время:** ~15 мин

### Что сделать:
Вызывать `alert_error()` / `alert_critical()` в критических местах.

### Где добавить:

**ai_service.py** (строка ~128):
```python
from app.services.alert_service import alert_error

except Exception as e:
    logger.error(f"AI generation error: {e}")
    alert_error("AI generation failed", {"error": str(e), "client_id": str(client_id)})
    return "Извините, произошла ошибка. Попробуйте позже."
```

**chatflow_service.py** (строка ~46):
```python
from app.services.alert_service import alert_critical

except Exception as e:
    logger.error(f"WhatsApp send error: {e}")
    alert_critical("WhatsApp message failed", {"error": str(e), "client_id": str(client_id)})
```

**escalation_service.py** (строка ~156):
```python
from app.services.alert_service import alert_error

if not result.get("ok"):
    logger.error(f"Telegram send error: {result}")
    alert_error("Telegram send failed", {"result": str(result)})
```

**knowledge_service.py** (строка ~60):
```python
from app.services.alert_service import alert_warning

if response.status_code != 200:
    logger.error(f"Qdrant error: {response.status_code}")
    alert_warning("Qdrant search failed", {"status": response.status_code})
```

### Критерии готовности:
- [ ] alert_error() вызывается при ошибках AI
- [ ] alert_critical() вызывается при невозможности отправить WhatsApp
- [ ] alert_error() вызывается при ошибках Telegram
- [ ] alert_warning() вызывается при ошибках Qdrant

---

## ЗАДАЧА 4: CI/CD (GitHub Actions)

**Время:** ~20 мин

### Что сделать:
Создать `.github/workflows/ci.yml`

### Файл ci.yml:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    
    defaults:
      run:
        working-directory: truffles-api
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install ruff pytest
      
      - name: Lint with ruff
        run: ruff check .
      
      - name: Run tests
        run: pytest --tb=short -q
        env:
          OPENAI_API_KEY: "test-key"
          DATABASE_URL: "sqlite:///:memory:"
```

### Критерии готовности:
- [ ] .github/workflows/ci.yml создан
- [ ] CI запускается на push и PR
- [ ] ruff check проходит
- [ ] pytest запускается (даже если тесты пропускаются)

---

## ЗАДАЧА 5: Тесты

**Время:** ~40 мин

### Существующие тесты (проверить что работают):
```
tests/test_callback.py
tests/test_telegram_webhook.py
tests/test_state_machine.py
tests/test_reminders.py
tests/test_message_endpoint.py
tests/test_intent.py
tests/test_escalation.py
```

### Что сделать:
1. Запустить существующие тесты
2. Исправить если падают
3. Добавить недостающие

### Добавить tests/test_ai_service.py:
```python
import pytest
from unittest.mock import Mock, patch
from app.services.ai_service import (
    get_system_prompt,
    get_conversation_history,
    generate_ai_response,
    KNOWLEDGE_CONFIDENCE_THRESHOLD
)


class TestKnowledgeConfidence:
    def test_threshold_is_0_7(self):
        assert KNOWLEDGE_CONFIDENCE_THRESHOLD == 0.7
    
    @patch("app.services.ai_service.search_knowledge")
    @patch("app.services.ai_service.get_llm_provider")
    def test_low_confidence_triggers_escalation_message(
        self, mock_llm, mock_search, db_session
    ):
        # Mock low confidence results
        mock_search.return_value = [{"score": 0.5, "text": "test"}]
        mock_llm.return_value.generate.return_value = Mock(content="Test response")
        
        # Should include escalation instruction in prompt
        # (verify through mock calls)
```

### Добавить tests/test_alert_service.py:
```python
import pytest
from unittest.mock import patch, Mock
from app.services.alert_service import send_alert, alert_error


class TestAlertService:
    @patch("app.services.alert_service.ALERT_BOT_TOKEN", "test-token")
    @patch("app.services.alert_service.ALERT_CHAT_ID", "test-chat")
    @patch("app.services.alert_service.httpx.Client")
    def test_send_alert_success(self, mock_client):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        result = send_alert("ERROR", "Test message")
        assert result is True
    
    @patch("app.services.alert_service.ALERT_BOT_TOKEN", None)
    def test_send_alert_not_configured(self):
        result = send_alert("ERROR", "Test message")
        assert result is False
```

### Добавить tests/conftest.py (если нет):
```python
import pytest
from unittest.mock import Mock


@pytest.fixture
def db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_env(monkeypatch):
    """Set test environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
```

### Критерии готовности:
- [ ] Все существующие тесты проходят
- [ ] test_ai_service.py создан (минимум 3 теста)
- [ ] test_alert_service.py создан (минимум 2 теста)
- [ ] conftest.py настроен
- [ ] `pytest` проходит без ошибок

---

## ПОРЯДОК ВЫПОЛНЕНИЯ

1. **ruff** → сначала линтер
2. **logging** → заменить print на logging
3. **alerts** → интеграция alert_service
4. **CI/CD** → GitHub Actions
5. **tests** → добавить недостающие

---

## ПРОВЕРКА ЗАВЕРШЕНИЯ

```bash
cd truffles-api

# 1. Линтер
ruff check .
ruff format . --check

# 2. Тесты
pytest --tb=short

# 3. Логи (запустить и проверить формат)
python -c "from app.logging_config import setup_logging, get_logger; setup_logging(); get_logger('test').info('Test')"

# 4. Нет print() в коде
grep -r "print(" app/ --include="*.py" | grep -v "__pycache__" | wc -l
# Должно быть 0 (или только в alert_service.py fallback)
```

---

## ПОСЛЕ ЗАВЕРШЕНИЯ

1. Запустить все проверки
2. Закоммитить: `git add . && git commit -m "Week 2: code quality (tests, logging, CI, linter)"`
3. Сообщить архитектору результат

---

*Создано: 2025-12-12*
*Архитектор: truffles-architect*
