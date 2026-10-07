#!/usr/bin/env python3
"""One-time: authorise this project to upload to YOUR YouTube channel.

Run this on your own computer (it opens a browser to sign in to Google):

    pip install google-auth-oauthlib
    python3 youtube_auth.py client_secret.json

client_secret.json comes from Google Cloud Console:
  1. console.cloud.google.com -> create a project (e.g. "DAA videos")
  2. APIs & Services -> Library -> "YouTube Data API v3" -> Enable
  3. APIs & Services -> OAuth consent screen -> External, add yourself as a test user
  4. APIs & Services -> Credentials -> Create credentials -> OAuth client ID -> Desktop app
     -> Download JSON

It prints three values. Add them as environment variables in the Claude cloud
environment settings (never paste them into a chat):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""
import json
import sys

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",       # upload videos + thumbnails
          "https://www.googleapis.com/auth/youtube.force-ssl"]    # add the subtitle track


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    client = json.load(open(sys.argv[1]))
    client = client.get("installed") or client.get("web")
    print("\nAdd these three environment variables in your Claude environment settings:\n")
    print(f"YT_CLIENT_ID={client['client_id']}")
    print(f"YT_CLIENT_SECRET={client['client_secret']}")
    print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
    print("\nKeep them private: anyone with them can upload to your channel.")


if __name__ == "__main__":
    main()
