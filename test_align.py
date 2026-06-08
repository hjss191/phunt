"""Non-interactive test: Stage 1-5 to test new aligner."""

import json
from pathlib import Path

from config import validate_config
from phunt_client import fetch_top_products
from copywriter import generate_copy_plain
from voice_gen import generate_voice
from formatter import get_output_dir

DEFAULT_STYLE = "style_a"


def main():
    print("=" * 50)
    print("  🧪 测试新 aligner — Stage 1-5")
    print("=" * 50)

    validate_config()

    # Stage 1: Fetch products
    print("\n📡 Stage 1: 拉取产品...")
    products = fetch_top_products(5)
    for i, p in enumerate(products, 1):
        print(f"  {i}. {p['name']} — {p['tagline']} ({p['votes']} votes)")

    # Stage 2: Select top product (non-interactive)
    product = products[0]
    print(f"\n✅ Stage 2: 自动选择: {product['name']}")

    # Stage 3: Generate copy
    print("\n✍️  Stage 3: 生成文案...")
    plain_text = generate_copy_plain(product, DEFAULT_STYLE)
    if plain_text is None:
        print("   ❌ 文案生成失败")
        return

    output_dir = get_output_dir()
    txt_path = output_dir / "copy" / f"{DEFAULT_STYLE}.txt"
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(plain_text)
    print(f"   📄 保存: {txt_path.name} ({len(plain_text)} 字)")

    # Stage 4: TTS
    print("\n🎙️  Stage 4: 生成配音...")
    audio_path = output_dir / "audio" / f"{DEFAULT_STYLE}.mp3"
    generate_voice(plain_text, audio_path)
    print(f"   ✅ 音频: {audio_path.name}")

    # Stage 5: Whisper alignment (new approach)
    print("\n🎯 Stage 5: Whisper 对齐（新方案）...")
    from aligner import align_plain, save_aligned_srt, save_alignment_json

    alignment = align_plain(audio_path, plain_text)
    save_aligned_srt(alignment, output_dir / "copy" / f"{DEFAULT_STYLE}_aligned.srt")
    save_alignment_json(alignment, output_dir / "alignment.json")

    print(f"\n  对齐结果:")
    for idx, start, end, text in alignment:
        print(f"    {idx:2d}  {start:6.2f}-{end:6.2f}s ({end-start:4.1f}s)  {text[:40]}")

    print(f"\n  ✅ 完成: {len(alignment)} 段, 总时长 {alignment[-1][2]:.1f}s")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断。")
