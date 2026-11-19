#!/usr/bin/env python3
"""Checks every connection without making or posting anything.
Run from GitHub: Actions → Inside Your Scan → Run workflow → mode: check-setup."""
import sys

import requests
import yaml

from src import generator
from src.telegram import TG

cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
ok = True


def step(name, fn):
    global ok
    try:
        print(f"✅ {name}: {fn()}")
    except Exception as e:  # noqa: BLE001
        ok = False
        print(f"❌ {name}: {e}")


step("Claude API", lambda: generator._call_claude(cfg, "Reply with one word.", "Say ready.", 10).strip())


def telegram():
    tg = TG()
    me = tg.me()
    if not tg.chat:
        ups = requests.get(f"https://api.telegram.org/bot{tg.token}/getUpdates", timeout=30).json().get("result", [])
        chats = {str(u["message"]["chat"]["id"]): u["message"]["chat"].get("first_name", "")
                 for u in ups if u.get("message")}
        if chats:
            raise RuntimeError(f"bot @{me['username']} works. Set TELEGRAM_CHAT_ID to: "
                               + ", ".join(f"{k} ({v})" for k, v in chats.items()))
        raise RuntimeError(f"bot @{me['username']} works, but TELEGRAM_CHAT_ID is missing. "
                           f"Open Telegram, send 'hi' to @{me['username']}, then run check-setup again.")
    tg.send_text("✅ Inside Your Scan is connected. Previews will arrive here.")
    return f"@{me['username']} → test message sent to you"


step("Telegram", telegram)


def youtube():
    from src.youtube import YT
    return f"signed in to channel '{YT(cfg).channel()}'"


step("YouTube", youtube)
sys.exit(0 if ok else 1)
