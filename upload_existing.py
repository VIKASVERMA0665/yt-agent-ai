"""
Upload an already-rendered video without rerunning the AI pipeline.
Run from the repo root:
    .\.venv\Scripts\python.exe upload_existing.py
Requires output\final_video.mp4, output\script.json and client_secret.json.
"""
import json
import os
import sys

from uploader.youtube import upload_to_youtube

VIDEO_PATH = os.path.join("output", "final_video.mp4")
SCRIPT_PATH = os.path.join("output", "script.json")

def main():
    if not os.path.isfile(VIDEO_PATH):
        raise FileNotFoundError(f"Rendered video not found: {VIDEO_PATH}")
    if not os.path.isfile(SCRIPT_PATH):
        raise FileNotFoundError(f"Video metadata/script not found: {SCRIPT_PATH}")
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script = json.load(f)

    title = str(script.get("title") or script.get("video_title") or "").strip()
    if not title:
        title = input("YouTube video title: ").strip()
        if not title:
            raise ValueError("A YouTube title is required.")
        script["title"] = title

    print("Video:", os.path.abspath(VIDEO_PATH))
    print("Title:", script["title"])
    print("Upload visibility is controlled by config.VIDEO_PRIVACY.")
    confirm = input("Type UPLOAD to start uploading this video: ").strip()
    if confirm != "UPLOAD":
        print("Cancelled. Nothing was uploaded.")
        return

    url = upload_to_youtube(script, os.path.abspath(VIDEO_PATH))
    print("\nUpload finished:", url)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"UPLOAD FAILED: {exc}", file=sys.stderr)
        raise
