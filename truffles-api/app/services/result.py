from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class Result(Generic[T]):
    ok: bool
    value: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    @staticmethod
    def success(value: T) -> "Result[T]":
        return Result(ok=True, value=value)

    @staticmethod
    def failure(error: str, code: str = "unknown") -> "Result[T]":
        return Result(ok=False, error=error, error_code=code)

    def unwrap_or(self, default: T) -> T:
        return self.value if self.ok else default
