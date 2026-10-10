"""Shared production pipeline for the DAA series (one video = beats.py + scene.py).

    schedule  timeline from the narration lines (or estimates while the voice is not ready)
    narration narration track + lip-sync envelope for the mascot
    render    Manim render of scene.py driven by the schedule
    mix       narration + sound effects + context music (very low, ducked) -> final video
              with burned captions and the thumbnail embedded as cover art
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import vedit  # noqa: E402

SR = 48000
FPS = 30
INTRO = 3.2          # seconds the thumbnail is shown before the narration starts
GAP = 0.55           # pause between lines
SECTION_GAP = 1.0    # longer pause when the section changes
END_CARD = 5.0

# music style per section mood, and how loud (dB) it sits relative to the base music level
MUSIC = {"bright": ("generated-upbeat.mp3", 0), "calm": ("generated-ambient.mp3", 0),
         "pulse": ("generated-lofi.mp3", 0), "quiet": ("generated-ambient.mp3", -7)}
MUSIC_BASE_DB = -27  # music file (-16 LUFS) -> about 26-28 dB under the narration
SFX_DB = {"place": -25, "kill": -29, "back": -27, "chime": -22, "pop": -30, "whoosh": -31}
FACE_POS = (-6.07, -1.05)   # face-cam circle centre in scene units (scene.py FACE_POS)


def phrases_of(text):
    return [p.strip() for p in text.split("|") if p.strip()]


# ---------------------------------------------------------------- schedule
def schedule(beats, sections, min_window, voice_dir, out, estimate=False, meta=None):
    """beats: [(key, mood, text)], sections: {key: (title, music)} at the first beat of each section."""
    t = INTRO + 0.4
    rows = []
    for i, (key, mood, text) in enumerate(beats):
        num = f"{i + 1:02d}"
        if key in sections and rows:
            t += SECTION_GAP - GAP
        if estimate:
            words = len(text.replace("|", " ").split())
            dur = words / 2.45
            ph = phrases_of(text)
            chars = sum(len(p) for p in ph)
            acc, timings = 0.0, []
            for p in ph:
                timings.append({"text": p, "start": acc, "end": acc + dur * len(p) / chars})
                acc += dur * len(p) / chars
            wav = None
        else:
            wav = Path(voice_dir) / f"{num}.wav"
            info = sf.info(wav)
            dur = info.frames / info.samplerate
            timings = json.loads((Path(voice_dir) / f"{num}.json").read_text())["phrases"]
        window = max(dur + GAP, min_window.get(key, 0))
        rows.append({"key": key, "num": num, "mood": mood, "start": round(t, 3), "voice": str(wav) if wav else None,
                     "dur": round(dur, 3), "end": round(t + window, 3),
                     "section": sections.get(key, (None, None))[0], "music": sections.get(key, (None, None))[1],
                     "phrases": [{"text": p["text"], "start": round(t + p["start"], 3), "end": round(t + p["end"], 3)}
                                 for p in timings]})
        t += window
    end_card = t + 0.3
    data = {**(meta or {}), "intro": INTRO, "beats": rows, "end_card": round(end_card, 3),
            "total": round(end_card + (meta or {}).get("end_secs", END_CARD), 3)}   # end_secs: room for YouTube's end screen
    Path(out).write_text(json.dumps(data, indent=1))
    print(f"Schedule: {len(rows)} beats, {data['total'] / 60:.1f} min" + (" (ESTIMATED)" if estimate else ""))
    return data


# ---------------------------------------------------------------- narration + envelope
def narration(sched, out_wav, out_env):
    total = int(sched["total"] * SR) + SR
    track = np.zeros(total, dtype="float32")
    for b in sched["beats"]:
        if not b["voice"]:
            continue
        y, sr = sf.read(b["voice"], dtype="float32")
        if y.ndim > 1:
            y = y.mean(1)
        if sr != SR:
            y = np.interp(np.arange(int(len(y) * SR / sr)) * sr / SR, np.arange(len(y)), y).astype("float32")
        i = int(b["start"] * SR)
        track[i:i + len(y)] += y[:total - i]
    sf.write(out_wav, track, SR)
    hop = SR // FPS
    frames = track[:len(track) // hop * hop].reshape(-1, hop)
    rms = np.sqrt((frames ** 2).mean(1))
    ref = np.percentile(rms[rms > 1e-4], 95) if (rms > 1e-4).any() else 1.0
    env = np.clip(rms / ref, 0, 1)
    env = np.convolve(env, [0.25, 0.5, 0.25], mode="same")      # a little smoothing for the mouth
    np.save(out_env, env.astype("float32"))
    return track


# ---------------------------------------------------------------- sound effects
def _tone(f0, f1, dur, decay, sr=SR):
    t = np.arange(int(dur * sr)) / sr
    f = np.linspace(f0, f1, len(t))
    return np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * decay)


def _layer(*parts):
    """Sum (offset_seconds, signal) parts of different lengths."""
    n = max(int(o * SR) + len(x) for o, x in parts)
    y = np.zeros(n)
    for o, x in parts:
        y[int(o * SR):int(o * SR) + len(x)] += x
    return y


def sfx_sample(kind):
    if kind == "place":
        y = _layer((0, _tone(1100, 650, 0.09, 45)), (0, 0.3 * _tone(2200, 1300, 0.05, 80)))
    elif kind == "kill":
        y = _tone(220, 150, 0.16, 28)
    elif kind == "back":
        y = _tone(760, 320, 0.26, 12)
    elif kind == "chime":
        y = _layer((0, _tone(1046.5, 1046.5, 0.9, 5)), (0.09, 0.7 * _tone(1318.5, 1318.5, 0.8, 5)))   # C6 then E6
    elif kind == "pop":
        y = _tone(1500, 1200, 0.05, 70)
    else:                                                        # whoosh: soft filtered noise swell
        n = int(0.32 * SR)
        noise = np.random.default_rng(1).standard_normal(n)
        noise = np.convolve(noise, np.ones(40) / 40, mode="same")
        y = noise * np.sin(np.linspace(0, np.pi, n)) * 2
    y = y.astype("float32")
    return y / (np.abs(y).max() + 1e-9)


def sfx_track(events, total_s):
    track = np.zeros(int(total_s * SR) + SR, dtype="float32")
    cache = {}
    for t, kind in events:
        if kind not in cache:
            cache[kind] = sfx_sample(kind) * 10 ** (SFX_DB.get(kind, -30) / 20) * 1.4
        y, i = cache[kind], int(t * SR)
        track[i:i + len(y)] += y[:len(track) - i]
    return track


# ---------------------------------------------------------------- music bed by section
def music_bed(sched, tmp):
    """Each section gets the music style its content calls for, cross-faded at the boundaries."""
    starts = [(b["start"] - (0.6 if i else b["start"]), b["music"]) for i, b in enumerate(sched["beats"]) if b["music"]]
    starts[0] = (0.0, starts[0][1])
    bounds = starts + [(sched["total"], None)]
    total = int(sched["total"] * SR) + SR
    bed = np.zeros(total, dtype="float32")
    fade = int(1.5 * SR)
    loaded = {}
    for (t0, mood), (t1, _) in zip(bounds, bounds[1:]):
        name, gain = MUSIC[mood]
        if name not in loaded:
            wav = Path(tmp) / (name + ".wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(ROOT / "music" / name), "-ac", "1",
                            "-ar", str(SR), str(wav)], check=True)
            loaded[name] = sf.read(wav, dtype="float32")[0]
        src = loaded[name]
        a, b = int(t0 * SR), min(total, int(t1 * SR) + fade)
        n = b - a
        idx = (np.arange(n) + a) % len(src)                     # keep each style's own timeline
        seg = src[idx] * 10 ** ((MUSIC_BASE_DB + gain) / 20)
        ramp = min(fade, n // 2)
        seg[:ramp] *= np.linspace(0, 1, ramp)
        seg[-ramp:] *= np.linspace(1, 0, ramp)
        bed[a:b] += seg
    end = int(sched["total"] * SR)
    bed[end - 2 * SR:end] *= np.linspace(1, 0, 2 * SR)
    return bed


# ---------------------------------------------------------------- captions
def srt(sched, out):
    def ts(s):
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    caps = []
    for b in sched["beats"]:
        ph = b["phrases"]
        for j, p in enumerate(ph):
            end = ph[j + 1]["start"] if j + 1 < len(ph) else p["end"] + 0.4
            caps.append((p["start"], end, p["text"]))
    Path(out).write_text("\n".join(f"{i + 1}\n{ts(a)} --> {ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(caps)))


# ---------------------------------------------------------------- render + mix
def render(scene_py, sched_path, env_path, sfx_log, media_dir, quality="h"):
    env = {**os.environ, "SCHEDULE": str(sched_path), "ENVELOPE": str(env_path), "SFX_LOG": str(sfx_log)}
    q = {"l": ["-ql", "--fps", "15"], "m": ["-qm", "--fps", "30"], "h": ["-qh", "--fps", "30", "-r", "1920,1080"]}[quality]
    cmd = ["manim", *q, "--media_dir", str(media_dir), "--disable_caching", str(scene_py), "Video"]
    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if res.returncode:
        sys.exit(res.stdout[-4000:] + res.stderr[-4000:])
    for line in res.stdout.splitlines():
        if "OVERRUN" in line:
            print(line)
    found = sorted(Path(media_dir).rglob("Video.mp4"), key=lambda p: p.stat().st_mtime)
    return found[-1]


def face_layer(faces, tmp):
    """FFmpeg inputs + filter laying each face clip, cut to a circle, over the scene while it is on.
    faces: [{"clip", "start", "end", "pos": (x, y) in scene units}]."""
    from PIL import Image
    px = 1920 / 14.2222                                         # pixels per scene unit at 1080p
    inputs, graph, masks, base = [], "", {}, "[0:v]"
    for i, f in enumerate(faces):
        size = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width",
                                   "-of", "csv=p=0", str(f["clip"])], capture_output=True, text=True).stdout)
        if size not in masks:                                   # soft-edged circle, one per clip size
            y, x = np.mgrid[:size, :size] + 0.5
            r = np.hypot(x - size / 2, y - size / 2)
            masks[size] = tmp / f"face-mask-{size}.png"
            Image.fromarray((np.clip(size / 2 - 1 - r + 0.5, 0, 1) * 255).astype("uint8"), "L").save(masks[size])
        cx, cy = 960 + f["pos"][0] * px, 540 - f["pos"][1] * px
        vi, mi = 4 + 2 * i, 5 + 2 * i                           # inputs 0-3 are the scene, voice and music
        inputs += ["-i", f["clip"], "-loop", "1", "-i", masks[size]]
        dur = f["end"] - f["start"]
        graph += (f"[{vi}:v]format=rgba[fc{i}];[{mi}:v]format=gray[mk{i}];[fc{i}][mk{i}]alphamerge,"
                  f"fade=t=in:st=0:d=0.4:alpha=1,fade=t=out:st={dur - 0.4:.3f}:d=0.4:alpha=1,"
                  f"setpts=PTS-STARTPTS+{f['start']:.3f}/TB[face{i}];"
                  f"{base}[face{i}]overlay={cx - size / 2:.0f}:{cy - size / 2:.0f}:eof_action=pass"
                  f":enable='between(t,{f['start']:.3f},{f['end']:.3f})'[ov{i}];")
        base = f"[ov{i}]"
    return inputs, graph.replace(base, "[base]") if faces else (inputs, graph)


def mix(sched, video, narr_wav, sfx_log, srt_path, thumbnail, out, theme="clean", faces=None):
    tmp = Path(out).parent / ("tmp-" + Path(out).stem)
    tmp.mkdir(exist_ok=True)
    voice, _ = sf.read(narr_wav, dtype="float32")
    events = json.loads(Path(sfx_log).read_text()) if Path(sfx_log).exists() else []
    fx = sfx_track(events, sched["total"])
    bed = music_bed(sched, tmp)
    n = min(len(voice), len(fx), len(bed))
    sf.write(tmp / "voice.wav", voice[:n], SR)
    sf.write(tmp / "fxmusic.wav", (fx[:n] + bed[:n]).astype("float32"), SR)
    # duck the music+effects bed further under the voice, then level the whole mix for YouTube
    graph = ("[2:a]asplit=2[v][key];[3:a][key]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=500[bed];"
             "[v][bed]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    t = vedit.load_theme(theme)
    c = t["captions"]
    style = (f"Fontname={c.get('font', t['font'])},FontSize={c['size']},PrimaryColour={vedit.ass_color(c['color'])},"
             f"OutlineColour={vedit.ass_color(c['outline'])},BorderStyle=1,Outline=2,Shadow=0,MarginV=22")
    subs = tmp / "captions.srt"
    subs.write_text(Path(srt_path).read_text())
    face_in, face_graph, base = [], "", "[0:v]"
    if faces:                                                   # your camera, in a circle
        face_in, face_graph = face_layer(faces, tmp)
        base = "[base]"
    vedit.run(["ffmpeg", "-y", "-i", video, "-i", video, "-i", tmp / "voice.wav", "-i", tmp / "fxmusic.wav", *face_in,
               "-filter_complex", graph + ";" + face_graph + f"{base}subtitles=filename='{subs}':force_style='{style}'[vout]",
               "-map", "[vout]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", out])
    vedit.embed_cover(Path(out), Path(thumbnail), False)
    return out


def youtube_description(sched, meta, out):
    """Title, description with chapters (from the real section start times), hashtags and tags."""
    chapters = [(0.0, "Intro")]
    for b in sched["beats"]:
        if b["section"]:
            title = b["section"].replace(" \u00b7 ", ": ")
            if b["start"] - 0.6 - chapters[-1][0] >= 10:          # YouTube needs 10 s per chapter
                chapters.append((b["start"] - 0.6, title))
            else:                                                 # too short: keep its name, merged
                t0, prev = chapters[-1]
                chapters[-1] = (t0, f"{prev} & {title}" if t0 > 0 else prev)
    lines = [f"{int(t // 60)}:{int(t % 60):02d} {name}" for t, name in chapters]
    text = f"""TITLE
{meta['title']} | DAA Unit {meta['unit']} ({meta['code']}) | {meta.get('title_suffix', 'Backtracking Explained')}

DESCRIPTION
{meta.get('summary', '')}

Chapters
{chr(10).join(lines)}

Course: Design and Analysis of Algorithms (ETCS329), Unit {meta['unit']}
Created by Abhijeet Karve

Music: original background music (generated, royalty-free).

{meta.get('hashtags', '')}

TAGS
{meta.get('tags', '')}
"""
    Path(out).write_text(text)


def cameo_voice(p, spec):
    """voice-cameo/: the cloned lines, with the beats named in spec["lines"] replaced by your real
    recording of the same line from another video (wav + caption timings)."""
    import shutil
    src, dst, real = p / "voice", p / "voice-cameo", ROOT / spec["real"]
    dst.mkdir(exist_ok=True)
    for f in src.glob("[0-9]*.*"):
        shutil.copy(f, dst / f.name)
    for num, real_num in spec["lines"].items():
        for ext in ("wav", "json"):
            shutil.copy(real / f"{real_num}.{ext}", dst / f"{num}.{ext}")
    return dst


def cameo_shots(sched, spec):
    """When each cameo is on screen: [{"kind", "start", "end", "pos", "num"?, "line_start"?}]."""
    beats = sched["beats"]
    at = {b["key"]: i for i, b in enumerate(beats)}
    shots = []
    for shot in spec["shots"]:
        kind, pos = shot["kind"], shot["pos"]
        if kind == "end":
            shots.append({"beat": "end", "kind": "quiet", "start": sched["end_card"] + 0.3, "end": sched["total"],
                          "pos": pos})
            continue
        b = beats[at[shot["beat"]]]
        nxt = beats[at[shot["beat"]] + 1]["start"] - 0.15
        if kind == "line":                                     # you say this line yourself, on camera
            shots.append({"beat": b["key"], "kind": "line", "start": round(b["start"] - 0.5, 3), "end": round(nxt, 3),
                          "pos": pos, "num": spec["lines"][b["num"]], "line_start": b["start"]})
        else:                                                  # "after": you wait on camera once the line is said
            start = b["start"] + b["dur"] + 0.35
            if nxt - start >= 1.5:
                shots.append({"beat": b["key"], "kind": "quiet", "start": round(start, 3), "end": round(nxt, 3),
                              "pos": pos})
    return shots


def main(beats_mod, scene_py, project_dir, sections, min_window, meta):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["schedule", "render", "mix", "all"])
    ap.add_argument("--estimate", action="store_true", help="schedule from word counts (voice not ready)")
    ap.add_argument("--quality", default="h", choices=["l", "m", "h"])
    ap.add_argument("--variant", default="", help="e.g. 'real': uses voice-real/, build-real/, daa-<code>-real.mp4; "
                    "'face': real voice + your camera (--camera) where the mascot stands; "
                    "'cameo': cloned voice + the mascot, with you on camera in a few short shots (meta['cameo'])")
    ap.add_argument("--camera", help="face/cameo variants: the camera recording your real-voice lines were cut from")
    args = ap.parse_args()
    p = Path(project_dir)
    sfx = f"-{args.variant}" if args.variant else ""
    if args.variant in ("face", "cameo") and not args.camera:
        sys.exit(f"The {args.variant} variant needs --camera <your camera recording>.")
    voice_dir = p / ("voice-real" if args.variant == "face" else f"voice{sfx}")
    if args.variant == "cameo":
        voice_dir = cameo_voice(p, meta["cameo"])
    build = p / f"build{sfx}"
    build.mkdir(parents=True, exist_ok=True)
    os.environ["VARIANT"] = args.variant                    # the scene can adapt (e.g. the intro line)
    sched_path, env_path = build / "schedule.json", build / "envelope.npy"
    narr, sfx_log, srt_path = build / "narration.wav", build / "sfx.json", build / "captions.srt"
    if args.step in ("schedule", "all"):
        sched = schedule(beats_mod.BEATS, sections, min_window, voice_dir, sched_path, args.estimate, meta)
        if args.variant == "cameo":
            sched["cameos"], sched["face_px"] = cameo_shots(sched, meta["cameo"]), meta["cameo"]["size"]
            sched_path.write_text(json.dumps(sched, indent=1))
        narration(sched, narr, env_path)
        srt(sched, srt_path)
    if args.step in ("render", "all"):
        video = render(scene_py, sched_path, env_path, sfx_log, build / "media", args.quality)
        (build / "render.txt").write_text(str(video))
        print(f"Rendered {video}")
    if args.step in ("mix", "all"):
        sched = json.loads(sched_path.read_text())
        video = Path((build / "render.txt").read_text().strip())
        out = p / "output" / f"daa-{meta['code']}{sfx}.mp4"
        out.parent.mkdir(exist_ok=True)
        faces = None
        if args.variant == "face":
            import facecam
            start = next(b["start"] for b in sched["beats"] if b["key"] == "hook_mascot")
            clip = facecam.track(sched, voice_dir, args.camera, build / "face.mp4", start)
            faces = [{"clip": clip, "start": start, "end": sched["total"], "pos": FACE_POS}]
        elif args.variant == "cameo":
            import facecam
            real = ROOT / meta["cameo"]["real"]
            clips = facecam.cameos(sched["cameos"], args.camera, real, build, sched["face_px"])
            faces = [{"clip": c, **{k: s[k] for k in ("start", "end", "pos")}} for c, s in zip(clips, sched["cameos"])]
        mix(sched, video, narr, sfx_log, srt_path, p / "output" / "thumbnail.png", out, faces=faces)
        youtube_description(sched, meta, p / "output" / f"youtube-description{sfx}.txt")
        print(f"Final video: {out}")
