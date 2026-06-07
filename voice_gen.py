"""Voice generation — converts copy text to audio using MiMo TTS API."""

import base64
from pathlib import Path
from openai import OpenAI
from config import MIMO_TTS_API_KEY, MIMO_TTS_BASE_URL


def generate_voice(text: str, output_path: Path) -> Path:
    """Generate TTS audio from text.

    Args:
        text: The text to convert to speech (placed in assistant role).
        output_path: Where to save the .mp3 file.

    Returns:
        Path to the generated audio file.
    """
    client = OpenAI(api_key=MIMO_TTS_API_KEY, base_url=MIMO_TTS_BASE_URL)

    completion = client.chat.completions.create(
        model="mimo-v2.5-tts",
        messages=[
            {
                "role": "user",
                "content": "用自然亲切的语调朗读，语速适中，像朋友分享好东西一样。",
            },
            {
                "role": "assistant",
                "content": text,
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


def generate_voices_for_copies(
    copies: dict[str, str],
    output_dir: Path,
) -> dict[str, Path]:
    """Generate audio for all copy variants.

    Args:
        copies: {style_key: copy_text}
        output_dir: Directory to save audio files.

    Returns:
        {style_key: audio_path}
    """
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for style_key, text in copies.items():
        filename = f"{style_key}.mp3"
        audio_path = audio_dir / filename
        print(f"  🎙️  生成配音: {filename}...")
        try:
            results[style_key] = generate_voice(text, audio_path)
        except Exception as e:
            print(f"  ⚠️  配音生成失败 ({filename}): {e}")
            results[style_key] = None

    return results
