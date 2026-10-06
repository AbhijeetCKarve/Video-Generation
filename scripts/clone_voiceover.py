#!/usr/bin/env python3
"""Voice-over in YOUR voice, from one recording of you.

Give it a recording of yourself (phone voice memo is fine). It:
  1. transcribes the recording (Whisper) and finds which script lines you
     already read - those lines use your real recording as-is;
  2. clones your voice for every other line (ZipVoice zero-shot cloning),
     trying each of your lines as the voice sample and keeping the take that
     sounds most like you (speaker-embedding similarity), is clearest
     (re-transcribed by Whisper) and, for lively moods, has the most pitch
     movement;
  3. polishes every line the same way and writes 01.wav, 01.json, ... that
     generators/nqueens.py --voice picks up.

    pip install sherpa-onnx numpy soundfile
    python3 scripts/clone_voiceover.py projects/nqueens/clips/nqueens.script.txt projects/nqueens/voice \\
        --reference my-voice.m4a

Models (downloaded on first run into models/, ~1.6 GB) all run offline on CPU:
Whisper small.en, ZipVoice-distill (zh-en, Emilia), Vocos vocoder, WeSpeaker ResNet34.
Only clone a voice you have the right to use - your own.
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from ai_voiceover import POLISH, parse_script  # noqa: E402

MODELS = ROOT / "models"
REL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
ASR_DIR = MODELS / "asr" / "sherpa-onnx-whisper-small.en"
ZV_DIR = MODELS / "zipvoice-int8" / "sherpa-onnx-zipvoice-distill-int8-zh-en-emilia"
VOCODER = MODELS / "zipvoice" / "vocos_24khz.onnx"
SPK = MODELS / "spk" / "wespeaker_en_voxceleb_resnet34_LM.onnx"
SR = 48000
LIVELY = {"excited", "curious", "emphatic"}
NUM = {str(i): w for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve".split())}


# ---------------------------------------------------------------- setup

def ensure_models():
    jobs = [(ASR_DIR, "asr-models/sherpa-onnx-whisper-small.en.tar.bz2"),
            (ZV_DIR, "tts-models/sherpa-onnx-zipvoice-distill-int8-zh-en-emilia.tar.bz2")]
    for folder, url in jobs:
        if not folder.exists():
            print(f"Downloading {url.split('/')[-1]} (one time)...")
            folder.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "m.tar.bz2"
                urllib.request.urlretrieve(REL + url, archive)
                with tarfile.open(archive) as t:
                    t.extractall(folder.parent, filter="data")
    for path, url in [(VOCODER, "vocoder-models/vocos_24khz.onnx"),
                      (SPK, "speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx")]:
        if not path.exists():
            print(f"Downloading {path.name} (one time)...")
            path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(REL + url, path)


def load(path, rate):
    """Any audio file -> mono float32 at `rate`."""
    res = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(rate),
                          "-f", "f32le", "-"], capture_output=True)
    if res.returncode:
        sys.exit(f"Cannot read {path}: {res.stderr.decode()[-500:]}")
    return np.frombuffer(res.stdout, dtype="float32").copy()


def resample(y, src, dst):
    if src == dst:
        return y
    res = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "f32le", "-ar", str(src), "-ac", "1", "-i", "-",
                          "-ar", str(dst), "-f", "f32le", "-"], input=y.astype("float32").tobytes(),
                         capture_output=True)
    return np.frombuffer(res.stdout, dtype="float32").copy()


class Models:
    def __init__(self):
        import sherpa_onnx as so
        a = str(ASR_DIR / "small.en-")
        self.asr = so.OfflineRecognizer.from_whisper(
            encoder=a + "encoder.int8.onnx", decoder=a + "decoder.int8.onnx", tokens=a + "tokens.txt",
            language="en", task="transcribe", num_threads=4)
        self.spk = so.SpeakerEmbeddingExtractor(so.SpeakerEmbeddingExtractorConfig(model=str(SPK), num_threads=4))
        z = ZV_DIR
        self.tts = so.OfflineTts(so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(
            zipvoice=so.OfflineTtsZipvoiceModelConfig(
                tokens=str(z / "tokens.txt"), encoder=str(z / "encoder.int8.onnx"),
                decoder=str(z / "decoder.int8.onnx"), vocoder=str(VOCODER),
                data_dir=str(z / "espeak-ng-data"), lexicon=str(z / "lexicon.txt"), guidance_scale=1.0),
            num_threads=4)))

    def transcribe(self, y16):
        s = self.asr.create_stream()
        s.accept_waveform(16000, y16)
        self.asr.decode_stream(s)
        return s.result.text.strip()

    def embed(self, y16):
        s = self.spk.create_stream()
        s.accept_waveform(16000, y16)
        s.input_finished()
        e = np.array(self.spk.compute(s))
        return e / np.linalg.norm(e)

    def clone(self, text, prompt_text, prompt24, speed, steps):
        g = self.tts.generate(text, prompt_text, prompt24.tolist(), 24000, speed=speed, num_steps=steps)
        return np.array(g.samples, dtype="float32"), g.sample_rate


# ---------------------------------------------------------------- analysis

def speech_segments(y, sr, min_gap=0.35, pad=0.12):
    """Split a recording at its pauses -> [(start_s, end_s)]. The silence level
    adapts to the recording: 6 dB above its own background noise."""
    hop = int(sr * 0.02)
    frames = y[:len(y) // hop * hop].reshape(-1, hop)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(1)) + 1e-9)
    voiced = db > np.percentile(db, 10) + 6
    segs, start, gap = [], None, 0
    for i, v in enumerate(list(voiced) + [False] * int(min_gap / 0.02 + 1)):
        if v:
            start = i if start is None else start
            gap = 0
        elif start is not None:
            gap += 1
            if gap * 0.02 >= min_gap:
                end = i - gap + 1
                if (end - start) * 0.02 > 0.25:
                    segs.append((max(0, start * 0.02 - pad), min(len(y) / sr, end * 0.02 + pad)))
                start, gap = None, 0
    return segs


def words(text):
    text = re.sub(r"(\d+)\s*x\s*(\d+)", r"\1 by \2", text.lower()).replace("-", " ")
    return [NUM.get(w, w) for w in re.sub(r"[^a-z0-9 ]", " ", text).split()]


def match(a, b):
    return difflib.SequenceMatcher(None, words(a), words(b)).ratio()


def align(lines, segs, min_score=0.6):
    """Find which script lines the speaker read: {line_no: (first_seg, last_seg, score)}."""
    found, j0 = {}, 0
    for num, _, phrases in lines:
        text = " ".join(phrases)
        best = None
        for a in range(j0, len(segs)):
            for b in range(a, min(a + 8, len(segs))):
                score = match(" ".join(s["text"] for s in segs[a:b + 1]), text)
                if best is None or score > best[2]:
                    best = (a, b, score)
        if best and best[2] >= min_score:
            found[num] = best
            j0 = best[1] + 1
    return found


def pitch_variation(y, sr):
    """Spread of the voice's pitch in semitones (higher = livelier, less monotone)."""
    hop, win = int(sr * 0.01), int(sr * 0.04)
    rms_all = np.sqrt(np.mean(y ** 2)) + 1e-9
    f0 = []
    for s in range(0, len(y) - win, hop):
        fr = y[s:s + win] - y[s:s + win].mean()
        if np.sqrt(np.mean(fr ** 2)) < 0.3 * rms_all:
            continue
        ac = np.correlate(fr, fr, "full")[win - 1:]
        lo, hi = int(sr / 300), int(sr / 60)
        lag = lo + np.argmax(ac[lo:hi])
        if ac[lag] / (ac[0] + 1e-9) > 0.45:
            f0.append(sr / lag)
    return float(np.std(12 * np.log2(np.array(f0) / np.median(f0)))) if len(f0) > 20 else 0.0


def phrase_times(phrases, cuts, total):
    """Caption timing: phrase boundaries snapped to the nearest real pause where possible."""
    chars = np.cumsum([len(p) for p in phrases]) / sum(len(p) for p in phrases)
    out, t = [], 0.0
    for k, frac in enumerate(chars):
        end = total if k == len(phrases) - 1 else frac * total
        later = [c for c in cuts if c > t + 0.4]            # each pause once, never before this caption
        if later and k < len(phrases) - 1:
            near = min(later, key=lambda c: abs(c - end))
            end = near if abs(near - end) < 0.12 * total else end
        end = max(end, t + 0.4)
        out.append({"text": phrases[k], "start": round(t, 3), "end": round(end, 3)})
        t = end
    return out


def polish(y, sr, tmp, name, denoise):
    src, dst = Path(tmp) / f"{name}_i.wav", Path(tmp) / f"{name}_o.wav"
    sf.write(src, y, sr)
    chain = ("afftdn=nf=-30," if denoise else "") + POLISH
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", chain, "-ar", str(SR), "-ac", "1",
                    str(dst)], check=True)
    out, _ = sf.read(dst, dtype="float32")
    speech = out[np.abs(out) > 0.01]
    out *= 10 ** (-20 / 20) / max(np.sqrt(np.mean(speech ** 2)) if speech.size else 1.0, 1e-6)
    return np.clip(out, -0.97, 0.97)


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", help="narration script (.script.txt)")
    ap.add_argument("outdir", help="folder to write 01.wav, 01.json, ...")
    ap.add_argument("--reference", nargs="+", required=True, help="recording(s) of your voice")
    ap.add_argument("--clone-all", action="store_true", help="clone every line, even ones you read yourself")
    ap.add_argument("--speed", type=float, default=1.0, help="pace of cloned lines (default 1.0 = like you)")
    ap.add_argument("--steps", type=int, default=8, help="cloning quality steps (more = slower, smoother)")
    args = ap.parse_args()

    ensure_models()
    m = Models()
    lines = parse_script(args.script)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 1. transcribe the reference recording(s), phrase by phrase
    segs = []
    for path in args.reference:
        y48 = load(path, SR)
        # find pauses on a 16 kHz copy: phone recordings carry hiss above 8 kHz that hides them
        for a, b in speech_segments(resample(y48, SR, 16000), 16000):
            piece = y48[int(a * SR):int(b * SR)]
            text = m.transcribe(resample(piece, SR, 16000))
            if len(words(text)) >= 2:                    # drop clicks, beeps and stray noises
                segs.append({"audio": piece, "text": text, "start": a, "end": b})
    if not segs:
        sys.exit("No speech found in the reference recording.")
    print(f"Heard {len(segs)} phrases ({sum(s['end'] - s['start'] for s in segs):.0f}s of speech):")
    for s in segs:
        print(f"   {s['text']}")

    # 2. which script lines did you read? those become prompts (and real lines)
    read = align(lines, segs)
    own = {}
    for num, mood, phrases in lines:
        if num in read:
            a, b, score = read[num]
            gap = np.zeros(int(0.25 * SR), dtype="float32")
            parts, cuts, t = [], [], 0.0
            for s in segs[a:b + 1]:                      # keep your phrases with natural short pauses
                parts += [s["audio"], gap]
                t += len(s["audio"]) / SR + len(gap) / SR
                cuts.append(t - len(gap) / SR / 2)
            audio = np.concatenate(parts[:-1])
            own[num] = {"audio": audio, "text": " ".join(phrases), "mood": mood, "cuts": cuts[:-1],
                        "score": score}
            print(f"[{num}] you read this line (match {score:.0%})")
    if own:
        prompts = [(num, o["text"], o["audio"], o["mood"]) for num, o in own.items()]
    else:                                                 # a free-form sample: use ~8 s chunks of it
        prompts, cur = [], []
        for s in segs:
            cur.append(s)
            if sum(len(c["audio"]) for c in cur) / SR >= 6:
                prompts.append((f"p{len(prompts)}", " ".join(c["text"] for c in cur),
                                np.concatenate([c["audio"] for c in cur]), "warm"))
                cur = []
    you = np.mean([m.embed(resample(p[2], SR, 16000)) for p in prompts], axis=0)
    you /= np.linalg.norm(you)
    lively = {p[0]: pitch_variation(p[2], SR) for p in prompts}

    with tempfile.TemporaryDirectory(prefix="clone_") as tmp:
        for num, mood, phrases in lines:
            text = " ".join(phrases)
            if num in own and not args.clone_all:
                o = own[num]
                y = polish(o["audio"], SR, tmp, num, denoise=True)
                timings = phrase_times(phrases, o["cuts"], len(y) / SR)
                kind = "your recording"
            else:
                # 3. clone: try every prompt, keep the take most like you, clear, and lively when it should be
                best = None
                for pid, ptext, paudio, pmood in prompts:
                    y24, rate = m.clone(text, ptext, resample(paudio, SR, 24000), args.speed, args.steps)
                    y16 = resample(y24, rate, 16000)
                    sim = float(m.embed(y16) @ you)
                    clear = match(m.transcribe(y16), text)
                    life = pitch_variation(y24, rate)
                    score = sim + 0.6 * clear + (0.04 * life if mood in LIVELY else 0) + (0.03 if pmood == mood else 0)
                    if clear < 0.8:
                        score -= 1                      # mispronounced or garbled take
                    if best is None or score > best[0]:
                        best = (score, y24, rate, pid, sim, clear, life)
                _, y24, rate, pid, sim, clear, life = best
                y = polish(resample(y24, rate, SR), SR, tmp, num, denoise=False)
                timings = phrase_times(phrases, [], len(y) / SR)
                kind = f"cloned (sample {pid}, like you {sim:.2f}, clear {clear:.0%}, pitch {life:.1f} st)"
            sf.write(outdir / f"{num}.wav", y, SR)
            (outdir / f"{num}.json").write_text(json.dumps({"mood": mood, "phrases": timings}, indent=1))
            print(f"[{num}] {mood:8} {len(y) / SR:4.1f}s  {kind}")
    print(f"Voice-over written to {outdir}")


if __name__ == "__main__":
    main()
