"""Main entry point — orchestrates the full daily workflow."""

from config import validate_config
from phunt_client import fetch_top_products, display_products, select_product
from copywriter import generate_copies
from voice_gen import generate_voices_for_copies
from image_gen import generate_product_images
from formatter import get_output_dir, save_copies, print_summary


def main():
    """Run the daily Product Hunt content generation workflow."""
    print("=" * 50)
    print("  🚀 Product Hunt 每日精选 → 多平台内容生成")
    print("=" * 50)

    # Step 0: Validate config
    print("\n📋 检查配置...")
    validate_config()
    print("   ✅ 配置检查通过")

    # Step 1: Fetch top products
    print("\n📡 拉取 Product Hunt 今日 Top 5...")
    products = fetch_top_products(5)
    display_products(products)

    # Step 2: User selects a product
    product = select_product(products)
    print(f"\n✅ 已选择: {product['name']}")
    print(f"   {product['tagline']}")

    # Step 3: Generate copies
    print("\n✍️  开始生成文案 (3风格 × 3平台)...")
    copies = generate_copies(product)
    print("   ✅ 文案生成完成")

    # Step 4: Generate voice
    print("\n🎙️  开始生成配音...")
    output_dir = get_output_dir()
    audio_files = generate_voices_for_copies(copies, output_dir)
    print("   ✅ 配音生成完成")

    # Step 5: Generate images
    print("\n🎨 开始生成配图...")
    image_files = generate_product_images(product, output_dir)
    print("   ✅ 配图生成完成")

    # Step 6: Save and summarize
    copy_files = save_copies(copies, output_dir)
    print_summary(output_dir, copy_files, audio_files, image_files)


if __name__ == "__main__":
    main()
