from __future__ import annotations

import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from desktop.launcher import SingleInstance, handle_window_closing, parse_args, port_is_available, webview2_is_available
from desktop.ollama_manager import check_ollama


class DesktopLauncherTests(unittest.TestCase):
    def test_default_arguments(self) -> None:
        args = parse_args([])
        self.assertFalse(args.browser)
        self.assertFalse(args.dev)
        self.assertEqual(args.port, 8000)

    def test_custom_flags(self) -> None:
        args = parse_args(["--browser", "--dev", "--port", "8123"])
        self.assertTrue(args.browser)
        self.assertTrue(args.dev)
        self.assertEqual(args.port, 8123)

    def test_port_range_is_validated(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args(["--port", "70000"])

    def test_port_availability_detects_bound_port(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            port = listener.getsockname()[1]
            self.assertFalse(port_is_available("127.0.0.1", port))

    def test_normal_close_hides_window(self) -> None:
        event = __import__("threading").Event()
        hide = __import__("unittest.mock", fromlist=["Mock"]).Mock()
        self.assertFalse(handle_window_closing(event, hide))
        hide.assert_called_once_with()

    def test_explicit_exit_allows_window_close(self) -> None:
        event = __import__("threading").Event()
        event.set()
        hide = __import__("unittest.mock", fromlist=["Mock"]).Mock()
        self.assertTrue(handle_window_closing(event, hide))
        hide.assert_not_called()

    def test_non_windows_single_instance_is_portable(self) -> None:
        instance = SingleInstance()
        if __import__("os").name != "nt":
            self.assertTrue(instance.acquire())
            instance.release()

    def test_webview2_detection_is_windows_only(self) -> None:
        if __import__("os").name != "nt":
            self.assertFalse(webview2_is_available())

    @patch("desktop.ollama_manager.shutil.which", return_value="/usr/bin/ollama")
    @patch("desktop.ollama_manager.urllib.request.urlopen", side_effect=OSError("offline"))
    def test_ollama_installed_but_not_running(self, _urlopen, _which) -> None:
        status = check_ollama()
        self.assertTrue(status.installed)
        self.assertFalse(status.running)
        self.assertIn("installed", status.message.lower())

    @patch("desktop.ollama_manager.shutil.which", return_value=None)
    @patch("desktop.ollama_manager.urllib.request.urlopen", side_effect=OSError("offline"))
    def test_ollama_missing(self, _urlopen, _which) -> None:
        status = check_ollama()
        self.assertFalse(status.installed)
        self.assertFalse(status.running)
        self.assertIn("not detected", status.message.lower())


if __name__ == "__main__":
    unittest.main()
