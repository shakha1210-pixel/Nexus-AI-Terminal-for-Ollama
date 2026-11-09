import threading
import unittest

from app.services.lazy_service import LazyService
from app.services.provider_policy_service import provider_policy_service
from app.services.provider_runtime_service import provider_runtime_service


class LazyServiceTests(unittest.TestCase):
    def test_factory_is_deferred_until_initialization(self):
        calls = []
        service = LazyService(lambda: calls.append("created") or {"ready": True})
        self.assertEqual(calls, [])
        self.assertEqual(service.initialize(), {"ready": True})
        self.assertEqual(calls, ["created"])

    def test_attribute_access_initializes_once(self):
        calls = []
        service = LazyService(lambda: calls.append("created") or type("Example", (), {"value": 42})())
        self.assertEqual(service.value, 42)
        self.assertEqual(service.value, 42)
        self.assertEqual(calls, ["created"])

    def test_concurrent_initialization_uses_one_instance(self):
        calls = []
        service = LazyService(lambda: calls.append("created") or object())
        results = []
        threads = [threading.Thread(target=lambda: results.append(service.initialize())) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(item is results[0] for item in results))

    def test_provider_services_are_not_constructed_during_import(self):
        self.assertIsNone(provider_policy_service._instance)
        self.assertIsNone(provider_runtime_service._instance)


if __name__ == "__main__":
    unittest.main()
