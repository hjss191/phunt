"""SRT alignment — Whisper word timestamps + sliding window Levenshtein matching."""

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
    """Get word-level timestamps and text from Whisper.

    Returns:
        List of {"start": float, "end": float, "text": str} dicts.
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

    # Extract word timestamps AND text for matching
    words = []
    for seg in segments:
        for word in seg.words:
            text = word.word.strip()
            if text:
                words.append({
                    "start": word.start,
                    "end": word.end,
                    "text": text,
                })

    return words


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if not s2:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _normalize(text: str) -> str:
    """Strip punctuation and whitespace for fuzzy matching."""
    return re.sub(r'[^一-鿿a-zA-Z0-9]', '', text)


def _split_sentences(text: str) -> list[str]:
    """Split plain text into sentences by newlines and Chinese punctuation."""
    sentences = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Split by sentence-ending punctuation only (NOT commas)
        parts = re.split(r'(?<=[。！？])', line)
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)
    return sentences


def align_plain(audio_path: Path, plain_text: str,
                model_name: str = "large-v3-turbo") -> list[tuple[int, float, float, str]]:
    """Align plain text to TTS audio using sliding window Levenshtein matching.

    Strategy: for each original sentence, slide a window over the Whisper
    word sequence and find the window whose concatenated text has the minimum
    Levenshtein distance to the sentence. This directly ties each sentence
    to its actual speech timestamps without relying on pause detection.

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

    # Pre-normalize Whisper word texts
    norm_words = [_normalize(w["text"]) for w in words]

    # Sliding window matching for each sentence
    results = []
    last_end_idx = -1  # track consumed position to enforce monotonic advance

    for sent_i, sentence in enumerate(original_sentences):
        norm_sent = _normalize(sentence)
        if not norm_sent:
            continue

        sent_char_len = len(norm_sent)
        # Estimate word count from character count (Chinese: ~1-2 chars per Whisper word)
        est_word_count = max(1, sent_char_len // 2)
        min_win = max(1, est_word_count - 3)
        max_win = min(n_words, est_word_count + 3)

        best_dist = float("inf")
        best_start = last_end_idx + 1
        best_end = min(best_start, n_words - 1)

        search_from = last_end_idx + 1
        for win_size in range(min_win, max_win + 1):
            for i in range(search_from, n_words - win_size + 1):
                j = i + win_size - 1
                candidate = "".join(norm_words[i:j + 1])
                dist = _levenshtein(norm_sent, candidate)
                if dist < best_dist:
                    best_dist = dist
                    best_start = i
                    best_end = j

        # Warn if match quality is poor
        quality = best_dist / max(sent_char_len, 1)
        if quality > 0.6:
            print(f"   ⚠️  句{sent_i+1} 匹配质量较差 (距离={best_dist}, 比例={quality:.2f}): 「{sentence[:20]}...」")

        start_time = words[best_start]["start"]
        end_time = words[best_end]["end"]
        results.append((sent_i + 1, start_time, end_time, sentence))
        last_end_idx = best_end

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
