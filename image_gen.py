"""Image fetcher — downloads product screenshots or generates AI images."""

import httpx
import json
from pathlib import Path
from config import TONGYI_API_KEY


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


def check_image_sufficiency(image_paths: dict, min_count: int = 6) -> bool:
    """Check if we have enough images.

    Args:
        image_paths: Dict from download_product_images.
        min_count: Minimum number of images needed.

    Returns:
        True if enough images, False otherwise.
    """
    valid = [p for p in image_paths.values() if p is not None]
    return len(valid) >= min_count


def generate_ai_images(product: dict, copy_text: str, palette: dict,
                       output_dir: Path, count: int = 8) -> list[Path]:
    """Generate images using 通义万相 API.

    Args:
        product: Product dict.
        copy_text: The copy text for context.
        palette: Color palette dict.
        output_dir: Directory to save images.
        count: Number of images to generate.

    Returns:
        List of generated image paths.
    """
    if not TONGYI_API_KEY:
        print("  ⚠️  TONGYI_API_KEY 未配置，无法生成 AI 图片")
        return []

    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # Build prompts based on product info
    product_name = product["name"]
    tagline = product.get("tagline", "")
    accent = palette.get("accent", "#60a5fa")

    # Create diverse prompts for different scenes
    prompts = [
        f"{product_name} product interface, modern UI design, clean and minimal, accent color {accent}",
        f"{product_name} dashboard view, data visualization, professional tech product",
        f"{product_name} mobile app screen, user-friendly interface, modern design",
        f"{product_name} feature showcase, AI technology illustration, futuristic",
        f"{product_name} user experience, happy users, productivity boost",
        f"{product_name} team collaboration, workplace efficiency, digital transformation",
        f"{product_name} AI automation, smart workflow, technology innovation",
        f"{product_name} success metrics, growth chart, positive results",
    ]

    generated = []
    print(f"  🎨 生成 AI 配图 ({count} 张)...")

    with httpx.Client(timeout=120) as client:
        for i in range(min(count, len(prompts))):
            prompt = prompts[i]
            filename = f"{i+1:02d}.png"
            filepath = images_dir / filename

            print(f"  🖼️  生成图片 {i+1}/{count}: {filename}...")
            try:
                # Call 通义万相 API
                resp = client.post(
                    "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis",
                    headers={
                        "Authorization": f"Bearer {TONGYI_API_KEY}",
                        "Content-Type": "application/json",
                        "X-DashScope-Async": "enable",
                    },
                    json={
                        "model": "wanx-v1",
                        "input": {"prompt": prompt},
                        "parameters": {
                            "style": "<auto>",
                            "size": "720*1280",
                            "n": 1,
                        },
                    },
                )
                resp.raise_for_status()
                task_id = resp.json()["output"]["task_id"]

                # Poll for result (max 60 seconds)
                import time
                for _ in range(30):
                    time.sleep(2)
                    result = client.get(
                        f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}",
                        headers={"Authorization": f"Bearer {TONGYI_API_KEY}"},
                    )
                    result.raise_for_status()
                    output = result.json()["output"]
                    status = output["task_status"]
                    if status == "SUCCEEDED":
                        img_url = output["results"][0]["url"]
                        img_resp = client.get(img_url)
                        img_resp.raise_for_status()
                        with open(filepath, "wb") as f:
                            f.write(img_resp.content)
                        generated.append(filepath)
                        print(f"    ✅ 完成: {filename}")
                        break
                    elif status == "FAILED":
                        print(f"    ❌ 生成失败: {output.get('message', '')}")
                        break
                else:
                    print(f"    ⚠️  超时 (60秒)")

            except Exception as e:
                print(f"    ❌ 异常: {e}")

    return generated
