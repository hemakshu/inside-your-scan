"""Small JSON state kept in the repo: drafts waiting for you, Telegram position, posting history."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "state.json"
HISTORY = ROOT / "state" / "history.json"


def load(path=STATE, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else (default or {})


def save(obj, path=STATE):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def now(cfg):
    return datetime.now(ZoneInfo(cfg["schedule"]["timezone"]))


def at(now_, hhmm):
    h, m = map(int, hhmm.split(":"))
    return now_.replace(hour=h, minute=m, second=0, microsecond=0)


def today_drafts(st, day):
    return [d for d in st.get("drafts", []) if d["date"] == day]
