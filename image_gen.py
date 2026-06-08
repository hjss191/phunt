"""Image fetcher — downloads product screenshots from Product Hunt."""

import httpx
from pathlib import Path


def download_product_images(product: dict, output_dir: Path) -> dict[str, Path]:
    """Download product screenshots from Product Hunt media URLs.

    Args:
        product: Product dict with 'media' key from phunt_client.
        output_dir: Directory to save images.

    Returns:
        {"01": path, "02": path, ...}
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    image_media = [m for m in product.get("media", []) if m["type"] == "image"]

    if not image_media:
        print("  ⚠️  该产品没有图片")
        return results

    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for i, m in enumerate(image_media, 1):
            filename = f"{i:02d}.png"
            filepath = images_dir / filename
            print(f"  🖼️  下载图片 {i}/{len(image_media)}: {filename}...")
            try:
                resp = client.get(m["url"])
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                results[f"{i:02d}"] = filepath
            except Exception as e:
                print(f"  ⚠️  下载失败 ({filename}): {e}")
                results[f"{i:02d}"] = None

    # Extract color palette from downloaded images
    try:
        from palette import extract_palette, save_palette
        palette = extract_palette(images_dir)
        palette_path = output_dir / "palette.json"
        save_palette(palette, palette_path)
        print(f"  🎨 配色提取完成: {palette_path.name}")
    except Exception as e:
        print(f"  ⚠️  配色提取失败: {e}")

    return results
