"""视频配音工具 — TTS语音 + Whisper字幕对齐 + 烧录

用法:
    python video_dub.py --video input.mp4 --text "要配音的文案" [--voice 苏打] [--style "播报风格"]

示例:
    python video_dub.py --video video/m2-res_360p.mp4 --text "就在刚刚，Figure AI庆祝了一个里程碑..."
"""

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from openai import OpenAI
from dotenv import load_dotenv
import os

from aligner import align_plain, save_aligned_srt

load_dotenv()

# === 默认配置 ===
DEFAULT_VOICE = "苏打"
DEFAULT_STYLE = "用沉稳、专业的新闻播报语气，语速适中，语调自然平稳。"
DEFAULT_FONT_SIZE = 18
DEFAULT_ORIGINAL_VOLUME = 0.3  # 原视频音量


def generate_tts(text: str, output_path: Path, voice: str = DEFAULT_VOICE, style: str = DEFAULT_STYLE) -> Path:
    """调用 MiMo TTS 生成语音"""
    client = OpenAI(api_key=os.getenv("MIMO_TTS_API_KEY"), base_url=os.getenv("MIMO_TTS_BASE_URL"))

    print(f"🎙️ 生成语音: {voice}...")
    print(f"📝 文案: {text[:60]}...")

    completion = client.chat.completions.create(
        model="mimo-v2.5-tts",
        messages=[
            {"role": "user", "content": style},
            {"role": "assistant", "content": text},
        ],
        audio={"format": "mp3", "voice": voice},
    )

    audio_bytes = base64.b64decode(completion.choices[0].message.audio.data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    print(f"✅ 语音已保存: {output_path} ({len(audio_bytes)} bytes)")
    return output_path


def align_subtitles(audio_path: Path, text: str, srt_path: Path) -> Path:
    """用 Whisper 对齐字幕"""
    print("\n📐 Whisper 字幕对齐...")
    alignment = align_plain(audio_path, text)
    save_aligned_srt(alignment, srt_path)
    print(f"✅ 字幕已保存: {srt_path}")
    return srt_path


def burn_subtitles(video_path: Path, audio_path: Path, srt_path: Path, output_path: Path,
                   font_size: int = DEFAULT_FONT_SIZE, original_volume: float = DEFAULT_ORIGINAL_VOLUME):
    """烧录字幕 + 混合音频"""
    # 字幕路径转义
    srt_esc = str(srt_path).replace("\\", "/").replace(":", "\\:")
    sub_filter = (
        f"subtitles='{srt_esc}':force_style='"
        f"FontName=Microsoft YaHei,"
        f"FontSize={font_size},"
        f"PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,"
        f"Outline=3,"
        f"Shadow=1,"
        f"Alignment=6,"
        f"MarginV=10'"
    )

    # 混合原声 + 配音
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter_complex",
        f"[0:v]{sub_filter}[v];"
        f"[0:a]volume={original_volume}[orig];"
        f"[orig][1:a]amix=inputs=2:duration=first[a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(output_path),
    ]

    print("\n🎬 合成视频...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ ffmpeg 错误:\n{result.stderr[-500:]}")
        sys.exit(1)

    print(f"✅ 视频已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="视频配音工具")
    parser.add_argument("--video", required=True, help="输入视频路径")
    parser.add_argument("--text", required=True, help="配音文案")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="TTS音色 (默认: 苏打)")
    parser.add_argument("--style", default=DEFAULT_STYLE, help="语音风格提示词")
    parser.add_argument("--font-size", type=int, default=DEFAULT_FONT_SIZE, help="字幕字号 (默认: 22)")
    parser.add_argument("--original-volume", type=float, default=DEFAULT_ORIGINAL_VOLUME, help="原视频音量 0-1 (默认: 0.3)")
    parser.add_argument("--output", help="输出路径 (默认: 输入文件名_dubbed.mp4)")

    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"❌ 视频不存在: {video_path}")
        sys.exit(1)

    # 输出目录（按日期）
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path("video") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    # 输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = output_dir / f"{video_path.stem}_dubbed{video_path.suffix}"

    # 中间文件（保存到日期目录）
    audio_path = output_dir / "voiceover.mp3"
    srt_path = output_dir / "subtitles.srt"

    print("=" * 50)
    print("🎬 视频配音工具")
    print("=" * 50)

    # 1. 生成语音
    generate_tts(args.text, audio_path, args.voice, args.style)

    # 2. Whisper 对齐字幕
    align_subtitles(audio_path, args.text, srt_path)

    # 3. 烧录字幕 + 混合音频
    burn_subtitles(video_path, audio_path, srt_path, output_path, args.font_size, args.original_volume)

    print("\n🎉 完成！")


if __name__ == "__main__":
    main()
