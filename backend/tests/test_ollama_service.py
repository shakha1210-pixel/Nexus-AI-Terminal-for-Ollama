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


if __name__ == "__main__":
    unittest.main()
