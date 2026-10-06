#!/usr/bin/env python3
"""AI voice-over: turns an annotated narration script into expressive speech.

Uses Kokoro (an open-source neural text-to-speech model that runs offline) and
writes OUTDIR/01.wav, 02.wav, ... plus 01.json, ... with phrase timings, which
generators/nqueens.py --voice OUTDIR picks up exactly like a recorded voice.

    pip install kokoro-onnx soundfile
    python3 scripts/ai_voiceover.py projects/nqueens/clips/nqueens.script.txt projects/nqueens/voice

Script format, one line each:   07  {emphatic} Uh-oh, a dead end! | So we backtrack.
    {mood}  delivery for the whole line: warm, explain, curious, excited, emphatic
    |       phrase break: a caption boundary (and a pause if it ends a sentence)

To avoid a flat, robotic read, every sentence is synthesised on its own and
gets its own pitch: lines start brighter and settle lower like a teacher
talking, questions and exclamations lift, and each mood has its own pace,
pitch and energy. The voice is then lowered (formants preserved, so it sounds
deeper rather than slowed down) and polished: warmth, clarity, de-essing and
even loudness.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models" / "kokoro"
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL_FILES = ["kokoro-v1.0.onnx", "voices-v1.0.bin"]

# speed multiplier, pitch offset (semitones), loudness offset (dB)
MOODS = {
    "warm":     dict(speed=0.94, pitch=0.0, gain=0.0),
    "explain":  dict(speed=0.92, pitch=-0.3, gain=0.0),
    "curious":  dict(speed=0.95, pitch=0.5, gain=0.0),
    "excited":  dict(speed=1.02, pitch=1.0, gain=1.5),
    "emphatic": dict(speed=0.90, pitch=-0.2, gain=1.0),
}
PAUSE = {".": 0.38, "?": 0.5, "!": 0.42}    # silence after a sentence, by its last mark
POLISH = ("highpass=f=70,lowshelf=f=160:g=2.5,equalizer=f=2800:t=q:w=1.2:g=1.5,"
          "deesser=i=0.3,acompressor=threshold=-20dB:ratio=2.5:attack=10:release=150")
SR = 48000


def ensure_models():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        dest = MODEL_DIR / name
        if not dest.exists():
            print(f"Downloading {name} (one time, ~{'310' if name.endswith('onnx') else '27'} MB)...")
            urllib.request.urlretrieve(MODEL_URL + name, dest)
    return [str(MODEL_DIR / n) for n in MODEL_FILES]


def parse_script(path):
    """-> [(number, mood, [phrase, ...])]"""
    lines = []
    for raw in Path(path).read_text().splitlines():
        num, _, text = raw.strip().partition("  ")
        if not (num.isdigit() and text):
            continue
        m = re.match(r"\s*\{(\w+)\}\s*", text)
        mood = m.group(1) if m else "warm"
        if mood not in MOODS:
            sys.exit(f"Line {num}: unknown mood '{mood}'. Use one of: {', '.join(MOODS)}")
        phrases = [p.strip() for p in text[m.end() if m else 0:].split("|") if p.strip()]
        lines.append((num, mood, phrases))
    if not lines:
        sys.exit(f"No lines found in {path}")
    return lines


def sentences(phrases):
    """Group phrases into sentences: [(text, last_mark, [phrase indexes])]."""
    out, cur = [], []
    for i, ph in enumerate(phrases):
        cur.append(i)
        ends = re.search(r"[.!?]$", ph) and not ph.endswith("...")
        if ends or i == len(phrases) - 1:
            text = " ".join(phrases[j] for j in cur)
            out.append((text, text[-1] if text[-1] in PAUSE else ".", cur))
            cur = []
    return out


def contour(j, mark):
    """Pitch offset for sentence j: start bright, settle lower, lift on ? and !"""
    base = 0.3 if j == 0 else max(-0.75, -0.25 * j)
    return base + {"?": 0.5, "!": 0.4}.get(mark, 0.0)


def trim(y, thresh=0.01):
    loud = np.flatnonzero(np.abs(y) > thresh)
    return y[max(0, loud[0] - 240):loud[-1] + 480] if loud.size else y


def ffmpeg_filter(y, sr, chain, tmp, name):
    src, dst = Path(tmp) / f"{name}_in.wav", Path(tmp) / f"{name}_out.wav"
    sf.write(src, y, sr)
    res = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", chain,
                          "-ar", str(SR), "-ac", "1", str(dst)], capture_output=True, text=True)
    if res.returncode:
        sys.exit(f"ffmpeg failed: {res.stderr}")
    out, _ = sf.read(dst, dtype="float32")
    return out


def render_line(tts, voice, lang, mood, phrases, args, tmp, tag):
    m = MOODS[mood]
    audio, timings, clock = [], [], 0.0
    sents = sentences(phrases)
    for j, (text, mark, idxs) in enumerate(sents):
        y, sr = tts.create(text, voice=voice, speed=m["speed"] * args.speed, lang=lang)
        y = trim(np.asarray(y, dtype="float32"))
        semis = args.pitch + m["pitch"] + contour(j, mark)
        y = ffmpeg_filter(y, sr, f"rubberband=pitch={2 ** (semis / 12):.5f}:formant=preserved",
                          tmp, f"{tag}_{j}")
        dur = len(y) / SR
        # phrase timings inside the sentence, proportional to their length
        chars = sum(len(phrases[i]) for i in idxs)
        t = clock
        for i in idxs:
            d = dur * len(phrases[i]) / chars
            timings.append({"text": phrases[i], "start": round(t, 3), "end": round(t + d, 3)})
            t += d
        audio.append(y)
        clock += dur
        if j < len(sents) - 1:
            gap = np.zeros(int(PAUSE[mark] * SR), dtype="float32")
            audio.append(gap)
            clock += len(gap) / SR
    y = ffmpeg_filter(np.concatenate(audio), SR, POLISH, tmp, f"{tag}_polish")
    # even loudness across lines (speech RMS -> -20 dBFS + mood energy), no clipping
    speech = y[np.abs(y) > 0.01]
    rms = np.sqrt(np.mean(speech ** 2)) if speech.size else 1.0
    y *= 10 ** ((-20 + m["gain"]) / 20) / max(rms, 1e-6)
    y = np.clip(y, -0.97, 0.97)
    return y, timings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", help="narration script (.script.txt)")
    ap.add_argument("outdir", help="folder to write 01.wav, 01.json, ...")
    ap.add_argument("--voice", default="am_michael",
                    help="Kokoro voice: am_michael (default), am_fenrir, am_puck, bm_george, bm_fable, ... "
                         "or a blend like 'am_michael:60,am_fenrir:40'")
    ap.add_argument("--pitch", type=float, default=-1.0, help="overall pitch in semitones (default -1: deeper)")
    ap.add_argument("--speed", type=float, default=1.0, help="overall pace multiplier")
    ap.add_argument("--only", type=int, action="append", help="redo just this line number, repeatable")
    args = ap.parse_args()

    from kokoro_onnx import Kokoro
    tts = Kokoro(*ensure_models())
    if ":" in args.voice:                       # weighted blend of several voices
        parts = [v.split(":") for v in args.voice.split(",")]
        total = sum(float(w) for _, w in parts)
        voice = sum(tts.get_voice_style(v) * (float(w) / total) for v, w in parts)
        lang = "en-gb" if parts[0][0].startswith("b") else "en-us"
    else:
        voice, lang = args.voice, "en-gb" if args.voice.startswith("b") else "en-us"

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    lines = parse_script(args.script)
    if args.only:
        lines = [ln for ln in lines if int(ln[0]) in args.only]
    with tempfile.TemporaryDirectory(prefix="aivo_") as tmp:
        for num, mood, phrases in lines:
            y, timings = render_line(tts, voice, lang, mood, phrases, args, tmp, num)
            sf.write(outdir / f"{num}.wav", y, SR)
            (outdir / f"{num}.json").write_text(json.dumps({"mood": mood, "phrases": timings}, indent=1))
            print(f"[{num}] {mood:8} {len(y) / SR:4.1f}s  {' '.join(phrases)[:70]}")
    print(f"Voice-over written to {outdir}")


if __name__ == "__main__":
    main()
