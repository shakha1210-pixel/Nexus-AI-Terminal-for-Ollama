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
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(provider: str) -> None:
            if provider in visiting:
                raise ValueError("Provider switching paths cannot contain cycles.")
            if provider in visited:
                return
            visiting.add(provider)
            for target in self.allowed_transitions.get(provider, []):
                visit(target)
            visiting.remove(provider)
            visited.add(provider)

        for provider in self.allowed_transitions:
            visit(provider)
        return self


class ProviderPolicySnapshot(ProviderPolicyUpdate):
    updated: bool = False
