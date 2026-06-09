"""HTML generator - Stripe-inspired full-width layouts with Aurora gradients."""

import json
import random
from pathlib import Path
from PIL import Image


# ── Image utils ────────────────────────────────────────────────────

def _image_info(path: Path) -> dict:
    img = Image.open(path)
    w, h = img.size
    ratio = w / h
    img_s = img.resize((20, 20))
    pixels = list(img_s.getdata())
    avg = sum(sum(p[:3]) / 3 for p in pixels) / len(pixels)
    return {"ratio": ratio, "width": w, "height": h, "brightness": avg}


def _classify_image(img_info: dict | None) -> str:
    if img_info is None:
        return "none"
    r = img_info["ratio"]
    if r > 1.5:
        return "wide"
    if r < 0.85:
        return "phone"
    return "square"


# ── Text templates (Stripe-style full-width) ───────────────────────

_TEMPLATES = {}


def _register(name):
    def decorator(func):
        _TEMPLATES[name] = func
        return func
    return decorator


@_register("tpl-hero")
def _(text, p):
    """Full-width hero with decorative quote mark."""
    return f'''<div style="position:relative;max-width:960px;">
  <div style="position:absolute;top:-60px;left:-30px;font-size:280px;font-weight:900;line-height:1;color:{p['accent']};opacity:0.12;font-family:Georgia,serif;pointer-events:none;">“</div>
  <div class="text-main" style="font-size:72px;font-weight:800;line-height:1.15;letter-spacing:-0.025em;position:relative;">{text}</div>
</div>'''


@_register("tpl-grid")
def _(text, p):
    """Grid split - colored left column, text right, fills width."""
    return f'''<div style="display:flex;width:100%;max-width:1000px;height:500px;border-radius:24px;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,0.06);">
  <div style="width:300px;background:linear-gradient(180deg,{p['accent']}30,{p['accent']}10);display:flex;align-items:center;justify-content:center;">
    <div style="font-size:200px;font-weight:900;color:{p['accent']};opacity:0.2;font-family:Georgia,serif;line-height:1;">“</div>
  </div>
  <div style="flex:1;display:flex;align-items:center;padding:60px 60px 60px 50px;background:rgba(255,255,255,0.7);backdrop-filter:blur(30px);-webkit-backdrop-filter:blur(30px);">
    <div class="text-main" style="font-size:50px;font-weight:700;line-height:1.3;letter-spacing:-0.02em;">{text}</div>
  </div>
</div>'''


@_register("tpl-bottom")
def _(text, p):
    """Text anchored bottom with quote mark above."""
    return f'''<div style="width:100%;max-width:960px;position:relative;">
  <div style="font-size:240px;font-weight:900;line-height:0.8;color:{p['accent']};opacity:0.1;font-family:Georgia,serif;margin-bottom:-40px;">“</div>
  <div class="text-main" style="font-size:58px;font-weight:700;line-height:1.25;letter-spacing:-0.02em;margin-bottom:36px;position:relative;">{text}</div>
  <div style="width:100%;height:4px;background:linear-gradient(90deg,{p['accent']},{p['accent']}00);border-radius:2px;"></div>
</div>'''


@_register("tpl-dark")
def _(text, p):
    """Full-width bold text with large quote mark."""
    return f'''<div style="position:relative;max-width:960px;">
  <div style="position:absolute;top:-40px;right:-20px;font-size:320px;font-weight:900;line-height:1;color:{p['accent']};opacity:0.08;font-family:Georgia,serif;pointer-events:none;">”</div>
  <div class="text-main" style="font-size:72px;font-weight:800;line-height:1.15;letter-spacing:-0.025em;color:#0a0a1a;position:relative;">{text}</div>
</div>'''


@_register("tpl-card")
def _(text, p):
    """Glass card with quote mark inside."""
    return f'''<div style="width:100%;max-width:980px;background:rgba(255,255,255,0.6);backdrop-filter:blur(40px);-webkit-backdrop-filter:blur(40px);border:1px solid rgba(255,255,255,0.8);border-radius:24px;padding:70px 80px;box-shadow:0 8px 32px rgba(0,0,0,0.04);position:relative;overflow:hidden;">
  <div style="position:absolute;top:20px;left:30px;font-size:180px;font-weight:900;line-height:1;color:{p['accent']};opacity:0.1;font-family:Georgia,serif;pointer-events:none;">“</div>
  <div class="text-main" style="font-size:54px;font-weight:700;line-height:1.3;letter-spacing:-0.02em;text-align:center;position:relative;">{text}</div>
</div>'''


_TEMPLATE_NAMES = list(_TEMPLATES.keys())


# ── CSS ────────────────────────────────────────────────────────────

_CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }

#stage {
  width: 1080px; height: 1920px;
  background: #f8f9fc;
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif;
  position: relative; overflow: hidden;
  color: #0a0a1a;
}

.clip {
  position: absolute; top: 0; left: 0;
  width: 1080px; height: 1920px;
  display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  padding: 120px 60px; opacity: 0;
  z-index: 1;
}

.aurora {
  position: absolute; border-radius: 50%; pointer-events: none; z-index: 0;
  filter: blur(120px);
}
.aurora-pink { width: 700px; height: 700px; background: #ff6b9d; opacity: 0.15; top: -200px; right: -150px; }
.aurora-blue { width: 600px; height: 600px; background: #60a5fa; opacity: 0.12; bottom: -100px; left: -200px; }
.aurora-yellow { width: 500px; height: 500px; background: #fbbf24; opacity: 0.08; top: 600px; right: 100px; }

.text-main .hl { color: %(accent)s; }

/* Image layout */
.layout-img .glass {
  background: rgba(255,255,255,0.65);
  backdrop-filter: blur(40px); -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255,255,255,0.8);
  border-radius: 28px; padding: 32px;
  max-width: 900px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.04);
}
.layout-img .img-container {
  width: 100%; height: 700px; border-radius: 20px; overflow: hidden;
  background: #1a1a2e;
}
.layout-img .img-container img { width: 100%; height: 100%; object-fit: cover; }
.layout-img .scene-text {
  margin-top: 28px; font-size: 38px; font-weight: 600;
  text-align: center; color: #3a3a5e; line-height: 1.4;
}

/* Brand layout */
.layout-brand .glass {
  background: rgba(255,255,255,0.65);
  backdrop-filter: blur(40px); -webkit-backdrop-filter: blur(40px);
  border: 1px solid rgba(255,255,255,0.8);
  border-radius: 28px; padding: 60px;
  max-width: 800px; text-align: center;
  box-shadow: 0 8px 32px rgba(0,0,0,0.04);
}
.layout-brand .brand-icon {
  width: 160px; height: 160px; border-radius: 36px; overflow: hidden;
  margin: 0 auto 36px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.08);
}
.layout-brand .brand-icon img { width: 100%; height: 100%; object-fit: cover; }
.layout-brand .brand-name {
  font-size: 64px; font-weight: 800; letter-spacing: -0.01em;
  background: linear-gradient(135deg, #ff6b9d, #60a5fa);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; margin-bottom: 16px;
}
.layout-brand .brand-desc { font-size: 36px; color: #6a6a8a; line-height: 1.5; }
"""


# ── Scene generation ───────────────────────────────────────────────

def _scene_html(idx, start, dur, text, layout, image_src="", product_name="", tpl=""):
    sid = f"s{idx}"
    cls = f"layout-{layout}" if layout in ("img", "brand") else ""

    lines = [f'  <div class="clip {cls}" id="{sid}" data-start="{start:.3f}" data-duration="{dur:.3f}" data-track-index="0">']

    if layout == "img":
        lines.append(f'    <div class="glass">')
        lines.append(f'      <div class="img-container"><img src="{image_src}" alt=""></div>')
        lines.append(f'      <div class="scene-text">{text}</div>')
        lines.append(f'    </div>')
    elif layout == "brand":
        lines.append(f'    <div class="glass">')
        if image_src:
            lines.append(f'      <div class="brand-icon"><img src="{image_src}" alt=""></div>')
        if product_name:
            lines.append(f'      <div class="brand-name">{product_name}</div>')
        lines.append(f'      <div class="brand-desc">{text}</div>')
        lines.append(f'    </div>')
    else:
        # Text template
        inner = _TEMPLATES[tpl](text, {"accent": "{accent}"})
        lines.append(f'    {inner}')

    lines.append(f'  </div>')
    return "\n".join(lines)


# ── Main generator ─────────────────────────────────────────────────

def generate_html(product, alignment, palette, image_paths, audio_path, output_path):
    """Generate a single HyperFrames HTML file with Stripe-style layouts."""
    # Classify images
    image_types = {}
    for p in image_paths:
        fname = Path(p).name
        try:
            image_types[fname] = _classify_image(_image_info(p))
        except Exception:
            image_types[fname] = "phone"

    all_imgs = list(image_types.keys())
    img_idx = 0

    def next_img():
        nonlocal img_idx
        if img_idx >= len(all_imgs):
            return ""
        f = all_imgs[img_idx]
        img_idx += 1
        return f"../images/{f}"

    # Extend scenes
    total = max(r[2] for r in alignment)
    extended = []
    for i, (idx, start, end, text) in enumerate(alignment):
        ext_end = alignment[i + 1][1] if i < len(alignment) - 1 else total
        extended.append((idx, start, ext_end, text))

    # Distribute images evenly
    num_scenes = len(extended)
    num_images = len(all_imgs)
    if num_images > 0 and num_scenes > 0:
        step = num_scenes / num_images
        image_scene_indices = set(int(i * step) for i in range(num_images))
    else:
        image_scene_indices = set()

    # Generate scenes
    scenes_html = []
    last_tpl = ""

    for i, (idx, start, end, text) in enumerate(extended):
        dur = end - start
        has_product = product["name"].lower() in text.lower()
        is_cta = idx >= len(extended) - 3
        has_votes = "250" in text or "投票" in text or "支持" in text

        if i in image_scene_indices:
            if has_votes or (is_cta and has_product):
                layout = "brand"
                img_src = next_img()
                pname = product["name"] if has_product else ""
            else:
                layout = "img"
                img_src = next_img()
                pname = ""
            scenes_html.append(_scene_html(idx, start, dur, text, layout, img_src, pname))
        else:
            tpl = random.choice(_TEMPLATE_NAMES)
            while tpl == last_tpl and len(_TEMPLATE_NAMES) > 1:
                tpl = random.choice(_TEMPLATE_NAMES)
            last_tpl = tpl
            scenes_html.append(_scene_html(idx, start, dur, text, "", "", "", tpl))

    # GSAP schedule
    gsap_entries = ",\n    ".join(
        f"['s{r[0]}', {r[1]:.3f}, {r[2] - r[1]:.3f}]"
        for r in extended
    )

    # CSS with palette accent
    css = _CSS.replace("{accent}", palette.get("accent", "#ff6b9d"))

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
{css}</style>
</head>
<body>
<div id="stage" data-composition-id="product-video" data-start="0.0" data-width="1080" data-height="1920">

  <div class="aurora aurora-pink"></div>
  <div class="aurora aurora-blue"></div>
  <div class="aurora aurora-yellow"></div>

{chr(10).join(scenes_html)}

  <audio id="bgm" data-start="0" data-duration="{total:.3f}" data-track-index="1" data-volume="1" src="{Path(audio_path).name}"></audio>

</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script>
(function() {{
  window.__timelines = window.__timelines || {{}};
  var master = gsap.timeline({{ paused: true }});
  window.__timelines["product-video"] = master;

  function animateClip(id, start, dur) {{
    var el = document.getElementById(id);
    if (!el) return;
    master.set(el, {{ opacity: 1 }}, start);
    var kids = el.querySelectorAll('.text-main, .text-block, .glass, .scene-text, .brand-name, .brand-icon, .brand-desc, .img-container');
    if (kids.length) {{
      master.fromTo(kids,
        {{ opacity: 0, y: 40, scale: 0.96 }},
        {{ opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "power3.out", stagger: 0.08 }},
        start
      );
    }}
    master.to(el, {{ opacity: 0, duration: 0.15 }}, start + dur - 0.15);
  }}

  var scenes = [
    {gsap_entries}
  ];
  scenes.forEach(function(s) {{ animateClip(s[0], s[1], s[2]); }});
}})();
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"   ✅ HTML 生成完成: {output_path.name} ({len(alignment)} 场景)")
    return output_path
