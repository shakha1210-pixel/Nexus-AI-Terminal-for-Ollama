from __future__ import annotations

from threading import RLock
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


class LazyService(Generic[T]):
    """Thread-safe service holder that defers construction until startup or first use."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._instance: T | None = None
        self._lock = RLock()

    def initialize(self) -> T:
        if self._instance is None:
            with self._lock:
                if self._instance is None:
                    self._instance = self._factory()
        return self._instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self.initialize(), name)
