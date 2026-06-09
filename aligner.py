"""SRT alignment — Whisper word timestamps + LLM original text."""

import json
import os
import re
import site
from pathlib import Path
from zhconv import convert

# Add NVIDIA DLL directories to search path (for CTranslate2 CUDA support)
_dll_dirs = []
for sp in site.getsitepackages() + [site.getusersitepackages()]:
    for sub in ("nvidia/cublas/bin", "nvidia/cuda_nvrtc/bin"):
        dll_dir = os.path.join(sp, sub)
        if os.path.isdir(dll_dir):
            _dll_dirs.append(dll_dir)
if _dll_dirs:
    os.environ["PATH"] = ";".join(_dll_dirs) + ";" + os.environ.get("PATH", "")
    os.environ["CT2_CUDA_LIBRARY_PATH"] = ";".join(_dll_dirs)
    for d in _dll_dirs:
        os.add_dll_directory(d)

from faster_whisper import WhisperModel


def _whisper_words(audio_path: Path, model_name: str = "large-v3-turbo",
                   initial_prompt: str = "") -> list[dict]:
    """Get word-level timestamps from Whisper.

    Returns:
        List of {"start": float, "end": float} dicts (no text).
    """
    # Auto-detect GPU via CTranslate2
    try:
        import ctranslate2
        device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
    except ImportError:
        device = "cpu"
        compute_type = "int8"

    print(f"  加载 Whisper 模型 ({model_name}, device={device}, compute={compute_type})...")
    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    print("  转录音频...")
    segments, info = model.transcribe(
        str(audio_path),
        language="zh",
        beam_size=5,
        temperature=0,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        word_timestamps=True,
        initial_prompt=initial_prompt if initial_prompt else None,
    )
    print(f"  语言: {info.language} (概率: {info.language_probability:.3f})")

    # Extract word timestamps only (ignore text)
    words = []
    for seg in segments:
        for word in seg.words:
            words.append({
                "start": word.start,
                "end": word.end,
            })

    return words


def _split_sentences(text: str) -> list[str]:
    """Split plain text into sentences by newlines and Chinese punctuation."""
    sentences = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Split by Chinese punctuation
        parts = re.split(r'(?<=[。！？])', line)
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)
    return sentences


def align_plain(audio_path: Path, plain_text: str,
                model_name: str = "large-v3-turbo") -> list[tuple[int, float, float, str]]:
    """Align plain text to TTS audio using Whisper word timestamps.

    1. Whisper outputs word-level timestamps (only timestamps, not text)
    2. Original text is split into sentences by punctuation
    3. Timestamps are assigned to sentences by order

    Args:
        audio_path: Path to the TTS audio file (mp3).
        plain_text: Original plain text from LLM.
        model_name: Whisper model name (default large-v3-turbo).

    Returns:
        List of (index, start_seconds, end_seconds, text) tuples.
    """
    # Split original text into sentences
    original_sentences = _split_sentences(plain_text)
    print(f"  原文分句: {len(original_sentences)} 句")

    # Get word timestamps from Whisper
    initial_prompt = plain_text[:50] if plain_text else ""
    words = _whisper_words(audio_path, model_name, initial_prompt)
    print(f"  Whisper 词数: {len(words)} 词")

    if not words:
        print("  ⚠️  Whisper 未识别到任何词")
        return []

    # Calculate total duration
    total_duration = words[-1]["end"]
    print(f"  音频时长: {total_duration:.1f}s")

    # Assign timestamps to sentences by word count proportion
    total_words = len(words)
    results = []
    word_idx = 0

    for i, sent in enumerate(original_sentences):
        # Count characters in sentence (excluding punctuation)
        sent_clean = re.sub(r'[，。？！：；、""''（）…—～~《》\s,\.!\?;:\'\"\-]', '', sent)
        char_count = max(len(sent_clean), 1)

        # Calculate how many words this sentence should get
        # (proportional to character count)
        total_chars = sum(
            len(re.sub(r'[，。？！：；、""''（）…—～~《》\s,\.!\?;:\'\"\-]', '', s))
            for s in original_sentences
        )
        word_count = max(1, round(char_count / total_chars * total_words))

        # Get start/end from word timestamps
        start = words[word_idx]["start"] if word_idx < total_words else total_duration
        end_idx = min(word_idx + word_count - 1, total_words - 1)
        end = words[end_idx]["end"] if end_idx < total_words else total_duration

        results.append((i + 1, start, end, sent))
        word_idx += word_count

    # Stats
    print(f"  对齐完成: {len(results)} 句, 总时长 {total_duration:.1f}s")

    return results


def save_aligned_srt(alignment: list, output_path: Path) -> Path:
    """Save aligned results as an SRT file."""
    lines = []
    for idx, start, end, text in alignment:
        h1, m1 = int(start // 3600), int((start % 3600) // 60)
        s1 = start % 60
        h2, m2 = int(end // 3600), int((end % 3600) // 60)
        s2 = end % 60
        ts1 = f"{h1:02d}:{m1:02d}:{s1:06.3f}".replace(".", ",")
        ts2 = f"{h2:02d}:{m2:02d}:{s2:06.3f}".replace(".", ",")
        lines.append(f"{idx}\n{ts1} --> {ts2}\n{text}\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output_path


def save_alignment_json(alignment: list, output_path: Path) -> Path:
    """Save alignment data as JSON for html_gen consumption."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            [(idx, start, end, text) for idx, start, end, text in alignment],
            f, ensure_ascii=False, indent=2,
        )
    return output_path
