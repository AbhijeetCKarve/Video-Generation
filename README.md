# vedit — a simple video editing system

Record with **Tella** → pick free music from **Pixabay Music**, **Mixkit** or **Thematic**
→ choose a **theme** → **FFmpeg** puts it all together into a finished video.

```
 Tella (record)          Pixabay / Mixkit / Thematic (music)
      │                              │
      ▼ export MP4 + captions        ▼ download MP3
 projects/<name>/clips/          music/  (+ catalog.json with credits)
      │                              │
      └────────────┬─────────────────┘
                   ▼
           project.json  ← the "recipe" for your video (theme, clips, titles, music)
                   │
                   ▼
        python3 vedit.py build      ← FFmpeg does the editing
                   │
                   ▼
  output/final.mp4  +  final.credits.txt (music attribution)
```

What the build does for you, automatically:

| Step | What happens |
|---|---|
| Intro / outro cards | Coloured title screens in your theme's colours and font, with fade in/out |
| Trim | Cuts each clip to the `start` / `end` seconds you give |
| Resize | Fits every clip to 1920×1080 (or any size), adding bars instead of stretching |
| Voice clean-up | Removes low rumble, reduces background hiss, evens out your voice level |
| Captions | Burns your `.srt` subtitles into the video, styled by the theme |
| Music | Loops the track to the video length, fades it in/out |
| Ducking | Music automatically gets quieter while you talk, louder in pauses |
| Loudness | Final mix normalised to −14 LUFS (YouTube / Spotify standard) |
| Credits | Writes a `.credits.txt` with the music title, artist, source and licence |

---

## Step-by-step

### Step 1 — Install the tools (one time)

You need **Python 3.8+** and **FFmpeg**.

| OS | Command |
|---|---|
| macOS | `brew install ffmpeg` |
| Windows | `winget install ffmpeg` (then reopen the terminal) |
| Ubuntu/Debian | `sudo apt install ffmpeg` |

Check it works: `ffmpeg -version`. Then get this repo:

```bash
git clone https://github.com/AbhijeetCKarve/Video-Generation.git
cd Video-Generation
./scripts/make_demo.sh        # optional: builds a test video to prove everything works
```

### Step 2 — Create a project

```bash
python3 vedit.py init my-first-video
```

This makes `projects/my-first-video/` with a `clips/` folder, an `output/` folder and a starter `project.json`.

### Step 3 — Record in Tella and export

1. Record your screen / camera in [Tella](https://www.tella.tv).
2. Do the rough edit inside Tella (cut mistakes, choose layouts) — Tella is great at that.
3. **Export → Download → MP4 (1080p)**. Save it into `projects/my-first-video/clips/`.
4. **Captions:** Tella makes a transcript automatically. Download the subtitles as **.srt** and
   save them next to the MP4 with the same name (e.g. `tella-export.mp4` + `tella-export.srt`).
   No captions? Just remove the `"captions"` line from `project.json`.

> Tip: if you recorded several parts, export each one and list them all under `"clips"` —
> they'll play in order.

### Step 4 — Get music (free)

You have two free options. You can mix them in the same library.

#### Option A: music made by vedit (ready to use, nothing to download)

`generators/music.py` composes and plays **original** background music from code: chord
progressions, electric piano, warm pads, bass, soft drums and a melody. Because nobody else owns
it, it is free for any use, needs **no credit**, and can never get a YouTube Content ID claim.
Three tracks are already in `music/`:

| File | Style | Moods (for `project.json`) | Feel |
|---|---|---|---|
| `generated-lofi.mp3` | lofi, 78 bpm | focus, calm, study, lofi | Jazzy chords, soft swung drums, vinyl crackle. Great under teaching |
| `generated-ambient.mp3` | ambient, 64 bpm | calm, ambient, focus, thoughtful | Slow pads and soft bells, no drums. The least distracting |
| `generated-upbeat.mp3` | upbeat, 104 bpm | upbeat, happy, energetic, intro | Bright piano, four-on-the-floor beat. For intros and promos |

Make more (each takes about 30 s). A different `--seed` gives a different melody and variation:

```bash
python3 generators/music.py --list
python3 generators/music.py --style lofi --seed 7 --length 240 --name lofi-long
python3 generators/music.py --style ambient --seed 3 --name calm-2
```

The new track is added to the catalog automatically with its moods. Then use
`"music": {"mood": "calm"}` or `"music": {"track": "calm-2.mp3"}` in `project.json`.

#### Option B: free music websites

Download an MP3 and register it with `--source`, so the credits file says where it came from.

| Site | `--source` | Credit needed? | Notes |
|---|---|---|---|
| [Pixabay Music](https://pixabay.com/music/) | `pixabay` | No | Pixabay Content License. A few tracks are registered with Content ID; if a claim appears, dispute it with the license link |
| [Mixkit](https://mixkit.co/free-stock-music/) | `mixkit` | No | Mixkit License. Also has free sound effects (clicks, whooshes) and video clips |
| [Thematic](https://www.hellothematic.com) | `thematic` | No | Free account. **Register each YouTube video** in Thematic, or it may be flagged |
| [YouTube Audio Library](https://studio.youtube.com) (YouTube Studio → Audio Library) | `youtube` | Some tracks | The library shows which tracks need credit. Safe for YouTube, including monetised videos |
| [Free Music Archive](https://freemusicarchive.org) | `fma` | Usually | The licence differs per track. Choose CC0 or CC BY. Avoid "NC" (non-commercial) if you monetise |
| [Incompetech](https://incompetech.com) (Kevin MacLeod) | `incompetech` | **Yes** | CC BY 4.0. Put the credit line in the description |
| [Uppbeat](https://uppbeat.io) | `uppbeat` | **Yes** (free plan) | Free plan has a monthly download limit and gives you a credit / claim-clearing code |
| [Bensound](https://www.bensound.com) | `bensound` | **Yes** (free licence) | Free with credit; paid licence removes it |
| [Chosic](https://www.chosic.com/free-music/all/) | `chosic` | Usually | Mostly Creative Commons tracks from other artists. Check each page |
| [Musopen](https://musopen.org) | `musopen` | Usually no | Public-domain classical recordings. Calm piano and strings work well under lessons |

> Licences change. Read the licence on the track's page when you download it and copy it into `--license`.

```bash
python3 vedit.py music add ~/Downloads/calm-lofi.mp3 \
  --source pixabay --title "Calm Lofi" --artist "SomeArtist" \
  --url "https://pixabay.com/music/..." --license "Pixabay Content License" \
  --mood calm --mood lofi

python3 vedit.py music list     # see everything in your library
```

The file is copied into `music/` and its details are saved in `music/catalog.json`.
**Always fill in `--url` and `--license`** — they go into the credits file, which keeps you safe if
anyone ever questions your music.

### Step 5 — Pick a theme

```bash
python3 vedit.py themes
```

| Theme | Look | Good for |
|---|---|---|
| `clean` | Dark slate, white text, blue accent | Tutorials, product demos |
| `bold` | Black, yellow accent, big boxed captions | Shorts, social clips |
| `warm` | Cream, dark serif text, orange accent | Vlogs, storytelling |

Want your own brand look? Copy `themes/clean.json` to `themes/mybrand.json`, change the colours /
font, and use `"theme": "mybrand"`.

### Step 6 — Write the recipe (`project.json`)

```json
{
  "theme": "clean",
  "resolution": [1920, 1080],
  "fps": 30,
  "intro":  { "title": "How I Edit Videos", "subtitle": "Episode 1", "duration": 3 },
  "clips": [
    { "file": "clips/tella-export.mp4", "start": 2.5, "end": 184, "captions": "clips/tella-export.srt" },
    { "file": "clips/part-2.mp4" }
  ],
  "outro":  { "title": "Thanks for watching", "subtitle": "Subscribe for more", "duration": 3 },
  "music":  { "mood": "calm", "volume": 0.25, "duck": true },
  "output": "output/final.mp4"
}
```

| Field | Meaning |
|---|---|
| `resolution` | `[1920, 1080]` for YouTube, `[1080, 1920]` for Shorts/Reels/TikTok |
| `intro` / `outro` | Optional. Delete them if you don't want title cards |
| `start` / `end` | Optional. Seconds to keep from that clip |
| `music.mood` | Picks the first track in your library with that mood tag… |
| `music.track` | …or name a file exactly, e.g. `"track": "calm-lofi.mp3"` |
| `music.volume` | 0.0–1.0. Around 0.2–0.3 sits nicely under speech |
| `music.duck` | `true` = music dips while you talk |
| Remove `music` | No background music, just your voice (still loudness-normalised) |

### Step 7 — Build

```bash
python3 vedit.py build projects/my-first-video/project.json
# add -v to see every FFmpeg command it runs
```

You get `projects/my-first-video/output/final.mp4` and `final.credits.txt`.

### Step 8 — Publish

- Upload `final.mp4` to YouTube / LinkedIn / wherever.
- Paste the contents of `final.credits.txt` into your video description.
- If you used a **Thematic** track, register the video URL in your Thematic dashboard.

---

## Project layout

```
vedit.py              the whole tool (Python standard library + FFmpeg, nothing to pip install)
themes/*.json         look & feel presets
music/                your downloaded tracks + catalog.json (MP3s are git-ignored)
projects/<name>/      one folder per video: project.json, clips/, output/
scripts/make_demo.sh  generates fake inputs and builds a test video
generators/           scripts that *create* animated clips (instead of recording them in Tella)
```

---

## Animated explainer: N-Queens

Not every video starts as a Tella recording. `generators/nqueens.py` **draws** an animated
explainer of the N-Queens puzzle (solved with backtracking) and writes a matching captions file.
vedit then adds the title cards, captions and music just like for any other clip. It needs Pillow (`pip install pillow`).

```bash
# 1. Generate the animation (MP4 + SRT captions) — takes about a minute
python3 generators/nqueens.py --n 6 --out projects/nqueens/clips/nqueens.mp4

# 2. Music: the project asks for mood "focus", which the built-in generated-lofi.mp3 already has.
#    (Or add your own track tagged "focus", see Step 4.)

# 3. Build the finished video
python3 vedit.py build projects/nqueens/project.json
#    → projects/nqueens/output/nqueens-final.mp4
```

What the viewer sees (about 1 min 50 s for N = 6):

1. **The puzzle**: an empty board and the goal.
2. **The rules**: one queen with every square it attacks shaded red.
3. **The strategy**: go row by row, skip attacked squares, back up when stuck.
4. **The search**: every step of the real algorithm. A red line shows *which* queen attacks a
   square. Green means a queen was placed, orange means backtracking. The side panel shows the
   `queens[row] = column` array and running counts. The first steps are slow, then it speeds up.
5. **Solved!** The final board and how many steps it took.
6. **How many solutions?** A table of solution counts for N = 1–10.

| Option | Meaning |
|---|---|
| `--n 8` | Board size (1–12). Steps until the first solution: N=4 → 30, N=5 → 15, N=6 → 196, N=7 → 44, N=8 → 981 (≈ 4.5 min, so add `--speed 2`) |
| `--speed 1.5` | Make the whole animation 1.5× faster (use `0.8` for slower) |
| `--theme bold` | Use another theme's colours and fonts (match the one in `project.json`) |

Change the titles in `projects/nqueens/project.json`. Delete the `"music"` block for no music.

### AI voice-over (no microphone needed)

`scripts/ai_voiceover.py` reads the narration script with **Kokoro**, a free, open-source AI voice
that runs on your own computer. The default is a male narrator (`am_michael`), lowered one
semitone so it sounds deeper. The first run downloads the voice model (≈ 340 MB) into `models/`.

```bash
pip install kokoro-onnx soundfile
python3 generators/nqueens.py --n 6 --out projects/nqueens/clips/nqueens.mp4 --script-only
python3 scripts/ai_voiceover.py projects/nqueens/clips/nqueens.script.txt projects/nqueens/voice
python3 generators/nqueens.py --n 6 --out projects/nqueens/clips/nqueens.mp4 --voice projects/nqueens/voice
python3 vedit.py build projects/nqueens/project.json
```

**How it avoids sounding robotic.** The script is written like a teacher talking ("Can you place
six queens…?", "Uh-oh, a dead end!", "And… solved!"), and each line carries delivery notes:

```
07  {emphatic} Uh-oh, a dead end! | There's no safe square left in the next row. | So we backtrack: | ...
```

| Mood | Pace | Pitch | Energy | Used for |
|---|---|---|---|---|
| `curious` | 0.95× | +0.5 | normal | Opening question |
| `explain` | 0.92× (slower) | −0.3 | normal | Rules, strategy, memory boxes |
| `warm` | 0.94× | 0 | normal | Encouraging lines, wrap-up |
| `emphatic` | 0.90× (slowest) | −0.2 | +1 dB | "Red means danger", "dead end" |
| `excited` | 1.02× | +1.0 | +1.5 dB | "Speed things up!", "Solved!" |

On top of the mood, each sentence gets its own pitch, like a teacher's voice. The first sentence
starts a little brighter, later ones settle lower, and questions and exclamations lift. `|` marks
where a new caption starts, so students read one short phrase at a time, in sync with the voice.
Finally the voice is polished: added warmth, clearer consonants, softer "s" sounds, and even
volume across lines.

Edit the wording or moods in the `.script.txt`, then regenerate (`--only 7` redoes just line 7).

| Option | Meaning |
|---|---|
| `--voice am_fenrir` | Another male voice: `am_fenrir`, `am_puck` (US), `bm_george`, `bm_fable` (British) |
| `--voice "am_michael:60,am_fenrir:40"` | Blend two voices |
| `--pitch -2` | Deeper (semitones; the default is −1, and 0 is the natural voice) |
| `--speed 0.9` | Slower overall, for younger students |

> Use either the AI voice or your own recordings in `projects/nqueens/voice/`, not both. A recorded
> `03.m4a` would sit next to an AI `03.wav` with the same number.

### Your voice, cloned from one recording

Record yourself once on your phone. Read some of the script lines, or just talk for 30–60 seconds.
`scripts/clone_voiceover.py` then:

1. **Transcribes** your recording (Whisper) and finds which script lines you read. Those lines use
   **your real recording**, cleaned up.
2. **Clones your voice** for every other line (ZipVoice). It tries each of your lines as the voice
   sample and keeps the best take. "Best" combines three things: how much it sounds like you
   (measured by a speaker-recognition model), how clearly it can be understood (Whisper transcribes
   it again), and, for excited lines, how lively the pitch is.
3. Writes `01.wav`, `01.json`, … with caption timings snapped to your real pauses.

```bash
pip install sherpa-onnx numpy soundfile
python3 generators/nqueens.py --n 6 --out projects/nqueens/clips/nqueens.mp4 --script-only
python3 scripts/clone_voiceover.py projects/nqueens/clips/nqueens.script.txt projects/nqueens/voice \
  --reference my-voice.m4a
python3 generators/nqueens.py --n 6 --out projects/nqueens/clips/nqueens.mp4 --voice projects/nqueens/voice
python3 vedit.py build projects/nqueens/project.json
```

The first run downloads about 1.6 GB of models into `models/`. After that everything runs offline
on your CPU (about 4 minutes for 6 cloned lines). `--clone-all` clones every line, even ones you
recorded, for a perfectly even sound. `--speed 0.95` slows the cloned lines a little.

Tips: a quiet room gives the best clone. Reading a few script lines in the tone you want (curious,
excited, calm) helps a lot, because the clone copies the delivery of its sample. Only clone a voice
that is yours.

### Adding your own voice-over

Your voice is recorded **one line at a time**, then each line is placed exactly where its scene
starts. If you talk longer than a scene lasts, that frame is simply held until you finish. So you
never have to match the timing yourself, and you can redo any single line.

```bash
# 1. Write the narration script (10 short lines, numbered 01, 02, ...)
python3 generators/nqueens.py --n 6 --out projects/nqueens/clips/nqueens.mp4 --script-only
#    → projects/nqueens/clips/nqueens.script.txt   (edit the wording here if you like)

# 2. Record yourself, teleprompter-style
python3 scripts/record_voiceover.py projects/nqueens/clips/nqueens.script.txt projects/nqueens/voice
#    shows a line → Enter → read it → Enter → [Enter]=next  p=play back  r=redo  q=quit
#    Quit any time; running it again continues where you stopped. Redo one line: --only 4

# 3. Render the animation with your voice, then build as usual
python3 generators/nqueens.py --n 6 --out projects/nqueens/clips/nqueens.mp4 --voice projects/nqueens/voice
python3 vedit.py build projects/nqueens/project.json
```

| Microphone setup | |
|---|---|
| macOS | Works out of the box (first mic). The first time, allow Terminal to use the microphone (System Settings → Privacy & Security → Microphone). Another mic: list them with `ffmpeg -f avfoundation -list_devices true -i ""` and pass `--device ":1"` |
| Windows | List mics with `ffmpeg -list_devices true -f dshow -i dummy`, then pass `--device "audio=Microphone (USB Audio)"` with your mic's exact name |
| Linux | Uses the default PulseAudio/PipeWire input |
| Rather use your phone or Tella? | Record each line as its own file and name them `01.m4a`, `02.m4a`, … (the number = the line in the script). Put them in `projects/nqueens/voice/`. Any audio format works |

Tips for a good-sounding voice-over:

- Record in a quiet, soft room. Curtains and a sofa beat an empty room with bare walls.
- Keep the mic about a hand's width from your mouth.
- Leave a short pause before and after each line. The silence is trimmed off automatically.
- vedit cleans up the voice too: it removes rumble and hiss and evens out the volume. It also
  lowers the music while you speak (`"duck": true`).
- Changed the wording of a line? Re-record just that line (`--only N`). Changed `--n`? The script
  changes too, so make a new script and record again.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Font 'Inter' not found` | Install the font, or set `"font"` in the theme to a font you have (or a full path to a `.ttf`) |
| Music too loud / quiet | Change `music.volume` (e.g. 0.15 or 0.35) |
| Video looks squashed | It shouldn't be — clips are fitted with bars. Check `resolution` is what you want |
| Something fails | Run with `-v` and look at the last FFmpeg command and error |
