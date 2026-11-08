import unittest

from app.providers.adapters.ollama import OllamaAdapter
from app.providers.adapters.openai_compatible import OpenAICompatibleAdapter


class ProviderAdapterNormalizationTests(unittest.TestCase):
    def test_openai_tool_call_arguments_are_normalized(self):
        message = OpenAICompatibleAdapter._normalize_message({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_123",
                "function": {"name": "workspace_read_file", "arguments": '{"path":"README.md"}'},
            }],
        })
        self.assertEqual(message["content"], "")
        self.assertEqual(message["tool_calls"][0]["id"], "call_123")
        self.assertEqual(message["tool_calls"][0]["function"]["arguments"], {"path": "README.md"})

    def test_openai_tool_history_preserves_exact_call_id(self):
        converted = OpenAICompatibleAdapter._to_openai_messages([
            {"role": "assistant", "content": "", "tool_calls": [{
                "id": "call_abc",
                "function": {"name": "workspace_read_file", "arguments": {"path": "README.md"}},
            }]},
            {"role": "tool", "tool_name": "workspace_read_file", "tool_call_id": "call_abc", "content": "ok"},
        ])
        self.assertEqual(converted[1]["tool_call_id"], "call_abc")
        self.assertEqual(converted[0]["tool_calls"][0]["function"]["arguments"], '{"path": "README.md"}')

    def test_ollama_adapter_follows_runtime_endpoint_and_auth(self):
        runtime = {"url": "http://127.0.0.1:11434", "auth": None}
        adapter = OllamaAdapter(
            base_url=lambda: runtime["url"],
            auth=lambda: runtime["auth"],
            provider_id="ollama",
        )
        self.assertEqual(adapter.base_url, "http://127.0.0.1:11434")
        self.assertIsNone(adapter.auth)
        runtime["url"] = "https://remote.example"
        runtime["auth"] = ("nexus", "secret")
        self.assertEqual(adapter.base_url, "https://remote.example")
        self.assertEqual(adapter.auth, ("nexus", "secret"))

    def test_ollama_adapter_removes_openai_only_tool_metadata(self):
        adapter = OllamaAdapter("http://127.0.0.1:11434")
        messages = [{
            "role": "tool", "tool_name": "workspace_read_file",
            "tool_call_id": "call_abc", "content": "ok",
        }]
        # The native adapter only serializes fields understood by Ollama's chat schema.
        sanitized = [{key: value for key, value in message.items()
                      if key in ("role", "content", "images", "tool_name", "tool_calls")}
                     for message in messages]
        self.assertNotIn("tool_call_id", sanitized[0])
        self.assertEqual(sanitized[0]["tool_name"], "workspace_read_file")


if __name__ == "__main__":
    unittest.main()
