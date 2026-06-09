"""SRT alignment — Whisper timestamps + LLM original text."""

import json
import os
import re
import site
from difflib import SequenceMatcher
from pathlib import Path
from zhconv import convert

# Add NVIDIA DLL directories to search path (for CTranslate2 CUDA support)
for sp in site.getsitepackages() + [site.getusersitepackages()]:
    nvidia_bin = os.path.join(sp, "nvidia", "cublas", "bin")
    if os.path.isdir(nvidia_bin):
        os.add_dll_directory(nvidia_bin)
    nvidia_nvrtc = os.path.join(sp, "nvidia", "cuda_nvrtc", "bin")
    if os.path.isdir(nvidia_nvrtc):
        os.add_dll_directory(nvidia_nvrtc)

from faster_whisper import WhisperModel


def _clean(s: str) -> str:
    """Remove punctuation for matching."""
    return re.sub(
        r"[，。？！：；、""''（）…—～~《》\s,\.!\?;:\'\"\-]", "", s
    )


def _similarity(a: str, b: str) -> float:
    """Similarity ratio between two cleaned strings."""
    return SequenceMatcher(None, _clean(a), _clean(b)).ratio()


def _whisper_duration(audio_path: Path, model_name: str = "large-v3-turbo") -> float:
    """Get total audio duration using Whisper."""
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
        temperature=0,
        no_speech_threshold=0.3,
        condition_on_previous_text=False,
    )
    print(f"  语言: {info.language} (概率: {info.language_probability:.3f})")

    # Get total duration from last segment
    last_end = 0.0
    for seg in segments:
        last_end = max(last_end, seg.end)

    return last_end


def _allocate_time(sentences: list[str], total_duration: float) -> list[tuple]:
    """Allocate time proportionally based on character count.

    Args:
        sentences: List of original sentences.
        total_duration: Total audio duration in seconds.

    Returns:
        List of (idx, start, end, text) tuples.
    """
    # Count characters per sentence (excluding punctuation)
    char_counts = []
    for sent in sentences:
        cleaned = _clean(sent)
        char_counts.append(max(len(cleaned), 1))  # At least 1 char

    total_chars = sum(char_counts)

    # Allocate time proportionally
    results = []
    current_time = 0.0

    for i, (sent, count) in enumerate(zip(sentences, char_counts)):
        duration = (count / total_chars) * total_duration
        start = current_time
        end = current_time + duration
        results.append((i + 1, start, end, sent))
        current_time = end

    return results


def _split_sentences(text: str) -> list[str]:
    """Split plain text into sentences by newlines and Chinese punctuation."""
    sentences = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = re.split(r'(?<=[。！？])', line)
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)
    return sentences


def align_plain(audio_path: Path, plain_text: str,
                model_name: str = "large-v3-turbo") -> list[tuple[int, float, float, str]]:
    """Align plain text to TTS audio using Whisper duration.

    1. Whisper gets total audio duration
    2. Time is allocated proportionally based on character count
    3. No text matching needed

    Args:
        audio_path: Path to the TTS audio file (mp3).
        plain_text: Original plain text from LLM.
        model_name: Whisper model name (default large-v3-turbo).

    Returns:
        List of (index, start_seconds, end_seconds, text) tuples.
    """
    original_sentences = _split_sentences(plain_text)
    print(f"  原文分句: {len(original_sentences)} 句")

    total_duration = _whisper_duration(audio_path, model_name)
    print(f"  音频时长: {total_duration:.1f}s")

    results = _allocate_time(original_sentences, total_duration)

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
