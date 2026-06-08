# Content Quality Improvement Design

**Date:** 2026-06-08
**Goal:** Fix copy pacing issues and image reuse problems in the video generation pipeline.

## Problem Statement

1. **Copy rhythm is padded** — LLM is forced to write 20-30 sentences to fill 60-90 seconds, but doesn't have enough content. Result: filler sentences that drag.
2. **Images are reused excessively** — Products typically have 3-10 screenshots, but videos have 25-30 scenes. Same images repeat many times, looking stale.

## Design Decisions

### Decision 1: Content dictates video length

**Approach:** Remove sentence count and duration constraints from the LLM prompt. Let the LLM write as much or as little as it has to say about the product.

**Changes:**
- `templates/srt_prompt.txt` — Remove "20-30 sentences", "15-25 characters each", "60-90 seconds" constraints
- `copywriter.py` — No changes needed (already handles variable-length output)

### Decision 2: Images used once, no repeating

**Approach:** Each product screenshot is assigned to exactly one scene. Once all images are used, remaining scenes use text-only layouts (Layout A: big text + CSS effects).

**Changes:**
- `html_gen.py` — Modify image assignment logic:
  - Track used images in a set
  - Assign images to scenes in order (prefer product-mentioning scenes first)
  - Once all images used, force remaining scenes to Layout A (text-only)
  - Remove the `next_img()` cycling logic that causes repetition

**Layout priority for image assignment:**
1. Product introduction scene (first mention of product name) → phone/square image
2. Feature showcase scenes → wide/phone images
3. CTA/vote scenes → square image (if available)
4. All other scenes → Layout A (text-only, no image)

### Decision 3: No changes to other modules

- HTML visual design — keep current 4 layouts (A/B/C/D) and CSS template
- Alignment — keep current Whisper segment matching approach
- TTS — keep current implementation
- Video rendering — keep current HyperFrames approach

## Files to Modify

| File | Change |
|------|--------|
| `templates/srt_prompt.txt` | Remove length constraints, focus on quality over quantity |
| `html_gen.py` | Rewrite image assignment: one-time use, text-only fallback |

## Expected Outcome

- Videos are shorter but higher quality (no filler)
- Each image appears only once
- More scenes use text-only layouts with CSS visual effects
- Overall video length varies by product (could be 30s or 90s, depending on content)
