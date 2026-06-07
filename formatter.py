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
    for subdir in ["copy", "audio", "images"]:
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)
    return output_dir


def get_style_names() -> dict[str, str]:
    """Load style display names from templates."""
    with open(TEMPLATES_DIR / "styles.json", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v["name"] for k, v in data["styles"].items()}


def save_copies(copies: dict[str, str], output_dir: Path) -> list[Path]:
    """Save all copy variants to files.

    Args:
        copies: {style_key: copy_text}
        output_dir: Today's output directory.

    Returns:
        List of saved file paths.
    """
    style_names = get_style_names()
    saved = []
    copy_dir = output_dir / "copy"

    for style_key, text in copies.items():
        style_name = style_names.get(style_key, style_key)
        filename = f"{style_key}_{style_name}.md"
        filepath = copy_dir / filename

        header = f"# {style_name}\n\n"
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
    for style_key, path in audio_files.items():
        if path:
            print(f"   {path.relative_to(output_dir)}")

    print("\n🖼️  图片文件:")
    for name, path in image_files.items():
        if path:
            print(f"   {path.relative_to(output_dir)}")

    print(f"\n💡 请打开 {output_dir} 文件夹，选择最佳文案发布到各平台。")
