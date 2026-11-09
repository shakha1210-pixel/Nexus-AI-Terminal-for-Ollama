import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


class FrontendServingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.dist = Path(self.temp_dir.name)
        (self.dist / "assets").mkdir()
        (self.dist / "index.html").write_text(
            "<!doctype html><html><body>NEXUS frontend</body></html>",
            encoding="utf-8",
        )
        (self.dist / "assets" / "app.js").write_text(
            "console.log('nexus');",
            encoding="utf-8",
        )
        self.client = TestClient(create_app(self.dist))

    def test_root_serves_frontend_index(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("NEXUS frontend", response.text)

    def test_spa_route_falls_back_to_index(self) -> None:
        response = self.client.get("/settings/providers")

        self.assertEqual(response.status_code, 200)
        self.assertIn("NEXUS frontend", response.text)

    def test_asset_is_served_from_dist(self) -> None:
        response = self.client.get("/assets/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("console.log", response.text)

    def test_unknown_api_route_remains_json_404(self) -> None:
        response = self.client.get("/api/route-that-does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Not Found"})

    def test_health_route_is_not_shadowed_by_static_mount(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
