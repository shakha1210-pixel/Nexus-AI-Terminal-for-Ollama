import json
from pathlib import Path
from threading import RLock

from app.providers.policy import ProviderSwitchPolicy
from app.schemas.providers import ProviderPolicyUpdate


class ProviderPolicyService:
    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or (Path(__file__).resolve().parents[2] / ".nexus" / "provider_policy.json")
        self._lock = RLock()
        self._policy = self._load()

    @staticmethod
    def _to_policy(config: ProviderPolicyUpdate) -> ProviderSwitchPolicy:
        return ProviderSwitchPolicy(
            mode=config.mode,
            max_switches_per_request=config.max_switches_per_request,
            allowed_transitions={key: tuple(value) for key, value in config.allowed_transitions.items()},
            exception_allowlist=frozenset(config.exception_allowlist),
            retry_limit=config.retry_limit,
            cooldown_seconds=config.cooldown_seconds,
            require_confirmation=config.require_confirmation,
        )

    def _load(self) -> ProviderPolicyUpdate:
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
            return ProviderPolicyUpdate.model_validate(payload)
        except FileNotFoundError:
            return ProviderPolicyUpdate()
        except (OSError, ValueError):
            # A corrupt settings file must not enable automatic switching.
            return ProviderPolicyUpdate()

    def snapshot(self) -> dict:
        with self._lock:
            return self._policy.model_dump(mode="json") | {"updated": False}

    def update(self, config: ProviderPolicyUpdate) -> dict:
        policy = self._to_policy(config)
        payload = config.model_dump(mode="json")
        with self._lock:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.store_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.store_path)
            self._policy = config
        return payload | {"updated": True}

    def runtime_policy(self) -> ProviderSwitchPolicy:
        with self._lock:
            return self._to_policy(self._policy)


provider_policy_service = ProviderPolicyService()
