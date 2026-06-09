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


def _whisper_transcribe(audio_path: Path, model_name: str = "large-v3-turbo"):
    """Transcribe audio with Whisper, return segments with timestamps."""
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
        word_timestamps=True,
    )
    print(f"  语言: {info.language} (概率: {info.language_probability:.3f})")

    words = []
    for seg in segments:
        for word in seg.words:
            text = convert(word.word.strip(), "zh-cn")
            if text:
                words.append({
                    "start": word.start,
                    "end": word.end,
                    "text": text,
                })

    return words


def _match_to_original(whisper_words: list[dict],
                       original_sentences: list[str]) -> list[tuple]:
    """Match Whisper word timestamps to original sentences.

    Strategy: use word-level timestamps from Whisper to build sentence-level
    timestamps for the original text. Each word is matched to the original
    sentence that contains it.

    Returns list of (idx, start, end, original_text) tuples.
    """
    results = []

    # Build a combined text from Whisper words
    whisper_text = "".join(w["text"] for w in whisper_words)

    # For each original sentence, find matching words
    for i, sent in enumerate(original_sentences):
        sent_clean = _clean(sent)
        if not sent_clean:
            continue

        # Find words that contribute to this sentence
        matched_words = []
        for word in whisper_words:
            word_clean = _clean(word["text"])
            if word_clean and word_clean in sent_clean:
                matched_words.append(word)

        if matched_words:
            # Use first and last matched word timestamps
            start = matched_words[0]["start"]
            end = matched_words[-1]["end"]
            results.append((i + 1, start, end, sent))
        else:
            # No match found — use previous sentence's end time
            if results:
                prev_end = results[-1][2]
                results.append((i + 1, prev_end, prev_end + 2.0, sent))
            else:
                results.append((i + 1, 0.0, 2.0, sent))

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
    """Align plain text to TTS audio using Whisper word-level timestamps.

    1. Whisper transcribes audio → word-level timestamps
    2. Each word is matched to the original sentence that contains it
    3. Sentence timestamps = first word start to last word end

    Args:
        audio_path: Path to the TTS audio file (mp3).
        plain_text: Original plain text from LLM.
        model_name: Whisper model name (default large-v3-turbo).

    Returns:
        List of (index, start_seconds, end_seconds, text) tuples.
    """
    original_sentences = _split_sentences(plain_text)
    print(f"  原文分句: {len(original_sentences)} 句")

    whisper_words = _whisper_transcribe(audio_path, model_name)
    print(f"  Whisper 词数: {len(whisper_words)} 词, "
          f"覆盖 {whisper_words[0]['start']:.1f}-{whisper_words[-1]['end']:.1f}s")

    results = _match_to_original(whisper_words, original_sentences)

    # Stats
    total_duration = results[-1][2] if results else 0
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
