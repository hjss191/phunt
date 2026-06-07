"""Voice generation — converts copy text to audio using MiMo TTS API."""

import httpx
from pathlib import Path
from config import MIMO_TTS_API_KEY, MIMO_TTS_BASE_URL


def generate_voice(text: str, output_path: Path) -> Path:
    """Generate TTS audio from text.

    Args:
        text: The text to convert to speech.
        output_path: Where to save the .mp3 file.

    Returns:
        Path to the generated audio file.
    """
    headers = {
        "Authorization": f"Bearer {MIMO_TTS_API_KEY}",
        "Content-Type": "application/json",
    }

    # MiMo TTS API — OpenAI compatible format
    # NOTE: Verify exact endpoint and model name with your MiMo TTS provider
    payload = {
        "model": "mimo-tts",
        "input": text,
        "voice": "zh-CN-Default",  # Chinese voice
        "response_format": "mp3",
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{MIMO_TTS_BASE_URL}/audio/speech",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)

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
