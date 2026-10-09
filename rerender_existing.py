"""Re-render the existing video from saved script, narration, and images (no AI/API regeneration)."""
import glob
import json
import os
import sys

from video.creator import create_video

OUTPUT_DIR = "output"
SCRIPT_PATH = os.path.join(OUTPUT_DIR, "script.json")
AUDIO_PATH = os.path.join(OUTPUT_DIR, "narration.mp3")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")


def main():
    for path in (SCRIPT_PATH, AUDIO_PATH):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Required existing asset missing: {path}")

    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script = json.load(f)

    image_map = {}
    for section in script.get("sections", []):
        sid = section["id"]
        matches = sorted(glob.glob(os.path.join(IMAGES_DIR, f"section_{int(sid):02d}_*")))
        image_map[sid] = [p for p in matches if p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]

    print("Re-rendering existing video assets only; no research, script generation, image downloads, or upload.")
    print("Script:", os.path.abspath(SCRIPT_PATH))
    print("Narration:", os.path.abspath(AUDIO_PATH))
    print("Sections:", len(script.get("sections", [])))
    out = create_video(script, AUDIO_PATH, OUTPUT_DIR, image_map)
    print("\nFresh video rendered:", os.path.abspath(out))
    print("Upload was NOT started. Review the new MP4 before publishing.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"RENDER FAILED: {exc}", file=sys.stderr)
        raise
