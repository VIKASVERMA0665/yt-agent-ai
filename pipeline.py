#!/usr/bin/env python3
"""Bhakti Dhun AI video pipeline with optional non-interactive auto-upload."""
import os
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

import config
from agents.researcher import research_topic
from agents.scriptwriter import write_script
from video.narrator import generate_narration
from video.stock import download_images
from video.creator import create_video
from review.app import start_review_server
from uploader.youtube import upload_to_youtube


def banner(text: str):
    print("\n" + "─" * 62)
    print(f"  {text}")
    print("─" * 62)


def run(topic_override: str = "", voice: str = "", no_review: bool = False,
        video_type: str = "normal", auto_upload: bool = False):
    if video_type not in ("normal", "shorts"):
        raise ValueError("video_type must be 'normal' or 'shorts'")

    # Each scheduled video gets its own assets so daily runs cannot overwrite
    # each other's script, narration, images, or rendered MP4.
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join("output", f"auto_{stamp}_{video_type}")
    config.OUTPUT_DIR = run_dir
    config.IMAGES_DIR = os.path.join(run_dir, "images")
    Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    if voice:
        config.VOICE_ID = voice

    print(f"\n🎬 Bhakti Dhun AI · {video_type.upper()} pipeline")
    print("Output folder:", os.path.abspath(config.OUTPUT_DIR))

    banner("1 / 6 · Researching devotional topic [Gemini]")
    research = research_topic(config.CHANNEL_DESCRIPTION, topic_override=topic_override)
    print(f"  Topic: {research.get('topic', '')}")
    print(f"  Title: {research.get('video_title', '')}")
    with open(os.path.join(config.OUTPUT_DIR, "research.json"), "w", encoding="utf-8") as f:
        json.dump(research, f, ensure_ascii=False, indent=2)

    banner("2 / 6 · Writing Hindi script [Gemini]")
    script = write_script(research, video_type=video_type)
    script["video_type"] = video_type
    if not script.get("title"):
        script["title"] = research.get("video_title") or research.get("topic") or "Bhakti Dhun"
    script.setdefault("description", research.get("description", ""))
    script.setdefault("tags", research.get("tags", []))
    with open(os.path.join(config.OUTPUT_DIR, "script.json"), "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"  Sections: {len(script.get('sections', []))}")

    banner("3 / 6 · Downloading visuals [Pixabay]")
    image_map = download_images(script, config.OUTPUT_DIR)
    print(f"  Sections with images: {sum(bool(v) for v in image_map.values())}/{len(image_map)}")

    banner("4 / 6 · Generating Hindi narration [Edge TTS]")
    audio_path = generate_narration(script, config.OUTPUT_DIR)
    print("  Audio:", audio_path)

    banner("5 / 6 · Rendering video [MoviePy/FFmpeg]")
    video_path = os.path.abspath(create_video(
        script, audio_path, config.OUTPUT_DIR, image_map, video_type=video_type
    ))
    if not os.path.isfile(video_path) or os.path.getsize(video_path) < 100_000:
        raise RuntimeError(f"Rendered MP4 missing or unexpectedly small: {video_path}")
    print("  Rendered:", video_path)

    if auto_upload:
        banner("6 / 6 · Automatic YouTube upload")
        url = upload_to_youtube(script, video_path)
        with open(os.path.join(config.OUTPUT_DIR, "upload_result.json"), "w", encoding="utf-8") as f:
            json.dump({"url": url, "video_type": video_type, "title": script["title"],
                       "privacy": config.VIDEO_PRIVACY, "uploaded_at": datetime.now().isoformat()},
                      f, ensure_ascii=False, indent=2)
        print("\nAUTO-UPLOAD SUCCESS:", url)
        print("Visibility:", config.VIDEO_PRIVACY)
        return url

    if no_review:
        print("\nVideo rendered. Upload was not started.")
        return video_path

    banner("6 / 6 · Human review [Flask dashboard]")
    review_data = {"research": research, "script": script, "video_path": video_path}
    with open(os.path.join(config.OUTPUT_DIR, "review_data.json"), "w", encoding="utf-8") as f:
        json.dump({"research": research, "script": script}, f, ensure_ascii=False, indent=2)
    approved = start_review_server(review_data)
    if approved:
        url = upload_to_youtube(script, video_path)
        print("\nVideo uploaded:", url)
    else:
        print("Rejected — pipeline stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate and optionally auto-upload a Bhakti Dhun video.")
    parser.add_argument("--topic", default="", help="Optional exact topic; blank lets AI choose")
    parser.add_argument("--voice", default="", help="Edge TTS voice ID")
    parser.add_argument("--video-type", choices=("normal", "shorts"), default="normal")
    parser.add_argument("--no-review", action="store_true", help="Render only; never upload")
    parser.add_argument("--auto-upload", action="store_true", help="Upload automatically after a successful render")
    args = parser.parse_args()
    run(topic_override=args.topic, voice=args.voice, no_review=args.no_review,
        video_type=args.video_type, auto_upload=args.auto_upload)
