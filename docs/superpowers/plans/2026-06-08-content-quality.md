# Content Quality Improvement — Implementation Plan

**Date:** 2026-06-08
**Spec:** `docs/superpowers/specs/2026-06-08-content-quality-design.md`

## Changes

### 1. `templates/srt_prompt.txt` — Remove length constraints

**Current:** Forces 20-30 sentences, 15-25 chars each, 60-90 seconds.

**New:** Remove all length/count constraints. Focus on content quality. Let LLM write naturally.

```
Changes:
- Remove "每句话控制在 15-25 字"
- Remove "总共 20-30 句话，目标时长 60-90 秒"
- Remove "时间戳基于中文语速 ~4.5 字/秒估算"
- Keep: content structure guidance (hook → intro → features → experience → CTA)
- Keep: SRT format requirements
- Add: "有多少说多少，不要注水或凑字数"
```

### 2. `html_gen.py` — One-time image assignment

**Current:** `next_img()` cycles through images with modulo, causing repetition.

**New:** Track used images. Assign to priority scenes first. Force Layout A (text-only) once images exhausted.

**Logic:**

```
1. Build prioritized scene list:
   - Scenes with product name mention (priority 1)
   - Feature/benefit scenes (priority 2)
   - All other scenes (priority 3)

2. Assign images to top N scenes (N = number of images):
   - Phone screenshots → Layout B (phone mockup)
   - Wide screenshots → Layout C (full-wide)
   - Square screenshots → Layout D (brand)

3. Remaining scenes → Layout A (text-only, no image)

4. Remove next_img() cycling function
```

**Key changes in `generate_html()`:**
- Remove `next_img()` function
- Remove `img_idx` counter
- Add `used_images` set
- Add `assign_image()` function that returns image path or empty string
- Layout selection: first pass assigns images to priority scenes, second pass assigns Layout A to remaining

## Files to Modify

| File | Lines | Change |
|------|-------|--------|
| `templates/srt_prompt.txt` | ~50 | Rewrite prompt, remove constraints |
| `html_gen.py` | ~80 | Rewrite image assignment logic (lines 230-310) |

## Testing

Run `python main.py` and verify:
1. LLM generates variable-length copy (not forced 25 sentences)
2. Each image appears exactly once in the video
3. Remaining scenes use Layout A (text-only)
4. No image repetition
