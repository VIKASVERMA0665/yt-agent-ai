#!/usr/bin/env python3
"""
YouTube AI Agent — Main Pipeline (Free Edition)
Uses: Gemini 2.5 Flash · Edge TTS · Pixabay · MoviePy · Flask · YouTube Data API

Run:  python pipeline.py
"""
import os
import json
import sys
import argparse
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import config
from agents.researcher   import research_topic
from agents.scriptwriter import write_script
from video.narrator      import generate_narration
from video.stock         import download_images
from video.creator       import create_video
from review.app          import start_review_server
from uploader.youtube    import upload_to_youtube


def banner(text: str):
    print("\n" + "─" * 62)
    print(f"  {text}")
    print("─" * 62)


def run(topic_override: str = "", voice: str = "", no_review: bool = False):
    Path(config.OUTPUT_DIR).mkdir(exist_ok=True)
    Path(config.IMAGES_DIR).mkdir(exist_ok=True)
    if voice:
        config.VOICE_ID = voice

    print("\n🎬  YT Agent AI  ·  Video Pipeline\n")

    # ── 1. Research ───────────────────────────────────────────
    banner("1 / 6  ·  Researching trending topic  [Gemini]")
    research = research_topic(config.CHANNEL_DESCRIPTION, topic_override=topic_override)
    print(f"\n  ✅  Topic : {research['topic']}")
    print(f"      Title : {research['video_title']}")
    print(f"      Hook  : {research.get('hook_question', '')[:90]}")
    with open(f"{config.OUTPUT_DIR}/research.json", "w") as f:
        json.dump(research, f, indent=2)

    # ── 2. Script ─────────────────────────────────────────────
    banner("2 / 6  ·  Writing script  [Gemini]")
    script = write_script(research)
    print(f"\n  ✅  {len(script['sections'])} sections written")
    for s in script["sections"]:
        words = len(s.get("narration", "").split())
        # Safely grab the title, or default to "Untitled" if the AI forgot it
        title = s.get("title", "Untitled") 
        print(f"      [{s.get('id', 9):02d}] {title:<42} {words:3d} words")
    with open(f"{config.OUTPUT_DIR}/script.json", "w") as f:
        json.dump(script, f, indent=2)

    # ── 3. Stock Images ───────────────────────────────────────
    banner("3 / 6  ·  Downloading stock images  [Pixabay]")
    image_map = download_images(script, config.OUTPUT_DIR)
    found = sum(1 for v in image_map.values() if v)
    print(f"\n  ✅  {found}/{len(image_map)} images downloaded")

    # ── 4. Narration ──────────────────────────────────────────
    banner("4 / 6  ·  Generating voiceover  [Edge TTS — free]")
    audio_path = generate_narration(script, config.OUTPUT_DIR)
    print(f"\n  ✅  Audio: {audio_path}")

    # ── 5. Video ──────────────────────────────────────────────
    banner("5 / 6  ·  Building cinematic video  [MoviePy]")
    video_path = create_video(script, audio_path, config.OUTPUT_DIR, image_map)
    # Use an absolute path so the Flask review server does not resolve
    # the relative output path from inside the review/ directory.
    video_path = os.path.abspath(video_path)

    # ── 6. Review ─────────────────────────────────────────────
    if no_review:
        print(f"\n✅ Fresh video rendered: {video_path}")
        print("   Upload was not started. Review the MP4 before publishing.")
        return

    banner("6 / 6  ·  Human review  [Flask dashboard]")
    print("\n  → Opening review dashboard in your browser…")
    review_data = {
        "research":   research,
        "script":     script,
        "video_path": video_path,
    }
    with open(f"{config.OUTPUT_DIR}/review_data.json", "w") as f:
        json.dump({k: v for k, v in review_data.items() if k != "video_path"},
                  f, indent=2)

    approved = start_review_server(review_data)

    # ── Upload or stop ────────────────────────────────────────
    if approved:
        banner("🚀  Uploading to YouTube")
        url = upload_to_youtube(script, video_path)
        print(f"\n  🎉  Video live: {url}\n")
    else:
        print("\n  ❌  Rejected — pipeline stopped.")
        print("      Tip: edit output/script.json and re-run just the video step.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a devotional video from CMD.")
    parser.add_argument("--topic", default="", help="Exact topic for this video")
    parser.add_argument("--voice", default="", help="Edge TTS voice ID, e.g. hi-IN-SwaraNeural")
    parser.add_argument("--no-review", action="store_true", help="Render and stop without review/upload")
    args = parser.parse_args()
    run(topic_override=args.topic, voice=args.voice, no_review=args.no_review)
