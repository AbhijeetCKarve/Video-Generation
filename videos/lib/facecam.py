"""Face-cam track: your camera recording, cut to follow the narration line by line.

The real-voice lines (voice-real/NN.wav) were cut from the same recording as the
camera video, so every phrase can be found again in the recording's audio. For each
moment the narration plays we show the frames recorded while you said those words
(lip-sync is exact); while the narration pauses (animations, section gaps) we show
you listening: the silent footage after the phrase, played back and forth when the
pause is longer than what was recorded. Cuts get a short cross-fade.

    track(sched, voice_dir, camera, out, start) -> square face clip from `start` to the end
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from clone_voiceover import load, speech_segments  # noqa: E402

FPS = 30
SIZE = 250                     # face circle diameter on screen, pixels (scene ring radius 0.926 units)
CROP = "crop=780:780:575:58"   # head-and-shoulders square inside the recording window
LOOK = "eq=contrast=1.18:brightness=-0.03:saturation=1.3:gamma=0.92,unsharp=5:5:0.6"   # dim webcam -> clearer
AR = 8000                      # audio rate for matching
XFADE = 3                      # frames of cross-fade at a cut


def _find(needle, hay, lo, hi):
    """Best offset of `needle` inside hay[lo:hi] (samples) and its normalized correlation."""
    lo, hi = max(0, lo), min(len(hay), hi)
    seg = hay[lo:hi]
    if len(seg) < len(needle):
        return None, 0.0
    c = fftconvolve(seg, needle[::-1], mode="valid")
    energy = np.sqrt(np.maximum(fftconvolve(seg ** 2, np.ones(len(needle)), mode="valid"), 1e-12))
    score = c / (energy * np.linalg.norm(needle) + 1e-12)
    i = int(np.argmax(score))
    return lo + i, float(score[i])


def line_pieces(raw_wav, line_wav, source, prev_end):
    """Where each phrase of one line came from: [(line_t0, line_t1, source_t0)] in seconds.
    raw = your phrases joined with 0.25 s of digital silence; line = raw after clean-up and edge trim."""
    raw, sr = sf.read(raw_wav, dtype="float32")
    quiet = np.abs(raw) < 1e-4
    d = np.diff(np.r_[0, quiet.astype(int), 0])
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    gaps = [(a, b) for a, b in zip(starts, ends) if b - a > 0.2 * sr]
    bounds = [0] + [x for g in gaps for x in g] + [len(raw)]
    pieces = [(bounds[i], bounds[i + 1]) for i in range(0, len(bounds), 2)]
    step = sr // AR
    raw8 = raw[::step]
    out = []
    for a, b in pieces:
        needle = raw8[a // step:b // step]
        pos, score = _find(needle, source, int((prev_end - 2) * AR), int((prev_end + 120) * AR))
        if score < 0.8:                                    # not where expected: search everything
            pos, score = _find(needle, source, 0, len(source))
        if score < 0.5:
            raise RuntimeError(f"{Path(raw_wav).name}: phrase not found in the camera audio (match {score:.2f})")
        out.append([a / sr, b / sr, pos / AR])
        prev_end = (pos + len(needle)) / AR
    line, lsr = sf.read(line_wav, dtype="float32")
    lead, _ = _find(line[::lsr // AR][:int(1.5 * AR)], raw8, 0, int(2.5 * AR))   # trimmed start of the clean line
    lead = (lead or 0) / AR
    return [(a - lead, b - lead, s) for a, b, s in out], prev_end


def frame_map(sched, voice_dir, source, talk, start, total):
    """Source time for every output frame from `start` to `total` (np.nan = keep previous)."""
    spoken, prev_end = [], 0.0
    for b in sched["beats"]:
        num = b["num"]
        pieces, prev_end = line_pieces(Path(voice_dir) / "raw" / f"{num}.wav", Path(voice_dir) / f"{num}.wav",
                                       source, prev_end)
        for i, (a, e, s) in enumerate(pieces):
            a = max(a, 0.0)
            e = min(e, b["dur"]) if i == len(pieces) - 1 else e
            spoken.append((b["start"] + a, b["start"] + e, s + (a - pieces[i][0])))
    talk = np.array(talk)
    end = len(source) / AR
    idle = [(e1 + 0.1, s2 - 0.1) for (_, e1), (s2, _) in zip(talk, talk[1:]) if s2 - e1 > 0.9]
    idle += [(0.0, talk[0, 0] - 0.1), (talk[-1, 1] + 0.4, end - 0.1)]    # before you start, after you finish

    def next_talk(p):
        later = talk[talk[:, 0] > p + 0.05]
        return later[0, 0] - 0.1 if len(later) else len(source) / AR - 0.1

    def pingpong(a, e, n):
        span = max(e - a, 1.0 / FPS)
        x = np.arange(n) / FPS
        tri = np.abs(((x / span) + 1) % 2 - 1)            # 1 -> 0 -> 1 ...
        return a + span * (1 - tri)

    n_out = int(round((total - start) * FPS))
    src = np.full(n_out, np.nan)
    times = start + np.arange(n_out) / FPS
    for oa, ob, s in spoken:
        k = (times >= oa) & (times < ob)
        src[k] = s + (times[k] - oa)
    # pauses: carry on from where the last phrase ended
    k = 0
    while k < n_out:
        if not np.isnan(src[k]):
            k += 1
            continue
        j = k
        while j < n_out and np.isnan(src[j]):
            j += 1
        n = j - k
        if k:
            p = src[k - 1] + 1.0 / FPS
        else:                                              # before the first phrase: silence leading into it
            p = max(0.0, src[j] - n / FPS) if j < n_out else 0.0
        need, room = n / FPS, next_talk(p) - p
        if room >= need:
            src[k:j] = p + np.arange(n) / FPS
        elif room >= min(need, 2.0):                       # short pause: rock gently in your own silence
            src[k:j] = pingpong(p, p + room, n)
        else:                                              # long pause: a nearby stretch of you sitting quietly
            fits = [r for r in idle if r[1] - r[0] >= min(need, 3.0)] or [max(idle, key=lambda r: r[1] - r[0])]
            a, e = min(fits, key=lambda r: abs(r[0] - p))
            src[k:j] = pingpong(a, e, n)
        k = j
    return src


def track(sched, voice_dir, camera, out, start):
    out = Path(out)
    work = out.parent
    audio = load(camera, AR)
    talk = speech_segments(load(camera, 16000), 16000)
    src = frame_map(sched, voice_dir, audio, talk, start, sched["total"])
    np.save(work / "face-map.npy", src)
    frames = work / "face-frames.rgb"
    if not frames.exists() or frames.stat().st_mtime < Path(camera).stat().st_mtime:
        print("Face cam: decoding the camera recording")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(camera), "-vf",
                        f"{CROP},scale={SIZE}:{SIZE}:flags=lanczos,{LOOK}", "-pix_fmt", "rgb24", "-f", "rawvideo",
                        str(frames)], check=True)
    cam = np.memmap(frames, dtype="uint8", mode="r").reshape(-1, SIZE, SIZE, 3)
    idx = np.clip(np.round(src * FPS).astype(int), 0, len(cam) - 1)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{SIZE}x{SIZE}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12",
                            "-preset", "medium", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    cuts = 0
    blend_from, blend_left = None, 0
    for i, f in enumerate(idx):
        frame = cam[f].astype("float32")
        if i and abs(int(f) - int(idx[i - 1])) > 1 and blend_left == 0:     # a cut: fade over a few frames
            blend_from, blend_left = int(idx[i - 1]), XFADE
            cuts += 1
        if blend_left:
            w = (XFADE - blend_left + 1) / (XFADE + 1)
            blend_from = min(blend_from + 1, len(cam) - 1)
            frame = (1 - w) * cam[blend_from].astype("float32") + w * frame
            blend_left -= 1
        enc.stdin.write(frame.astype("uint8").tobytes())
    enc.stdin.close()
    enc.wait()
    (work / "face.json").write_text(json.dumps({"start": start, "frames": len(idx), "cuts": cuts}))
    print(f"Face cam: {len(idx) / FPS:.0f}s, {cuts} cuts -> {out}")
    return out
