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
