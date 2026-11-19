"""Uploads to YouTube with the official Data API (resumable upload, OAuth refresh token)."""
import json
import os
from pathlib import Path

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YT:
    def __init__(self, cfg):
        clean = lambda k: "".join((os.environ.get(k) or "").split())
        self.client_id, self.secret, self.refresh = clean("YT_CLIENT_ID"), clean("YT_CLIENT_SECRET"), clean("YT_REFRESH_TOKEN")
        if not (self.client_id and self.secret and self.refresh):
            raise RuntimeError("YT_CLIENT_ID / YT_CLIENT_SECRET / YT_REFRESH_TOKEN secrets are missing (see README).")
        self.cfg = cfg["youtube"]
        self._token = None

    def token(self):
        if not self._token:
            r = requests.post(TOKEN_URL, data={"client_id": self.client_id, "client_secret": self.secret,
                                               "refresh_token": self.refresh, "grant_type": "refresh_token"}, timeout=60)
            j = r.json()
            if "access_token" not in j:
                hint = ""
                if j.get("error") == "invalid_grant":
                    hint = (" — the refresh token is invalid or expired. If your Google Cloud app is still in "
                            "'Testing', tokens expire after 7 days: set it to 'In production' and make a new token.")
                raise RuntimeError(f"YouTube sign-in failed: {j.get('error_description') or j}{hint}")
            self._token = j["access_token"]
        return self._token

    def _h(self):
        return {"Authorization": f"Bearer {self.token()}"}

    def channel(self):
        r = requests.get("https://www.googleapis.com/youtube/v3/channels", headers=self._h(),
                         params={"part": "snippet", "mine": "true"}, timeout=60)
        j = r.json()
        if r.status_code != 200 or not j.get("items"):
            raise RuntimeError(f"Could not read your YouTube channel: {j.get('error', j)}")
        return j["items"][0]["snippet"]["title"]

    def upload(self, video: Path, post: dict):
        meta = {
            "snippet": {"title": post["yt_title"], "description": post["full_description"][:4900],
                        "tags": post["tags"], "categoryId": self.cfg["category_id"],
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": {"privacyStatus": self.cfg["privacy"], "selfDeclaredMadeForKids": self.cfg["made_for_kids"],
                       "containsSyntheticMedia": False},  # drawn, non-realistic visuals: no AI disclosure needed
        }
        size = video.stat().st_size
        r = requests.post(UPLOAD_URL, params={"uploadType": "resumable", "part": "snippet,status"},
                          headers={**self._h(), "Content-Type": "application/json; charset=UTF-8",
                                   "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
                          data=json.dumps(meta), timeout=120)
        if r.status_code != 200 or "Location" not in r.headers:
            raise RuntimeError(f"YouTube upload could not start ({r.status_code}): {r.text[:400]}")
        with open(video, "rb") as f:
            put = requests.put(r.headers["Location"], data=f, timeout=900,
                               headers={**self._h(), "Content-Type": "video/mp4", "Content-Length": str(size)})
        if put.status_code not in (200, 201):
            raise RuntimeError(f"YouTube upload failed ({put.status_code}): {put.text[:400]}")
        j = put.json()
        vid = j["id"]
        status = j.get("status", {}).get("privacyStatus")
        return vid, f"https://youtube.com/shorts/{vid}", status
