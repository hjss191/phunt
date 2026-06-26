"""Main entry point — orchestrates the daily workflow with video generation."""

# Add NVIDIA DLL directories before any imports (for CTranslate2 CUDA support)
import os as _os
import site as _site
_dll_dirs = []
for _sp in _site.getsitepackages() + [_site.getusersitepackages()]:
    for _sub in ("nvidia/cublas/bin", "nvidia/cuda_nvrtc/bin"):
        _dll_dir = _os.path.join(_sp, _sub)
        if _os.path.isdir(_dll_dir):
            _dll_dirs.append(_dll_dir)
if _dll_dirs:
    _os.environ["PATH"] = ";".join(_dll_dirs) + ";" + _os.environ.get("PATH", "")
    _os.environ["CT2_CUDA_LIBRARY_PATH"] = ";".join(_dll_dirs)
    for _d in _dll_dirs:
        _os.add_dll_directory(_d)

import json
from pathlib import Path

from config import validate_config, TEMPLATES_DIR
from phunt_client import fetch_top_products, display_products, select_product
from copywriter import generate_copy_plain, load_templates


def select_style() -> str:
    """Let user pick a writing style. Returns style_key."""
    templates = load_templates()
    styles = templates["styles"]
    style_keys = list(styles.keys())

    print("\n🎨 选择文案风格:")
    for i, key in enumerate(style_keys, 1):
        s = styles[key]
        print(f"   {i}) {s['name']} — {s['description']}")

    while True:
        choice = input(f"\n  请选择 [1-{len(style_keys)}]，直接回车默认 1: ").strip()
        if not choice:
            return style_keys[0]
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(style_keys):
                selected = style_keys[idx]
                print(f"   ✅ 已选择: {styles[selected]['name']}")
                return selected
        except ValueError:
            pass
        print("   ⚠️  无效输入，请重新选择")
from voice_gen import generate_voice
from image_gen import download_product_images, generate_ai_images
from html_gen import generate_html
from video_gen import render_video, check_hyperframes_available
from formatter import get_output_dir, print_summary

BGM_DIR = TEMPLATES_DIR / "bgm"


def select_bgm() -> str | None:
    """Let user pick a BGM file. Returns path or None."""
    if not BGM_DIR.is_dir():
        return None
    bgm_files = sorted(BGM_DIR.glob("*.mp3"))
    if not bgm_files:
        return None

    print("\n🎵 选择背景音乐:")
    print("   0) 不使用 BGM")
    for i, f in enumerate(bgm_files, 1):
        print(f"   {i}) {f.name}")

    while True:
        choice = input(f"\n  请选择 [0-{len(bgm_files)}]，直接回车默认 0: ").strip()
        if not choice or choice == "0":
            print("   ✅ 不使用 BGM")
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(bgm_files):
                selected = bgm_files[idx]
                print(f"   ✅ 已选择: {selected.name}")
                return str(selected)
        except ValueError:
            pass
        print("   ⚠️  无效输入，请重新选择")


def main():
    """Run the daily Product Hunt content generation workflow."""
    print("=" * 50)
    print("  🚀 Product Hunt 每日精选 → 视频内容生成")
    print("=" * 50)

    # ── Stage 0: 检查配置 ──────────────────────────────────────
    print("\n📋 检查配置...")
    validate_config()
    print("   ✅ 配置检查通过")

    # ── Stage 1: 选择日期 ──────────────────────────────────────
    print("\n📅 选择产品日期:")
    print("   1) 今日")
    print("   2) 昨日")
    while True:
        date_choice = input("\n  请选择 [1-2]，直接回车默认 1: ").strip()
        if not date_choice or date_choice == "1":
            days_ago = 0
            date_label = "今日"
            break
        elif date_choice == "2":
            days_ago = 1
            date_label = "昨日"
            break
        print("   ⚠️  无效输入，请重新选择")

    # ── Stage 1.5: 拉取产品 ────────────────────────────────────
    print(f"\n📡 拉取 Product Hunt {date_label} Top 5...")
    products = fetch_top_products(5, days_ago=days_ago)
    display_products(products, label=date_label)

    # ── Stage 2: 选择产品 ──────────────────────────────────────
    product = select_product(products)
    print(f"\n✅ 已选择: {product['name']}")
    print(f"   {product['tagline']}")

    # ── Stage 2.5: 选择风格 ────────────────────────────────────
    style_key = select_style()

    # ── Stage 3: 生成文案 ──────────────────────────────────────
    print("\n✍️  生成文案...")
    plain_text = generate_copy_plain(product, style_key)
    if not plain_text:
        print("   ❌ 文案生成失败（空内容），无法继续")
        return
    print("   ✅ 文案生成完成")

    output_dir = get_output_dir()
    txt_path = output_dir / "copy" / f"{style_key}.txt"
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(plain_text)
    print(f"   📄 已保存: {txt_path.resolve()}")
    print(f"\n  文案预览:\n{plain_text[:500]}...")

    # ── 人工审核文案 ─────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  请打开文件审核并修改文案:")
    print(f"  {txt_path.resolve()}")
    print(f"  修改完成后保存文件，然后按回车继续...")
    input()

    # 重新读取修改后的文案
    plain_text = txt_path.read_text(encoding="utf-8")
    print(f"   📄 已加载修改后文案 ({len(plain_text)} 字)")

    # ── Stage 4: 生成配音 ──────────────────────────────────────
    print("\n🎙️  生成 TTS 配音...")
    audio_path = output_dir / "audio" / f"{style_key}.mp3"
    generate_voice(plain_text, audio_path)
    print(f"   ✅ 配音生成完成: {audio_path.name}")

    # ── Stage 5: Whisper 时间对齐 ──────────────────────────────
    print("\n🎯 Whisper 时间对齐...")
    use_alignment = None
    try:
        from aligner import align_plain, save_aligned_srt, save_alignment_json

        alignment = align_plain(audio_path, plain_text)
        save_aligned_srt(alignment, output_dir / "copy" / f"{style_key}_aligned.srt")
        save_alignment_json(alignment, output_dir / "alignment.json")
        print(f"   ✅ 对齐完成: {len(alignment)} 段, 总时长 {alignment[-1][2]:.1f}s")
        use_alignment = alignment
    except Exception as e:
        print(f"   ⚠️  对齐失败 ({e})，无法继续")
        return

    # ── Stage 6: 下载产品图片 + 提取配色 ──────────────────────
    print("\n🖼️  下载产品截图 + 提取配色...")
    image_files = download_product_images(product, output_dir)
    image_paths = [str(p) for p in image_files.values() if p]
    print(f"   ✅ 下载完成 ({len(image_paths)} 张)")

    palette = None
    try:
        with open(output_dir / "palette.json", "r", encoding="utf-8") as f:
            palette = json.load(f)
        print(f"   🎨 配色: bg={palette['bg']} accent={palette['accent']}")
    except Exception:
        print("   ⚠️  配色数据不可用，无法继续")
        return

    # ── Stage 6.5: 检查图片数量 ───────────────────────────────
    if not image_paths:
        print(f"\n   ⚠️  没有图片，尝试 AI 生成...")
        ai_images = generate_ai_images(product, plain_text, palette, output_dir, 6)
        if ai_images:
            image_paths = [str(p) for p in ai_images]
            print(f"   ✅ AI 配图生成完成 ({len(image_paths)} 张)")
        else:
            print("   ⚠️  AI 配图生成失败，将使用纯文字场景")
    else:
        print(f"   ✅ 图片充足 ({len(image_paths)} 张)")

    # ── Stage 6.8: 选择 BGM ───────────────────────────────────
    bgm_path = select_bgm()

    # ── Stage 7: 生成 HTML ─────────────────────────────────────
    print("\n🌐 生成 HyperFrames HTML...")
    html_path = output_dir / "html" / "index.html"

    # Get actual audio duration (alignment timestamps may be shorter than audio)
    audio_dur = None
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(audio_path)],
            capture_output=True, text=True
        )
        audio_dur = float(result.stdout.strip())
    except Exception:
        pass

    generate_html(
        product=product,
        alignment=use_alignment,
        palette=palette,
        image_paths=image_paths,
        audio_path=str(audio_path),
        output_path=html_path,
        audio_duration=audio_dur,
        bgm_path=bgm_path,
    )

    # ── Stage 8: 渲染视频 ─────────────────────────────────────
    video_path = None
    if not check_hyperframes_available():
        print("\n⚠️  HyperFrames 未安装，跳过视频渲染")
        print("   安装方法: npm install -g hyperframes")
    else:
        print("\n🎬 渲染视频...")
        video_path = output_dir / "video" / f"{style_key}.mp4"
        video_path = render_video(html_path, audio_path, video_path)
        if video_path:
            print(f"   ✅ 视频渲染完成: {video_path}")
        else:
            print("   ⚠️  视频渲染失败，但 HTML 文件已生成")

    # ── 输出摘要 ───────────────────────────────────────────────
    print_summary(
        output_dir,
        {style_key: txt_path},
        {style_key: audio_path},
        image_files,
        {style_key: html_path},
        {style_key: video_path} if video_path else None,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断，已退出。")
