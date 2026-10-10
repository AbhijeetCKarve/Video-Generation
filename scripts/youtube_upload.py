#!/usr/bin/env python3
"""Upload a finished, QA-passed video to YouTube - only with the owner's consent.

    python3 scripts/youtube_upload.py projects/daa-3.2 --consent "upload daa-3.2.mp4"

Safety gates (all must hold, or nothing is sent):
  1. --consent must be exactly "upload <video file name>" - typed only after the
     channel owner has said yes to this specific video.
  2. output/qa-report.md exists, is newer than the video, and has no FAIL.
  3. The video was not uploaded before (output/upload.json), unless --again.

The video goes up as PRIVATE with title, description, tags, chapters, category
Education, "not made for kids", the AI-voice disclosure, the thumbnail and an
English subtitle track. YouTube then runs its own copyright check (Content ID);
the owner publishes it from YouTube Studio once that shows no issues.

Credentials come from environment variables YT_CLIENT_ID, YT_CLIENT_SECRET and
YT_REFRESH_TOKEN (made once with scripts/youtube_auth.py).
pip install google-api-python-client google-auth
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]


def read_metadata(desc_file):
    text = Path(desc_file).read_text()
    title = text.split("TITLE\n")[1].split("\n")[0].strip()
    body = text.split("DESCRIPTION\n")[1].split("\nTAGS")[0].strip()
    tags = [t.strip() for t in text.split("TAGS\n")[1].strip().split(",") if t.strip()]
    return title, body, tags


def gates(project, video, consent, again, sfx=""):
    expected = f"upload {video.name}"
    if consent != expected:
        sys.exit(f'Not uploading: consent must be exactly "{expected}" (given after the owner approved this video).')
    qa = project / "output" / f"qa-report{sfx}.md"
    if not qa.exists() or qa.stat().st_mtime < video.stat().st_mtime:
        sys.exit("Not uploading: run scripts/qa_check.py on this exact video first.")
    if "Verdict: FAIL" in qa.read_text():
        sys.exit("Not uploading: the QA report has failures. Fix them and re-run the check.")
    done = project / "output" / f"upload{sfx}.json"
    if done.exists() and not again:
        prev = json.loads(done.read_text())
        sys.exit(f"Already uploaded on {prev['uploaded_at']}: {prev['url']} (use --again to upload a second copy).")


def youtube_client():
    missing = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Not uploading: missing environment variables {', '.join(missing)} (see scripts/youtube_auth.py).")
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"], scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--consent", required=True, help='exactly "upload <video file name>"')
    ap.add_argument("--again", action="store_true", help="allow a second upload of the same video")
    ap.add_argument("--variant", default="", help="upload daa-<code>-<variant>.mp4 (e.g. real)")
    args = ap.parse_args()
    project = Path(args.project)
    sfx = f"-{args.variant}" if args.variant else ""
    videos = [f for f in (project / "output").glob("daa-*.mp4") if f.stem.endswith(sfx) and
              (sfx or not any(f.stem.endswith(x) for x in ("-real", "-face", "-cameo")))]
    video = sorted(videos, key=lambda f: f.stat().st_mtime)[-1]
    gates(project, video, args.consent, args.again, sfx)
    title, body, tags = read_metadata(project / "output" / f"youtube-description{sfx}.txt")
    synthetic = args.variant not in ("real", "face")   # only the cloned narration needs the AI disclosure

    from googleapiclient.http import MediaFileUpload
    yt = youtube_client()
    request = yt.videos().insert(part="snippet,status", body={
        "snippet": {"title": title, "description": body, "tags": tags, "categoryId": "27",       # 27 = Education
                    "defaultLanguage": "en", "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": synthetic, "embeddable": True, "license": "youtube"},
    }, media_body=MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4"))
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  uploaded {status.progress() * 100:.0f}%")
    vid = response["id"]
    print(f"Video uploaded (private): https://youtu.be/{vid}")

    thumb = project / "output" / "thumbnail.png"
    if thumb.exists():
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/png")).execute()
        print("Thumbnail set")
    srt = project / f"build{sfx}" / "captions.srt"
    if srt.exists():
        yt.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": "en", "name": "English"}},
                             media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream")).execute()
        print("English subtitles added")

    record = {"video_id": vid, "url": f"https://youtu.be/{vid}", "file": video.name, "title": title,
              "privacy": "private", "uploaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (project / "output" / f"upload{sfx}.json").write_text(json.dumps(record, indent=1))
    print("\nNext: open YouTube Studio -> Content -> this video -> check 'Copyright' shows no issues -> Publish.")


if __name__ == "__main__":
    main()
