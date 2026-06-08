"""Continue workflow from Stage 4 — resume from existing output directory."""

import json
from pathlib import Path

from config import validate_config
from voice_gen import generate_voice
from html_gen import generate_html
from video_gen import render_video, check_hyperframes_available
from formatter import print_summary

DEFAULT_STYLE = "style_a"


def main():
    """Resume workflow from Stage 4 using existing output directory."""
    print("=" * 50)
    print("  🚀 继续流程 — 从 Stage 4 开始")
    print("=" * 50)

    validate_config()

    # Load existing output
    output_dir = Path("output/2026-06-08")
    # Find the copy txt file (may have Chinese suffix like _口语风)
    copy_dir = output_dir / "copy"
    txt_candidates = list(copy_dir.glob(f"{DEFAULT_STYLE}*.txt"))
    if not txt_candidates:
        print(f"   ❌ 找不到文案文件: {copy_dir}/{DEFAULT_STYLE}*.txt")
        return
    txt_path = txt_candidates[0]

    if not txt_path.exists():
        print(f"   ❌ 找不到文案文件: {txt_path}")
        return

    plain_text = txt_path.read_text(encoding="utf-8")
    print(f"   📄 已加载文案: {txt_path.name} ({len(plain_text)} 字)")

    product = {"name": "Dreambeans", "tagline": "Daily AI-generated stories from your digital life"}

    # ── Stage 4: 生成配音 ──────────────────────────────────────
    print("\n🎙️  Stage 4: 生成 TTS 配音...")
    audio_path = output_dir / "audio" / f"{DEFAULT_STYLE}.mp3"
    generate_voice(plain_text, audio_path)
    print(f"   ✅ 配音生成完成: {audio_path.name}")

    # ── Stage 5: Whisper 时间对齐 ──────────────────────────────
    print("\n🎯 Stage 5: Whisper 时间对齐...")
    use_alignment = None
    try:
        from aligner import align_plain, save_aligned_srt, save_alignment_json

        alignment = align_plain(audio_path, plain_text)
        save_aligned_srt(alignment, output_dir / "copy" / f"{DEFAULT_STYLE}_aligned.srt")
        alignment_json_path = save_alignment_json(alignment, output_dir / "alignment.json")
        print(f"   ✅ 对齐完成: {alignment_json_path.name}")

        print("\n  对齐预览 (前5句):")
        for idx, start, end, text in alignment[:5]:
            print(f"    {idx:2d}  {start:6.2f}s → {end:6.2f}s  {text[:30]}")

        use_alignment = alignment
    except Exception as e:
        print(f"   ⚠️  对齐失败 ({e})，使用估算时间戳")

    # ── Stage 6: 加载已有图片 + 配色 ──────────────────────────
    print("\n🖼️  Stage 6: 加载已有图片 + 配色...")
    images_dir = output_dir / "images"
    image_paths = sorted(str(p) for p in images_dir.glob("*.png"))
    print(f"   ✅ 已有图片: {len(image_paths)} 张")

    palette = None
    try:
        with open(output_dir / "palette.json", "r", encoding="utf-8") as f:
            palette = json.load(f)
        print(f"   🎨 配色: bg={palette['bg']} accent={palette['accent']}")
    except Exception:
        print("   ⚠️  配色数据不可用")

    # ── Stage 7: 生成 HTML ─────────────────────────────────────
    print("\n🌐 Stage 7: 生成 HyperFrames HTML...")
    html_path = output_dir / "html" / "index.html"

    if use_alignment and palette:
        generate_html(
            product=product,
            alignment=use_alignment,
            palette=palette,
            image_paths=image_paths,
            audio_path=str(audio_path),
            output_path=html_path,
        )
        print(f"   ✅ HTML 生成完成")
    else:
        print("   ⚠️  对齐/配色数据缺失，无法生成 HTML")
        return

    # ── Stage 8: 渲染视频 ─────────────────────────────────────
    video_path = None
    if check_hyperframes_available():
        print("\n🎬 Stage 8: 渲染视频...")
        video_path = output_dir / "video" / f"{DEFAULT_STYLE}.mp4"
        video_path = render_video(html_path, audio_path, video_path)
        if video_path:
            print(f"   ✅ 视频渲染完成: {video_path}")
        else:
            print("   ⚠️  视频渲染失败，但 HTML 文件已生成")
    else:
        print("\n⚠️  HyperFrames 未安装，跳过视频渲染")
        print("   安装方法: npm install -g hyperframes")

    # ── 输出摘要 ───────────────────────────────────────────────
    print_summary(
        output_dir,
        {DEFAULT_STYLE: txt_path},
        {DEFAULT_STYLE: audio_path},
        {p: Path(p) for p in image_paths},
        {DEFAULT_STYLE: html_path},
        {DEFAULT_STYLE: video_path} if video_path else None,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断，已退出。")
