#!/usr/bin/env python3
"""Teleprompter-style voice-over recorder.

Shows one line of a narration script at a time and records your microphone
with FFmpeg into OUTDIR/01.wav, 02.wav, ... Lines already recorded are skipped,
so you can stop and continue later.

    python3 scripts/record_voiceover.py projects/nqueens/clips/nqueens.script.txt projects/nqueens/voice
    python3 scripts/record_voiceover.py SCRIPT OUTDIR --only 3      # redo just line 3

Microphone input per OS (override with --format / --device):
    macOS    avfoundation  ":0"        (list: ffmpeg -f avfoundation -list_devices true -i "")
    Windows  dshow         required:   --device "audio=Microphone (USB Audio)"
                                       (list: ffmpeg -list_devices true -f dshow -i dummy)
    Linux    pulse         "default"
"""
import argparse
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from vedit import probe_duration  # noqa: E402


def default_input():
    system = platform.system()
    if system == "Darwin":
        return "avfoundation", ":0"
    if system == "Windows":
        return "dshow", None
    return "pulse", "default"


def read_script(path):
    lines = []
    for raw in Path(path).read_text().splitlines():
        num, _, text = raw.strip().partition("  ")
        if num.isdigit() and text:
            # "{excited} a | b" -> "(read it: excited) a b"; the markup is for the AI voice
            mood = re.match(r"\s*\{(\w+)\}", text)
            text = re.sub(r"\{[^}]*\}", "", text).replace("|", " ")
            text = " ".join(text.split())
            lines.append((num, f"({mood.group(1)}) {text}" if mood else text))
    if not lines:
        sys.exit(f"No lines found in {path} (expected '01  text' per line)")
    return lines


def record(fmt, device, out):
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", fmt, "-i", device,
                             "-ac", "1", "-ar", "48000", str(out)],
                            stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    input("  ● REC  speak now, press Enter when done ")
    _, err = proc.communicate(b"q")            # 'q' tells ffmpeg to stop and finish the file
    if not out.exists() or out.stat().st_size < 1000:
        sys.exit(f"Recording failed - check your microphone settings:\n{err.decode()[-1500:]}")


def play(path):
    if shutil.which("ffplay"):
        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
                       stdin=subprocess.DEVNULL)
    else:
        print(f"  (ffplay not found - open {path} to listen)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", help="narration script (.script.txt)")
    ap.add_argument("outdir", help="folder for the recordings")
    ap.add_argument("--format", help="ffmpeg input format (avfoundation, dshow, pulse, alsa...)")
    ap.add_argument("--device", help="ffmpeg input device")
    ap.add_argument("--only", type=int, action="append", help="(re)record just this line number, repeatable")
    args = ap.parse_args()

    fmt, device = default_input()
    fmt, device = args.format or fmt, args.device or device
    if device is None:
        sys.exit("On Windows pass your microphone, e.g. --device \"audio=Microphone (USB Audio)\"\n"
                 "List them with: ffmpeg -list_devices true -f dshow -i dummy")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    lines = read_script(args.script)
    if args.only:
        lines = [(n, t) for n, t in lines if int(n) in args.only]

    print(f"{len(lines)} line(s). Speak clearly, pause a moment before and after - silence is trimmed.\n")
    for num, text in lines:
        out = outdir / f"{num}.wav"
        if out.exists() and not args.only:
            print(f"[{num}] already recorded, skipping (use --only {int(num)} to redo)")
            continue
        while True:
            print(f"\n[{num}/{len(read_script(args.script)):02d}]  “{text}”")
            input("  press Enter to start recording ")
            record(fmt, device, out)
            choice = ""
            while True:
                choice = input(f"  saved {probe_duration(out):.1f}s  [Enter]=next  p=play  r=redo  q=quit: ").strip().lower()
                if choice == "p":
                    play(out)
                    continue
                break
            if choice == "q":
                print(f"Stopped (line {num} kept). Run the same command again to continue.")
                return
            if choice != "r":
                break
    print(f"\nAll done. Recordings are in {outdir}")


if __name__ == "__main__":
    main()
