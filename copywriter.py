"""AI copywriter — generates 3 copy variants (3 styles) using MiMo API."""

import json
from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, TEMPLATES_DIR


def load_templates() -> dict:
    """Load style templates from styles.json."""
    with open(TEMPLATES_DIR / "styles.json", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(product: dict, style: dict) -> str:
    """Build the user prompt for a specific product × style combo."""
    topics_str = ", ".join(product["topics"]) if product["topics"] else "N/A"
    return f"""请为以下产品写一篇中文推广文案。

产品信息：
- 名称：{product['name']}
- 一句话介绍：{product['tagline']}
- 详细介绍：{product['description']}
- 产品链接：{product['url']}
- 投票数：{product['votes']}
- 相关话题：{topics_str}

要求：
- 字数 300-800 字
- 适合在抖音、小红书、公众号等平台发布
- {style['description']}

请直接输出文案内容，不要加任何前缀说明。"""


def generate_copies(product: dict) -> dict[str, str]:
    """Generate 3 copy variants for a product.

    Returns: {style_key: copy_text}
    """
    client = OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)
    templates = load_templates()

    results = {}
    for style_key, style in templates["styles"].items():
        print(f"  ✍️  生成 {style['name']}...")
        prompt = build_prompt(product, style)

        response = client.chat.completions.create(
            model="mimo",
            messages=[
                {"role": "system", "content": style["system_prompt"]},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=2000,
        )
        results[style_key] = response.choices[0].message.content.strip()

    return results
