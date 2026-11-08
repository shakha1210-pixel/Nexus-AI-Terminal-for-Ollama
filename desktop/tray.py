from __future__ import annotations

import threading
from collections.abc import Callable


class TrayController:
    """Optional system-tray integration; absence of optional packages is non-fatal."""

    def __init__(self, on_show: Callable[[], None], on_exit: Callable[[], None]) -> None:
        self.on_show = on_show
        self.on_exit = on_exit
        self.available = False
        self._icon = None
        self._thread: threading.Thread | None = None

    @staticmethod
    def _make_image():
        from PIL import Image, ImageDraw

        from pathlib import Path

        icon_path = Path(__file__).resolve().parent / "assets" / "icon.ico"
        if icon_path.is_file():
            with Image.open(icon_path) as icon:
                return icon.convert("RGBA").resize((64, 64))

        image = Image.new("RGBA", (64, 64), (18, 24, 38, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((5, 5, 59, 59), radius=13, outline=(74, 222, 128, 255), width=3)
        draw.text((17, 17), "N", fill=(240, 248, 255, 255), stroke_width=1)
        return image

    def start(self) -> bool:
        try:
            import pystray
        except ImportError:
            return False

        menu = pystray.Menu(
            pystray.MenuItem("Open NEXUS AI", lambda _icon, _item: self.on_show(), default=True),
            pystray.MenuItem("Exit", lambda _icon, _item: self.on_exit()),
        )
        self._icon = pystray.Icon("NEXUS AI", self._make_image(), "NEXUS AI", menu)
        self._thread = threading.Thread(target=self._icon.run, name="nexus-tray", daemon=True)
        self._thread.start()
        self.available = True
        return True

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()
        self.available = False
