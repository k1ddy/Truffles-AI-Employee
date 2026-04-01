"""
Truffles Result Contract

Result pattern для безопасной обработки успехов и ошибок.
Все сервисы должны возвращать Result вместо исключений.
"""

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from app.contracts.errors import TrufflesError

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class Result(Generic[T]):
    """
    Результат операции: успех с данными или ошибка.
    
    Usage:
        result = chatflow_service.send_message(...)
        if result.is_ok():
            msg_id = result.unwrap()
        else:
            log_error(result.error)
    """
    
    _success: bool
    _data: T | None = None
    _error: TrufflesError | None = None
    
    @classmethod
    def ok(cls, data: T) -> "Result[T]":
        """Создать успешный результат."""
        return cls(_success=True, _data=data)
    
    @classmethod
    def fail(cls, error: TrufflesError) -> "Result[T]":
        """Создать результат с ошибкой."""
        return cls(_success=False, _error=error)
    
    def is_ok(self) -> bool:
        """Проверить успешность."""
        return self._success
    
    def is_err(self) -> bool:
        """Проверить наличие ошибки."""
        return not self._success
    
    def unwrap(self) -> T:
        """Получить данные или выбросить исключение."""
        if not self._success:
            raise self._error or Exception("Result is error but no error provided")
        return self._data  # type: ignore
    
    def unwrap_or(self, default: T) -> T:
        """Получить данные или вернуть значение по умолчанию."""
        return self._data if self._success else default
    
    def unwrap_or_else(self, fn: Callable[[TrufflesError], T]) -> T:
        """Получить данные или вычислить значение из ошибки."""
        if self._success:
            return self._data  # type: ignore
        return fn(self._error)  # type: ignore
    
    @property
    def data(self) -> T | None:
        """Данные (None если ошибка)."""
        return self._data
    
    @property
    def error(self) -> TrufflesError | None:
        """Ошибка (None если успех)."""
        return self._error
    
    def map(self, fn: Callable[[T], U]) -> "Result[U]":
        """Трансформировать данные если успех."""
        if self._success:
            return Result.ok(fn(self._data))  # type: ignore
        return Result.fail(self._error)  # type: ignore
    
    def map_err(self, fn: Callable[[TrufflesError], TrufflesError]) -> "Result[T]":
        """Трансформировать ошибку если неуспех."""
        if not self._success:
            return Result.fail(fn(self._error))  # type: ignore
        return self
    
    def and_then(self, fn: Callable[[T], "Result[U]"]) -> "Result[U]":
        """Chain результатов (flatMap)."""
        if self._success:
            return fn(self._data)  # type: ignore
        return Result.fail(self._error)  # type: ignore
    
    def to_dict(self) -> dict[str, Any]:
        """Сериализация для API/логов."""
        if self._success:
            return {"success": True, "data": self._data}
        return {"success": False, "error": self._error.to_dict() if self._error else None}


# Хелперы для удобства
def Ok(data: T) -> Result[T]:
    """Shorthand для Result.ok()."""
    return Result.ok(data)


def Err(error: TrufflesError) -> Result[Any]:
    """Shorthand для Result.fail()."""
    return Result.fail(error)
