"""Writes each Short with Claude (structured output), then a second Claude call reviews it as a
senior radiologist. Only reviewed drafts are rendered and sent to you for approval."""
import json
from pathlib import Path
import os
import re
import time

import requests

from . import guardrails
from .organs import MODALITIES, ORGAN_NAMES, ORGANS, catalogue_text

API_URL = "https://api.anthropic.com/v1/messages"


def _strict(schema):
    """Structured outputs need every object closed (additionalProperties: false) with all fields required."""
    if isinstance(schema, dict):
        schema = {k: _strict(v) for k, v in schema.items()}
        if schema.get("type") == "object" and "properties" in schema:
            schema["additionalProperties"] = False
            schema["required"] = list(schema["properties"])
    elif isinstance(schema, list):
        schema = [_strict(x) for x in schema]
    return schema


def _call_claude(cfg: dict, system: str, user: str, max_tokens: int = 3500, tool: dict | None = None):
    """Plain call returns text. With `tool` (a name + JSON schema), Claude must reply in exactly
    that JSON shape (Anthropic structured outputs), and the parsed dict is returned."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set (add it as a GitHub secret).")
    body = {"model": cfg["llm"]["model"], "max_tokens": max_tokens, "system": system,
            "messages": [{"role": "user", "content": user}]}
    if tool:
        body["output_config"] = {"format": {"type": "json_schema", "schema": _strict(tool["input_schema"])}}

    def send(b):
        for attempt in range(3):  # retry brief API hiccups (overloaded / rate limit)
            r = requests.post(API_URL, json=b, timeout=240,
                              headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                       "content-type": "application/json"})
            if r.status_code in (429, 500, 502, 503, 529) and attempt < 2:
                time.sleep(20 * (attempt + 1))
                continue
            return r

    r = send(body)
    if r.status_code == 400 and tool:
        # model/account without structured outputs → ask for plain JSON and parse it ourselves
        print(f"  ℹ️  structured output not accepted ({r.text[:160]}); using plain JSON", flush=True)
        body.pop("output_config")
        body["messages"][0]["content"] += ("\n\nReply with ONLY one JSON object matching this schema, no other text:\n"
                                           + json.dumps(tool["input_schema"]))
        r = send(body)
    if r.status_code != 200:
        raise RuntimeError(f"Claude API error {r.status_code}: {r.text[:500]}")
    j = r.json()
    if j.get("stop_reason") == "max_tokens":
        raise ValueError(f"Claude's reply was cut off at {max_tokens} tokens")
    if j.get("stop_reason") == "refusal":
        raise ValueError("Claude declined this draft")
    text = "".join(b.get("text", "") for b in j["content"] if b.get("type") == "text")
    return _parse_json(text) if tool else text


def _parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("model did not return JSON")
    return json.loads(m.group(0))




ANCHORS = sorted({a for o in ORGANS.values() for a in o["anchors"]})
VISUAL = {"type": "object", "properties": {
    "organ": {"type": "string", "enum": ORGAN_NAMES},
    "modality": {"type": "string", "enum": list(MODALITIES)},
    "annotation": {"type": "object", "properties": {
        "type": {"type": "string", "enum": ["arrow", "caliper", "circle", "none"]},
        "anchor": {"type": "string", "enum": ANCHORS},
        "label": {"type": "string"}}}}}
POST_TOOL = {"name": "submit_post", "input_schema": {"type": "object", "properties": {
    "hook": {"type": "string"}, "hook_emphasis": {"type": "string"}, "subtitle": {"type": "string"},
    "cover_visual": VISUAL,
    "slides": {"type": "array", "items": {"type": "object", "properties": {
        "heading": {"type": "string"}, "lines": {"type": "array", "items": {"type": "string"}},
        "narration": {"type": "string"}, "visual": VISUAL}}},
    "takeaway": {"type": "string"}, "hook_narration": {"type": "string"}, "cta_narration": {"type": "string"},
    "yt_title": {"type": "string"}, "yt_description": {"type": "string"},
    "tags": {"type": "array", "items": {"type": "string"}}}}}
REVIEW_TOOL = {"name": "submit_review", "input_schema": {"type": "object", "properties": {
    "approved": {"type": "boolean"},
    "issues": {"type": "array", "items": {"type": "object", "properties": {
        "severity": {"type": "string", "enum": ["blocking", "polish"]},
        "problem": {"type": "string"}, "fix": {"type": "string"}}}}}}}

WRITER_SYSTEM = """You write YouTube Shorts for "Inside Your Scan", an English channel where a radiologist
explains scans and scan reports to ordinary adults worldwide. Voice: calm, clear, kind, a little warm.
Plain words; explain any medical term the first time; short spoken sentences.

ABSOLUTE RULES (a draft that breaks any is rejected):
1. Medically accurate, mainstream and conservative. No numbers you are not certain of. If a figure varies,
   say it varies. Never diagnose the viewer; always point them to their own doctor for their own report.
2. PC&PNDT Act: never mention or hint at the sex of a baby, in any way.
3. Medical ethics: education only. No self-promotion, clinics, prices, booking, testimonials, superlatives,
   guarantees or cure claims. Never mention any clinic or city.
4. No fear-mongering or clickbait. Curiosity is fine; scaring people is not.
5. Visuals are drawn illustrations from a fixed library. Choose the organ and look that best fit each slide.
   Annotation labels are 1–3 words naming a part (e.g. "Bright liver", "Stone", "Shadow"), never a fake
   measurement or number.
6. Every video must have its own clear point; do not pad with generic filler."""


def write_post(cfg, topic, category, feedback=None, previous=None):
    c = cfg["content"]
    fb = ""
    if feedback and previous:
        fb = ("\n\nREVISION TASK: below is your previous draft and the required fixes. Return the SAME draft with ONLY "
              "those fixes applied; keep everything else unchanged.\nRequired fixes:\n- " + "\n- ".join(feedback) +
              "\n\nPrevious draft:\n" + json.dumps(previous, ensure_ascii=False, indent=1))
    elif feedback:
        fb = "\n\nYOUR PREVIOUS DRAFT FAILED THESE CHECKS:\n- " + "\n- ".join(feedback) + "\nAvoid all of them."
    user = f"""Topic: {topic}
Category: {category}
Audience: {c['audience']}
Format: YouTube Short, about 40–55 seconds: a cover, {c['slides_min']}–{c['slides_max']} content slides, a closing slide.

Visual library (organ: what it shows; best look; anchors you can point at):
{catalogue_text()}
Looks: us (ultrasound), doppler (only for 'vessel'), ct, mri, xray, diagram (machines/body outline).

Fields:
- hook: on-screen cover line, max 55 characters, makes a scroller stop; it may quote a report word.
- hook_emphasis: 1–3 words copied exactly from the hook to highlight (or empty).
- subtitle: max 70 characters.
- cover_visual + each slide's visual: organ, modality, annotation (type, anchor, short label).
- slides: heading (max 6 words), lines (2–3, each max 60 characters), narration (1–2 sentences, max 30 words).
- takeaway: one line, max 70 characters.
- hook_narration: spoken opener, max 18 words. cta_narration: closing line, max 22 words, MUST say this is for
  learning and to talk to your own doctor, then invite viewers to follow for one scan explained every day.
- yt_title: 40–80 characters, specific and searchable (e.g. "What 'Fatty Liver' on Your Ultrasound Means").
- yt_description: 2–3 plain sentences summarising the video (no hashtags, no links; a disclaimer is added).
- tags: 6–10 search phrases people actually type.{fb}"""
    return _call_claude(cfg, WRITER_SYSTEM, user, max_tokens=8000, tool=POST_TOOL)


REVIEWER_SYSTEM = """You are a senior consultant radiologist and the final reviewer for a public YouTube
channel. Block anything wrong or harmful; do not block a good video over taste or optional detail."""


def review_post(cfg, post):
    ref_note = ("\nNote: content slide 1 shows a REAL anonymised scan image supplied by the radiologist (described in "
                "the topic brief); its text is meant to walk the viewer through that image."
                if "REAL SCAN SLIDE" in post.get("_brief", "") else "")
    user = f"""Review this YouTube Short draft (the visuals are drawn illustrations chosen from a fixed library).{ref_note}

Mark an issue BLOCKING only if you are confident it is one of these:
1. A medically wrong, outdated or misleading statement; a wrong or invented number; an annotation pointing at
   the wrong structure or a visual that clearly misrepresents the anatomy being discussed.
2. Anything that diagnoses the viewer, discourages seeing a doctor, or could cause harm or panic.
3. Any hint at a baby's sex; any self-promotion, clinic, price or cure claim.
4. A misleading title/hook that the video doesn't deliver on.
Everything else (wording, style, extra detail) is POLISH and does not block.

Draft:
{json.dumps(post, ensure_ascii=False, indent=2)}

Reply with approved (true if there are no BLOCKING issues) and issues (max 8, each with severity, problem, fix)."""
    v = _call_claude(cfg, REVIEWER_SYSTEM, user, max_tokens=4000, tool=REVIEW_TOOL)
    issues = v.get("issues") or []
    blocking = [f"{i.get('problem', '')} → FIX: {i.get('fix', '')}" for i in issues if i.get("severity") == "blocking"]
    polish = [f"{i.get('problem', '')} → {i.get('fix', '')}" for i in issues if i.get("severity") != "blocking"]
    if v.get("approved") is not True and not blocking:
        blocking = polish or ["reviewer did not approve"]
    return blocking, polish


class DraftRejected(RuntimeError):
    def __init__(self, msg, draft, issues):
        super().__init__(msg)
        self.draft, self.issues = draft, issues


def describe_reference(cfg, image_path, caption=""):
    """Look at a real scan the radiologist sent. Returns (ok, description)."""
    import base64
    data = base64.b64encode(Path(image_path).read_bytes()).decode()
    mt = "image/png" if Path(image_path).read_bytes()[:4] == b"\x89PNG" else "image/jpeg"
    content = [{"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}},
               {"type": "text", "text": (
                   "This is a real, anonymised scan image a radiologist wants to show in a patient-education Short."
                   + (f" His note: {caption}" if caption else "") +
                   "\nLine 1: write exactly IDENTIFIERS: YES if any patient name, ID number, date of birth or hospital "
                   "name is readable in the image, otherwise IDENTIFIERS: NO.\nThen, in at most 60 words, describe what "
                   "the image shows and what each visible label/marker points to, in plain language for a layperson. "
                   "Never mention or guess the baby's sex.")}]
    text = _call_claude(cfg, "You describe medical images accurately and briefly.", content, max_tokens=300)
    first, _, rest = text.strip().partition("\n")
    return ("YES" not in first.upper()), rest.strip()


def create_checked_post(cfg, topic, category, log=print, extra_feedback=None):
    feedback, previous, post, polish = (extra_feedback or None), None, None, []
    for attempt in range(1, cfg["llm"]["max_attempts"] + 1):
        log(f"  ✍️  {'drafting' if not previous else 'revising'} (attempt {attempt}) …")
        try:
            post = write_post(cfg, topic, category, feedback, previous)
        except (ValueError, KeyError, TypeError) as e:
            log(f"  ⚠️  draft unusable ({e}) — trying again")
            continue
        problems = guardrails.check_post(post, cfg)
        if problems:
            log("  ⚠️  failed rules: " + " | ".join(problems))
            feedback, previous = problems, None
            continue
        log("  🔎 senior-radiologist review …")
        try:
            post["_brief"] = topic
            blocking, polish = review_post(cfg, post)
            post.pop("_brief", None)
        except (ValueError, KeyError, TypeError) as e:
            log(f"  ⚠️  review unusable ({e}) — reviewing a fresh draft")
            continue
        for n in polish:
            log(f"     · note: {n}")
        if not blocking:
            log("  ✅ draft approved by reviewer")
            return finalize(post, cfg, topic, category, polish)
        log("  ⚠️  must fix: " + " | ".join(blocking))
        feedback, previous = blocking, post
    raise DraftRejected(f"No safe draft after {cfg['llm']['max_attempts']} attempts. Last issues: {feedback}",
                        post, feedback)


def finalize(post, cfg, topic, category, polish=()):
    tags, seen = [], set()
    for t in post.get("tags", []) + ["radiology", "scan explained", "medical education"]:
        t = re.sub(r"[<>#]", "", t).strip()
        if t and t.lower() not in seen and len(",".join(tags + [t])) < 450:
            seen.add(t.lower())
            tags.append(t)
    post["tags"] = tags
    post["topic"], post["category"], post["review_notes"] = topic, category, list(polish)
    post["yt_title"] = post["yt_title"].strip()[:95]
    post["full_description"] = (post["yt_description"].strip() + "\n\n" + cfg["channel"]["byline"] + "\n\n" +
                                cfg["channel"]["description_footer"].strip() + "\n\n#Shorts #Radiology #ScanExplained")
    return post
