"""Voice generation — converts copy text to audio using MiMo TTS API."""

import base64
import re
import random
from pathlib import Path
from openai import OpenAI
from config import MIMO_TTS_API_KEY, MIMO_TTS_BASE_URL
from srt_parser import srt_to_text


def strip_markdown(text: str) -> str:
    """Remove markdown formatting for clean TTS reading."""
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def generate_voice(text: str, output_path: Path) -> Path:
    """Generate TTS audio from text.

    Args:
        text: The text to convert to speech (placed in assistant role).
        output_path: Where to save the .mp3 file.

    Returns:
        Path to the generated audio file.
    """
    clean_text = strip_markdown(text)
    print(f"   📝 TTS 文本预览: {clean_text[:100]}...")
    print(f"   📝 TTS 文本长度: {len(clean_text)} 字")

    client = OpenAI(api_key=MIMO_TTS_API_KEY, base_url=MIMO_TTS_BASE_URL)

    completion = client.chat.completions.create(
        model="mimo-v2.5-tts",
        messages=[
            {
                "role": "user",
                "content": "逐字朗读以下文本，不要修改、省略或改写任何内容。语速稍快，有节奏感，语调富有感染力。",
            },
            {
                "role": "assistant",
                "content": clean_text,
            },
        ],
        audio={
            "format": "mp3",
            "voice": "冰糖",
        },
    )

    message = completion.choices[0].message
    audio_bytes = base64.b64decode(message.audio.data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    return output_path


def generate_voice_from_srt(srt_text: str, output_path: Path) -> Path:
    """Generate TTS audio from SRT text (extracts plain text first).

    Args:
        srt_text: SRT 格式文本。
        output_path: Where to save the .mp3 file.

    Returns:
        Path to the generated audio file.
    """
    plain_text = srt_to_text(srt_text)
    return generate_voice(plain_text, output_path)


def generate_voices_for_copies(
    copies: dict[str, tuple[str, str]],
    output_dir: Path,
) -> dict[str, Path]:
    """Generate audio for all copy variants.

    Args:
        copies: {style_key: (srt_text, plain_text)}
        output_dir: Directory to save audio files.

    Returns:
        {style_key: audio_path}
    """
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for style_key, (srt_text, plain_text) in copies.items():
        filename = f"{style_key}.mp3"
        audio_path = audio_dir / filename
        print(f"  🎙️  生成配音: {filename}...")
        try:
            results[style_key] = generate_voice(plain_text, audio_path)
        except Exception as e:
            print(f"  ⚠️  配音生成失败 ({filename}): {e}")
            results[style_key] = None

    return results
