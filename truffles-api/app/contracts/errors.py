"""
Truffles Error Contracts

Единая система ошибок для всех модулей платформы.
Каждая ошибка имеет код, сообщение и контекст для трейсинга.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrufflesError(Exception):
    """Базовая ошибка Truffles с кодом и контекстом."""
    
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Сериализация для логов и API."""
        return {
            "error_type": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "context": self.context,
        }
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


@dataclass
class ValidationError(TrufflesError):
    """Ошибка валидации входных данных."""
    pass


@dataclass
class IntegrationError(TrufflesError):
    """Ошибка интеграции с внешним сервисом (ChatFlow, Telegram, Qdrant, LLM)."""
    
    service: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        if self.service:
            self.context["service"] = self.service


@dataclass
class StateError(TrufflesError):
    """Ошибка перехода состояния (невалидный переход FSM)."""
    
    current_state: str = ""
    target_state: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        if self.current_state:
            self.context["current_state"] = self.current_state
        if self.target_state:
            self.context["target_state"] = self.target_state


@dataclass
class AuthError(TrufflesError):
    """Ошибка аутентификации/авторизации."""
    pass


@dataclass
class ConfigError(TrufflesError):
    """Ошибка конфигурации (отсутствует env, неверные настройки)."""
    pass


@dataclass
class RateLimitError(TrufflesError):
    """Превышен лимит запросов."""
    
    retry_after_seconds: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        if self.retry_after_seconds:
            self.context["retry_after_seconds"] = self.retry_after_seconds


# Предопределённые коды ошибок
class ErrorCodes:
    """Стандартные коды ошибок."""
    
    # Validation
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    
    # Integration
    CHATFLOW_TIMEOUT = "CHATFLOW_TIMEOUT"
    CHATFLOW_ERROR = "CHATFLOW_ERROR"
    TELEGRAM_ERROR = "TELEGRAM_ERROR"
    TELEGRAM_RATE_LIMIT = "TELEGRAM_RATE_LIMIT"
    QDRANT_ERROR = "QDRANT_ERROR"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_ERROR = "LLM_ERROR"
    
    # State
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    CONVERSATION_NOT_FOUND = "CONVERSATION_NOT_FOUND"
    HANDOVER_NOT_FOUND = "HANDOVER_NOT_FOUND"
    
    # Auth
    AUTH_REQUIRED = "AUTH_REQUIRED"
    ACCESS_DENIED = "ACCESS_DENIED"
    TOKEN_INVALID = "TOKEN_INVALID"
    
    # Config
    CONFIG_MISSING = "CONFIG_MISSING"
    CLIENT_NOT_FOUND = "CLIENT_NOT_FOUND"
    
    # Rate limit
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    MEDIA_LIMIT_EXCEEDED = "MEDIA_LIMIT_EXCEEDED"
