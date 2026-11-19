"""Hard rules every draft must pass before it is even shown to you.

Layer 1 (this file): fixed word/phrase rules that cannot be talked around.
Layer 2 (generator.review_post): an independent Claude "senior radiologist" review.
Layer 3: your ✅ on Telegram. Nothing is uploaded without it.
"""
import re

PCPNDT = [  # PC&PNDT Act: nothing that hints at the baby's sex
    r"\bgender\b", r"\bsex\s+(of|determination|detection|selection|prediction|reveal)",
    r"\b(baby'?s?|fetal|foetal|fetus'?s?|foetus'?s?)\s+sex\b", r"\bboy\s*(or|/)\s*girl\b",
    r"\bgirl\s*(or|/)\s*boy\b", r"\bit'?s\s+a\s+(boy|girl)\b", r"\b(nub|ramzi|skull)\s+theory\b",
    r"\bpink\s+or\s+blue\b",
]
PROMOTION = [  # medical-ethics / advertising red lines
    r"\bbest\s+(clinic|doctor|radiologist|centre|center|hospital)\b", r"\bno\.?\s*1\b", r"\b#1\b",
    r"\bguarantee(d|s)?\b", r"\b100\s*%\s*(accurate|accuracy|safe|cure)", r"\bcures?\b", r"\bmiracle\b",
    r"\bdiscount\b", r"\b\d+\s*%\s*off\b", r"₹\s*\d", r"\$\s*\d", r"\bbook\s+(now|your\s+scan|an?\s+appointment)\b",
    r"\bcall\s+(us|now)\b", r"\bvisit\s+(our|my)\s+(clinic|centre|center)\b", r"\btestimonial",
    r"\banjaneya\b", r"\bnani\s+daman\b",  # keep the channel separate from the clinic
]
CLICKBAIT = [
    r"\byou\s+won'?t\s+believe\b", r"\bshocking\b", r"\bdoctors\s+hate\b", r"\bsecret\s+(trick|cure)\b",
    r"\bthis\s+one\s+trick\b", r"\bwill\s+(kill|destroy)\s+you\b",
]
SAFETY = [
    r"\bstop\s+(taking\s+)?(your\s+)?(medicine|medication|treatment)", r"\bno\s+need\s+(to\s+see|for)\s+(a\s+)?doctor",
    r"\bself[-\s]?medicat", r"\bdon'?t\s+(see|consult|tell)\s+(a\s+|your\s+)?doctor", r"\bskip\s+(your\s+)?scan\b",
    r"\byou\s+(definitely\s+)?have\s+(cancer|a\s+tumou?r)\b", r"\bdiagnose\s+yourself\b",
]
ALL = [("PC&PNDT", PCPNDT), ("promotion/ethics", PROMOTION), ("clickbait", CLICKBAIT), ("medical safety", SAFETY)]


def _texts(post):
    parts = [post.get(k, "") for k in ("hook", "subtitle", "takeaway", "hook_narration", "cta_narration",
                                       "yt_title", "yt_description")]
    parts += post.get("tags", [])
    for s in post.get("slides", []):
        parts += [s.get("heading", ""), *s.get("lines", []), s.get("narration", "")]
        parts.append(((s.get("visual") or {}).get("annotation") or {}).get("label", ""))
    return [p for p in parts if p]


def check_post(post, cfg):
    problems = []
    blob = "\n".join(_texts(post))
    for label, pats in ALL:
        for pat in pats:
            m = re.search(pat, blob, flags=re.IGNORECASE)
            if m:
                problems.append(f"{label}: forbidden phrase '{m.group(0)}'")
    c = cfg["content"]
    n = len(post.get("slides", []))
    if not (c["slides_min"] <= n <= c["slides_max"]):
        problems.append(f"structure: {n} slides (need {c['slides_min']}–{c['slides_max']})")
    if len(post.get("hook", "")) > 60:
        problems.append("structure: hook longer than 60 characters")
    if not 15 <= len(post.get("yt_title", "")) <= 90:
        problems.append("structure: YouTube title must be 15–90 characters")
    for i, s in enumerate(post.get("slides", []), 1):
        if not s.get("heading") or not s.get("lines"):
            problems.append(f"structure: slide {i} missing heading/lines")
        if len(s.get("lines", [])) > 3 or any(len(x) > 70 for x in s.get("lines", [])):
            problems.append(f"structure: slide {i} needs at most 3 lines of at most 70 characters")
        if len(s.get("narration", "").split()) > 34:
            problems.append(f"structure: slide {i} narration over 34 words (Shorts must stay short)")
    words = sum(len(s.get("narration", "").split()) for s in post.get("slides", [])) + \
        len(post.get("hook_narration", "").split()) + len(post.get("cta_narration", "").split())
    if words > 150:
        problems.append(f"structure: total narration {words} words; keep it under 150 (about 55 seconds)")
    return problems
