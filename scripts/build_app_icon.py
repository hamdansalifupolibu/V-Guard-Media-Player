"""
Prepare logo assets from the original root PNG.

- vguard_logo.png  — trimmed full logo (sidebar, About)
- vguard_mark.png  — shield-only square (taskbar / small icons)
- vguard_icon.ico  — multi-size Windows icon
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_LOGO = PROJECT_ROOT / "V Guard logo.png"
ASSETS_DIR = PROJECT_ROOT / "app" / "assets"
LOGO_PNG = ASSETS_DIR / "vguard_logo.png"
MARK_PNG = ASSETS_DIR / "vguard_mark.png"
ICON_ICO = ASSETS_DIR / "vguard_icon.ico"

# Fraction of trimmed logo height that is shield-only (above the wordmark)
SHIELD_HEIGHT_RATIO = 0.56
CONTENT_LUMINANCE_MIN = 120
CONTENT_ALPHA_MIN = 128


def _content_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    """Bounding box of non-black logo pixels (original is mostly empty canvas)."""
    rgba = np.array(img.convert("RGBA"))
    rgb_sum = (
        rgba[:, :, 0].astype(np.int32)
        + rgba[:, :, 1].astype(int)
        + rgba[:, :, 2].astype(int)
    )
    mask = (rgba[:, :, 3] >= CONTENT_ALPHA_MIN) & (rgb_sum >= CONTENT_LUMINANCE_MIN)
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any() or not cols.any():
        w, h = img.size
        return 0, 0, w, h
    ys = np.where(rows)[0]
    xs = np.where(cols)[0]
    return int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1


def trim_logo(img: Image.Image, *, pad: int = 12) -> Image.Image:
    x0, y0, x1, y1 = _content_bbox(img)
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(img.width, x1 + pad)
    y1 = min(img.height, y1 + pad)
    return img.crop((x0, y0, x1, y1))


def extract_shield_mark(trimmed: Image.Image) -> Image.Image:
    """Square crop of the shield for legible 16–48 px taskbar icons."""
    w, h = trimmed.size
    shield_h = max(1, int(h * SHIELD_HEIGHT_RATIO))
    mark = trimmed.crop((0, 0, w, shield_h))
    side = max(mark.width, mark.height)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    ox = (side - mark.width) // 2
    oy = (side - mark.height) // 2
    square.paste(mark, (ox, oy), mark)
    return square


def _resize_square(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.Resampling.LANCZOS)


def _resize_fit(img: Image.Image, size: int) -> Image.Image:
    img = img.convert("RGBA")
    img.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ox = (size - img.width) // 2
    oy = (size - img.height) // 2
    canvas.paste(img, (ox, oy), img)
    return canvas


def build_ico(mark: Image.Image, full: Image.Image) -> None:
    """Small sizes = shield mark; large sizes = full trimmed logo."""
    frames: list[Image.Image] = []
    for size in (16, 20, 24, 32, 40, 48, 64):
        frames.append(_resize_square(mark, size))
    for size in (96, 128, 256):
        frames.append(_resize_fit(full, size))
    frames[0].save(
        ICON_ICO,
        format="ICO",
        sizes=[(f.width, f.height) for f in frames],
        append_images=frames[1:],
    )


def main() -> int:
    source = SOURCE_LOGO
    if not source.is_file():
        print(f"Logo not found: {source}")
        return 1

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    original = Image.open(source)
    if original.mode != "RGBA":
        original = original.convert("RGBA")

    trimmed = trim_logo(original)
    mark = extract_shield_mark(trimmed)

    trimmed.save(LOGO_PNG, format="PNG", optimize=True)
    mark.save(MARK_PNG, format="PNG", optimize=True)
    build_ico(mark, trimmed)

    print(f"Source:     {source} ({original.width}x{original.height})")
    print(f"Trimmed UI: {LOGO_PNG} ({trimmed.width}x{trimmed.height})")
    print(f"Task mark:  {MARK_PNG} ({mark.width}x{mark.height})")
    print(f"Windows:    {ICON_ICO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
