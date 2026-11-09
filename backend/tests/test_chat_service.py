import tempfile
import unittest
from pathlib import Path

from app.services.chat_service import ChatError, ChatService


class ChatServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.service = ChatService(Path(self.temp_dir.name))

    def test_conversation_history_round_trip(self) -> None:
        conversation = {
            "id": "a" * 32,
            "title": "NEXUS test",
            "created_at": "2026-11-09T00:00:00+00:00",
            "updated_at": "2026-11-09T00:00:00+00:00",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        self.service._write(conversation)
        self.assertEqual(self.service.get_conversation("a" * 32)["messages"][0]["content"], "Hello")
        self.assertEqual(self.service.list_conversations()[0]["message_count"], 1)
        self.service.delete_conversation("a" * 32)
        with self.assertRaises(ChatError):
            self.service.get_conversation("a" * 32)

    def test_rejects_invalid_conversation_id(self) -> None:
        with self.assertRaises(ChatError):
            self.service.get_conversation("../outside")


if __name__ == "__main__":
    unittest.main()
