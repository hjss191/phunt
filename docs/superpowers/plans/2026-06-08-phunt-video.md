# Product Hunt 视频生成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有文案+配音流程基础上，新增视频生成能力。LLM 生成 SRT 格式文案，SRT 同时驱动 TTS 音频和 HyperFrames HTML 画面，最终渲染成 MP4 视频。

**Architecture:** 改造 copywriter.py 输出 SRT 格式，新增 html_gen.py 生成 HyperFrames HTML，新增 video_gen.py 调用 HyperFrames CLI 渲染。SRT 作为核心桥梁连接音频和画面。

**Tech Stack:** Python 3.10+, openai (MiMo API), HyperFrames (Node.js 22+), FFmpeg

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `copywriter.py` | Modify | 输出 SRT 格式文案 + 纯文本 |
| `voice_gen.py` | Modify | 从 SRT 提取纯文本 |
| `formatter.py` | Modify | 管理新目录结构（html/, video/） |
| `html_gen.py` | Create | LLM 生成 HyperFrames HTML |
| `video_gen.py` | Create | 调用 HyperFrames CLI 渲染视频 |
| `main.py` | Modify | 加入新步骤 |
| `templates/srt_prompt.txt` | Create | SRT 生成 prompt 模板 |
| `templates/html_prompt.txt` | Create | HTML 生成 prompt 模板 |

---

### Task 1: SRT 解析工具函数

**Files:**
- Create: `srt_parser.py`

- [ ] **Step 1: 创建 SRT 解析模块**

```python
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
        start_str = _seconds_to_srt_time(self.start)
        end_str = _seconds_to_srt_time(self.end)
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


def _seconds_to_srt_time(seconds: float) -> str:
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
```

- [ ] **Step 2: 验证模块导入**

Run: `python -c "from srt_parser import parse_srt, srt_to_text, estimate_srt_from_text; print('srt_parser.py OK')"`
Expected: `srt_parser.py OK`

- [ ] **Step 3: Commit**

```bash
git add srt_parser.py
git commit -m "feat: add SRT parser with timestamp extraction and estimation"
```

---

### Task 2: 改造 copywriter.py 输出 SRT 格式

**Files:**
- Modify: `copywriter.py`
- Create: `templates/srt_prompt.txt`

- [ ] **Step 1: 创建 SRT prompt 模板**

```txt
请为以下产品写一篇中文推广文案，以 SRT 字幕格式输出。

产品信息：
- 名称：{name}
- 一句话介绍：{tagline}
- 详细介绍：{description}
- 产品链接：{url}
- 投票数：{votes}
- 相关话题：{topics}

要求：
1. 每句话控制在 10-20 字（适合画面展示）
2. 总共 8-15 句话
3. 按标准 SRT 格式输出（序号、时间戳、文本）
4. 时间戳基于中文语速 ~4.5 字/秒估算，句间停顿 ~0.4 秒
5. {style_description}

SRT 格式示例：
1
00:00:00,000 --> 00:00:03,200
第一句话内容

2
00:00:03,600 --> 00:00:07,100
第二句话内容

请直接输出 SRT 内容，不要加任何前缀说明。
```

- [ ] **Step 2: 改造 copywriter.py**

```python
"""AI copywriter — generates copy in SRT format using MiMo API."""

import json
from pathlib import Path
from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, TEMPLATES_DIR
from srt_parser import parse_srt, extract_text, build_srt, estimate_srt_from_text


def load_templates() -> dict:
    """Load style templates from styles.json."""
    with open(TEMPLATES_DIR / "styles.json", encoding="utf-8") as f:
        return json.load(f)


def load_srt_prompt_template() -> str:
    """Load SRT prompt template."""
    with open(TEMPLATES_DIR / "srt_prompt.txt", encoding="utf-8") as f:
        return f.read()


def build_prompt(product: dict, style: dict) -> str:
    """Build the user prompt for SRT generation."""
    topics_str = ", ".join(product["topics"]) if product["topics"] else "N/A"
    template = load_srt_prompt_template()
    return template.format(
        name=product["name"],
        tagline=product["tagline"],
        description=product["description"],
        url=product["url"],
        votes=product["votes"],
        topics=topics_str,
        style_description=style["description"],
    )


def generate_copy_srt(product: dict, style_key: str = "style_a") -> tuple[str, str]:
    """Generate copy in SRT format for a product.

    Args:
        product: Product dict from phunt_client.
        style_key: Which style to use (default: style_a 口语风).

    Returns:
        (srt_text, plain_text) — SRT 格式文本和纯文本。
    """
    client = OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)
    templates = load_templates()
    style = templates["styles"][style_key]

    print(f"  ✍️  生成 {style['name']}文案（SRT 格式）...")
    prompt = build_prompt(product, style)

    response = client.chat.completions.create(
        model="mimo-v2.5-pro",
        messages=[
            {"role": "system", "content": style["system_prompt"]},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=2000,
    )
    raw_output = response.choices[0].message.content.strip()

    # 尝试解析 SRT
    entries = parse_srt(raw_output)

    if entries:
        # LLM 输出了有效的 SRT
        srt_text = build_srt(entries)
        plain_text = extract_text(entries)
        print(f"   ✅ 解析到 {len(entries)} 条字幕")
    else:
        # LLM 未输出 SRT 格式，回退：按行分割估算时间戳
        print("   ⚠️  LLM 未输出 SRT 格式，使用估算时间戳")
        entries = estimate_srt_from_text(raw_output)
        srt_text = build_srt(entries)
        plain_text = raw_output

    return srt_text, plain_text


def generate_copies(product: dict) -> dict[str, tuple[str, str]]:
    """Generate copy variants for a product.

    Returns: {style_key: (srt_text, plain_text)}
    """
    templates = load_templates()
    results = {}

    for style_key in templates["styles"]:
        srt_text, plain_text = generate_copy_srt(product, style_key)
        results[style_key] = (srt_text, plain_text)

    return results
```

- [ ] **Step 3: 验证导入**

Run: `python -c "from copywriter import generate_copy_srt, generate_copies; print('copywriter.py OK')"`
Expected: `copywriter.py OK`

- [ ] **Step 4: Commit**

```bash
git add copywriter.py templates/srt_prompt.txt
git commit -m "feat: copywriter outputs SRT format with timestamp estimation"
```

---

### Task 3: 改造 voice_gen.py 支持 SRT 输入

**Files:**
- Modify: `voice_gen.py`

- [ ] **Step 1: 更新 voice_gen.py**

```python
"""Voice generation — converts copy text to audio using MiMo TTS API."""

import base64
import re
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
```

- [ ] **Step 2: 验证导入**

Run: `python -c "from voice_gen import generate_voice, generate_voice_from_srt, generate_voices_for_copies; print('voice_gen.py OK')"`
Expected: `voice_gen.py OK`

- [ ] **Step 3: Commit**

```bash
git add voice_gen.py
git commit -m "feat: voice_gen supports SRT input with text extraction"
```

---

### Task 4: 创建 html_gen.py 生成 HyperFrames HTML

**Files:**
- Create: `html_gen.py`
- Create: `templates/html_prompt.txt`

- [ ] **Step 1: 创建 HTML prompt 模板**

```txt
请根据以下 SRT 字幕和产品信息，生成一个 HyperFrames 格式的 HTML 视频文件。

SRT 字幕：
{srt_content}

产品信息：
- 名称：{name}
- 一句话介绍：{tagline}
- 详细介绍：{description}
- 产品链接：{url}
- 投票数：{votes}
- 相关话题：{topics}

产品图片路径：
{image_paths}

要求：
1. 生成竖屏视频 HTML（1080×1920）
2. 每句字幕对应一个 section，用 data-start 和 data-duration 绑定时间戳
3. 产品图片穿插在相关字幕的画面中
4. 使用简单 CSS 渐变动画（fadeIn）
5. 整体风格：简洁现代，深色背景，白色文字
6. 字幕文字要大且清晰（适合手机观看）
7. 音频轨道引用：{audio_path}

HyperFrames HTML 结构要求：
- 根元素：<div id="stage" data-composition-id="product-video" data-start="0" data-width="1080" data-height="1920">
- 每个画面：<section class="frame" data-start="X" data-duration="Y" data-track-index="0">
- 音频：<audio data-start="0" data-duration="TOTAL" data-track-index="1" src="audio.mp3">

请直接输出完整的 HTML 文件内容，不要加任何前缀说明。
```

- [ ] **Step 2: 创建 html_gen.py**

```python
"""HTML generation — creates HyperFrames HTML from SRT and product info."""

import json
from pathlib import Path
from openai import OpenAI
from config import MIMO_API_KEY, MIMO_BASE_URL, TEMPLATES_DIR
from srt_parser import parse_srt


def load_html_prompt_template() -> str:
    """Load HTML prompt template."""
    with open(TEMPLATES_DIR / "html_prompt.txt", encoding="utf-8") as f:
        return f.read()


def build_html_prompt(
    product: dict,
    srt_text: str,
    image_paths: list[str],
    audio_path: str,
) -> str:
    """Build the prompt for HTML generation."""
    topics_str = ", ".join(product["topics"]) if product["topics"] else "N/A"
    image_paths_str = "\n".join(f"- {p}" for p in image_paths) if image_paths else "- 无图片"

    template = load_html_prompt_template()
    return template.format(
        srt_content=srt_text,
        name=product["name"],
        tagline=product["tagline"],
        description=product["description"],
        url=product["url"],
        votes=product["votes"],
        topics=topics_str,
        image_paths=image_paths_str,
        audio_path=audio_path,
    )


def generate_html(
    product: dict,
    srt_text: str,
    image_paths: list[str],
    audio_path: str,
    output_path: Path,
) -> Path:
    """Generate HyperFrames HTML file.

    Args:
        product: Product dict from phunt_client.
        srt_text: SRT 格式文本。
        image_paths: 产品图片本地路径列表。
        audio_path: 音频文件路径（相对于 HTML 文件）。
        output_path: 输出 HTML 文件路径。

    Returns:
        Path to the generated HTML file.
    """
    client = OpenAI(api_key=MIMO_API_KEY, base_url=MIMO_BASE_URL)

    print("  🎨  生成 HyperFrames HTML...")
    prompt = build_html_prompt(product, srt_text, image_paths, audio_path)

    response = client.chat.completions.create(
        model="mimo-v2.5-pro",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个前端开发专家，擅长生成 HyperFrames 格式的 HTML 视频文件。"
                    "你会根据 SRT 字幕的时间戳，为每句话设计合适的画面，"
                    "并确保 HTML 结构符合 HyperFrames 规范。"
                    "只输出 HTML 代码，不要加任何说明。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=4000,
    )
    html_content = response.choices[0].message.content.strip()

    # 清理可能的 markdown 代码块标记
    if html_content.startswith("```html"):
        html_content = html_content[7:]
    if html_content.startswith("```"):
        html_content = html_content[3:]
    if html_content.endswith("```"):
        html_content = html_content[:-3]
    html_content = html_content.strip()

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"   ✅ HTML 生成完成: {output_path.name}")
    return output_path
```

- [ ] **Step 3: 验证导入**

Run: `python -c "from html_gen import generate_html, build_html_prompt; print('html_gen.py OK')"`
Expected: `html_gen.py OK`

- [ ] **Step 4: Commit**

```bash
git add html_gen.py templates/html_prompt.txt
git commit -m "feat: html_gen module for HyperFrames HTML generation"
```

---

### Task 5: 创建 video_gen.py 调用 HyperFrames 渲染

**Files:**
- Create: `video_gen.py`

- [ ] **Step 1: 创建 video_gen.py**

```python
"""Video generation — renders HyperFrames HTML to MP4 using HyperFrames CLI."""

import subprocess
import shutil
from pathlib import Path


def check_hyperframes_available() -> bool:
    """Check if HyperFrames CLI is available."""
    return shutil.which("npx") is not None


def render_video(
    html_path: Path,
    audio_path: Path,
    output_path: Path,
    width: int = 1080,
    height: int = 1920,
) -> Path | None:
    """Render HyperFrames HTML to MP4 video.

    Args:
        html_path: Path to the HyperFrames HTML file.
        audio_path: Path to the audio file.
        output_path: Path for the output MP4 file.
        width: Video width (default 1080).
        height: Video height (default 1920).

    Returns:
        Path to the rendered MP4 file, or None if rendering failed.
    """
    if not check_hyperframes_available():
        print("  ⚠️  npx 不可用，请安装 Node.js 22+")
        print("     下载地址: https://nodejs.org/")
        return None

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 复制音频到 HTML 同目录（HyperFrames 需要）
    audio_dest = html_path.parent / audio_path.name
    if not audio_dest.exists():
        shutil.copy2(audio_path, audio_dest)

    print("  🎬  渲染视频...")
    print(f"     HTML: {html_path}")
    print(f"     音频: {audio_path}")
    print(f"     输出: {output_path}")

    try:
        # 使用 hyperframes render 命令
        cmd = [
            "npx", "hyperframes", "render",
            "--input", str(html_path),
            "--output", str(output_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时
            cwd=html_path.parent,
        )

        if result.returncode == 0:
            print(f"   ✅ 视频渲染完成: {output_path.name}")
            return output_path
        else:
            print(f"   ⚠️  渲染失败:")
            print(f"     {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print("   ⚠️  渲染超时（5分钟）")
        return None
    except FileNotFoundError:
        print("   ⚠️  npx 命令未找到，请安装 Node.js")
        return None
    except Exception as e:
        print(f"   ⚠️  渲染异常: {e}")
        return None
```

- [ ] **Step 2: 验证导入**

Run: `python -c "from video_gen import render_video, check_hyperframes_available; print('video_gen.py OK')"`
Expected: `video_gen.py OK`

- [ ] **Step 3: Commit**

```bash
git add video_gen.py
git commit -m "feat: video_gen module for HyperFrames rendering"
```

---

### Task 6: 改造 formatter.py 支持新目录结构

**Files:**
- Modify: `formatter.py`

- [ ] **Step 1: 更新 formatter.py**

```python
"""Formatter — manages output directory structure and file writing."""

from datetime import datetime
from pathlib import Path
from config import OUTPUT_DIR, TEMPLATES_DIR
import json


def get_output_dir() -> Path:
    """Get today's output directory, creating it if needed."""
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = OUTPUT_DIR / today
    # 创建子目录
    for subdir in ["copy", "audio", "images", "html", "video"]:
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)
    return output_dir


def get_style_names() -> dict[str, str]:
    """Load style display names from templates."""
    with open(TEMPLATES_DIR / "styles.json", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v["name"] for k, v in data["styles"].items()}


def save_srt_copy(srt_text: str, plain_text: str, style_key: str, output_dir: Path) -> tuple[Path, Path]:
    """Save SRT and plain text files.

    Args:
        srt_text: SRT 格式文本。
        plain_text: 纯文本。
        style_key: 风格标识（如 style_a）。
        output_dir: 今日输出目录。

    Returns:
        (srt_path, txt_path) 保存的文件路径。
    """
    style_names = get_style_names()
    style_name = style_names.get(style_key, style_key)

    copy_dir = output_dir / "copy"
    copy_dir.mkdir(parents=True, exist_ok=True)

    srt_path = copy_dir / f"{style_key}_{style_name}.srt"
    txt_path = copy_dir / f"{style_key}_{style_name}.txt"

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_text)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(plain_text)

    return srt_path, txt_path


def print_summary(
    output_dir: Path,
    srt_files: dict[str, tuple[Path, Path]],
    audio_files: dict[str, Path],
    image_files: dict[str, Path],
    html_files: dict[str, Path] = None,
    video_files: dict[str, Path] = None,
) -> None:
    """Print a summary of generated files."""
    print(f"\n✅ 所有内容已生成到: {output_dir}\n")

    print("📄 文案文件:")
    for style_key, (srt_path, txt_path) in srt_files.items():
        print(f"   {srt_path.relative_to(output_dir)}")
        print(f"   {txt_path.relative_to(output_dir)}")

    print("\n🎙️  音频文件:")
    for style_key, path in audio_files.items():
        if path:
            print(f"   {path.relative_to(output_dir)}")

    print("\n🖼️  图片文件:")
    for name, path in image_files.items():
        if path:
            print(f"   {path.relative_to(output_dir)}")

    if html_files:
        print("\n🌐 HTML 文件:")
        for style_key, path in html_files.items():
            if path:
                print(f"   {path.relative_to(output_dir)}")

    if video_files:
        print("\n🎬 视频文件:")
        for style_key, path in video_files.items():
            if path:
                print(f"   {path.relative_to(output_dir)}")

    print(f"\n💡 请打开 {output_dir} 文件夹查看生成的内容。")
```

- [ ] **Step 2: 验证导入**

Run: `python -c "from formatter import get_output_dir, save_srt_copy, print_summary; print('formatter.py OK')"`
Expected: `formatter.py OK`

- [ ] **Step 3: Commit**

```bash
git add formatter.py
git commit -m "feat: formatter supports SRT files and new directory structure"
```

---

### Task 7: 改造 main.py 集成视频生成流程

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 更新 main.py**

```python
"""Main entry point — orchestrates the daily workflow with video generation."""

from config import validate_config
from phunt_client import fetch_top_products, display_products, select_product
from copywriter import generate_copy_srt
from voice_gen import generate_voice
from image_gen import download_product_images
from html_gen import generate_html
from video_gen import render_video, check_hyperframes_available
from formatter import get_output_dir, save_srt_copy, print_summary


def main():
    """Run the daily Product Hunt content generation workflow."""
    print("=" * 50)
    print("  🚀 Product Hunt 每日精选 → 视频内容生成")
    print("=" * 50)

    # Step 0: 检查配置
    print("\n📋 检查配置...")
    validate_config()
    print("   ✅ 配置检查通过")

    # Step 1: 拉取产品
    print("\n📡 拉取 Product Hunt 今日 Top 5...")
    products = fetch_top_products(5)
    display_products(products)

    # Step 2: 选择产品
    product = select_product(products)
    print(f"\n✅ 已选择: {product['name']}")
    print(f"   {product['tagline']}")

    # Step 3: 生成文案（SRT 格式）
    print("\n✍️  开始生成文案（SRT 格式）...")
    srt_text, plain_text = generate_copy_srt(product, "style_a")
    print("   ✅ 文案生成完成")

    # Step 4: 保存文案
    output_dir = get_output_dir()
    srt_path, txt_path = save_srt_copy(srt_text, plain_text, "style_a", output_dir)
    print(f"   📄 SRT: {srt_path.name}")
    print(f"   📄 TXT: {txt_path.name}")

    # Step 5: 生成配音
    print("\n🎙️  开始生成配音...")
    audio_path = output_dir / "audio" / "style_a.mp3"
    generate_voice(plain_text, audio_path)
    print("   ✅ 配音生成完成")

    # Step 6: 下载产品图片
    print("\n🖼️  下载产品截图...")
    image_files = download_product_images(product, output_dir)
    image_paths = [str(p) for p in image_files.values() if p]
    print(f"   ✅ 下载完成 ({len(image_paths)} 张)")

    # Step 7: 生成 HTML
    print("\n🌐 生成 HyperFrames HTML...")
    html_path = output_dir / "html" / "style_a.html"
    generate_html(product, srt_text, image_paths, str(audio_path), html_path)
    print("   ✅ HTML 生成完成")

    # Step 8: 渲染视频（如果 HyperFrames 可用）
    video_path = None
    if check_hyperframes_available():
        print("\n🎬 渲染视频...")
        video_path = output_dir / "video" / "style_a.mp4"
        video_path = render_video(html_path, audio_path, video_path)
        if video_path:
            print("   ✅ 视频渲染完成")
        else:
            print("   ⚠️  视频渲染失败，但 HTML 文件已生成")
    else:
        print("\n⚠️  HyperFrames 未安装，跳过视频渲染")
        print("   安装方法: npm install -g hyperframes")
        print("   HTML 文件已生成，可手动渲染")

    # 输出摘要
    print_summary(
        output_dir,
        {"style_a": (srt_path, txt_path)},
        {"style_a": audio_path},
        image_files,
        {"style_a": html_path},
        {"style_a": video_path} if video_path else None,
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 验证语法**

Run: `python -c "import main; print('main.py OK')"`
Expected: `main.py OK`

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: main.py integrates video generation workflow"
```

---

### Task 8: 完整集成测试

- [ ] **Step 1: 安装依赖（如果还没安装）**

Run: `pip install -r requirements.txt`
Expected: Successfully installed required packages

- [ ] **Step 2: 检查 HyperFrames 是否可用**

Run: `npx hyperframes --version`
Expected: 版本号输出（如果已安装）或错误提示（未安装）

- [ ] **Step 3: 运行完整流程**

Run: `python main.py`
Expected:
1. 配置检查通过
2. Product Hunt Top 5 显示
3. 选择产品
4. SRT 格式文案生成
5. 配音生成
6. 图片下载
7. HTML 生成
8. 视频渲染（如果 HyperFrames 可用）

- [ ] **Step 4: 验证输出文件**

Run: `ls output/`（检查今日日期文件夹）

预期文件结构：
```
output/2026-06-08/
├── copy/
│   ├── style_a_口语风.srt
│   └── style_a_口语风.txt
├── audio/
│   └── style_a.mp3
├── images/
│   ├── 01.png
│   └── 02.png
├── html/
│   └── style_a.html
└── video/
    └── style_a.mp4  （如果 HyperFrames 可用）
```

- [ ] **Step 5: 最终 Commit**

```bash
git add -A
git commit -m "feat: complete video generation pipeline with HyperFrames"
```

---

## NOTES

**HyperFrames 安装：** 需要 Node.js 22+ 和 FFmpeg。安装命令：`npm install -g hyperframes` 或使用 `npx hyperframes`。

**SRT 时间戳精度：** MVP 阶段使用估算时间戳（~4.5 字/秒），后续可考虑用 Whisper 对齐提高精度。

**LLM 输出格式：** copywriter.py 包含容错逻辑，如果 LLM 未输出 SRT 格式，会自动回退到估算模式。

**HTML 生成质量：** LLM 生成的 HTML 可能需要手动调整，MVP 阶段接受这个限制。
