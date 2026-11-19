"""Renders a post into 1080×1920 frames (PNG) using the reading-room template."""
import hashlib
import html
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from .organs import MODALITIES, ORGANS

ROOT = Path(__file__).resolve().parent.parent
FONTS = (ROOT / "assets" / "fonts").as_uri()

PALETTES = [
    {"name": "pacs", "acc": "#F2D14B", "acc2": "#57D4E8"},   # caliper yellow + label cyan
    {"name": "lime", "acc": "#9BE15D", "acc2": "#F6A6E1"},
    {"name": "amber", "acc": "#FFB547", "acc2": "#8DB8FF"},
]
LAYOUTS = ["top", "split", "bleed"]

OVERFLOW_JS = """() => {
  let bad = false;
  for (const t of document.querySelectorAll('.txt')) {
    const r = t.getBoundingClientRect();
    if (r.bottom > 1560 || r.right > 1000) bad = true;
  }
  return bad;
}"""


def _visual(v):
    """Normalise a visual spec from the writer into something drawable."""
    v = v or {}
    name = v.get("organ") if v.get("organ") in ORGANS else "body"
    o = ORGANS[name]
    mod = v.get("modality") if v.get("modality") in MODALITIES else o["default"]
    if o["default"] == "diagram":
        mod = "diagram"  # machines/outlines always as diagrams
    if mod == "doppler" and name != "vessel":
        mod = "us"
    ann = None
    a = v.get("annotation") or {}
    if a.get("type") in ("arrow", "caliper", "circle"):
        anchor = a.get("anchor") if a.get("anchor") in o["anchors"] else next(iter(o["anchors"]))
        ann = {"type": a["type"], "xy": o["anchors"][anchor], "label": (a.get("label") or "")[:22]}
    return o, mod, ann


def _hook_html(hook, emph):
    """Highlight one key word/phrase of the hook in the accent colour (only if it is in the hook)."""
    h = html.escape(hook)
    if emph and emph.lower() in hook.lower():
        i = hook.lower().index(emph.lower())
        h = html.escape(hook[:i]) + "<em>" + html.escape(hook[i:i + len(emph)]) + "</em>" + html.escape(hook[i + len(emph):])
    return h


def style_for(post):
    k = int(hashlib.md5(post.get("hook", "x").encode()).hexdigest()[:8], 16)
    return PALETTES[k % 3], LAYOUTS[(k // 3) % 3], k % 997


def page_plan(post):
    pages = [("cover", None, post.get("cover_visual") or (post["slides"][0].get("visual") if post["slides"] else None))]
    pages += [("content", s, s.get("visual")) for s in post["slides"]]
    pages.append(("close", None, None))
    return pages


def render_post(post, cfg, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=True)
    tpl = env.get_template("slide.html")
    pal, layout, seed = style_for(post)
    plan = page_plan(post)
    total = len(plan)
    files = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1920})
        for n, (kind, slide, visual) in enumerate(plan):
            o, mod, ann = _visual(visual)
            scale = 1.0
            for _ in range(8):
                lines = sum(len(x) for x in (slide or {}).get("lines", []))
                sizes = {"hook": round((104 if len(post["hook"]) < 34 else 90) * scale),
                         "head": round((74 if len((slide or {}).get("heading", "")) < 26 else 64) * scale),
                         "line": round((50 if lines < 130 else 44) * scale),
                         "take": round((86 if len(post.get("takeaway", "")) < 60 else 74) * scale)}
                html_s = tpl.render(kind=kind, post=post, slide=slide, o=o, mod=mod, ann=ann, idx=n + 1, total=total,
                                    layout=layout, pal=pal, seed=seed + n, sizes=sizes, fonts=FONTS,
                                    channel=cfg["channel"]["name"], byline=cfg["channel"]["byline"],
                                    modname=MODALITIES[mod],
                                    hook_html=_hook_html(post["hook"], post.get("hook_emphasis", "")))
                tmp = out_dir / f"_p{n}.html"
                tmp.write_text(html_s, encoding="utf-8")
                page.goto(tmp.as_uri())
                page.evaluate("document.fonts.ready")
                if not page.evaluate(OVERFLOW_JS):
                    break
                scale *= 0.93
            png = out_dir / f"frame_{n:02d}.png"
            page.screenshot(path=str(png))
            tmp.unlink(missing_ok=True)
            files.append(png)
        browser.close()
    return files
