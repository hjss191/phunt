"""HTML generation — creates HyperFrames HTML from SRT and product info."""

import json
from pathlib import Path
from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, TEMPLATES_DIR
from srt_parser import parse_srt, seconds_to_srt_time


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

    # 解析 SRT 获取总时长
    entries = parse_srt(srt_text)
    total_duration = entries[-1].end if entries else 0
    total_duration_srt = seconds_to_srt_time(total_duration)

    template = load_html_prompt_template()
    # Use .replace() instead of .format() to avoid injection from product data
    # containing literal { or } characters.
    result = template
    result = result.replace("{srt_content}", srt_text)
    result = result.replace("{name}", product["name"])
    result = result.replace("{tagline}", product["tagline"])
    result = result.replace("{description}", product["description"])
    result = result.replace("{url}", product["url"])
    result = result.replace("{votes}", str(product["votes"]))
    result = result.replace("{topics}", topics_str)
    result = result.replace("{image_paths}", image_paths_str)
    result = result.replace("{audio_path}", audio_path)
    result = result.replace("{total_duration}", total_duration_srt)
    return result


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

    try:
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
    except Exception as e:
        raise RuntimeError(f"HTML generation API call failed: {e}") from e
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
