"""Video generation — renders HyperFrames HTML to MP4 using HyperFrames CLI."""

import subprocess
import shutil
from pathlib import Path


def check_hyperframes_available() -> bool:
    """Check if HyperFrames CLI is available."""
    return shutil.which("npx") is not None


def render_video(
    html_path: Path,
    audio_path: Path,
    output_path: Path,
    width: int = 1080,
    height: int = 1920,
) -> Path | None:
    """Render HyperFrames HTML to MP4 video.

    Args:
        html_path: Path to the HyperFrames HTML file.
        audio_path: Path to the audio file.
        output_path: Path for the output MP4 file.
        width: Video width (default 1080).
        height: Video height (default 1920).

    Returns:
        Path to the rendered MP4 file, or None if rendering failed.
    """
    if not check_hyperframes_available():
        print("  ⚠️  npx 不可用，请安装 Node.js 22+")
        print("     下载地址: https://nodejs.org/")
        return None

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 复制音频到 HTML 同目录（HyperFrames 需要）
    audio_dest = html_path.parent / audio_path.name
    if not audio_dest.exists():
        shutil.copy2(audio_path, audio_dest)

    print("  🎬  渲染视频...")
    print(f"     HTML: {html_path}")
    print(f"     音频: {audio_path}")
    print(f"     输出: {output_path}")

    try:
        # 使用 hyperframes render 命令
        cmd = [
            "npx", "hyperframes", "render",
            "--input", str(html_path),
            "--output", str(output_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时
            cwd=html_path.parent,
        )

        if result.returncode == 0:
            print(f"   ✅ 视频渲染完成: {output_path.name}")
            return output_path
        else:
            print(f"   ⚠️  渲染失败:")
            print(f"     {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print("   ⚠️  渲染超时（5分钟）")
        return None
    except FileNotFoundError:
        print("   ⚠️  npx 命令未找到，请安装 Node.js")
        return None
    except Exception as e:
        print(f"   ⚠️  渲染异常: {e}")
        return None
