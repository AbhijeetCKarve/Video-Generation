#!/usr/bin/env python3
"""vedit - a small FFmpeg-driven video editing pipeline.

Workflow:
  1. Record with Tella, export MP4 into projects/<name>/clips/
  2. Download music from Pixabay Music, Mixkit or Thematic into music/
     and register it with `vedit.py music add`
  3. Describe the edit in projects/<name>/project.json
  4. Run `vedit.py build projects/<name>/project.json`

Only the Python standard library and the ffmpeg/ffprobe binaries are needed.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
THEMES_DIR = ROOT / "themes"
MUSIC_DIR = ROOT / "music"
CATALOG = MUSIC_DIR / "catalog.json"
# where a track came from - recorded in the catalog and the credits file
MUSIC_SOURCES = ["generated", "pixabay", "mixkit", "thematic", "youtube", "fma", "incompetech",
                 "uppbeat", "bensound", "chosic", "musopen", "other"]


# ---------------------------------------------------------------- helpers

def run(cmd, verbose=False):
    if verbose:
        print("  $ " + " ".join(str(c) for c in cmd))
    res = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"ffmpeg failed:\n{res.stderr[-3000:]}")
    return res.stdout


def probe_duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=nw=1:nk=1", path])
    return float(out.strip())


def has_audio(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "a",
               "-show_entries", "stream=index", "-of", "csv=p=0", path])
    return bool(out.strip())


def find_font(name):
    """Return a font file path for a family name (or a path given directly)."""
    if os.path.isfile(name):
        return name
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", name],
                             capture_output=True, text=True).stdout.strip()
        if out:
            return out
    except FileNotFoundError:
        pass
    sys.exit(f"Font '{name}' not found; set an existing font file in the theme.")


def ass_color(hex_color, alpha=0):
    """#RRGGBB -> ASS &HAABBGGRR."""
    h = hex_color.lstrip("#")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def load_theme(name):
    theme = load_json(THEMES_DIR / f"{name}.json")
    if theme is None:
        available = ", ".join(p.stem for p in THEMES_DIR.glob("*.json"))
        sys.exit(f"Theme '{name}' not found. Available: {available}")
    return theme


# ---------------------------------------------------------------- segments

def encode_args(fps):
    return ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]


def render_card(card, theme, size, fps, out, tmp, verbose):
    """Solid-colour title card with a title, optional subtitle and accent bar."""
    w, h = size
    dur = float(card.get("duration", 3))
    font = find_font(theme["font"])
    title_file = Path(tmp) / f"{out.stem}_title.txt"
    title_file.write_text(card.get("title", ""))
    fade = min(0.5, dur / 4)
    filters = [
        f"drawbox=x=(iw-{w // 8})/2:y=ih/2+{h // 40}:w={w // 8}:h={max(4, h // 180)}"
        f":color={theme['accent']}:t=fill",
        f"drawtext=fontfile='{font}':textfile='{title_file}':fontcolor={theme['text']}"
        f":fontsize={int(h * theme.get('title_scale', 0.07))}:x=(w-tw)/2:y=h/2-th-{h // 40}",
    ]
    if card.get("subtitle"):
        sub_file = Path(tmp) / f"{out.stem}_sub.txt"
        sub_file.write_text(card["subtitle"])
        filters.append(
            f"drawtext=fontfile='{font}':textfile='{sub_file}':fontcolor={theme['muted']}"
            f":fontsize={int(h * 0.035)}:x=(w-tw)/2:y=h/2+{h // 15}")
    filters += [f"fade=t=in:st=0:d={fade}", f"fade=t=out:st={dur - fade}:d={fade}"]
    run(["ffmpeg", "-y",
         "-f", "lavfi", "-i", f"color=c={theme['background']}:s={w}x{h}:r={fps}:d={dur}",
         "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo:d={dur}",
         "-vf", ",".join(filters), "-shortest", *encode_args(fps), out], verbose)


def render_clip(clip, theme, size, fps, base, out, tmp, verbose):
    """Trim, scale/pad to the target size, clean up voice, burn captions."""
    w, h = size
    src = (base / clip["file"]).resolve()
    if not src.exists():
        sys.exit(f"Clip not found: {src}")
    cmd = ["ffmpeg", "-y"]
    if "start" in clip:
        cmd += ["-ss", str(clip["start"])]
    if "end" in clip:
        cmd += ["-to", str(clip["end"])]
    cmd += ["-i", src]

    vf = [f"scale={w}:{h}:force_original_aspect_ratio=decrease",
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={theme['background']}",
          "setsar=1", f"fps={fps}"]
    if clip.get("captions"):
        srt = (base / clip["captions"]).resolve()
        safe = Path(tmp) / f"{out.stem}.srt"          # avoid path escaping issues
        shutil.copy(srt, safe)
        c = theme["captions"]
        style = (f"Fontname={c.get('font', theme['font'])},FontSize={c['size']},"
                 f"PrimaryColour={ass_color(c['color'])},"
                 f"OutlineColour={ass_color(c['outline'])},"
                 f"BackColour={ass_color(c.get('box', '#000000'), 0x60)},"
                 f"BorderStyle={c.get('border_style', 1)},Outline={c.get('outline_width', 2)},"
                 f"Shadow=0,MarginV={c.get('margin_v', 40)},Bold={1 if c.get('bold') else 0}")
        # SRT times refer to the untrimmed file, so shift back to source time while burning
        offset = float(clip.get("start", 0))
        vf += [f"setpts=PTS+{offset}/TB",
               f"subtitles=filename='{safe}':force_style='{style}'",
               "setpts=PTS-STARTPTS"]

    if has_audio(src):
        # gentle voice clean-up for raw screen recordings; "clean_audio": false for narration
        # that is already processed (running it twice makes speech sound watery)
        af = ("highpass=f=80,afftdn=nf=-25,acompressor=threshold=-18dB:ratio=3:attack=5:release=100"
              if clip.get("clean_audio", True) else "anull")
        cmd += ["-vf", ",".join(vf), "-af", af]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                "-vf", ",".join(vf), "-map", "0:v", "-map", "1:a", "-shortest"]
    run(cmd + encode_args(fps) + [out], verbose)


# ---------------------------------------------------------------- music

def pick_track(music_cfg):
    catalog = load_json(CATALOG, [])
    if music_cfg.get("track"):
        entry = next((t for t in catalog if t["file"] == music_cfg["track"]), None)
        path = MUSIC_DIR / music_cfg["track"]
        if not path.exists():
            sys.exit(f"Music file not found: {path}")
        return path, entry
    mood = music_cfg.get("mood")
    for t in catalog:
        if mood is None or mood in t.get("moods", []):
            return MUSIC_DIR / t["file"], t
    print(f"  warning: no track in {CATALOG.name} matches mood '{mood}' - building without music.\n"
          f"  Add one with: python3 vedit.py music add <file> --source pixabay --mood {mood}")
    return None, None


def mix_music(video, music_path, cfg, theme, out, verbose):
    """Loop music under the edit, duck it under speech, then normalise loudness."""
    dur = probe_duration(video)
    vol = cfg.get("volume", theme.get("music_volume", 0.25))
    fade = cfg.get("fade", 2)
    # dip the music where speech is most intelligible (consonants ~2-4 kHz) so words cut through
    music_chain = (f"[1:a]volume={vol},atrim=0:{dur},"
                   "equalizer=f=2500:t=q:w=1.5:g=-5,equalizer=f=400:t=q:w=1:g=-2,"
                   f"afade=t=in:st=0:d={fade},afade=t=out:st={max(0, dur - fade)}:d={fade},"
                   f"aformat=sample_rates=48000:channel_layouts=stereo[m]")
    if cfg.get("duck", True):
        graph = (music_chain + ";[0:a]asplit=2[voice][key];"
                 "[m][key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=600[ducked];"
                 "[voice][ducked]amix=inputs=2:duration=first:normalize=0,")
    else:
        graph = music_chain + ";[0:a][m]amix=inputs=2:duration=first:normalize=0,"
    graph += "loudnorm=I=-14:TP=-1.5:LRA=11[a]"
    run(["ffmpeg", "-y", "-i", video, "-stream_loop", "-1", "-i", music_path,
         "-filter_complex", graph, "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out], verbose)


def normalise_only(video, out, verbose):
    run(["ffmpeg", "-y", "-i", video, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", out], verbose)


# ---------------------------------------------------------------- commands

def cmd_build(args):
    project_path = Path(args.project).resolve()
    base = project_path.parent
    p = load_json(project_path)
    theme = load_theme(p.get("theme", "clean"))
    w, h = p.get("resolution", [1920, 1080])
    fps = p.get("fps", 30)
    out = (base / p.get("output", "output/final.mp4")).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="vedit_") as tmp:
        tmp_path = Path(tmp)
        segments = []
        timeline = ([("card", p["intro"])] if p.get("intro") else []) + \
                   [("clip", c) for c in p["clips"]] + \
                   ([("card", p["outro"])] if p.get("outro") else [])
        for i, (kind, item) in enumerate(timeline):
            seg = tmp_path / f"seg{i:03d}.mp4"
            print(f"[{i + 1}/{len(timeline)}] {kind}: {item.get('title') or item.get('file')}")
            if kind == "card":
                render_card(item, theme, (w, h), fps, seg, tmp, args.verbose)
            else:
                render_clip(item, theme, (w, h), fps, base, seg, tmp, args.verbose)
            segments.append(seg)

        print("Joining segments...")
        concat_list = tmp_path / "concat.txt"
        concat_list.write_text("".join(f"file '{s}'\n" for s in segments))
        joined = tmp_path / "joined.mp4"
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
             "-c", "copy", joined], args.verbose)

        credits = []
        track, entry = pick_track(p["music"]) if p.get("music") else (None, None)
        if track:
            print(f"Mixing music: {track.name}")
            mix_music(joined, track, p["music"], theme, out, args.verbose)
            if entry:
                credits.append(entry)
        else:
            print("Normalising loudness...")
            normalise_only(joined, out, args.verbose)

    if credits:
        lines = [f"\"{c.get('title', c['file'])}\" by {c.get('artist', 'unknown')} - {c['source']}"
                 + (f" ({c['url']})" if c.get("url") else "") + f" - license: {c.get('license', '?')}"
                 for c in credits]
        (out.with_suffix(".credits.txt")).write_text("Music credits\n" + "\n".join(lines) + "\n")
    print(f"Done: {out}  ({probe_duration(out):.1f}s)")


def cmd_init(args):
    proj = ROOT / "projects" / args.name
    if proj.exists():
        sys.exit(f"{proj} already exists")
    (proj / "clips").mkdir(parents=True)
    (proj / "output").mkdir()
    save_json(proj / "project.json", {
        "theme": "clean",
        "resolution": [1920, 1080],
        "fps": 30,
        "intro": {"title": args.name.replace("-", " ").title(),
                  "subtitle": "Subtitle here", "duration": 3},
        "clips": [{"file": "clips/tella-export.mp4", "captions": "clips/tella-export.srt"}],
        "outro": {"title": "Thanks for watching", "duration": 3},
        "music": {"mood": "calm", "volume": 0.25, "duck": True},
        "output": "output/final.mp4",
    })
    print(f"Created {proj}\n  1. Put your Tella export(s) in {proj / 'clips'}\n"
          f"  2. Edit {proj / 'project.json'}\n  3. python3 vedit.py build {proj / 'project.json'}")


def cmd_music_add(args):
    src = Path(args.file).resolve()
    if not src.exists():
        sys.exit(f"{src} not found")
    MUSIC_DIR.mkdir(exist_ok=True)
    dest = MUSIC_DIR / src.name
    if src != dest:
        shutil.copy(src, dest)
    catalog = [t for t in load_json(CATALOG, []) if t["file"] != dest.name]
    catalog.append({"file": dest.name, "title": args.title or src.stem,
                    "artist": args.artist or "unknown", "source": args.source,
                    "url": args.url or "", "license": args.license or "",
                    "moods": args.mood or [], "duration": round(probe_duration(dest), 1)})
    save_json(CATALOG, catalog)
    print(f"Added {dest.name} ({args.source}) to the music catalog")


def cmd_music_list(args):
    catalog = load_json(CATALOG, [])
    if not catalog:
        print("Music catalog is empty. Add tracks with `vedit.py music add`.")
    for t in catalog:
        print(f"{t['file']:40} {t['source']:9} {t['duration']:>6}s  moods: {', '.join(t['moods'])}")


def cmd_themes(args):
    for f in sorted(THEMES_DIR.glob("*.json")):
        t = load_json(f)
        print(f"{f.stem:10} {t.get('description', '')}")


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is not installed or not on PATH")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="render a project.json to a finished video")
    b.add_argument("project")
    b.add_argument("-v", "--verbose", action="store_true", help="print ffmpeg commands")
    b.set_defaults(func=cmd_build)

    i = sub.add_parser("init", help="create a new project folder")
    i.add_argument("name")
    i.set_defaults(func=cmd_init)

    sub.add_parser("themes", help="list themes").set_defaults(func=cmd_themes)

    m = sub.add_parser("music", help="manage the music library")
    msub = m.add_subparsers(dest="music_cmd", required=True)
    ma = msub.add_parser("add", help="register a downloaded track")
    ma.add_argument("file")
    ma.add_argument("--source", choices=MUSIC_SOURCES, required=True)
    ma.add_argument("--title")
    ma.add_argument("--artist")
    ma.add_argument("--url", help="page you downloaded it from (for credits)")
    ma.add_argument("--license", help="e.g. 'Pixabay Content License', 'Mixkit License'")
    ma.add_argument("--mood", action="append", help="tag, repeatable: calm, upbeat, ...")
    ma.set_defaults(func=cmd_music_add)
    msub.add_parser("list", help="show the catalog").set_defaults(func=cmd_music_list)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
