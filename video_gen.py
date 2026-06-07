"""Video generation — renders HyperFrames HTML to MP4 using HyperFrames CLI."""

import subprocess
import shutil
import sys
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
    # 验证输入文件存在
    if not html_path.is_file():
        print(f"  ⚠️  HTML 文件不存在: {html_path}")
        return None
    if not audio_path.is_file():
        print(f"  ⚠️  音频文件不存在: {audio_path}")
        return None

    if not check_hyperframes_available():
        print("  ⚠️  npx 不可用，请安装 Node.js 22+")
        print("     下载地址: https://nodejs.org/")
        return None

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 复制音频到 HTML 同目录 — HyperFrames 通过约定（同目录同名）自动发现音频文件，
    # 所以 render 命令中不需要显式传入 audio_path 参数。
    # 参见: https://hyperframes.dev/docs/conventions
    audio_dest = html_path.parent / audio_path.name
    if not audio_dest.exists():
        shutil.copy2(audio_path, audio_dest)

    # HyperFrames 默认查找 index.html，必须创建 index.html
    index_path = html_path.parent / "index.html"
    if not index_path.exists():
        shutil.copy2(html_path, index_path)

    print("  🎬  渲染视频...")
    print(f"     HTML: {html_path}")
    print(f"     音频: {audio_path}")
    print(f"     输出: {output_path}")

    try:
        # HyperFrames render 需要目录作为输入，用 -c 指定 composition 文件
        project_dir = html_path.parent
        cmd = [
            "npx", "hyperframes", "render",
            str(project_dir),
            "-c", html_path.name,
            "-o", str(output_path),
        ]

        # Windows 上 npx 实际是 npx.cmd，需要 shell=True 才能找到
        use_shell = sys.platform == "win32"

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时
            cwd=html_path.parent,
            shell=use_shell,
        )

        if result.returncode == 0:
            # HyperFrames 默认输出到 renders 子目录，需要移动到目标位置
            renders_dir = project_dir / "renders"
            if renders_dir.exists():
                # 找到最新的 mp4 文件
                mp4_files = list(renders_dir.glob("*.mp4"))
                if mp4_files:
                    latest_mp4 = max(mp4_files, key=lambda f: f.stat().st_mtime)
                    shutil.move(str(latest_mp4), str(output_path))
                    print(f"   ✅ 视频渲染完成: {output_path.name}")
                    return output_path
            # 如果找不到，返回原路径
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
