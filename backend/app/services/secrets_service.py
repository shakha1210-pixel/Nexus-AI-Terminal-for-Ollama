import sys

SERVICE_NAME = "NEXUS AI"
ALLOWED_SECRET_NAMES = frozenset({
    "kaggle-key",
    "tunnel-password",
    "openai-compatible-api-key",
})


class SecretsService:
    """Fail-closed wrapper around the OS credential store."""

    @staticmethod
    def _keyring():
        if sys.platform != "win32":
            raise RuntimeError("Credential Manager secrets are available in the Windows desktop app.")
        import keyring
        backend = keyring.get_keyring()
        backend_name = f"{backend.__class__.__module__}.{backend.__class__.__name__}"
        if "Windows" not in backend_name:
            raise RuntimeError("Windows Credential Manager backend is unavailable; refusing insecure storage.")
        return keyring

    def set(self, name: str, value: str) -> None:
        self._validate_name(name)
        if not value or len(value) > 8192:
            raise ValueError("Secret must contain 1–8192 characters.")
        self._keyring().set_password(SERVICE_NAME, name, value)

    def get(self, name: str) -> str | None:
        self._validate_name(name)
        try:
            return self._keyring().get_password(SERVICE_NAME, name)
        except RuntimeError:
            return None

    def delete(self, name: str) -> bool:
        self._validate_name(name)
        keyring = self._keyring()
        try:
            keyring.delete_password(SERVICE_NAME, name)
            return True
        except keyring.errors.PasswordDeleteError:
            return False

    def status(self) -> dict[str, bool]:
        return {name: self.get(name) is not None for name in sorted(ALLOWED_SECRET_NAMES)}

    @staticmethod
    def _validate_name(name: str) -> None:
        if name not in ALLOWED_SECRET_NAMES:
            raise ValueError("Unsupported credential name.")


secrets_service = SecretsService()
