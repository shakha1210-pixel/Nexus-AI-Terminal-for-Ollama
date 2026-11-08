from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Any

import httpx


@dataclass
class ProviderState:
    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    last_error: str | None = None
    last_error_kind: str | None = None
    last_success_at: float | None = None


class ProviderCooldownError(RuntimeError):
    def __init__(self, provider_id: str, retry_after: float) -> None:
        self.provider_id = provider_id
        self.retry_after = max(0.0, retry_after)
        super().__init__(f"Provider '{provider_id}' is cooling down for {self.retry_after:.1f}s.")


class ProviderResilienceService:
    """Per-provider circuit state. Uses monotonic time and never sleeps inside requests."""

    def __init__(self, *, base_cooldown: float = 5.0, max_cooldown: float = 120.0, failure_threshold: int = 2) -> None:
        if base_cooldown < 0 or max_cooldown < base_cooldown or failure_threshold < 1:
            raise ValueError("Invalid provider resilience configuration.")
        self.base_cooldown = base_cooldown
        self.max_cooldown = max_cooldown
        self.failure_threshold = failure_threshold
        self._states: dict[str, ProviderState] = {}
        self._lock = RLock()

    def _state(self, provider_id: str) -> ProviderState:
        return self._states.setdefault(provider_id, ProviderState())

    def before_request(self, provider_id: str) -> None:
        with self._lock:
            remaining = self._state(provider_id).cooldown_until - monotonic()
        if remaining > 0:
            raise ProviderCooldownError(provider_id, remaining)

    @staticmethod
    def classify(exc: BaseException) -> tuple[str, bool, float | None]:
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            if status == 429:
                raw = exc.response.headers.get("Retry-After")
                try:
                    retry_after = min(3600.0, max(0.0, float(raw))) if raw else None
                except ValueError:
                    retry_after = None
                return "rate_limit", True, retry_after
            if status in (401, 403):
                return "authentication", False, None
            if status >= 500:
                return "server_error", True, None
            return "http_error", False, None
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
            return "timeout", True, None
        if isinstance(exc, httpx.NetworkError):
            return "network_error", True, None
        return "unknown", False, None

    def record_success(self, provider_id: str) -> None:
        with self._lock:
            state = self._state(provider_id)
            state.consecutive_failures = 0
            state.cooldown_until = 0.0
            state.last_error = None
            state.last_error_kind = None
            state.last_success_at = monotonic()

    def record_failure(self, provider_id: str, exc: BaseException) -> None:
        kind, transient, retry_after = self.classify(exc)
        with self._lock:
            state = self._state(provider_id)
            state.consecutive_failures += 1
            state.last_error_kind = kind
            state.last_error = type(exc).__name__
            if not transient:
                return
            if retry_after is not None:
                duration = retry_after
            elif state.consecutive_failures >= self.failure_threshold:
                exponent = state.consecutive_failures - self.failure_threshold
                duration = min(self.max_cooldown, self.base_cooldown * (2 ** exponent))
            else:
                duration = 0.0
            if duration > 0:
                state.cooldown_until = max(state.cooldown_until, monotonic() + duration)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        now = monotonic()
        with self._lock:
            return {
                provider_id: {
                    "state": "cooldown" if state.cooldown_until > now else "available",
                    "cooldown_remaining_seconds": round(max(0.0, state.cooldown_until - now), 1),
                    "consecutive_failures": state.consecutive_failures,
                    "last_error_kind": state.last_error_kind,
                    "last_error": state.last_error,
                    "last_success": state.last_success_at is not None,
                }
                for provider_id, state in self._states.items()
            }


provider_resilience_service = ProviderResilienceService()
