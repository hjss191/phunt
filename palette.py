"""Palette extractor — derives color scheme from product screenshots."""

import colorsys
import json
from pathlib import Path
from PIL import Image


def extract_palette(image_dir: Path) -> dict:
    """Analyze all PNG images in a directory and derive a color palette.

    Args:
        image_dir: Directory containing product screenshots.

    Returns:
        {
            "bg": "#ecebe8",           // light background
            "accent": "#bf913f",       // warm gold accent
            "text_primary": "#292723", // dark text
            "text_secondary": "#514d47", // muted text
            "brand_gradient": "#78613a,#bf913f,#78613a",
            "hue": 38,
            "avg_rgb": [147, 138, 122],
        }
    """
    pngs = sorted(image_dir.glob("*.png"))
    if not pngs:
        raise FileNotFoundError(f"No PNG images found in {image_dir}")

    # Collect all pixels
    all_pixels = []
    for fp in pngs:
        img = Image.open(fp).resize((50, 50))
        all_pixels.extend(list(img.getdata()))

    # Average RGB
    n = len(all_pixels)
    avg_r = sum(p[0] for p in all_pixels) // n
    avg_g = sum(p[1] for p in all_pixels) // n
    avg_b = sum(p[2] for p in all_pixels) // n

    # Convert to HSL
    r, g, b = avg_r / 255, avg_g / 255, avg_b / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    def hsl_hex(hue, lightness, saturation):
        rr, gg, bb = colorsys.hls_to_rgb(hue, lightness, saturation)
        return f"#{int(rr * 255):02x}{int(gg * 255):02x}{int(bb * 255):02x}"

    palette = {
        "bg": hsl_hex(h, 0.92, 0.10),
        "accent": hsl_hex(h, 0.50, 0.50),
        "accent_dim": hsl_hex(h, 0.35, 0.35),
        "text_primary": hsl_hex(h, 0.15, 0.08),
        "text_secondary": hsl_hex(h, 0.30, 0.06),
        "brand_gradient": f"{hsl_hex(h, 0.35, 0.35)},{hsl_hex(h, 0.50, 0.50)},{hsl_hex(h, 0.35, 0.35)}",
        "hue": round(h * 360),
        "avg_rgb": [avg_r, avg_g, avg_b],
    }
    return palette


def save_palette(palette: dict, output_path: Path) -> Path:
    """Save palette as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(palette, f, ensure_ascii=False, indent=2)
    return output_path
