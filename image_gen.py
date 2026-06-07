"""Image generation — creates cyberpunk-style product images using 通义万相 API."""

import httpx
import time
from pathlib import Path
from config import TONGYI_API_KEY

# 通义万相 DashScope API
TONGYI_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"


def build_image_prompt(product: dict) -> str:
    """Build a cyberpunk-style image prompt from product info."""
    topics_str = " ".join(product["topics"][:3]) if product["topics"] else "technology"
    return (
        f"Cyberpunk style digital art of a futuristic product concept: {product['name']}. "
        f"{product['tagline']}. "
        f"Neon lights, holographic UI elements, dark background with glowing accents, "
        f"high-tech aesthetic, {topics_str} theme. "
        f"Professional product showcase, 16:9 aspect ratio, ultra detailed."
    )


def generate_image(prompt: str, output_path: Path, size: str = "1024*1024") -> Path:
    """Generate an image using 通义万相 API.

    Args:
        prompt: Image generation prompt.
        output_path: Where to save the .png file.
        size: Image dimensions (e.g., "1024*1024", "1280*720").

    Returns:
        Path to the generated image.
    """
    headers = {
        "Authorization": f"Bearer {TONGYI_API_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    payload = {
        "model": "wanx-v1",
        "input": {
            "prompt": prompt,
            "negative_prompt": "low quality, blurry, text, watermark, logo",
        },
        "parameters": {
            "size": size,
            "n": 1,
        },
    }

    with httpx.Client(timeout=120) as client:
        # Submit task
        resp = client.post(TONGYI_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        task_id = resp.json()["output"]["task_id"]

        # Poll for result
        check_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        for _ in range(60):  # max 60 polls
            time.sleep(3)
            check_resp = client.get(check_url, headers={"Authorization": f"Bearer {TONGYI_API_KEY}"})
            check_resp.raise_for_status()
            status = check_resp.json()["output"]["task_status"]
            if status == "SUCCEEDED":
                image_url = check_resp.json()["output"]["results"][0]["url"]
                break
            elif status == "FAILED":
                raise RuntimeError(f"Image generation failed: {check_resp.json()}")
        else:
            raise TimeoutError("Image generation timed out")

        # Download image
        img_resp = client.get(image_url)
        img_resp.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(img_resp.content)

    return output_path


def generate_product_images(product: dict, output_dir: Path) -> dict[str, Path]:
    """Generate cover and detail images for a product.

    Returns:
        {"cover": path, "detail": path}
    """
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    prompt = build_image_prompt(product)

    # Cover image (16:9 for social media)
    print("  🎨  生成封面图...")
    try:
        results["cover"] = generate_image(prompt, images_dir / "cover.png", "1280*720")
    except Exception as e:
        print(f"  ⚠️  封面图生成失败: {e}")
        results["cover"] = None

    # Detail image (1:1 for Xiaohongshu)
    print("  🎨  生成详情图...")
    try:
        detail_prompt = prompt + " Close-up detail view, product interface mockup."
        results["detail"] = generate_image(detail_prompt, images_dir / "detail.png", "1024*1024")
    except Exception as e:
        print(f"  ⚠️  详情图生成失败: {e}")
        results["detail"] = None

    return results
