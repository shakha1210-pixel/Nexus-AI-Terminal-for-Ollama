from pydantic import BaseModel, Field, model_validator

from app.providers.policy import FailureKind, SwitchingMode


class ProviderPolicyUpdate(BaseModel):
    mode: SwitchingMode = SwitchingMode.MANUAL_ONLY
    max_switches_per_request: int = Field(default=1, ge=0, le=5)
    allowed_transitions: dict[str, list[str]] = Field(default_factory=dict)
    exception_allowlist: list[FailureKind] = Field(default_factory=list)
    retry_limit: int = Field(default=1, ge=0, le=10)
    cooldown_seconds: float = Field(default=0.0, ge=0, le=3600)
    require_confirmation: bool = False

    @model_validator(mode="after")
    def validate_paths(self):
        for source, targets in self.allowed_transitions.items():
            if not source.strip() or any(not target.strip() for target in targets):
                raise ValueError("Provider path entries cannot be empty.")
            if source in targets or len(set(targets)) != len(targets):
                raise ValueError("Provider path cannot contain self-transitions or duplicates.")
        return self


class ProviderPolicySnapshot(ProviderPolicyUpdate):
    updated: bool = False
