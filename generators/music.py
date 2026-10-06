#!/usr/bin/env python3
"""Original background music, generated from code.

Composes and synthesises a track (chords, electric piano, pad, bass, drums
and a melody), writes it to music/ and registers it in the music catalog.
The result is your own music: free to use anywhere, no attribution, no
YouTube Content ID claims.

    python3 generators/music.py --style lofi --length 150
    python3 generators/music.py --style ambient --seed 3 --name my-ambient
    python3 generators/music.py --list

Needs numpy + soundfile (pip install numpy soundfile) and ffmpeg.
"""
import argparse
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from vedit import CATALOG, MUSIC_DIR, load_json, probe_duration, save_json  # noqa: E402

SR = 44100
PENTATONIC = [72, 74, 76, 79, 81, 84]          # C major pentatonic: fits every chord below

# chord = (bass root, voicing) as MIDI note numbers
STYLES = {
    "lofi": dict(
        description="Lo-fi study beat: jazzy chords, soft swung drums, vinyl crackle",
        moods=["focus", "calm", "study", "lofi"], bpm=78, swing=0.14, bars_per_chord=1,
        chords=[(38, [53, 57, 60, 64]),           # Dm9
                (43, [53, 59, 64]),               # G13
                (36, [52, 55, 59, 62]),           # Cmaj9
                (45, [55, 60, 64, 67])],          # Am9
        final=(36, [52, 55, 59, 62, 67]),
        keys=[(0, 6), (10, 6)], drums="lofi", melody="half", lowpass=6500, crackle=True),
    "ambient": dict(
        description="Ambient: slow warm pads and soft bells, no drums",
        moods=["calm", "ambient", "focus", "thoughtful"], bpm=64, swing=0.0, bars_per_chord=2,
        chords=[(41, [57, 60, 64, 67]),           # Fmaj7 (add 9 feel)
                (45, [55, 60, 64, 67]),           # Am7
                (36, [55, 59, 62, 64]),           # Cmaj9
                (43, [55, 59, 62, 64])],          # G6
        final=(41, [53, 57, 60, 64, 67]),
        keys=[(0, 28)], drums=None, melody="bells", lowpass=7000, crackle=False,
        levels={"keys": -27, "pad": -24, "melody": -27}),
    "upbeat": dict(
        description="Upbeat: bright piano stabs, four-on-the-floor drums, catchy melody",
        moods=["upbeat", "happy", "energetic", "intro"], bpm=104, swing=0.0, bars_per_chord=1,
        chords=[(36, [55, 60, 64, 62]),           # C(add9)
                (43, [55, 59, 62, 69]),           # G6
                (45, [57, 60, 64, 71]),           # Am(add9)
                (41, [57, 60, 65, 67])],          # F(add9)
        final=(36, [55, 60, 64, 67, 72]),
        keys=[(0, 2), (3, 2), (6, 3), (10, 2), (12, 3)], drums="four", melody="full",
        lowpass=12000, crackle=False),
}

# target loudness of each part (dBFS RMS) - the mix is balanced by these, not by synth levels
LEVELS = {"keys": -21, "pad": -27, "bass": -22, "kick": -21, "snare": -27, "hats": -33,
          "melody": -24, "crackle": -42}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def t_axis(seconds):
    return np.arange(int(seconds * SR)) / SR


# ---------------------------------------------------------------- instruments

def epiano(f, dur, vel=1.0):
    """FM electric piano (Rhodes-like): bright attack that mellows as it decays."""
    t = t_axis(dur + 1.2)
    index = 1.4 * np.exp(-t * 5) + 0.12
    y = np.sin(2 * np.pi * f * t + index * np.sin(2 * np.pi * f * t)) * np.exp(-t * 1.4)
    y += 0.2 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 3.5)
    y *= np.minimum(1, t / 0.004) * np.where(t > dur, np.exp(-(t - dur) * 7), 1)
    return vel * y


def bell(f, dur, vel=1.0):
    t = t_axis(dur + 2.5)
    y = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 3)
    return vel * y * np.exp(-t * 1.1) * np.minimum(1, t / 0.006)


def pad(freqs, dur, rng):
    """Detuned additive saw voices with a slow swell."""
    t = t_axis(dur + 3.0)
    y = np.zeros_like(t)
    for f in freqs:
        for cents in (-8, 0, 8):
            fv = f * 2 ** (cents / 1200)
            for k in range(1, 7):
                y += np.sin(2 * np.pi * fv * k * t + rng.uniform(0, 2 * np.pi)) / k
    env = np.minimum(1, t / 0.8) * np.where(t > dur, np.exp(-(t - dur) * 1.3), 1)
    return y * env


def bass(f, dur, vel=1.0):
    t = t_axis(dur + 0.15)
    y = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    env = np.minimum(1, t / 0.01) * (0.6 + 0.4 * np.exp(-t * 6))
    return vel * y * env * np.where(t > dur, np.exp(-(t - dur) * 40), 1)


def kick(vel=1.0):
    t = t_axis(0.5)
    phase = 2 * np.pi * np.cumsum(45 + 85 * np.exp(-t * 30)) / SR
    return vel * np.sin(phase) * np.exp(-t * 7)


def snare(rng, vel=1.0):
    t = t_axis(0.25)
    noise = band(rng.standard_normal(len(t)), 900, 5000)
    return vel * (noise * np.exp(-t * 24) + 0.5 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30))


def hat(rng, vel=1.0):
    t = t_axis(0.08)
    return vel * band(rng.standard_normal(len(t)), 7000, 16000) * np.exp(-t * 70)


# ---------------------------------------------------------------- dsp helpers

def band(y, lo=None, hi=None):
    """Zero-phase filter in the frequency domain (smooth 4th-order style slopes)."""
    n = fast_len(len(y))
    spec = np.fft.rfft(y, n)
    f = np.fft.rfftfreq(n, 1 / SR)
    if hi:
        spec /= 1 + (f / hi) ** 4
    if lo:
        spec *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    return np.fft.irfft(spec, n)[:len(y)]


def fast_len(n):
    """FFT is far faster on power-of-two sizes than on awkward lengths."""
    return 1 << (n - 1).bit_length()


def reverb(y, rng, seconds=2.2):
    t = t_axis(seconds)
    ir = rng.standard_normal(len(t)) * np.exp(-t * 3.2)
    ir = band(ir, 200, 6000)
    n = fast_len(len(y) + len(ir))
    out = np.fft.irfft(np.fft.rfft(y, n) * np.fft.rfft(ir, n), n)[:len(y)]
    return out / (np.abs(out).max() + 1e-9)


def place(track, y, start):
    i = int(start * SR)
    if i >= len(track):
        return
    seg = y[:len(track) - i]
    track[i:i + len(seg)] += seg


def set_level(y, db):
    active = y[np.abs(y) > 1e-4]
    rms = np.sqrt(np.mean(active ** 2)) if active.size else 1.0
    return y * (10 ** (db / 20) / max(rms, 1e-9))


# ---------------------------------------------------------------- composition

def melody_line(chord, rng, density):
    """Pentatonic phrase for one bar: [(step, length_in_steps, midi)]."""
    patterns = [[0, 3, 6, 8], [0, 4, 10], [2, 6, 8, 12], [0, 6, 8, 11], [0, 8, 12]]
    if density == "full":
        patterns += [[0, 2, 4, 6, 8, 12], [0, 3, 6, 10, 12, 14]]
    steps = patterns[rng.integers(len(patterns))]
    pcs = {n % 12 for n in chord[1]} | {chord[0] % 12}
    tones = [n for n in PENTATONIC if n % 12 in pcs] or PENTATONIC
    note = tones[rng.integers(len(tones))]
    out = []
    for j, s in enumerate(steps):
        length = (steps[j + 1] if j + 1 < len(steps) else 16) - s
        out.append((s, length, note))
        i = PENTATONIC.index(note) + rng.choice([-2, -1, -1, 1, 1, 2])
        note = PENTATONIC[min(max(i, 0), len(PENTATONIC) - 1)]
        if s + length >= 8 and s < 8:           # land on a chord tone on the strong beat
            note = min(tones, key=lambda n: abs(n - note))
    return out


def compose(style, length, seed):
    st, rng = STYLES[style], np.random.default_rng(seed)
    beat = 60 / st["bpm"]
    bar, step = 4 * beat, beat / 4
    cycle = len(st["chords"]) * st["bars_per_chord"]
    n_bars = max(cycle, math.ceil(length / bar / cycle) * cycle)   # whole progressions
    total = (n_bars + 1) * bar + 3                                   # + final chord + tail
    parts = {k: np.zeros(int(total * SR)) for k in LEVELS}
    pad_cache = {}                                  # repeated chords reuse their (slow) pad

    def swung(s):
        return s * step + (st["swing"] * step if s % 2 else 0)

    for b in range(n_bars + 1):
        last = b == n_bars
        chord = st["final"] if last else st["chords"][(b // st["bars_per_chord"]) % len(st["chords"])]
        t0 = b * bar
        intro = b < 2
        breakdown = b % 16 in (14, 15) or b >= n_bars - 1
        if b % st["bars_per_chord"] == 0 or last:          # pad + bass follow the chord changes
            dur = bar * (2 if last else st["bars_per_chord"])
            key = (tuple(chord[1]), dur)
            if key not in pad_cache:
                pad_cache[key] = pad([hz(n) for n in chord[1]], dur, rng)
            # start the swell a little early so chords cross-fade instead of dipping
            place(parts["pad"], pad_cache[key], max(0.0, t0 - 0.4))
            if not intro:
                place(parts["bass"], bass(hz(chord[0]), dur), t0)
        hits = [(0, 16)] if last else st["keys"]
        if style == "ambient" and b % 2:
            hits = []
        for s, length in hits:
            for j, n in enumerate(sorted(chord[1])):       # gentle strum, low to high
                strum = j * (0.06 if style == "ambient" else 0.012)
                place(parts["keys"], epiano(hz(n), length * step, rng.uniform(0.7, 1.0)),
                      t0 + swung(s) + strum)
        if st["drums"] and not intro and not breakdown:
            pattern = {"lofi": ([0, 10] + ([7] if b % 2 else []), [4, 12], range(0, 16, 2)),
                       "four": ([0, 4, 8, 12], [4, 12], range(2, 16, 4))}[st["drums"]]
            for s in pattern[0]:
                place(parts["kick"], kick(rng.uniform(0.85, 1.0)), t0 + swung(s))
            for s in pattern[1]:
                place(parts["snare"], snare(rng, rng.uniform(0.8, 1.0)), t0 + swung(s))
            for s in pattern[2]:
                place(parts["hats"], hat(rng, rng.uniform(0.5, 1.0)), t0 + swung(s))
            if st["drums"] == "four":
                for s in range(1, 16, 2):
                    place(parts["hats"], hat(rng, 0.35), t0 + swung(s))
        play_melody = {"half": b >= 4 and (b // 4) % 2 == 1,
                       "full": b >= 4 and b % 8 != 7,
                       "bells": b >= 4 and b % 2 == 0}[st["melody"]]
        if play_melody and not last and b < n_bars - 1:
            instrument = bell if st["melody"] == "bells" else epiano
            line = melody_line(chord, rng, st["melody"])
            if st["melody"] == "bells":
                line = line[:2]
            for s, ln, n in line:
                place(parts["melody"], instrument(hz(n), ln * step * 0.9, rng.uniform(0.6, 0.9)),
                      t0 + swung(s))

    if st["crackle"]:
        c = np.zeros_like(parts["crackle"])
        pops = rng.integers(0, len(c) - 200, int(total * 9))
        c[pops] = rng.standard_normal(len(pops)) * rng.uniform(0.2, 1.0, len(pops))
        parts["crackle"] = band(c, 1500, 9000) + band(rng.standard_normal(len(c)), 300, 5000) * 0.02

    parts["pad"] = band(parts["pad"], 120, 1600)
    parts["bass"] = band(parts["bass"], None, 700)
    levels = {**LEVELS, **st.get("levels", {})}
    return {k: set_level(v, levels[k]) for k, v in parts.items() if np.abs(v).max() > 0}, rng


def mixdown(parts, style, rng):
    st = STYLES[style]
    pan = {"hats": 0.3, "melody": -0.2, "crackle": 0.0}
    left = sum(v * (1 - max(0, pan.get(k, 0))) for k, v in parts.items())
    right = sum(v * (1 + min(0, pan.get(k, 0))) for k, v in parts.items())
    send = parts.get("keys", 0) + parts.get("pad", 0) + parts.get("melody", 0)
    wet = 0.22 if style != "ambient" else 0.35
    send_level = np.sqrt(np.mean(send ** 2)) * wet
    left = left + reverb(send, rng) * send_level * 3
    right = right + reverb(send, rng) * send_level * 3
    stereo = np.stack([band(left, 30, st["lowpass"]), band(right, 30, st["lowpass"])], axis=1)
    return stereo / (np.abs(stereo).max() + 1e-9) * 0.89


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--style", choices=STYLES, default="lofi")
    ap.add_argument("--length", type=float, default=150, help="seconds (vedit loops it if the video is longer)")
    ap.add_argument("--seed", type=int, default=1, help="change for a different melody / variation")
    ap.add_argument("--name", help="file name without extension (default generated-<style>)")
    ap.add_argument("--list", action="store_true", help="show the styles")
    args = ap.parse_args()
    if args.list:
        for name, st in STYLES.items():
            print(f"{name:8} {st['bpm']:>3} bpm  moods: {', '.join(st['moods']):34} {st['description']}")
        return

    name = args.name or f"generated-{args.style}"
    print(f"Composing {args.style} ({args.length:.0f}s, seed {args.seed})...")
    parts, rng = compose(args.style, args.length, args.seed)
    audio = mixdown(parts, args.style, rng)
    MUSIC_DIR.mkdir(exist_ok=True)
    dest = MUSIC_DIR / f"{name}.mp3"
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "mix.wav"
        sf.write(wav, audio.astype("float32"), SR)
        res = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                              "-af", "afade=t=out:st={:.2f}:d=3,loudnorm=I=-16:TP=-1.5:LRA=11".format(
                                  len(audio) / SR - 3),
                              "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "160k", str(dest)],
                             capture_output=True, text=True)
        if res.returncode:
            sys.exit(res.stderr)

    st = STYLES[args.style]
    catalog = [t for t in load_json(CATALOG, []) if t["file"] != dest.name]
    catalog.append({"file": dest.name, "title": f"{args.style.title()} (generated, seed {args.seed})",
                    "artist": "vedit music generator", "source": "generated", "url": "",
                    "license": "Original music generated by vedit - free to use, no attribution needed",
                    "moods": st["moods"], "duration": round(probe_duration(dest), 1)})
    save_json(CATALOG, catalog)
    print(f"Wrote {dest} and added it to the catalog (moods: {', '.join(st['moods'])})")


if __name__ == "__main__":
    main()
