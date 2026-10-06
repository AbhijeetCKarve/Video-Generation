#!/usr/bin/env bash
# Generates fake inputs (a "Tella recording", captions, a music track) and
# builds projects/demo so you can check the pipeline works end to end.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p projects/demo/clips music
# Stand-in for a Tella export: test pattern + a tone that turns on and off like speech
ffmpeg -y -loglevel error \
  -f lavfi -i "testsrc2=s=1280x720:r=30:d=8" \
  -f lavfi -i "sine=f=300:r=48000:d=8" \
  -af "volume='if(lt(mod(t,2),1.2),0.8,0)':eval=frame" \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest projects/demo/clips/tella-export.mp4

cat > projects/demo/clips/tella-export.srt <<'EOF'
1
00:00:00,500 --> 00:00:03,000
Hi! This is a demo of the vedit pipeline.

2
00:00:03,500 --> 00:00:06,500
Captions are styled by the selected theme.
EOF

# Stand-in for a downloaded Pixabay/Mixkit/Thematic track
ffmpeg -y -loglevel error -f lavfi -i "sine=f=440:r=48000:d=5" \
  -af "volume=0.5" /tmp/demo-music.mp3
python3 vedit.py music add /tmp/demo-music.mp3 --source pixabay \
  --title "Demo Tone" --artist "vedit" --license "test only" --mood calm

cat > projects/demo/project.json <<'EOF'
{
  "theme": "clean",
  "resolution": [1920, 1080],
  "fps": 30,
  "intro": {"title": "vedit demo", "subtitle": "Tella + FFmpeg + free music", "duration": 3},
  "clips": [
    {"file": "clips/tella-export.mp4", "start": 0, "end": 7, "captions": "clips/tella-export.srt"}
  ],
  "outro": {"title": "Thanks for watching", "duration": 2},
  "music": {"mood": "calm", "volume": 0.25, "duck": true},
  "output": "output/final.mp4"
}
EOF

python3 vedit.py build projects/demo/project.json
