"""Main entry point — orchestrates the daily workflow with video generation."""

DEFAULT_STYLE = "style_a"

from config import validate_config
from phunt_client import fetch_top_products, display_products, select_product
from copywriter import generate_copy_srt
from voice_gen import generate_voice
from image_gen import download_product_images
from html_gen import generate_html
from video_gen import render_video, check_hyperframes_available
from formatter import get_output_dir, save_srt_copy, print_summary


def main():
    """Run the daily Product Hunt content generation workflow."""
    print("=" * 50)
    print("  🚀 Product Hunt 每日精选 → 视频内容生成")
    print("=" * 50)

    # Step 0: 检查配置
    print("\n📋 检查配置...")
    validate_config()
    print("   ✅ 配置检查通过")

    # Step 1: 拉取产品
    print("\n📡 拉取 Product Hunt 今日 Top 5...")
    products = fetch_top_products(5)
    display_products(products)

    # Step 2: 选择产品
    product = select_product(products)
    print(f"\n✅ 已选择: {product['name']}")
    print(f"   {product['tagline']}")

    # Step 3: 生成文案（SRT 格式）
    print("\n✍️  开始生成文案（SRT 格式）...")
    srt_text, plain_text = generate_copy_srt(product, DEFAULT_STYLE)
    if srt_text is None:
        print("   ❌ 文案生成失败，无法继续")
        return
    print("   ✅ 文案生成完成")

    # Step 4: 保存文案
    output_dir = get_output_dir()
    srt_path, txt_path = save_srt_copy(srt_text, plain_text, DEFAULT_STYLE, output_dir)
    print(f"   📄 SRT: {srt_path.name}")
    print(f"   📄 TXT: {txt_path.name}")

    # Step 5: 生成配音
    print("\n🎙️  开始生成配音...")
    audio_path = output_dir / "audio" / f"{DEFAULT_STYLE}.mp3"
    generate_voice(plain_text, audio_path)
    print("   ✅ 配音生成完成")

    # Step 6: 下载产品图片
    print("\n🖼️  下载产品截图...")
    image_files = download_product_images(product, output_dir)
    image_paths = [str(p) for p in image_files.values() if p]
    print(f"   ✅ 下载完成 ({len(image_paths)} 张)")

    # Step 7: 生成 HTML
    print("\n🌐 生成 HyperFrames HTML...")
    html_path = output_dir / "html" / f"{DEFAULT_STYLE}.html"
    generate_html(product, srt_text, image_paths, str(audio_path), html_path)
    print("   ✅ HTML 生成完成")

    # Step 8: 渲染视频（如果 HyperFrames 可用）
    video_path = None
    if check_hyperframes_available():
        print("\n🎬 渲染视频...")
        video_path = output_dir / "video" / f"{DEFAULT_STYLE}.mp4"
        video_path = render_video(html_path, audio_path, video_path)
        if video_path:
            print("   ✅ 视频渲染完成")
        else:
            print("   ⚠️  视频渲染失败，但 HTML 文件已生成")
    else:
        print("\n⚠️  HyperFrames 未安装，跳过视频渲染")
        print("   安装方法: npm install -g hyperframes")
        print("   HTML 文件已生成，可手动渲染")

    # 输出摘要
    print_summary(
        output_dir,
        {DEFAULT_STYLE: (srt_path, txt_path)},
        {DEFAULT_STYLE: audio_path},
        image_files,
        {DEFAULT_STYLE: html_path},
        {DEFAULT_STYLE: video_path} if video_path else None,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  用户中断，已退出。")
