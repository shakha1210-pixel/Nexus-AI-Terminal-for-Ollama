import unittest
from unittest.mock import AsyncMock

from app.services.ollama_service import OllamaService


class OllamaServiceStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_accepts_valid_version_payload(self) -> None:
        service = OllamaService()
        service._get = AsyncMock(return_value={"version": "0.5.0"})  # type: ignore[method-assign]

        result = await service.get_status()

        self.assertTrue(result["connected"])
        self.assertEqual(result["version"], "0.5.0")

    async def test_status_rejects_non_object_payload(self) -> None:
        service = OllamaService()
        service._get = AsyncMock(return_value=["unexpected"])  # type: ignore[method-assign]

        result = await service.get_status()

        self.assertFalse(result["connected"])
        self.assertIsNone(result["version"])
        self.assertIn("formatda emas", result["message"])

    async def test_status_rejects_missing_version(self) -> None:
        service = OllamaService()
        service._get = AsyncMock(return_value={})  # type: ignore[method-assign]

        result = await service.get_status()

        self.assertFalse(result["connected"])
        self.assertIsNone(result["version"])


class OllamaRuntimeModeTests(unittest.TestCase):
    def test_runtime_starts_in_local_mode(self) -> None:
        from app.config import settings

        service = OllamaService()

        self.assertEqual(service.mode, "local")
        self.assertEqual(service.base_url, settings.ollama_base_url.rstrip("/"))
        self.assertIsNone(service.auth)

    def test_runtime_can_switch_remote_and_back_to_local(self) -> None:
        service = OllamaService()
        local_url = service.local_base_url

        service.use_remote("https://runtime.example/ollama/", ("nexus", "test-secret"))
        self.assertEqual(service.mode, "kaggle")
        self.assertEqual(service.base_url, "https://runtime.example/ollama")
        self.assertEqual(service.auth, ("nexus", "test-secret"))

        service.use_local()
        self.assertEqual(service.mode, "local")
        self.assertEqual(service.base_url, local_url)
        self.assertIsNone(service.auth)



if __name__ == "__main__":
    unittest.main()
