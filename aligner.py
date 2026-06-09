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


def _whisper_transcribe(audio_path: Path, model_name: str = "large-v3-turbo",
                        initial_prompt: str = ""):
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
        beam_size=5,
        word_timestamps=True,
        no_speech_threshold=0.3,
        condition_on_previous_text=False,
        initial_prompt=initial_prompt if initial_prompt else None,
    )
    print(f"  语言: {info.language} (概率: {info.language_probability:.3f})")

    result = []
    for seg in segments:
        text = convert(seg.text.strip(), "zh-cn")
        if text:
            result.append({
                "start": seg.start,
                "end": seg.end,
                "text": text,
            })

    return result


def _match_to_original(whisper_segments: list[dict],
                       original_sentences: list[str]) -> list[tuple]:
    """Match Whisper segments to original sentences.

    Strategy: each Whisper segment may contain multiple original sentences.
    For each segment, find all original sentences that are contained in it
    (using fuzzy matching). Each original sentence can only be used once.

    Returns list of (idx, start, end, original_text) tuples.
    """
    used = set()
    results = []

    for seg in whisper_segments:
        seg_text = _clean(seg["text"])
        matched_in_seg = []

        # Find all original sentences contained in this segment
        for i, sent in enumerate(original_sentences):
            if i in used:
                continue
            sent_clean = _clean(sent)
            # Check if the original sentence is contained in the segment
            if len(sent_clean) >= 2 and sent_clean in seg_text:
                matched_in_seg.append(i)
            else:
                # Fallback: use similarity score with lower threshold
                score = _similarity(seg["text"], sent)
                if score >= 0.5:
                    matched_in_seg.append(i)

        if matched_in_seg:
            # Distribute time evenly among matched sentences
            duration = seg["end"] - seg["start"]
            time_per_sent = duration / len(matched_in_seg)
            for j, idx in enumerate(matched_in_seg):
                used.add(idx)
                start = seg["start"] + j * time_per_sent
                end = start + time_per_sent
                results.append((
                    len(results) + 1,
                    start,
                    end,
                    original_sentences[idx],
                ))
        else:
            # No match found — use Whisper's own text
            results.append((
                len(results) + 1,
                seg["start"],
                seg["end"],
                seg["text"],
            ))

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
    """Align plain text to TTS audio using Whisper segments.

    1. Whisper transcribes audio → segments with accurate timestamps
    2. Each segment is matched to the best matching original sentence
    3. Output: Whisper timestamps + original text

    Args:
        audio_path: Path to the TTS audio file (mp3).
        plain_text: Original plain text from LLM.
        model_name: Whisper model name (default large-v3-turbo).

    Returns:
        List of (index, start_seconds, end_seconds, text) tuples.
    """
    original_sentences = _split_sentences(plain_text)
    print(f"  原文分句: {len(original_sentences)} 句")

    # Use first 50 chars of original text as initial prompt
    initial_prompt = plain_text[:50] if plain_text else ""

    whisper_segments = _whisper_transcribe(audio_path, model_name, initial_prompt)
    print(f"  Whisper 段落: {len(whisper_segments)} 段, "
          f"覆盖 {whisper_segments[0]['start']:.1f}-{whisper_segments[-1]['end']:.1f}s")

    results = _match_to_original(whisper_segments, original_sentences)

    # Stats
    matched = sum(1 for r in results if r[3] in original_sentences)
    print(f"  匹配: {matched}/{len(results)} 段, 总时长 {results[-1][2]:.1f}s")

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
