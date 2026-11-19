"""Soft, royalty-free ambient pad generated in code (a different chord each video) — no copyright issues."""
import wave
from pathlib import Path

import numpy as np

SR = 44100
CHORDS = [  # gentle open voicings (Hz): Cmaj9, Dm9, Fmaj7, Am(add9), Gsus2
    [130.81, 196.00, 246.94, 293.66], [146.83, 220.00, 261.63, 329.63], [174.61, 220.00, 261.63, 329.63],
    [110.00, 164.81, 246.94, 261.63], [98.00, 146.83, 220.00, 293.66],
]


def make_pad(path: Path, seconds: float, seed: int = 1) -> Path:
    rng = np.random.default_rng(seed)
    chord = CHORDS[seed % len(CHORDS)]
    t = np.arange(int(SR * seconds)) / SR
    y = np.zeros_like(t)
    for f in chord:
        for det in (-0.6, 0.6):  # slight detune for warmth
            ph = rng.uniform(0, 2 * np.pi)
            y += np.sin(2 * np.pi * (f + det) * t + ph) * (0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(.03, .08) * t))
    y += 0.25 * np.sin(2 * np.pi * chord[0] / 2 * t)  # soft sub
    # slow brightness swell
    y *= 0.55 + 0.45 * np.sin(2 * np.pi * 0.05 * t + rng.uniform(0, 6)) ** 2
    fade = int(SR * 2)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.7
    st = np.stack([y, np.roll(y, int(0.015 * SR))], axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    return path
