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
        vad_filter=False,
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

    Strategy: for each sentence, find the pause boundary closest to its
    proportional position in the audio. This respects both the original
    sentence structure and the actual speech rhythm.

    Args:
        audio_path: Path to the TTS audio file (mp3).
        plain_text: Original plain text from LLM.
        model_name: Whisper model name (default large-v3-turbo).

    Returns:
        List of (index, start_seconds, end_seconds, text) tuples.
    """
    original_sentences = _split_sentences(plain_text)
    n_sent = len(original_sentences)
    print(f"  原文分句: {n_sent} 句")

    words = _whisper_words(audio_path, model_name)
    n_words = len(words)
    print(f"  Whisper 词数: {n_words} 词")

    if not words:
        print("  ⚠️  Whisper 未识别到任何词")
        return []

    total_duration = words[-1]["end"]
    print(f"  音频时长: {total_duration:.1f}s")

    if n_sent <= 1:
        return [(1, words[0]["start"], words[-1]["end"], original_sentences[0])]

    # Detect pauses (gaps between consecutive words)
    pauses = []  # [(word_idx, gap_duration, time_position)]
    for i in range(1, n_words):
        gap = words[i]["start"] - words[i - 1]["end"]
        pauses.append({"idx": i, "gap": gap, "time": words[i]["start"]})

    # For each sentence boundary (between sentence i and i+1),
    # find the pause closest to the expected proportional time
    sent_chars = [len(re.findall(r'[一-鿿]', s)) + len(re.findall(r'[a-zA-Z]', s))
                  for s in original_sentences]
    total_chars = sum(sent_chars)

    # Expected time for each sentence boundary
    boundary_times = []
    cum_chars = 0
    for i in range(n_sent - 1):
        cum_chars += sent_chars[i]
        boundary_times.append(cum_chars / total_chars * total_duration)

    # For each boundary, find the best pause (closest in time, with preference for larger gaps)
    cut_indices = []
    used = set()
    for target_time in boundary_times:
        best = None
        best_score = -1
        for p in pauses:
            if p["idx"] in used:
                continue
            # Score: prefer pauses close to target time, with slight bias for larger gaps
            time_diff = abs(p["time"] - target_time)
            # Proximity is dominant factor; gap size is tiebreaker
            score = p["gap"] * 0.1 - time_diff
            if score > best_score:
                best_score = score
                best = p
        if best:
            cut_indices.append(best["idx"])
            used.add(best["idx"])

    cut_indices.sort()
    print(f"  切分点: {len(cut_indices)} 个")

    # Split words into groups at cut points
    groups = []
    prev = 0
    for cut in cut_indices:
        groups.append((prev, cut - 1))
        prev = cut
    groups.append((prev, n_words - 1))

    results = []
    for i, (w_start, w_end) in enumerate(groups):
        start = words[w_start]["start"]
        end = words[w_end]["end"]
        results.append((i + 1, start, end, original_sentences[i]))

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
