"""Builds the Short: frames + gentle zoom + crossfades + AI voiceover + soft ambient pad, under a size cap."""
import asyncio
import json
import os
import random
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
XF = 0.45  # crossfade seconds


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd[:6])} …\n{r.stderr[-1500:]}")
    return r.stdout


def _duration(path: Path) -> float:
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)])
    return float(json.loads(out)["format"]["duration"])


BACKUP_VOICES = ["en-US-AndrewMultilingualNeural", "en-US-GuyNeural", "en-IN-PrabhatNeural"]


async def _say(edge_tts, text, voice, rate, f):
    """Microsoft's free TTS sometimes returns 'No audio was received'. Retry, then try backup voices."""
    import re
    text = text.replace("&", " and ")
    clean = re.sub(r"[<>*_#`~|\[\]{}]", " ", text)
    clean = re.sub(r"[\U0001F000-\U0001FFFF\u2600-\u27BF]", "", clean)  # emoji
    clean = re.sub(r"\s+", " ", clean).strip() or "."
    tries = [(voice, rate)] * 3 + [(v, rate) for v in BACKUP_VOICES if v != voice and voice.split("-")[0] == v.split("-")[0]]
    last = None
    for n, (v, r) in enumerate(tries):
        try:
            await edge_tts.Communicate(clean, v, rate=r).save(str(f))
            if f.exists() and f.stat().st_size > 1000:
                if v != voice:
                    print(f"  ℹ️  used backup voice {v}", flush=True)
                return
            last = RuntimeError("empty audio file")
        except Exception as e:  # noqa: BLE001
            last = e
        await asyncio.sleep(2 + 2 * n)
    raise RuntimeError(f"voiceover failed after {len(tries)} tries: {last}")


async def _tts_all(items, rate, out_dir):
    import edge_tts
    files = []
    for i, parts in enumerate(items):
        segs = []
        for j, (text, voice) in enumerate(parts):
            f = out_dir / f"vo_{i:02d}_{j}.mp3"
            await _say(edge_tts, text, voice, rate, f)
            segs.append(f)
        if len(segs) == 1:
            files.append(segs[0])
        else:  # join with a short pause
            out = out_dir / f"vo_{i:02d}.m4a"
            ins, fc = [], []
            for k, sg in enumerate(segs):
                ins += ["-i", str(sg)]
                fc.append(f"[{k}:a]aresample=48000,apad=pad_dur=0.6[s{k}]")
            fc.append("".join(f"[s{k}]" for k in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[o]")
            _run(["ffmpeg", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[o]", "-c:a", "aac", str(out)])
            files.append(out)
    return files


def make_voiceover(items, cfg, out_dir: Path, log=print):
    """items: list of segments; each segment is a list of (text, voice). Returns one audio file per segment."""
    if os.environ.get("NO_TTS") == "1":  # offline test mode: silent placeholders
        files = []
        for i, parts in enumerate(items):
            words = sum(len(t.split()) for t, _ in parts)
            f = out_dir / f"vo_{i:02d}.m4a"
            _run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", f"{max(2.0, words / 2.4):.2f}",
                  "-c:a", "aac", str(f)])
            files.append(f)
        return files
    try:
        return asyncio.run(_tts_all(items, cfg["reel"]["rate"], out_dir))
    except Exception as e:  # noqa: BLE001
        # never publish a silent video: stop here so the next check tries again
        raise RuntimeError(f"Voiceover failed, so no video was made this time ({e}). It will try again at the next check.")


def _music(cfg, seconds, out_dir):
    mode = cfg["reel"].get("music", "pad")
    if mode == "folder":
        tracks = sorted((ROOT / "assets" / "music").glob("*.mp3"))
        return random.choice(tracks) if tracks else None
    if mode == "pad":
        from .pad import make_pad
        return make_pad(out_dir / "pad.wav", seconds + 1, seed=random.randint(1, 99999))
    return None


def build_reel(post: dict, frames: list[Path], cfg: dict, out_dir: Path, log=print) -> Path:
    voice = cfg["reel"]["voice"]
    items = [[(post.get("hook_narration") or post["hook"], voice)]]
    items += [[(s.get("narration") or s["heading"], voice)] for s in post["slides"]]
    items.append([(post.get("cta_narration") or post["takeaway"], voice)])
    assert len(items) == len(frames), f"frames/narration mismatch {len(items)} vs {len(frames)}"

    vo = make_voiceover(items, cfg, out_dir, log)
    if any(v is None for v in vo):
        if cfg["reel"].get("music", "pad") == "none":
            raise RuntimeError("No voiceover and music is off — cannot make a good reel.")
        log("  ↪ continuing with music and on-screen text only")

    # durations per slide
    durs = []
    for i, v in enumerate(vo):
        base = _duration(v) + 0.8 if v else 4.0
        if i == 0:
            base = max(base, 3.0)
        if i == len(vo) - 1:
            base += 1.5
        durs.append(max(2.8, base))

    # 1) a gently zooming clip per slide
    clips = []
    for i, (fr, d) in enumerate(zip(frames, durs)):
        n = int(d * FPS) + 1
        clip = out_dir / f"clip_{i:02d}.mp4"
        zin = "min(zoom+0.0007,1.06)" if i % 2 == 0 else "if(eq(on,0),1.06,max(zoom-0.0007,1.0))"
        vf = (f"scale=2160:3840,zoompan=z='{zin}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={n}:s=1080x1920:fps={FPS},format=yuv420p")
        _run(["ffmpeg", "-y", "-loop", "1", "-i", str(fr), "-t", f"{d:.3f}", "-vf", vf,
              "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-r", str(FPS), str(clip)])
        clips.append(clip)

    # 2) crossfade chain + voice timeline + music
    inputs, fc = [], []
    for c in clips:
        inputs += ["-i", str(c)]
    starts, t = [], 0.0
    for i, d in enumerate(durs):
        starts.append(t)
        t += d - (XF if i < len(durs) - 1 else 0)
    total = t
    prev = "[0:v]"
    for i in range(1, len(clips)):
        out = f"[v{i}]"
        fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={XF}:offset={starts[i]:.3f}{out}")
        prev = out
    vlabel = prev

    alabels = []
    k = len(clips)
    for i, v in enumerate(vo):
        if v is None:
            continue
        inputs += ["-i", str(v)]
        ms = int((starts[i] + 0.25) * 1000)
        fc.append(f"[{k}:a]aresample=48000,adelay={ms}|{ms},apad[a{i}]")
        alabels.append(f"[a{i}]")
        k += 1
    music = _music(cfg, total, out_dir)
    if music:
        loop = ["-stream_loop", "-1"] if str(music).endswith(".mp3") else []
        inputs += [*loop, "-i", str(music)]
        vol = cfg["reel"]["music_volume"] if alabels else 0.5
        fc.append(f"[{k}:a]aresample=48000,volume={vol},afade=t=in:d=1.5,"
                  f"afade=t=out:st={max(0, total - 2.5):.2f}:d=2.5[m]")
        alabels.append("[m]")
    fc.append(f"{''.join(alabels)}amix=inputs={len(alabels)}:normalize=0:duration=longest,"
              f"atrim=0:{total:.3f},aformat=channel_layouts=stereo[aout]")

    reel = out_dir / "reel.mp4"
    _run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", vlabel, "-map", "[aout]",
          "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
          "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
          "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(reel)])
    cap = cfg["reel"].get("max_mb", 19) * 1024 * 1024
    if reel.stat().st_size > cap:  # Telegram previews must stay under 20 MB
        kbps = int(cap * 8 * 0.9 / total / 1000) - 170
        log(f"  ↘ {reel.stat().st_size/1e6:.1f} MB is too big; re-encoding at {kbps} kb/s")
        small = out_dir / "reel_small.mp4"
        _run(["ffmpeg", "-y", "-i", str(reel), "-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{kbps}k",
              "-maxrate", f"{kbps}k", "-bufsize", f"{kbps*2}k", "-pix_fmt", "yuv420p", "-c:a", "copy",
              "-movflags", "+faststart", str(small)])
        small.replace(reel)
    log(f"  🎬 Short built: {total:.1f}s, {reel.stat().st_size/1e6:.1f} MB")
    return reel
