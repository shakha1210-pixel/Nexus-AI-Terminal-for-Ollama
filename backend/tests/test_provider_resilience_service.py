import unittest
from time import monotonic

import httpx

from app.services.provider_resilience_service import (
    ProviderCooldownError,
    ProviderResilienceService,
)


class ProviderResilienceServiceTests(unittest.TestCase):
    def test_first_transient_failure_does_not_lock_provider(self):
        service = ProviderResilienceService(base_cooldown=2, max_cooldown=8, failure_threshold=2)
        service.record_failure("ollama", httpx.ConnectError("offline"))
        service.before_request("ollama")

    def test_repeated_transient_failures_enter_bounded_cooldown(self):
        service = ProviderResilienceService(base_cooldown=2, max_cooldown=4, failure_threshold=2)
        error = httpx.ConnectError("offline")
        service.record_failure("ollama", error)
        service.record_failure("ollama", error)
        with self.assertRaises(ProviderCooldownError) as caught:
            service.before_request("ollama")
        self.assertGreater(caught.exception.retry_after, 0)
        self.assertLessEqual(caught.exception.retry_after, 2)

    def test_rate_limit_honors_numeric_retry_after(self):
        service = ProviderResilienceService(base_cooldown=2, max_cooldown=4)
        request = httpx.Request("POST", "https://provider.test")
        response = httpx.Response(429, headers={"Retry-After": "7"}, request=request)
        service.record_failure("openai-compatible", httpx.HTTPStatusError("limited", request=request, response=response))
        with self.assertRaises(ProviderCooldownError) as caught:
            service.before_request("openai-compatible")
        self.assertGreater(caught.exception.retry_after, 6)
        self.assertLessEqual(caught.exception.retry_after, 7)

    def test_authentication_failure_does_not_start_cooldown(self):
        service = ProviderResilienceService(base_cooldown=2, max_cooldown=4)
        request = httpx.Request("POST", "https://provider.test")
        response = httpx.Response(401, request=request)
        service.record_failure("openai-compatible", httpx.HTTPStatusError("unauthorized", request=request, response=response))
        service.before_request("openai-compatible")

    def test_only_one_recovery_probe_can_run_after_cooldown(self):
        service = ProviderResilienceService(base_cooldown=2, max_cooldown=4, failure_threshold=1)
        service.record_failure("ollama", httpx.ConnectError("offline"))
        service._states["ollama"].cooldown_until = monotonic() - 0.1
        self.assertTrue(service.begin_recovery_probe("ollama"))
        self.assertFalse(service.begin_recovery_probe("ollama"))
        with self.assertRaises(ProviderCooldownError):
            service.before_request("ollama")
        service.record_success("ollama")
        service.before_request("ollama")

    def test_cancelled_probe_can_be_released_without_sticking_circuit(self):
        service = ProviderResilienceService(base_cooldown=2, max_cooldown=4, failure_threshold=1)
        service.record_failure("ollama", httpx.ConnectError("offline"))
        service._states["ollama"].cooldown_until = monotonic() - 0.1
        self.assertTrue(service.begin_recovery_probe("ollama"))
        service.release_probe("ollama")
        self.assertTrue(service.begin_recovery_probe("ollama"))

    def test_success_resets_failure_state_and_cooldown(self):
        service = ProviderResilienceService(base_cooldown=2, max_cooldown=4, failure_threshold=1)
        service.record_failure("ollama", httpx.ConnectError("offline"))
        service.record_success("ollama")
        service.before_request("ollama")
        state = service.snapshot()["ollama"]
        self.assertEqual(state["state"], "available")
        self.assertEqual(state["consecutive_failures"], 0)


if __name__ == "__main__":
    unittest.main()
