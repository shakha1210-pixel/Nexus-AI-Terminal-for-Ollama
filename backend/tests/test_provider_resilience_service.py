import httpx
import pytest

from app.services.provider_resilience_service import (
    ProviderCooldownError,
    ProviderResilienceService,
)


def test_first_transient_failure_does_not_lock_provider():
    service = ProviderResilienceService(base_cooldown=2, max_cooldown=8, failure_threshold=2)
    service.record_failure("ollama", httpx.ConnectError("offline"))
    service.before_request("ollama")


def test_repeated_transient_failures_enter_bounded_cooldown():
    service = ProviderResilienceService(base_cooldown=2, max_cooldown=4, failure_threshold=2)
    error = httpx.ConnectError("offline")
    service.record_failure("ollama", error)
    service.record_failure("ollama", error)
    with pytest.raises(ProviderCooldownError) as caught:
        service.before_request("ollama")
    assert 0 < caught.value.retry_after <= 2


def test_rate_limit_honors_numeric_retry_after():
    service = ProviderResilienceService(base_cooldown=2, max_cooldown=4)
    request = httpx.Request("POST", "https://provider.test")
    response = httpx.Response(429, headers={"Retry-After": "7"}, request=request)
    service.record_failure("openai-compatible", httpx.HTTPStatusError("limited", request=request, response=response))
    with pytest.raises(ProviderCooldownError) as caught:
        service.before_request("openai-compatible")
    assert 6 < caught.value.retry_after <= 7


def test_authentication_failure_does_not_start_cooldown():
    service = ProviderResilienceService(base_cooldown=2, max_cooldown=4)
    request = httpx.Request("POST", "https://provider.test")
    response = httpx.Response(401, request=request)
    service.record_failure("openai-compatible", httpx.HTTPStatusError("unauthorized", request=request, response=response))
    service.before_request("openai-compatible")


def test_success_resets_failure_state_and_cooldown():
    service = ProviderResilienceService(base_cooldown=2, max_cooldown=4, failure_threshold=1)
    service.record_failure("ollama", httpx.ConnectError("offline"))
    service.record_success("ollama")
    service.before_request("ollama")
    state = service.snapshot()["ollama"]
    assert state["state"] == "available"
    assert state["consecutive_failures"] == 0
