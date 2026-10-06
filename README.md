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

### Step 4 — Get music (Pixabay Music, Mixkit, Thematic)

| Source | Where | Notes |
|---|---|---|
| Pixabay Music | https://pixabay.com/music/ | Free, no attribution required (Pixabay Content License) |
| Mixkit | https://mixkit.co/free-stock-music/ | Free under the Mixkit License; also has free sound effects & video clips |
| Thematic | https://www.hellothematic.com | Free for creators, but you must **register the YouTube video** in Thematic so it isn't flagged by Content ID |

Download an MP3, then register it in your library with a mood tag so you can find it later:

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
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `Font 'Inter' not found` | Install the font, or set `"font"` in the theme to a font you have (or a full path to a `.ttf`) |
| Music too loud / quiet | Change `music.volume` (e.g. 0.15 or 0.35) |
| Video looks squashed | It shouldn't be — clips are fitted with bars. Check `resolution` is what you want |
| Something fails | Run with `-v` and look at the last FFmpeg command and error |
