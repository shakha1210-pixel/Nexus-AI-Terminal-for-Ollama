import unittest

from app.providers.policy import (
    FailureKind,
    ProviderSwitchPolicy,
    ProviderSwitchingEngine,
    SwitchingMode,
)


class ProviderSwitchingPolicyTests(unittest.TestCase):
    def test_default_policy_is_manual_only(self):
        engine = ProviderSwitchingEngine(ProviderSwitchPolicy())
        decision = engine.evaluate(
            source_provider="openai-compatible", failure=FailureKind.TIMEOUT, attempts=2
        )
        self.assertFalse(decision.allowed)

    def test_error_triggered_switch_requires_exhausted_retries_and_allowed_path(self):
        engine = ProviderSwitchingEngine(ProviderSwitchPolicy(
            mode=SwitchingMode.ERROR_TRIGGERED,
            retry_limit=1,
            allowed_transitions={"openai-compatible": ("ollama-kaggle",)},
        ))
        too_early = engine.evaluate(
            source_provider="openai-compatible", failure=FailureKind.TIMEOUT, attempts=1
        )
        allowed = engine.evaluate(
            source_provider="openai-compatible", failure=FailureKind.TIMEOUT, attempts=2
        )
        self.assertFalse(too_early.allowed)
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.target_provider, "ollama-kaggle")

    def test_unlisted_target_is_never_selected(self):
        engine = ProviderSwitchingEngine(ProviderSwitchPolicy(
            mode=SwitchingMode.ERROR_TRIGGERED,
            retry_limit=0,
            allowed_transitions={"provider-a": ()},
        ))
        decision = engine.evaluate(
            source_provider="provider-a", failure=FailureKind.NETWORK_ERROR, attempts=1
        )
        self.assertFalse(decision.allowed)

    def test_authentication_and_security_failures_never_fallback(self):
        engine = ProviderSwitchingEngine(ProviderSwitchPolicy(
            mode=SwitchingMode.EXCEPTION_BASED,
            retry_limit=0,
            exception_allowlist=frozenset({FailureKind.AUTHENTICATION, FailureKind.SECURITY_BLOCK}),
            allowed_transitions={"provider-a": ("provider-b",)},
        ))
        for failure in (FailureKind.AUTHENTICATION, FailureKind.SECURITY_BLOCK):
            with self.subTest(failure=failure):
                self.assertFalse(engine.evaluate(
                    source_provider="provider-a", failure=failure, attempts=1
                ).allowed)

    def test_isolation_and_pending_approval_block_switching(self):
        engine = ProviderSwitchingEngine(ProviderSwitchPolicy(
            mode=SwitchingMode.ERROR_TRIGGERED,
            retry_limit=0,
            allowed_transitions={"provider-a": ("provider-b",)},
        ))
        for state in ({"isolated": True}, {"approval_pending": True}):
            with self.subTest(state=state):
                decision = engine.evaluate(
                    source_provider="provider-a", failure=FailureKind.TIMEOUT,
                    attempts=1, **state,
                )
                self.assertFalse(decision.allowed)

    def test_stream_started_locks_switch_for_request(self):
        engine = ProviderSwitchingEngine(ProviderSwitchPolicy(
            mode=SwitchingMode.ERROR_TRIGGERED,
            retry_limit=0,
            allowed_transitions={"provider-a": ("provider-b",)},
        ))
        decision = engine.evaluate(
            source_provider="provider-a", failure=FailureKind.TIMEOUT,
            attempts=1, stream_started=True,
        )
        self.assertFalse(decision.allowed)

    def test_guided_mode_requires_confirmation(self):
        engine = ProviderSwitchingEngine(ProviderSwitchPolicy(
            mode=SwitchingMode.GUIDED,
            retry_limit=0,
            allowed_transitions={"provider-a": ("provider-b",)},
        ))
        pending = engine.evaluate(
            source_provider="provider-a", failure=FailureKind.TIMEOUT, attempts=1
        )
        self.assertTrue(pending.allowed)
        self.assertTrue(pending.requires_confirmation)
        confirmed = engine.confirm(pending)
        self.assertTrue(confirmed.allowed)
        self.assertFalse(confirmed.requires_confirmation)

    def test_invalid_policy_rejects_self_transition(self):
        with self.assertRaises(ValueError):
            ProviderSwitchPolicy(allowed_transitions={"provider-a": ("provider-a",)})


if __name__ == "__main__":
    unittest.main()
