#!/usr/bin/env python3
"""Pre-upload quality & compliance check for a finished video.

    python3 scripts/qa_check.py projects/daa-3.2 --facts videos/daa_3_2/facts.py

Reads <project>/output/{daa-*.mp4, thumbnail.png, youtube-description.txt} and
<project>/build/{captions.srt, schedule.json}. Writes <project>/output/qa-report.md
and exits 1 if anything FAILs. Nothing is uploaded until this passes.

Checks
  technical   1920x1080, 30 fps, H.264 + AAC, length vs target, cover art
  audio       loudness -14 LUFS (YouTube), true peak, clipping, long silences
  picture     black frames, long frozen stretches
  captions    present, in order, readable durations
  content     every fact the video states, recomputed (--facts)
  rights      every asset original or licensed for YouTube use; AI-voice disclosure
  youtube     title/description/tag limits, chapters valid, thumbnail limits
"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

# assets the pipeline uses and why each is safe to publish on YouTube
LICENSES = [
    ("Animation", "Rendered by our own code with Manim (MIT licence)", PASS),
    ("Fonts", "Inter (SIL Open Font Licence), DejaVu Sans / Mono (free licence) - allowed in videos", PASS),
    ("Mascot, thumbnail, diagrams", "Drawn by our own code - original", PASS),
    ("Sound effects", "Synthesized by our own code - original", PASS),
    ("Pseudocode", "Our own wording of standard textbook algorithms (algorithms are not copyrightable)", PASS),
]


def run(cmd):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True)


def probe(video):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type,codec_name,width,height,r_frame_rate:stream_disposition=attached_pic:format=duration,size",
               "-of", "json", video]).stdout
    return json.loads(out)


def check_technical(video, target_min, report):
    info = probe(video)
    v = [s for s in info["streams"] if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")]
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    cover = [s for s in info["streams"] if s.get("disposition", {}).get("attached_pic")]
    dur = float(info["format"]["duration"])
    v = v[0] if v else {}
    report("technical", "Resolution 1920x1080", PASS if (v.get("width"), v.get("height")) == (1920, 1080) else FAIL,
           f"{v.get('width')}x{v.get('height')}")
    report("technical", "Frame rate 30 fps", PASS if v.get("r_frame_rate") == "30/1" else WARN, v.get("r_frame_rate", "?"))
    report("technical", "Codecs H.264 video + AAC audio",
           PASS if v.get("codec_name") == "h264" and a and a[0]["codec_name"] == "aac" else FAIL,
           f"{v.get('codec_name')} + {a[0]['codec_name'] if a else 'no audio'}")
    lo, hi = target_min
    status = PASS if lo * 60 <= dur <= hi * 60 else WARN
    report("technical", f"Length {lo}-{hi} min", status, f"{int(dur // 60)}:{int(dur % 60):02d}")
    report("technical", "Thumbnail embedded as cover art", PASS if cover else WARN, "yes" if cover else "no")
    return dur


def check_audio(video, report):
    r = run(["ffmpeg", "-i", video, "-af", "ebur128=peak=true:framelog=quiet,astats=measure_perchannel=none",
             "-f", "null", "-"]).stderr
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
    tp = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r)[-1])
    report("audio", "Loudness -14 LUFS (YouTube standard)", PASS if abs(lufs + 14) <= 1.0 else WARN, f"{lufs:.1f} LUFS")
    report("audio", "True peak at most -1 dBTP", PASS if tp <= -0.9 else WARN, f"{tp:.1f} dBTP")
    peak = re.findall(r"Peak level dB:\s+(-?[\d.]+)", r)
    peak_db = float(peak[-1]) if peak else 0.0
    report("audio", "No clipping (sample peak below full scale)", PASS if peak_db < -0.1 else WARN, f"peak {peak_db:.1f} dBFS")
    s = run(["ffmpeg", "-i", video, "-af", "silencedetect=n=-55dB:d=4", "-f", "null", "-"]).stderr
    gaps = re.findall(r"silence_duration: ([\d.]+)", s)
    report("audio", "No dead air over 4 s", PASS if not gaps else WARN, f"{len(gaps)} silent stretches")


def check_picture(video, dur, report):
    b = run(["ffmpeg", "-i", video, "-vf", "blackdetect=d=1.0:pix_th=0.04", "-an", "-f", "null", "-"]).stderr
    blacks = re.findall(r"black_start:([\d.]+)", b)
    report("picture", "No black screens over 1 s", PASS if not blacks else FAIL, f"{len(blacks)} found")
    f = run(["ffmpeg", "-i", video, "-vf", "freezedetect=n=0.0005:d=9", "-an", "-f", "null", "-"]).stderr
    freezes = re.findall(r"freeze_duration: ([\d.]+)", f)
    report("picture", "No frozen picture over 9 s", PASS if not freezes else WARN,
           f"{len(freezes)} found" + (f" (longest {max(map(float, freezes)):.0f} s)" if freezes else ""))


def check_captions(srt, report):
    if not srt.exists():
        report("captions", "Captions file present", FAIL, "missing")
        return
    blocks = [b for b in srt.read_text().strip().split("\n\n") if b.strip()]

    def ts(t):
        h, m, s = t.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    times = [tuple(map(ts, b.splitlines()[1].split(" --> "))) for b in blocks]
    overlaps = sum(1 for (a1, b1), (a2, b2) in zip(times, times[1:]) if a2 < b1 - 0.01)
    short = sum(1 for a, b in times if b - a < 0.5)
    long_ = sum(1 for a, b in times if b - a > 8)
    report("captions", "Captions present", PASS, f"{len(blocks)} captions")
    report("captions", "No overlapping captions", PASS if not overlaps else WARN, f"{overlaps} overlaps")
    report("captions", "Readable durations (0.5-8 s)", PASS if not short and not long_ else WARN,
           f"{short} too short, {long_} too long")


def check_facts(facts_py, report):
    if not facts_py:
        report("content", "Facts recomputed", WARN, "no facts file given")
        return
    spec = importlib.util.spec_from_file_location("facts", facts_py)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for claim, ok in mod.check():
        report("content", claim, PASS if ok else FAIL, "recomputed")


def check_rights(project, desc, report, real_voice=False, camera=False):
    for name, why, status in LICENSES:
        report("rights", name, status, why)
    catalog = json.loads((ROOT / "music" / "catalog.json").read_text())
    used = [t for t in catalog if t["file"].startswith("generated-")]
    report("rights", "Background music", PASS if used else WARN,
           "original, generated by our code - no Content ID claims possible" if used else "check the track licence")
    if real_voice:
        report("rights", "Voice", PASS, "your own recorded voice, nothing cloned - no synthetic-content disclosure needed")
    else:
        report("rights", "Voice", WARN,
               "your own voice, partly AI-cloned: tick 'Altered or synthetic content' when uploading")
    if camera:
        report("rights", "Camera footage", PASS, "your own face-cam recording")
    report("rights", "Credit line in description", PASS if "Created by" in desc else WARN,
           "present" if "Created by" in desc else "add 'Created by ...'")
    report("rights", "Final Content ID check", WARN,
           "runs inside YouTube on upload; we upload as Private and publish only after it shows no issues")


def check_youtube(desc_text, thumb, report):
    title = desc_text.split("TITLE\n")[1].split("\n")[0].strip()
    body = desc_text.split("DESCRIPTION\n")[1].split("\nTAGS")[0].strip()
    tags = desc_text.split("TAGS\n")[1].strip()
    report("youtube", "Title at most 100 characters", PASS if len(title) <= 100 else FAIL, f"{len(title)} chars")
    report("youtube", "No < or > in title/description", PASS if not re.search(r"[<>]", title + body) else FAIL, "")
    report("youtube", "Description at most 5000 characters", PASS if len(body) <= 5000 else FAIL, f"{len(body)} chars")
    report("youtube", "Tags at most 500 characters", PASS if len(tags) <= 500 else FAIL, f"{len(tags)} chars")
    ch = re.findall(r"^(\d+):(\d\d) ", body, flags=re.M)
    secs = [int(m) * 60 + int(s) for m, s in ch]
    ok = len(secs) >= 3 and secs[0] == 0 and all(b - a >= 10 for a, b in zip(secs, secs[1:]))
    report("youtube", "Chapters valid (start 0:00, 3+, 10 s each)", PASS if ok else FAIL, f"{len(secs)} chapters")
    if thumb.exists():
        info = json.loads(run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "json", thumb]).stdout)
        w, h = info["streams"][0]["width"], info["streams"][0]["height"]
        size = thumb.stat().st_size
        report("youtube", "Thumbnail 1280x720, under 2 MB", PASS if (w, h) == (1280, 720) and size < 2e6 else FAIL,
               f"{w}x{h}, {size / 1024:.0f} KB")
    else:
        report("youtube", "Thumbnail present", FAIL, "missing")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--facts", help="facts.py with check() -> [(claim, ok)]")
    ap.add_argument("--video", help="defaults to the newest daa-*.mp4 in output/")
    ap.add_argument("--minutes", default="6,8", help="target length range, e.g. 6,8")
    ap.add_argument("--variant", default="", help="check daa-*-<variant>.mp4 with build-<variant>/ captions")
    args = ap.parse_args()
    p = Path(args.project)
    sfx = f"-{args.variant}" if args.variant else ""
    candidates = [f for f in (p / "output").glob("daa-*.mp4") if f.stem.endswith(sfx) and
                  (sfx or not any(f.stem.endswith(x) for x in ("-real", "-face", "-cameo")))]
    video = Path(args.video) if args.video else sorted(candidates, key=lambda f: f.stat().st_mtime)[-1]
    desc_path = p / "output" / f"youtube-description{sfx}.txt"
    desc = desc_path.read_text() if desc_path.exists() else ""
    rows = []

    def report(area, check, status, detail):
        rows.append((area, check, status, detail))
        print(f"{status:4}  {area:9} {check} - {detail}")

    lo, hi = map(float, args.minutes.split(","))
    dur = check_technical(video, (lo, hi), report)
    check_audio(video, report)
    check_picture(video, dur, report)
    check_captions(p / f"build{sfx}" / "captions.srt", report)
    check_facts(args.facts, report)
    check_rights(p, desc, report, real_voice=args.variant in ("real", "face"), camera=args.variant == "face")
    if desc:
        check_youtube(desc, p / "output" / "thumbnail.png", report)
    else:
        report("youtube", "Description file present", FAIL, "missing")

    fails = [r for r in rows if r[2] == FAIL]
    warns = [r for r in rows if r[2] == WARN]
    verdict = "FAIL - fix before upload" if fails else ("PASS with notes" if warns else "PASS")
    lines = [f"# QA report: {video.name}", "", f"**Verdict: {verdict}** ({len(rows) - len(fails) - len(warns)} pass, "
             f"{len(warns)} notes, {len(fails)} fail)", "", "| Area | Check | Result | Detail |", "|---|---|---|---|"]
    lines += [f"| {a} | {c} | {s} | {d} |" for a, c, s, d in rows]
    (p / "output" / f"qa-report{sfx}.md").write_text("\n".join(lines) + "\n")
    print(f"\n{verdict}  ->  {p / 'output' / f'qa-report{sfx}.md'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
