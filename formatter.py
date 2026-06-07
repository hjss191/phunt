"""Formatter — manages output directory structure and file writing."""

from datetime import datetime
from pathlib import Path
from config import OUTPUT_DIR, TEMPLATES_DIR
import json


def get_output_dir() -> Path:
    """Get today's output directory, creating it if needed."""
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUT_DIR / today
    # 创建子目录
    for subdir in ["copy", "audio", "images", "html", "video"]:
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)
    return output_dir


def get_style_names() -> dict[str, str]:
    """Load style display names from templates."""
    with open(TEMPLATES_DIR / "styles.json", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v["name"] for k, v in data["styles"].items()}


def save_srt_copy(srt_text: str, plain_text: str, style_key: str, output_dir: Path) -> tuple[Path, Path]:
    """Save SRT and plain text files.

    Args:
        srt_text: SRT 格式文本。
        plain_text: 纯文本。
        style_key: 风格标识（如 style_a）。
        output_dir: 今日输出目录。

    Returns:
        (srt_path, txt_path) 保存的文件路径。
    """
    style_names = get_style_names()
    style_name = style_names.get(style_key, style_key)

    copy_dir = output_dir / "copy"
    copy_dir.mkdir(parents=True, exist_ok=True)

    srt_path = copy_dir / f"{style_key}_{style_name}.srt"
    txt_path = copy_dir / f"{style_key}_{style_name}.txt"

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_text)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(plain_text)

    return srt_path, txt_path


def print_summary(
    output_dir: Path,
    srt_files: dict[str, tuple[Path, Path]],
    audio_files: dict[str, Path],
    image_files: dict[str, Path],
    html_files: dict[str, Path] = None,
    video_files: dict[str, Path] = None,
) -> None:
    """Print a summary of generated files."""
    print(f"\n✅ 所有内容已生成到: {output_dir}\n")

    print("📄 文案文件:")
    for style_key, (srt_path, txt_path) in srt_files.items():
        print(f"   {srt_path.relative_to(output_dir)}")
        print(f"   {txt_path.relative_to(output_dir)}")

    print("\n🎙️  音频文件:")
    for style_key, path in audio_files.items():
        if path:
            print(f"   {path.relative_to(output_dir)}")

    print("\n🖼️  图片文件:")
    for name, path in image_files.items():
        if path:
            print(f"   {path.relative_to(output_dir)}")

    if html_files:
        print("\n🌐 HTML 文件:")
        for style_key, path in html_files.items():
            if path:
                print(f"   {path.relative_to(output_dir)}")

    if video_files:
        print("\n🎬 视频文件:")
        for style_key, path in video_files.items():
            if path:
                print(f"   {path.relative_to(output_dir)}")

    print(f"\n💡 请打开 {output_dir} 文件夹查看生成的内容。")
