from dataclasses import dataclass, field
from enum import Enum
from time import monotonic


class SwitchingMode(str, Enum):
    DISABLED = "disabled"
    MANUAL_ONLY = "manual_only"
    ERROR_TRIGGERED = "error_triggered"
    EXCEPTION_BASED = "exception_based"
    GUIDED = "guided"


class FailureKind(str, Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION = "authentication"
    MODEL_NOT_FOUND = "model_not_found"
    USER_CANCELLED = "user_cancelled"
    SECURITY_BLOCK = "security_block"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderSwitchPolicy:
    mode: SwitchingMode = SwitchingMode.MANUAL_ONLY
    max_switches_per_request: int = 1
    allowed_transitions: dict[str, tuple[str, ...]] = field(default_factory=dict)
    exception_allowlist: frozenset[FailureKind] = frozenset()
    retry_limit: int = 1
    cooldown_seconds: float = 0.0
    require_confirmation: bool = False
    allow_after_stream_started: bool = False

    def __post_init__(self) -> None:
        if self.max_switches_per_request < 0:
            raise ValueError("max_switches_per_request cannot be negative.")
        if self.retry_limit < 0:
            raise ValueError("retry_limit cannot be negative.")
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds cannot be negative.")
        if self.allow_after_stream_started:
            raise ValueError("Provider switching after stream start is not supported.")
        for source, targets in self.allowed_transitions.items():
            if not source or source in targets:
                raise ValueError("Transition paths must be non-empty and cannot target themselves.")
            if len(set(targets)) != len(targets):
                raise ValueError("Transition targets must be unique.")


@dataclass(frozen=True)
class SwitchDecision:
    allowed: bool
    target_provider: str | None = None
    requires_confirmation: bool = False
    reason: str = ""


class ProviderSwitchingEngine:
    """Evaluates policy only; it never executes a provider switch itself."""

    _ERROR_TRIGGERED = frozenset({
        FailureKind.TIMEOUT, FailureKind.RATE_LIMIT, FailureKind.SERVER_ERROR,
        FailureKind.NETWORK_ERROR,
    })
    _NEVER_FALLBACK = frozenset({
        FailureKind.AUTHENTICATION, FailureKind.USER_CANCELLED,
        FailureKind.SECURITY_BLOCK, FailureKind.MODEL_NOT_FOUND,
    })

    def __init__(self, policy: ProviderSwitchPolicy) -> None:
        self.policy = policy
        self._last_switch_at: float | None = None

    def evaluate(
        self,
        *,
        source_provider: str,
        failure: FailureKind,
        switches_used: int = 0,
        attempts: int = 1,
        stream_started: bool = False,
        isolated: bool = False,
        approval_pending: bool = False,
    ) -> SwitchDecision:
        if isolated or approval_pending:
            return SwitchDecision(False, reason="Agent security state blocks provider switching.")
        if stream_started:
            return SwitchDecision(False, reason="A response stream has started; switching is locked for this request.")
        if failure in self._NEVER_FALLBACK:
            return SwitchDecision(False, reason=f"Failure '{failure.value}' is not eligible for automatic fallback.")
        if self.policy.mode in (SwitchingMode.DISABLED, SwitchingMode.MANUAL_ONLY):
            return SwitchDecision(False, reason="Automatic provider switching is disabled by policy.")
        if switches_used >= self.policy.max_switches_per_request:
            return SwitchDecision(False, reason="Per-request provider switch limit reached.")
        if attempts <= self.policy.retry_limit:
            return SwitchDecision(False, reason="Configured retry limit has not been exhausted.")
        if self._last_switch_at is not None and monotonic() - self._last_switch_at < self.policy.cooldown_seconds:
            return SwitchDecision(False, reason="Provider switching is in cooldown.")

        if self.policy.mode == SwitchingMode.ERROR_TRIGGERED and failure not in self._ERROR_TRIGGERED:
            return SwitchDecision(False, reason="This failure type is not enabled for error-triggered fallback.")
        if self.policy.mode == SwitchingMode.EXCEPTION_BASED and failure not in self.policy.exception_allowlist:
            return SwitchDecision(False, reason="This failure is not in the exception allowlist.")

        targets = self.policy.allowed_transitions.get(source_provider, ())
        if not targets:
            return SwitchDecision(False, reason="No permitted transition is configured for this provider.")
        target = targets[0]
        needs_confirmation = self.policy.mode == SwitchingMode.GUIDED or self.policy.require_confirmation
        if needs_confirmation:
            return SwitchDecision(True, target, True, "Fallback is eligible and awaits user confirmation.")
        self._last_switch_at = monotonic()
        return SwitchDecision(True, target, False, "Fallback is permitted by policy.")

    def confirm(
        self, decision: SwitchDecision, *, isolated: bool = False,
        approval_pending: bool = False, stream_started: bool = False,
    ) -> SwitchDecision:
        if not decision.allowed or not decision.requires_confirmation or not decision.target_provider:
            return SwitchDecision(False, reason="There is no pending provider switch to confirm.")
        if isolated or approval_pending:
            return SwitchDecision(False, reason="Agent security state blocks provider switching.")
        if stream_started:
            return SwitchDecision(False, reason="A response stream has started; switching is locked for this request.")
        self._last_switch_at = monotonic()
        return SwitchDecision(True, decision.target_provider, False, "Provider switch confirmed.")
