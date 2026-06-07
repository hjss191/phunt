"""AI copywriter — generates copy in SRT format using MiMo API."""

import json
from pathlib import Path
from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, TEMPLATES_DIR
from srt_parser import parse_srt, extract_text, build_srt, estimate_srt_from_text


def load_templates() -> dict:
    """Load style templates from styles.json."""
    with open(TEMPLATES_DIR / "styles.json", encoding="utf-8") as f:
        return json.load(f)


def load_srt_prompt_template() -> str:
    """Load SRT prompt template."""
    with open(TEMPLATES_DIR / "srt_prompt.txt", encoding="utf-8") as f:
        return f.read()


def build_prompt(product: dict, style: dict) -> str:
    """Build the user prompt for SRT generation."""
    topics_str = ", ".join(product["topics"]) if product["topics"] else "N/A"
    template = load_srt_prompt_template()
    return template.format(
        name=product["name"],
        tagline=product["tagline"],
        description=product["description"],
        url=product["url"],
        votes=product["votes"],
        topics=topics_str,
        style_description=style["description"],
    )


def generate_copy_srt(product: dict, style_key: str = "style_a") -> tuple[str, str]:
    """Generate copy in SRT format for a product.

    Args:
        product: Product dict from phunt_client.
        style_key: Which style to use (default: style_a 口语风).

    Returns:
        (srt_text, plain_text) — SRT 格式文本和纯文本。
    """
    client = OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)
    templates = load_templates()
    style = templates["styles"][style_key]

    print(f"  ✍️  生成 {style['name']}文案（SRT 格式）...")
    prompt = build_prompt(product, style)

    try:
        response = client.chat.completions.create(
            model="mimo-v2.5-pro",
            messages=[
                {"role": "system", "content": style["system_prompt"]},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=2000,
        )
        raw_output = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"   ❌ API 调用失败: {e}")
        return None, None

    # 尝试解析 SRT
    entries = parse_srt(raw_output)

    if entries:
        # LLM 输出了有效的 SRT
        srt_text = build_srt(entries)
        plain_text = extract_text(entries)
        print(f"   ✅ 解析到 {len(entries)} 条字幕")
    else:
        # LLM 未输出 SRT 格式，回退：按行分割估算时间戳
        print("   ⚠️  LLM 未输出 SRT 格式，使用估算时间戳")
        entries = estimate_srt_from_text(raw_output)
        srt_text = build_srt(entries)
        plain_text = raw_output

    return srt_text, plain_text


def generate_copies(product: dict) -> dict[str, tuple[str, str]]:
    """Generate copy variants for a product.

    Returns: {style_key: (srt_text, plain_text)}
    """
    templates = load_templates()
    results = {}

    for style_key in templates["styles"]:
        srt_text, plain_text = generate_copy_srt(product, style_key)
        if srt_text is None:
            print(f"   ⚠️  跳过失败的风格: {style_key}")
            continue
        results[style_key] = (srt_text, plain_text)

    return results
