"""Telegram bot: sends you each finished Short with ✅ / ❌ buttons and reads your answers.
No server needed: every wake-up simply asks Telegram for new button presses."""
import os
from pathlib import Path

import requests

API = "https://api.telegram.org"


class TG:
    def __init__(self):
        self.token = "".join((os.environ.get("TELEGRAM_BOT_TOKEN") or "").split())
        self.chat = "".join((os.environ.get("TELEGRAM_CHAT_ID") or "").split())
        if not self.token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN secret is missing (see README: Telegram).")

    def _call(self, method, files=None, http_timeout=60, **data):
        r = requests.post(f"{API}/bot{self.token}/{method}", data=data if files else None,
                          json=None if files else data, files=files, timeout=http_timeout)
        j = r.json()
        if not j.get("ok"):
            raise RuntimeError(f"Telegram {method} failed: {j.get('description', r.text[:200])}")
        return j["result"]

    def me(self):
        return self._call("getMe")

    def send_text(self, text):
        return self._call("sendMessage", chat_id=self.chat, text=text, disable_web_page_preview=True)

    def send_preview(self, video: Path, caption: str, draft_id: str, buttons: bool = True):
        import json
        kb = {"inline_keyboard": [[{"text": "✅ Publish", "callback_data": f"ok:{draft_id}"},
                                   {"text": "❌ Remake", "callback_data": f"no:{draft_id}"}]]}
        with open(video, "rb") as f:
            res = self._call("sendVideo", files={"video": (video.name, f, "video/mp4")}, http_timeout=300,
                             chat_id=self.chat, caption=caption[:1020], supports_streaming="true",
                             width="1080", height="1920", **({"reply_markup": json.dumps(kb)} if buttons else {}))
        return res["message_id"], res["video"]["file_id"]

    def updates(self, offset):
        return self._call("getUpdates", offset=offset, timeout=0, allowed_updates=["callback_query", "message"])

    def answer(self, cb_id, text):
        try:
            self._call("answerCallbackQuery", callback_query_id=cb_id, text=text[:190])
        except RuntimeError:
            pass  # button answers expire after a while; harmless

    def edit_caption(self, message_id, text):
        try:
            self._call("editMessageCaption", chat_id=self.chat, message_id=message_id, caption=text[:1020])
        except RuntimeError:
            pass

    def download(self, file_id, dest: Path):
        info = self._call("getFile", file_id=file_id)
        r = requests.get(f"{API}/file/bot{self.token}/{info['file_path']}", timeout=300)
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest
