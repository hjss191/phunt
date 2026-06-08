# PHUNT - Product Hunt Daily Video Generator

## Project Overview

Automated pipeline that fetches Product Hunt products, generates Chinese promotional copy, synthesizes TTS audio, and renders vertical videos (1080×1920) with Stripe-style Aurora visual design.

## Pipeline Flow

```
Stage 1: Fetch Product Hunt Top 5
Stage 2: Select product
Stage 3: LLM generates copy → save to file → MANUAL REVIEW → continue with edited copy
Stage 4: TTS audio generation (MiMo-V2.5-TTS)
Stage 5: Whisper alignment (faster-whisper, GPU preferred)
Stage 6: Download product images + extract color palette
Stage 7: Generate HyperFrames HTML (single file, all scenes)
Stage 8: Render video via HyperFrames CLI
```

## Visual Template: Stripe-style Aurora

### Color System

- **Background**: `#f8f9fc` (light gray-white) — NEVER change background color between scenes
- **Aurora glow blobs**: Three blurred circles (filter: blur(120px))
  - Pink: `#ff6b9d`, opacity 0.15, top-right
  - Blue: `#60a5fa`, opacity 0.12, bottom-left
  - Yellow: `#fbbf24`, opacity 0.08, mid-right
- **Text primary**: `#0a0a1a` (near-black)
- **Text secondary**: `#6a6a8a` (muted gray)
- **Accent**: Extracted from product images via `palette.py`, used for decorative elements

### Typography

- **Font stack**: `'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif`
- **Hero text**: 72px, font-weight 800, line-height 1.15, letter-spacing -0.025em
- **Body text**: 44-54px, font-weight 500-700, line-height 1.3-1.5
- **Text color**: Always dark (`#0a0a1a`) on light background — NEVER use light text on light bg

### Decorative Quote Mark

Every text-only scene has a large `"` (left double quotation mark, Unicode U+201C) as a visual anchor:

- **Font**: Georgia, serif (for elegant curve)
- **Size**: 180-320px depending on template
- **Color**: Accent color
- **Opacity**: 0.08-0.12 (subtle, not overpowering)
- **Position**: Varies per template (top-left, top-right, above text, inside card)

### 5 Text Templates

#### tpl-hero — Full-width centered
- Quote mark: top-left, 280px, opacity 0.12
- Text: 72px, max-width 960px, left-aligned within block
- Use for: Opening hooks, key statements

#### tpl-grid — Split column layout
- Left column: 300px wide, accent gradient background, large quote mark (200px) centered
- Right column: Text 50px, glass card background (rgba(255,255,255,0.7), backdrop-filter: blur(30px))
- Total: 1000px wide, 500px tall, border-radius 24px
- Use for: Feature descriptions, comparisons

#### tpl-bottom — Bottom-aligned with bar
- Quote mark: above text, 240px, opacity 0.1
- Text: 58px, bottom-aligned
- Accent bar: full-width gradient line below text (4px, accent → transparent)
- Use for: Closing statements, CTAs

#### tpl-dark — Bold full-width
- Quote mark: top-right, 320px, opacity 0.08
- Text: 72px, color #0a0a1a (dark on light, NOT dark bg)
- Use for: Emphasis, key numbers, bold claims

#### tpl-card — Glass card centered
- Quote mark: inside card top-left, 180px, opacity 0.1
- Card: max-width 980px, glass effect, border-radius 24px
- Text: 54px, centered
- Use for: General content, quotes, summaries

### Image Layout (layout-img)

- **Container**: Glass card, max-width 900px, padding 32px
- **Image area**: 900×700px, border-radius 20px, background #1a1a2e
- **Image fit**: `object-fit: cover` (fills container, crops if needed)
- **Caption**: Below image, 38px, centered, color #3a3a5e
- **Distribution**: Images spread evenly across scenes, each used exactly once

### Brand Layout (layout-brand)

- Used for: CTA scenes, vote mentions, product name highlights
- Glass card with brand icon (160×160px, border-radius 36px)
- Brand name: 64px, gradient text (pink → blue)
- Description: 36px, muted color

### GSAP Animations

- **Fade in**: opacity 0→1, y 40→0, scale 0.96→1, duration 0.6s, ease power3.out
- **Fade out**: opacity→0, duration 0.15s, starts at (end - 0.15s)
- **Stagger**: 0.08s between child elements
- **Timeline**: Registered as `window.__timelines["product-video"]`

## Key Technical Decisions

### Single HTML File
All scenes in one HTML file (not per-scene files). This allows single Chrome launch for rendering, much faster than per-scene rendering.

### Whisper Alignment (not sentence matching)
Whisper transcribes audio → segments with accurate timestamps. Each segment matched to original LLM text. This is more reliable than trying to match LLM sentences to Whisper words.

### Manual Copy Review
After LLM generates copy, pipeline pauses. User reviews/edits the file, then presses Enter to continue. This ensures quality and prevents TTS from reading bad text.

### TTS Verbatim Instruction
User message to TTS: "逐字朗读以下文本，不要修改、省略或改写任何内容。语速适中，语调自然。" This prevents the TTS model from paraphrasing.

### GPU for Whisper
Use CTranslate2 CUDA detection (not torch). Install `nvidia-cublas-cu12` for CUDA 12 support. Auto-fallback to CPU if GPU unavailable.

## File Structure

```
D:\phunt\
├── main.py              # Pipeline orchestrator (8 stages)
├── config.py            # Env vars from .env
├── phunt_client.py      # Product Hunt GraphQL API
├── copywriter.py        # LLM copy generation (MiMo)
├── voice_gen.py         # TTS generation (MiMo-V2.5-TTS)
├── aligner.py           # Whisper alignment (GPU/CPU)
├── image_gen.py         # Download PH screenshots
├── palette.py           # Extract color palette from images
├── html_gen.py          # Generate HyperFrames HTML (Stripe Aurora style)
├── video_gen.py         # Render via HyperFrames CLI
├── formatter.py         # Output directory management
├── srt_parser.py        # SRT format utilities
├── templates/
│   ├── styles.json      # Writing styles (口语风/故事风/分析风)
│   └── srt_prompt.txt   # LLM prompt template
└── output/YYYY-MM-DD/   # Generated content (gitignored)
```

## Running

```bash
python main.py
```

Each stage runs sequentially. Stage 3 pauses for manual copy review (edit file, press Enter).

## Dependencies

- Python: openai, requests, python-dotenv, httpx, Pillow, faster-whisper, zhconv
- Node.js: npx hyperframes (for video rendering)
- System: ffmpeg (for audio/video processing)
- GPU: nvidia-cublas-cu12 (optional, for Whisper acceleration)
