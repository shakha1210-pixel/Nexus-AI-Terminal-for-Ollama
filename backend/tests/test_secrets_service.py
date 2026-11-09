import unittest
from unittest.mock import patch

from app.services.secrets_service import SecretsService


class FakeKeyring:
    values = {}

    @classmethod
    def get_keyring(cls):
        class WindowsBackend:
            __module__ = "keyring.backends.Windows"
        return WindowsBackend()

    @classmethod
    def set_password(cls, service, name, value):
        cls.values[(service, name)] = value

    @classmethod
    def get_password(cls, service, name):
        return cls.values.get((service, name))

    @classmethod
    def delete_password(cls, service, name):
        cls.values.pop((service, name), None)


class SecretServiceTests(unittest.TestCase):
    def setUp(self):
        FakeKeyring.values = {}
        self.service = SecretsService()

    def test_rejects_unknown_names(self):
        with self.assertRaises(ValueError):
            self.service.set("arbitrary", "secret")

    def test_secret_is_stored_and_status_does_not_return_value(self):
        with patch("app.services.secrets_service.sys.platform", "win32"), patch.dict("sys.modules", {"keyring": FakeKeyring}):
            self.service.set("kaggle-key", "private-value")
            self.assertEqual(self.service.get("kaggle-key"), "private-value")
            self.assertTrue(self.service.status()["kaggle-key"])
            self.assertNotIn("private-value", str(self.service.status()))

    def test_rejects_empty_secret(self):
        with patch("app.services.secrets_service.sys.platform", "win32"), patch.dict("sys.modules", {"keyring": FakeKeyring}):
            with self.assertRaises(ValueError):
                self.service.set("kaggle-key", "")


if __name__ == "__main__":
    unittest.main()
