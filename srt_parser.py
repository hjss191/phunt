"""SRT 字幕解析工具 — 解析 SRT 格式，提取时间戳和文本。"""

import re
from dataclasses import dataclass


@dataclass
class SrtEntry:
    """一条 SRT 字幕记录。"""
    index: int
    start: float  # 秒
    end: float    # 秒
    text: str

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_srt_block(self) -> str:
        """转回 SRT 格式文本块。"""
        start_str = seconds_to_srt_time(self.start)
        end_str = seconds_to_srt_time(self.end)
        return f"{self.index}\n{start_str} --> {end_str}\n{self.text}\n"


def _srt_time_to_seconds(time_str: str) -> float:
    """将 SRT 时间格式 (HH:MM:SS,mmm) 转换为秒数。"""
    time_str = time_str.strip()
    # 支持逗号和句号作为毫秒分隔符
    time_str = time_str.replace(",", ".")
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def seconds_to_srt_time(seconds: float) -> str:
    """将秒数转换为 SRT 时间格式 (HH:MM:SS,mmm)。"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    whole_secs = int(secs)
    millis = int((secs - whole_secs) * 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_secs:02d},{millis:03d}"


def parse_srt(srt_text: str) -> list[SrtEntry]:
    """解析 SRT 格式文本，返回字幕条目列表。

    Args:
        srt_text: SRT 格式的文本内容。

    Returns:
        SrtEntry 列表。
    """
    entries = []
    # 按空行分割字幕块
    blocks = re.split(r"\n\s*\n", srt_text.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        # 第一行：序号
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        # 第二行：时间戳
        time_match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            lines[1].strip(),
        )
        if not time_match:
            continue

        start = _srt_time_to_seconds(time_match.group(1))
        end = _srt_time_to_seconds(time_match.group(2))

        # 第三行起：文本
        text = "\n".join(lines[2:]).strip()

        entries.append(SrtEntry(index=index, start=start, end=end, text=text))

    return entries


def extract_text(entries: list[SrtEntry]) -> str:
    """从 SRT 条目中提取纯文本（用于 TTS）。

    Args:
        entries: SrtEntry 列表。

    Returns:
        用换行符连接的纯文本。
    """
    return "\n".join(entry.text for entry in entries)


def srt_to_text(srt_text: str) -> str:
    """从 SRT 格式文本中提取纯文本。

    Args:
        srt_text: SRT 格式的文本内容。

    Returns:
        用换行符连接的纯文本。
    """
    entries = parse_srt(srt_text)
    return extract_text(entries)


def build_srt(entries: list[SrtEntry]) -> str:
    """将 SrtEntry 列表转回 SRT 格式文本。

    Args:
        entries: SrtEntry 列表。

    Returns:
        SRT 格式文本。
    """
    return "\n".join(entry.to_srt_block() for entry in entries)


def estimate_srt_from_text(text: str, chars_per_second: float = 4.5, pause: float = 0.4) -> list[SrtEntry]:
    """从纯文本估算生成 SRT 条目（用于 LLM 未输出 SRT 时的回退方案）。

    Args:
        text: 纯文本，每行一句话。
        chars_per_second: 中文语速（字/秒）。
        pause: 句间停顿（秒）。

    Returns:
        SrtEntry 列表。
    """
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    entries = []
    current_time = 0.0

    for i, line in enumerate(lines, 1):
        duration = len(line) / chars_per_second
        entries.append(SrtEntry(
            index=i,
            start=current_time,
            end=current_time + duration,
            text=line,
        ))
        current_time += duration + pause

    return entries
