from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "desktop" / "assets" / "icon.ico"


def build_icon() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    for size in (16, 24, 32, 48, 64, 128, 256):
        image = Image.new("RGBA", (size, size), (13, 20, 34, 255))
        draw = ImageDraw.Draw(image)
        margin = max(1, size // 12)
        radius = max(3, size // 5)
        draw.rounded_rectangle(
            (margin, margin, size - margin - 1, size - margin - 1),
            radius=radius,
            fill=(20, 31, 49, 255),
            outline=(65, 220, 145, 255),
            width=max(1, size // 24),
        )
        font_size = max(10, int(size * 0.58))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
        bounds = draw.textbbox((0, 0), "N", font=font, stroke_width=0)
        x = (size - (bounds[2] - bounds[0])) / 2 - bounds[0]
        y = (size - (bounds[3] - bounds[1])) / 2 - bounds[1] - size * 0.03
        draw.text((x, y), "N", font=font, fill=(242, 248, 255, 255))
        frames.append(image)
    frames[-1].save(OUTPUT, format="ICO", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    return OUTPUT


if __name__ == "__main__":
    print(f"Created {build_icon()}")
