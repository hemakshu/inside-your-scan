#!/usr/bin/env python3
"""Makes today's Short and sends it to you on Telegram for ✅ / ❌.

  python make.py              # normal (called by the workflow when tick.py says make=true)
  python make.py --mock       # sample content, no Claude API (for testing the look + Telegram)
  python make.py --no-send    # make the video but don't send it (local test)
"""
import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

import yaml

from src import generator, reel, render
from src import state as S

ROOT = Path(__file__).resolve().parent


def log(m):
    print(m, flush=True)


def pick_topic(cfg, st):
    if st.get("next_topic"):
        return st.pop("next_topic"), "requested"
    bank = yaml.safe_load((ROOT / "content" / "topics.yaml").read_text(encoding="utf-8"))["categories"]
    hist = S.load(S.HISTORY, {"posts": []})["posts"]
    used = {p["topic"].lower() for p in hist[-cfg["content"]["avoid_repeat_posts"]:]}
    used |= {d["topic"].lower() for d in st.get("drafts", [])[-10:]}  # incl. today's rejected ones
    last_cat = hist[-1]["category"] if hist else None
    cats = [c for c in bank if c != last_cat] or list(bank)
    random.shuffle(cats)
    for c in cats:
        fresh = [t for t in bank[c] if t.lower() not in used]
        if fresh:
            return random.choice(fresh), c
    c = cats[0]
    text = generator._call_claude(cfg, generator.WRITER_SYSTEM,
                                  f"Suggest ONE new topic for the category '{c}' of a radiology explainer channel. "
                                  f"Different from: {sorted(used)[:80]}. Reply with the topic only, max 12 words.",
                                  max_tokens=100)
    return text.strip().strip('"').splitlines()[0], c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--no-send", action="store_true")
    a = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    st = S.load()
    st.setdefault("drafts", [])
    now = S.now(cfg)

    if a.mock:
        post = generator.finalize(json.loads((ROOT / "samples" / "sample_post.json").read_text(encoding="utf-8")),
                                  cfg, "Sample: fatty liver", "report_words")
    else:
        note = st.pop("note", None)
        today = [d for d in st["drafts"] if d["date"] == f"{now:%Y-%m-%d}"]
        redo = st.pop("redo", None)
        if redo and not st.get("next_topic"):
            topic, cat = redo["topic"], redo["category"]  # /remake: same subject, following your note
        elif note and today and today[-1]["status"] == "rejected" and not st.get("next_topic"):
            topic, cat = today[-1]["topic"], today[-1]["category"]  # redo the same topic, following your note
        else:
            topic, cat = pick_topic(cfg, st)
        brief = topic + (f"\n(Note from the radiologist for this video: {note})" if note else "")
        ref_path = None
        if st.get("ref_images"):
            ref = st.pop("ref_images")[-1]
            from src.telegram import TG as _TG
            (ROOT / "out").mkdir(exist_ok=True)
            if ref.get("path"):  # an image saved in the repo (e.g. added by Claude)
                ref_path = ROOT / ref["path"]
            else:
                ref_path = _TG().download(ref["file_id"], ROOT / "out" / "reference_scan.jpg")
            ok, desc = generator.describe_reference(cfg, ref_path, ref.get("caption", ""))
            if not ok:
                log("⚠️  Reference image seems to show patient details; not using it.")
                _TG().send_text("⚠️ I didn't use your reference image: it seems to show a patient name, ID or date. "
                                "Crop or blank those out and send it again.")
                ref_path = None
            else:
                log(f"🖼 Using your reference scan: {desc[:120]}")
                brief += ("\n\nREAL SCAN SLIDE: the radiologist supplied a real, anonymised scan image. Content slide 1 "
                          "will SHOW THIS IMAGE instead of a drawing. Make slide 1's heading like 'On a real scan', and "
                          "use its lines and narration to walk the viewer through what it shows and what each label "
                          f"points to. What the image shows: {desc}")
        log(f"🧠 Topic: {topic} [{cat}]" + (f" — with your note: {note}" if note else ""))
        try:
            post = generator.create_checked_post(cfg, brief, cat, log)
        except generator.DraftRejected as e:
            S.save(st)
            out = ROOT / "out"
            out.mkdir(exist_ok=True)
            (out / "rejected_draft.json").write_text(json.dumps({"topic": topic, "issues": e.issues, "draft": e.draft},
                                                                indent=2, ensure_ascii=False), encoding="utf-8")
            raise
        post["topic"] = topic
        if ref_path and post.get("slides"):
            post["slides"][0]["ref_image"] = str(ref_path)

    did = f"{now:%Y%m%d-%H%M}-" + hashlib.md5(post["yt_title"].encode()).hexdigest()[:5]
    out = ROOT / "out" / did
    log("🎨 Drawing frames …")
    frames = render.render_post(post, cfg, out / "frames")
    log("🎞  Building the Short …")
    video = reel.build_reel(post, frames, cfg, out / "frames", log)
    final = out / "short.mp4"
    video.replace(final)
    for sl in post.get("slides", []):
        sl.pop("ref_src", None)
    (out / "post.json").write_text(json.dumps(post, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"📁 Saved to {final.relative_to(ROOT)}")
    if a.no_send:
        return

    from src.telegram import TG
    tg = TG()
    sch = cfg["schedule"]
    notes = "\n".join(f"• {n}" for n in post.get("review_notes", [])[:3])
    caption = (("🧪 TEST PREVIEW: sample only, never uploaded (no buttons)\n" if a.mock else "") +
               f"🎬 {post['yt_title']}\n\n{post['yt_description']}\n\n"
               f"Tags: {', '.join(post['tags'][:8])}\n" +
               (f"\nReviewer notes (not blocking):\n{notes}\n" if notes else "") +
               f"\n✅ Publish → goes live from {sch['publish_at']} (or at the next check if later)\n"
               f"❌ Remake → a new video at the next check. Reply with a note to steer it, or /topic <subject>.\n"
               f"⏱ Your tap is picked up at the next check (every ~2 h), so the button may keep loading until then. "
               f"That's normal: tap once.")
    log("📲 Sending preview to Telegram …")
    msg_id, file_id = tg.send_preview(final, caption, did, buttons=not a.mock)
    if a.mock:
        log("🧪 Mock preview sent (not added to the schedule).")
        return
    for d in st["drafts"]:  # an older unanswered preview from today is replaced by this one
        if d["date"] == f"{now:%Y-%m-%d}" and d["status"] == "pending":
            d["status"] = "replaced"
    st["drafts"].append({"id": did, "date": f"{now:%Y-%m-%d}", "status": "pending", "title": post["yt_title"],
                         "topic": post["topic"], "category": post["category"], "message_id": msg_id, "file_id": file_id,
                         "meta": {k: post[k] for k in ("yt_title", "full_description", "tags")}})
    S.save(st)
    log("✅ Preview sent. Waiting for your ✅ / ❌.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        log(f"❌ {e}")
        sys.exit(1)
