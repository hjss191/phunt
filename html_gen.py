"""HTML generation — creates HyperFrames HTML from SRT and product info."""

import json
from pathlib import Path
from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, TEMPLATES_DIR
from srt_parser import parse_srt


def load_html_prompt_template() -> str:
    """Load HTML prompt template."""
    with open(TEMPLATES_DIR / "html_prompt.txt", encoding="utf-8") as f:
        return f.read()


def build_html_prompt(
    product: dict,
    srt_text: str,
    image_paths: list[str],
    audio_path: str,
) -> str:
    """Build the prompt for HTML generation."""
    topics_str = ", ".join(product["topics"]) if product["topics"] else "N/A"
    image_paths_str = "\n".join(f"- {p}" for p in image_paths) if image_paths else "- 无图片"

    template = load_html_prompt_template()
    return template.format(
        srt_content=srt_text,
        name=product["name"],
        tagline=product["tagline"],
        description=product["description"],
        url=product["url"],
        votes=product["votes"],
        topics=topics_str,
        image_paths=image_paths_str,
        audio_path=audio_path,
    )


def generate_html(
    product: dict,
    srt_text: str,
    image_paths: list[str],
    audio_path: str,
    output_path: Path,
) -> Path:
    """Generate HyperFrames HTML file.

    Args:
        product: Product dict from phunt_client.
        srt_text: SRT 格式文本。
        image_paths: 产品图片本地路径列表。
        audio_path: 音频文件路径（相对于 HTML 文件）。
        output_path: 输出 HTML 文件路径。

    Returns:
        Path to the generated HTML file.
    """
    client = OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)

    print("  🎨  生成 HyperFrames HTML...")
    prompt = build_html_prompt(product, srt_text, image_paths, audio_path)

    response = client.chat.completions.create(
        model="mimo-v2.5-pro",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个前端开发专家，擅长生成 HyperFrames 格式的 HTML 视频文件。"
                    "你会根据 SRT 字幕的时间戳，为每句话设计合适的画面，"
                    "并确保 HTML 结构符合 HyperFrames 规范。"
                    "只输出 HTML 代码，不要加任何说明。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=4000,
    )
    html_content = response.choices[0].message.content.strip()

    # 清理可能的 markdown 代码块标记
    if html_content.startswith("```html"):
        html_content = html_content[7:]
    if html_content.startswith("```"):
        html_content = html_content[3:]
    if html_content.endswith("```"):
        html_content = html_content[:-3]
    html_content = html_content.strip()

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"   ✅ HTML 生成完成: {output_path.name}")
    return output_path
