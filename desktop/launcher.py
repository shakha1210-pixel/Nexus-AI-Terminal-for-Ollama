from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
VITE_PORT = 5173
WEBVIEW2_GUIDANCE = (
    "Microsoft Edge WebView2 Runtime is missing. Install the Evergreen WebView2 Runtime "
    "from Microsoft's official download page, then restart NEXUS AI. "
    "You can use --browser as a temporary alternative."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NEXUS AI Windows desktop launcher")
    parser.add_argument("--browser", action="store_true", help="Open NEXUS in the system browser")
    parser.add_argument("--dev", action="store_true", help="Use the Vite development server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Local FastAPI port (default: 8000)")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    return args


class SingleInstance:
    """Windows named mutex; the OS releases it automatically after a crash."""

    def __init__(self, name: str = r"Local\NexusAITerminal") -> None:
        self.name = name
        self.handle = None
        self.already_running = False

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        ctypes.set_last_error(0)
        handle = kernel32.CreateMutexW(None, False, self.name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.handle = handle
        self.already_running = ctypes.get_last_error() == 183
        return not self.already_running

    def release(self) -> None:
        if self.handle and os.name == "nt":
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel32.CloseHandle(self.handle)
            self.handle = None


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def webview2_is_available() -> bool:
    if os.name != "nt":
        return False
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/EdgeWebView/Application",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft/EdgeWebView/Application",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft/EdgeWebView/Application",
    ]
    for path in candidates:
        try:
            if path.is_dir() and any(child.is_dir() for child in path.iterdir()):
                return True
        except OSError:
            continue
    return False


def start_backend(port: int):
    sys.path.insert(0, str(BACKEND_DIR))
    import uvicorn
    from app.main import app

    config = uvicorn.Config(app, host=DEFAULT_HOST, port=port, log_level="info", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="nexus-fastapi", daemon=True)
    thread.start()

    deadline = time.monotonic() + 15
    health_url = f"http://{DEFAULT_HOST}:{port}/api/health"
    while time.monotonic() < deadline:
        if server.started:
            try:
                with urllib.request.urlopen(health_url, timeout=1) as response:
                    if response.status == 200:
                        return server, thread
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
        if not thread.is_alive():
            raise RuntimeError("FastAPI server stopped before becoming ready. Check the terminal logs.")
        time.sleep(0.1)
    server.should_exit = True
    raise RuntimeError("FastAPI server did not become ready within 15 seconds.")


def start_vite() -> subprocess.Popen:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        raise RuntimeError("Node.js/npm was not found. Install Node.js or launch without --dev.")
    env = os.environ.copy()
    env["NEXUS_API_TARGET"] = f"http://{DEFAULT_HOST}:{os.environ.get('NEXUS_API_PORT', DEFAULT_PORT)}"
    command = [npm, "run", "dev", "--", "--host", DEFAULT_HOST, "--port", str(VITE_PORT), "--strictPort"]
    process = subprocess.Popen(command, cwd=PROJECT_ROOT / "frontend", env=env)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Vite development server exited unexpectedly.")
        try:
            with urllib.request.urlopen(f"http://{DEFAULT_HOST}:{VITE_PORT}", timeout=0.5):
                return process
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.2)
    process.terminate()
    raise RuntimeError("Vite development server did not become ready within 20 seconds.")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    os.chdir(BACKEND_DIR)
    instance = SingleInstance()
    if not instance.acquire():
        print("NEXUS AI is already running.")
        return 0

    server = None
    server_thread = None
    vite_process = None
    tray = None
    stop_event = threading.Event()
    try:
        if not args.dev and not (PROJECT_ROOT / "frontend" / "dist" / "index.html").is_file():
            raise RuntimeError("Frontend build is missing. Run `npm ci` and `npm run build` in frontend/, or launch with --dev.")
        if not port_is_available(DEFAULT_HOST, args.port):
            raise RuntimeError(
                f"Port {args.port} is already in use. Close the other service or choose another port with --port."
            )

        from desktop.ollama_manager import check_ollama
        ollama = check_ollama()
        print(f"Ollama: {ollama.message}")

        server, server_thread = start_backend(args.port)
        os.environ["NEXUS_API_PORT"] = str(args.port)

        if args.dev:
            vite_process = start_vite()
            url = f"http://{DEFAULT_HOST}:{VITE_PORT}"
        else:
            url = f"http://{DEFAULT_HOST}:{args.port}"

        if args.browser:
            webbrowser.open(url)
            print(f"NEXUS AI is running at {url}. Press Ctrl+C to stop.")
            while not stop_event.wait(0.5):
                if not server_thread.is_alive():
                    break
            return 0

        if os.name == "nt" and not webview2_is_available():
            print(WEBVIEW2_GUIDANCE)
            webbrowser.open(url)
            print(f"Opened browser fallback: {url}. Press Ctrl+C to stop.")
            while not stop_event.wait(0.5):
                if not server_thread.is_alive():
                    break
            return 0

        try:
            import webview
        except ImportError:
            print("PyWebView is not installed. Install desktop/requirements.txt or use --browser.")
            webbrowser.open(url)
            while not stop_event.wait(0.5):
                if not server_thread.is_alive():
                    break
            return 0

        window = webview.create_window("NEXUS AI", url, width=1440, height=900, min_size=(960, 640))

        def request_exit() -> None:
            stop_event.set()
            if server is not None:
                server.should_exit = True
            try:
                webview.destroy_window()
            except Exception:
                pass

        tray = None
        try:
            from desktop.tray import TrayController
            tray = TrayController(on_show=window.show, on_exit=request_exit)
            tray.start()
        except Exception as exc:
            print(f"System tray unavailable: {type(exc).__name__}")

        if tray and tray.available:
            def minimize_to_tray() -> bool:
                window.hide()
                return False
            window.events.closing += minimize_to_tray

        webview.start(gui="edgechromium" if os.name == "nt" else None)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"NEXUS AI launcher error: {exc}", file=sys.stderr)
        return 1
    finally:
        stop_event.set()
        if tray is not None:
            tray.stop()
        if server is not None:
            server.should_exit = True
        if server_thread is not None:
            server_thread.join(timeout=5)
        if vite_process is not None and vite_process.poll() is None:
            vite_process.terminate()
            try:
                vite_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                vite_process.kill()
        instance.release()


if __name__ == "__main__":
    raise SystemExit(main())
