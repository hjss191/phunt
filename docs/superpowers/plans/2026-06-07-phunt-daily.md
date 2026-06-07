# Product Hunt 每日精选 → 多平台发布 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that fetches Product Hunt Top 5 products, generates 3 styles × 3 platforms of AI copy, TTS audio, and cyberpunk-style images for manual posting to Douyin, Xiaohongshu, and WeChat.

**Architecture:** Modular Python project with separate files for each responsibility (data fetching, copywriting, voice, image, formatting). Config via .env. Interactive CLI flow.

**Tech Stack:** Python 3.10+, openai (MiMo API), requests, python-dotenv, httpx (通义万相)

---

## File Map

| File | Responsibility |
|------|---------------|
| `config.py` | Load .env, expose API keys and paths |
| `phunt_client.py` | GraphQL query to Product Hunt API, return top products |
| `templates/styles.json` | 3 style prompts × 3 platform requirements |
| `copywriter.py` | Call MiMo API, generate 9 copy variants |
| `voice_gen.py` | Call MiMo TTS API, generate mp3 files |
| `image_gen.py` | Call 通义万相 API, generate cyberpunk images |
| `formatter.py` | Create output dirs, write files with correct naming |
| `main.py` | Orchestrate the full flow, interactive CLI |
| `.env.example` | Template for required API keys |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Ignore .env, output/, __pycache__ |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `config.py`

- [ ] **Step 1: Create requirements.txt**

```
openai>=1.0.0
requests>=2.28.0
python-dotenv>=1.0.0
httpx>=0.24.0
```

- [ ] **Step 2: Create .env.example**

```env
# Product Hunt API
PHUNT_API_TOKEN=your_product_hunt_token_here

# MiMo API (OpenAI 兼容)
MIMO_API_KEY=your_mimo_api_key_here
MIMO_BASE_URL=https://api.mimo.example.com/v1

# MiMo TTS API
MIMO_TTS_API_KEY=your_mimo_tts_key_here
MIMO_TTS_BASE_URL=https://tts.mimo.example.com/v1

# 通义万相 API (阿里云 DashScope)
TONGYI_API_KEY=your_tongyi_api_key_here
```

- [ ] **Step 3: Create .gitignore**

```gitignore
.env
output/
__pycache__/
*.pyc
.venv/
venv/
```

- [ ] **Step 4: Create config.py**

```python
"""Configuration management — loads API keys and paths from .env."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

# Project paths
PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"

# Product Hunt
PHUNT_API_TOKEN = os.getenv("PHUNT_API_TOKEN", "")

# MiMo LLM
MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "")

# MiMo TTS
MIMO_TTS_API_KEY = os.getenv("MIMO_TTS_API_KEY", "")
MIMO_TTS_BASE_URL = os.getenv("MIMO_TTS_BASE_URL", "")

# 通义万相
TONGYI_API_KEY = os.getenv("TONGYI_API_KEY", "")


def validate_config():
    """Check that all required API keys are set."""
    missing = []
    if not PHUNT_API_TOKEN:
        missing.append("PHUNT_API_TOKEN")
    if not MIMO_API_KEY:
        missing.append("MIMO_API_KEY")
    if not MIMO_BASE_URL:
        missing.append("MIMO_BASE_URL")
    if not TONGYI_API_KEY:
        missing.append("TONGYI_API_KEY")
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}\nCopy .env.example to .env and fill in your API keys.")
```

- [ ] **Step 5: Verify config loads**

Run: `python -c "from config import validate_config; print('config.py OK')"`
Expected: `config.py OK` (or error about missing .env — that's fine, the import works)

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore config.py
git commit -m "feat: project scaffolding with config management"
```

---

### Task 2: Product Hunt API Client

**Files:**
- Create: `phunt_client.py`

- [ ] **Step 1: Create phunt_client.py**

```python
"""Product Hunt GraphQL API client — fetch today's top products."""

import requests
from config import PHUNT_API_TOKEN

API_URL = "https://api.producthunt.com/v2/api/graphql"

QUERY = """
query GetTodayPosts($first: Int!) {
  posts(order: VOTES, first: $first) {
    edges {
      node {
        id
        name
        tagline
        description
        url
        votesCount
        thumbnail {
          url
        }
        topics {
          edges {
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""


def fetch_top_products(count: int = 5) -> list[dict]:
    """Fetch top products from Product Hunt.

    Returns list of dicts with keys:
        name, tagline, description, url, votes, thumbnail, topics
    """
    headers = {
        "Authorization": f"Bearer {PHUNT_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"query": QUERY, "variables": {"first": count}}

    resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    products = []
    for edge in data["data"]["posts"]["edges"]:
        node = edge["node"]
        topics = [t["node"]["name"] for t in node["topics"]["edges"]]
        products.append({
            "name": node["name"],
            "tagline": node["tagline"],
            "description": node["description"],
            "url": node["url"],
            "votes": node["votesCount"],
            "thumbnail": node["thumbnail"]["url"] if node["thumbnail"] else "",
            "topics": topics,
        })
    return products


def display_products(products: list[dict]) -> None:
    """Print products as a numbered list for user selection."""
    print("\n🏆 Product Hunt 今日 Top 5:\n")
    for i, p in enumerate(products, 1):
        topics_str = ", ".join(p["topics"][:3]) if p["topics"] else "N/A"
        print(f"  [{i}] {p['name']}  ({p['votes']} votes)")
        print(f"      {p['tagline']}")
        print(f"      Topics: {topics_str}")
        print()


def select_product(products: list[dict]) -> dict:
    """Prompt user to select a product by number."""
    while True:
        try:
            choice = int(input("选择产品编号 (1-5): "))
            if 1 <= choice <= len(products):
                return products[choice - 1]
            print(f"请输入 1-{len(products)} 之间的数字")
        except ValueError:
            print("请输入数字")
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from phunt_client import fetch_top_products, display_products, select_product; print('phunt_client.py OK')"`
Expected: `phunt_client.py OK`

- [ ] **Step 3: Commit**

```bash
git add phunt_client.py
git commit -m "feat: Product Hunt API client with GraphQL query"
```

---

### Task 3: Style Templates

**Files:**
- Create: `templates/styles.json`

- [ ] **Step 1: Create styles.json**

```json
{
  "styles": {
    "style_a": {
      "name": "口语风",
      "description": "短句、口语化、有梗、直接说好处",
      "system_prompt": "你是一个抖音/小红书爆款文案写手。你的风格：口语化、接地气、用短句、有梗、直接告诉读者这个产品有什么用。像跟朋友聊天一样。不要用书面语，不要用'首先/其次/最后'这种结构。"
    },
    "style_b": {
      "name": "故事风",
      "description": "场景代入、描述痛点、产品是解决方案",
      "system_prompt": "你是一个擅长讲故事的文案写手。你的风格：先描述一个读者熟悉的场景或痛点，让读者产生共鸣，然后自然引出产品作为解决方案。要有画面感，让人读完觉得'这说的不就是我吗'。"
    },
    "style_c": {
      "name": "分析风",
      "description": "深度拆解、数据支撑、专业视角",
      "system_prompt": "你是一个科技产品分析师。你的风格：用专业但不枯燥的语言，拆解产品的核心价值、技术亮点、市场定位。有数据支撑，有对比分析，让读者觉得看完涨知识了。适合公众号深度阅读。"
    }
  },
  "platforms": {
    "douyin": {
      "name": "抖音",
      "max_chars": 150,
      "requirements": "口语化，短句为主，带2-3个话题标签（#标签），开头要有 hook 能抓住注意力，结尾引导互动（点赞/评论/关注）"
    },
    "xiaohongshu": {
      "name": "小红书",
      "max_chars": 300,
      "requirements": "种草风格，适当使用 emoji，分段清晰，带 3-5 个话题标签，标题要有吸引力，语气真诚像在分享好物"
    },
    "wechat": {
      "name": "公众号",
      "max_chars": 1500,
      "requirements": "深度长文，结构清晰（标题/引言/正文/总结），可以分小节，适合图文排版，专业但不晦涩"
    }
  }
}
```

- [ ] **Step 2: Verify JSON is valid**

Run: `python -c "import json; json.load(open('templates/styles.json', encoding='utf-8')); print('styles.json OK')"`
Expected: `styles.json OK`

- [ ] **Step 3: Commit**

```bash
git add templates/styles.json
git commit -m "feat: add 3-style × 3-platform prompt templates"
```

---

### Task 4: Copywriter Module

**Files:**
- Create: `copywriter.py`

- [ ] **Step 1: Create copywriter.py**

```python
"""AI copywriter — generates 9 copy variants (3 styles × 3 platforms) using MiMo API."""

import json
from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, TEMPLATES_DIR


def load_templates() -> dict:
    """Load style and platform templates from styles.json."""
    with open(TEMPLATES_DIR / "styles.json", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(product: dict, style: dict, platform: dict) -> str:
    """Build the user prompt for a specific product × style × platform combo."""
    topics_str = ", ".join(product["topics"]) if product["topics"] else "N/A"
    return f"""请为以下产品写一篇{platform['name']}文案。

产品信息：
- 名称：{product['name']}
- 一句话介绍：{product['tagline']}
- 详细介绍：{product['description']}
- 产品链接：{product['url']}
- 投票数：{product['votes']}
- 相关话题：{topics_str}

平台要求：
- 平台：{platform['name']}
- 字数限制：{platform['max_chars']}字以内
- 具体要求：{platform['requirements']}

风格要求：
- {style['description']}

请直接输出文案内容，不要加任何前缀说明。"""


def generate_copies(product: dict) -> dict[str, dict[str, str]]:
    """Generate 9 copy variants for a product.

    Returns: {style_key: {platform_key: copy_text}}
    """
    client = OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)
    templates = load_templates()

    results = {}
    for style_key, style in templates["styles"].items():
        results[style_key] = {}
        for plat_key, platform in templates["platforms"].items():
            print(f"  ✍️  生成 {style['name']} × {platform['name']}...")
            prompt = build_prompt(product, style, platform)

            response = client.chat.completions.create(
                model="mimo",
                messages=[
                    {"role": "system", "content": style["system_prompt"]},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=2000,
            )
            results[style_key][plat_key] = response.choices[0].message.content.strip()

    return results
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from copywriter import load_templates, build_prompt, generate_copies; t = load_templates(); print(f'Loaded {len(t[\"styles\"])} styles, {len(t[\"platforms\"])} platforms')"`
Expected: `Loaded 3 styles, 3 platforms`

- [ ] **Step 3: Commit**

```bash
git add copywriter.py
git commit -m "feat: copywriter module with MiMo API integration"
```

---

### Task 5: Voice Generation Module

**Files:**
- Create: `voice_gen.py`

- [ ] **Step 1: Create voice_gen.py**

```python
"""Voice generation — converts copy text to audio using MiMo TTS API."""

import httpx
from pathlib import Path
from config import MIMO_TTS_API_KEY, MIMO_TTS_BASE_URL


def generate_voice(text: str, output_path: Path) -> Path:
    """Generate TTS audio from text.

    Args:
        text: The text to convert to speech.
        output_path: Where to save the .mp3 file.

    Returns:
        Path to the generated audio file.
    """
    headers = {
        "Authorization": f"Bearer {MIMO_TTS_API_KEY}",
        "Content-Type": "application/json",
    }

    # MiMo TTS API — OpenAI compatible format
    # NOTE: Verify exact endpoint and model name with your MiMo TTS provider
    payload = {
        "model": "mimo-tts",
        "input": text,
        "voice": "zh-CN-Default",  # Chinese voice
        "response_format": "mp3",
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{MIMO_TTS_BASE_URL}/audio/speech",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)

    return output_path


def generate_voices_for_copies(
    copies: dict[str, dict[str, str]],
    output_dir: Path,
) -> dict[str, dict[str, Path]]:
    """Generate audio for all copy variants.

    Args:
        copies: {style_key: {platform_key: copy_text}}
        output_dir: Directory to save audio files.

    Returns:
        {style_key: {platform_key: audio_path}}
    """
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for style_key, platforms in copies.items():
        results[style_key] = {}
        for plat_key, text in platforms.items():
            filename = f"{plat_key}_{style_key}.mp3"
            audio_path = audio_dir / filename
            print(f"  🎙️  生成配音: {filename}...")
            try:
                results[style_key][plat_key] = generate_voice(text, audio_path)
            except Exception as e:
                print(f"  ⚠️  配音生成失败 ({filename}): {e}")
                results[style_key][plat_key] = None

    return results
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from voice_gen import generate_voice, generate_voices_for_copies; print('voice_gen.py OK')"`
Expected: `voice_gen.py OK`

- [ ] **Step 3: Commit**

```bash
git add voice_gen.py
git commit -m "feat: voice generation module with MiMo TTS"
```

---

### Task 6: Image Generation Module

**Files:**
- Create: `image_gen.py`

- [ ] **Step 1: Create image_gen.py**

```python
"""Image generation — creates cyberpunk-style product images using 通义万相 API."""

import httpx
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
            import time
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
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from image_gen import generate_image, generate_product_images, build_image_prompt; print('image_gen.py OK')"`
Expected: `image_gen.py OK`

- [ ] **Step 3: Commit**

```bash
git add image_gen.py
git commit -m "feat: image generation module with 通义万相 API"
```

---

### Task 7: Formatter Module

**Files:**
- Create: `formatter.py`

- [ ] **Step 1: Create formatter.py`

```python
"""Formatter — manages output directory structure and file writing."""

from datetime import datetime
from pathlib import Path
from config import OUTPUT_DIR, TEMPLATES_DIR
import json


def get_output_dir() -> Path:
    """Get today's output directory, creating it if needed."""
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUT_DIR / today
    # Create subdirectories
    for subdir in ["douyin", "xiaohongshu", "wechat", "audio", "images"]:
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)
    return output_dir


def get_style_names() -> dict[str, str]:
    """Load style display names from templates."""
    with open(TEMPLATES_DIR / "styles.json", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v["name"] for k, v in data["styles"].items()}


def save_copies(copies: dict[str, dict[str, str]], output_dir: Path) -> list[Path]:
    """Save all copy variants to files.

    Args:
        copies: {style_key: {platform_key: copy_text}}
        output_dir: Today's output directory.

    Returns:
        List of saved file paths.
    """
    style_names = get_style_names()
    saved = []

    for style_key, platforms in copies.items():
        style_name = style_names.get(style_key, style_key)
        for plat_key, text in platforms.items():
            filename = f"{style_key}_{style_name}.md"
            filepath = output_dir / plat_key / filename

            # Add markdown header
            header = f"# {style_name} — {plat_key}\n\n"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(header + text)

            saved.append(filepath)

    return saved


def print_summary(
    output_dir: Path,
    copy_files: list[Path],
    audio_files: dict,
    image_files: dict,
) -> None:
    """Print a summary of generated files."""
    print(f"\n✅ 所有内容已生成到: {output_dir}\n")
    print("📄 文案文件:")
    for f in copy_files:
        print(f"   {f.relative_to(output_dir)}")

    print("\n🎙️  音频文件:")
    for style_key, platforms in audio_files.items():
        for plat_key, path in platforms.items():
            if path:
                print(f"   {path.relative_to(output_dir)}")

    print("\n🖼️  图片文件:")
    for name, path in image_files.items():
        if path:
            print(f"   {path.relative_to(output_dir)}")

    print(f"\n💡 请打开 {output_dir} 文件夹，选择最佳文案发布到各平台。")
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from formatter import get_output_dir, save_copies, print_summary, get_style_names; print(f'Styles: {get_style_names()}')"`
Expected: `Styles: {'style_a': '口语风', 'style_b': '故事风', 'style_c': '分析风'}`

- [ ] **Step 3: Commit**

```bash
git add formatter.py
git commit -m "feat: formatter module for output management"
```

---

### Task 8: Main Orchestration

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create main.py**

```python
"""Main entry point — orchestrates the full daily workflow."""

from config import validate_config
from phunt_client import fetch_top_products, display_products, select_product
from copywriter import generate_copies
from voice_gen import generate_voices_for_copies
from image_gen import generate_product_images
from formatter import get_output_dir, save_copies, print_summary


def main():
    """Run the daily Product Hunt content generation workflow."""
    print("=" * 50)
    print("  🚀 Product Hunt 每日精选 → 多平台内容生成")
    print("=" * 50)

    # Step 0: Validate config
    print("\n📋 检查配置...")
    validate_config()
    print("   ✅ 配置检查通过")

    # Step 1: Fetch top products
    print("\n📡 拉取 Product Hunt 今日 Top 5...")
    products = fetch_top_products(5)
    display_products(products)

    # Step 2: User selects a product
    product = select_product(products)
    print(f"\n✅ 已选择: {product['name']}")
    print(f"   {product['tagline']}")

    # Step 3: Generate copies
    print("\n✍️  开始生成文案 (3风格 × 3平台)...")
    copies = generate_copies(product)
    print("   ✅ 文案生成完成")

    # Step 4: Generate voice
    print("\n🎙️  开始生成配音...")
    output_dir = get_output_dir()
    audio_files = generate_voices_for_copies(copies, output_dir)
    print("   ✅ 配音生成完成")

    # Step 5: Generate images
    print("\n🎨 开始生成配图...")
    image_files = generate_product_images(product, output_dir)
    print("   ✅ 配图生成完成")

    # Step 6: Save and summarize
    copy_files = save_copies(copies, output_dir)
    print_summary(output_dir, copy_files, audio_files, image_files)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify syntax**

Run: `python -c "import main; print('main.py OK')"`
Expected: `main.py OK`

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: main orchestration with interactive CLI flow"
```

---

### Task 9: Full Integration Test

- [ ] **Step 1: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: Successfully installed openai, requests, python-dotenv, httpx

- [ ] **Step 2: Configure .env**

```bash
cp .env.example .env
# Edit .env with actual API keys
```

- [ ] **Step 3: Run the full flow**

Run: `python main.py`
Expected:
1. Config check passes
2. Product Hunt Top 5 displayed
3. User selects a product
4. 9 copies generated
5. Audio files generated
6. Images generated
7. Files saved to output/YYYY-MM-DD/

- [ ] **Step 4: Verify output files**

Run: `ls output/` (check today's date folder exists with all subdirectories and files)

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete Product Hunt daily content generation pipeline"
```

---

## NOTES

**MiMo TTS API:** The voice_gen.py uses OpenAI-compatible TTS endpoint format (`/audio/speech`). Verify the exact endpoint and model name with your MiMo TTS provider. Adjust `payload` and URL if needed.

**通义万相 API:** Uses DashScope async API pattern (submit → poll → download). If your account has a different endpoint or model name (e.g., `wanx2.1-t2i-turbo`), update `TONGYI_API_URL` and `payload.model` in image_gen.py.

**MiMo model name:** In copywriter.py, the model is set to `"mimo"`. Update this to match your actual MiMo model ID (e.g., `"MiMo-7B-Chat"` or whatever your provider uses).
