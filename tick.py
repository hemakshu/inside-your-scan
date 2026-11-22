#!/usr/bin/env python3
"""The quick check that runs at every wake-up (needs only `requests` + `PyYAML`, takes seconds):

  1. read your Telegram taps (✅ / ❌) and notes
  2. publish today's approved video once it's time
  3. tidy up old drafts
  4. tell the workflow whether a new video needs making (make=true)
"""
import os
import sys
from pathlib import Path

import yaml

from src import state as S
from src.telegram import TG

ROOT = Path(__file__).resolve().parent
S_cfg = None


def log(m):
    print(m, flush=True)


def output(**kv):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def read_telegram(tg, st):
    """Apply button taps and notes since the last check."""
    offset = st.get("tg_offset", 0)
    ups = tg.updates(offset)
    by_id = {d["id"]: d for d in st.get("drafts", [])}
    for u in ups:
        st["tg_offset"] = u["update_id"] + 1
        cq = u.get("callback_query")
        if cq:
            if str(cq["message"]["chat"]["id"]) != tg.chat:
                continue
            action, _, did = cq.get("data", "").partition(":")
            d = by_id.get(did)
            if not d:
                tg.answer(cq["id"], "This preview is no longer active.")
                continue
            if d["status"] == "expired" and action == "ok":
                d["status"] = "pending"  # a late ✅ on an older preview still counts
            if d["status"] != "pending":
                tg.answer(cq["id"], f"Already {d['status']}.")
                continue
            if action == "ok":
                d["status"] = "approved"
                tg.answer(cq["id"], "Approved ✅ Nothing else to do: it goes live automatically.")
                tg.edit_caption(d["message_id"], f"✅ Approved: {d['title']}\nGoes live automatically from "
                                                 f"{S_cfg['schedule']['publish_at']} IST. You'll get the link here.")
                tg.send_text(f"✅ Approved: {d['title']}\nIt goes live automatically from {S_cfg['schedule']['publish_at']} "
                             "IST. I'll send you the YouTube link. Nothing else to do.")
                log(f"✅ You approved: {d['title']}")
            elif action == "no":
                d["status"] = "rejected"
                tg.answer(cq["id"], "OK, making a new one. Reply with a note if you want something specific.")
                tg.edit_caption(d["message_id"], f"❌ Rejected: {d['title']}\nA new video will be made at the next check.")
                log(f"❌ You rejected: {d['title']}")
            continue
        msg = u.get("message")
        if msg and str(msg["chat"]["id"]) == tg.chat and msg.get("text"):
            text = msg["text"].strip()
            if text.lower().startswith("/topic "):
                st["next_topic"] = text[7:].strip()
                tg.send_text(f"📝 Next video will be about: {st['next_topic']}")
                log(f"📝 Next topic set: {st['next_topic']}")
            elif text.lower() in ("/status", "status"):
                tg.send_text(status_text(st))
            elif text.lower().split()[0] in ("/remake", "/regenerate", "/redo", "/reject"):
                extra = text.split(None, 1)[1].strip() if len(text.split(None, 1)) > 1 else ""
                live = [d for d in st.get("drafts", []) if d["status"] in ("pending", "approved")]
                if live:
                    d = live[-1]
                    d["status"] = "rejected"
                    tg.edit_caption(d["message_id"], f"❌ Rejected: {d['title']}\nA new video is being made.")
                    st["redo"] = {"topic": d["topic"], "category": d["category"]}  # remake the same subject
                if extra:
                    st["note"] = extra
                tg.send_text("🔁 OK, making a new video now" + (f", following your note: {extra}" if extra else "") + ".")
                log(f"🔁 Remake requested{': ' + extra if extra else ''}")
            elif text.startswith("/"):
                tg.send_text("Commands:\n✅ / ❌ buttons on a preview\n/remake <optional note>: make a new video\n"
                             "/topic <subject>: choose the next subject\n/status: recent videos\n"
                             "Any plain message is used as a note for the next video.")
            elif text.lower().strip("!. ") in ("hi", "hello", "hey", "ok", "okay", "thanks", "thank you", "start"):
                pass  # greetings aren't notes
            else:
                st["note"] = text
                tg.send_text("📝 Noted, I'll use that for the next video.")
                log(f"📝 Note for next draft: {text}")


def status_text(st):
    ds = st.get("drafts", [])[-5:]
    if not ds:
        return "No videos yet."
    return "Recent videos:\n" + "\n".join(f"• {d['date']}: {d['status']}: {d['title']}" for d in ds)


def publish(cfg, st, tg, d, log=log):
    from src.youtube import YT
    tmp = ROOT / "out" / f"{d['id']}.mp4"
    tmp.parent.mkdir(exist_ok=True)
    log(f"📥 Fetching approved video from Telegram: {d['title']}")
    tg.download(d["file_id"], tmp)
    log("📤 Uploading to YouTube …")
    vid, url, privacy = YT(cfg).upload(tmp, d["meta"])
    d.update(status="published", video_id=vid, url=url)
    hist = S.load(S.HISTORY, {"posts": []})
    hist["posts"].append({"date": d["date"], "topic": d["topic"], "category": d["category"], "url": url})
    S.save(hist, S.HISTORY)
    note = "" if privacy == "public" else (f"\n⚠️ YouTube set it to '{privacy}'. Your Google project may need YouTube's "
                                           "API audit before uploads can be public (see README).")
    tg.send_text(f"🎉 Live on YouTube: {d['title']}\n{url}{note}")
    log(f"🎉 Published: {url} ({privacy})")


def main():
    global S_cfg
    cfg = S_cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    st = S.load()
    st.setdefault("drafts", [])
    now = S.now(cfg)
    day = f"{now:%Y-%m-%d}"
    sch = cfg["schedule"]
    tg = TG()

    read_telegram(tg, st)

    # tidy: previews from earlier days you never answered are replaced by today's
    for d in st["drafts"]:
        if d["date"] < day and d["status"] == "pending":
            d["status"] = "expired"
    # approved on an earlier day but never published (e.g. GitHub skipped the evening checks): publish now
    for d in [d for d in st["drafts"] if d["date"] < day and d["status"] == "approved"]:
        try:
            publish(cfg, st, tg, d)
        except Exception as e:  # noqa: BLE001
            d["error"] = str(e)[:300]
            tg.send_text(f"⚠️ Couldn't publish '{d['title']}': {str(e)[:300]}\nI'll retry at the next check.")
            S.save(st)
            raise
    # keep the list short
    st["drafts"] = st["drafts"][-40:]

    make = False
    if cfg.get("paused"):
        log("⏸  Paused in config.yaml.")
    else:
        mine = S.today_drafts(st, day)
        live = [d for d in mine if d["status"] in ("pending", "approved", "published")]
        approved = [d for d in mine if d["status"] == "approved"]
        in_window = S.at(now, sch["publish_at"]) <= now <= S.at(now, sch["latest"])
        if approved and in_window:
            try:
                publish(cfg, st, tg, approved[0])
            except Exception as e:  # noqa: BLE001
                approved[0]["error"] = str(e)[:300]
                tg.send_text(f"⚠️ Couldn't publish '{approved[0]['title']}': {str(e)[:300]}\nI'll retry at the next check.")
                S.save(st)
                raise
        elif approved:
            log(f"⏳ Approved and waiting for {sch['publish_at']}: {approved[0]['title']}")
        elif any(d["status"] == "pending" for d in mine):
            log("⏳ Waiting for your ✅ / ❌ on Telegram.")
        elif any(d["status"] == "published" for d in mine):
            log("✅ Today's video is already live.")
        if not live:
            if len(mine) >= sch["max_drafts_per_day"]:
                log(f"⏭  {len(mine)} drafts made today already; trying again tomorrow.")
            elif S.at(now, sch["make_from"]) <= now <= S.at(now, sch["latest"]):
                make = True
                log("🛠  No video for today yet: a new one will be made now.")
            else:
                log(f"⏭  Outside making hours ({sch['make_from']}–{sch['latest']}).")
    S.save(st)
    output(make=str(make).lower())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        log(f"❌ {e}")
        sys.exit(1)
